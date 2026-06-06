# treasury_management/decorators.py
"""
Decorators وصلاحيات تطبيق الخزينة.

هذا الملف موحد ومنظف:
- حذف تكرار treasury_required
- دعم superuser
- دعم مجموعات الخزينة
- دعم صلاحيات Django permissions اختيارياً
- حفظ بيانات الوصول المرفوض في session
- توجيه موحد إلى صفحة access_denied
"""

from functools import wraps
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


# ===================================
# أسماء مجموعات الخزينة
# ===================================

TREASURY_ADMIN_GROUP = 'treasury_admin'
TREASURY_MANAGER_GROUP = 'treasury_manager'
TREASURY_ACCOUNTANT_GROUP = 'treasury_accountant'
TREASURY_CASHIER_GROUP = 'treasury_cashier'
TREASURY_VIEWER_GROUP = 'treasury_viewer'

TREASURY_GROUPS = [
    TREASURY_ADMIN_GROUP,
    TREASURY_MANAGER_GROUP,
    TREASURY_ACCOUNTANT_GROUP,
    TREASURY_CASHIER_GROUP,
    TREASURY_VIEWER_GROUP,
]

TREASURY_ROLE_NAMES = {
    TREASURY_ADMIN_GROUP: 'مدير الخزينة العام',
    TREASURY_MANAGER_GROUP: 'مدير الخزينة',
    TREASURY_ACCOUNTANT_GROUP: 'محاسب الخزينة',
    TREASURY_CASHIER_GROUP: 'أمين الخزينة',
    TREASURY_VIEWER_GROUP: 'مراجع الخزينة',
}


# ===================================
# Helper Functions
# ===================================

def get_user_group_names(user):
    """إرجاع أسماء مجموعات المستخدم بشكل آمن"""
    try:
        if not user or not user.is_authenticated:
            return []

        return list(user.groups.values_list('name', flat=True))

    except Exception as e:
        logger.error(f'خطأ في قراءة مجموعات المستخدم: {e}')
        return []


def user_has_any_group(user, groups):
    """التحقق من امتلاك المستخدم لأي مجموعة من المجموعات المطلوبة"""
    if not groups:
        return True

    if user and user.is_authenticated and user.is_superuser:
        return True

    user_groups = get_user_group_names(user)
    return any(group in user_groups for group in groups)


def user_has_treasury_access(user):
    """التحقق من وجود صلاحية خزينة للمستخدم"""
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return user_has_any_group(user, TREASURY_GROUPS)


def get_user_treasury_role(user):
    """الحصول على دور المستخدم في الخزينة حسب أولوية المجموعات"""
    if not user or not user.is_authenticated:
        return 'غير مسجل'

    if user.is_superuser:
        return 'Super Admin'

    user_groups = get_user_group_names(user)

    role_priority = [
        TREASURY_ADMIN_GROUP,
        TREASURY_MANAGER_GROUP,
        TREASURY_ACCOUNTANT_GROUP,
        TREASURY_CASHIER_GROUP,
        TREASURY_VIEWER_GROUP,
    ]

    for group_name in role_priority:
        if group_name in user_groups:
            return TREASURY_ROLE_NAMES.get(group_name, group_name)

    return 'بدون صلاحية'


def get_required_groups_display(groups):
    """تحويل أسماء المجموعات المطلوبة لأسماء عربية للرسائل"""
    if not groups:
        return []

    return [TREASURY_ROLE_NAMES.get(group, group) for group in groups]


# ===================================
# Main Decorator
# ===================================

