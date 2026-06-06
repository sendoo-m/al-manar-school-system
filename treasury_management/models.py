from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction as db_transaction
from django.db.models import Sum
from django.utils import timezone

from school_settings.models import AcademicYear


# ============================================================
# شجرة وتصنيفات الحسابات
# ============================================================

class AccountCategory(models.Model):
    """تصنيفات الحسابات"""

    CATEGORY_TYPES = [
        ('REVENUE', 'إيرادات'),
        ('EXPENSE', 'مصروفات'),
        ('ASSET', 'أصول'),
        ('LIABILITY', 'خصوم'),
        ('EQUITY', 'حقوق الملكية'),
    ]

    name = models.CharField(max_length=100, verbose_name='اسم التصنيف')
    category_type = models.CharField(max_length=15, choices=CATEGORY_TYPES, verbose_name='نوع التصنيف')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='التصنيف الرئيسي'
    )
    code = models.CharField(max_length=20, unique=True, verbose_name='كود التصنيف')
    description = models.TextField(blank=True, verbose_name='الوصف')
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'تصنيف الحساب'
        verbose_name_plural = 'تصنيفات الحسابات'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Account(models.Model):
    """الحسابات المالية"""

    category = models.ForeignKey(
        AccountCategory,
        on_delete=models.CASCADE,
        related_name='accounts',
        verbose_name='التصنيف'
    )
    name = models.CharField(max_length=150, verbose_name='اسم الحساب')
    code = models.CharField(max_length=30, unique=True, verbose_name='كود الحساب')
    description = models.TextField(blank=True, verbose_name='وصف الحساب')
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الرصيد الافتتاحي')
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الرصيد الحالي')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'حساب مالي'
        verbose_name_plural = 'الحسابات المالية'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def category_type(self):
        return self.category.category_type if self.category_id else None


# ============================================================
# الخزائن
# ============================================================

class Treasury(models.Model):
    """خزائن المدرسة"""

    name = models.CharField(max_length=100, verbose_name='اسم الخزنة')
    code = models.CharField(max_length=20, unique=True, verbose_name='كود الخزنة')
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name='treasury',
        verbose_name='الحساب المالي'
    )
    responsible_person = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='المسؤول'
    )
    location = models.CharField(max_length=100, blank=True, verbose_name='الموقع')
    max_limit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name='الحد الأقصى')
    min_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الحد الأدنى')
    is_active = models.BooleanField(default=True, verbose_name='نشطة')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'خزنة'
        verbose_name_plural = 'الخزائن'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - الرصيد: {self.current_balance}"

    @property
    def current_balance(self):
        if self.account_id:
            return self.account.current_balance
        return Decimal('0.00')

    def clean(self):
        if self.account_id and self.account.category.category_type != 'ASSET':
            raise ValidationError('حساب الخزنة يجب أن يكون من نوع أصول.')


# ============================================================
# العمليات المالية
# ============================================================

