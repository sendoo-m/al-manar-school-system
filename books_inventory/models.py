from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.db.models import Sum, F
from django.contrib.auth.models import User


# نموذج الموردين
class Supplier(models.Model):
    name = models.CharField(max_length=200, verbose_name="اسم المورد")
    contact_person = models.CharField(max_length=100, blank=True, verbose_name="الشخص المسؤول")
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="رقم الهاتف")
    email = models.EmailField(blank=True, verbose_name="البريد الإلكتروني")
    address = models.TextField(blank=True, verbose_name="العنوان")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "مورد"
        verbose_name_plural = "الموردين"
        ordering = ['name']
    
    def __str__(self):
        return self.name


# نموذج المواد الدراسية
from django.utils import timezone
class Subject(models.Model):
    # البيانات الأساسية الموجودة
    name = models.CharField(max_length=100, verbose_name="اسم المادة")
    name_en = models.CharField(max_length=100, blank=True, verbose_name="الاسم بالإنجليزية")
    code = models.CharField(max_length=20, blank=True, verbose_name="كود المادة")
    subject_code = models.CharField(max_length=20, blank=True, verbose_name="رمز المادة", help_text="رمز مختصر للمادة")
    description = models.TextField(blank=True, verbose_name="الوصف")
    color = models.CharField(max_length=7, default='#007bff', verbose_name="اللون", help_text="لون المادة في الواجهة")
    
    # إضافة ربط بالصفوف الدراسية والمراحل التعليمية
    grade_levels = models.ManyToManyField(
        'school_settings.GradeLevel', 
        blank=True, 
        verbose_name="الصفوف الدراسية",
        help_text="الصفوف التي تُدرّس فيها هذه المادة"
    )
    
    education_levels = models.ManyToManyField(
        'school_settings.EducationLevel', 
        blank=True, 
        verbose_name="المراحل التعليمية",
        help_text="المراحل التعليمية التي تتضمن هذه المادة"
    )
    
    # إعدادات إضافية
    is_core_subject = models.BooleanField(default=True, verbose_name="مادة أساسية", help_text="هل هذه مادة أساسية أم اختيارية")
    weekly_hours = models.PositiveIntegerField(default=2, verbose_name="عدد الحصص الأسبوعية")
    
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="تاريخ الإضافة")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "مادة دراسية"
        verbose_name_plural = "المواد الدراسية"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_core_subject']),
        ]
    
    def __str__(self):
        return self.name
    
    # خصائص محسوبة
    @property
    def books_count(self):
        return self.book_set.count()
    
    @property
    def active_books_count(self):
        return self.book_set.filter(is_active=True).count()
    
    @property
    def total_books_stock(self):
        total = self.book_set.aggregate(total=models.Sum('total_stock'))['total']
        return total or 0
    
    @property
    def grade_levels_names(self):
        """أسماء الصفوف الدراسية مفصولة بفاصلة"""
        return ', '.join([grade.name for grade in self.grade_levels.all()])
    
    @property
    def education_levels_names(self):
        """أسماء المراحل التعليمية مفصولة بفاصلة"""
        return ', '.join([level.name for level in self.education_levels.all()])
    
    def get_books_for_grade(self, grade_level):
        """الحصول على الكتب المناسبة للصف الدراسي"""
        return self.book_set.filter(
            grade_levels=grade_level,
            is_active=True,
            available_stock__gt=0
        )
    
    def get_grade_levels_list(self):
        """قائمة بكافة الصفوف الدراسية للمادة"""
        return list(self.grade_levels.values('id', 'name', 'education_level__name'))

