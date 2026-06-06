# treasury_management/urls.py
# نسخة منظمة ومتوافقة مع views.py الحالي

from django.urls import path
from . import views

app_name = 'treasury_management'

urlpatterns = [
    # ===================================
    # 🏠 الصفحات الرئيسية ولوحة التحكم
    # ===================================
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard-api/', views.dashboard_api, name='dashboard_api'),
    path('daily-summary/', views.daily_summary, name='daily_summary'),
    path('access-denied/', views.access_denied, name='access_denied'),

    # ===================================
    # 🔧 الإعداد السريع والتكوين
    # ===================================
    path('quick-setup/', views.quick_setup, name='quick_setup'),
    path('setup-categories/', views.setup_basic_categories, name='setup_basic_categories'),
    path('setup-accounts/', views.setup_basic_accounts, name='setup_basic_accounts'),
    path('setup-expense-categories/', views.setup_expense_categories, name='setup_expense_categories'),

    # ===================================
    # 💰 العمليات المالية
    # ===================================
    path('transactions/', views.transactions_list, name='transactions_list'),
    path('transactions/add/', views.add_transaction, name='add_transaction'),
    path('add-transaction/', views.add_transaction, name='add_transaction_old'),

    # صفحة تفاصيل عادية للعملية المالية
    path('transactions/<int:transaction_id>/', views.transaction_detail, name='transaction_detail'),
    path('transaction-detail-ajax/<int:transaction_id>/', views.transaction_detail_ajax, name='transaction_detail_ajax'),
    
    # اعتماد/إلغاء العمليات
    path('transactions/<int:transaction_id>/approve/', views.approve_transaction, name='approve_transaction'),
    path('transactions/<int:transaction_id>/cancel/', views.cancel_transaction, name='cancel_transaction'),

    # مسارات قديمة للتوافق مع القوالب القديمة
    path('approve-transaction/<int:transaction_id>/', views.approve_transaction, name='approve_transaction_old'),
    path('cancel-transaction/<int:transaction_id>/', views.cancel_transaction, name='cancel_transaction_old'),

    path('bulk-approve-transactions/', views.bulk_approve_transactions, name='bulk_approve_transactions'),
    path('search-transactions/', views.search_transactions, name='search_transactions'),

    # ===================================
    # 🏦 إدارة الخزائن
    # ===================================
    path('treasuries/', views.treasuries_list, name='treasuries_list'),
    path('add-treasury/', views.add_treasury, name='add_treasury'),
    path('edit-treasury/<int:pk>/', views.edit_treasury, name='edit_treasury'),
    path('treasury-detail/<int:pk>/', views.treasury_detail, name='treasury_detail'),
    path('treasury-statement/<int:treasury_id>/', views.treasury_statement, name='treasury_statement'),

    # ===================================
    # 📊 الحسابات المالية
    # ===================================
    path('accounts/', views.accounts_list, name='accounts_list'),
    path('add-account/', views.add_account, name='add_account'),
    path('edit-account/<int:pk>/', views.edit_account, name='edit_account'),
    path('account-detail/<int:account_id>/', views.account_detail_ajax, name='account_detail_ajax'),
    path('account-statement/<int:account_id>/', views.account_statement, name='account_statement'),

    # ===================================
    # 🗂️ تصنيفات الحسابات
    # ===================================
    path('account-categories/', views.account_categories_list, name='account_categories_list'),
    path('add-account-category/', views.add_account_category, name='add_account_category'),
    path('edit-account-category/<int:pk>/', views.edit_account_category, name='edit_account_category'),
    path('delete-account-category/<int:pk>/', views.delete_account_category, name='delete_account_category'),

    # صفحة تفاصيل عادية
    path('account-categories/<int:pk>/', views.account_category_detail, name='account_category_detail'),
    path('account-category-detail/<int:category_id>/', views.account_category_detail_ajax, name='account_category_detail_ajax'),
    # AJAX منفصل حتى لا يتعارض مع صفحة التفاصيل
    path('ajax/account-category/<int:category_id>/', views.account_category_detail_ajax, name='account_category_detail_ajax'),

    # ===================================
    # 💸 المصروفات اليومية وتصنيفاتها
    # ===================================
    path('expenses/', views.expenses_list, name='expenses_list'),
    path('expenses/add/', views.add_expense, name='add_expense'),
    path('add-expense/', views.add_expense, name='add_expense_old'),
    path('expenses/<int:pk>/approve/', views.approve_expense, name='approve_expense'),

    path('expenses/<int:pk>/', views.expense_detail, name='expense_detail'),
    path('expense-detail-ajax/<int:pk>/', views.expense_detail_ajax, name='expense_detail_ajax'),

    # مسار قديم للتوافق مع القوالب القديمة
    path('approve-expense/<int:pk>/', views.approve_expense, name='approve_expense_old'),

    path('expense-categories/', views.expense_categories_list, name='expense_categories_list'),
    path('add-expense-category/', views.add_expense_category, name='add_expense_category'),
    path('edit-expense-category/<int:pk>/', views.edit_expense_category, name='edit_expense_category'),
    path('delete-expense-category/<int:pk>/', views.delete_expense_category, name='delete_expense_category'),
    path(
    'expense-category-detail/<int:category_id>/',
    views.expense_category_detail_ajax,
    name='expense_category_detail_ajax'
),
    path('expense-detail/<int:expense_id>/', views.expense_detail_ajax, name='expense_detail_ajax'),
    path('expense-category-detail/<int:category_id>/', views.expense_category_detail_ajax, name='expense_category_detail_ajax'),
    # ===================================
    # 📈 التقارير والملخصات
    # ===================================
    path('reports/', views.reports, name='reports'),
    path('create-snapshot/', views.create_treasury_snapshot, name='create_snapshot'),

    # ===================================
    # 👥 الإدارة المتقدمة
    # ===================================
    path('manage-users/', views.manage_users, name='manage_users'),
    path('system-settings/', views.system_settings, name='system_settings'),
    path('backup-restore/', views.backup_restore, name='backup_restore'),

    # ===================================
    # 🔌 APIs والخدمات
    # ===================================
    path('api/treasury-balance/<int:treasury_id>/', views.treasury_balance_api, name='treasury_balance_api'),
    path('api/get-treasury-balance/<int:treasury_id>/', views.get_treasury_balance, name='get_treasury_balance'),
    path('api/dashboard-widgets/', views.dashboard_widgets_data, name='dashboard_widgets_data'),
    path('api/accounts-by-type/', views.ajax_get_accounts_by_type, name='ajax_get_accounts_by_type'),
    path('api/categories-by-type/', views.get_categories_by_type, name='get_categories_by_type'),
    path('api/notifications/', views.get_notifications, name='get_notifications'),

    # ===================================
    # 🚀 الميزات المستقبلية
    # ===================================
    path('coming-soon/<str:feature_name>/', views.coming_soon, name='coming_soon'),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('advanced-reports/', views.financial_reports_advanced, name='financial_reports_advanced'),
    path('budget-planning/', views.budget_planning, name='budget_planning'),
    path('backup-restore/', views.backup_restore, name='backup_restore'),
    path('backup-restore/download/<str:filename>/', views.download_backup, name='download_backup'),
    path('daily-closing/', views.daily_closing, name='daily_closing'),
    path('daily-closing/<int:pk>/delete/', views.delete_daily_closing, name='delete_daily_closing'),
]
