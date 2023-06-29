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

# Create your views here.



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
            messages.success(request, 'Sign up successful!')
            return redirect('account:login')
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form,
    }
    return render(request, 'account/signup.html', context)


# =================== signup ===================
# User = get_user_model()

# def signup(request):
#     if request.method == 'POST':
#         form = UserCreationForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, 'Sign up successful!')
#             return redirect('account:login')
#     else:
#         form = UserCreationForm()
    
#     context = {
#         'form': form,
#     }
#     return render(request, 'account/signup.html', context)
# # =================== signup ===================

# =================== Login  ===================

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if user.department == 'student_affairs':
                    return redirect('students:student_affairs_home')
                elif user.department == 'administration':
                    return redirect('students:administration_home')
                elif user.department == 'accounts':
                    return redirect('students:accounts_home')
                else:
                    return redirect('students:home')  # Replace 'home' with the name of your default homepage URL
    else:
        form = AuthenticationForm()
    
    context = {
        'form': form,
    }
    return render(request, 'account/login.html', context)

# Existing views...

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Update the session to maintain the user's authentication
            messages.success(request, 'Your password has been changed successfully!')
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

# Existing views...

@login_required
def view_profile(request):
    user = request.user
    context = {
        'user': user
    }
    return render(request, 'account/profile.html', context)


# =================== Login  ===================

# =================== logout  ===================

# from django.contrib.auth import logout
# from django.shortcuts import redirect, render

# def custom_logout(request):
#     logout(request)  # Log out the user
#     # if request.user.is_staff:  # Check if the user is an admin
#     #     return redirect('account:admin_logout')  # Redirect to the admin logout page
#     # else:
#     return redirect('account:logout')  # Redirect to the frontend logout page


# def admin_logout(request):
#     # Perform any necessary logout logic for admin
#     return redirect('admin:index')  # Redirect to the admin page after logout



# =================== logout  ===================

# def students_view(request):
#     user = request.user
#     is_administration = user.groups.filter(name='Administration').exists()
#     # Pass the `is_administration` variable to the template context
#     context = {
#         'is_administration': is_administration
#     }
#     return render(request, 'students/home.html', context)
