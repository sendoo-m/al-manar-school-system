# treasury_management/admin.py
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.utils import timezone

from .models import (
    AccountCategory,
    Account,
    Treasury,
    Transaction,
    ExpenseCategory,
    DailyExpense,
    TreasurySnapshot,
    DailyClosing,
    TreasuryReconciliation,
    TreasurySettings,
)


# ============================================================
# Helpers
# ============================================================

def money(value):
    """تنسيق آمن للمبالغ داخل الأدمن"""
    try:
        return f'{float(value or 0):,.2f}'
    except Exception:
        return '0.00'


# ============================================================
# تصنيفات الحسابات
# ============================================================

@admin.register(AccountCategory)
class AccountCategoryAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'category_type',
        'parent',
        'accounts_count',
        'is_active',
    )
    list_filter = ('category_type', 'is_active')
    search_fields = ('name', 'code', 'description')
    ordering = ('code',)
    list_editable = ('is_active',)

    def accounts_count(self, obj):
        return obj.accounts.count()
    accounts_count.short_description = 'عدد الحسابات'


# ============================================================
# الحسابات
# ============================================================

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'category',
        'category_type_display',
        'opening_balance',
        'formatted_current_balance',
        'is_active',
    )
    list_filter = ('category__category_type', 'category', 'is_active')
    search_fields = ('name', 'code', 'description', 'category__name')
    ordering = ('code',)
    readonly_fields = ('current_balance', 'created_at', 'updated_at')
    list_editable = ('is_active',)

    fieldsets = (
        ('بيانات الحساب', {
            'fields': (
                'category',
                'name',
                'code',
                'description',
                'is_active',
            )
        }),
        ('الأرصدة', {
            'fields': (
                'opening_balance',
                'current_balance',
            )
        }),
        ('معلومات النظام', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )

    def category_type_display(self, obj):
        return obj.category.get_category_type_display() if obj.category_id else '-'
    category_type_display.short_description = 'نوع الحساب'

    def formatted_current_balance(self, obj):
        return format_html('<strong>{}</strong>', money(obj.current_balance))
    formatted_current_balance.short_description = 'الرصيد الحالي'


# ============================================================
# الخزائن
# ============================================================

@admin.register(Treasury)
class TreasuryAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'account',
        'formatted_current_balance',
        'responsible_person',
        'location',
        'min_limit',
        'max_limit',
        'is_active',
    )
    list_filter = ('is_active', 'responsible_person')
    search_fields = ('name', 'code', 'location', 'account__name', 'account__code')
    readonly_fields = ('current_balance_display', 'created_at')
    list_editable = ('is_active',)

    fieldsets = (
        ('بيانات الخزنة', {
            'fields': (
                'name',
                'code',
                'account',
                'responsible_person',
                'location',
                'is_active',
            )
        }),
        ('الحدود والرصيد', {
            'fields': (
                'current_balance_display',
                'min_limit',
                'max_limit',
            )
        }),
        ('معلومات النظام', {
            'fields': (
                'created_at',
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('account', 'responsible_person')

    def formatted_current_balance(self, obj):
        return format_html('<strong>{}</strong>', money(obj.current_balance))
    formatted_current_balance.short_description = 'الرصيد الحالي'

    def current_balance_display(self, obj):
        return format_html('<strong>{}</strong>', money(obj.current_balance))
    current_balance_display.short_description = 'الرصيد الحالي'


# ============================================================
# العمليات المالية
# ============================================================

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_number',
        'transaction_type',
        'source_type',
        'treasury',
        'to_treasury',
        'account',
        'formatted_amount',
        'status_display',
        'payment_method',
        'transaction_date',
        'created_by',
    )
    list_filter = (
        'transaction_type',
        'source_type',
        'is_approved',
        'is_cancelled',
        'treasury',
        'to_treasury',
        'payment_method',
        'transaction_date',
    )
    search_fields = (
        'transaction_number',
        'description',
        'reference_number',
        'notes',
        'treasury__name',
        'to_treasury__name',
        'account__name',
        'created_by__username',
    )
    readonly_fields = (
        'transaction_number',
        'created_at',
        'updated_at',
        'approved_by',
        'approved_at',
        'cancelled_by',
        'cancelled_at',
        'is_approved',
        'is_cancelled',
    )
    ordering = ('-transaction_date', '-created_at')
    date_hierarchy = 'transaction_date'
    actions = ('approve_selected_transactions', 'cancel_selected_transactions')

    fieldsets = (
        ('بيانات العملية', {
            'fields': (
                'transaction_number',
                'transaction_type',
                'source_type',
                'treasury',
                'to_treasury',
                'account',
                'amount',
                'description',
                'notes',
            )
        }),
        ('الدفع والمراجع', {
            'fields': (
                'payment_method',
                'reference_number',
                'related_model',
                'related_id',
            )
        }),
        ('التاريخ والمستخدمين', {
            'fields': (
                'transaction_date',
                'academic_year',
                'created_by',
                'approved_by',
                'approved_at',
                'cancelled_by',
                'cancelled_at',
            )
        }),
        ('الحالة', {
            'fields': (
                'is_approved',
                'is_cancelled',
                'cancellation_reason',
            )
        }),
        ('معلومات النظام', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'treasury',
            'to_treasury',
            'account',
            'account__category',
            'created_by',
            'approved_by',
            'cancelled_by',
            'academic_year',
        )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def formatted_amount(self, obj):
        css = 'success' if obj.transaction_type == 'INCOME' else 'danger' if obj.transaction_type == 'EXPENSE' else 'info'
        sign = '+' if obj.transaction_type == 'INCOME' else '-' if obj.transaction_type == 'EXPENSE' else '↔'
        return format_html('<strong class="text-{}">{} {}</strong>', css, sign, money(obj.amount))
    formatted_amount.short_description = 'المبلغ'

    def status_display(self, obj):
        if obj.is_cancelled:
            return format_html('<span style="color:#dc3545;font-weight:bold;">ملغية</span>')
        if obj.is_approved:
            return format_html('<span style="color:#198754;font-weight:bold;">معتمدة</span>')
        return format_html('<span style="color:#ffc107;font-weight:bold;">معلقة</span>')
    status_display.short_description = 'الحالة'

    @admin.action(description='اعتماد العمليات المحددة وتحديث الأرصدة')
    def approve_selected_transactions(self, request, queryset):
        approved_count = 0
        errors = 0

        for obj in queryset:
            try:
                if not obj.is_approved and not obj.is_cancelled:
                    obj.approve(request.user)
                    approved_count += 1
            except Exception as exc:
                errors += 1
                self.message_user(
                    request,
                    f'تعذر اعتماد {obj.transaction_number}: {exc}',
                    level=messages.ERROR,
                )

        if approved_count:
            self.message_user(request, f'تم اعتماد {approved_count} عملية بنجاح.', level=messages.SUCCESS)
        if errors:
            self.message_user(request, f'حدثت أخطاء في {errors} عملية.', level=messages.WARNING)

    @admin.action(description='إلغاء العمليات المحددة وعكس الأرصدة')
    def cancel_selected_transactions(self, request, queryset):
        cancelled_count = 0
        errors = 0

        for obj in queryset:
            try:
                if not obj.is_cancelled:
                    obj.cancel('إلغاء من لوحة الإدارة', request.user)
                    cancelled_count += 1
            except Exception as exc:
                errors += 1
                self.message_user(
                    request,
                    f'تعذر إلغاء {obj.transaction_number}: {exc}',
                    level=messages.ERROR,
                )

        if cancelled_count:
            self.message_user(request, f'تم إلغاء {cancelled_count} عملية بنجاح.', level=messages.SUCCESS)
        if errors:
            self.message_user(request, f'حدثت أخطاء في {errors} عملية.', level=messages.WARNING)


# ============================================================
# تصنيفات المصروفات
# ============================================================

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'account',
        'monthly_budget',
        'current_month_spending_display',
        'budget_percentage_display',
        'remaining_budget_display',
        'is_active',
    )
    list_filter = ('is_active', 'account')
    search_fields = ('name', 'code', 'description', 'account__name')
    ordering = ('code',)
    readonly_fields = (
        'current_month_spending_display',
        'budget_percentage_display',
        'remaining_budget_display',
        'created_at',
        'updated_at',
    )
    list_editable = ('is_active',)

    fieldsets = (
        ('بيانات التصنيف', {
            'fields': (
                'name',
                'code',
                'account',
                'description',
                'monthly_budget',
                'is_active',
            )
        }),
        ('متابعة الميزانية', {
            'fields': (
                'current_month_spending_display',
                'budget_percentage_display',
                'remaining_budget_display',
            )
        }),
        ('معلومات النظام', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )

    def current_month_spending_display(self, obj):
        return money(obj.current_month_spending)
    current_month_spending_display.short_description = 'مصروف الشهر'

    def budget_percentage_display(self, obj):
        return f'{obj.budget_percentage}%'
    budget_percentage_display.short_description = 'نسبة الاستخدام'

    def remaining_budget_display(self, obj):
        return money(obj.remaining_budget)
    remaining_budget_display.short_description = 'المتبقي'


# ============================================================
# المصروفات اليومية
# ============================================================

@admin.register(DailyExpense)
class DailyExpenseAdmin(admin.ModelAdmin):
    list_display = (
        'expense_number',
        'category',
        'expense_type',
        'formatted_amount',
        'vendor_name',
        'is_approved',
        'expense_date',
        'created_by',
    )
    list_filter = ('expense_type', 'is_approved', 'category', 'expense_date')
    search_fields = (
        'expense_number',
        'description',
        'vendor_name',
        'invoice_number',
        'notes',
    )
    readonly_fields = (
        'expense_number',
        'created_at',
        'approved_by',
        'approved_at',
    )
    ordering = ('-expense_date', '-created_at')
    date_hierarchy = 'expense_date'
    actions = ('approve_selected_expenses',)

    fieldsets = (
        ('بيانات المصروف', {
            'fields': (
                'expense_number',
                'category',
                'expense_type',
                'description',
                'amount',
                'notes',
            )
        }),
        ('المورد والفاتورة', {
            'fields': (
                'vendor_name',
                'invoice_number',
            )
        }),
        ('التاريخ والربط المالي', {
            'fields': (
                'expense_date',
                'transaction',
            )
        }),
        ('المستخدمون والحالة', {
            'fields': (
                'created_by',
                'approved_by',
                'approved_at',
                'is_approved',
            )
        }),
        ('معلومات النظام', {
            'fields': (
                'created_at',
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category',
            'category__account',
            'transaction',
            'created_by',
            'approved_by',
        )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user

        if not obj.expense_number:
            obj.expense_number = DailyExpense.generate_expense_number()

        super().save_model(request, obj, form, change)

    def formatted_amount(self, obj):
        return format_html('<strong>{}</strong>', money(obj.amount))
    formatted_amount.short_description = 'المبلغ'

    @admin.action(description='اعتماد المصروفات المحددة')
    def approve_selected_expenses(self, request, queryset):
        approved_count = 0
        errors = 0

        for obj in queryset:
            try:
                if not obj.is_approved:
                    obj.approve(request.user)
                    approved_count += 1
            except Exception as exc:
                errors += 1
                self.message_user(
                    request,
                    f'تعذر اعتماد {obj.expense_number}: {exc}',
                    level=messages.ERROR,
                )

        if approved_count:
            self.message_user(request, f'تم اعتماد {approved_count} مصروف بنجاح.', level=messages.SUCCESS)
        if errors:
            self.message_user(request, f'حدثت أخطاء في {errors} مصروف.', level=messages.WARNING)


# ============================================================
# لقطات الخزينة
# ============================================================

@admin.register(TreasurySnapshot)
class TreasurySnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'treasury',
        'snapshot_date',
        'opening_balance',
        'closing_balance',
        'total_income',
        'total_expenses',
        'transactions_count',
    )
    list_filter = ('treasury', 'snapshot_date')
    ordering = ('-snapshot_date',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'snapshot_date'


# ============================================================
# قفل اليوميات
# ============================================================

@admin.register(DailyClosing)
class DailyClosingAdmin(admin.ModelAdmin):
    list_display = (
        'treasury',
        'closing_date',
        'opening_balance',
        'total_income',
        'total_expenses',
        'closing_balance',
        'closed_by',
        'closed_at',
    )
    list_filter = ('treasury', 'closing_date', 'closed_at')
    search_fields = ('treasury__name', 'treasury__code', 'notes')
    readonly_fields = (
        'opening_balance',
        'total_income',
        'total_expenses',
        'closing_balance',
        'closed_by',
        'closed_at',
    )
    ordering = ('-closing_date', '-closed_at')


# ============================================================
# جرد الخزائن
# ============================================================

@admin.register(TreasuryReconciliation)
class TreasuryReconciliationAdmin(admin.ModelAdmin):
    list_display = (
        'treasury',
        'reconciliation_date',
        'book_balance',
        'actual_balance',
        'difference_display',
        'is_approved',
        'created_by',
        'approved_by',
    )
    list_filter = ('treasury', 'reconciliation_date', 'is_approved')
    search_fields = ('treasury__name', 'reason')
    readonly_fields = ('difference', 'created_at', 'approved_by', 'approved_at')
    ordering = ('-reconciliation_date', '-created_at')
    date_hierarchy = 'reconciliation_date'
    actions = ('approve_selected_reconciliations',)

    fieldsets = (
        ('بيانات الجرد', {
            'fields': (
                'treasury',
                'reconciliation_date',
                'book_balance',
                'actual_balance',
                'difference',
                'reason',
            )
        }),
        ('المستخدمون والحالة', {
            'fields': (
                'created_by',
                'is_approved',
                'approved_by',
                'approved_at',
            )
        }),
        ('معلومات النظام', {
            'fields': (
                'created_at',
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def difference_display(self, obj):
        value = obj.difference or 0
        color = '#198754' if value == 0 else '#dc3545'
        return format_html('<strong style="color:{};">{}</strong>', color, money(value))
    difference_display.short_description = 'الفرق'

    @admin.action(description='اعتماد الجرد المحدد')
    def approve_selected_reconciliations(self, request, queryset):
        count = 0
        for obj in queryset.filter(is_approved=False):
            obj.is_approved = True
            obj.approved_by = request.user
            obj.approved_at = timezone.now()
            obj.save(update_fields=['is_approved', 'approved_by', 'approved_at'])
            count += 1

        self.message_user(request, f'تم اعتماد {count} جرد.', level=messages.SUCCESS)


# ============================================================
# إعدادات الخزينة
# ============================================================

@admin.register(TreasurySettings)
class TreasurySettingsAdmin(admin.ModelAdmin):
    """
    إدارة إعدادات الخزينة من لوحة الإدارة.
    الموديل مصمم كسجل واحد فقط pk=1.
    """

    list_display = (
        'settings_title',
        'currency_display',
        'payment_limits',
        'approval_display',
        'notifications_display',
        'updated_display',
    )

    fieldsets = (
        ('إعدادات الخزينة', {
            'fields': (
                'currency',
                'min_payment',
                'max_payment',
            )
        }),
        ('إعدادات التقارير', {
            'fields': (
                'date_format',
                'report_language',
            )
        }),
        ('إعدادات الأمان والتنبيهات', {
            'fields': (
                'require_approval',
                'enable_notifications',
            )
        }),
        ('معلومات التحديث', {
            'fields': (
                'updated_at',
                'updated_by',
            )
        }),
    )

    readonly_fields = ('updated_at', 'updated_by')

    def has_add_permission(self, request):
        try:
            return not TreasurySettings.objects.exists()
        except Exception:
            return True

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.pk = 1
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def settings_title(self, obj):
        return 'إعدادات الخزينة'
    settings_title.short_description = 'الإعدادات'

    def currency_display(self, obj):
        return obj.currency or '-'
    currency_display.short_description = 'العملة'

    def payment_limits(self, obj):
        return f'{money(obj.min_payment)} - {money(obj.max_payment)}'
    payment_limits.short_description = 'حدود الدفع'

    def approval_display(self, obj):
        return 'نعم' if obj.require_approval else 'لا'
    approval_display.short_description = 'يتطلب موافقة'

    def notifications_display(self, obj):
        return 'مفعلة' if obj.enable_notifications else 'معطلة'
    notifications_display.short_description = 'الإشعارات'

    def updated_display(self, obj):
        return obj.updated_at or '-'
    updated_display.short_description = 'آخر تحديث'


