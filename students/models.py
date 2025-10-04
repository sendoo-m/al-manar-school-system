# students/models.py - منظم ومحسن
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
from django.core.exceptions import ValidationError
from datetime import date, datetime
from decimal import Decimal
import re

# ===================================
# 📦 الاستيراد من نظام الإعدادات
# ===================================

from school_settings.models import (
    AcademicYear as SettingsAcademicYear, 
    EducationLevel, 
    GradeLevel,
)

# ===================================
# 🔧 الدوال المساعدة للرقم القومي
# ===================================

def extract_birth_date_from_national_id(national_id):
    """استخراج تاريخ الميلاد من الرقم القومي المصري"""
    if not national_id or len(str(national_id)) != 14:
        return None
    
    try:
        national_str = str(national_id)
        
        century_indicator = int(national_str[0])
        year_part = national_str[1:3]
        month = national_str[3:5]
        day = national_str[5:7]
        
        if century_indicator == 2:
            year = f"19{year_part}"
        elif century_indicator == 3:
            year = f"20{year_part}"
        else:
            return None
        
        birth_date = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d").date()
        
        if birth_date <= date.today():
            return birth_date
        else:
            return None
            
    except (ValueError, IndexError):
        return None

def calculate_age_from_birth_date(birth_date):
    """حساب العمر من تاريخ الميلاد"""
    if not birth_date:
        return None
    
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def extract_gender_from_national_id(national_id):
    """استخراج الجنس من الرقم القومي"""
    if not national_id or len(str(national_id)) != 14:
        return ''
    
    try:
        national_str = str(national_id)
        gender_digit = int(national_str[12])
        
        if gender_digit % 2 == 0:
            return 'F'
        else:
            return 'M'
            
    except (ValueError, IndexError):
        return ''

def validate_egyptian_national_id(national_id):
    """التحقق من صحة الرقم القومي المصري"""
    if not national_id:
        return False, "الرقم القومي مطلوب"
    
    national_str = str(national_id).strip()
    
    if len(national_str) != 14:
        return False, "الرقم القومي يجب أن يكون 14 رقماً"
    
    if not national_str.isdigit():
        return False, "الرقم القومي يجب أن يحتوي على أرقام فقط"
    
    century_indicator = int(national_str[0])
    if century_indicator not in [2, 3]:
        return False, "الرقم القومي غير صحيح (القرن غير صالح)"
    
    birth_date = extract_birth_date_from_national_id(national_id)
    if not birth_date:
        return False, "تاريخ الميلاد في الرقم القومي غير صحيح"
    
    return True, "صحيح"

# ===================================
# 📚 النماذج الأساسية
# ===================================

