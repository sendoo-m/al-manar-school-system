# home/decorators.py - الحل الوحيد والبسيط
import functools
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

def get_user_role(user):
    """الحصول على دور المستخدم"""
    try:
        if hasattr(user, 'system_role') and user.system_role:
            return user.system_role.role
    except:
        pass
    return None

def role_required(allowed_roles=None, redirect_to='home:access_denied'):
    """decorator موحد للتحقق من صلاحيات النظام"""
    if allowed_roles is None:
        allowed_roles = []
    
    def decorator(view_func):
        @functools.wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            # السوبر يوزر يدخل على كل شي
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            user_role = get_user_role(request.user)
            
            # التحقق من الصلاحية
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                # حفظ معلومات الطلب للصفحة
                request.session['requested_url'] = request.get_full_path()
                request.session['required_roles'] = allowed_roles
                request.session['user_current_role'] = user_role
                request.session['view_name'] = view_func.__name__
                
                return redirect(redirect_to)
        
        return _wrapped_view
    return decorator

# Decorators مخصصة لكل دور
system_admin_required = role_required(['SYSTEM_ADMIN'])
school_manager_required = role_required(['SYSTEM_ADMIN', 'SCHOOL_MANAGER'])
accountant_required = role_required(['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'ACCOUNTANT'])
student_affairs_required = role_required(['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'STUDENT_AFFAIRS'])
books_inventory_required = role_required(['SYSTEM_ADMIN', 'BOOKS_INVENTORY'])
uniforms_inventory_required = role_required(['SYSTEM_ADMIN', 'UNIFORMS_INVENTORY'])

# decorator للأقسام التي تحتاج صلاحيات متعددة
inventory_staff_required = role_required(['SYSTEM_ADMIN', 'BOOKS_INVENTORY', 'UNIFORMS_INVENTORY'])
financial_staff_required = role_required(['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'ACCOUNTANT'])
academic_staff_required = role_required(['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'STUDENT_AFFAIRS'])
