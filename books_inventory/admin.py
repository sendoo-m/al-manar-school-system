from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.urls import reverse
from django.http import HttpResponse
import csv
from datetime import datetime

from .models import (
    Supplier, Subject, Book, Notebook, SchoolSupply,
    StockReceipt, BookReceiptItem, NotebookReceiptItem, SupplyReceiptItem,
    StudentDistribution, BookDistributionItem, NotebookDistributionItem, SupplyDistributionItem,
    StockShortage
)


# إجراءات مخصصة
def export_selected_to_csv(modeladmin, request, queryset):
    """تصدير العناصر المحددة إلى CSV"""
    meta = modeladmin.model._meta
    field_names = [field.name for field in meta.fields]
    
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename={meta.verbose_name_plural}_{datetime.now().strftime("%Y%m%d")}.csv'
    
    writer = csv.writer(response)
    writer.writerow(field_names)
    
    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in field_names])
    
    return response

export_selected_to_csv.short_description = "تصدير المحدد إلى CSV"


# إدارة الموردين
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'contact_person',
        'phone_number',
        'email',
        'is_active',
        'receipts_count',
        'created_at'
    )
    
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'contact_person', 'phone_number', 'email')
    list_editable = ('is_active',)
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'contact_person', 'is_active')
        }),
        ('معلومات الاتصال', {
            'fields': ('phone_number', 'email', 'address')
        }),
        ('ملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )
    
    actions = [export_selected_to_csv]

    def receipts_count(self, obj):
        """عدد الإيصالات"""
        count = obj.stockreceipt_set.count()
        if count > 0:
            url = reverse('admin:books_inventory_stockreceipt_changelist') + f'?supplier__id__exact={obj.id}'
            return format_html('<a href="{}">{} إيصال</a>', url, count)
        return '0 إيصال'
    receipts_count.short_description = 'عدد الإيصالات'


# إدارة المواد الدراسية
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'code', 'books_count', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'name_en', 'code')
    list_editable = ('is_active',)
    
    def books_count(self, obj):
        """عدد الكتب"""
        count = obj.book_set.filter(is_active=True).count()
        return format_html('<span class="badge">{}</span>', count)
    books_count.short_description = 'عدد الكتب'


# إدارة الكتب
@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        'title_display',
        'subject',
        'book_type_with_icon',
        'term',
        'stock_info',
        'stock_status_display',
        'is_active'
    )
    
    list_filter = (
        'book_type',
        'term',
        'subject',
        'academic_year',
        'is_active',
        'created_at'
    )
    
    search_fields = ('title', 'description')
    list_editable = ('is_active',)
    filter_horizontal = ('grade_levels',)
    
    fieldsets = (
        ('معلومات الكتاب', {
            'fields': (
                'title',
                'book_type',
                'subject'
            )
        }),
        
        ('التفاصيل الأكاديمية', {
            'fields': (
                ('academic_year', 'term'),
                ('edition_year', 'pages_count'),
                'description'
            )
        }),
        
        ('المخزون', {
            'fields': (
                ('total_stock', 'available_stock'),
                ('distributed_count', 'damaged_count'),
                'minimum_stock_level'
            )
        }),
        
        ('إعدادات إضافية', {
            'fields': (
                'cost_price',
                'grade_levels',
                'is_active'
            )
        })
    )
    
    readonly_fields = ('available_stock', 'created_at', 'updated_at')
    actions = [export_selected_to_csv]

    def title_display(self, obj):
        """عرض عنوان الكتاب"""
        extra_info = []
        if obj.academic_year:
            extra_info.append(f"العام: {obj.academic_year}")
        if obj.edition_year:
            extra_info.append(f"الطبعة: {obj.edition_year}")
        if obj.pages_count:
            extra_info.append(f"{obj.pages_count} صفحة")
        
        extra_text = " | ".join(extra_info) if extra_info else ""
        
        return format_html(
            '<strong>{}</strong><br><small class="text-muted">{}</small>',
            obj.title,
            extra_text or "لا توجد تفاصيل إضافية"
        )
    title_display.short_description = 'الكتاب'

    def book_type_with_icon(self, obj):
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
        
        color_class = 'text-warning' if obj.book_type.startswith('MANAR_') else 'text-primary'
        
        return format_html(
            '{} <span class="{}">{}</span>',
            icons.get(obj.book_type, '<i class="fas fa-book"></i>'),
            color_class,
            obj.get_book_type_display()
        )
    book_type_with_icon.short_description = 'النوع'

    def stock_info(self, obj):
        """معلومات المخزون"""
        return format_html(
            'الإجمالي: {}<br>'
            'المتاح: <span class="text-success">{}</span><br>'
            'الموزع: <span class="text-info">{}</span><br>'
            'التالف: <span class="text-danger">{}</span>',
            obj.total_stock,
            obj.available_stock,
            obj.distributed_count,
            obj.damaged_count
        )
    stock_info.short_description = 'المخزون'

    def stock_status_display(self, obj):
        """حالة المخزون"""
        if obj.available_stock == 0:
            return format_html('<span class="badge" style="background-color: #dc3545; color: white;">نفد المخزون</span>')
        elif obj.available_stock <= obj.minimum_stock_level:
            return format_html('<span class="badge" style="background-color: #ffc107; color: black;">مخزون منخفض</span>')
        else:
            return format_html('<span class="badge" style="background-color: #198754; color: white;">متوفر</span>')
    stock_status_display.short_description = 'حالة المخزون'