# نموذج الكتب - محدث
class Book(models.Model):
    BOOK_TYPE_CHOICES = (
        ('MINISTRY', 'كتاب وزاري'),
        ('WORKBOOK', 'كتاب تمارين وزاري'),
        ('MANAR_BOOK', 'كتاب المنار'),
        ('MANAR_SUMMARY', 'ملخص المنار'),
        ('MANAR_EXERCISES', 'تمارين المنار'),
        ('REFERENCE', 'كتاب مرجعي'),
        ('DICTIONARY', 'قاموس'),
        ('ATLAS', 'أطلس'),
        ('OTHER', 'أخرى'),
    )
    
    title = models.CharField(max_length=200, verbose_name="عنوان الكتاب")
    book_type = models.CharField(max_length=20, choices=BOOK_TYPE_CHOICES, default='MINISTRY', verbose_name="نوع الكتاب")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="المادة الدراسية")
    grade_levels = models.ManyToManyField('school_settings.GradeLevel', blank=True, verbose_name="الصفوف الدراسية")
    
    # معلومات إضافية للكتب الخاصة بالمدرسة
    edition_year = models.CharField(max_length=10, blank=True, verbose_name="سنة الطبعة")
    academic_year = models.CharField(max_length=20, blank=True, verbose_name="السنة الدراسية")
    term = models.CharField(max_length=20, choices=[
        ('FIRST', 'الترم الأول'),
        ('SECOND', 'الترم الثاني'),
        ('FULL_YEAR', 'السنة كاملة')
    ], default='FULL_YEAR', verbose_name="الفترة الدراسية")
    
    # تفاصيل إضافية للملخصات والكتب الخاصة
    description = models.TextField(blank=True, verbose_name="الوصف")
    pages_count = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1)], verbose_name="عدد الصفحات")
    
    # المخزون
    total_stock = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="إجمالي المخزون")
    available_stock = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="المتاح للتوزيع")
    distributed_count = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="الموزع")
    damaged_count = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="التالف")
    
    # معلومات إضافية
    cost_price = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="سعر التكلفة")
    minimum_stock_level = models.IntegerField(default=10, validators=[MinValueValidator(0)], verbose_name="الحد الأدنى للمخزون")
    
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "كتاب"
        verbose_name_plural = "الكتب"
        ordering = ['title']
        indexes = [
            models.Index(fields=['subject', 'book_type']),
            models.Index(fields=['available_stock']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.subject.name}"
    
    @property
    def is_low_stock(self):
        """التحقق من انخفاض المخزون"""
        return self.available_stock <= self.minimum_stock_level
    
    @property
    def stock_status(self):
        """حالة المخزون"""
        if self.available_stock == 0:
            return 'نفد المخزون'
        elif self.is_low_stock:
            return 'مخزون منخفض'
        else:
            return 'متوفر'
    
    @property
    def is_manar_material(self):
        """التحقق من كون المادة من إنتاج المدرسة"""
        return self.book_type.startswith('MANAR_')
    
    @property
    def type_display_with_icon(self):
        """عرض نوع الكتاب مع أيقونة"""
        icons = {
            'MINISTRY': '<i class="fas fa-university text-primary"></i>',
            'WORKBOOK': '<i class="fas fa-edit text-info"></i>',
            'MANAR_BOOK': '<i class="fas fa-star text-warning"></i>',
            'MANAR_SUMMARY': '<i class="fas fa-clipboard-list text-success"></i>',
            'MANAR_EXERCISES': '<i class="fas fa-pencil-alt text-info"></i>',
            'REFERENCE': '<i class="fas fa-book text-secondary"></i>',
            'DICTIONARY': '<i class="fas fa-language text-primary"></i>',
            'ATLAS': '<i class="fas fa-globe text-info"></i>',
            'OTHER': '<i class="fas fa-book-open text-muted"></i>',
        }
        return f'{icons.get(self.book_type, "")} {self.get_book_type_display()}'
    
    def update_stock(self):
        """تحديث المخزون المتاح"""
        self.available_stock = self.total_stock - self.distributed_count - self.damaged_count
        self.save()

    # في نموذج Book
    def update_stock(self):
        """تحديث المخزون المتاح"""
        self.available_stock = self.total_stock - self.distributed_count - self.damaged_count
        self.save(update_fields=['available_stock'])

    # في نموذج Notebook
    def update_stock(self):
        """تحديث المخزون المتاح"""
        self.available_stock = self.total_stock - self.distributed_count - self.damaged_count
        self.save(update_fields=['available_stock'])

    # في نموذج SchoolSupply
    def update_stock(self):
        """تحديث المخزون المتاح"""
        self.available_stock = self.total_stock - self.distributed_count - self.damaged_count
        self.save(update_fields=['available_stock'])

    
    @property
    def actual_total_stock(self):
        """إجمالي المخزون الفعلي من إيصالات الاستلام"""
        from django.db.models import Sum
        
        total = BookReceiptItem.objects.filter(book=self).aggregate(
            total_received=Sum('quantity_received')
        )['total_received'] or 0
        
        return total

    @property
    def actual_damaged_count(self):
        """إجمالي التالف الفعلي من إيصالات الاستلام"""
        from django.db.models import Sum
        
        damaged = BookReceiptItem.objects.filter(book=self).aggregate(
            total_damaged=Sum('quantity_damaged')
        )['total_damaged'] or 0
        
        return damaged

    @property
    def actual_distributed_count(self):
        """إجمالي الموزع الفعلي من إيصالات التوزيع"""
        from django.db.models import Sum
        
        # إذا كان لديك نموذج للتوزيع
        try:
            distributed = BookDistributionItem.objects.filter(book=self).aggregate(
                total_distributed=Sum('quantity_distributed')
            )['total_distributed'] or 0
            return distributed
        except:
            return 0

    @property
    def actual_available_stock(self):
        """المخزون المتاح الفعلي"""
        total = self.actual_total_stock
        damaged = self.actual_damaged_count
        distributed = self.actual_distributed_count
        
        return max(0, total - damaged - distributed)

    @property
    def is_low_stock(self):
        """هل المخزون منخفض"""
        return self.actual_available_stock <= self.minimum_stock_level

    def sync_stock_from_receipts(self):
        """تحديث أرقام المخزون من إيصالات الاستلام"""
        self.total_stock = self.actual_total_stock
        self.damaged_count = self.actual_damaged_count
        # يمكن أيضاً تحديث distributed_count إذا كان موجود
        self.available_stock = self.actual_available_stock
        self.save(update_fields=['total_stock', 'damaged_count', 'available_stock'])

# نموذج الكراسات
class Notebook(models.Model):
    NOTEBOOK_TYPE_CHOICES = (
        ('LINED', 'مسطر'),
        ('SQUARED', 'مربعات'),
        ('BLANK', 'أبيض'),
        ('DRAWING', 'رسم'),
        ('MUSIC', 'موسيقى'),
        ('OTHER', 'أخرى'),
    )
    
    SIZE_CHOICES = (
        ('A4', 'A4'),
        ('A5', 'A5'),
        ('B5', 'B5'),
        ('SMALL', 'صغير'),
        ('MEDIUM', 'متوسط'),
        ('LARGE', 'كبير'),
    )
    
    name = models.CharField(max_length=150, verbose_name="اسم الكراسة")
    notebook_type = models.CharField(max_length=10, choices=NOTEBOOK_TYPE_CHOICES, verbose_name="نوع الكراسة")
    size = models.CharField(max_length=10, choices=SIZE_CHOICES, default='A4', verbose_name="الحجم")
    pages_count = models.IntegerField(default=60, validators=[MinValueValidator(1)], verbose_name="عدد الصفحات")
    
    # المخزون
    total_stock = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="إجمالي المخزون")
    available_stock = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="المتاح للتوزيع")
    distributed_count = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="الموزع")
    damaged_count = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="التالف")
    
    # معلومات إضافية
    cost_price = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="سعر التكلفة")
    minimum_stock_level = models.IntegerField(default=50, validators=[MinValueValidator(0)], verbose_name="الحد الأدنى للمخزون")
    
    grade_levels = models.ManyToManyField('school_settings.GradeLevel', blank=True, verbose_name="الصفوف الدراسية")
    
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "كراسة"
        verbose_name_plural = "الكراسات"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.get_notebook_type_display()}"
    
    @property
    def is_low_stock(self):
        return self.available_stock <= self.minimum_stock_level
    
    @property
    def stock_status(self):
        if self.available_stock == 0:
            return 'نفد المخزون'
        elif self.is_low_stock:
            return 'مخزون منخفض'
        else:
            return 'متوفر'
    
    def update_stock(self):
        self.available_stock = self.total_stock - self.distributed_count - self.damaged_count
        self.save()


