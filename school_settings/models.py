from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q
from django.urls import reverse
import datetime
import json
import logging

# نموذج إعدادات النظام العامة - مُصحح
class SystemSettings(models.Model):
    # معلومات المدرسة الأساسية
    school_name = models.CharField(max_length=200, default="مدرسة المنار", verbose_name="اسم المدرسة")
    school_name_en = models.CharField(max_length=200, default="Al-Manar School", verbose_name="اسم المدرسة بالإنجليزية")
    school_logo = models.ImageField(upload_to='school_settings/logos/', null=True, blank=True, verbose_name="شعار المدرسة")
    school_stamp = models.ImageField(upload_to='school_settings/stamps/', null=True, blank=True, verbose_name="ختم المدرسة")
    
    # معلومات الاتصال
    school_address = models.TextField(default="", blank=True, verbose_name="عنوان المدرسة")
    school_phone = models.CharField(max_length=20, default="", blank=True, verbose_name="هاتف المدرسة")
    school_fax = models.CharField(max_length=20, blank=True, verbose_name="فاكس المدرسة")
    school_email = models.EmailField(default="", blank=True, verbose_name="بريد إلكتروني")
    school_website = models.URLField(blank=True, verbose_name="موقع المدرسة")
    
    # العملة والإعدادات المالية
    currency_symbol = models.CharField(max_length=10, default="ج.م", verbose_name="رمز العملة")
    currency_name = models.CharField(max_length=50, default="جنيه مصري", verbose_name="اسم العملة")
    
    # إعدادات الأقساط
    default_installments_count = models.IntegerField(default=4, verbose_name="عدد الأقساط الافتراضي")
    late_payment_penalty_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة غرامة التأخير %")
    grace_period_days = models.IntegerField(default=7, verbose_name="فترة السماح (أيام)")
    
    # إعدادات النظام
    system_language = models.CharField(max_length=10, choices=[('ar', 'العربية'), ('en', 'English')], default='ar', verbose_name="لغة النظام")
    max_students_per_classroom = models.IntegerField(default=30, verbose_name="الحد الأقصى للطلاب بالفصل")
    
    # معلومات إضافية للإيصالات
    receipt_footer_text = models.TextField(default="شكراً لكم على ثقتكم بنا", verbose_name="نص تذييل الإيصالات")
    receipt_terms = models.TextField(blank=True, verbose_name="شروط وأحكام الإيصالات")
    
    # تواريخ التحديث - مُصحح
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,  # تغيير من CASCADE إلى SET_NULL
        null=True,  # السماح بالقيمة الفارغة
        blank=True,  # السماح بالفراغ في النماذج
        verbose_name="محدث بواسطة"
    )
    
    class Meta:
        verbose_name = "إعدادات النظام"
        verbose_name_plural = "إعدادات النظام"
    
    def __str__(self):
        return f"إعدادات {self.school_name}"
    
    @classmethod
    def get_current_settings(cls):
        """الحصول على الإعدادات الحالية أو إنشاؤها"""
        try:
            settings_obj = cls.objects.first()
            if not settings_obj:
                # إنشاء إعدادات افتراضية
                settings_obj = cls.objects.create(
                    school_name="مدرسة المنار",
                    school_name_en="Al-Manar School",
                    school_address="العنوان غير محدد",
                    school_phone="غير محدد",
                    school_email="info@almanar.edu",
                    currency_symbol="ج.م",
                    currency_name="جنيه مصري",
                    updated_by=None  # لا يوجد مستخدم عند الإنشاء الأول
                )
            return settings_obj
        except Exception as e:
            print(f"خطأ في الحصول على الإعدادات: {e}")
            # إنشاء إعدادات افتراضية حتى لو حدث خطأ
            return cls(
                school_name="مدرسة المنار",
                school_name_en="Al-Manar School",
                school_address="العنوان غير محدد",
                school_phone="غير محدد",
                school_email="info@almanar.edu",
                currency_symbol="ج.م",
                currency_name="جنيه مصري"
            )


# في school_settings/models.py - إضافة في نموذج AcademicYear