# إدارة الكراسات
@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    list_display = (
        'name_display',
        'notebook_type',
        'size',
        'pages_count',
        'stock_info',
        'stock_status_display',
        'is_active'
    )
    
    list_filter = (
        'notebook_type',
        'size',
        'is_active',
        'created_at'
    )
    
    search_fields = ('name',)
    list_editable = ('is_active',)
    filter_horizontal = ('grade_levels',)
    
    actions = [export_selected_to_csv]

    def name_display(self, obj):
        """عرض اسم الكراسة"""
        return format_html(
            '<strong>{}</strong><br><small>{} صفحة</small>',
            obj.name,
            obj.pages_count
        )
    name_display.short_description = 'الكراسة'

    def stock_info(self, obj):
        """معلومات المخزون"""
        return format_html(
            'الإجمالي: {}<br>المتاح: <span class="text-success">{}</span>',
            obj.total_stock,
            obj.available_stock
        )
    stock_info.short_description = 'المخزون'

    def stock_status_display(self, obj):
        """حالة المخزون"""
        if obj.available_stock == 0:
            return format_html('<span class="badge" style="background-color: #dc3545; color: white;">نفد المخزون</span>')
        elif obj.available_stock <= obj.minimum_stock_level:
            return format_html('<span class="badge" style="background-color: #ffc107; color: black;">مخزون منخفض</span>')
        else:
            return format_html('<span class="badge" style="background-color: #198754; color: white;">متوفر</span>')
    stock_status_display.short_description = 'حالة المخزون'


# إدارة الأدوات المدرسية
@admin.register(SchoolSupply)
class SchoolSupplyAdmin(admin.ModelAdmin):
    list_display = (
        'name_display',
        'category',
        'unit',
        'stock_info',
        'stock_status_display',
        'is_active'
    )
    
    list_filter = (
        'category',
        'is_active',
        'created_at'
    )
    
    search_fields = ('name', 'description')
    list_editable = ('is_active',)
    filter_horizontal = ('grade_levels',)
    
    actions = [export_selected_to_csv]

    def name_display(self, obj):
        """عرض اسم الأداة"""
        description_text = obj.description[:50] + '...' if obj.description and len(obj.description) > 50 else obj.description or ""
        return format_html(
            '<strong>{}</strong><br><small class="text-muted">{}</small>',
            obj.name,
            description_text
        )
    name_display.short_description = 'الأداة'

    def stock_info(self, obj):
        """معلومات المخزون"""
        return format_html(
            'الإجمالي: {}<br>المتاح: <span class="text-success">{}</span>',
            obj.total_stock,
            obj.available_stock
        )
    stock_info.short_description = 'المخزون'

    def stock_status_display(self, obj):
        """حالة المخزون"""
        if obj.available_stock == 0:
            return format_html('<span class="badge" style="background-color: #dc3545; color: white;">نفد المخزون</span>')
        elif obj.available_stock <= obj.minimum_stock_level:
            return format_html('<span class="badge" style="background-color: #ffc107; color: black;">مخزون منخفض</span>')
        else:
            return format_html('<span class="badge" style="background-color: #198754; color: white;">متوفر</span>')
    stock_status_display.short_description = 'حالة المخزون'