class Transaction(models.Model):
    """العمليات المالية"""

    TRANSACTION_TYPES = [
        ('INCOME', 'إيراد'),
        ('EXPENSE', 'مصروف'),
        ('TRANSFER', 'تحويل'),
    ]

    SOURCE_TYPES = [
        ('STUDENT_FEES', 'مصروفات دراسية'),
        ('BUS_FEES', 'إيرادات الباص'),
        ('ACTIVITY_FEES', 'إيرادات الأنشطة'),
        ('BOOKS_SALES', 'إيرادات الكتب'),
        ('UNIFORM_SALES', 'إيرادات الزي'),
        ('OTHER_INCOME', 'إيراد آخر'),
        ('DAILY_EXPENSE', 'مصروف يومي'),
        ('SALARY', 'مرتبات'),
        ('MAINTENANCE', 'صيانة'),
        ('UTILITIES', 'مرافق'),
        ('SUPPLIES', 'مستلزمات'),
        ('TRANSPORTATION', 'نقل'),
        ('OTHER_EXPENSE', 'مصروف آخر'),
        ('TRANSFER', 'تحويل بين الخزائن'),
        ('ADJUSTMENT', 'تسوية / جرد'),
    ]

    PAYMENT_METHODS = [
        ('CASH', 'نقدي'),
        ('BANK_TRANSFER', 'تحويل بنكي'),
        ('CHECK', 'شيك'),
        ('CREDIT_CARD', 'كارت ائتماني'),
        ('OTHER', 'أخرى'),
    ]

    transaction_number = models.CharField(max_length=30, unique=True, blank=True, verbose_name='رقم العملية')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name='نوع العملية')
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPES, blank=True, verbose_name='مصدر العملية')

    treasury = models.ForeignKey(
        Treasury,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='الخزنة'
    )
    to_treasury = models.ForeignKey(
        Treasury,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incoming_transfers',
        verbose_name='الخزنة المحول إليها'
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='الحساب'
    )

    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='المبلغ')
    description = models.TextField(verbose_name='وصف العملية')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CASH', verbose_name='طريقة الدفع')

    reference_number = models.CharField(max_length=50, blank=True, verbose_name='رقم المرجع')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    related_model = models.CharField(max_length=50, blank=True, verbose_name='النموذج المرتبط')
    related_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='معرف السجل المرتبط')

    transaction_date = models.DateTimeField(default=timezone.now, verbose_name='تاريخ العملية')
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='العام الدراسي'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_transactions',
        verbose_name='أنشأ بواسطة'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_transactions',
        verbose_name='اعتمد بواسطة'
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الاعتماد')

    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_transactions',
        verbose_name='ألغيت بواسطة'
    )
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الإلغاء')

    is_approved = models.BooleanField(default=False, verbose_name='معتمدة')
    is_cancelled = models.BooleanField(default=False, verbose_name='ملغية')
    cancellation_reason = models.TextField(blank=True, verbose_name='سبب الإلغاء')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'عملية مالية'
        verbose_name_plural = 'العمليات المالية'
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['transaction_type', 'is_approved', 'is_cancelled']),
            models.Index(fields=['transaction_date']),
            models.Index(fields=['treasury']),
            models.Index(fields=['source_type']),
        ]

    def __str__(self):
        return f"{self.transaction_number} - {self.get_transaction_type_display()} - {self.amount}"

    def clean(self):
        if self.amount is None or self.amount <= 0:
            raise ValidationError('المبلغ يجب أن يكون أكبر من صفر.')

        if self.transaction_type == 'INCOME':
            if self.account_id and self.account.category.category_type != 'REVENUE':
                raise ValidationError('عملية الإيراد يجب أن ترتبط بحساب من نوع إيرادات.')

        elif self.transaction_type == 'EXPENSE':
            if self.account_id and self.account.category.category_type != 'EXPENSE':
                raise ValidationError('عملية المصروف يجب أن ترتبط بحساب من نوع مصروفات.')

        elif self.transaction_type == 'TRANSFER':
            if not self.to_treasury_id:
                raise ValidationError('يجب اختيار الخزنة المحول إليها في عملية التحويل.')
            if self.to_treasury_id == self.treasury_id:
                raise ValidationError('لا يمكن التحويل إلى نفس الخزنة.')

    def save(self, *args, **kwargs):
        if not self.transaction_number:
            self.transaction_number = self.generate_transaction_number()
        super().save(*args, **kwargs)

    @classmethod
    def generate_transaction_number(cls):
        """
        توليد رقم عملية آمن وغير مكرر.

        سبب التعديل:
        الطريقة القديمة كانت تعتمد على count + 1 وقد تنتج رقم مكرر
        خصوصاً عند إضافة عمليات بتاريخ مختلف أو عند حذف سجلات قديمة.
        """
        today = timezone.localdate()
        date_str = today.strftime('%Y%m%d')
        prefix = f"TRX{date_str}"

        last_transaction = cls.objects.filter(
            transaction_number__startswith=prefix
        ).order_by('-transaction_number').first()

        if last_transaction and last_transaction.transaction_number:
            try:
                last_serial = int(last_transaction.transaction_number.replace(prefix, ''))
            except (ValueError, TypeError):
                last_serial = 0
        else:
            last_serial = 0

        serial = last_serial + 1

        while True:
            number = f"{prefix}{serial:04d}"
            if not cls.objects.filter(transaction_number=number).exists():
                return number
            serial += 1


    def approve(self, user):
        """اعتماد العملية وتحديث الأرصدة مرة واحدة فقط"""
        if self.is_cancelled:
            raise ValidationError('لا يمكن اعتماد عملية ملغية.')
        if self.is_approved:
            return

        self.full_clean()

        with db_transaction.atomic():
            Transaction.objects.select_for_update().filter(pk=self.pk).first()
            self.is_approved = True
            self.approved_by = user
            self.approved_at = timezone.now()
            self.save(update_fields=['is_approved', 'approved_by', 'approved_at', 'updated_at'])
            self.update_balances()

    def cancel(self, reason, user):
        """إلغاء العملية وعكس تأثيرها إذا كانت معتمدة"""
        if self.is_cancelled:
            return
        if not reason:
            raise ValidationError('يجب إدخال سبب الإلغاء.')

        with db_transaction.atomic():
            Transaction.objects.select_for_update().filter(pk=self.pk).first()
            if self.is_approved:
                self.reverse_balances()
            self.is_cancelled = True
            self.cancellation_reason = reason
            self.cancelled_by = user
            self.cancelled_at = timezone.now()
            self.save(update_fields=[
                'is_cancelled', 'cancellation_reason', 'cancelled_by', 'cancelled_at', 'updated_at'
            ])

    def update_balances(self):
        """تحديث الأرصدة حسب نوع العملية"""
        amount = Decimal(self.amount)

        if self.transaction_type == 'INCOME':
            self.treasury.account.current_balance += amount
            self.account.current_balance += amount
            self.treasury.account.save(update_fields=['current_balance', 'updated_at'])
            self.account.save(update_fields=['current_balance', 'updated_at'])

        elif self.transaction_type == 'EXPENSE':
            if self.treasury.account.current_balance < amount:
                raise ValidationError('الرصيد غير كافٍ في الخزنة.')
            self.treasury.account.current_balance -= amount
            self.account.current_balance += amount
            self.treasury.account.save(update_fields=['current_balance', 'updated_at'])
            self.account.save(update_fields=['current_balance', 'updated_at'])

        elif self.transaction_type == 'TRANSFER':
            if not self.to_treasury_id:
                raise ValidationError('يجب تحديد الخزنة المحول إليها.')
            if self.treasury.account.current_balance < amount:
                raise ValidationError('الرصيد غير كافٍ في الخزنة المحول منها.')
            self.treasury.account.current_balance -= amount
            self.to_treasury.account.current_balance += amount
            self.treasury.account.save(update_fields=['current_balance', 'updated_at'])
            self.to_treasury.account.save(update_fields=['current_balance', 'updated_at'])

    def reverse_balances(self):
        """عكس تأثير العملية على الأرصدة عند الإلغاء"""
        amount = Decimal(self.amount)

        if self.transaction_type == 'INCOME':
            self.treasury.account.current_balance -= amount
            self.account.current_balance -= amount
            self.treasury.account.save(update_fields=['current_balance', 'updated_at'])
            self.account.save(update_fields=['current_balance', 'updated_at'])

        elif self.transaction_type == 'EXPENSE':
            self.treasury.account.current_balance += amount
            self.account.current_balance -= amount
            self.treasury.account.save(update_fields=['current_balance', 'updated_at'])
            self.account.save(update_fields=['current_balance', 'updated_at'])

        elif self.transaction_type == 'TRANSFER':
            if not self.to_treasury_id:
                raise ValidationError('لا يمكن عكس تحويل بدون خزنة محول إليها.')
            self.treasury.account.current_balance += amount
            self.to_treasury.account.current_balance -= amount
            self.treasury.account.save(update_fields=['current_balance', 'updated_at'])
            self.to_treasury.account.save(update_fields=['current_balance', 'updated_at'])


