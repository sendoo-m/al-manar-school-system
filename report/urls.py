from django.urls import path
from . import views

app_name = 'report'

urlpatterns = [
    # الصفحة الرئيسية للتقارير
    path('', views.reports_home, name='reports_home'),
    
    # التقارير الأساسية
    path('daily/', views.daily_report, name='daily_report'),
    path('monthly/', views.monthly_report, name='monthly_report'),
    path('financial/', views.financial_report, name='financial_report'),
    path('student-list/', views.student_list_report, name='student_list_report'),
    path('statistics/', views.statistics_report, name='statistics_report'),
    path('archived/', views.archived_students_report, name='archived_students_report'),
    
    # التصدير
    path('export/csv/', views.export_csv, name='export_csv'),
    
    # APIs
    path('api/grades/<int:education_level_id>/', views.api_get_grades, name='api_get_grades'),
]
