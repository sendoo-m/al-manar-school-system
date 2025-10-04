# payments/models.py - النسخة النهائية النظيفة

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.conf import settings

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
    
    # العلاقات الأساسية
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, verbose_name="الطالب")
    
    # ربط بالعام الدراسي والمصروفات
    academic_year = models.ForeignKey('school_settings.AcademicYear', on_delete=models.CASCADE, 
                                    null=True, blank=True, verbose_name="العام الدراسي")
    fee_type = models.CharField(max_length=20, choices=FEE_TYPE_CHOICES, 
                               default='TUITION', verbose_name="نوع المصروفات")
    fee_name = models.CharField(max_length=100, blank=True, verbose_name="اسم المصروفات")
    
    # تفاصيل القسط
    installment_number = models.PositiveIntegerField(verbose_name="رقم القسط")
    amount_tuition = models.DecimalField(max_digits=10, decimal_places=2, 
                                       validators=[MinValueValidator(Decimal('0.01'))],
                                       verbose_name="مبلغ القسط المطلوب")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, 
                                    validators=[MinValueValidator(Decimal('0.00'))],
                                    verbose_name="المبلغ المدفوع")
    
    # الخصومات
    applied_discount = models.ForeignKey('school_settings.StudentDiscount', on_delete=models.SET_NULL,
                                       null=True, blank=True, verbose_name="الخصم المطبق")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                        validators=[MinValueValidator(Decimal('0.00'))],
                                        verbose_name="مبلغ الخصم")
    
    # تفاصيل الدفع
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, 
                                    default='cash', verbose_name="طريقة الدفع")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, 
                                    default='PENDING', verbose_name="حالة الدفع")
    payment_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الدفع")
    due_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الاستحقاق")
    
    # معلومات إضافية
    receipt_number = models.CharField(max_length=50, blank=True, verbose_name="رقم الإيصال")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    payment_user = models.CharField(max_length=100, blank=True, verbose_name="المحاسب")
    
    # تواريخ النظام
    created_date = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_date = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "قسط مدرسي"
        verbose_name_plural = "أقساط مدرسية"
        ordering = ['-payment_date', '-created_date']
        unique_together = ['student', 'fee_type', 'installment_number', 'academic_year']
    
    def __str__(self):
        return f"{self.student.name} - {self.get_fee_type_display()} - قسط #{self.installment_number}"
    
    @property
    def remaining_amount(self):
        return max(0, self.amount_tuition - self.amount_paid)
    
    @property
    def is_fully_paid(self):
        return self.amount_paid >= self.amount_tuition
    
    @property
    def is_overdue(self):
        if self.due_date and not self.is_fully_paid:
            return timezone.now().date() > self.due_date
        return False
    
    def update_payment_status(self):
        if self.amount_paid >= self.amount_tuition:
            self.payment_status = 'PAID'
        elif self.amount_paid > 0:
            self.payment_status = 'PARTIALLY_PAID'
        elif self.is_overdue:
            self.payment_status = 'OVERDUE'
        else:
            self.payment_status = 'PENDING'
    
    def save(self, *args, **kwargs):
        self.update_payment_status()
        
        if not self.receipt_number and self.payment_status == 'PAID':
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            self.receipt_number = f"REC-{self.student.id}-{timestamp}"
        
        super().save(*args, **kwargs)


class PaymentRecord(models.Model):
    """سجل المدفوعات"""
    tuition = models.ForeignKey(Tuition, on_delete=models.CASCADE, verbose_name="القسط")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="المبلغ المدفوع")
    payment_method = models.CharField(max_length=20, choices=Tuition.PAYMENT_METHOD_CHOICES, verbose_name="طريقة الدفع")
    payment_date = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الدفع")
    payment_user = models.CharField(max_length=100, verbose_name="المحاسب")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    
    class Meta:
        verbose_name = "سجل دفع"
        verbose_name_plural = "سجلات الدفع"
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.tuition} - {self.amount_paid} ج.م"


# في payments/models.py - تحديث نموذج Discount مع قيم افتراضية آمنة

# في payments/models.py - تحديث نموذج Discount ليكون آمناً