# ============================================================
# المصروفات اليومية
# ============================================================

class ExpenseCategory(models.Model):
    """تصنيفات المصروفات"""

    name = models.CharField(max_length=100, verbose_name='اسم التصنيف')
    code = models.CharField(max_length=20, unique=True, verbose_name='كود التصنيف')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='expense_categories', verbose_name='الحساب المرتبط')
    description = models.TextField(blank=True, verbose_name='الوصف')
    monthly_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='الميزانية الشهرية')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'تصنيف المصروفات'
        verbose_name_plural = 'تصنيفات المصروفات'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        if self.account_id and self.account.category.category_type != 'EXPENSE':
            raise ValidationError('تصنيف المصروفات يجب أن يرتبط بحساب من نوع مصروفات.')

    @property
    def current_month_spending(self):
        month_start = timezone.localdate().replace(day=1)
        total = self.daily_expenses.filter(
            expense_date__gte=month_start,
            is_approved=True,
            transaction__is_cancelled=False,
        ).aggregate(total=Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def budget_percentage(self):
        if self.monthly_budget and self.monthly_budget > 0:
            return round((self.current_month_spending / self.monthly_budget) * 100, 2)
        return 0

    @property
    def remaining_budget(self):
        if self.monthly_budget:
            return self.monthly_budget - self.current_month_spending
        return Decimal('0.00')


class DailyExpense(models.Model):
    """المصروفات اليومية"""

    EXPENSE_TYPES = [
        ('SALARIES', 'مرتبات'),
        ('UTILITIES', 'مرافق'),
        ('SUPPLIES', 'مستلزمات'),
        ('MAINTENANCE', 'صيانة'),
        ('MARKETING', 'دعاية'),
        ('TRANSPORTATION', 'نقل'),
        ('OTHER', 'أخرى'),
    ]

    expense_number = models.CharField(max_length=30, unique=True, blank=True, verbose_name='رقم المصروف')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name='daily_expenses', verbose_name='التصنيف')
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPES, verbose_name='نوع المصروف')
    description = models.TextField(verbose_name='وصف المصروف')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='المبلغ')

    vendor_name = models.CharField(max_length=100, blank=True, verbose_name='اسم المورد')
    invoice_number = models.CharField(max_length=50, blank=True, verbose_name='رقم الفاتورة')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    expense_date = models.DateField(default=timezone.localdate, verbose_name='تاريخ المصروف')
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='daily_expense',
        verbose_name='العملية المالية'
    )

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_daily_expenses', verbose_name='أنشأ بواسطة')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenses', verbose_name='اعتمد بواسطة')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الاعتماد')
    is_approved = models.BooleanField(default=False, verbose_name='معتمد')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'مصروف يومي'
        verbose_name_plural = 'المصروفات اليومية'
        ordering = ['-expense_date', '-created_at']

    def __str__(self):
        return f"{self.expense_number} - {self.description} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.expense_number:
            self.expense_number = self.generate_expense_number()
        super().save(*args, **kwargs)

    @classmethod
    def generate_expense_number(cls):
        """
        توليد رقم مصروف آمن وغير مكرر.

        سبب التعديل:
        الطريقة القديمة كانت:
            count = DailyExpense.objects.filter(expense_date=today).count() + 1

        وهذا قد يكرر الرقم لو تم تسجيل مصروف بتاريخ قديم أو مختلف
        لأن الرقم نفسه كان يعتمد على تاريخ اليوم وليس تاريخ المصروف.
        """
        today = timezone.localdate()
        date_str = today.strftime('%Y%m%d')
        prefix = f"EXP{date_str}"

        last_expense = cls.objects.filter(
            expense_number__startswith=prefix
        ).order_by('-expense_number').first()

        if last_expense and last_expense.expense_number:
            try:
                last_serial = int(last_expense.expense_number.replace(prefix, ''))
            except (ValueError, TypeError):
                last_serial = 0
        else:
            last_serial = 0

        serial = last_serial + 1

        while True:
            number = f"{prefix}{serial:04d}"
            if not cls.objects.filter(expense_number=number).exists():
                return number
            serial += 1


    def approve(self, user):
        if self.is_approved:
            return
        with db_transaction.atomic():
            self.is_approved = True
            self.approved_by = user
            self.approved_at = timezone.now()
            self.save(update_fields=['is_approved', 'approved_by', 'approved_at'])
            if self.transaction and not self.transaction.is_approved:
                self.transaction.approve(user)


