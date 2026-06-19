import time

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login as auth_login,
    logout as auth_logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth.views import PasswordChangeDoneView as DjangoPasswordChangeDoneView
from django.http import JsonResponse
from django.shortcuts import redirect, render


User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username',)


def get_dashboard_redirect_name(user):
    """تحديد لوحة التحكم المناسبة حسب دور المستخدم"""
    role = user.get_system_role() if hasattr(user, 'get_system_role') else None

    role_redirects = {
        'SYSTEM_ADMIN': 'home:admin_dashboard',
        'SCHOOL_MANAGER': 'home:manager_dashboard',
        'ACCOUNTANT': 'home:accountant_dashboard',
        'STUDENT_AFFAIRS': 'home:student_affairs_dashboard',
        'BOOKS_INVENTORY': 'home:books_inventory_dashboard',
        'UNIFORMS_INVENTORY': 'home:uniforms_inventory_dashboard',
        'TREASURY_ADMIN': 'treasury_management:dashboard',
        'TREASURY_MANAGER': 'treasury_management:dashboard',
        'TREASURY_ACCOUNTANT': 'treasury_management:dashboard',
        'TREASURY_CASHIER': 'treasury_management:dashboard',
        'TREASURY_VIEWER': 'treasury_management:dashboard',
        'INVENTORY_MANAGER': 'books_inventory:dashboard',
    }

    return role_redirects.get(role, 'home:default_dashboard')


def signup(request):
    """إنشاء حساب جديد"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم التسجيل بنجاح!')
            return redirect('account:login')
    else:
        form = CustomUserCreationForm()

    return render(request, 'account/signup.html', {'form': form})


def login_view(request):
    """تسجيل الدخول وتوجيه المستخدم حسب الدور"""
    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if not user.is_superuser and hasattr(user, 'is_role_active') and not user.is_role_active():
                    messages.error(
                        request,
                        'حسابك غير نشط أو لم يتم تحديد دور لك. يرجى التواصل مع الإدارة.'
                    )
                    return render(request, 'account/login.html', {'form': form})

                auth_login(request, user)
                request.session['last_activity'] = time.time()

                redirect_name = get_dashboard_redirect_name(user)
                try:
                    return redirect(redirect_name)
                except Exception:
                    return redirect('admin:index')

            messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة.')
    else:
        form = AuthenticationForm()

    return render(request, 'account/login.html', {'form': form})


@login_required
def change_password(request):
    """تغيير كلمة المرور"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            request.session['last_activity'] = time.time()
            messages.success(request, 'تم تغيير كلمة المرور بنجاح!')
            return redirect('account:password_change_done')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'account/change_password.html', {'form': form})


class PasswordChangeDoneView(DjangoPasswordChangeDoneView):
    template_name = 'account/change_password_done.html'


@login_required
def view_profile(request):
    """عرض الملف الشخصي"""
    return render(
        request,
        'account/profile.html',
        {
            'user': request.user,
            'user_role': request.user.get_role_display_name()
            if hasattr(request.user, 'get_role_display_name')
            else 'غير محدد',
        }
    )


@login_required
def custom_logout(request):
    """تسجيل خروج مخصص"""
    auth_logout(request)
    messages.success(request, 'تم تسجيل الخروج بنجاح')
    return redirect('account:login')


@login_required
def heartbeat(request):
    """
    يُستدعى من JavaScript كل دقيقة للإعلام بأن المستخدم لا يزال نشطاً.
    يُحدّث وقت آخر نشاط في الـ Session.
    """
    if request.method == 'POST':
        request.session['last_activity'] = time.time()
        return JsonResponse({'status': 'ok'})

    return JsonResponse({'status': 'error'}, status=405)

# from django.contrib import messages
# from django.contrib.auth import (
#     authenticate,
#     get_user_model,
#     login as auth_login,
#     logout as auth_logout,
#     update_session_auth_hash,
# )
# from django.contrib.auth.decorators import login_required
# from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
# from django.contrib.auth.views import PasswordChangeDoneView as DjangoPasswordChangeDoneView
# from django.shortcuts import redirect, render
# from django.views.generic import TemplateView
# import time  # ← أضف هذا في أعلى الملف
# from django.http import JsonResponse

# User = get_user_model()


# class CustomUserCreationForm(UserCreationForm):
#     class Meta:
#         model = User
#         fields = ('username',)


# def get_dashboard_redirect_name(user):
#     """تحديد لوحة التحكم المناسبة حسب دور المستخدم"""
#     role = user.get_system_role() if hasattr(user, 'get_system_role') else None

#     role_redirects = {
#         'SYSTEM_ADMIN': 'home:admin_dashboard',
#         'SCHOOL_MANAGER': 'home:manager_dashboard',
#         'ACCOUNTANT': 'home:accountant_dashboard',
#         'STUDENT_AFFAIRS': 'home:student_affairs_dashboard',
#         'BOOKS_INVENTORY': 'home:books_inventory_dashboard',
#         'UNIFORMS_INVENTORY': 'home:uniforms_inventory_dashboard',

