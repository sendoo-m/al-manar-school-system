# payments/admin.py - النسخة المصححة النهائية

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
from django.contrib.admin import SimpleListFilter
import csv
from datetime import datetime, date

# استيراد النماذج الموجودة فقط
from .models import Tuition, PaymentRecord, Discount

# مرشحات مخصصة
class PaymentStatusFilter(SimpleListFilter):
    title = 'حالة الدفع'
    parameter_name = 'payment_status'

    def lookups(self, request, model_admin):
        return (
            ('PAID', 'مدفوع'),
            ('PENDING', 'في الانتظار'),
            ('OVERDUE', 'متأخر'),
            ('PARTIALLY_PAID', 'مدفوع جزئياً'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(payment_status=self.value())
        return queryset

class PaymentMethodFilter(SimpleListFilter):
    title = 'طريقة الدفع'
    parameter_name = 'payment_method'

    def lookups(self, request, model_admin):
        return (
            ('cash', 'نقدي'),
            ('transfer', 'تحويل بنكي'),
            ('check', 'شيك'),
            ('card', 'بطاقة ائتمان'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(payment_method=self.value())
        return queryset

# إجراءات مخصصة
def export_tuitions_csv(modeladmin, request, queryset):
    """تصدير الأقساط إلى CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="tuitions_export_{datetime.now().strftime("%Y%m%d_%H%M")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'اسم الطالب', 'الرقم القومي', 'رقم القسط', 'مبلغ القسط', 
        'المبلغ المدفوع', 'المبلغ المتبقي', 'حالة الدفع', 'تاريخ الاستحقاق',
        'تاريخ الدفع', 'طريقة الدفع', 'مسؤول الدفع', 'رقم الإيصال'
    ])
    
    for tuition in queryset.select_related('student'):
        writer.writerow([
            tuition.student.name,
            tuition.student.national_number,
            tuition.installment_number,
            float(tuition.amount_tuition),
            float(tuition.amount_paid),
            float(tuition.remaining_amount),
            tuition.get_payment_status_display(),
            tuition.due_date.strftime('%Y-%m-%d') if tuition.due_date else '',
            tuition.payment_date.strftime('%Y-%m-%d %H:%M') if tuition.payment_date else '',
            tuition.get_payment_method_display(),
            tuition.payment_user,
            tuition.receipt_number
        ])
    
    return response

export_tuitions_csv.short_description = "تصدير الأقساط المحددة إلى CSV"

# إدارة الأقساط
@admin.register(Tuition)
class TuitionAdmin(admin.ModelAdmin):
    list_display = (
        'student_info',
        'installment_display',
        'amounts_display',
        'payment_status_display',
        'due_date_display',
        'payment_info'
    )
    
    list_filter = (
        PaymentStatusFilter,
        PaymentMethodFilter,
        'fee_type',
        'created_date',
        'due_date'
    )
    
    search_fields = (
        'student__name',
        'student__national_number',
        'installment_number',
        'receipt_number',
        'payment_user'
    )
    
    ordering = ('-created_date', '-installment_number')
    list_per_page = 25
    
    readonly_fields = (
        'created_date',
        'updated_date',
        'remaining_amount_display',
        'is_overdue_display'
    )
    
    fieldsets = (
        ('معلومات القسط', {
            'fields': (
                'student',
                'academic_year',
                'fee_type',
                'fee_name',
                'installment_number',
                ('amount_tuition', 'amount_paid'),
                'remaining_amount_display'
            )
        }),
        
        ('الخصومات', {
            'fields': (
                'applied_discount',
                'discount_amount'
            ),
            'classes': ('collapse',)
        }),
        
        ('تواريخ مهمة', {
            'fields': (
                'due_date',
                'payment_date',
                'created_date',
                'updated_date'
            )
        }),
        
        ('معلومات الدفع', {
            'fields': (
                'payment_status',
                'payment_method',
                'payment_user',
                'receipt_number'
            )
        }),
        
        ('ملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )
    
    actions = [export_tuitions_csv]
    
    def student_info(self, obj):
        """معلومات الطالب"""
        try:
            return format_html(
                '<strong>{}</strong><br>'
                '<small>الرقم القومي: {}</small><br>'
                '<small class="text-info">{}</small>',
                obj.student.name,
                obj.student.national_number,
                obj.get_fee_type_display()
            )
        except:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.student.name if obj.student else 'غير محدد',
                obj.student.national_number if obj.student else 'غير محدد'
            )
    student_info.short_description = 'الطالب'
    student_info.admin_order_field = 'student__name'

    def installment_display(self, obj):
        """عرض رقم القسط"""
        return format_html(
            '<div class="text-center">'
            '<strong style="font-size: 1.2em;">#{}</strong><br>'
            '<small class="text-muted">قسط رقم</small>'
            '</div>',
            obj.installment_number
        )
    installment_display.short_description = 'رقم القسط'
    installment_display.admin_order_field = 'installment_number'

    def amounts_display(self, obj):
        """عرض المبالغ"""
        try:
            remaining = obj.remaining_amount
            percentage = (obj.amount_paid / obj.amount_tuition * 100) if obj.amount_tuition > 0 else 0
            
            color_class = 'success' if remaining <= 0 else 'warning' if remaining < obj.amount_tuition else 'danger'
            
            return format_html(
                '<div>'
                '<strong>القسط:</strong> {:.2f} ج.م<br>'
                '<strong>المدفوع:</strong> {:.2f} ج.م<br>'
                '<strong>المتبقي:</strong> <span class="text-{}">{:.2f} ج.م</span><br>'
                '<small class="text-muted">نسبة الدفع: {:.1f}%</small>'
                '</div>',
                float(obj.amount_tuition),
                float(obj.amount_paid),
                color_class,
                float(remaining),
                percentage
            )
        except Exception:
            return format_html('<span class="text-danger">خطأ في العرض</span>')
    amounts_display.short_description = 'المبالغ'

    def payment_status_display(self, obj):
        """عرض حالة الدفع"""
        status_colors = {
            'PAID': 'success',
            'PENDING': 'warning',
            'OVERDUE': 'danger',
            'PARTIALLY_PAID': 'info'
        }
        color = status_colors.get(obj.payment_status, 'secondary')
        
        return format_html(
            '<span class="badge badge-{}" style="font-size: 0.9em;">{}</span>',
            color,
            obj.get_payment_status_display()
        )
    payment_status_display.short_description = 'حالة الدفع'
    payment_status_display.admin_order_field = 'payment_status'

    def due_date_display(self, obj):
        """عرض تاريخ الاستحقاق"""
        if not obj.due_date:
            return '-'
        
        try:
            today = date.today()
            days_diff = (obj.due_date - today).days
            
            if days_diff < 0:
                status_class = 'text-danger'
                status_text = 'متأخر {} يوم'.format(abs(days_diff))
            elif days_diff == 0:
                status_class = 'text-warning'
                status_text = 'اليوم'
            elif days_diff <= 7:
                status_class = 'text-info'
                status_text = 'خلال {} أيام'.format(days_diff)
            else:
                status_class = 'text-muted'
                status_text = 'خلال {} يوم'.format(days_diff)
            
            return format_html(
                '<div>'
                '<strong>{}</strong><br>'
                '<small class="{}">{}</small>'
                '</div>',
                obj.due_date.strftime('%Y-%m-%d'),
                status_class,
                status_text
            )
        except:
            return format_html('<strong>{}</strong>', obj.due_date.strftime('%Y-%m-%d'))
    due_date_display.short_description = 'تاريخ الاستحقاق'
    due_date_display.admin_order_field = 'due_date'

    def payment_info(self, obj):
        """معلومات الدفع"""
        try:
            if obj.payment_date and obj.payment_status == 'PAID':
                return format_html(
                    '<div>'
                    '<strong>تاريخ الدفع:</strong><br>{}<br>'
                    '<strong>الطريقة:</strong> {}<br>'
                    '<strong>الموظف:</strong> {}<br>'
                    '{}'
                    '</div>',
                    obj.payment_date.strftime('%Y-%m-%d %H:%M'),
                    obj.get_payment_method_display(),
                    obj.payment_user or 'غير محدد',
                    '<strong>رقم الإيصال: {}</strong>'.format(obj.receipt_number) if obj.receipt_number else ''
                )
            else:
                return format_html(
                    '<div class="text-muted">'
                    '<small>لم يتم الدفع بعد</small><br>'
                    '<strong>الموظف المسؤول:</strong><br>{}'
                    '</div>',
                    obj.payment_user or 'غير محدد'
                )
        except:
            return format_html('<span class="text-muted">غير متاح</span>')
    payment_info.short_description = 'معلومات الدفع'

    def remaining_amount_display(self, obj):
        """المبلغ المتبقي (للقراءة فقط)"""
        try:
            remaining = obj.remaining_amount
            if remaining <= 0:
                return format_html('<span class="text-success">مسدد بالكامل</span>')
            else:
                return format_html('<span class="text-warning">{:.2f} ج.م</span>', float(remaining))
        except:
            return format_html('<span class="text-muted">غير محدد</span>')
    remaining_amount_display.short_description = 'المبلغ المتبقي'

    def is_overdue_display(self, obj):
        """حالة التأخير (للقراءة فقط)"""
        try:
            if obj.is_overdue:
                return format_html('<span class="text-danger">متأخر</span>')
            else:
                return format_html('<span class="text-success">في الموعد</span>')
        except:
            return format_html('<span class="text-muted">غير محدد</span>')
    is_overdue_display.short_description = 'حالة التأخير'

    def get_queryset(self, request):
        """تحسين الاستعلامات"""
        return super().get_queryset(request).select_related(
            'student',
            'academic_year',
            'applied_discount'
        )

# إدارة سجلات المدفوعات
@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = (
        'payment_basic_info',
        'amount_paid',
        'payment_date',
        'payment_method',
        'payment_user'
    )
    
    list_filter = (
        'payment_method',
        'payment_date'
    )
    
    search_fields = (
        'tuition__student__name',
        'payment_user'
    )
    
    ordering = ('-payment_date',)
    readonly_fields = ('payment_date',)

    def payment_basic_info(self, obj):
        """معلومات الدفع الأساسية"""
        try:
            return format_html(
                '<strong>{}</strong><br>'
                '<small>قسط رقم {} - {}</small>',
                obj.tuition.student.name,
                obj.tuition.installment_number,
                obj.tuition.student.national_number
            )
        except:
            return format_html('<span class="text-muted">معلومات غير متاحة</span>')
    payment_basic_info.short_description = 'معلومات الدفع'

# إدارة الخصومات
@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'discount_amount',
        'reason_short',
        'is_active',
        'created_date'
    )
    
    list_filter = (
        'is_active',
        'created_date',
        'academic_year'
    )
    
    search_fields = (
        'student__name',
        'reason'
    )
    
    list_editable = ('is_active',)
    
    fieldsets = (
        ('معلومات الخصم', {
            'fields': (
                'student',
                'academic_year',
                ('discount_amount', 'discount_percentage'),
                'reason'
            )
        }),
        ('الحالة', {
            'fields': (
                'is_active',
                'created_date'
            )
        })
    )
    
    readonly_fields = ('created_date',)
    
    def reason_short(self, obj):
        """عرض مختصر للسبب"""
        return obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason
    reason_short.short_description = 'سبب الخصم'