# ============================================================
# اللقطات اليومية والجرد والقفل اليومي
# ============================================================

class TreasurySnapshot(models.Model):
    """لقطة يومية للخزنة"""

    treasury = models.ForeignKey(Treasury, on_delete=models.CASCADE, related_name='snapshots', verbose_name='الخزنة')
    snapshot_date = models.DateField(verbose_name='تاريخ اللقطة')
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='الرصيد الافتتاحي')
    closing_balance = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='الرصيد الختامي')
    total_income = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي الإيرادات')
    total_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي المصروفات')
    transactions_count = models.IntegerField(default=0, verbose_name='عدد العمليات')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'لقطة الخزنة اليومية'
        verbose_name_plural = 'لقطات الخزنة اليومية'
        unique_together = ['treasury', 'snapshot_date']
        ordering = ['-snapshot_date']

    def __str__(self):
        return f"{self.treasury.name} - {self.snapshot_date} - {self.closing_balance}"


class DailyClosing(models.Model):
    """قفل اليومية لكل خزنة"""

    treasury = models.ForeignKey(Treasury, on_delete=models.CASCADE, related_name='daily_closings', verbose_name='الخزنة')
    closing_date = models.DateField(verbose_name='تاريخ القفل')
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='رصيد بداية اليوم')
    total_income = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي الداخل')
    total_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي الخارج')
    closing_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='رصيد نهاية اليوم')
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='أغلق بواسطة')
    closed_at = models.DateTimeField(auto_now_add=True, verbose_name='وقت القفل')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'قفل يومية'
        verbose_name_plural = 'قفل اليوميات'
        unique_together = ['treasury', 'closing_date']
        ordering = ['-closing_date']

    def __str__(self):
        return f"{self.treasury.name} - {self.closing_date}"