#         # أدوار الخزينة الجديدة
#         'TREASURY_ADMIN': 'treasury_management:dashboard',
#         'TREASURY_MANAGER': 'treasury_management:dashboard',
#         'TREASURY_ACCOUNTANT': 'treasury_management:dashboard',
#         'TREASURY_CASHIER': 'treasury_management:dashboard',
#         'TREASURY_VIEWER': 'treasury_management:dashboard',

#         # أدوار المخازن
#         'INVENTORY_MANAGER': 'books_inventory:dashboard',
#     }

#     return role_redirects.get(role, 'home:default_dashboard')


# def signup(request):
#     """إنشاء حساب جديد"""
#     if request.method == 'POST':
#         form = CustomUserCreationForm(request.POST)

#         if form.is_valid():
#             form.save()
#             messages.success(request, 'تم التسجيل بنجاح!')
#             return redirect('account:login')
#     else:
#         form = CustomUserCreationForm()

#     return render(request, 'account/signup.html', {'form': form})


# def login_view(request):
#     """تسجيل الدخول وتوجيه المستخدم حسب الدور"""
#     if request.method == 'POST':
#         form = AuthenticationForm(request, request.POST)

#         if form.is_valid():
#             username = form.cleaned_data.get('username')
#             password = form.cleaned_data.get('password')

#             user = authenticate(request, username=username, password=password)

#             if user is not None:
#                 # السماح للـ superuser بالدخول حتى بدون SystemRole
#                 if not user.is_superuser and hasattr(user, 'is_role_active') and not user.is_role_active():
#                     messages.error(
#                         request,
#                         'حسابك غير نشط أو لم يتم تحديد دور لك. يرجى التواصل مع الإدارة.'
#                     )
#                     return render(request, 'account/login.html', {'form': form})

#                 auth_login(request, user)

#                 redirect_name = get_dashboard_redirect_name(user)
#                 try:
#                     return redirect(redirect_name)
#                 except Exception:
#                     return redirect('admin:index')

#             messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة.')
#     else:
#         form = AuthenticationForm()

#     return render(request, 'account/login.html', {'form': form})


# @login_required
# def change_password(request):
#     """تغيير كلمة المرور"""
#     if request.method == 'POST':
#         form = PasswordChangeForm(request.user, request.POST)

#         if form.is_valid():
#             user = form.save()
#             update_session_auth_hash(request, user)
#             messages.success(request, 'تم تغيير كلمة المرور بنجاح!')
#             return redirect('account:password_change_done')
#     else:
#         form = PasswordChangeForm(request.user)

#     return render(request, 'account/change_password.html', {'form': form})


# class PasswordChangeDoneView(DjangoPasswordChangeDoneView):
#     template_name = 'account/change_password_done.html'


# @login_required
# def view_profile(request):
#     """عرض الملف الشخصي"""
#     return render(
#         request,
#         'account/profile.html',
#         {
#             'user': request.user,
#             'user_role': request.user.get_role_display_name()
#             if hasattr(request.user, 'get_role_display_name')
#             else 'غير محدد',
#         }
#     )


# @login_required
# def custom_logout(request):
#     """تسجيل خروج مخصص"""
#     auth_logout(request)
#     messages.success(request, 'تم تسجيل الخروج بنجاح')
#     return redirect('account:login')


# # في login_view، بعد سطر auth_login(request, user) أضف:
# def login_view(request):
#     if request.method == 'POST':
#         form = AuthenticationForm(request, request.POST)
#         if form.is_valid():
#             username = form.cleaned_data.get('username')
#             password = form.cleaned_data.get('password')
#             user = authenticate(request, username=username, password=password)

#             if user is not None:
#                 if not user.is_superuser and hasattr(user, 'is_role_active') and not user.is_role_active():
#                     messages.error(
#                         request,
#                         'حسابك غير نشط أو لم يتم تحديد دور لك. يرجى التواصل مع الإدارة.'
#                     )
#                     return render(request, 'account/login.html', {'form': form})

#                 auth_login(request, user)

#                 # ✅ تسجيل وقت الدخول كأول نشاط
#                 request.session['last_activity'] = time.time()

#                 redirect_name = get_dashboard_redirect_name(user)
#                 try:
#                     return redirect(redirect_name)
#                 except Exception:
#                     return redirect('admin:index')

#             messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة.')
#     else:
#         form = AuthenticationForm()

#     return render(request, 'account/login.html', {'form': form})


# # ✅ أضف هذا الـ view الجديد

# @login_required
# def heartbeat(request):
#     """
#     يُستدعى من JavaScript كل دقيقة للإعلام بأن المستخدم لا يزال نشطاً.
#     يُحدّث وقت آخر نشاط في الـ Session.
#     """
#     if request.method == 'POST':
#         request.session['last_activity'] = time.time()
#         return JsonResponse({'status': 'ok'})
#     return JsonResponse({'status': 'error'}, status=405)

