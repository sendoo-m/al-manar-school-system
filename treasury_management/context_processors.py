# treasury_management/context_processors.py
from .decorators import user_has_treasury_access, get_user_treasury_role

def treasury_permissions(request):
    """إضافة معلومات صلاحيات الخزينة للقوالب"""
    if not request.user.is_authenticated:
        return {}
    
    user = request.user
    user_groups = list(user.groups.values_list('name', flat=True))
    
    # التحقق من الصلاحيات
    has_access = user_has_treasury_access(user)
    
    permissions = {
        # الوصول الأساسي
        'has_treasury_access': has_access,
        'treasury_role': get_user_treasury_role(user),
        
        # مستويات الصلاحيات
        'is_treasury_admin': user.is_superuser or 'treasury_admin' in user_groups,
        'is_treasury_manager': user.is_superuser or any(group in user_groups for group in ['treasury_admin', 'treasury_manager']),
        'is_treasury_accountant': user.is_superuser or any(group in user_groups for group in ['treasury_admin', 'treasury_manager', 'treasury_accountant']),
        'is_treasury_cashier': user.is_superuser or any(group in user_groups for group in ['treasury_admin', 'treasury_manager', 'treasury_accountant', 'treasury_cashier']),
        'is_treasury_viewer': has_access,
        
        # صلاحيات خاصة
        'can_approve_transactions': user.is_superuser or any(group in user_groups for group in ['treasury_admin', 'treasury_manager']),
        'can_cancel_transactions': user.is_superuser or any(group in user_groups for group in ['treasury_admin', 'treasury_manager']),
        'can_delete_records': user.is_superuser or 'treasury_admin' in user_groups,
        'can_manage_users': user.is_superuser or 'treasury_admin' in user_groups,
        'can_access_reports': user.is_superuser or any(group in user_groups for group in ['treasury_admin', 'treasury_manager', 'treasury_accountant', 'treasury_viewer']),
        
        # معلومات إضافية
        'treasury_groups': user_groups,
        'treasury_permissions': list(user.get_all_permissions()) if user.is_authenticated else [],
    }
    
    return permissions
