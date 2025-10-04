from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from school_settings.models import AcademicYear

class AccountCategory(models.Model):
    """تصنيفات الحسابات"""
    CATEGORY_TYPES = [
        ('REVENUE', 'إيرادات'),
        ('EXPENSE', 'مصروفات'),
        ('ASSET', 'أصول'),
        ('LIABILITY', 'خصوم'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='اسم التصنيف')
    category_type = models.CharField(max_length=15, choices=CATEGORY_TYPES, verbose_name='نوع التصنيف')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name='التصنيف الرئيسي')
    code = models.CharField(max_length=10, unique=True, verbose_name='كود التصنيف')
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
    category = models.ForeignKey(AccountCategory, on_delete=models.CASCADE, verbose_name='التصنيف')
    name = models.CharField(max_length=150, verbose_name='اسم الحساب')
    code = models.CharField(max_length=15, unique=True, verbose_name='كود الحساب')
    description = models.TextField(blank=True, verbose_name='وصف الحساب')
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الرصيد الافتتاحي')
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الرصيد الحالي')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'حساب مالي'
        verbose_name_plural = 'الحسابات المالية'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class Treasury(models.Model):
    """خزائن المدرسة"""
    name = models.CharField(max_length=100, verbose_name='اسم الخزنة')
    code = models.CharField(max_length=10, unique=True, verbose_name='كود الخزنة')
    account = models.OneToOneField(Account, on_delete=models.CASCADE, verbose_name='الحساب المالي')
    responsible_person = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='المسؤول')
    location = models.CharField(max_length=100, blank=True, verbose_name='الموقع')
    max_limit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name='الحد الأقصى')
    min_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الحد الأدنى')
    is_active = models.BooleanField(default=True, verbose_name='نشطة')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'خزنة'
        verbose_name_plural = 'الخزائن'
    
    def __str__(self):
        return f"{self.name} - الرصيد: {self.account.current_balance}"
    
    @property
    def current_balance(self):
        return self.account.current_balance

class Transaction(models.Model):
    """العمليات المالية"""
    TRANSACTION_TYPES = [
        ('INCOME', 'إيراد'),
        ('EXPENSE', 'مصروف'),
        ('TRANSFER', 'تحويل'),
    ]
    
    PAYMENT_METHODS = [
        ('CASH', 'نقدي'),
        ('BANK_TRANSFER', 'تحويل بنكي'),
        ('CHECK', 'شيك'),
        ('CREDIT_CARD', 'كارت ائتماني'),
        ('OTHER', 'أخرى'),
    ]
    
    transaction_number = models.CharField(max_length=20, unique=True, verbose_name='رقم العملية')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name='نوع العملية')
    treasury = models.ForeignKey(Treasury, on_delete=models.CASCADE, verbose_name='الخزنة')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name='الحساب')
    
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='المبلغ')
    description = models.TextField(verbose_name='وصف العملية')
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHODS, default='CASH', verbose_name='طريقة الدفع')
    
    # معلومات إضافية
    reference_number = models.CharField(max_length=50, blank=True, verbose_name='رقم المرجع')
    related_model = models.CharField(max_length=50, blank=True, verbose_name='النموذج المرتبط')
    related_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='معرف السجل المرتبط')
    
    # التواريخ والمستخدمين
    transaction_date = models.DateTimeField(default=timezone.now, verbose_name='تاريخ العملية')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, verbose_name='العام الدراسي')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='أنshأ بواسطة')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='approved_transactions', verbose_name='اعتمد بواسطة')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الاعتماد')
    
    # الحالة
    is_approved = models.BooleanField(default=False, verbose_name='معتمدة')
    is_cancelled = models.BooleanField(default=False, verbose_name='ملغية')
    cancellation_reason = models.TextField(blank=True, verbose_name='سبب الإلغاء')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'عملية مالية'
        verbose_name_plural = 'العمليات المالية'
        ordering = ['-transaction_date', '-created_at']
    
    def __str__(self):
        return f"{self.transaction_number} - {self.get_transaction_type_display()} - {self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.transaction_number:
            self.transaction_number = self.generate_transaction_number()
        super().save(*args, **kwargs)
    
    def generate_transaction_number(self):
        from datetime import datetime
        date_str = datetime.now().strftime('%Y%m%d')
        count = Transaction.objects.filter(
            transaction_date__date=datetime.now().date()
        ).count() + 1
        return f"TRX{date_str}{count:04d}"
    
    def approve(self, user):
        """اعتماد العملية"""
        if not self.is_approved:
            self.is_approved = True
            self.approved_by = user
            self.approved_at = timezone.now()
            self.save()
            
            # تحديث رصيد الحساب والخزنة
            self.update_balances()
    
    def cancel(self, reason, user):
        """إلغاء العملية"""
        if not self.is_cancelled and self.is_approved:
            # عكس العملية
            self.reverse_balances()
            
        self.is_cancelled = True
        self.cancellation_reason = reason
        self.save()
    
    def update_balances(self):
        """تحديث الأرصدة"""
        if self.transaction_type == 'INCOME':
            self.treasury.account.current_balance += self.amount
            self.account.current_balance += self.amount
        elif self.transaction_type == 'EXPENSE':
            self.treasury.account.current_balance -= self.amount
            self.account.current_balance -= self.amount
        
        self.treasury.account.save()
        self.account.save()
    
    def reverse_balances(self):
        """عكس تأثير العملية على الأرصدة"""
        if self.transaction_type == 'INCOME':
            self.treasury.account.current_balance -= self.amount
            self.account.current_balance -= self.amount
        elif self.transaction_type == 'EXPENSE':
            self.treasury.account.current_balance += self.amount
            self.account.current_balance += self.amount
        
        self.treasury.account.save()
        self.account.save()