def treasury_required(
    groups=None,
    permission=None,
    redirect_url='treasury_management:access_denied',
    show_message=True,
):
    """
    Decorator موحد لصلاحيات الخزينة.

    Args:
        groups:
            قائمة مجموعات مطلوبة. إذا كانت None يعني أي مجموعة خزينة.
        permission:
            صلاحية Django اختيارية مثل app_label.permission_codename.
        redirect_url:
            صفحة التوجيه عند رفض الوصول.
        show_message:
            إظهار رسالة خطأ للمستخدم أم لا.
    """

    if groups is None:
        groups = TREASURY_GROUPS

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            # superuser يدخل كل شيء
            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_groups = get_user_group_names(user)
            has_group_permission = any(group in user_groups for group in groups) if groups else True

            has_django_permission = True
            if permission:
                has_django_permission = user.has_perm(permission)

            if has_group_permission and has_django_permission:
                return view_func(request, *args, **kwargs)

            # حفظ معلومات الصفحة المطلوبة لعرضها في access_denied
            request.session['requested_url'] = request.get_full_path()
            request.session['required_groups'] = list(groups or [])
            request.session['required_groups_display'] = get_required_groups_display(groups or [])
            request.session['user_groups'] = user_groups
            request.session['treasury_role'] = get_user_treasury_role(user)
            request.session['missing_permission'] = permission or ''

            logger.warning(
                'Treasury access denied | user=%s | groups=%s | required_groups=%s | permission=%s',
                getattr(user, 'username', 'unknown'),
                user_groups,
                groups,
                permission,
            )

            if show_message:
                required_display = get_required_groups_display(groups or [])
                if required_display:
                    messages.error(
                        request,
                        '❌ ليس لديك صلاحية للوصول لهذا القسم. '
                        f'الصلاحيات المطلوبة: {", ".join(required_display)}'
                    )
                elif permission:
                    messages.error(request, f'❌ ليس لديك الصلاحية المطلوبة: {permission}')
                else:
                    messages.error(request, '❌ ليس لديك صلاحية للوصول لهذا القسم.')

            try:
                return redirect(redirect_url)
            except Exception:
                return redirect('/')

        return _wrapped_view

    return decorator


# ===================================
# Decorators حسب مستوى الصلاحية
# ===================================

def treasury_access_required(view_func):
    """أي صلاحية خزينة - وصول أساسي"""
    return treasury_required(groups=TREASURY_GROUPS)(view_func)


def treasury_admin_required(view_func):
    """مدير الخزينة العام فقط"""
    return treasury_required(groups=[TREASURY_ADMIN_GROUP])(view_func)


def treasury_manager_required(view_func):
    """مدير خزينة أو أعلى"""
    return treasury_required(groups=[
        TREASURY_ADMIN_GROUP,
        TREASURY_MANAGER_GROUP,
    ])(view_func)


def treasury_accountant_required(view_func):
    """محاسب خزينة أو أعلى"""
    return treasury_required(groups=[
        TREASURY_ADMIN_GROUP,
        TREASURY_MANAGER_GROUP,
        TREASURY_ACCOUNTANT_GROUP,
    ])(view_func)


def treasury_cashier_required(view_func):
    """أمين خزينة أو أعلى"""
    return treasury_required(groups=[
        TREASURY_ADMIN_GROUP,
        TREASURY_MANAGER_GROUP,
        TREASURY_ACCOUNTANT_GROUP,
        TREASURY_CASHIER_GROUP,
    ])(view_func)


def treasury_viewer_required(view_func):
    """مراجع خزينة أو أي صلاحية أعلى"""
    return treasury_required(groups=TREASURY_GROUPS)(view_func)


# ===================================
# Decorators لوظائف خاصة
# ===================================

def can_approve_transactions(view_func):
    """اعتماد العمليات المالية - مدير خزينة أو أعلى"""
    return treasury_required(groups=[
        TREASURY_ADMIN_GROUP,
        TREASURY_MANAGER_GROUP,
    ])(view_func)


def can_cancel_transactions(view_func):
    """إلغاء العمليات المالية - مدير خزينة أو أعلى"""
    return treasury_required(groups=[
        TREASURY_ADMIN_GROUP,
        TREASURY_MANAGER_GROUP,
    ])(view_func)


def can_delete_records(view_func):
    """حذف السجلات - مدير الخزينة العام فقط"""
    return treasury_required(groups=[
        TREASURY_ADMIN_GROUP,
    ])(view_func)


def can_manage_users(view_func):
    """إدارة مستخدمي الخزينة - مدير الخزينة العام فقط"""
    return treasury_required(groups=[
        TREASURY_ADMIN_GROUP,
    ])(view_func)


