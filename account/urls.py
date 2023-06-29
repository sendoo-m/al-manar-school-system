from django.urls import path
from django.contrib.auth.views import LoginView
from . import views
from django.contrib.auth.views import LogoutView
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.contrib import admin

app_name = 'account'

urlpatterns = [
    # path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('signup/', views.signup, name='signup'),
    # path('login/', LoginView.as_view(template_name='account/login.html'), name='login'),
    path('login/', views.login_view, name='login'),
    # path('logout/', LogoutView.as_view(next_page='account:home'), name='logout'),
    path('change_password/', views.change_password, name='change_password'),
    path('password_change_done/', views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('view_profile/', views.view_profile, name='view_profile'),
    # path('admin/logout/', views.custom_logout, name='admin_logout'),  # Custom logout URL for admin
    # path('logout/', views.custom_logout, name='logout'),  # Custom logout URL for frontend user
    # path('admin_logout/', views.admin_logout, name='admin_logout'),
]