# في treasury_management/models.py - تحديث نموذج ExpenseCategory
class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name='اسم التصنيف')
    code = models.CharField(max_length=20, unique=True, verbose_name='كود التصنيف')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name='الحساب المرتبط')
    description = models.TextField(blank=True, verbose_name='الوصف')
    monthly_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='الميزانية الشهرية')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    
    # إضافة هذه الحقول إذا لم تكن موجودة
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    
    class Meta:
        verbose_name = 'تصنيف المصروفات'
        verbose_name_plural = 'تصنيفات المصروفات'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def current_month_spending(self):
        """الإنفاق الحالي هذا الشهر"""
        from django.utils import timezone
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        try:
            total = self.dailyexpense_set.filter(
                expense_date__gte=month_start,
                is_approved=True
            ).aggregate(total=Sum('amount'))['total']
            return total or 0
        except:
            return 0
    
    @property
    def budget_percentage(self):
        """النسبة المئوية المستخدمة من الميزانية"""
        if self.monthly_budget and self.monthly_budget > 0:
            return (self.current_month_spending / self.monthly_budget) * 100
        return 0
    
    @property
    def remaining_budget(self):
        """المتبقي من الميزانية"""
        if self.monthly_budget:
            return self.monthly_budget - self.current_month_spending
        return 0

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
    
    expense_number = models.CharField(max_length=20, unique=True, verbose_name='رقم المصروف')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, verbose_name='التصنيف')
    expense_type = models.CharField(max_length=15, choices=EXPENSE_TYPES, verbose_name='نوع المصروف')
    
    description = models.TextField(verbose_name='وصف المصروف')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='المبلغ')
    
    vendor_name = models.CharField(max_length=100, blank=True, verbose_name='اسم المورد')
    invoice_number = models.CharField(max_length=50, blank=True, verbose_name='رقم الفاتورة')
    
    expense_date = models.DateField(default=timezone.now, verbose_name='تاريخ المصروف')
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, null=True, blank=True, verbose_name='العملية المالية')
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='أنشأ بواسطة')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='approved_expenses', verbose_name='اعتمد بواسطة')
    
    is_approved = models.BooleanField(default=False, verbose_name='معتمد')
    created_at = models.DateTimeField(auto_now_add=True)
    
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
    
    def generate_expense_number(self):
        from datetime import datetime
        date_str = datetime.now().strftime('%Y%m%d')
        count = DailyExpense.objects.filter(
            expense_date=datetime.now().date()
        ).count() + 1
        return f"EXP{date_str}{count:04d}"

class TreasurySnapshot(models.Model):
    """لقطة يومية للخزنة"""
    treasury = models.ForeignKey(Treasury, on_delete=models.CASCADE, verbose_name='الخزنة')
    snapshot_date = models.DateField(verbose_name='تاريخ اللقطة')
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='الرصيد الافتتاحي')
    closing_balance = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='الرصيد الختامي')
    total_income = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي الإيرادات')
    total_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي المصروفات')
    transactions_count = models.IntegerField(default=0, verbose_name='عدد العمليات')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'لقطة الخزنة اليومية'
        verbose_name_plural = 'لقطات الخزنة اليومية'
        unique_together = ['treasury', 'snapshot_date']
        ordering = ['-snapshot_date']
    
    def __str__(self):
        return f"{self.treasury.name} - {self.snapshot_date} - {self.closing_balance}"

# نموذج للربط مع المدفوعات (سيتم تفعيله لاحقاً عند إنشاء تطبيق المدفوعات)
class StudentPaymentTransaction(models.Model):
    """ربط مدفوعات الطلاب بالنظام المحاسبي"""
    # سيتم إلغاء التعليق عند إنشاء نموذج StudentPayment
    # student_payment = models.OneToOneField('payments.StudentPayment', on_delete=models.CASCADE, verbose_name='دفعة الطالب')
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, verbose_name='العملية المالية')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'عملية دفع طالب'
        verbose_name_plural = 'عمليات دفع الطلاب'
