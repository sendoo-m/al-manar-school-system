"""
Decorators وصلاحيات تطبيق الخزينة.

هذا الملف موحد ومنظف:
- حذف تكرار treasury_required
- دعم superuser موثوق فقط (sendoo, admin)
- منع باقي الـ superusers من الخزينة
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

TREASURY_ADMIN_GROUP     = 'treasury_admin'
TREASURY_MANAGER_GROUP   = 'treasury_manager'
TREASURY_ACCOUNTANT_GROUP = 'treasury_accountant'
TREASURY_CASHIER_GROUP   = 'treasury_cashier'
TREASURY_VIEWER_GROUP    = 'treasury_viewer'

TREASURY_GROUPS = [
    TREASURY_ADMIN_GROUP,
    TREASURY_MANAGER_GROUP,
    TREASURY_ACCOUNTANT_GROUP,
    TREASURY_CASHIER_GROUP,
    TREASURY_VIEWER_GROUP,
]

# ===================================
# الحسابات الموثوقة — استثناء من الحجب
# ===================================
TRUSTED_ADMIN_USERNAMES = ['sendoo', 'admin']

TREASURY_ROLE_NAMES = {
    TREASURY_ADMIN_GROUP:      'مدير الخزينة العام',
    TREASURY_MANAGER_GROUP:    'مدير الخزينة',
    TREASURY_ACCOUNTANT_GROUP: 'محاسب الخزينة',
    TREASURY_CASHIER_GROUP:    'أمين الخزينة',
    TREASURY_VIEWER_GROUP:     'مراجع الخزينة',
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


def _is_trusted_admin(user):
    """التحقق إن المستخدم من الحسابات الموثوقة"""
    return (
        user
        and user.is_authenticated
        and user.is_superuser
        and user.username in TRUSTED_ADMIN_USERNAMES
    )


def user_has_any_group(user, groups):
    """التحقق من امتلاك المستخدم لأي مجموعة من المجموعات المطلوبة"""
    if not groups:
        return True

    # الحسابات الموثوقة لها كل الصلاحيات دايمًا
    if _is_trusted_admin(user):
        return True

    # superuser غير موثوق → ممنوع من الخزينة
    if user and user.is_authenticated and user.is_superuser:
        return False

    user_groups = get_user_group_names(user)
    return any(group in user_groups for group in groups)


def user_has_treasury_access(user):
    """التحقق من وجود صلاحية خزينة للمستخدم"""
    if not user or not user.is_authenticated:
        return False

    # الحسابات الموثوقة → دخول كامل دايمًا
    if _is_trusted_admin(user):
        return True

    # أي superuser تاني → ممنوع
    if user.is_superuser:
        return False

    return user_has_any_group(user, TREASURY_GROUPS)


def get_user_treasury_role(user):
    """الحصول على دور المستخدم في الخزينة حسب أولوية المجموعات"""
    if not user or not user.is_authenticated:
        return 'غير مسجل'

    if _is_trusted_admin(user):
        return 'Super Admin'

    # superuser غير موثوق → بدون صلاحية
    if user.is_superuser:
        return 'بدون صلاحية'

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

            # الحسابات الموثوقة فقط تدخل كل شيء
            if _is_trusted_admin(user):
                return view_func(request, *args, **kwargs)

            # superuser غير موثوق → ممنوع فوراً
            if user.is_superuser:
                request.session['requested_url'] = request.get_full_path()
                request.session['required_groups'] = list(groups or [])
                request.session['required_groups_display'] = get_required_groups_display(groups or [])
                request.session['user_groups'] = []
                request.session['treasury_role'] = 'بدون صلاحية'
                request.session['missing_permission'] = permission or ''

                if show_message:
                    messages.error(request, '❌ مديرو النظام ليس لديهم صلاحية الوصول للخزينة.')

                try:
                    return redirect(redirect_url)
                except Exception:
                    return redirect('/')

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
    return treasury_required(groups=[TREASURY_ADMIN_GROUP])(view_func)


def can_manage_users(view_func):
    """إدارة مستخدمي الخزينة - مدير الخزينة العام فقط"""
    return treasury_required(groups=[TREASURY_ADMIN_GROUP])(view_func)


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
# """
# Decorators وصلاحيات تطبيق الخزينة.

# هذا الملف موحد ومنظف:
# - حذف تكرار treasury_required
# - دعم superuser
# - دعم مجموعات الخزينة
# - دعم صلاحيات Django permissions اختيارياً
# - حفظ بيانات الوصول المرفوض في session
# - توجيه موحد إلى صفحة access_denied
# """

# from functools import wraps
# import logging

# from django.contrib import messages
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import redirect

# logger = logging.getLogger(__name__)


# # ===================================
# # أسماء مجموعات الخزينة
# # ===================================

