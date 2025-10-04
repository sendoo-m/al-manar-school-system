from django.urls import path
from . import views

app_name = 'books_inventory'

urlpatterns = [
    # الصفحة الرئيسية
    path('', views.inventory_home, name='inventory_home'),
    
    # ===== إدارة المواد الدراسية =====
    path('subjects/', views.subjects_list, name='subjects_list'),
    path('subjects/add/', views.add_subject, name='add_subject'),
    path('subjects/<int:pk>/', views.subject_detail, name='subject_detail'),
    path('subjects/<int:pk>/edit/', views.edit_subject, name='edit_subject'),
    path('subjects/<int:pk>/delete/', views.delete_subject, name='delete_subject'),
    
    # ===== إدارة الكتب =====
    path('books/', views.books_list, name='books_list'),
    path('books/add/', views.add_book, name='add_book'),
    path('books/<int:pk>/', views.book_detail, name='book_detail'),
    path('books/<int:pk>/edit/', views.edit_book, name='edit_book'),
    path('books/<int:pk>/delete/', views.delete_book, name='delete_book'),
    
    # ===== إدارة الكراسات =====
    path('notebooks/', views.notebooks_list, name='notebooks_list'),
    path('notebooks/add/', views.add_notebook, name='add_notebook'),
    path('notebooks/<int:pk>/', views.notebook_detail, name='notebook_detail'),
    path('notebooks/<int:pk>/edit/', views.edit_notebook, name='edit_notebook'),
    path('notebooks/<int:pk>/delete/', views.delete_notebook, name='delete_notebook'),
    
    # ===== إدارة الأدوات المدرسية =====
    path('supplies/', views.supplies_list, name='supplies_list'),
    path('supplies/add/', views.add_supply, name='add_supply'),
    path('supplies/<int:pk>/', views.supply_detail, name='supply_detail'),
    path('supplies/<int:pk>/edit/', views.edit_supply, name='edit_supply'),
    path('supplies/<int:pk>/delete/', views.delete_supply, name='delete_supply'),
    
    # ===== إدارة الموردين =====
    path('suppliers/', views.suppliers_list, name='suppliers_list'),
    path('suppliers/add/', views.add_supplier, name='add_supplier'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', views.edit_supplier, name='edit_supplier'),
    
    # ===== إدارة إيصالات الاستلام =====
    path('receipts/', views.receipts_list, name='receipts_list'),
    path('receipts/add/', views.add_receipt, name='add_receipt'),
    path('receipts/<int:pk>/', views.receipt_detail, name='receipt_detail'),
    path('receipts/<int:pk>/edit/', views.edit_receipt, name='edit_receipt'),
    
    # ===== إدارة توزيعات الطلاب =====
    # القائمة والإنشاء
    path('distributions/', views.student_distributions_list, name='distributions_list'),
    path('distributions/create/', views.create_student_distribution, name='create_distribution'),
    
    # التفاصيل والتعديل
    path('distributions/<int:pk>/', views.student_distribution_detail, name='student_distribution_detail'),
    path('distributions/<int:pk>/edit/', views.edit_distribution, name='edit_distribution'),
    path('distributions/<int:pk>/verify/', views.verify_payment, name='verify_payment'),
    path('api/get-items-for-grade/', views.get_items_for_grade, name='get_items_for_grade'),

    # إضافة عناصر للتوزيع
    path('distributions/<int:pk>/add-book/', views.add_book_to_distribution, name='add_book_to_distribution'),
    path('distributions/<int:pk>/add-notebook/', views.add_notebook_to_distribution, name='add_notebook_to_distribution'),
    path('distributions/<int:pk>/add-supply/', views.add_supply_to_distribution, name='add_supply_to_distribution'),
    
    # حذف عناصر من التوزيع
    path('distributions/book-item/<int:item_id>/delete/', views.delete_book_item, name='delete_book_item'),
    path('distributions/notebook-item/<int:item_id>/delete/', views.delete_notebook_item, name='delete_notebook_item'),
    path('distributions/supply-item/<int:item_id>/delete/', views.delete_supply_item, name='delete_supply_item'),
    path('distributions/<int:pk>/details/', views.student_distribution_detail, name='distribution_detail'),  # إضافة alias
    path('distributions/<int:pk>/print/', views.print_distribution, name='print_distribution'),  # إضافة جديدة
        
    # ===== عرض بيانات الطلاب (للقراءة فقط) =====
    path('students/search/', views.student_search_view, name='student_search_view'),
    path('students/payments/', views.student_payments_view, name='student_payments_view'),
    path('students/<int:pk>/', views.student_detail_view, name='student_detail_view'),
    
    # ===== النواقص والتقارير =====
    path('shortages/', views.shortages_list, name='shortages_list'),
    path('reports/', views.inventory_reports, name='inventory_reports'),
    path('export/<str:export_type>/', views.export_inventory_report, name='export_report'),
    
    # ===== APIs =====
    path('api/student-search/', views.student_search_api, name='student_search_api'),
    path('api/student-search-distribution/', views.student_search_for_distribution, name='student_search_for_distribution'),
    path('api/report-shortage/', views.report_shortage, name='report_shortage_api'),
]