class TreasuryReconciliation(models.Model):
    """جرد وتسوية الخزنة"""

    treasury = models.ForeignKey(Treasury, on_delete=models.CASCADE, related_name='reconciliations', verbose_name='الخزنة')
    reconciliation_date = models.DateField(default=timezone.localdate, verbose_name='تاريخ الجرد')
    book_balance = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='الرصيد الدفتري')
    actual_balance = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='الرصيد الفعلي')
    difference = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الفرق')
    reason = models.TextField(blank=True, verbose_name='سبب الفرق')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_reconciliations', verbose_name='تم الجرد بواسطة')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_reconciliations', verbose_name='تم الاعتماد بواسطة')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الاعتماد')
    is_approved = models.BooleanField(default=False, verbose_name='معتمد')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'جرد خزنة'
        verbose_name_plural = 'جرد الخزائن'
        ordering = ['-reconciliation_date', '-created_at']

    def save(self, *args, **kwargs):
        self.difference = Decimal(self.actual_balance or 0) - Decimal(self.book_balance or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.treasury.name} - {self.reconciliation_date} - فرق: {self.difference}"


# ============================================================
# ربط مدفوعات الطلاب
# ============================================================

class StudentPaymentTransaction(models.Model):
    """ربط مدفوعات الطلاب بالنظام المحاسبي"""

    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='student_payment_link', verbose_name='العملية المالية')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'عملية دفع طالب'
        verbose_name_plural = 'عمليات دفع الطلاب'


# ============================================================
# إعدادات الخزينة
# ============================================================

class TreasurySettings(models.Model):
    """إعدادات نظام الخزينة"""

    currency = models.CharField(max_length=10, default='EGP', verbose_name='العملة')
    min_payment = models.DecimalField(max_digits=12, decimal_places=2, default=50, verbose_name='أقل مبلغ دفع')
    max_payment = models.DecimalField(max_digits=12, decimal_places=2, default=5000, verbose_name='أكبر مبلغ دفع')
    require_approval = models.BooleanField(default=False, verbose_name='يتطلب اعتماد العمليات')
    enable_notifications = models.BooleanField(default=True, verbose_name='تفعيل التنبيهات')
    report_language = models.CharField(
        max_length=5,
        choices=[('ar', 'العربية'), ('en', 'English')],
        default='ar',
        verbose_name='لغة التقارير'
    )
    date_format = models.CharField(max_length=20, default='d/m/Y', verbose_name='تنسيق التاريخ')

    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='آخر تعديل بواسطة'
    )

    class Meta:
        verbose_name = 'إعدادات الخزينة'
        verbose_name_plural = 'إعدادات الخزينة'

    def __str__(self):
        return 'إعدادات الخزينة'

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


# from django.db import models
# from django.contrib.auth.models import User
# from django.conf import settings
# from django.utils import timezone
# from decimal import Decimal
# from school_settings.models import AcademicYear

# class AccountCategory(models.Model):
#     """تصنيفات الحسابات"""
#     CATEGORY_TYPES = [
#         ('REVENUE', 'إيرادات'),
#         ('EXPENSE', 'مصروفات'),
#         ('ASSET', 'أصول'),
#         ('LIABILITY', 'خصوم'),
#     ]
    
#     name = models.CharField(max_length=100, verbose_name='اسم التصنيف')
#     category_type = models.CharField(max_length=15, choices=CATEGORY_TYPES, verbose_name='نوع التصنيف')
#     parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name='التصنيف الرئيسي')
#     code = models.CharField(max_length=10, unique=True, verbose_name='كود التصنيف')
#     description = models.TextField(blank=True, verbose_name='الوصف')
#     is_active = models.BooleanField(default=True, verbose_name='نشط')
    
#     class Meta:
#         verbose_name = 'تصنيف الحساب'
#         verbose_name_plural = 'تصنيفات الحسابات'
#         ordering = ['code']
    