def can_access_reports(view_func):
    """الوصول للتقارير - مدير/محاسب/مراجع"""
    return treasury_required(groups=[
        TREASURY_ADMIN_GROUP,
        TREASURY_MANAGER_GROUP,
        TREASURY_ACCOUNTANT_GROUP,
        TREASURY_VIEWER_GROUP,
    ])(view_func)


# ===================================
# اختصارات اختيارية للاستخدام داخل views/templates
# ===================================

def can_user_approve_transactions(user):
    return user_has_any_group(user, [TREASURY_ADMIN_GROUP, TREASURY_MANAGER_GROUP])


def can_user_cancel_transactions(user):
    return user_has_any_group(user, [TREASURY_ADMIN_GROUP, TREASURY_MANAGER_GROUP])


def can_user_delete_records(user):
    return user_has_any_group(user, [TREASURY_ADMIN_GROUP])


def can_user_manage_treasury_users(user):
    return user_has_any_group(user, [TREASURY_ADMIN_GROUP])

# # treasury_management/decorators.py
# from functools import wraps
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import redirect
# from django.contrib import messages
# from django.http import HttpResponseForbidden
# import logging
# # treasury_management/decorators.py - تحديث الـ decorator
# import functools
# from django.shortcuts import redirect
# from django.contrib import messages
# from django.shortcuts import render
# logger = logging.getLogger(__name__)

# def treasury_required(permission=None, groups=None, redirect_url='home:home'):
#     """
#     التحقق من صلاحيات الخزينة
    
#     Args:
#         permission: صلاحية Django مطلوبة
#         groups: قائمة بأسماء المجموعات المطلوبة
#         redirect_url: رابط التوجيه عند عدم وجود صلاحية
#     """
#     def decorator(view_func):
#         @wraps(view_func)
#         @login_required
#         def _wrapped_view(request, *args, **kwargs):
#             user = request.user
            
#             # السماح للـ superuser دائماً
#             if user.is_superuser:
#                 return view_func(request, *args, **kwargs)
            
#             # التحقق من المجموعات المطلوبة
#             if groups:
#                 user_groups = list(user.groups.values_list('name', flat=True))
#                 has_required_group = any(group in user_groups for group in groups)
                
#                 if not has_required_group:
#                     logger.warning(f'User {user.username} attempted access without required groups: {groups}')
#                     messages.error(
#                         request, 
#                         f'❌ ليس لديك صلاحية للوصول لهذا القسم. الصلاحيات المطلوبة: {", ".join(groups)}'
#                     )
#                     try:
#                         return redirect(redirect_url)
#                     except:
#                         return redirect('/')
            
#             # التحقق من الصلاحية المحددة
#             if permission:
#                 if not user.has_perm(permission):
#                     logger.warning(f'User {user.username} attempted access without permission: {permission}')
#                     messages.error(request, f'❌ ليس لديك صلاحية: {permission}')
#                     try:
#                         return redirect(redirect_url)
#                     except:
#                         return redirect('/')
            
#             return view_func(request, *args, **kwargs)
#         return _wrapped_view
#     return decorator

# # Decorators للمستويات المختلفة
# def treasury_admin_required(view_func):
#     """مدير خزينة عام فقط - كامل الصلاحيات"""
#     return treasury_required(groups=['treasury_admin'])(view_func)

# def treasury_manager_required(view_func):
#     """مدير خزينة أو أعلى - إدارة وإشراف"""
#     return treasury_required(groups=['treasury_admin', 'treasury_manager'])(view_func)

# def treasury_accountant_required(view_func):
#     """محاسب أو أعلى - عمليات محاسبية"""
#     return treasury_required(groups=['treasury_admin', 'treasury_manager', 'treasury_accountant'])(view_func)

# def treasury_cashier_required(view_func):
#     """أمين خزينة أو أعلى - عمليات نقدية"""
#     return treasury_required(groups=['treasury_admin', 'treasury_manager', 'treasury_accountant', 'treasury_cashier'])(view_func)