# نموذج الأدوات المكتبية والمدرسية
class SchoolSupply(models.Model):
    SUPPLY_CATEGORY_CHOICES = (
        ('STATIONERY', 'أدوات مكتبية'),
        ('ART', 'أدوات فنية'),
        ('SCIENCE', 'أدوات علمية'),
        ('SPORTS', 'أدوات رياضية'),
        ('ELECTRONICS', 'إلكترونيات'),
        ('CLEANING', 'أدوات تنظيف'),
        ('OTHER', 'أخرى'),
    )
    
    name = models.CharField(max_length=150, verbose_name="اسم الأداة")
    category = models.CharField(max_length=15, choices=SUPPLY_CATEGORY_CHOICES, verbose_name="الفئة")
    description = models.TextField(blank=True, verbose_name="الوصف")
    unit = models.CharField(max_length=20, default='قطعة', verbose_name="الوحدة")
    
    # المخزون
    total_stock = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="إجمالي المخزون")
    available_stock = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="المتاح للتوزيع")
    distributed_count = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="الموزع")
    damaged_count = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="التالف")
    
    cost_price = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="سعر التكلفة")
    minimum_stock_level = models.IntegerField(default=10, validators=[MinValueValidator(0)], verbose_name="الحد الأدنى للمخزون")
    
    grade_levels = models.ManyToManyField('school_settings.GradeLevel', blank=True, verbose_name="الصفوف الدراسية")
    
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "أداة مدرسية"
        verbose_name_plural = "الأدوات المدرسية"
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.get_category_display()}"
    
    @property
    def is_low_stock(self):
        return self.available_stock <= self.minimum_stock_level
    
    @property
    def stock_status(self):
        if self.available_stock == 0:
            return 'نفد المخزون'
        elif self.is_low_stock:
            return 'مخزون منخفض'
        else:
            return 'متوفر'
    
    def update_stock(self):
        self.available_stock = self.total_stock - self.distributed_count - self.damaged_count
        self.save()


