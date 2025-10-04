from django.urls import path
from . import views


app_name = 'school_settings'


urlpatterns = [
    # ============================================================================
    # الصفحة الرئيسية والشاملة
    # ============================================================================
    path('', views.comprehensive_settings, name='comprehensive_settings'),
    
    # ============================================================================
    # إدارة معلومات المدرسة
    # ============================================================================
    path('update-school-settings/', views.update_school_settings, name='update_school_settings'),
    path('school-settings-form/', views.school_settings_form, name='school_settings_form'),

    # ============================================================================
    # إدارة الأعوام الدراسية
    # ============================================================================
    path('academic-years/', views.academic_years_list, name='academic_years_list'),
    path('create-academic-year/', views.create_academic_year, name='create_academic_year'),
    path('edit-academic-year/<int:pk>/', views.edit_academic_year, name='edit_academic_year'),
    path('delete-academic-year/<int:pk>/', views.delete_academic_year, name='delete_academic_year'),
    path('set-current-year/<int:year_id>/', views.set_current_academic_year, name='set_current_academic_year'),
    path('academic-years/<int:year_id>/details/', views.academic_year_details, name='academic_year_details'),

    # ============================================================================
    # إدارة المراحل التعليمية
    # ============================================================================
    path('education-levels/', views.education_levels_list, name='education_levels_list'),
    path('create-education-level/', views.create_education_level, name='create_education_level'),
    path('edit-education-level/<int:pk>/', views.edit_education_level, name='edit_education_level'),
    path('delete-education-level/<int:pk>/', views.delete_education_level, name='delete_education_level'),
    
    # ============================================================================
    # إدارة الصفوف الدراسية
    # ============================================================================
    path('grade-levels/', views.grade_levels_list, name='grade_levels_list'),
    path('create-grade-level/', views.create_grade_level, name='create_grade_level'),
    path('edit-grade-level/<int:pk>/', views.edit_grade_level, name='edit_grade_level'),
    path('delete-grade-level/<int:pk>/', views.delete_grade_level, name='delete_grade_level'),
    
    # ============================================================================
    # إدارة المصروفات المدرسية
    # ============================================================================
    path('school-fees/', views.school_fees_list, name='school_fees_list'),
    path('create-school-fee/', views.create_school_fee, name='create_school_fee'),
    path('edit-school-fee/<int:pk>/', views.edit_school_fee, name='edit_school_fee'),
    path('delete-school-fee/<int:pk>/', views.delete_school_fee, name='delete_school_fee'),
    
    # ============================================================================
    # إدارة الخصومات
    # ============================================================================
    path('discounts/', views.discounts_list, name='discounts_list'),
    path('create-discount/', views.create_discount, name='create_discount'),
    path('edit-discount/<int:pk>/', views.edit_discount, name='edit_discount'),
    path('delete-discount/<int:pk>/', views.delete_discount, name='delete_discount'),
    path('apply-discount/<int:student_id>/<int:discount_id>/', views.apply_discount_to_student, name='apply_discount_to_student'),
    path('calculate-discount/<int:student_id>/<int:discount_id>/', views.calculate_student_discount, name='calculate_student_discount'),
    
    # ============================================================================
    # الإعدادات العامة للنظام
    # ============================================================================
    path('system/', views.system_settings, name='system_settings'),
    path('update-system-settings/', views.update_system_settings, name='update_system_settings'),
    path('notifications/', views.notification_settings, name='notification_settings'),
    path('reports/', views.report_settings, name='report_settings'),
    path('security/', views.security_settings, name='security_settings'),
    
    # ============================================================================
    # إدارة الأدوار والمستخدمين
    # ============================================================================
    path('roles/', views.roles_list, name='roles_list'),
    path('assign-role/<int:user_id>/', views.assign_role, name='assign_role'),
    path('remove-role/<int:user_id>/', views.remove_role, name='remove_role'),
    # ... URLs أخرى
    path('roles/', views.roles_list, name='roles_list'),
    path('roles/add/', views.add_role, name='add_role'),
    path('roles/<int:role_id>/edit/', views.edit_role, name='edit_role'),
    path('roles/<int:role_id>/delete/', views.delete_role, name='delete_role'),

    # ============================================================================
    # سجل الإعدادات والتغييرات
    # ============================================================================
    path('logs/', views.settings_logs, name='settings_logs'),
    path('logs/export/', views.export_settings_logs, name='export_settings_logs'),
    path('logs/clear-old/', views.clear_old_logs, name='clear_old_logs'),
    path('export-logs/', views.export_logs, name='export_logs'),
    path('logs/<int:log_id>/details/', views.log_details, name='log_details'),
    path('logs/', views.settings_logs, name='settings_logs'),
    path('logs/<int:log_id>/details/', views.log_details, name='log_details'),
    
    # ============================================================================
    # APIs ومعالجات Ajax
    # ============================================================================
    path('dashboard-api/', views.settings_dashboard_api, name='dashboard_api'),
    path('update-setting/', views.update_setting_ajax, name='update_setting_ajax'),
    path('delete/<str:item_type>/<int:item_id>/', views.delete_item, name='delete_item'),
    path('test-email/', views.test_email_settings, name='test_email_settings'),
    
    # ============================================================================
    # APIs للأعوام الدراسية
    # ============================================================================
    path('api/academic-year-details/<int:year_id>/', views.academic_year_details_api, name='academic_year_details_api'),
    path('api/set-current-year/<int:year_id>/', views.set_current_year_api, name='set_current_year_api'),
]
