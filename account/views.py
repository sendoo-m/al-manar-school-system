from django.shortcuts import render, redirect
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth import login, authenticate, update_session_auth_hash, logout
from django.views.generic import TemplateView
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.contrib.auth import authenticate, login as auth_login
from django import forms

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username',)

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم التسجيل بنجاح!')
            return redirect('account:login')
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form,
    }
    return render(request, 'account/signup.html', context)

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                # التحقق من وجود دور نشط
                if not user.is_role_active():
                    messages.error(request, 'حسابك غير نشط أو لم يتم تحديد دور لك. يرجى التواصل مع الإدارة.')
                    return render(request, 'account/login.html', {'form': form})
                
                login(request, user)
                
                # توجيه المستخدم حسب دوره
                system_role = user.get_system_role()
                if system_role == 'SYSTEM_ADMIN':
                    return redirect('home:admin_dashboard')
                elif system_role == 'SCHOOL_MANAGER':
                    return redirect('home:manager_dashboard')
                elif system_role == 'ACCOUNTANT':
                    return redirect('home:accountant_dashboard')
                elif system_role == 'STUDENT_AFFAIRS':
                    return redirect('home:student_affairs_dashboard')
                elif system_role == 'BOOKS_INVENTORY':
                    return redirect('home:books_inventory_dashboard')
                elif system_role == 'UNIFORMS_INVENTORY':
                    return redirect('home:uniforms_inventory_dashboard')
                else:
                    return redirect('home:default_dashboard')
            else:
                messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة.')
    else:
        form = AuthenticationForm()
    
    context = {
        'form': form,
    }
    return render(request, 'account/login.html', context)

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'تم تغيير كلمة المرور بنجاح!')
            return redirect('account:password_change_done')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'account/change_password.html', context)

class PasswordChangeView(PasswordChangeView):
    template_name = 'account/change_password.html'
    success_url = 'account:password_change_done'

class PasswordChangeDoneView(PasswordChangeDoneView):
    template_name = 'account/change_password_done.html'

@login_required
def view_profile(request):
    user = request.user
    context = {
        'user': user,
        'user_role': user.get_role_display_name(),
    }
    return render(request, 'account/profile.html', context)

# دالة تسجيل خروج مخصصة
@login_required
def custom_logout(request):
    auth_logout(request)
    messages.success(request, 'تم تسجيل الخروج بنجاح')
    return redirect('account:login')
