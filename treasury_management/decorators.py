# treasury_management/decorators.py
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
import logging
# treasury_management/decorators.py - تحديث الـ decorator
import functools
from django.shortcuts import redirect
from django.contrib import messages
from django.shortcuts import render
logger = logging.getLogger(__name__)

def treasury_required(permission=None, groups=None, redirect_url='home:home'):
    """
    التحقق من صلاحيات الخزينة
    
    Args:
        permission: صلاحية Django مطلوبة
        groups: قائمة بأسماء المجموعات المطلوبة
        redirect_url: رابط التوجيه عند عدم وجود صلاحية
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            # السماح للـ superuser دائماً
            if user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # التحقق من المجموعات المطلوبة
            if groups:
                user_groups = list(user.groups.values_list('name', flat=True))
                has_required_group = any(group in user_groups for group in groups)
                
                if not has_required_group:
                    logger.warning(f'User {user.username} attempted access without required groups: {groups}')
                    messages.error(
                        request, 
                        f'❌ ليس لديك صلاحية للوصول لهذا القسم. الصلاحيات المطلوبة: {", ".join(groups)}'
                    )
                    try:
                        return redirect(redirect_url)
                    except:
                        return redirect('/')
            
            # التحقق من الصلاحية المحددة
            if permission:
                if not user.has_perm(permission):
                    logger.warning(f'User {user.username} attempted access without permission: {permission}')
                    messages.error(request, f'❌ ليس لديك صلاحية: {permission}')
                    try:
                        return redirect(redirect_url)
                    except:
                        return redirect('/')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# Decorators للمستويات المختلفة
def treasury_admin_required(view_func):
    """مدير خزينة عام فقط - كامل الصلاحيات"""
    return treasury_required(groups=['treasury_admin'])(view_func)

def treasury_manager_required(view_func):
    """مدير خزينة أو أعلى - إدارة وإشراف"""
    return treasury_required(groups=['treasury_admin', 'treasury_manager'])(view_func)

def treasury_accountant_required(view_func):
    """محاسب أو أعلى - عمليات محاسبية"""
    return treasury_required(groups=['treasury_admin', 'treasury_manager', 'treasury_accountant'])(view_func)

def treasury_cashier_required(view_func):
    """أمين خزينة أو أعلى - عمليات نقدية"""
    return treasury_required(groups=['treasury_admin', 'treasury_manager', 'treasury_accountant', 'treasury_cashier'])(view_func)

def treasury_access_required(view_func):
    """أي صلاحية خزينة - وصول أساسي"""
    return treasury_required(groups=[
        'treasury_admin', 'treasury_manager', 'treasury_accountant', 
        'treasury_cashier', 'treasury_viewer'
    ])(view_func)

# Decorators للوظائف الخاصة
def can_approve_transactions(view_func):
    """يمكنه اعتماد العمليات المالية"""
    return treasury_required(groups=['treasury_admin', 'treasury_manager'])(view_func)

def can_cancel_transactions(view_func):
    """يمكنه إلغاء العمليات المالية"""
    return treasury_required(groups=['treasury_admin', 'treasury_manager'])(view_func)

def can_delete_records(view_func):
    """يمكنه حذف السجلات"""
    return treasury_required(groups=['treasury_admin'])(view_func)

def can_manage_users(view_func):
    """يمكنه إدارة المستخدمين"""
    return treasury_required(groups=['treasury_admin'])(view_func)

def can_access_reports(view_func):
    """يمكنه الوصول للتقارير"""
    return treasury_required(groups=[
        'treasury_admin', 'treasury_manager', 'treasury_accountant', 'treasury_viewer'
    ])(view_func)

# Helper Functions
def user_has_treasury_access(user):
    """التحقق من وجود صلاحية خزينة للمستخدم"""
    if user.is_superuser:
        return True
    
    treasury_groups = [
        'treasury_admin', 'treasury_manager', 'treasury_accountant', 
        'treasury_cashier', 'treasury_viewer'
    ]
    
    user_groups = user.groups.values_list('name', flat=True)
    return any(group in user_groups for group in treasury_groups)

def get_user_treasury_role(user):
    """الحصول على دور المستخدم في الخزينة"""
    if user.is_superuser:
        return 'Super Admin'
    
    user_groups = list(user.groups.values_list('name', flat=True))
    
    role_priority = [
        ('treasury_admin', 'مدير الخزينة العام'),
        ('treasury_manager', 'مدير الخزينة'),
        ('treasury_accountant', 'محاسب الخزينة'),
        ('treasury_cashier', 'أمين الخزينة'),
        ('treasury_viewer', 'مراجع الخزينة'),
    ]
    
    for group_name, role_name in role_priority:
        if group_name in user_groups:
            return role_name
    
    return 'بدون صلاحية'


def treasury_required(allowed_groups=None, redirect_url='treasury_management:access_denied'):
    """
    تحسين decorator للصلاحيات مع صفحة رفض مخصصة
    """
    if allowed_groups is None:
        allowed_groups = [
            'treasury_admin', 'treasury_manager', 'treasury_accountant', 
            'treasury_cashier', 'treasury_viewer'
        ]
    
    def decorator(view_func):
        @functools.wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            user_groups = request.user.groups.values_list('name', flat=True)
            has_permission = any(group in user_groups for group in allowed_groups)
            
            if has_permission:
                return view_func(request, *args, **kwargs)
            else:
                # حفظ معلومات الصفحة المطلوبة
                request.session['requested_url'] = request.get_full_path()
                request.session['required_groups'] = allowed_groups
                request.session['user_groups'] = list(user_groups)
                
                return redirect(redirect_url)
        
        return _wrapped_view
    return decorator

# استخدام الـ decorator المحسن
treasury_access_required = treasury_required()
treasury_admin_required = treasury_required(['treasury_admin'])
treasury_manager_required = treasury_required(['treasury_admin', 'treasury_manager'])
treasury_accountant_required = treasury_required(['treasury_admin', 'treasury_manager', 'treasury_accountant'])
treasury_cashier_required = treasury_required(['treasury_admin', 'treasury_manager', 'treasury_accountant', 'treasury_cashier'])
can_approve_transactions = treasury_required(['treasury_admin', 'treasury_manager'])
