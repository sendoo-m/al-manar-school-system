from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    # صفحة تسجيل الدخول
    path('', views.CustomLoginView.as_view(), name='login'),
    path('login/', views.CustomLoginView.as_view(), name='login_page'),
    
    # لوحات التحكم المختلفة
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manager-dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('accountant-dashboard/', views.accountant_dashboard, name='accountant_dashboard'),
    path('student-affairs-dashboard/', views.student_affairs_dashboard, name='student_affairs_dashboard'),
    path('books-inventory-dashboard/', views.books_inventory_dashboard, name='books_inventory_dashboard'),
    path('uniforms-inventory-dashboard/', views.uniforms_inventory_dashboard, name='uniforms_inventory_dashboard'),
    path('default-dashboard/', views.default_dashboard, name='default_dashboard'),
    
    path('access-denied/', views.access_denied, name='access_denied'),

    # تسجيل الخروج
    path('logout/', views.logout_view, name='logout'),
]
