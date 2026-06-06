# payments/models.py
# نسخة نظيفة وآمنة لتطبيق المدفوعات

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Tuition(models.Model):
    """نموذج المدفوعات الرئيسي"""

    PAYMENT_STATUS_CHOICES = (
        ('PENDING', 'معلق'),
        ('PAID', 'مدفوع'),
        ('PARTIALLY_PAID', 'مدفوع جزئياً'),
        ('OVERDUE', 'متأخر'),
        ('CANCELLED', 'ملغي'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('cash', 'نقدي'),
        ('transfer', 'تحويل بنكي'),
        ('card', 'بطاقة ائتمان'),
        ('check', 'شيك'),
    )

    FEE_TYPE_CHOICES = (
        ('TUITION', 'مصروفات دراسية'),
        ('BOOKS', 'مصروفات كتب'),
        ('UNIFORMS', 'مصروفات ملابس'),
        ('TRANSPORT', 'مصروفات نقل'),
        ('MEALS', 'مصروفات وجبات'),
        ('ACTIVITIES', 'مصروفات أنشطة'),
        ('REGISTRATION', 'رسوم تسجيل'),
        ('OTHER', 'مصروفات أخرى'),
    )

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='tuition_payments',
        verbose_name='الطالب',
    )

    academic_year = models.ForeignKey(
        'school_settings.AcademicYear',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tuition_payments',
        verbose_name='العام الدراسي',
    )

    fee_type = models.CharField(
        max_length=20,
        choices=FEE_TYPE_CHOICES,
        default='TUITION',
        verbose_name='نوع المصروفات',
    )

    fee_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='اسم المصروفات',
    )

    installment_number = models.PositiveIntegerField(
        verbose_name='رقم القسط',
    )

    amount_tuition = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='مبلغ القسط المطلوب',
    )

    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='المبلغ المدفوع',
    )

    applied_discount = models.ForeignKey(
        'school_settings.StudentDiscount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tuition_payments',
        verbose_name='الخصم المطبق',
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='مبلغ الخصم',
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash',
        verbose_name='طريقة الدفع',
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING',
        verbose_name='حالة الدفع',
    )

    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ الدفع',
    )

    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='تاريخ الاستحقاق',
    )

    receipt_number = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        verbose_name='رقم الإيصال',
    )

    notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات',
    )

    payment_user = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='المحاسب',
    )

    created_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء',
    )

    updated_date = models.DateTimeField(
        auto_now=True,
        verbose_name='تاريخ التحديث',
    )

    class Meta:
        verbose_name = 'قسط مدرسي'
        verbose_name_plural = 'أقساط مدرسية'
        ordering = ['-payment_date', '-created_date']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'fee_type', 'installment_number', 'academic_year'],
                name='unique_student_fee_installment_year',
            )
        ]
        indexes = [
            models.Index(fields=['student', 'academic_year']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['fee_type']),
        ]

    def __str__(self):
        student_name = self.student.name if self.student else 'طالب غير محدد'
        return f'{student_name} - {self.get_fee_type_display()} - قسط #{self.installment_number}'

    @property
    def remaining_amount(self):
        amount_tuition = self.amount_tuition or Decimal('0.00')
        amount_paid = self.amount_paid or Decimal('0.00')
        remaining = amount_tuition - amount_paid
        return max(Decimal('0.00'), remaining)

    @property
    def is_fully_paid(self):
        return (self.amount_paid or Decimal('0.00')) >= (self.amount_tuition or Decimal('0.00'))

    @property
    def is_partially_paid(self):
        return Decimal('0.00') < (self.amount_paid or Decimal('0.00')) < (self.amount_tuition or Decimal('0.00'))

    @property
    def is_overdue(self):
        if self.due_date and not self.is_fully_paid and self.payment_status != 'CANCELLED':
            return timezone.now().date() > self.due_date
        return False

    def update_payment_status(self):
        if self.payment_status == 'CANCELLED':
            return

        if self.amount_paid >= self.amount_tuition:
            self.payment_status = 'PAID'
        elif self.amount_paid > 0:
            self.payment_status = 'PARTIALLY_PAID'
        elif self.is_overdue:
            self.payment_status = 'OVERDUE'
        else:
            self.payment_status = 'PENDING'

    def generate_receipt_number(self):
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        student_id = self.student_id or '0'
        return f'REC-{student_id}-{timestamp}'

    # def save(self, *args, **kwargs):
    #     self.amount_paid = self.amount_paid or Decimal('0.00')
    #     self.discount_amount = self.discount_amount or Decimal('0.00')

    #     self.update_payment_status()

    #     if self.amount_paid > 0 and not self.payment_date:
    #         self.payment_date = timezone.now()

    #     if not self.receipt_number and self.amount_paid > 0:
    #         self.receipt_number = self.generate_receipt_number()

    #     super().save(*args, **kwargs)
    def save(self, *args, **kwargs):
        self.update_payment_status()

        if not self.receipt_number and self.amount_paid and self.amount_paid > 0:
            try:
                settings_obj = PaymentSettings.get_settings()

                if settings_obj.auto_generate_receipt_number:
                    from datetime import datetime
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    prefix = settings_obj.receipt_prefix or 'REC'
                    student_id = self.student.id if self.student else '0'
                    self.receipt_number = f"{prefix}-{student_id}-{timestamp}"

            except Exception:
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                student_id = self.student.id if self.student else '0'
                self.receipt_number = f"REC-{student_id}-{timestamp}"

        super().save(*args, **kwargs)
        
        self.sync_student_payment_totals()

    def sync_student_payment_totals(self):
        """
        تحديث الحقول المالية داخل Student بعد كل حفظ.
        هذا يحافظ على توافق تطبيق الطلاب مع المدفوعات.
        """
        if not self.student_id:
            return

        student = self.student

        total_paid = Tuition.objects.filter(
            student=student,
        ).exclude(
            payment_status='CANCELLED',
        ).aggregate(
            total=Sum('amount_paid')
        )['total'] or Decimal('0.00')

        total_required = Tuition.objects.filter(
            student=student,
        ).exclude(
            payment_status='CANCELLED',
        ).aggregate(
            total=Sum('amount_tuition')
        )['total'] or Decimal('0.00')

        total_owed = max(Decimal('0.00'), total_required - total_paid)

        update_fields = []

        if hasattr(student, 'total_payments'):
            student.total_payments = total_paid
            update_fields.append('total_payments')

        if hasattr(student, 'total_fees'):
            student.total_fees = total_required
            update_fields.append('total_fees')

        if hasattr(student, 'total_owed'):
            student.total_owed = total_owed
            update_fields.append('total_owed')

        if hasattr(student, 'updated_at'):
            update_fields.append('updated_at')

        if update_fields:
            student.save(update_fields=update_fields)