#     def __str__(self):
#         return f"{self.code} - {self.name}"

# class Account(models.Model):
#     """الحسابات المالية"""
#     category = models.ForeignKey(AccountCategory, on_delete=models.CASCADE, verbose_name='التصنيف')
#     name = models.CharField(max_length=150, verbose_name='اسم الحساب')
#     code = models.CharField(max_length=15, unique=True, verbose_name='كود الحساب')
#     description = models.TextField(blank=True, verbose_name='وصف الحساب')
#     opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الرصيد الافتتاحي')
#     current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الرصيد الحالي')
#     is_active = models.BooleanField(default=True, verbose_name='نشط')
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         verbose_name = 'حساب مالي'
#         verbose_name_plural = 'الحسابات المالية'
#         ordering = ['code']
    
#     def __str__(self):
#         return f"{self.code} - {self.name}"

# class Treasury(models.Model):
#     """خزائن المدرسة"""
#     name = models.CharField(max_length=100, verbose_name='اسم الخزنة')
#     code = models.CharField(max_length=10, unique=True, verbose_name='كود الخزنة')
#     account = models.OneToOneField(Account, on_delete=models.CASCADE, verbose_name='الحساب المالي')
#     responsible_person = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='المسؤول')
#     location = models.CharField(max_length=100, blank=True, verbose_name='الموقع')
#     max_limit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name='الحد الأقصى')
#     min_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الحد الأدنى')
#     is_active = models.BooleanField(default=True, verbose_name='نشطة')
#     created_at = models.DateTimeField(auto_now_add=True)
    
#     class Meta:
#         verbose_name = 'خزنة'
#         verbose_name_plural = 'الخزائن'
    
#     def __str__(self):
#         return f"{self.name} - الرصيد: {self.account.current_balance}"
    
#     @property
#     def current_balance(self):
#         return self.account.current_balance

# class Transaction(models.Model):
#     """العمليات المالية"""
#     TRANSACTION_TYPES = [
#         ('INCOME', 'إيراد'),
#         ('EXPENSE', 'مصروف'),
#         ('TRANSFER', 'تحويل'),
#     ]
    
#     PAYMENT_METHODS = [
#         ('CASH', 'نقدي'),
#         ('BANK_TRANSFER', 'تحويل بنكي'),
#         ('CHECK', 'شيك'),
#         ('CREDIT_CARD', 'كارت ائتماني'),
#         ('OTHER', 'أخرى'),
#     ]
    
#     transaction_number = models.CharField(max_length=20, unique=True, verbose_name='رقم العملية')
#     transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name='نوع العملية')
#     treasury = models.ForeignKey(Treasury, on_delete=models.CASCADE, verbose_name='الخزنة')
#     account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name='الحساب')
    
#     amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='المبلغ')
#     description = models.TextField(verbose_name='وصف العملية')
#     payment_method = models.CharField(max_length=15, choices=PAYMENT_METHODS, default='CASH', verbose_name='طريقة الدفع')
    
#     # معلومات إضافية
#     reference_number = models.CharField(max_length=50, blank=True, verbose_name='رقم المرجع')
#     related_model = models.CharField(max_length=50, blank=True, verbose_name='النموذج المرتبط')
#     related_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='معرف السجل المرتبط')
    
#     # التواريخ والمستخدمين
#     transaction_date = models.DateTimeField(default=timezone.now, verbose_name='تاريخ العملية')
#     academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, verbose_name='العام الدراسي')
#     created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='أنshأ بواسطة')
#     approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, 
#                                    related_name='approved_transactions', verbose_name='اعتمد بواسطة')
#     approved_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الاعتماد')
    
#     # الحالة
#     is_approved = models.BooleanField(default=False, verbose_name='معتمدة')
#     is_cancelled = models.BooleanField(default=False, verbose_name='ملغية')
#     cancellation_reason = models.TextField(blank=True, verbose_name='سبب الإلغاء')
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         verbose_name = 'عملية مالية'
#         verbose_name_plural = 'العمليات المالية'
#         ordering = ['-transaction_date', '-created_at']
    
#     def __str__(self):
#         return f"{self.transaction_number} - {self.get_transaction_type_display()} - {self.amount}"
    
#     def save(self, *args, **kwargs):
#         if not self.transaction_number:
#             self.transaction_number = self.generate_transaction_number()
#         super().save(*args, **kwargs)
    