# TREASURY_ADMIN_GROUP = 'treasury_admin'
# TREASURY_MANAGER_GROUP = 'treasury_manager'
# TREASURY_ACCOUNTANT_GROUP = 'treasury_accountant'
# TREASURY_CASHIER_GROUP = 'treasury_cashier'
# TREASURY_VIEWER_GROUP = 'treasury_viewer'

# TREASURY_GROUPS = [
#     TREASURY_ADMIN_GROUP,
#     TREASURY_MANAGER_GROUP,
#     TREASURY_ACCOUNTANT_GROUP,
#     TREASURY_CASHIER_GROUP,
#     TREASURY_VIEWER_GROUP,
# ]

# # ===================================
# # الحسابات الموثوقة — استثناء من الحجب
# # ===================================
# TRUSTED_ADMIN_USERNAMES = ['sendoo', 'admin']

# TREASURY_ROLE_NAMES = {
#     TREASURY_ADMIN_GROUP: 'مدير الخزينة العام',
#     TREASURY_MANAGER_GROUP: 'مدير الخزينة',
#     TREASURY_ACCOUNTANT_GROUP: 'محاسب الخزينة',
#     TREASURY_CASHIER_GROUP: 'أمين الخزينة',
#     TREASURY_VIEWER_GROUP: 'مراجع الخزينة',
# }


# # ===================================
# # Helper Functions
# # ===================================

# def get_user_group_names(user):
#     """إرجاع أسماء مجموعات المستخدم بشكل آمن"""
#     try:
#         if not user or not user.is_authenticated:
#             return []

#         return list(user.groups.values_list('name', flat=True))

#     except Exception as e:
#         logger.error(f'خطأ في قراءة مجموعات المستخدم: {e}')
#         return []


# def user_has_any_group(user, groups):
#     """التحقق من امتلاك المستخدم لأي مجموعة من المجموعات المطلوبة"""
#     if not groups:
#         return True

#     if user and user.is_authenticated and user.is_superuser:
#         return True

#     user_groups = get_user_group_names(user)
#     return any(group in user_groups for group in groups)


# def user_has_treasury_access(user):
#     """التحقق من وجود صلاحية خزينة للمستخدم"""
#     if not user or not user.is_authenticated:
#         return False

#     # الحسابات الموثوقة دايمًا لها دخول كامل
#     if user.is_superuser and user.username in TRUSTED_ADMIN_USERNAMES:
#         return True

#     # أي superuser تاني → ممنوع من الخزينة
#     if user.is_superuser:
#         return False

#     return user_has_any_group(user, TREASURY_GROUPS)

# def get_user_treasury_role(user):
#     """الحصول على دور المستخدم في الخزينة حسب أولوية المجموعات"""
#     if not user or not user.is_authenticated:
#         return 'غير مسجل'

#     if user.is_superuser:
#         return 'Super Admin'

#     user_groups = get_user_group_names(user)

#     role_priority = [
#         TREASURY_ADMIN_GROUP,
#         TREASURY_MANAGER_GROUP,
#         TREASURY_ACCOUNTANT_GROUP,
#         TREASURY_CASHIER_GROUP,
#         TREASURY_VIEWER_GROUP,
#     ]

#     for group_name in role_priority:
#         if group_name in user_groups:
#             return TREASURY_ROLE_NAMES.get(group_name, group_name)

#     return 'بدون صلاحية'


# def get_required_groups_display(groups):
#     """تحويل أسماء المجموعات المطلوبة لأسماء عربية للرسائل"""
#     if not groups:
#         return []

#     return [TREASURY_ROLE_NAMES.get(group, group) for group in groups]


# # ===================================
# # Main Decorator
# # ===================================

# def treasury_required(
#     groups=None,
#     permission=None,
#     redirect_url='treasury_management:access_denied',
#     show_message=True,
# ):
#     """
#     Decorator موحد لصلاحيات الخزينة.

#     Args:
#         groups:
#             قائمة مجموعات مطلوبة. إذا كانت None يعني أي مجموعة خزينة.
#         permission:
#             صلاحية Django اختيارية مثل app_label.permission_codename.
#         redirect_url:
#             صفحة التوجيه عند رفض الوصول.
#         show_message:
#             إظهار رسالة خطأ للمستخدم أم لا.
#     """

#     if groups is None:
#         groups = TREASURY_GROUPS

#     def decorator(view_func):
#         @wraps(view_func)
#         @login_required
#         def _wrapped_view(request, *args, **kwargs):
#             user = request.user

#             # superuser يدخل كل شيء
#             if user.is_superuser:
#                 return view_func(request, *args, **kwargs)

#             user_groups = get_user_group_names(user)
#             has_group_permission = any(group in user_groups for group in groups) if groups else True

#             has_django_permission = True
#             if permission:
#                 has_django_permission = user.has_perm(permission)

#             if has_group_permission and has_django_permission:
#                 return view_func(request, *args, **kwargs)