# نموذج استلام البضائع من المورد
class StockReceipt(models.Model):
    RECEIPT_TYPE_CHOICES = (
        ('BOOKS', 'كتب'),
        ('NOTEBOOKS', 'كراسات'),
        ('SUPPLIES', 'أدوات مدرسية'),
    )
    
    receipt_number = models.CharField(max_length=20, unique=True, verbose_name="رقم الإيصال")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name="المورد")
    receipt_type = models.CharField(max_length=15, choices=RECEIPT_TYPE_CHOICES, verbose_name="نوع البضاعة")
    
    receipt_date = models.DateField(default=timezone.now, verbose_name="تاريخ الاستلام")
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="مستلم بواسطة")
    
    total_items = models.IntegerField(default=0, verbose_name="إجمالي الكمية")
    damaged_items = models.IntegerField(default=0, verbose_name="الكمية التالفة")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="إجمالي التكلفة")
    
    invoice_number = models.CharField(max_length=50, blank=True, verbose_name="رقم الفاتورة")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "إيصال استلام"
        verbose_name_plural = "إيصالات الاستلام"
        ordering = ['-receipt_date', '-created_at']
    
    def __str__(self):
        return f"إيصال {self.receipt_number} - {self.supplier.name}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            # إنشاء رقم إيصال تلقائي
            today = timezone.now()
            prefix = f"RCP-{today.strftime('%Y%m%d')}"
            last_receipt = StockReceipt.objects.filter(
                receipt_number__startswith=prefix
            ).order_by('-receipt_number').first()
            
            if last_receipt:
                last_num = int(last_receipt.receipt_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.receipt_number = f"{prefix}-{new_num:04d}"
        
        super().save(*args, **kwargs)


# نموذج تفاصيل استلام الكتب
class BookReceiptItem(models.Model):
    receipt = models.ForeignKey(StockReceipt, on_delete=models.CASCADE, related_name='book_items', verbose_name="الإيصال")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="الكتاب")
    quantity_received = models.IntegerField(validators=[MinValueValidator(1)], verbose_name="الكمية المستلمة")
    quantity_damaged = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="الكمية التالفة")
    unit_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="سعر الوحدة")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="إجمالي التكلفة")
    
    class Meta:
        verbose_name = "عنصر استلام كتاب"
        verbose_name_plural = "عناصر استلام الكتب"
    
    def save(self, *args, **kwargs):
        self.total_cost = self.unit_cost * self.quantity_received
        super().save(*args, **kwargs)
        
        # تحديث مخزون الكتاب
        self.book.total_stock += self.quantity_received
        self.book.damaged_count += self.quantity_damaged
        self.book.update_stock()