#     def generate_transaction_number(self):
#         from datetime import datetime
#         date_str = datetime.now().strftime('%Y%m%d')
#         count = Transaction.objects.filter(
#             transaction_date__date=datetime.now().date()
#         ).count() + 1
#         return f"TRX{date_str}{count:04d}"
    
#     def approve(self, user):
#         """اعتماد العملية"""
#         if not self.is_approved:
#             self.is_approved = True
#             self.approved_by = user
#             self.approved_at = timezone.now()
#             self.save()
            
#             # تحديث رصيد الحساب والخزنة
#             self.update_balances()
    
#     def cancel(self, reason, user):
#         """إلغاء العملية"""
#         if not self.is_cancelled and self.is_approved:
#             # عكس العملية
#             self.reverse_balances()
            
#         self.is_cancelled = True
#         self.cancellation_reason = reason
#         self.save()
    
#     def update_balances(self):
#         """تحديث الأرصدة"""
#         if self.transaction_type == 'INCOME':
#             self.treasury.account.current_balance += self.amount
#             self.account.current_balance += self.amount
#         elif self.transaction_type == 'EXPENSE':
#             self.treasury.account.current_balance -= self.amount
#             self.account.current_balance -= self.amount
        
#         self.treasury.account.save()
#         self.account.save()
    
#     def reverse_balances(self):
#         """عكس تأثير العملية على الأرصدة"""
#         if self.transaction_type == 'INCOME':
#             self.treasury.account.current_balance -= self.amount
#             self.account.current_balance -= self.amount
#         elif self.transaction_type == 'EXPENSE':
#             self.treasury.account.current_balance += self.amount
#             self.account.current_balance += self.amount
        
#         self.treasury.account.save()
#         self.account.save()

# # في treasury_management/models.py - تحديث نموذج ExpenseCategory
# class ExpenseCategory(models.Model):
#     name = models.CharField(max_length=100, verbose_name='اسم التصنيف')
#     code = models.CharField(max_length=20, unique=True, verbose_name='كود التصنيف')
#     account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name='الحساب المرتبط')
#     description = models.TextField(blank=True, verbose_name='الوصف')
#     monthly_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='الميزانية الشهرية')
#     is_active = models.BooleanField(default=True, verbose_name='نشط')
    
#     # إضافة هذه الحقول إذا لم تكن موجودة
#     created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
#     updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    
#     class Meta:
#         verbose_name = 'تصنيف المصروفات'
#         verbose_name_plural = 'تصنيفات المصروفات'
#         ordering = ['code']
    
#     def __str__(self):
#         return f"{self.code} - {self.name}"
    
#     @property
#     def current_month_spending(self):
#         """الإنفاق الحالي هذا الشهر"""
#         from django.utils import timezone
#         today = timezone.now().date()
#         month_start = today.replace(day=1)
        
#         try:
#             total = self.dailyexpense_set.filter(
#                 expense_date__gte=month_start,
#                 is_approved=True
#             ).aggregate(total=Sum('amount'))['total']
#             return total or 0
#         except:
#             return 0
    
#     @property
#     def budget_percentage(self):
#         """النسبة المئوية المستخدمة من الميزانية"""
#         if self.monthly_budget and self.monthly_budget > 0:
#             return (self.current_month_spending / self.monthly_budget) * 100
#         return 0
    
#     @property
#     def remaining_budget(self):
#         """المتبقي من الميزانية"""
#         if self.monthly_budget:
#             return self.monthly_budget - self.current_month_spending
#         return 0

# class DailyExpense(models.Model):
#     """المصروفات اليومية"""
#     EXPENSE_TYPES = [
#         ('SALARIES', 'مرتبات'),
#         ('UTILITIES', 'مرافق'),
#         ('SUPPLIES', 'مستلزمات'),
#         ('MAINTENANCE', 'صيانة'),
#         ('MARKETING', 'دعاية'),
#         ('TRANSPORTATION', 'نقل'),
#         ('OTHER', 'أخرى'),
#     ]
    
#     expense_number = models.CharField(max_length=20, unique=True, verbose_name='رقم المصروف')
#     category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, verbose_name='التصنيف')
#     expense_type = models.CharField(max_length=15, choices=EXPENSE_TYPES, verbose_name='نوع المصروف')
    
#     description = models.TextField(verbose_name='وصف المصروف')
#     amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='المبلغ')
    
#     vendor_name = models.CharField(max_length=100, blank=True, verbose_name='اسم المورد')
#     invoice_number = models.CharField(max_length=50, blank=True, verbose_name='رقم الفاتورة')
    