class Student(models.Model):
    """نموذج الطالب الرئيسي"""
    
    # خيارات الجنس
    GENDER_CHOICES = (
        ('', 'اختر الجنس'),
        ('M', 'ذكر'),
        ('F', 'أنثى'),
    )

    # ===================================
    # 👤 البيانات الشخصية
    # ===================================
    
    name = models.CharField(
        max_length=100, 
        verbose_name="اسم الطالب",
        help_text="الاسم الرباعي للطالب"
    )
    
    national_number = models.CharField(
        max_length=14, 
        unique=True, 
        verbose_name="الرقم القومي",
        help_text="أدخل الرقم القومي المكون من 14 رقماً"
    )
    
    age = models.IntegerField(
        verbose_name="العمر", 
        blank=True, 
        null=True,
        help_text="سيتم حسابه تلقائياً من الرقم القومي"
    )
    
    gender = models.CharField(
        max_length=1, 
        choices=GENDER_CHOICES, 
        verbose_name="الجنس", 
        blank=True,
        help_text="سيتم استخراجه تلقائياً من الرقم القومي"
    )
    
    date_of_birth = models.DateField(
        verbose_name="تاريخ الميلاد", 
        blank=True, 
        null=True,
        help_text="سيتم استخراجه تلقائياً من الرقم القومي"
    )
    
    phone_number = models.CharField(
        max_length=20, 
        default='', 
        blank=True, 
        verbose_name="رقم الهاتف"
    )
    
    address = models.TextField(
        blank=True, 
        verbose_name="العنوان"
    )
    
    # ===================================
    # 🎓 البيانات الأكاديمية
    # ===================================
    
    academic_year = models.ForeignKey(
        SettingsAcademicYear, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="العام الدراسي",
        help_text="العام الدراسي للتسجيل"
    )
    
    grade_level = models.ForeignKey(
        GradeLevel, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="الصف الدراسي",
        help_text="الصف الدراسي الحالي"
    )
    
    # ===================================
    # 💰 البيانات المالية
    # ===================================
    
    total_payments = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name="إجمالي المدفوعات",
        help_text="مجموع ما تم دفعه من رسوم"
    )
    
    total_fees = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name="إجمالي المصروفات",
        help_text="مجموع الرسوم المستحقة"
    )
    
    total_owed = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name="إجمالي المستحقات",
        help_text="المبلغ المتبقي للسداد"
    )
    
    # ===================================
    # 👨‍👩‍👧‍👦 بيانات ولي الأمر
    # ===================================
    
    parent_name = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="اسم ولي الأمر"
    )
    
    parent_phone = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name="هاتف ولي الأمر"
    )
    
    parent_email = models.EmailField(
        blank=True, 
        verbose_name="بريد ولي الأمر"
    )
    
    # ===================================
    # 🕒 تواريخ النظام
    # ===================================
    
    created_at = models.DateTimeField(
        default=timezone.now, 
        verbose_name="تاريخ التسجيل"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="تاريخ آخر تحديث"
    )
    
    is_active = models.BooleanField(
        default=True, 
        verbose_name="نشط",
        help_text="هل الطالب نشط في النظام؟"
    )

    # ===================================
    # 🔧 الدوال والخصائص
    # ===================================
    
    class Meta:
        indexes = [
            models.Index(fields=['national_number']),
            models.Index(fields=['name']),
            models.Index(fields=['grade_level']),
            models.Index(fields=['academic_year']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = "طالب"
        verbose_name_plural = "الطلاب"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.grade_name}"

    def clean(self):
        """التحقق من صحة البيانات قبل الحفظ"""
        if self.national_number:
            is_valid, message = validate_egyptian_national_id(self.national_number)
            if not is_valid:
                raise ValidationError({'national_number': message})

    def save(self, *args, **kwargs):
        """حفظ الطالب مع استخراج البيانات من الرقم القومي"""
        
        # استخراج البيانات من الرقم القومي
        if self.national_number and len(str(self.national_number)) == 14:
            # استخراج تاريخ الميلاد
            if not self.date_of_birth:
                extracted_birth_date = extract_birth_date_from_national_id(self.national_number)
                if extracted_birth_date:
                    self.date_of_birth = extracted_birth_date
            
            # حساب العمر
            if self.date_of_birth:
                self.age = calculate_age_from_birth_date(self.date_of_birth)
            
            # استخراج الجنس
            if not self.gender:
                self.gender = extract_gender_from_national_id(self.national_number)
        
        # تحديد العام الدراسي الحالي إذا لم يكن محدد
        if not self.academic_year:
            try:
                self.academic_year = SettingsAcademicYear.get_current_year()
            except:
                pass
        
        # تحديث المستحقات
        self.total_owed = self.total_fees - self.total_payments
        
        super().save(*args, **kwargs)

    # ===================================
    # 📊 خصائص محسوبة
    # ===================================
    
    @property
    def education_level(self):
        """الحصول على المرحلة التعليمية من خلال الصف"""
        if self.grade_level and self.grade_level.education_level:
            return self.grade_level.education_level
        return None

    @property
    def grade_name(self):
        """اسم الصف الدراسي"""
        return self.grade_level.name if self.grade_level else "غير محدد"

    @property
    def education_level_name(self):
        """اسم المرحلة التعليمية"""
        if self.education_level:
            return self.education_level.name
        return "غير محدد"

    def get_financial_status(self):
        """الحصول على الحالة المالية للطالب"""
        if self.total_owed <= 0:
            return 'مسدد بالكامل'
        elif self.total_owed < (self.total_fees * Decimal('0.5')):
            return 'مسدد جزئياً'
        else:
            return 'مستحق السداد'
    
    def get_status_color(self):
        """الحصول على لون يمثل الحالة المالية"""
        status = self.get_financial_status()
        colors = {
            'مسدد بالكامل': 'success',
            'مسدد جزئياً': 'warning', 
            'مستحق السداد': 'danger'
        }
        return colors.get(status, 'secondary')

    def get_payment_percentage(self):
        """نسبة ما تم سداده"""
        if self.total_fees > 0:
            return (self.total_payments / self.total_fees) * 100
        return 0

    def get_age_display(self):
        """عرض العمر مع النص"""
        return f"{self.age} سنة" if self.age else "غير محدد"

    def get_gender_display_arabic(self):
        """عرض الجنس بالعربية"""
        return dict(self.GENDER_CHOICES).get(self.gender, 'غير محدد')

# ===================================
# 📁 النماذج المساعدة
# ===================================

class UserProfile(models.Model):
    """ملف المستخدم الإضافي"""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        verbose_name="المستخدم"
    )
    
    address = models.CharField(
        max_length=200, 
        blank=True,
        verbose_name="العنوان"
    )
    
    phone_number = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="رقم الهاتف"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="تاريخ الإنشاء"
    )

    class Meta:
        verbose_name = "ملف المستخدم"
        verbose_name_plural = "ملفات المستخدمين"

    def __str__(self):
        return f"ملف {self.user.get_full_name() or self.user.username}"


