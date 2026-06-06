# students/urls.py - مع تعليقات الصلاحيات
from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    # ===================================
    # 🏠 الصفحات الرئيسية (جميع المستخدمين)
    # ===================================
    path('', views.home, name='home'),  # أساسي
    path('student_affairs_home/', views.student_affairs_home, name='student_affairs_home'),  # أساسي
    
    # ===================================
    # 👥 إدارة الطلاب
    # ===================================
    path('student_list/', views.student_list, name='student_list'),  # عرض - أساسي
    path('add_student/', views.add_student, name='add_student'),  # إضافة - موظف شؤون الطلاب
    path('student_detail/<int:pk>/', views.student_detail, name='student_detail'),  # عرض - أساسي
    path('edit_student/<int:pk>/', views.edit_student, name='edit_student'),  # تعديل - مدير فقط
    path('students/confirm_delete_student/<int:student_id>/', views.confirm_delete_student, name='confirm_delete_student'),  # حذف - مدير عام فقط
    
    # ===================================
    # 🔍 البحث (جميع المستخدمين)
    # ===================================
    path('search_student/', views.search_student, name='search_student'),  # بحث - أساسي
    path('ajax/search/', views.ajax_student_search, name='ajax_search'),  # AJAX - أساسي
    
    # ===================================
    # 📊 التقارير (مدير + إدارة فقط)
    # ===================================
    path('report/', views.report, name='report'),  # تقارير أساسية
    path('all_reports/', views.all_reports, name='all_reports'),  # تقارير متقدمة
    path('daily_report/', views.daily_report, name='daily_report'),  # تقرير يومي
    path('student_dashboard/', views.student_dashboard, name='student_dashboard'),  # لوحة إحصائيات
    
    # ===================================
    # 🔧 الأدوات الإدارية (مدير عام فقط)
    # ===================================
    path('export_students/', views.export_students, name='export_students'),  # تصدير - حساس
    path('upgrade_students/', views.upgrade_students, name='upgrade_students'),  # ترقية - حساس
    
    # ===================================
    # 🔌 APIs (جميع المستخدمين)
    # ===================================
    path('api/grades/<int:level_id>/', views.get_grades_by_level, name='get_grades_by_level'),  # API - أساسي
    path('get-grades-by-level/<int:level_id>/', views.get_grades_by_level, name='get_grades_by_level'),

    
    # الأدوات المتقدمة
    path('export-advanced/', views.export_students_advanced, name='export_students_advanced'),
    path('import-advanced/', views.import_students_advanced, name='import_students_advanced'),
    path('upgrade-wizard/', views.upgrade_students_wizard, name='upgrade_students_wizard'),
    path('user-guide/', views.user_guide, name='user_guide'),
    path('import-template/', views.download_import_template, name='download_import_template'),
    path('sync-financial-data/', views.sync_students_financial_data, name='sync_students_financial_data'),
]
