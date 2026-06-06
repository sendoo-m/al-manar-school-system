# treasury_management/forms.py
"""
Forms لتطبيق الخزينة.

الهدف:
- تنظيم إدخال البيانات بدل قراءة request.POST مباشرة.
- استخدام DecimalField بدلاً من float.
- التحقق من الحساب المناسب حسب نوع العملية.
- التحقق من كفاية رصيد الخزنة عند المصروف والتحويل.
- دعم الحقول الجديدة في Transaction مثل source_type, to_treasury, notes.
"""

from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    AccountCategory,
    Account,
    Treasury,
    Transaction,
    ExpenseCategory,
    DailyExpense,
    TreasurySettings,
    DailyClosing,
    TreasuryReconciliation,
)


# ============================================================
# Helpers / Mixins
# ============================================================

class BootstrapFormMixin:
    """إضافة Bootstrap classes لكل الحقول تلقائياً"""

    def apply_bootstrap(self):
        for field_name, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault('class', 'form-control')
                widget.attrs.setdefault('rows', 3)
            else:
                widget.attrs.setdefault('class', 'form-control')


def active_treasuries():
    return Treasury.objects.filter(is_active=True).select_related('account').order_by('name')


def active_accounts():
    return Account.objects.filter(is_active=True).select_related('category').order_by('code')


def income_accounts():
    return Account.objects.filter(
        is_active=True,
        category__category_type='REVENUE'
    ).select_related('category').order_by('code')


def expense_accounts():
    return Account.objects.filter(
        is_active=True,
        category__category_type='EXPENSE'
    ).select_related('category').order_by('code')


def asset_accounts():
    return Account.objects.filter(
        is_active=True,
        category__category_type='ASSET'
    ).select_related('category').order_by('code')


# ============================================================
# العمليات المالية
# ============================================================

