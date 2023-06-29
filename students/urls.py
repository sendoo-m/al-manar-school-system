from django.urls import path
from . import views

app_name = 'students'
urlpatterns = [
    path('accounts_home/', views.accounts_home, name='accounts_home'),
    path('student_affairs_home/', views.student_affairs_home, name='student_affairs_home'),
    path('administration_home/', views.administration_home, name='administration_home'),
    path('', views.home, name='home'),
    path('students/', views.student_list, name='student_list'),
    path('student_detail/<int:pk>/', views.student_detail, name='student_detail'),
    path('delete_installment/<int:pk>/', views.delete_installment, name='delete_installment'),
    path('edit_student/<int:pk>/', views.edit_student, name='edit_student'),
    # path('register/', views.register, name='register'),
    path('add_student/', views.add_student, name='add_student'),
    path('delete_student/<int:student_id>/', views.delete_student, name='delete_student'),
    path('students/confirm_delete_student/<int:student_id>/', views.confirm_delete_student, name='confirm_delete_student'),
    path('add_expense/<int:pk>/', views.add_expense, name='add_expense'),
    path('pay_installment/<int:pk>/', views.pay_installment, name='pay_installment'),
    path('receipt/<int:pk>/', views.receipt, name='receipt'),
    path('report/', views.report, name='report'),
    path('daily_report/', views.generate_daily_report, name='daily_report'),
    path('all_reports/', views.all_reports, name='all_reports'),
    path('classroom/<int:classroom_id>/', views.classroom_details, name='classroom_details'),
    path('search/', views.search_student, name='search_student'),
    path('generate-student-report/', views.generate_student_report, name='generate_student_report'),
    path('generate-installment-report/', views.generate_installment_report, name='generate_installment_report'),
    path('g-reports/', views.g_reports, name='g_reports'),
    path('upgrade-students/', views.upgrade_students_view, name='upgrade_students'),
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('export/', views.export_students, name='export_students'),
]