#     expense_date = models.DateField(default=timezone.now, verbose_name='تاريخ المصروف')
#     transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, null=True, blank=True, verbose_name='العملية المالية')
    
#     created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='أنشأ بواسطة')
#     approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
#                                    related_name='approved_expenses', verbose_name='اعتمد بواسطة')
    
#     is_approved = models.BooleanField(default=False, verbose_name='معتمد')
#     created_at = models.DateTimeField(auto_now_add=True)
    
#     class Meta:
#         verbose_name = 'مصروف يومي'
#         verbose_name_plural = 'المصروفات اليومية'
#         ordering = ['-expense_date', '-created_at']
    
#     def __str__(self):
#         return f"{self.expense_number} - {self.description} - {self.amount}"
    
#     def save(self, *args, **kwargs):
#         if not self.expense_number:
#             self.expense_number = self.generate_expense_number()
#         super().save(*args, **kwargs)
    
#     def generate_expense_number(self):
#         from datetime import datetime
#         date_str = datetime.now().strftime('%Y%m%d')
#         count = DailyExpense.objects.filter(
#             expense_date=datetime.now().date()
#         ).count() + 1
#         return f"EXP{date_str}{count:04d}"

# class TreasurySnapshot(models.Model):
#     """لقطة يومية للخزنة"""
#     treasury = models.ForeignKey(Treasury, on_delete=models.CASCADE, verbose_name='الخزنة')
#     snapshot_date = models.DateField(verbose_name='تاريخ اللقطة')
#     opening_balance = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='الرصيد الافتتاحي')
#     closing_balance = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='الرصيد الختامي')
#     total_income = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي الإيرادات')
#     total_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي المصروفات')
#     transactions_count = models.IntegerField(default=0, verbose_name='عدد العمليات')
#     created_at = models.DateTimeField(auto_now_add=True)
    
#     class Meta:
#         verbose_name = 'لقطة الخزنة اليومية'
#         verbose_name_plural = 'لقطات الخزنة اليومية'
#         unique_together = ['treasury', 'snapshot_date']
#         ordering = ['-snapshot_date']
    
#     def __str__(self):
#         return f"{self.treasury.name} - {self.snapshot_date} - {self.closing_balance}"

# # نموذج للربط مع المدفوعات (سيتم تفعيله لاحقاً عند إنشاء تطبيق المدفوعات)
# class StudentPaymentTransaction(models.Model):
#     """ربط مدفوعات الطلاب بالنظام المحاسبي"""
#     # سيتم إلغاء التعليق عند إنشاء نموذج StudentPayment
#     # student_payment = models.OneToOneField('payments.StudentPayment', on_delete=models.CASCADE, verbose_name='دفعة الطالب')
#     transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, verbose_name='العملية المالية')
#     created_at = models.DateTimeField(auto_now_add=True)
    
#     class Meta:
#         verbose_name = 'عملية دفع طالب'
#         verbose_name_plural = 'عمليات دفع الطلاب'


# class TreasurySettings(models.Model):
#     """إعدادات نظام الخزينة"""

#     currency = models.CharField(max_length=10, default='EGP', verbose_name='العملة')
#     min_payment = models.DecimalField(max_digits=12, decimal_places=2, default=50, verbose_name='أقل مبلغ دفع')
#     max_payment = models.DecimalField(max_digits=12, decimal_places=2, default=5000, verbose_name='أكبر مبلغ دفع')
#     require_approval = models.BooleanField(default=False, verbose_name='يتطلب اعتماد العمليات')
#     enable_notifications = models.BooleanField(default=True, verbose_name='تفعيل التنبيهات')
#     report_language = models.CharField(
#         max_length=5,
#         choices=[('ar', 'العربية'), ('en', 'English')],
#         default='ar',
#         verbose_name='لغة التقارير'
#     )
#     date_format = models.CharField(max_length=20, default='d/m/Y', verbose_name='تنسيق التاريخ')

#     updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')
#     updated_by = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         verbose_name='آخر تعديل بواسطة'
#     )

#     class Meta:
#         verbose_name = 'إعدادات الخزينة'
#         verbose_name_plural = 'إعدادات الخزينة'

#     def __str__(self):
#         return 'إعدادات الخزينة'

#     @classmethod
#     def get_settings(cls):
#         obj, created = cls.objects.get_or_create(pk=1)
#         return obj