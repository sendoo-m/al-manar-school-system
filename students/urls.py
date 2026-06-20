# students/urls.py
from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    # ===================================
    # 🏠 الصفحات الرئيسية
    # ===================================
    path('', views.home, name='home'),
    path('student_affairs_home/', views.student_affairs_home, name='student_affairs_home'),

    # ===================================
    # 👥 إدارة الطلاب
    # ===================================
    path('student_list/', views.student_list, name='student_list'),
    path('add_student/', views.add_student, name='add_student'),
    path('student_detail/<int:pk>/', views.student_detail, name='student_detail'),
    path('edit_student/<int:pk>/', views.edit_student, name='edit_student'),

    # أرشفة الطالب بدل الحذف النهائي
    path(
        'confirm_delete_student/<int:student_id>/',
        views.confirm_delete_student,
        name='confirm_delete_student'
    ),

    # رابط قديم احتياطي لو في قوالب قديمة بتستخدمه
    path(
        'students/confirm_delete_student/<int:student_id>/',
        views.confirm_delete_student,
        name='confirm_delete_student_old'
    ),

    # ===================================
    # 🔍 البحث
    # ===================================
    path('search_student/', views.search_student, name='search_student'),
    path('ajax/search/', views.ajax_student_search, name='ajax_search'),

    # ===================================
    # 📊 التقارير
    # ===================================
    path('report/', views.report, name='report'),
    path('all_reports/', views.all_reports, name='all_reports'),
    path('daily_report/', views.daily_report, name='daily_report'),
    path('student_dashboard/', views.student_dashboard, name='student_dashboard'),

    # ===================================
    # 📤 التصدير والاستيراد
    # ===================================
    path('export_students/', views.export_students, name='export_students'),
    path('export-advanced/', views.export_students_advanced, name='export_students_advanced'),

    path('import-advanced/', views.import_students_advanced, name='import_students_advanced'),
    path('import-template/', views.download_import_template, name='download_import_template'),

    # روابط بديلة أوضح اختيارية
    path('download-import-template/', views.download_import_template, name='download_import_template_alt'),
    path('students-import-template/', views.download_import_template, name='students_import_template'),

    # ===================================
    # ⬆️ ترقية الطلاب
    # ===================================
    path('upgrade_students/', views.upgrade_students, name='upgrade_students'),
    path('upgrade-wizard/', views.upgrade_students_wizard, name='upgrade_students_wizard'),

    # ===================================
    # 🔧 أدوات إدارية
    # ===================================
    path('sync-financial-data/', views.sync_students_financial_data, name='sync_students_financial_data'),
    path('user-guide/', views.user_guide, name='user_guide'),

    # ===================================
    # 🔌 APIs
    # ===================================
    path('api/grades/<int:level_id>/', views.get_grades_by_level, name='get_grades_by_level'),
    path('get-grades-by-level/<int:level_id>/', views.get_grades_by_level, name='get_grades_by_level_old'),
    path('student/<int:pk>/enrollment-statement-word/', views.student_enrollment_statement_word, name='student_enrollment_statement_word'),
]


def get_urls(self):
    urls = super().get_urls()
    custom_urls = [
        path('export/', self.admin_site.admin_view(self.export_students), name='students_student_export'),
        path('import/', self.admin_site.admin_view(self.import_students_view), name='students_student_import'),
        path('import/process/', self.admin_site.admin_view(self.process_import), name='students_student_import_process'),
        path('export/template/', self.admin_site.admin_view(self.download_template), name='students_student_export_template'),
        path('export/reference/', self.admin_site.admin_view(self.download_reference_data), name='students_student_export_reference'),
    ]
    return custom_urls + urls