class ArchiveStudent(models.Model):
    """أرشيف الطلاب المحذوفين"""
    
    GENDER_CHOICES = (
        ('', 'غير محدد'),
        ('M', 'ذكر'),
        ('F', 'أنثى'),
    )

    # ===================================
    # 📚 البيانات المؤرشفة
    # ===================================
    
    archive_name = models.CharField(
        max_length=100, 
        verbose_name="اسم الطالب"
    )
    
    archive_national_number = models.CharField(
        max_length=14, 
        verbose_name="الرقم القومي"
    )
    
    archive_age = models.IntegerField(
        default=0, 
        verbose_name="العمر"
    )
    
    archive_gender = models.CharField(
        max_length=1, 
        choices=GENDER_CHOICES, 
        default='', 
        verbose_name="الجنس"
    )
    
    archive_date_of_birth = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="تاريخ الميلاد"
    )
    
    # البيانات الأكاديمية المؤرشفة
    archive_academic_year = models.CharField(
        max_length=100, 
        default="غير محدد", 
        verbose_name="العام الدراسي"
    )
    
    archive_grade_level = models.CharField(
        max_length=100, 
        default="غير محدد", 
        verbose_name="الصف الدراسي"
    )
    
    archive_education_level = models.CharField(
        max_length=100, 
        default="غير محدد", 
        verbose_name="المرحلة التعليمية"
    )
    
    # البيانات المالية المؤرشفة
    archive_total_payments = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name="إجمالي المدفوعات"
    )
    
    archive_total_fees = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name="إجمالي المصروفات"
    )
    
    archive_total_owed = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        verbose_name="إجمالي المستحقات"
    )
    
    # تفاصيل الأرشفة
    archived_date = models.DateTimeField(
        default=timezone.now, 
        verbose_name="تاريخ الأرشفة"
    )
    
    archived_reason = models.CharField(
        max_length=200, 
        default="غير محدد", 
        verbose_name="سبب الأرشفة"
    )
    
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="تم الأرشفة بواسطة"
    )

    class Meta:
        verbose_name = "طالب مؤرشف"
        verbose_name_plural = "الطلاب المؤرشفون"
        ordering = ['-archived_date']

    def __str__(self):
        return f"{self.archive_name} - مؤرشف في {self.archived_date.date()}"

# ===================================
# 📡 الإشارات (Signals)
# ===================================

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """إنشاء ملف مستخدم تلقائي عند إنشاء مستخدم جديد"""
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=Student)
def update_student_data(sender, instance, created, **kwargs):
    """تحديث بيانات الطالب بعد الحفظ"""
    if created:
        # إضافة أي منطق إضافي للطلاب الجدد
        pass