# def treasury_access_required(view_func):
#     """أي صلاحية خزينة - وصول أساسي"""
#     return treasury_required(groups=[
#         'treasury_admin', 'treasury_manager', 'treasury_accountant', 
#         'treasury_cashier', 'treasury_viewer'
#     ])(view_func)

# # Decorators للوظائف الخاصة
# def can_approve_transactions(view_func):
#     """يمكنه اعتماد العمليات المالية"""
#     return treasury_required(groups=['treasury_admin', 'treasury_manager'])(view_func)

# def can_cancel_transactions(view_func):
#     """يمكنه إلغاء العمليات المالية"""
#     return treasury_required(groups=['treasury_admin', 'treasury_manager'])(view_func)

# def can_delete_records(view_func):
#     """يمكنه حذف السجلات"""
#     return treasury_required(groups=['treasury_admin'])(view_func)

# def can_manage_users(view_func):
#     """يمكنه إدارة المستخدمين"""
#     return treasury_required(groups=['treasury_admin'])(view_func)

# def can_access_reports(view_func):
#     """يمكنه الوصول للتقارير"""
#     return treasury_required(groups=[
#         'treasury_admin', 'treasury_manager', 'treasury_accountant', 'treasury_viewer'
#     ])(view_func)

# # Helper Functions
# def user_has_treasury_access(user):
#     """التحقق من وجود صلاحية خزينة للمستخدم"""
#     if user.is_superuser:
#         return True
    
#     treasury_groups = [
#         'treasury_admin', 'treasury_manager', 'treasury_accountant', 
#         'treasury_cashier', 'treasury_viewer'
#     ]
    
#     user_groups = user.groups.values_list('name', flat=True)
#     return any(group in user_groups for group in treasury_groups)

# def get_user_treasury_role(user):
#     """الحصول على دور المستخدم في الخزينة"""
#     if user.is_superuser:
#         return 'Super Admin'
    
#     user_groups = list(user.groups.values_list('name', flat=True))
    
#     role_priority = [
#         ('treasury_admin', 'مدير الخزينة العام'),
#         ('treasury_manager', 'مدير الخزينة'),
#         ('treasury_accountant', 'محاسب الخزينة'),
#         ('treasury_cashier', 'أمين الخزينة'),
#         ('treasury_viewer', 'مراجع الخزينة'),
#     ]
    
#     for group_name, role_name in role_priority:
#         if group_name in user_groups:
#             return role_name
    
#     return 'بدون صلاحية'


# def treasury_required(allowed_groups=None, redirect_url='treasury_management:access_denied'):
#     """
#     تحسين decorator للصلاحيات مع صفحة رفض مخصصة
#     """
#     if allowed_groups is None:
#         allowed_groups = [
#             'treasury_admin', 'treasury_manager', 'treasury_accountant', 
#             'treasury_cashier', 'treasury_viewer'
#         ]
    
#     def decorator(view_func):
#         @functools.wraps(view_func)
#         @login_required
#         def _wrapped_view(request, *args, **kwargs):
#             if request.user.is_superuser:
#                 return view_func(request, *args, **kwargs)
            
#             user_groups = request.user.groups.values_list('name', flat=True)
#             has_permission = any(group in user_groups for group in allowed_groups)
            
#             if has_permission:
#                 return view_func(request, *args, **kwargs)
#             else:
#                 # حفظ معلومات الصفحة المطلوبة
#                 request.session['requested_url'] = request.get_full_path()
#                 request.session['required_groups'] = allowed_groups
#                 request.session['user_groups'] = list(user_groups)
                
#                 return redirect(redirect_url)
        
#         return _wrapped_view
#     return decorator

# # استخدام الـ decorator المحسن
# treasury_access_required = treasury_required()
# treasury_admin_required = treasury_required(['treasury_admin'])
# treasury_manager_required = treasury_required(['treasury_admin', 'treasury_manager'])
# treasury_accountant_required = treasury_required(['treasury_admin', 'treasury_manager', 'treasury_accountant'])
# treasury_cashier_required = treasury_required(['treasury_admin', 'treasury_manager', 'treasury_accountant', 'treasury_cashier'])
# can_approve_transactions = treasury_required(['treasury_admin', 'treasury_manager'])
