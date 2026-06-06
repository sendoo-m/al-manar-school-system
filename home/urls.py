# home/urls.py
from django.urls import path

from . import views

app_name = 'home'

urlpatterns = [
    # الصفحة الرئيسية
    path('', views.home, name='home'),

    # Authentication URLs
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('home-logout/', views.logout_view, name='logout'),

    # لوحات التحكم المختلفة
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manager-dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('accountant-dashboard/', views.accountant_dashboard, name='accountant_dashboard'),
    path('student-affairs-dashboard/', views.student_affairs_dashboard, name='student_affairs_dashboard'),
    path('books-inventory-dashboard/', views.books_inventory_dashboard, name='books_inventory_dashboard'),
    path('uniforms-inventory-dashboard/', views.uniforms_inventory_dashboard, name='uniforms_inventory_dashboard'),
    path('default-dashboard/', views.default_dashboard, name='default_dashboard'),

    # رفض الوصول
    path('access-denied/', views.access_denied, name='access_denied'),

    # إدارة المستخدمين
    path('users/', views.users_list, name='users_list'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/details/', views.user_details, name='user_details'),

    # إدارة موظفي المخازن والخزينة
    path('inventory-staff/', views.inventory_staff_list, name='inventory_staff_list'),
    path('inventory-staff/<int:user_id>/manage/', views.manage_inventory_staff, name='manage_inventory_staff'),
]

# from django.urls import path
# from . import views

# app_name = 'home'

# urlpatterns = [
#     # صفحة تسجيل الدخول
#     path('', views.home, name='home'),
#     # ===================================
#     # 🔐 Authentication URLs
#     # ===================================
#     path('login/', views.CustomLoginView.as_view(), name='login'),
#     path('home-logout/', views.logout_view, name='logout'),  # ✅ المسار الموحد
      

#     # لوحات التحكم المختلفة
#     path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
#     path('manager-dashboard/', views.manager_dashboard, name='manager_dashboard'),
#     path('accountant-dashboard/', views.accountant_dashboard, name='accountant_dashboard'),
#     path('student-affairs-dashboard/', views.student_affairs_dashboard, name='student_affairs_dashboard'),
#     path('books-inventory-dashboard/', views.books_inventory_dashboard, name='books_inventory_dashboard'),
#     path('uniforms-inventory-dashboard/', views.uniforms_inventory_dashboard, name='uniforms_inventory_dashboard'),
#     path('default-dashboard/', views.default_dashboard, name='default_dashboard'),
    
#     path('access-denied/', views.access_denied, name='access_denied'),

    
#     # إدارة المستخدمين - مدير النظام فقط
#     path('users/', views.users_list, name='users_list'),
#     path('users/add/', views.add_user, name='add_user'),
#     path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
#     path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
#     path('users/<int:user_id>/details/', views.user_details, name='user_details'),
    
#     # إدارة موظفي المخازن
#     path('inventory-staff/', views.inventory_staff_list, name='inventory_staff_list'),
#     path('inventory-staff/<int:user_id>/manage/', views.manage_inventory_staff, name='manage_inventory_staff'),
# ]
