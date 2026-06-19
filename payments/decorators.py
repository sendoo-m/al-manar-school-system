from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


# ===================================
# الحسابات الموثوقة — استثناء من الحجب
# ===================================
TRUSTED_ADMIN_USERNAMES = ['sendoo', 'admin']


def get_payment_user_role(user):
    """
    جلب دور المستخدم بشكل آمن.
    متوافق مع system_role إن وجد، ومع is_superuser / is_staff.
    """
    try:
        if hasattr(user, 'system_role') and user.system_role:
            return user.system_role.role

        if user.is_superuser:
            return 'SYSTEM_ADMIN'

        if user.is_staff:
            return 'ACCOUNTANT'

        return 'USER'

    except Exception:
        if getattr(user, 'is_superuser', False):
            return 'SYSTEM_ADMIN'

        if getattr(user, 'is_staff', False):
            return 'ACCOUNTANT'

        return 'USER'


def _is_trusted_admin(user):
    """التحقق إن المستخدم من الحسابات الموثوقة"""
    return (
        user
        and user.is_authenticated
        and user.is_superuser
        and user.username in TRUSTED_ADMIN_USERNAMES
    )


def payments_basic_access(view_func):
    """
    صلاحية أساسية لدخول تطبيق المدفوعات.
    الحسابات الموثوقة → دخول دايمًا.
    SYSTEM_ADMIN / SCHOOL_MANAGER غير موثوقين → ممنوعون.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if _is_trusted_admin(user):
            return view_func(request, *args, **kwargs)

        role = get_payment_user_role(user)

        if role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
            messages.error(request, '❌ مديرو النظام ليس لديهم صلاحية الوصول للمدفوعات')
            return redirect('payments:access_denied')

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def payments_full_access(view_func):
    """
    صلاحية كاملة لإضافة وتعديل المدفوعات.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if _is_trusted_admin(user):
            return view_func(request, *args, **kwargs)

        role = get_payment_user_role(user)

        if role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
            messages.error(request, '❌ مديرو النظام ليس لديهم صلاحية الوصول للمدفوعات')
            return redirect('payments:access_denied')

        if role not in ['ACCOUNTANT', 'ADMIN']:
            messages.error(request, '❌ لا تملك صلاحية كافية لإدارة المدفوعات')
            return redirect('payments:payments_home')

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def payments_manager_access(view_func):
    """
    صلاحية إدارية للمدفوعات.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if _is_trusted_admin(user):
            return view_func(request, *args, **kwargs)

        role = get_payment_user_role(user)

        if role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
            messages.error(request, '❌ مديرو النظام ليس لديهم صلاحية الوصول للمدفوعات')
            return redirect('payments:access_denied')

        if role not in ['ADMIN']:
            messages.error(request, '❌ لا تملك صلاحية إدارية للوصول لهذه الصفحة')
            return redirect('payments:payments_home')

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def payments_admin_access(view_func):
    """
    صلاحية الإدارة العليا — الحسابات الموثوقة فقط.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if _is_trusted_admin(user):
            return view_func(request, *args, **kwargs)

        role = get_payment_user_role(user)

        if role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
            messages.error(request, '❌ مديرو النظام ليس لديهم صلاحية الوصول للمدفوعات')
            return redirect('payments:access_denied')

        messages.error(request, '❌ هذه الصفحة تتطلب صلاحية المدير العام')
        return redirect('payments:payments_home')

    return _wrapped_view


def payments_sensitive_operation(view_func):
    """
    العمليات الحساسة مثل الحذف وإلغاء المدفوعات.
    الحسابات الموثوقة فقط.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if _is_trusted_admin(user):
            return view_func(request, *args, **kwargs)

        role = get_payment_user_role(user)

        if role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
            messages.error(request, '❌ مديرو النظام ليس لديهم صلاحية الوصول للمدفوعات')
            return redirect('payments:access_denied')

        messages.error(request, '❌ هذه العملية تتطلب صلاحية إدارية عليا')
        return redirect('payments:payments_home')

    return _wrapped_view


def payments_financial_reports(view_func):
    """
    التقارير المالية.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if _is_trusted_admin(user):
            return view_func(request, *args, **kwargs)

        role = get_payment_user_role(user)

        if role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
            messages.error(request, '❌ مديرو النظام ليس لديهم صلاحية الوصول للمدفوعات')
            return redirect('payments:access_denied')

        if role not in ['ACCOUNTANT', 'ADMIN']:
            messages.error(request, '❌ لا تملك صلاحية لعرض التقارير المالية')
            return redirect('payments:payments_home')

        return view_func(request, *args, **kwargs)

    return _wrapped_view