class TransactionForm(BootstrapFormMixin, forms.ModelForm):
    """نموذج إضافة وتعديل عملية مالية"""

    transaction_date = forms.DateField(
        label='تاريخ العملية',
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.localdate,
        required=True,
    )

    class Meta:
        model = Transaction
        fields = [
            'transaction_type',
            'source_type',
            'treasury',
            'to_treasury',
            'account',
            'amount',
            'description',
            'payment_method',
            'reference_number',
            'notes',
            'transaction_date',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['treasury'].queryset = active_treasuries()
        self.fields['to_treasury'].queryset = active_treasuries()
        self.fields['account'].queryset = active_accounts()

        self.fields['to_treasury'].required = False
        self.fields['source_type'].required = False
        self.fields['reference_number'].required = False
        self.fields['notes'].required = False

        self.fields['amount'].min_value = Decimal('0.01')
        self.fields['amount'].widget.attrs.update({
            'min': '0.01',
            'step': '0.01',
            'placeholder': '0.00',
        })

        self.apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()

        transaction_type = cleaned_data.get('transaction_type')
        treasury = cleaned_data.get('treasury')
        to_treasury = cleaned_data.get('to_treasury')
        account = cleaned_data.get('account')
        amount = cleaned_data.get('amount')
        description = cleaned_data.get('description')

        if not description:
            self.add_error('description', 'وصف العملية مطلوب.')

        if not amount or amount <= 0:
            self.add_error('amount', 'المبلغ يجب أن يكون أكبر من صفر.')

        if not transaction_type:
            self.add_error('transaction_type', 'يجب اختيار نوع العملية.')

        if not treasury:
            self.add_error('treasury', 'يجب اختيار الخزنة.')

        if not account:
            self.add_error('account', 'يجب اختيار الحساب.')

        if transaction_type == 'INCOME':
            if account and account.category.category_type != 'REVENUE':
                self.add_error('account', 'عملية الإيراد يجب أن ترتبط بحساب من نوع إيرادات.')

            cleaned_data['to_treasury'] = None

        elif transaction_type == 'EXPENSE':
            if account and account.category.category_type != 'EXPENSE':
                self.add_error('account', 'عملية المصروف يجب أن ترتبط بحساب من نوع مصروفات.')

            if treasury and amount and treasury.current_balance < amount:
                self.add_error('amount', f'الرصيد غير كافٍ في {treasury.name}. الرصيد الحالي: {treasury.current_balance}')

            cleaned_data['to_treasury'] = None

        elif transaction_type == 'TRANSFER':
            if not to_treasury:
                self.add_error('to_treasury', 'يجب اختيار الخزنة المحول إليها.')

            if treasury and to_treasury and treasury.id == to_treasury.id:
                self.add_error('to_treasury', 'لا يمكن التحويل إلى نفس الخزنة.')

            if treasury and amount and treasury.current_balance < amount:
                self.add_error('amount', f'الرصيد غير كافٍ في {treasury.name}. الرصيد الحالي: {treasury.current_balance}')

            # في التحويل نسمح بحساب أصول أو حساب الخزنة نفسه.
            if account and account.category.category_type != 'ASSET':
                self.add_error('account', 'عملية التحويل يجب أن ترتبط بحساب من نوع أصول.')

        return cleaned_data

    def save(self, commit=True):
        obj = super().save(commit=False)

        # transaction_date في الموديل DateTimeField، والنموذج DateField
        date_value = self.cleaned_data.get('transaction_date')
        if date_value and not hasattr(date_value, 'hour'):
            obj.transaction_date = timezone.make_aware(
                timezone.datetime.combine(date_value, timezone.datetime.min.time())
            )

        if self.user and not obj.created_by_id:
            obj.created_by = self.user

        if commit:
            obj.save()

        return obj


class TransactionFilterForm(BootstrapFormMixin, forms.Form):
    """فلترة قائمة العمليات المالية"""

    type = forms.ChoiceField(
        label='نوع العملية',
        choices=[('', 'كل الأنواع')] + Transaction.TRANSACTION_TYPES,
        required=False,
    )
    source_type = forms.ChoiceField(
        label='مصدر العملية',
        choices=[('', 'كل المصادر')] + Transaction.SOURCE_TYPES,
        required=False,
    )
    treasury = forms.ModelChoiceField(
        label='الخزنة',
        queryset=Treasury.objects.none(),
        required=False,
        empty_label='كل الخزائن',
    )
    approved = forms.ChoiceField(
        label='الحالة',
        choices=[
            ('', 'كل الحالات'),
            ('true', 'معتمدة'),
            ('false', 'معلقة'),
            ('cancelled', 'ملغية'),
        ],
        required=False,
    )
    from_date = forms.DateField(
        label='من تاريخ',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
    )
    to_date = forms.DateField(
        label='إلى تاريخ',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
    )
    search = forms.CharField(
        label='بحث',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'رقم العملية، الوصف، المرجع...'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['treasury'].queryset = active_treasuries()
        self.apply_bootstrap()


class TransactionCancelForm(BootstrapFormMixin, forms.Form):
    """نموذج إلغاء عملية مالية"""

    cancellation_reason = forms.CharField(
        label='سبب الإلغاء',
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'اكتب سبب الإلغاء بوضوح'}),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.apply_bootstrap()


# ============================================================
# المصروفات اليومية
# ============================================================

class DailyExpenseForm(BootstrapFormMixin, forms.ModelForm):
    """نموذج إضافة مصروف يومي"""

    treasury = forms.ModelChoiceField(
        label='الخزنة',
        queryset=Treasury.objects.none(),
        required=True,
    )

    expense_date = forms.DateField(
        label='تاريخ المصروف',
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.localdate,
        required=True,
    )

    class Meta:
        model = DailyExpense
        fields = [
            'category',
            'expense_type',
            'description',
            'amount',
            'vendor_name',
            'invoice_number',
            'notes',
            'expense_date',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['treasury'].queryset = active_treasuries()
        self.fields['category'].queryset = ExpenseCategory.objects.filter(
            is_active=True
        ).select_related('account').order_by('name')

        self.fields['vendor_name'].required = False
        self.fields['invoice_number'].required = False
        self.fields['notes'].required = False

        self.fields['amount'].min_value = Decimal('0.01')
        self.fields['amount'].widget.attrs.update({
            'min': '0.01',
            'step': '0.01',
            'placeholder': '0.00',
        })

        self.apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()

        treasury = cleaned_data.get('treasury')
        amount = cleaned_data.get('amount')
        category = cleaned_data.get('category')
        description = cleaned_data.get('description')

        if not description:
            self.add_error('description', 'وصف المصروف مطلوب.')

        if not category:
            self.add_error('category', 'تصنيف المصروف مطلوب.')

        if not amount or amount <= 0:
            self.add_error('amount', 'المبلغ يجب أن يكون أكبر من صفر.')

        if treasury and amount and treasury.current_balance < amount:
            self.add_error('amount', f'الرصيد غير كافٍ في {treasury.name}. الرصيد الحالي: {treasury.current_balance}')

        if category and category.account.category.category_type != 'EXPENSE':
            self.add_error('category', 'تصنيف المصروف يجب أن يكون مرتبطاً بحساب مصروفات.')

        return cleaned_data

    def save(self, commit=True):
        obj = super().save(commit=False)

        if self.user and not obj.created_by_id:
            obj.created_by = self.user

        if commit:
            obj.save()

        return obj


class DailyExpenseFilterForm(BootstrapFormMixin, forms.Form):
    """فلترة المصروفات اليومية"""

    category = forms.ModelChoiceField(
        label='التصنيف',
        queryset=ExpenseCategory.objects.none(),
        required=False,
        empty_label='كل التصنيفات',
    )
    type = forms.ChoiceField(
        label='نوع المصروف',
        choices=[('', 'كل الأنواع')] + DailyExpense.EXPENSE_TYPES,
        required=False,
    )
    approved = forms.ChoiceField(
        label='الحالة',
        choices=[
            ('', 'كل الحالات'),
            ('true', 'معتمد'),
            ('false', 'معلق'),
        ],
        required=False,
    )
    from_date = forms.DateField(
        label='من تاريخ',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
    )
    to_date = forms.DateField(
        label='إلى تاريخ',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
    )
    search = forms.CharField(
        label='بحث',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'الوصف، المورد، رقم الفاتورة...'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['category'].queryset = ExpenseCategory.objects.filter(is_active=True).order_by('name')
        self.apply_bootstrap()


# ============================================================
# الخزائن
# ============================================================

class TreasuryForm(BootstrapFormMixin, forms.ModelForm):
    """نموذج إنشاء/تعديل خزنة"""

    opening_balance = forms.DecimalField(
        label='الرصيد الافتتاحي',
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.00'),
        required=False,
        initial=Decimal('0.00'),
        help_text='يستخدم عند إنشاء حساب جديد للخزنة فقط.',
    )

    class Meta:
        model = Treasury
        fields = [
            'name',
            'code',
            'account',
            'responsible_person',
            'location',
            'min_limit',
            'max_limit',
            'is_active',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['account'].queryset = asset_accounts()
        self.fields['responsible_person'].required = False
        self.fields['location'].required = False
        self.fields['max_limit'].required = False
        self.fields['min_limit'].required = False

        if self.instance and self.instance.pk:
            self.fields['opening_balance'].disabled = True
            self.fields['opening_balance'].required = False

        self.apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()

        account = cleaned_data.get('account')
        min_limit = cleaned_data.get('min_limit') or Decimal('0.00')
        max_limit = cleaned_data.get('max_limit')

        if account and account.category.category_type != 'ASSET':
            self.add_error('account', 'حساب الخزنة يجب أن يكون من نوع أصول.')

        if max_limit is not None and max_limit < min_limit:
            self.add_error('max_limit', 'الحد الأقصى لا يمكن أن يكون أقل من الحد الأدنى.')

        return cleaned_data


# ============================================================
# الحسابات وتصنيفات الحسابات
# ============================================================

class AccountCategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AccountCategory
        fields = [
            'name',
            'code',
            'category_type',
            'parent',
            'description',
            'is_active',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['parent'].queryset = AccountCategory.objects.filter(is_active=True).order_by('code')
        self.fields['parent'].required = False
        self.fields['description'].required = False

        if self.instance and self.instance.pk:
            self.fields['parent'].queryset = self.fields['parent'].queryset.exclude(pk=self.instance.pk)

        self.apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()

        parent = cleaned_data.get('parent')
        category_type = cleaned_data.get('category_type')

        if parent and parent.category_type != category_type:
            self.add_error('parent', 'التصنيف الفرعي يجب أن يكون من نفس نوع التصنيف الرئيسي.')

        return cleaned_data


class AccountForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            'category',
            'name',
            'code',
            'description',
            'opening_balance',
            'is_active',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['category'].queryset = AccountCategory.objects.filter(is_active=True).order_by('code')
        self.fields['description'].required = False

        self.fields['opening_balance'].widget.attrs.update({
            'step': '0.01',
        })

        # لا نسمح بتغيير الرصيد الافتتاحي للحسابات القائمة من النموذج العادي
        if self.instance and self.instance.pk:
            self.fields['opening_balance'].disabled = True

        self.apply_bootstrap()

    def save(self, commit=True):
        obj = super().save(commit=False)

        if not obj.pk:
            obj.current_balance = obj.opening_balance or Decimal('0.00')

        if commit:
            obj.save()

        return obj


# ============================================================
# تصنيفات المصروفات
# ============================================================

class ExpenseCategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = [
            'name',
            'code',
            'account',
            'description',
            'monthly_budget',
            'is_active',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['account'].queryset = expense_accounts()
        self.fields['description'].required = False
        self.fields['monthly_budget'].required = False
        self.fields['monthly_budget'].widget.attrs.update({
            'min': '0',
            'step': '0.01',
        })

        self.apply_bootstrap()

    def clean_account(self):
        account = self.cleaned_data.get('account')

        if account and account.category.category_type != 'EXPENSE':
            raise ValidationError('تصنيف المصروفات يجب أن يرتبط بحساب من نوع مصروفات.')

        return account


# ============================================================
# إعدادات الخزينة
# ============================================================

class TreasurySettingsForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TreasurySettings
        fields = [
            'currency',
            'min_payment',
            'max_payment',
            'require_approval',
            'enable_notifications',
            'report_language',
            'date_format',
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['min_payment'].widget.attrs.update({
            'min': '0',
            'step': '0.01',
        })
        self.fields['max_payment'].widget.attrs.update({
            'min': '0',
            'step': '0.01',
        })

        self.apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()

        min_payment = cleaned_data.get('min_payment') or Decimal('0.00')
        max_payment = cleaned_data.get('max_payment') or Decimal('0.00')

        if max_payment > 0 and min_payment > max_payment:
            self.add_error('max_payment', 'أكبر مبلغ دفع يجب أن يكون أكبر من أو يساوي أقل مبلغ دفع.')

        return cleaned_data

    def save(self, commit=True):
        obj = super().save(commit=False)

        if self.user and hasattr(obj, 'updated_by'):
            obj.updated_by = self.user

        if commit:
            obj.save()

        return obj


# ============================================================
# قفل اليومية والجرد
# ============================================================

class DailyClosingForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DailyClosing
        fields = [
            'treasury',
            'closing_date',
            'opening_balance',
            'total_income',
            'total_expenses',
            'closing_balance',
            'notes',
        ]
        widgets = {
            'closing_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['treasury'].queryset = active_treasuries()
        self.fields['notes'].required = False

        self.apply_bootstrap()

    def save(self, commit=True):
        obj = super().save(commit=False)

        if self.user and not obj.closed_by_id:
            obj.closed_by = self.user

        if commit:
            obj.save()

        return obj


class TreasuryReconciliationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TreasuryReconciliation
        fields = [
            'treasury',
            'reconciliation_date',
            'book_balance',
            'actual_balance',
            'reason',
        ]
        widgets = {
            'reconciliation_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['treasury'].queryset = active_treasuries()
        self.fields['reason'].required = False

        self.apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()

        book_balance = cleaned_data.get('book_balance')
        actual_balance = cleaned_data.get('actual_balance')

        if book_balance is None:
            self.add_error('book_balance', 'الرصيد الدفتري مطلوب.')

        if actual_balance is None:
            self.add_error('actual_balance', 'الرصيد الفعلي مطلوب.')

        return cleaned_data

    def save(self, commit=True):
        obj = super().save(commit=False)

        if self.user and not obj.created_by_id:
            obj.created_by = self.user

        if commit:
            obj.save()

        return obj