class AcademicYear(models.Model):
    name = models.CharField(max_length=20, verbose_name="العام الدراسي", help_text="مثال: 2024-2025")
    start_date = models.DateField(verbose_name="تاريخ البداية")
    end_date = models.DateField(verbose_name="تاريخ النهاية")
    is_current = models.BooleanField(default=False, verbose_name="العام الحالي")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    # إعدادات الفصول الدراسية
    first_term_start = models.DateField(verbose_name="بداية الفصل الأول")
    first_term_end = models.DateField(verbose_name="نهاية الفصل الأول")
    second_term_start = models.DateField(verbose_name="بداية الفصل الثاني")
    second_term_end = models.DateField(verbose_name="نهاية الفصل الثاني")
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "العام الدراسي"
        verbose_name_plural = "الأعوام الدراسية"
        ordering = ['-start_date']
    
    def __str__(self):
        return self.name
    
    # ===================================
    # 📊 الخصائص المحسوبة الجديدة
    # ===================================
    
    @property
    def students_count(self):
        """عدد الطلاب في هذا العام الدراسي"""
        try:
            from students.models import Student
            return Student.objects.filter(
                academic_year=self,
                is_active=True
            ).count()
        except ImportError:
            return 0
    
    @property
    def total_students(self):
        """مرادف لـ students_count"""
        return self.students_count
    
    @property
    def male_students_count(self):
        """عدد الطلاب الذكور"""
        try:
            from students.models import Student
            return Student.objects.filter(
                academic_year=self,
                gender='M',
                is_active=True
            ).count()
        except ImportError:
            return 0
    
    @property
    def female_students_count(self):
        """عدد الطالبات الإناث"""
        try:
            from students.models import Student
            return Student.objects.filter(
                academic_year=self,
                gender='F',
                is_active=True
            ).count()
        except ImportError:
            return 0
    
    @property
    def fees_settings_count(self):
        """عدد إعدادات المصروفات المرتبطة بهذا العام"""
        try:
            return self.schoolfeessettings_set.filter(is_active=True).count()
        except:
            return 0
    
    @property
    def duration_days(self):
        """مدة العام الدراسي بالأيام"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None
    
    @property
    def first_term_duration(self):
        """مدة الفصل الأول بالأيام"""
        if self.first_term_start and self.first_term_end:
            return (self.first_term_end - self.first_term_start).days
        return None
    
    @property
    def second_term_duration(self):
        """مدة الفصل الثاني بالأيام"""
        if self.second_term_start and self.second_term_end:
            return (self.second_term_end - self.second_term_start).days
        return None
    
    @property
    def total_fees_amount(self):
        """إجمالي المبلغ المطلوب من جميع الطلاب"""
        try:
            from students.models import Student
            from django.db.models import Sum
            result = Student.objects.filter(
                academic_year=self,
                is_active=True
            ).aggregate(total=Sum('total_fees'))
            return result['total'] or 0
        except ImportError:
            return 0
    
    @property
    def total_payments_received(self):
        """إجمالي المدفوعات المحصلة"""
        try:
            from students.models import Student
            from django.db.models import Sum
            result = Student.objects.filter(
                academic_year=self,
                is_active=True
            ).aggregate(total=Sum('total_payments'))
            return result['total'] or 0
        except ImportError:
            return 0
    
    @property
    def total_outstanding(self):
        """إجمالي المبالغ المستحقة"""
        try:
            from students.models import Student
            from django.db.models import Sum
            result = Student.objects.filter(
                academic_year=self,
                is_active=True
            ).aggregate(total=Sum('total_owed'))
            return result['total'] or 0
        except ImportError:
            return 0
    
    @property
    def collection_percentage(self):
        """نسبة التحصيل"""
        if self.total_fees_amount > 0:
            return (self.total_payments_received / self.total_fees_amount) * 100
        return 0
    
    @property
    def grades_count(self):
        """عدد الصفوف التي لديها إعدادات مصروفات في هذا العام"""
        try:
            return self.schoolfeessettings_set.values('grade_level').distinct().count()
        except:
            return 0
    
    def get_students_by_grade(self):
        """الحصول على توزيع الطلاب حسب الصفوف"""
        try:
            from students.models import Student
            from django.db.models import Count
            
            return Student.objects.filter(
                academic_year=self,
                is_active=True
            ).values(
                'grade_level__name',
                'grade_level__education_level__name'
            ).annotate(
                count=Count('id')
            ).order_by('grade_level__education_level__order', 'grade_level__order')
        except ImportError:
            return []
    
    def get_financial_summary(self):
        """ملخص مالي شامل للعام الدراسي"""
        return {
            'total_students': self.students_count,
            'total_fees': float(self.total_fees_amount),
            'total_payments': float(self.total_payments_received),
            'total_outstanding': float(self.total_outstanding),
            'collection_percentage': round(self.collection_percentage, 2),
            'fees_settings_count': self.fees_settings_count,
        }
    
    @classmethod
    def get_current_year(cls):
        try:
            return cls.objects.filter(is_current=True, is_active=True).first()
        except Exception:
            return None
    
    def save(self, *args, **kwargs):
        if self.is_current:
            # إلغاء تفعيل العام الحالي السابق
            AcademicYear.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


# نموذج المراحل التعليمية (ابتدائي، إعدادي، ثانوي)
class EducationLevel(models.Model):
    name = models.CharField(max_length=50, verbose_name="المرحلة التعليمية")
    name_en = models.CharField(max_length=50, blank=True, verbose_name="المرحلة بالإنجليزية")
    description = models.TextField(blank=True, verbose_name="وصف المرحلة")
    min_age = models.IntegerField(verbose_name="العمر الأدنى")
    max_age = models.IntegerField(verbose_name="العمر الأقصى")
    order = models.PositiveIntegerField(verbose_name="ترتيب العرض", help_text="لترتيب المراحل في القوائم")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    class Meta:
        verbose_name = "المرحلة التعليمية"
        verbose_name_plural = "المراحل التعليمية"
        ordering = ['order']
    
    def __str__(self):
        return self.name


# نموذج الصفوف الدراسية
class GradeLevel(models.Model):
    education_level = models.ForeignKey(EducationLevel, on_delete=models.CASCADE, verbose_name="المرحلة التعليمية")
    name = models.CharField(max_length=50, verbose_name="اسم الصف")
    name_en = models.CharField(max_length=50, blank=True, verbose_name="اسم الصف بالإنجليزية")
    grade_number = models.IntegerField(verbose_name="رقم الصف", help_text="مثال: 1 للصف الأول")
    typical_age = models.IntegerField(verbose_name="العمر المعتاد")
    order = models.PositiveIntegerField(verbose_name="ترتيب العرض")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    class Meta:
        verbose_name = "الصف الدراسي"
        verbose_name_plural = "الصفوف الدراسية"
        ordering = ['education_level__order', 'order']
        unique_together = ['education_level', 'grade_number']
    
    def __str__(self):
        return f"{self.education_level.name} - {self.name}"


# نموذج إعدادات المصاريف المدرسية
class SchoolFeesSettings(models.Model):
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
    
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, verbose_name="العام الدراسي")
    grade_level = models.ForeignKey(GradeLevel, on_delete=models.CASCADE, verbose_name="الصف الدراسي")
    
    # أنواع المصروفات
    fee_type = models.CharField(max_length=20, choices=FEE_TYPE_CHOICES, verbose_name="نوع المصروفات")
    fee_name = models.CharField(max_length=100, verbose_name="اسم المصروفات")
    
    # المبالغ
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="المبلغ الإجمالي")
    installments_count = models.IntegerField(default=4, validators=[MinValueValidator(1), MaxValueValidator(12)], 
                                           verbose_name="عدد الأقساط")
    installment_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="مبلغ القسط")
    
    # تواريخ الاستحقاق
    first_installment_due_date = models.DateField(verbose_name="تاريخ استحقاق القسط الأول")
    installment_interval_days = models.IntegerField(default=30, verbose_name="فترة بين الأقساط (أيام)")
    
    # إعدادات إضافية
    is_mandatory = models.BooleanField(default=True, verbose_name="إجباري")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "إعدادات المصروفات"
        verbose_name_plural = "إعدادات المصروفات"
        unique_together = ['academic_year', 'grade_level', 'fee_type']
    
    def __str__(self):
        return f"{self.fee_name} - {self.grade_level} - {self.academic_year}"
    
    def save(self, *args, **kwargs):
        # حساب مبلغ القسط تلقائياً
        if self.total_amount and self.installments_count:
            self.installment_amount = self.total_amount / self.installments_count
        super().save(*args, **kwargs)


# نموذج إعدادات الخصومات
class DiscountSettings(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('PERCENTAGE', 'نسبة مئوية'),
        ('FIXED_AMOUNT', 'مبلغ ثابت'),
    )
    
    DISCOUNT_CATEGORY_CHOICES = (
        ('SIBLING', 'خصم الأشقاء'),
        ('FINANCIAL_HARDSHIP', 'خصم الحالة المالية'),
        ('ACADEMIC_EXCELLENCE', 'خصم التفوق الأكاديمي'),
        ('STAFF_CHILDREN', 'خصم أبناء الموظفين'),
        ('EARLY_PAYMENT', 'خصم الدفع المبكر'),
        ('LOYALTY', 'خصم الولاء'),
        ('OTHER', 'خصومات أخرى'),
    )
    
    name = models.CharField(max_length=100, verbose_name="اسم الخصم")
    category = models.CharField(max_length=20, choices=DISCOUNT_CATEGORY_CHOICES, verbose_name="فئة الخصم")
    discount_type = models.CharField(max_length=15, choices=DISCOUNT_TYPE_CHOICES, verbose_name="نوع الخصم")
    
    # قيمة الخصم
    percentage_value = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                         validators=[MinValueValidator(0), MaxValueValidator(100)],
                                         verbose_name="النسبة المئوية")
    fixed_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     validators=[MinValueValidator(0)],
                                     verbose_name="المبلغ الثابت")
    
    # شروط التطبيق
    applicable_to_grades = models.ManyToManyField(GradeLevel, blank=True, verbose_name="الصفوف المطبق عليها")
    applicable_to_fee_types = models.CharField(max_length=200, blank=True, 
                                             verbose_name="أنواع المصروفات المطبق عليها",
                                             help_text="فاصل بينها بفواصل")
    
    # حدود التطبيق
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                            verbose_name="الحد الأقصى لمبلغ الخصم")
    min_payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                           verbose_name="الحد الأدنى للمبلغ لتطبيق الخصم")
    
    # تواريخ الصلاحية
    valid_from_date = models.DateField(verbose_name="صالح من تاريخ")
    valid_to_date = models.DateField(verbose_name="صالح حتى تاريخ")
    
    # إعدادات إضافية
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    requires_approval = models.BooleanField(default=False, verbose_name="يتطلب موافقة")
    description = models.TextField(blank=True, verbose_name="وصف الخصم")
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "إعدادات الخصم"
        verbose_name_plural = "إعدادات الخصومات"
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.get_category_display()}"
    
    def calculate_discount(self, amount):
        """حساب قيمة الخصم بناء على المبلغ"""
        if not self.is_active:
            return 0
            
        if self.min_payment_amount and amount < self.min_payment_amount:
            return 0
        
        if self.discount_type == 'PERCENTAGE':
            discount = amount * (self.percentage_value / 100)
        else:
            discount = self.fixed_amount or 0
        
        # تطبيق الحد الأقصى
        if self.max_discount_amount:
            discount = min(discount, self.max_discount_amount)
        
        return discount


# نموذج تطبيق الخصومات على الطلاب
class StudentDiscount(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'في الانتظار'),
        ('APPROVED', 'موافق عليه'),
        ('REJECTED', 'مرفوض'),
        ('EXPIRED', 'منتهي الصلاحية'),
    )
    
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, verbose_name="الطالب")
    discount_setting = models.ForeignKey(DiscountSettings, on_delete=models.CASCADE, verbose_name="إعدادات الخصم")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, verbose_name="العام الدراسي")
    
    # تفاصيل التطبيق
    applied_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="مبلغ الخصم المطبق")
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="المبلغ الأصلي")
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="المبلغ النهائي")
    
    # حالة الموافقة
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING', verbose_name="الحالة")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='approved_discounts', verbose_name="موافق عليه بواسطة")
    approval_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الموافقة")
    
    # ملاحظات
    application_reason = models.TextField(verbose_name="سبب التقدم للخصم")
    admin_notes = models.TextField(blank=True, verbose_name="ملاحظات الإدارة")
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                                 related_name='created_discounts', verbose_name="منشأ بواسطة")
    
    class Meta:
        verbose_name = "خصم الطالب"
        verbose_name_plural = "خصومات الطلاب"
        unique_together = ['student', 'discount_setting', 'academic_year']
    
    def __str__(self):
        return f"{self.student.name} - {self.discount_setting.name}"


# نموذج أدوار النظام
class SystemRole(models.Model):
    ROLE_CHOICES = (
        ('SYSTEM_ADMIN', 'مدير النظام'),
        ('SCHOOL_MANAGER', 'مدير المدرسة'),
        ('ACCOUNTANT', 'موظف الحسابات'),
        ('STUDENT_AFFAIRS', 'موظف شؤون الطلاب'),
        ('BOOKS_INVENTORY', 'موظف مخزن الكتب'),
        ('UNIFORMS_INVENTORY', 'موظف مخزن الملابس'),
        ('TEACHER', 'مدرس'),
    )
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='system_role')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    permissions = models.TextField(blank=True, verbose_name="صلاحيات إضافية", 
                                 help_text="JSON format للصلاحيات الخاصة")
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "دور المستخدم"
        verbose_name_plural = "أدوار المستخدمين"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


# نموذج إعدادات التنبيهات والإشعارات
class NotificationSettings(models.Model):
    NOTIFICATION_TYPES = (
        ('EMAIL', 'بريد إلكتروني'),
        ('SMS', 'رسائل نصية'),
        ('SYSTEM', 'إشعارات النظام'),
    )
    
    # إعدادات تنبيهات الأقساط
    payment_due_notification_days = models.IntegerField(default=7, verbose_name="تنبيه قبل موعد الاستحقاق (أيام)")
    overdue_payment_notification = models.BooleanField(default=True, verbose_name="تنبيه المتأخرات")
    
    # إعدادات التنبيهات العامة
    low_balance_notification = models.BooleanField(default=True, verbose_name="تنبيه الرصيد المنخفض")
    new_student_registration_notification = models.BooleanField(default=True, verbose_name="تنبيه تسجيل طالب جديد")
    
    # وسائل التنبيه
    notification_method = models.CharField(max_length=10, choices=NOTIFICATION_TYPES, default='SYSTEM', verbose_name="وسيلة التنبيه")
    
    # إعدادات البريد الإلكتروني
    email_host = models.CharField(max_length=100, blank=True, verbose_name="خادم البريد")
    email_port = models.IntegerField(default=587, verbose_name="منفذ البريد")
    email_username = models.CharField(max_length=100, blank=True, verbose_name="اسم المستخدم")
    email_password = models.CharField(max_length=100, blank=True, verbose_name="كلمة المرور")
    email_use_tls = models.BooleanField(default=True, verbose_name="استخدام TLS")
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "إعدادات التنبيهات"
        verbose_name_plural = "إعدادات التنبيهات"
    
    def __str__(self):
        return "إعدادات التنبيهات"
    
    @classmethod
    def get_current_settings(cls):
        settings_obj, created = cls.objects.get_or_create(pk=1)
        return settings_obj


# نموذج إعدادات التقارير
class ReportSettings(models.Model):
    # إعدادات تصدير التقارير
    default_export_format = models.CharField(
        max_length=10, 
        choices=[('PDF', 'PDF'), ('EXCEL', 'Excel'), ('CSV', 'CSV')], 
        default='PDF', 
        verbose_name="تنسيق التصدير الافتراضي"
    )
    
    # إعدادات عرض التقارير
    reports_per_page = models.IntegerField(default=50, verbose_name="عدد السجلات لكل صفحة")
    include_school_logo_in_reports = models.BooleanField(default=True, verbose_name="تضمين شعار المدرسة في التقارير")
    
    # إعدادات التقارير المالية
    financial_reports_show_details = models.BooleanField(default=True, verbose_name="إظهار التفاصيل في التقارير المالية")
    group_payments_by_month = models.BooleanField(default=True, verbose_name="تجميع المدفوعات حسب الشهر")
    
    # إعدادات تقارير الطلاب
    student_reports_include_photo = models.BooleanField(default=False, verbose_name="تضمين صور الطلاب")
    show_parent_contact_info = models.BooleanField(default=True, verbose_name="إظهار معلومات اتصال ولي الأمر")
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "إعدادات التقارير"
        verbose_name_plural = "إعدادات التقارير"
    
    def __str__(self):
        return "إعدادات التقارير"
    
    @classmethod
    def get_current_settings(cls):
        settings_obj, created = cls.objects.get_or_create(pk=1)
        return settings_obj


# نموذج إعدادات الأمان
class SecuritySettings(models.Model):
    # إعدادات كلمة المرور
    min_password_length = models.IntegerField(default=8, verbose_name="الحد الأدنى لطول كلمة المرور")
    require_special_characters = models.BooleanField(default=True, verbose_name="تطلب رموز خاصة")
    require_numbers = models.BooleanField(default=True, verbose_name="تطلب أرقام")
    password_expiry_days = models.IntegerField(default=90, verbose_name="انتهاء صلاحية كلمة المرور (أيام)")
    
    # إعدادات الجلسات
    session_timeout_minutes = models.IntegerField(default=30, verbose_name="انتهاء الجلسة (دقائق)")
    max_login_attempts = models.IntegerField(default=5, verbose_name="الحد الأقصى لمحاولات تسجيل الدخول")
    account_lockout_duration = models.IntegerField(default=30, verbose_name="مدة قفل الحساب (دقائق)")
    
    # إعدادات التدقيق
    log_user_actions = models.BooleanField(default=True, verbose_name="تسجيل أنشطة المستخدمين")
    log_financial_transactions = models.BooleanField(default=True, verbose_name="تسجيل العمليات المالية")
    backup_frequency_days = models.IntegerField(default=7, verbose_name="تكرار النسخ الاحتياطي (أيام)")
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "إعدادات الأمان"
        verbose_name_plural = "إعدادات الأمان"
    
    def __str__(self):
        return "إعدادات الأمان"
    
    @classmethod
    def get_current_settings(cls):
        settings_obj, created = cls.objects.get_or_create(pk=1)
        return settings_obj


# نموذج سجل التغييرات في الإعدادات
class SettingsLog(models.Model):
    ACTION_CHOICES = (
        ('CREATE', 'إنشاء'),
        ('UPDATE', 'تحديث'),
        ('DELETE', 'حذف'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="المستخدم")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name="نوع العملية")
    setting_type = models.CharField(max_length=100, verbose_name="نوع الإعداد")
    old_value = models.TextField(blank=True, verbose_name="القيمة السابقة")
    new_value = models.TextField(blank=True, verbose_name="القيمة الجديدة")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="وقت التغيير")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="عنوان IP")
    
    class Meta:
        verbose_name = "سجل تغييرات الإعدادات"
        verbose_name_plural = "سجل تغييرات الإعدادات"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.setting_type} - {self.timestamp}"


# في school_settings/models.py - إضافة في النهاية
# تحديث نموذج SettingsLog ليكون آمن أكثر
class SettingsLog(models.Model):
    """سجل تغييرات الإعدادات - نسخة محسنة وآمنة"""
    
    ACTION_CHOICES = [
        ('CREATE', 'إنشاء'),
        ('UPDATE', 'تحديث'),
        ('DELETE', 'حذف'),
        ('VIEW', 'عرض'),
        ('LOGIN', 'تسجيل دخول'),
        ('LOGOUT', 'تسجيل خروج'),
    ]
    
    SETTING_TYPES = [
        ('ACADEMIC_YEAR', 'عام دراسي'),
        ('EDUCATION_LEVEL', 'مرحلة تعليمية'),
        ('GRADE_LEVEL', 'صف دراسي'),
        ('SCHOOL_FEE', 'مصروفات مدرسية'),
        ('DISCOUNT', 'خصم'),
        ('SYSTEM_SETTING', 'إعداد نظام'),
        ('USER_ROLE', 'دور مستخدم'),
        ('SCHOOL_INFO', 'معلومات المدرسة'),
        ('OTHER', 'أخرى'),
    ]
    
    # معلومات العملية
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # تغيير من CASCADE إلى SET_NULL
        null=True,  # السماح بالقيمة الفارغة
        blank=True,
        verbose_name="المستخدم"
    )
    
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name="نوع العملية"
    )
    
    setting_type = models.CharField(
        max_length=50,
        choices=SETTING_TYPES,
        default='OTHER',
        verbose_name="نوع الإعداد"
    )
    
    # تفاصيل التغيير
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="معرف الكائن"
    )
    
    object_name = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name="اسم الكائن"
    )
    
    old_value = models.TextField(
        blank=True,
        default='',
        verbose_name="القيمة السابقة"
    )
    
    new_value = models.TextField(
        blank=True,
        default='',
        verbose_name="القيمة الجديدة"
    )
    
    description = models.TextField(
        blank=True,
        default='',
        verbose_name="وصف العملية"
    )
    
    # معلومات النظام
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="وقت العملية"
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="عنوان IP"
    )
    
    user_agent = models.TextField(
        blank=True,
        default='',
        verbose_name="معلومات المتصفح"
    )
    
    class Meta:
        verbose_name = "سجل إعدادات"
        verbose_name_plural = "سجلات الإعدادات"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['setting_type', 'timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        try:
            username = self.user.username if self.user else 'مستخدم محذوف'
            return f"{username} - {self.get_action_display()} - {self.get_setting_type_display()}"
        except Exception:
            return f"سجل #{self.pk}"
    
    @classmethod
    def log_action(cls, user, action, setting_type, object_id=None, object_name='', 
                   old_value='', new_value='', description='', request=None):
        """دالة مساعدة لتسجيل العمليات - نسخة آمنة"""
        try:
            ip_address = None
            user_agent = ''
            
            if request:
                ip_address = get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # تحديد الطول
            
            return cls.objects.create(
                user=user,
                action=action,
                setting_type=setting_type,
                object_id=object_id,
                object_name=str(object_name)[:200] if object_name else '',  # تحديد الطول
                old_value=str(old_value)[:1000] if old_value else '',  # تحديد الطول
                new_value=str(new_value)[:1000] if new_value else '',  # تحديد الطول
                description=str(description)[:500] if description else '',  # تحديد الطول
                ip_address=ip_address,
                user_agent=user_agent
            )
            
        except Exception as e:
            logger.error(f"خطأ في تسجيل العملية: {e}")
            return None
    
    def get_action_icon(self):
        """الحصول على أيقونة العملية"""
        icons = {
            'CREATE': 'fas fa-plus text-success',
            'UPDATE': 'fas fa-edit text-warning',
            'DELETE': 'fas fa-trash text-danger',
            'VIEW': 'fas fa-eye text-info',
            'LOGIN': 'fas fa-sign-in-alt text-primary',
            'LOGOUT': 'fas fa-sign-out-alt text-secondary',
        }
        return icons.get(self.action, 'fas fa-question text-muted')
    
    def get_setting_type_icon(self):
        """الحصول على أيقونة نوع الإعداد"""
        icons = {
            'ACADEMIC_YEAR': 'fas fa-calendar-alt',
            'EDUCATION_LEVEL': 'fas fa-layer-group',
            'GRADE_LEVEL': 'fas fa-graduation-cap',
            'SCHOOL_FEE': 'fas fa-money-bill-wave',
            'DISCOUNT': 'fas fa-percentage',
            'SYSTEM_SETTING': 'fas fa-cog',
            'USER_ROLE': 'fas fa-users-cog',
            'SCHOOL_INFO': 'fas fa-school',
            'OTHER': 'fas fa-ellipsis-h',
        }
        return icons.get(self.setting_type, 'fas fa-cog')
    
    def save(self, *args, **kwargs):
        """حفظ آمن مع تحديد أطوال النصوص"""
        try:
            # تحديد أطوال النصوص لتجنب الأخطاء
            if self.object_name and len(self.object_name) > 200:
                self.object_name = self.object_name[:200]
            
            if self.old_value and len(self.old_value) > 1000:
                self.old_value = self.old_value[:1000]
                
            if self.new_value and len(self.new_value) > 1000:
                self.new_value = self.new_value[:1000]
                
            if self.description and len(self.description) > 500:
                self.description = self.description[:500]
                
            if self.user_agent and len(self.user_agent) > 500:
                self.user_agent = self.user_agent[:500]
            
            super().save(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"خطأ في حفظ سجل الإعدادات: {e}")
            raise