# Inline للعناصر في الإيصالات
class BookReceiptItemInline(admin.TabularInline):
    model = BookReceiptItem
    extra = 1
    fields = ('book', 'quantity_received', 'quantity_damaged', 'unit_cost', 'total_cost')
    readonly_fields = ('total_cost',)


class NotebookReceiptItemInline(admin.TabularInline):
    model = NotebookReceiptItem
    extra = 1
    fields = ('notebook', 'quantity_received', 'quantity_damaged', 'unit_cost', 'total_cost')
    readonly_fields = ('total_cost',)


class SupplyReceiptItemInline(admin.TabularInline):
    model = SupplyReceiptItem
    extra = 1
    fields = ('supply', 'quantity_received', 'quantity_damaged', 'unit_cost', 'total_cost')
    readonly_fields = ('total_cost',)


# إدارة إيصالات الاستلام
@admin.register(StockReceipt)
class StockReceiptAdmin(admin.ModelAdmin):
    list_display = (
        'receipt_number',
        'supplier',
        'receipt_type',
        'receipt_date',
        'total_items_display',
        'total_cost_display',
        'received_by'
    )
    
    list_filter = (
        'receipt_type',
        'receipt_date',
        'supplier'
    )
    
    search_fields = ('receipt_number', 'supplier__name', 'invoice_number')
    date_hierarchy = 'receipt_date'
    
    fieldsets = (
        ('معلومات الإيصال', {
            'fields': (
                ('receipt_number', 'receipt_type'),
                ('supplier', 'receipt_date'),
                ('received_by', 'invoice_number')
            )
        }),
        
        ('الملخص', {
            'fields': (
                ('total_items', 'damaged_items'),
                'total_cost'
            )
        }),
        
        ('ملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('receipt_number', 'created_at', 'updated_at')
    
    def get_inlines(self, request, obj=None):
        """عرض inline حسب نوع الإيصال"""
        if obj:
            if obj.receipt_type == 'BOOKS':
                return [BookReceiptItemInline]
            elif obj.receipt_type == 'NOTEBOOKS':
                return [NotebookReceiptItemInline]
            elif obj.receipt_type == 'SUPPLIES':
                return [SupplyReceiptItemInline]
        return []

    def total_items_display(self, obj):
        """عرض إجمالي العناصر"""
        return format_html(
            '<span class="badge" style="background-color: #0d6efd; color: white;">{}</span>',
            obj.total_items
        )
    total_items_display.short_description = 'إجمالي العناصر'

    def total_cost_display(self, obj):
        """عرض إجمالي التكلفة"""
        return format_html(
            '<strong>{} ج.م</strong>',
            obj.total_cost
        )
    total_cost_display.short_description = 'إجمالي التكلفة'


# Inline لعناصر التوزيع
class BookDistributionItemInline(admin.TabularInline):
    model = BookDistributionItem
    extra = 0
    fields = ('book', 'quantity_requested', 'quantity_distributed', 'is_distributed', 'distribution_date', 'notes')
    readonly_fields = ('distribution_date',)


class NotebookDistributionItemInline(admin.TabularInline):
    model = NotebookDistributionItem
    extra = 0
    fields = ('notebook', 'quantity_requested', 'quantity_distributed', 'is_distributed', 'distribution_date', 'notes')
    readonly_fields = ('distribution_date',)


class SupplyDistributionItemInline(admin.TabularInline):
    model = SupplyDistributionItem
    extra = 0
    fields = ('supply', 'quantity_requested', 'quantity_distributed', 'is_distributed', 'distribution_date', 'notes')
    readonly_fields = ('distribution_date',)


# إدارة توزيعات الطلاب
@admin.register(StudentDistribution)
class StudentDistributionAdmin(admin.ModelAdmin):
    list_display = (
        'student_info',
        'distribution_date',
        'verification_status',
        'status_display',
        'total_items',
        'distributed_by'
    )
    
    list_filter = (
        'status',
        'first_installment_verified',
        'distribution_date',
        'distributed_by'
    )
    
    search_fields = ('student__name', 'student__national_number')
    date_hierarchy = 'distribution_date'
    
    inlines = [BookDistributionItemInline, NotebookDistributionItemInline, SupplyDistributionItemInline]
    
    fieldsets = (
        ('معلومات التوزيع', {
            'fields': (
                'student',
                ('distribution_date', 'distributed_by'),
                'status'
            )
        }),
        
        ('التحقق من الدفع', {
            'fields': (
                'first_installment_verified',
                'verification_date',
                'verification_notes'
            )
        }),
        
        ('ملخص التوزيع', {
            'fields': (
                'total_items',
                'notes'
            )
        })
    )
    
    readonly_fields = ('verification_date', 'created_at', 'updated_at')

    def student_info(self, obj):
        """معلومات الطالب"""
        return format_html(
            '<strong>{}</strong><br>'
            '<small>{} - {}</small>',
            obj.student.name,
            obj.student.national_number,
            getattr(obj.student, 'grade_name', 'غير محدد')
        )
    student_info.short_description = 'الطالب'

    def verification_status(self, obj):
        """حالة التحقق من الدفع"""
        if obj.first_installment_verified:
            return format_html('<span style="color: green;">✓ تم التحقق</span>')
        else:
            return format_html('<span style="color: red;">✗ غير محقق</span>')
    verification_status.short_description = 'حالة التحقق'

    def status_display(self, obj):
        """عرض حالة التوزيع"""
        colors = {
            'PENDING': '#ffc107',
            'PARTIAL': '#17a2b8',
            'COMPLETED': '#28a745',
            'CANCELLED': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span class="badge" style="background-color: {}; color: white;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'الحالة'


# إدارة النواقص
@admin.register(StockShortage)
class StockShortageAdmin(admin.ModelAdmin):
    list_display = (
        'item_info',
        'shortage_details',
        'priority_display',
        'status_display',
        'reported_by',
        'reported_date'
    )
    
    list_filter = (
        'item_type',
        'status',
        'priority',
        'reported_date'
    )
    
    search_fields = ('item_name', 'notes')
    date_hierarchy = 'reported_date'
    
    fieldsets = (
        ('معلومات العنصر', {
            'fields': (
                'item_type',
                'item_name',
                ('book', 'notebook', 'supply')
            )
        }),
        
        ('تفاصيل النقص', {
            'fields': (
                ('current_stock', 'required_quantity', 'shortage_quantity'),
                ('priority', 'status')
            )
        }),
        
        ('معلومات البلاغ', {
            'fields': (
                ('reported_by', 'reported_date'),
                'notes'
            )
        }),
        
        ('معلومات الحل', {
            'fields': (
                'resolution_notes',
                'resolved_date'
            ),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('reported_date', 'resolved_date')

    def item_info(self, obj):
        """معلومات العنصر"""
        return format_html(
            '<strong>{}</strong><br>'
            '<small class="text-muted">{}</small>',
            obj.item_name,
            obj.get_item_type_display()
        )
    item_info.short_description = 'العنصر'

    def shortage_details(self, obj):
        """تفاصيل النقص"""
        return format_html(
            'الحالي: {}<br>'
            'المطلوب: {}<br>'
            '<strong style="color: red;">النقص: {}</strong>',
            obj.current_stock,
            obj.required_quantity,
            obj.shortage_quantity
        )
    shortage_details.short_description = 'تفاصيل النقص'

    def priority_display(self, obj):
        """عرض الأولوية"""
        colors = {'HIGH': '#dc3545', 'MEDIUM': '#ffc107', 'LOW': '#17a2b8'}
        color = colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span class="badge" style="background-color: {}; color: white;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_display.short_description = 'الأولوية'

    def status_display(self, obj):
        """عرض الحالة"""
        colors = {
            'REPORTED': '#ffc107',
            'ACKNOWLEDGED': '#17a2b8',
            'ORDERED': '#007bff',
            'RESOLVED': '#28a745'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span class="badge" style="background-color: {}; color: white;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'الحالة'