# نموذج تفاصيل استلام الكراسات
class NotebookReceiptItem(models.Model):
    receipt = models.ForeignKey(StockReceipt, on_delete=models.CASCADE, related_name='notebook_items', verbose_name="الإيصال")
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE, verbose_name="الكراسة")
    quantity_received = models.IntegerField(validators=[MinValueValidator(1)], verbose_name="الكمية المستلمة")
    quantity_damaged = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="الكمية التالفة")
    unit_cost = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="سعر الوحدة")
    total_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="إجمالي التكلفة")
    
    class Meta:
        verbose_name = "عنصر استلام كراسة"
        verbose_name_plural = "عناصر استلام الكراسات"
    
    def save(self, *args, **kwargs):
        self.total_cost = self.unit_cost * self.quantity_received
        super().save(*args, **kwargs)
        
        # تحديث مخزون الكراسة
        self.notebook.total_stock += self.quantity_received
        self.notebook.damaged_count += self.quantity_damaged
        self.notebook.update_stock()


# نموذج تفاصيل استلام الأدوات المدرسية
class SupplyReceiptItem(models.Model):
    receipt = models.ForeignKey(StockReceipt, on_delete=models.CASCADE, related_name='supply_items', verbose_name="الإيصال")
    supply = models.ForeignKey(SchoolSupply, on_delete=models.CASCADE, verbose_name="الأداة المدرسية")
    quantity_received = models.IntegerField(validators=[MinValueValidator(1)], verbose_name="الكمية المستلمة")
    quantity_damaged = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="الكمية التالفة")
    unit_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="سعر الوحدة")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="إجمالي التكلفة")
    
    class Meta:
        verbose_name = "عنصر استلام أداة مدرسية"
        verbose_name_plural = "عناصر استلام الأدوات المدرسية"
    
    def save(self, *args, **kwargs):
        self.total_cost = self.unit_cost * self.quantity_received
        super().save(*args, **kwargs)
        
        # تحديث مخزون الأداة المدرسية
        self.supply.total_stock += self.quantity_received
        self.supply.damaged_count += self.quantity_damaged
        self.supply.update_stock()


# نموذج توزيع المواد على الطلاب - إصلاح max_length
class StudentDistribution(models.Model):
    DISTRIBUTION_STATUS_CHOICES = (
        ('PENDING', 'في الانتظار'),
        ('PARTIAL', 'موزع جزئياً'),  # تقصير النص
        ('COMPLETED', 'مكتمل'),
        ('CANCELLED', 'ملغي'),
    )
    
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, verbose_name="الطالب")
    distribution_date = models.DateField(default=timezone.now, verbose_name="تاريخ التوزيع")
    distributed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="موزع بواسطة")
    
    # التحقق من دفع القسط الأول
    first_installment_verified = models.BooleanField(default=False, verbose_name="تم التحقق من دفع القسط الأول")
    verification_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ التحقق")
    verification_notes = models.TextField(blank=True, verbose_name="ملاحظات التحقق")
    
    # إصلاح max_length إلى 25 ليتسع أطول قيمة
    status = models.CharField(max_length=25, choices=DISTRIBUTION_STATUS_CHOICES, default='PENDING', verbose_name="الحالة")
    total_items = models.IntegerField(default=0, verbose_name="إجمالي العناصر")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "توزيع الطالب"
        verbose_name_plural = "توزيعات الطلاب"
        ordering = ['-distribution_date', '-created_at']
        unique_together = ['student', 'distribution_date']  # توزيع واحد لكل طالب في اليوم
    
    def __str__(self):
        return f"توزيع {self.student.name} - {self.distribution_date}"
    
    def can_distribute(self):
        """التحقق من إمكانية التوزيع"""
        return self.first_installment_verified and self.status != 'CANCELLED'