# # payments/decorators.py

# from functools import wraps

# from django.contrib import messages
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import redirect


# def get_payment_user_role(user):
#     """
#     جلب دور المستخدم بشكل آمن.
#     متوافق مع system_role إن وجد، ومع is_superuser / is_staff.
#     """
#     try:
#         if hasattr(user, 'system_role') and user.system_role:
#             return user.system_role.role

#         if user.is_superuser:
#             return 'SYSTEM_ADMIN'

#         if user.is_staff:
#             return 'ACCOUNTANT'

#         return 'USER'

#     except Exception:
#         if getattr(user, 'is_superuser', False):
#             return 'SYSTEM_ADMIN'

#         if getattr(user, 'is_staff', False):
#             return 'ACCOUNTANT'

#         return 'USER'


# def payments_basic_access(view_func):
#     """
#     صلاحية أساسية لدخول تطبيق المدفوعات.
#     """
#     @wraps(view_func)
#     @login_required
#     def _wrapped_view(request, *args, **kwargs):
#         return view_func(request, *args, **kwargs)

#     return _wrapped_view


# def payments_full_access(view_func):
#     """
#     صلاحية كاملة لإضافة وتعديل المدفوعات.
#     """
#     @wraps(view_func)
#     @login_required
#     def _wrapped_view(request, *args, **kwargs):
#         role = get_payment_user_role(request.user)

#         if role not in [
#             'SYSTEM_ADMIN',
#             'SCHOOL_MANAGER',
#             'ACCOUNTANT',
#             'ADMIN',
#         ]:
#             messages.error(request, 'لا تملك صلاحية كافية لإدارة المدفوعات')
#             return redirect('payments:payments_home')

#         return view_func(request, *args, **kwargs)

#     return _wrapped_view


# def payments_manager_access(view_func):
#     """
#     صلاحية إدارية للمدفوعات.
#     """
#     @wraps(view_func)
#     @login_required
#     def _wrapped_view(request, *args, **kwargs):
#         role = get_payment_user_role(request.user)

#         if role not in [
#             'SYSTEM_ADMIN',
#             'SCHOOL_MANAGER',
#             'ADMIN',
#         ]:
#             messages.error(request, 'لا تملك صلاحية إدارية للوصول لهذه الصفحة')
#             return redirect('payments:payments_home')

#         return view_func(request, *args, **kwargs)

#     return _wrapped_view


# def payments_admin_access(view_func):
#     """
#     صلاحية الإدارة العليا.
#     """
#     @wraps(view_func)
#     @login_required
#     def _wrapped_view(request, *args, **kwargs):
#         role = get_payment_user_role(request.user)

#         if role != 'SYSTEM_ADMIN':
#             messages.error(request, 'هذه الصفحة تتطلب صلاحية المدير العام')
#             return redirect('payments:payments_home')

#         return view_func(request, *args, **kwargs)

#     return _wrapped_view


# def payments_sensitive_operation(view_func):
#     """
#     العمليات الحساسة مثل الحذف، إلغاء المدفوعات، أو ترحيل الخزنة.
#     """
#     @wraps(view_func)
#     @login_required
#     def _wrapped_view(request, *args, **kwargs):
#         role = get_payment_user_role(request.user)

#         if role != 'SYSTEM_ADMIN':
#             messages.error(request, 'هذه العملية تتطلب صلاحية إدارية عليا')
#             return redirect('payments:payments_home')

#         return view_func(request, *args, **kwargs)

#     return _wrapped_view


# def payments_financial_reports(view_func):
#     """
#     التقارير المالية.
#     """
#     @wraps(view_func)
#     @login_required
#     def _wrapped_view(request, *args, **kwargs):
#         role = get_payment_user_role(request.user)

#         if role not in [
#             'SYSTEM_ADMIN',
#             'SCHOOL_MANAGER',
#             'ACCOUNTANT',
#             'ADMIN',
#         ]:
#             messages.error(request, 'لا تملك صلاحية لعرض التقارير المالية')
#             return redirect('payments:payments_home')

#         return view_func(request, *args, **kwargs)

#     return _wrapped_view

