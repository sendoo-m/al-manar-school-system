from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    AccountCategory, Account, Treasury, Transaction, 
    ExpenseCategory, DailyExpense, TreasurySnapshot
)

@admin.register(AccountCategory)
class AccountCategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category_type', 'parent', 'is_active')
    list_filter = ('category_type', 'is_active')
    search_fields = ('name', 'code')
    ordering = ('code',)

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'current_balance', 'is_active')
    list_filter = ('category__category_type', 'is_active')
    search_fields = ('name', 'code')
    ordering = ('code',)
    readonly_fields = ('current_balance',)

@admin.register(Treasury)
class TreasuryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'current_balance', 'responsible_person', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    
    def current_balance(self, obj):
        return format_html('<strong>{:.2f}</strong>', obj.current_balance)
    current_balance.short_description = 'الرصيد الحالي'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_number', 'transaction_type', 'treasury', 'amount', 'is_approved', 'transaction_date')
    list_filter = ('transaction_type', 'is_approved', 'is_cancelled', 'treasury', 'transaction_date')
    search_fields = ('transaction_number', 'description', 'reference_number')
    readonly_fields = ('transaction_number', 'created_at', 'updated_at')
    ordering = ('-transaction_date',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('treasury', 'account', 'created_by')

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account', 'monthly_budget', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('code',)

@admin.register(DailyExpense)
class DailyExpenseAdmin(admin.ModelAdmin):
    list_display = ('expense_number', 'category', 'expense_type', 'amount', 'vendor_name', 'is_approved', 'expense_date')
    list_filter = ('expense_type', 'is_approved', 'category', 'expense_date')
    search_fields = ('expense_number', 'description', 'vendor_name', 'invoice_number')
    readonly_fields = ('expense_number', 'created_at')
    ordering = ('-expense_date',)

@admin.register(TreasurySnapshot)
class TreasurySnapshotAdmin(admin.ModelAdmin):
    list_display = ('treasury', 'snapshot_date', 'opening_balance', 'closing_balance', 'total_income', 'total_expenses')
    list_filter = ('treasury', 'snapshot_date')
    ordering = ('-snapshot_date',)
    readonly_fields = ('created_at',)