# نموذج تفاصيل توزيع الكتب
class BookDistributionItem(models.Model):
    distribution = models.ForeignKey(StudentDistribution, on_delete=models.CASCADE, related_name='book_items', verbose_name="التوزيع")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="الكتاب")
    quantity_requested = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="الكمية المطلوبة")
    quantity_distributed = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="الكمية الموزعة")
    is_distributed = models.BooleanField(default=False, verbose_name="تم التوزيع")
    distribution_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ التوزيع")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    
    class Meta:
        verbose_name = "توزيع كتاب"
        verbose_name_plural = "توزيعات الكتب"
    
    def save(self, *args, **kwargs):
        if self.is_distributed and self.quantity_distributed > 0:
            # تحديث مخزون الكتاب
            self.book.distributed_count += self.quantity_distributed
            self.book.update_stock()
            
            if not self.distribution_date:
                self.distribution_date = timezone.now()
        
        super().save(*args, **kwargs)


# نموذج تفاصيل توزيع الكراسات
class NotebookDistributionItem(models.Model):
    distribution = models.ForeignKey(StudentDistribution, on_delete=models.CASCADE, related_name='notebook_items', verbose_name="التوزيع")
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE, verbose_name="الكراسة")
    quantity_requested = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="الكمية المطلوبة")
    quantity_distributed = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="الكمية الموزعة")
    is_distributed = models.BooleanField(default=False, verbose_name="تم التوزيع")
    distribution_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ التوزيع")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    
    class Meta:
        verbose_name = "توزيع كراسة"
        verbose_name_plural = "توزيعات الكراسات"
    
    def save(self, *args, **kwargs):
        if self.is_distributed and self.quantity_distributed > 0:
            self.notebook.distributed_count += self.quantity_distributed
            self.notebook.update_stock()
            
            if not self.distribution_date:
                self.distribution_date = timezone.now()
        
        super().save(*args, **kwargs)


# نموذج تفاصيل توزيع الأدوات المدرسية
class SupplyDistributionItem(models.Model):
    distribution = models.ForeignKey(StudentDistribution, on_delete=models.CASCADE, related_name='supply_items', verbose_name="التوزيع")
    supply = models.ForeignKey(SchoolSupply, on_delete=models.CASCADE, verbose_name="الأداة المدرسية")
    quantity_requested = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="الكمية المطلوبة")
    quantity_distributed = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="الكمية الموزعة")
    is_distributed = models.BooleanField(default=False, verbose_name="تم التوزيع")
    distribution_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ التوزيع")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    
    class Meta:
        verbose_name = "توزيع أداة مدرسية"
        verbose_name_plural = "توزيعات الأدوات المدرسية"
    
    def save(self, *args, **kwargs):
        if self.is_distributed and self.quantity_distributed > 0:
            self.supply.distributed_count += self.quantity_distributed
            self.supply.update_stock()
            
            if not self.distribution_date:
                self.distribution_date = timezone.now()
        
        super().save(*args, **kwargs)