#             # حفظ معلومات الصفحة المطلوبة لعرضها في access_denied
#             request.session['requested_url'] = request.get_full_path()
#             request.session['required_groups'] = list(groups or [])
#             request.session['required_groups_display'] = get_required_groups_display(groups or [])
#             request.session['user_groups'] = user_groups
#             request.session['treasury_role'] = get_user_treasury_role(user)
#             request.session['missing_permission'] = permission or ''

#             logger.warning(
#                 'Treasury access denied | user=%s | groups=%s | required_groups=%s | permission=%s',
#                 getattr(user, 'username', 'unknown'),
#                 user_groups,
#                 groups,
#                 permission,
#             )

#             if show_message:
#                 required_display = get_required_groups_display(groups or [])
#                 if required_display:
#                     messages.error(
#                         request,
#                         '❌ ليس لديك صلاحية للوصول لهذا القسم. '
#                         f'الصلاحيات المطلوبة: {", ".join(required_display)}'
#                     )
#                 elif permission:
#                     messages.error(request, f'❌ ليس لديك الصلاحية المطلوبة: {permission}')
#                 else:
#                     messages.error(request, '❌ ليس لديك صلاحية للوصول لهذا القسم.')

#             try:
#                 return redirect(redirect_url)
#             except Exception:
#                 return redirect('/')

#         return _wrapped_view

#     return decorator


# # ===================================
# # Decorators حسب مستوى الصلاحية
# # ===================================

# def treasury_access_required(view_func):
#     """أي صلاحية خزينة - وصول أساسي"""
#     return treasury_required(groups=TREASURY_GROUPS)(view_func)


# def treasury_admin_required(view_func):
#     """مدير الخزينة العام فقط"""
#     return treasury_required(groups=[TREASURY_ADMIN_GROUP])(view_func)


# def treasury_manager_required(view_func):
#     """مدير خزينة أو أعلى"""
#     return treasury_required(groups=[
#         TREASURY_ADMIN_GROUP,
#         TREASURY_MANAGER_GROUP,
#     ])(view_func)


# def treasury_accountant_required(view_func):
#     """محاسب خزينة أو أعلى"""
#     return treasury_required(groups=[
#         TREASURY_ADMIN_GROUP,
#         TREASURY_MANAGER_GROUP,
#         TREASURY_ACCOUNTANT_GROUP,
#     ])(view_func)


# def treasury_cashier_required(view_func):
#     """أمين خزينة أو أعلى"""
#     return treasury_required(groups=[
#         TREASURY_ADMIN_GROUP,
#         TREASURY_MANAGER_GROUP,
#         TREASURY_ACCOUNTANT_GROUP,
#         TREASURY_CASHIER_GROUP,
#     ])(view_func)


# def treasury_viewer_required(view_func):
#     """مراجع خزينة أو أي صلاحية أعلى"""
#     return treasury_required(groups=TREASURY_GROUPS)(view_func)


# # ===================================
# # Decorators لوظائف خاصة
# # ===================================

# def can_approve_transactions(view_func):
#     """اعتماد العمليات المالية - مدير خزينة أو أعلى"""
#     return treasury_required(groups=[
#         TREASURY_ADMIN_GROUP,
#         TREASURY_MANAGER_GROUP,
#     ])(view_func)


# def can_cancel_transactions(view_func):
#     """إلغاء العمليات المالية - مدير خزينة أو أعلى"""
#     return treasury_required(groups=[
#         TREASURY_ADMIN_GROUP,
#         TREASURY_MANAGER_GROUP,
#     ])(view_func)


# def can_delete_records(view_func):
#     """حذف السجلات - مدير الخزينة العام فقط"""
#     return treasury_required(groups=[
#         TREASURY_ADMIN_GROUP,
#     ])(view_func)


# def can_manage_users(view_func):
#     """إدارة مستخدمي الخزينة - مدير الخزينة العام فقط"""
#     return treasury_required(groups=[
#         TREASURY_ADMIN_GROUP,
#     ])(view_func)


# def can_access_reports(view_func):
#     """الوصول للتقارير - مدير/محاسب/مراجع"""
#     return treasury_required(groups=[
#         TREASURY_ADMIN_GROUP,
#         TREASURY_MANAGER_GROUP,
#         TREASURY_ACCOUNTANT_GROUP,
#         TREASURY_VIEWER_GROUP,
#     ])(view_func)


# # ===================================
# # اختصارات اختيارية للاستخدام داخل views/templates
# # ===================================

# def can_user_approve_transactions(user):
#     return user_has_any_group(user, [TREASURY_ADMIN_GROUP, TREASURY_MANAGER_GROUP])


# def can_user_cancel_transactions(user):
#     return user_has_any_group(user, [TREASURY_ADMIN_GROUP, TREASURY_MANAGER_GROUP])


# def can_user_delete_records(user):
#     return user_has_any_group(user, [TREASURY_ADMIN_GROUP])


# def can_user_manage_treasury_users(user):
#     return user_has_any_group(user, [TREASURY_ADMIN_GROUP])