class Discount(models.Model):
    """نموذج الخصم - مع إعدادات آمنة للترقية"""
    
    student = models.ForeignKey(
        'students.Student', 
        on_delete=models.CASCADE, 
        null=True,  # السماح بـ null مؤقتاً
        blank=True,  # السماح بالفراغ
        verbose_name="الطالب"
    )
    
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="مبلغ الخصم"
    )
    
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        default=0,
        verbose_name="نسبة الخصم"
    )
    
    reason = models.TextField(
        default="خصم عام",
        blank=True,
        verbose_name="سبب الخصم"
    )
    
    academic_year = models.ForeignKey(
        'school_settings.AcademicYear', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        verbose_name="العام الدراسي"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_date = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    class Meta:
        verbose_name = "خصم"
        verbose_name_plural = "خصومات"
        ordering = ['-created_date']
    
    def __str__(self):
        student_name = self.student.name if self.student else "غير محدد"
        return f"{student_name} - خصم {self.discount_amount} ج.م"


# from django.db import models
# from django.utils import timezone
# from django.db.models import Sum
# from datetime import date
# from django.db.models import Q, Count
# from decimal import Decimal
# from django.core.validators import MinValueValidator

# # نموذج الأقساط الدراسية - لتتبع المدفوعات والأقساط لكل طالب مع تواريخ الاستحقاق

# # في payments/models.py - تصحيح الروابط

# from django.db import models
# from django.utils import timezone
# from django.core.validators import MinValueValidator, MaxValueValidator
# from decimal import Decimal
# from django.conf import settings

# class Tuition(models.Model):
#     """نموذج المدفوعات المحدث - مربوط بـ school_settings"""
#     PAYMENT_STATUS_CHOICES = (
#         ('PENDING', 'معلق'),
#         ('PAID', 'مدفوع'),
#         ('PARTIALLY_PAID', 'مدفوع جزئياً'),
#         ('OVERDUE', 'متأخر'),
#         ('CANCELLED', 'ملغي'),
#     )
    
#     PAYMENT_METHOD_CHOICES = (
#         ('cash', 'نقدي'),
#         ('transfer', 'تحويل بنكي'),
#         ('card', 'بطاقة ائتمان'),
#         ('check', 'شيك'),
#     )
    
#     FEE_TYPE_CHOICES = (
#         ('TUITION', 'مصروفات دراسية'),
#         ('BOOKS', 'مصروفات كتب'),
#         ('UNIFORMS', 'مصروفات ملابس'),
#         ('TRANSPORT', 'مصروفات نقل'),
#         ('MEALS', 'مصروفات وجبات'),
#         ('ACTIVITIES', 'مصروفات أنشطة'),
#         ('REGISTRATION', 'رسوم تسجيل'),
#         ('OTHER', 'مصروفات أخرى'),
#     )
    
#     # العلاقات الأساسية
#     student = models.ForeignKey('students.Student', on_delete=models.CASCADE, verbose_name="الطالب")
    
#     # ربط بالعام الدراسي والمصروفات - مصحح للتطبيق الصحيح
#     academic_year = models.ForeignKey('school_settings.AcademicYear', on_delete=models.CASCADE, 
#                                     null=True, blank=True, verbose_name="العام الدراسي")
#     fee_type = models.CharField(max_length=20, choices=FEE_TYPE_CHOICES, 
#                                default='TUITION', verbose_name="نوع المصروفات")
#     fee_name = models.CharField(max_length=100, blank=True, verbose_name="اسم المصروفات")
    
#     # تفاصيل القسط
#     installment_number = models.PositiveIntegerField(verbose_name="رقم القسط")
#     amount_tuition = models.DecimalField(max_digits=10, decimal_places=2, 
#                                        validators=[MinValueValidator(Decimal('0.01'))],
#                                        verbose_name="مبلغ القسط المطلوب")
#     amount_paid = models.DecimalField(max_digits=10, decimal_places=2, 
#                                     validators=[MinValueValidator(Decimal('0.00'))],
#                                     verbose_name="المبلغ المدفوع")
    
#     # الخصومات - مصحح للتطبيق الصحيح
#     applied_discount = models.ForeignKey('school_settings.StudentDiscount', on_delete=models.SET_NULL,
#                                        null=True, blank=True, verbose_name="الخصم المطبق")
#     discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,
#                                         validators=[MinValueValidator(Decimal('0.00'))],
#                                         verbose_name="مبلغ الخصم")
    
#     # تفاصيل الدفع
#     payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, 
#                                     default='cash', verbose_name="طريقة الدفع")
#     payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, 
#                                     default='PENDING', verbose_name="حالة الدفع")
#     payment_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الدفع")
#     due_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الاستحقاق")
    
#     # معلومات إضافية
#     receipt_number = models.CharField(max_length=50, blank=True, verbose_name="رقم الإيصال")
#     notes = models.TextField(blank=True, verbose_name="ملاحظات")
#     payment_user = models.CharField(max_length=100, blank=True, verbose_name="المحاسب")
    
#     # تواريخ النظام
#     created_date = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
#     updated_date = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
#     class Meta:
#         verbose_name = "قسط مدرسي"
#         verbose_name_plural = "أقساط مدرسية"
#         ordering = ['-payment_date', '-created_date']
#         unique_together = ['student', 'fee_type', 'installment_number', 'academic_year']
    
#     def __str__(self):
#         return f"{self.student.name} - {self.get_fee_type_display()} - قسط #{self.installment_number}"
    
#     @property
#     def remaining_amount(self):
#         return max(0, self.amount_tuition - self.amount_paid)
    
#     @property
#     def is_fully_paid(self):
#         return self.amount_paid >= self.amount_tuition
    
#     @property
#     def is_overdue(self):
#         if self.due_date and not self.is_fully_paid:
#             return timezone.now().date() > self.due_date
#         return False
    
#     def update_payment_status(self):
#         if self.amount_paid >= self.amount_tuition:
#             self.payment_status = 'PAID'
#         elif self.amount_paid > 0:
#             self.payment_status = 'PARTIALLY_PAID'
#         elif self.is_overdue:
#             self.payment_status = 'OVERDUE'
#         else:
#             self.payment_status = 'PENDING'
    
#     def save(self, *args, **kwargs):
#         self.update_payment_status()
        
#         if not self.receipt_number and self.payment_status == 'PAID':
#             from datetime import datetime
#             timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
#             self.receipt_number = f"REC-{self.student.id}-{timestamp}"
        
#         super().save(*args, **kwargs)



# # إزالة النماذج المكررة وإبقاء هذا فقط
# class PaymentRecord(models.Model):
#     """سجل المدفوعات - نسخة واحدة فقط"""
#     tuition = models.ForeignKey(Tuition, on_delete=models.CASCADE, verbose_name="القسط")
#     amount_paid = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="المبلغ المدفوع")
#     payment_method = models.CharField(max_length=20, choices=Tuition.PAYMENT_METHOD_CHOICES, verbose_name="طريقة الدفع")
#     payment_date = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الدفع")
#     payment_user = models.CharField(max_length=100, verbose_name="المحاسب")
#     notes = models.TextField(blank=True, verbose_name="ملاحظات")
    
#     class Meta:
#         verbose_name = "سجل دفع"
#         verbose_name_plural = "سجلات الدفع"
#         ordering = ['-payment_date']
    
#     def __str__(self):
#         return f"{self.tuition} - {self.amount_paid} ج.م"


# # إبقاء نموذج Discount واحد فقط
# class Discount(models.Model):
#     """نموذج الخصم - نسخة واحدة فقط"""
#     student = models.ForeignKey('students.Student', on_delete=models.CASCADE, verbose_name="الطالب")
#     discount_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="مبلغ الخصم")
#     discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="نسبة الخصم")
#     reason = models.TextField(verbose_name="سبب الخصم")
#     academic_year = models.ForeignKey('school_settings.AcademicYear', on_delete=models.CASCADE, 
#                                     null=True, blank=True, verbose_name="العام الدراسي")
#     is_active = models.BooleanField(default=True, verbose_name="نشط")
#     created_date = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
#     class Meta:
#         verbose_name = "خصم"
#         verbose_name_plural = "خصومات"
#         ordering = ['-created_date']
    
#     def __str__(self):
#         return f"{self.student.name} - خصم {self.discount_amount} ج.م"


# # إضافة نماذج إضافية آمنة
# class PaymentSettings(models.Model):
#     """إعدادات المدفوعات"""
#     late_payment_penalty_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة غرامة التأخير %")
#     grace_period_days = models.IntegerField(default=7, verbose_name="فترة السماح (أيام)")
#     allow_partial_payments = models.BooleanField(default=True, verbose_name="السماح بالدفع الجزئي")
#     require_receipt_number = models.BooleanField(default=True, verbose_name="تطلب رقم إيصال")
    
#     created_date = models.DateTimeField(auto_now_add=True)
#     updated_date = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         verbose_name = "إعدادات المدفوعات"
#         verbose_name_plural = "إعدادات المدفوعات"
    
#     def __str__(self):
#         return "إعدادات المدفوعات"
    
#     @classmethod
#     def get_current_settings(cls):
#         settings_obj, created = cls.objects.get_or_create(pk=1)
#         return settings_obj


# class OverdueTracking(models.Model):
#     """تتبع المتأخرات"""
#     student = models.ForeignKey('students.Student', on_delete=models.CASCADE, verbose_name="الطالب")
#     tuition = models.ForeignKey(Tuition, on_delete=models.CASCADE, verbose_name="القسط")
#     days_overdue = models.IntegerField(verbose_name="أيام التأخير")
#     penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="مبلغ الغرامة")
#     notification_sent = models.BooleanField(default=False, verbose_name="تم إرسال التنبيه")
#     last_notification_date = models.DateTimeField(null=True, blank=True, verbose_name="آخر تنبيه")
    
#     created_date = models.DateTimeField(auto_now_add=True)
#     updated_date = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         verbose_name = "تتبع متأخر"
#         verbose_name_plural = "تتبع المتأخرات"
#         unique_together = ['student', 'tuition']
    
#     def __str__(self):
#         return f"{self.student.name} - متأخر {self.days_overdue} أيام"

# # نموذج إعدادات المدفوعات
# class PaymentSettings(models.Model):
#     late_payment_penalty_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="معدل غرامة التأخير (%)")
#     grace_period_days = models.IntegerField(default=7, verbose_name="فترة السماح (أيام)")
#     default_installments_count = models.IntegerField(default=10, verbose_name="عدد الأقساط الافتراضي")
#     auto_generate_installments = models.BooleanField(default=True, verbose_name="إنشاء أقساط تلقائي")
#     currency_symbol = models.CharField(max_length=5, default='ج.م', verbose_name="رمز العملة")
    
#     def __str__(self):
#         return "إعدادات المدفوعات"
    
#     class Meta:
#         verbose_name = "إعدادات المدفوعات"
#         verbose_name_plural = "إعدادات المدفوعات"


# # نموذج تتبع المتأخرات
# class OverdueTracking(models.Model):
#     student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
#     total_overdue_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="إجمالي المتأخرات")
#     overdue_count = models.IntegerField(verbose_name="عدد الأقساط المتأخرة")
#     last_payment_date = models.DateField(null=True, blank=True, verbose_name="تاريخ آخر دفع")
#     notification_sent = models.BooleanField(default=False, verbose_name="تم إرسال تنبيه")
#     last_notification_date = models.DateTimeField(null=True, blank=True)
#     created_date = models.DateTimeField(default=timezone.now)
#     updated_date = models.DateTimeField(auto_now=True)
    
#     def __str__(self):
#         return f"متأخرات {self.student.name} - {self.total_overdue_amount} ج.م"
    
#     class Meta:
#         ordering = ['-total_overdue_amount']

# # payments/models.py - إضافة بسيطة في نهاية الملف
# # ... الكود الموجود كما هو ...

# # إضافة في نهاية الملف:
# class PaymentSummary(models.Model):
#     """ملخص يومي للمدفوعات - للتحسين والسرعة"""
#     date = models.DateField(unique=True, verbose_name="التاريخ")
#     total_payments = models.IntegerField(default=0, verbose_name="عدد المدفوعات")
#     total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="إجمالي المبلغ")
#     cash_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="المدفوعات النقدية")
#     transfer_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="التحويلات البنكية")
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         verbose_name = "ملخص المدفوعات اليومي"
#         verbose_name_plural = "ملخصات المدفوعات اليومية"
#         ordering = ['-date']
    
#     def __str__(self):
#         return f"ملخص {self.date} - {self.total_amount} ج.م"
    
#     @classmethod
#     def generate_summary(cls, target_date):
#         """إنشاء ملخص ليوم محدد"""
#         payments = Tuition.objects.filter(
#             payment_date__date=target_date,
#             payment_status='PAID'
#         )
        
#         summary_data = payments.aggregate(
#             total_payments=Count('id'),
#             total_amount=Sum('amount_paid'),
#             cash_amount=Sum('amount_paid', filter=Q(payment_method='cash')),
#             transfer_amount=Sum('amount_paid', filter=Q(payment_method='transfer'))
#         )
        
#         summary, created = cls.objects.get_or_create(
#             date=target_date,
#             defaults={
#                 'total_payments': summary_data['total_payments'] or 0,
#                 'total_amount': summary_data['total_amount'] or Decimal('0'),
#                 'cash_amount': summary_data['cash_amount'] or Decimal('0'),
#                 'transfer_amount': summary_data['transfer_amount'] or Decimal('0'),
#             }
#         )
        
#         if not created:
#             # تحديث البيانات إذا كانت موجودة
#             summary.total_payments = summary_data['total_payments'] or 0
#             summary.total_amount = summary_data['total_amount'] or Decimal('0')
#             summary.cash_amount = summary_data['cash_amount'] or Decimal('0')
#             summary.transfer_amount = summary_data['transfer_amount'] or Decimal('0')
#             summary.save()
        
#         return summary