# نموذج تسجيل النواقص
class StockShortage(models.Model):
    ITEM_TYPE_CHOICES = (
        ('BOOK', 'كتاب'),
        ('NOTEBOOK', 'كراسة'),
        ('SUPPLY', 'أداة مدرسية'),
    )
    
    SHORTAGE_STATUS_CHOICES = (
        ('REPORTED', 'مُبلغ عنه'),
        ('ACKNOWLEDGED', 'معترف به'),
        ('ORDERED', 'تم الطلب'),
        ('RESOLVED', 'تم الحل'),
    )
    
    item_type = models.CharField(max_length=10, choices=ITEM_TYPE_CHOICES, verbose_name="نوع العنصر")
    item_name = models.CharField(max_length=200, verbose_name="اسم العنصر")
    
    # مراجع للعناصر
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True, verbose_name="الكتاب")
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE, null=True, blank=True, verbose_name="الكراسة")
    supply = models.ForeignKey(SchoolSupply, on_delete=models.CASCADE, null=True, blank=True, verbose_name="الأداة المدرسية")
    
    current_stock = models.IntegerField(verbose_name="المخزون الحالي")
    required_quantity = models.IntegerField(verbose_name="الكمية المطلوبة")
    shortage_quantity = models.IntegerField(verbose_name="كمية النقص")
    
    status = models.CharField(max_length=15, choices=SHORTAGE_STATUS_CHOICES, default='REPORTED', verbose_name="الحالة")
    priority = models.CharField(max_length=10, choices=[('HIGH', 'عالي'), ('MEDIUM', 'متوسط'), ('LOW', 'منخفض')], default='MEDIUM', verbose_name="الأولوية")
    
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="مُبلغ بواسطة")
    reported_date = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ البلاغ")
    
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    resolution_notes = models.TextField(blank=True, verbose_name="ملاحظات الحل")
    resolved_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الحل")
    
    class Meta:
        verbose_name = "نقص في المخزون"
        verbose_name_plural = "النواقص في المخزون"
        ordering = ['-reported_date', 'priority']
    
    def __str__(self):
        return f"نقص في {self.item_name} - كمية: {self.shortage_quantity}"
    
    def save(self, *args, **kwargs):
        if self.status == 'RESOLVED' and not self.resolved_date:
            self.resolved_date = timezone.now()
        super().save(*args, **kwargs)


class ShortageReport(models.Model):
    """تقارير النقص في المخزون"""
    ITEM_TYPE_CHOICES = [
        ('BOOK', 'كتاب'),
        ('NOTEBOOK', 'كراسة'),
        ('SUPPLY', 'أداة مدرسية'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'في الانتظار'),
        ('IN_PROGRESS', 'قيد المعالجة'),
        ('RESOLVED', 'تم الحل'),
        ('CANCELLED', 'ملغي'),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'منخفض'),
        ('MEDIUM', 'متوسط'),
        ('HIGH', 'عالي'),
        ('URGENT', 'عاجل'),
    ]
    
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, verbose_name="نوع العنصر")
    item_id = models.PositiveIntegerField(verbose_name="معرف العنصر")
    item_name = models.CharField(max_length=255, verbose_name="اسم العنصر")
    current_stock = models.PositiveIntegerField(default=0, verbose_name="المخزون الحالي")
    requested_quantity = models.PositiveIntegerField(verbose_name="الكمية المطلوبة")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM', verbose_name="الأولوية")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="الحالة")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    
    # استخدام settings.AUTH_USER_MODEL بدلاً من User مباشرة
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="مُبلغ بواسطة")
    report_date = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإبلاغ")
    resolved_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الحل")
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, 
                                   related_name='resolved_shortages', verbose_name="حُل بواسطة")
    
    class Meta:
        verbose_name = "تقرير نقص"
        verbose_name_plural = "تقارير النقص"
        ordering = ['-report_date']
        indexes = [
            models.Index(fields=['status', 'item_type']),
            models.Index(fields=['priority', 'report_date']),
        ]
    
    def __str__(self):
        return f"نقص {self.get_item_type_display()}: {self.item_name}"

    @property
    def shortage_quantity(self):
        """كمية النقص"""
        return max(0, self.requested_quantity - self.current_stock)
    
    @property
    def is_urgent(self):
        """هل التقرير عاجل"""
        return self.priority in ['HIGH', 'URGENT'] or self.current_stock == 0
    
    def mark_as_resolved(self, resolved_by, notes=None):
        """وضع علامة كمحلول"""
        self.status = 'RESOLVED'
        self.resolved_by = resolved_by
        self.resolved_date = timezone.now()
        if notes:
            self.notes = f"{self.notes}\n\nحُل في {timezone.now().strftime('%Y-%m-%d %H:%M')}: {notes}" if self.notes else f"حُل في {timezone.now().strftime('%Y-%m-%d %H:%M')}: {notes}"
        self.save()