class PaymentRecord(models.Model):
    """سجل المدفوعات"""

    tuition = models.ForeignKey(
        Tuition,
        on_delete=models.CASCADE,
        related_name='payment_records',
        verbose_name='القسط',
    )

    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='المبلغ المدفوع',
    )

    payment_method = models.CharField(
        max_length=20,
        choices=Tuition.PAYMENT_METHOD_CHOICES,
        verbose_name='طريقة الدفع',
    )

    payment_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الدفع',
    )

    payment_user = models.CharField(
        max_length=100,
        verbose_name='المحاسب',
    )

    notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات',
    )

    class Meta:
        verbose_name = 'سجل دفع'
        verbose_name_plural = 'سجلات الدفع'
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['payment_date']),
            models.Index(fields=['payment_method']),
        ]

    def __str__(self):
        return f'{self.tuition} - {self.amount_paid} ج.م'


class Discount(models.Model):
    """نموذج خصم بسيط داخل تطبيق المدفوعات"""

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payment_discounts',
        verbose_name='الطالب',
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='مبلغ الخصم',
    )

    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='نسبة الخصم',
    )

    reason = models.TextField(
        default='خصم عام',
        blank=True,
        verbose_name='سبب الخصم',
    )

    academic_year = models.ForeignKey(
        'school_settings.AcademicYear',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payment_discounts',
        verbose_name='العام الدراسي',
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط',
    )

    created_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء',
    )

    class Meta:
        verbose_name = 'خصم'
        verbose_name_plural = 'خصومات'
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['student', 'academic_year']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        student_name = self.student.name if self.student else 'غير محدد'
        return f'{student_name} - خصم {self.discount_amount} ج.م'

    def calculate_discount(self, base_amount):
        base_amount = Decimal(str(base_amount or 0))

        if self.discount_amount and self.discount_amount > 0:
            return min(self.discount_amount, base_amount)

        if self.discount_percentage and self.discount_percentage > 0:
            calculated = base_amount * (self.discount_percentage / Decimal('100'))
            return min(calculated, base_amount)

        return Decimal('0.00')
    


class PaymentSettings(models.Model):
    """إعدادات نظام المدفوعات"""

    school_name_ar = models.CharField(
        max_length=200,
        default='مدرسة المنار الخاصة للغات',
        verbose_name='اسم المدرسة بالعربية'
    )

    school_name_en = models.CharField(
        max_length=200,
        default='Al-Manar Private Language School',
        verbose_name='اسم المدرسة بالإنجليزية'
    )

    receipt_prefix = models.CharField(
        max_length=20,
        default='REC',
        verbose_name='بادئة رقم الإيصال'
    )

    receipt_footer_text = models.TextField(
        default='هذا إيصال رسمي صادر من نظام إدارة المدفوعات. يرجى الاحتفاظ به كمرجع.',
        blank=True,
        verbose_name='نص أسفل الإيصال'
    )

    default_payment_method = models.CharField(
        max_length=20,
        choices=Tuition.PAYMENT_METHOD_CHOICES,
        default='cash',
        verbose_name='طريقة الدفع الافتراضية'
    )

    daily_collection_target = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=10000,
        verbose_name='هدف التحصيل اليومي'
    )

    monthly_collection_target = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=300000,
        verbose_name='هدف التحصيل الشهري'
    )

    allow_overpayment = models.BooleanField(
        default=False,
        verbose_name='السماح بدفع مبلغ أكبر من المطلوب'
    )

    auto_generate_receipt_number = models.BooleanField(
        default=True,
        verbose_name='توليد رقم الإيصال تلقائيًا'
    )

    show_school_name_on_receipt = models.BooleanField(
        default=True,
        verbose_name='إظهار اسم المدرسة في الإيصال'
    )

    show_payment_records_on_receipt = models.BooleanField(
        default=True,
        verbose_name='إظهار سجل الدفعات في الإيصال'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر تحديث'
    )

    class Meta:
        verbose_name = 'إعدادات المدفوعات'
        verbose_name_plural = 'إعدادات المدفوعات'

    def __str__(self):
        return 'إعدادات المدفوعات'

    @classmethod
    def get_settings(cls):
        settings_obj, created = cls.objects.get_or_create(pk=1)
        return settings_obj

