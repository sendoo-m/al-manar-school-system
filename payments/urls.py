# في payments/urls.py - إضافة المسارات المفقودة

from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # ===================================
    # 🏠 الصفحات الرئيسية
    # ===================================
    path('', views.payments_home, name='payments_home'),
    path('all/', views.all_payments, name='all_payments'),

    # ===================================
    # 💰 عمليات المدفوعات
    # ===================================
    path('pay/<int:pk>/', views.pay_installment, name='pay_installment'),
    path('edit/<int:payment_id>/', views.edit_payment, name='edit_payment'),
    path('receipt/<int:pk>/', views.receipt, name='receipt'),
    path('delete/<int:pk>/', views.delete_installment, name='delete_installment'),
    path('delete-all-payments/<int:student_id>/', views.delete_all_payments, name='delete_all_payments'),

    # ===================================
    # 🔍 البحث والعمليات السريعة
    # ===================================
    path('search/', views.student_search, name='student_search'),
    path('student-search/', views.student_search, name='student_search'),
    path('quick-pay/', views.quick_payment, name='quick_payment'),
    path('quick-payment/', views.quick_payment, name='quick_payment'),
    path('print-receipts/', views.print_receipts, name='print_receipts'),
    path('print-receipt/<int:payment_id>/', views.print_receipt, name='print_receipt'),


    # ===================================
    # 📊 التقارير المالية
    # ===================================
    path('reports/', views.financial_reports, name='financial_reports'),

    # Alias إضافي لنفس صفحة التقارير المالية
    path('reports/financial/', views.financial_reports, name='financial_reports_alias'),

    path('reports/daily/', views.daily_report, name='daily_report'),
    path('reports/monthly/', views.monthly_report, name='monthly_report'),
    path('reports/advanced/', views.advanced_statistics, name='advanced_statistics'),

    path('export/daily-pdf/', views.export_daily_report_pdf, name='export_daily_report_pdf'),
    path('print-daily-report/', views.print_daily_report, name='print_daily_report'),
    path('export/monthly-pdf/', views.export_monthly_report_pdf, name='export_monthly_report_pdf'),
    path('print-monthly-report/', views.print_monthly_report, name='print_monthly_report'),
    # ===================================
    # 🎯 الإدارة المتقدمة
    # ===================================
    path('discounts/', views.manage_discounts, name='manage_discounts'),
    path('overdue/', views.overdue_payments, name='overdue_payments'),
    path('settings/', views.payment_settings, name='payment_settings'),
    
    # ===================================
    # 🔧 المساعدة والأدوات
    # ===================================
    path('help/', views.user_guide, name='user_guide'),
    path('calculator/', views.payment_calculator, name='payment_calculator'),
    path('support/', views.technical_support, name='technical_support'),

    # ===================================
    # 🔌 APIs وAjax
    # ===================================
    path('api/student-search/', views.student_search_ajax, name='student_search_ajax'),
    path('api/record-payment/', views.record_payment_ajax, name='record_payment_ajax'),
    path('api/student-payments/', views.get_student_payments_ajax, name='get_student_payments_ajax'),
    path('api/payment-details/<int:payment_id>/', views.get_payment_details_ajax, name='get_payment_details_ajax'),
    path('api/validate-payment/', views.validate_payment_ajax, name='validate_payment_ajax'),
    path('api/calculate-total/', views.calculate_student_total_ajax, name='calculate_student_total_ajax'),
    # APIs الخصومات
    path('api/approve-discount/<int:discount_id>/', views.approve_discount_ajax, name='approve_discount_ajax'),
    path('api/reject-discount/<int:discount_id>/', views.reject_discount_ajax, name='reject_discount_ajax'),
    path('api/discount-details/<int:discount_id>/', views.get_discount_details_ajax, name='get_discount_details_ajax'),
    
    # APIs للطلاب
    path('api/student-details/<int:student_id>/', views.student_details_api, name='student_details_api'),
    path('api/student-payment-history/<int:student_id>/', views.student_payment_history_api, name='student_payment_history_api'),
    path('students/api/contact-details/<int:student_id>/', views.student_contact_details_api, name='student_contact_details_api'),
    # APIs للطلاب - كلها في payments
        
    path('api/student-contact-details/<int:student_id>/', views.student_contact_details_api, name='student_contact_details_api'),
    path('api/student-search/', views.student_search_ajax, name='student_search_ajax'),

    # ===================================
    # 📤 التصدير
    # ===================================
    path('export/pdf/', views.export_payments_pdf, name='export_payments_pdf'),
    path('export/csv/', views.export_payments, name='export_payments_csv'),
    path('print-report/', views.print_payments_report, name='print_payments_report'),
    path('student/<int:student_id>/request-discount/', views.request_student_discount, name='request_student_discount'),
    
]
