# في payments/decorators.py أو في أعلى views.py

from django.contrib.auth.decorators import login_required
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

def payments_basic_access(view_func):
    """صلاحية أساسية للمدفوعات"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def payments_full_access(view_func):
    """صلاحية كاملة للمدفوعات"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def payments_manager_access(view_func):
    """صلاحية إدارية"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, 'لا تملك صلاحية للوصول لهذه الصفحة')
            return redirect('payments:payments_home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def payments_admin_access(view_func):
    """صلاحية إدارة عليا"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, 'لا تملك صلاحية إدارية كافية')
            return redirect('payments:payments_home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def payments_sensitive_operation(view_func):
    """العمليات الحساسة"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, 'هذه العملية تتطلب صلاحية إدارية عليا')
            return redirect('payments:payments_home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def payments_financial_reports(view_func):
    """التقارير المالية"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view
