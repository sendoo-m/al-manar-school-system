"""
Django Admin Configuration for School Settings
نظام إدارة إعدادات المدرسة - إعدادات لوحة الإدارة المُصححة

هذا الملف يحتوي على جميع إعدادات لوحة الإدارة الخاصة بنظام إدارة المدرسة
"""

from django.contrib import admin
from django.utils.html import format_html
from django.forms import ModelForm, ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.admin import SimpleListFilter
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Q, Count
import logging

# إعداد السجل
logger = logging.getLogger(__name__)

# دالة للحصول على عنوان IP
def get_client_ip(request):
    """الحصول على عنوان IP للمستخدم"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# دالة تسجيل تغييرات الإعدادات
def log_settings_change(user, action, setting_type, obj=None, old_value='', new_value='', description='', request=None):
    """تسجيل تغييرات الإعدادات"""
    try:
        from .models import SettingsLog
        
        object_id = obj.pk if obj else None
        object_name = str(obj) if obj else ''
        
        ip_address = None
        user_agent = ''
        
        if request:
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        SettingsLog.objects.create(
            user=user,
            action=action,
            setting_type=setting_type,
            object_id=object_id,
            object_name=object_name[:200] if object_name else '',
            old_value=str(old_value)[:1000] if old_value else '',
            new_value=str(new_value)[:1000] if new_value else '',
            description=description[:500] if description else '',
            ip_address=ip_address,
            user_agent=user_agent
        )
        
    except Exception as e:
        logger.error(f"خطأ في تسجيل تغيير الإعدادات: {e}")

# استيراد النماذج الأساسية
from .models import (
    SystemSettings, 
    AcademicYear, 
    EducationLevel, 
    GradeLevel,
    SchoolFeesSettings,
    DiscountSettings,
    SystemRole,
    SettingsLog
)

# =====================================================
# إعدادات عامة للوحة الإدارة
# =====================================================

admin.site.site_header = "🏫 نظام إدارة إعدادات المدرسة"
admin.site.site_title = "إعدادات المدرسة"
admin.site.index_title = "لوحة التحكم الرئيسية"
admin.site.empty_value_display = '(غير محدد)'

# =====================================================
# الفلاتر المخصصة
# =====================================================

class ActiveFilter(SimpleListFilter):
    """فلتر الحالة النشطة/غير النشطة"""
    title = _('حالة التفعيل')
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return (
            ('1', _('✅ نشط')),
            ('0', _('❌ غير نشط')),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(is_active=True)
        if self.value() == '0':
            return queryset.filter(is_active=False)
        return queryset


class CurrentYearFilter(SimpleListFilter):
    """فلتر العام الحالي"""
    title = _('العام الحالي')
    parameter_name = 'is_current'

    def lookups(self, request, model_admin):
        return (
            ('1', _('⭐ العام الحالي')),
            ('0', _('📅 أعوام أخرى')),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(is_current=True)
        if self.value() == '0':
            return queryset.filter(is_current=False)
        return queryset

# =====================================================
# نماذج مخصصة للتحقق من البيانات
# =====================================================

class SystemSettingsForm(ModelForm):
    """نموذج مخصص لإعدادات النظام مع التحقق من صحة البيانات"""
    
    class Meta:
        model = SystemSettings
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        
        # التحقق من وجود إعداد واحد فقط
        if not self.instance.pk and SystemSettings.objects.exists():
            raise ValidationError(
                '⚠️ يمكن وجود إعدادات نظام واحدة فقط في النظام'
            )
        
        # التحقق من صحة البيانات المالية
        late_penalty = cleaned_data.get('late_payment_penalty_rate', 0)
        if late_penalty and (late_penalty < 0 or late_penalty > 50):
            raise ValidationError(
                'نسبة غرامة التأخير يجب أن تكون بين 0% و 50%'
            )
        
        # التحقق من عدد الطلاب بالفصل
        max_students = cleaned_data.get('max_students_per_classroom', 0)
        if max_students and (max_students < 5 or max_students > 100):
            raise ValidationError(
                'الحد الأقصى للطلاب يجب أن يكون بين 5 و 100 طالب'
            )
        
        return cleaned_data

# =====================================================
# إدارة إعدادات النظام
# =====================================================

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """إدارة إعدادات النظام العامة"""
    
    form = SystemSettingsForm
    
    list_display = (
        'school_name_display',
        'contact_info_display',
        'currency_display',
        'system_settings_display',
        'last_updated_display'
    )
    
    fieldsets = (
        ('🏫 معلومات المدرسة الأساسية', {
            'fields': (
                ('school_name', 'school_name_en'),
                ('school_logo', 'school_stamp'),
                'school_address',
                ('school_phone', 'school_fax'),
                ('school_email', 'school_website')
            ),
            'classes': ('wide',),
            'description': 'المعلومات الأساسية التي تظهر في جميع المستندات والتقارير'
        }),
        
        ('💰 الإعدادات المالية', {
            'fields': (
                ('currency_symbol', 'currency_name'),
                'default_installments_count',
                ('late_payment_penalty_rate', 'grace_period_days')
            ),
            'classes': ('wide',),
            'description': 'إعدادات العملة والأقساط والغرامات'
        }),
        
        ('⚙️ إعدادات النظام العامة', {
            'fields': (
                ('system_language', 'max_students_per_classroom'),
            ),
            'classes': ('wide',)
        }),
        
        ('🧾 إعدادات الإيصالات والتقارير', {
            'fields': (
                'receipt_footer_text',
                'receipt_terms'
            ),
            'classes': ('collapse',),
            'description': 'النصوص التي تظهر في الإيصالات والمستندات الرسمية'
        }),
        
        ('📊 معلومات النظام', {
            'fields': ('created_date', 'updated_date', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_date', 'updated_date')
    
    def school_name_display(self, obj):
        """عرض معلومات المدرسة مع الشعار"""
        logo_html = ""
        if obj.school_logo:
            logo_html = f'<img src="{obj.school_logo.url}" style="width: 32px; height: 32px; border-radius: 4px; margin-left: 8px;">'
        
        return format_html(
            '<div style="display: flex; align-items: center;">'
            '{}'
            '<div>'
            '<strong style="font-size: 14px;">{}</strong><br>'
            '<small style="color: #666;">{}</small>'
            '</div>'
            '</div>',
            logo_html,
            obj.school_name,
            obj.school_name_en or 'لا يوجد اسم بالإنجليزية'
        )
    school_name_display.short_description = '🏫 معلومات المدرسة'

    def contact_info_display(self, obj):
        """عرض معلومات الاتصال"""
        contact_items = []
        
        if obj.school_phone:
            contact_items.append(f'📞 {obj.school_phone}')
        if obj.school_email:
            contact_items.append(f'📧 {obj.school_email[:20]}...' if len(obj.school_email) > 20 else f'📧 {obj.school_email}')
        if obj.school_website:
            contact_items.append('🌐 موقع إلكتروني')
        
        if not contact_items:
            return format_html('<span style="color: #999;">لا توجد معلومات اتصال</span>')
        
        return format_html('<br>'.join(contact_items))
    contact_info_display.short_description = '📞 معلومات الاتصال'

    def currency_display(self, obj):
        """عرض معلومات العملة"""
        return format_html(
            '<div style="text-align: center;">'
            '<strong style="font-size: 16px; color: #2e7d32;">{}</strong><br>'
            '<small style="color: #666;">💱 {}</small>'
            '</div>',
            obj.currency_symbol or '؟',
            obj.currency_name or 'غير محدد'
        )
    currency_display.short_description = '💰 العملة'

    def system_settings_display(self, obj):
        """عرض الإعدادات العامة"""
        language_emoji = '🇸🇦' if obj.system_language == 'ar' else '🇺🇸'
        
        return format_html(
            '<div style="font-size: 12px;">'
            '<div style="margin-bottom: 4px;"><strong>اللغة:</strong> {} {}</div>'
            '<div style="margin-bottom: 4px;"><strong>أقساط:</strong> {} قسط</div>'
            '<div style="margin-bottom: 4px;"><strong>طلاب/فصل:</strong> {} طالب</div>'
            '<div><strong>غرامة:</strong> {}% - سماح {} يوم</div>'
            '</div>',
            language_emoji,
            'العربية' if obj.system_language == 'ar' else 'English',
            obj.default_installments_count or 0,
            obj.max_students_per_classroom or 0,
            obj.late_payment_penalty_rate or 0,
            obj.grace_period_days or 0
        )
    system_settings_display.short_description = '⚙️ إعدادات النظام'

    def last_updated_display(self, obj):
        """عرض آخر تحديث"""
        if obj.updated_by:
            return format_html(
                '<div style="font-size: 11px; color: #666;">'
                '<div>📅 {}</div>'
                '<div>👤 {}</div>'
                '</div>',
                obj.updated_date.strftime('%Y-%m-%d %H:%M'),
                obj.updated_by.get_full_name() or obj.updated_by.username
            )
        return format_html(
            '<div style="font-size: 11px; color: #666;">📅 {}</div>',
            obj.updated_date.strftime('%Y-%m-%d %H:%M')
        )
    last_updated_display.short_description = '🕒 آخر تحديث'

    def has_add_permission(self, request):
        """منع إضافة أكثر من إعداد واحد"""
        return not SystemSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """منع حذف الإعدادات"""
        return False

    def save_model(self, request, obj, form, change):
        """حفظ مع تسجيل المستخدم المُحدِّث"""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        
        # تسجيل العملية
        action = 'تحديث' if change else 'إنشاء'
        logger.info(f'{action} إعدادات النظام بواسطة {request.user.username}')

# =====================================================
# إدارة السنوات الدراسية
# =====================================================

@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    """إدارة السنوات الدراسية"""
    
    list_display = (
        'name_with_status_display',
        'duration_display',
        'terms_display',
        'status_display',
        'actions_display'
    )
    
    list_filter = (
        CurrentYearFilter,
        ActiveFilter,
        'start_date',
        'created_date'
    )
    
    search_fields = ('name',)
    list_per_page = 20
    ordering = ('-start_date',)
    
    fieldsets = (
        ('📅 معلومات السنة الدراسية', {
            'fields': (
                'name',
                ('start_date', 'end_date'),
                ('is_current', 'is_active')
            ),
            'classes': ('wide',)
        }),
        
        ('📚 إعدادات الفصول الدراسية', {
            'fields': (
                ('first_term_start', 'first_term_end'),
                ('second_term_start', 'second_term_end')
            ),
            'classes': ('wide',),
            'description': 'تواريخ بداية ونهاية كل فصل دراسي'
        }),
        
        ('📊 معلومات النظام', {
            'fields': ('created_date', 'updated_date'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_date', 'updated_date')

    def name_with_status_display(self, obj):
        """عرض اسم السنة مع الحالة"""
        status_icon = "⭐" if obj.is_current else "📅"
        active_icon = "✅" if obj.is_active else "❌"
        
        return format_html(
            '<div>'
            '<strong style="font-size: 14px;">{} {}</strong> {}<br>'
            '<small style="color: #666;">تم الإنشاء: {}</small>'
            '</div>',
            status_icon,
            obj.name,
            active_icon,
            obj.created_date.strftime('%Y-%m-%d')
        )
    name_with_status_display.short_description = '📚 السنة الدراسية'

    def duration_display(self, obj):
        """عرض مدة السنة الدراسية"""
        if obj.start_date and obj.end_date:
            duration = (obj.end_date - obj.start_date).days
            months = duration // 30
            
            return format_html(
                '<div style="text-align: center;">'
                '<div style="font-weight: bold; color: #1976d2;">{}</div>'
                '<div style="font-size: 11px; color: #666;">إلى</div>'
                '<div style="font-weight: bold; color: #1976d2;">{}</div>'
                '<small style="color: #888;">({} شهر تقريباً)</small>'
                '</div>',
                obj.start_date.strftime('%d/%m/%Y'),
                obj.end_date.strftime('%d/%m/%Y'),
                months
            )
        return format_html('<span style="color: #999;">غير محدد</span>')
    duration_display.short_description = '⏱️ مدة السنة'

    def terms_display(self, obj):
        """عرض معلومات الفصول الدراسية"""
        terms_info = []
        
        if obj.first_term_start and obj.first_term_end:
            first_duration = (obj.first_term_end - obj.first_term_start).days
            terms_info.append(f'📖 الأول: {first_duration} يوم')
        
        if obj.second_term_start and obj.second_term_end:
            second_duration = (obj.second_term_end - obj.second_term_start).days
            terms_info.append(f'📘 الثاني: {second_duration} يوم')
        
        if not terms_info:
            return format_html('<span style="color: #999;">غير مُعرَّف</span>')
        
        return format_html(
            '<div style="font-size: 11px;">{}</div>',
            '<br>'.join(terms_info)
        )
    terms_display.short_description = '📚 الفصول الدراسية'

    def status_display(self, obj):
        """عرض حالة السنة الدراسية"""
        if obj.is_current:
            status_class = 'success'
            status_text = 'العام الحالي'
            status_icon = '⭐'
        elif obj.is_active:
            status_class = 'info'
            status_text = 'نشط'
            status_icon = '✅'
        else:
            status_class = 'secondary'
            status_text = 'غير نشط'
            status_icon = '❌'
        
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px;">'
            '{} {}'
            '</span>',
            '#4caf50' if status_class == 'success' else '#2196f3' if status_class == 'info' else '#9e9e9e',
            status_icon,
            status_text
        )
    status_display.short_description = '📊 الحالة'

    def actions_display(self, obj):
        """عرض الإجراءات المتاحة"""
        actions = []
        
        if not obj.is_current and obj.is_active:
            actions.append('🔄 يمكن تفعيله كحالي')
        
        if obj.is_active:
            actions.append('📝 قابل للتعديل')
        
        if not actions:
            actions.append('🔒 محدود الإجراءات')
        
        return format_html(
            '<div style="font-size: 10px; color: #666;">{}</div>',
            '<br>'.join(actions)
        )
    actions_display.short_description = '⚡ إجراءات متاحة'

    def save_model(self, request, obj, form, change):
        """حفظ مع التأكد من وجود عام حالي واحد فقط"""
        if obj.is_current:
            # إلغاء تحديد باقي السنوات كحالية
            AcademicYear.objects.exclude(pk=obj.pk).update(is_current=False)
            logger.info(f'تم تعيين {obj.name} كعام حالي بواسطة {request.user.username}')
        
        super().save_model(request, obj, form, change)

# =====================================================
# إدارة المراحل التعليمية - مُصححة
# =====================================================

@admin.register(EducationLevel)
class EducationLevelAdmin(admin.ModelAdmin):
    """إدارة المراحل التعليمية"""
    
    list_display = (
        'name_display',
        'age_range_display',
        'statistics_display',
        'order_display',
        'status_display'
    )
    
    list_filter = (
        ActiveFilter,
        'order'
    )
    
    search_fields = ('name', 'name_en', 'description')
    ordering = ('order', 'name')
    list_per_page = 25
    
    fieldsets = (
        ('🎓 معلومات المرحلة التعليمية', {
            'fields': (
                ('name', 'name_en'),
                'description',
                ('min_age', 'max_age'),
                ('order', 'is_active')
            ),
            'classes': ('wide',)
        }),
    )

    def name_display(self, obj):
        """عرض اسم المرحلة مع معلومات إضافية"""
        return format_html(
            '<div>'
            '<strong style="font-size: 14px; color: #1976d2;">{}</strong><br>'
            '<small style="color: #666;">{}</small><br>'
            '<small style="color: #888; font-style: italic;">{}</small>'
            '</div>',
            obj.name,
            obj.name_en or 'لا يوجد اسم بالإنجليزية',
            obj.description[:50] + '...' if obj.description and len(obj.description) > 50 else obj.description or 'لا يوجد وصف'
        )
    name_display.short_description = '🎓 اسم المرحلة'

    def age_range_display(self, obj):
        """عرض الفئة العمرية مع رموز تعبيرية"""
        min_age = obj.min_age or 0
        max_age = obj.max_age or 0
        
        # تحديد الرمز المناسب للفئة العمرية
        if max_age <= 5:
            emoji = '🧒'
            stage = 'طفولة مبكرة'
        elif max_age <= 11:
            emoji = '👦'
            stage = 'طفولة'
        elif max_age <= 14:
            emoji = '👨‍🎓'
            stage = 'مراهقة مبكرة'
        else:
            emoji = '👨‍💼'
            stage = 'مراهقة'
        
        return format_html(
            '<div style="text-align: center;">'
            '<div style="font-size: 24px;">{}</div>'
            '<div style="font-weight: bold; color: #4caf50;">{} - {} سنة</div>'
            '<small style="color: #666;">{}</small>'
            '</div>',
            emoji,
            min_age,
            max_age,
            stage
        )
    age_range_display.short_description = '👶 الفئة العمرية'

    def statistics_display(self, obj):
        """عرض إحصائيات المرحلة"""
        try:
            grades_count = obj.gradelevel_set.filter(is_active=True).count()
            total_grades = obj.gradelevel_set.count()
            
            # محاولة حساب عدد الطلاب إذا كان النموذج متاحاً
            students_count = 0
            try:
                from students.models import Student
                students_count = Student.objects.filter(
                    grade_level__education_level=obj,
                    is_active=True
                ).count()
            except ImportError:
                pass
            
            return format_html(
                '<div style="font-size: 12px;">'
                '<div style="margin-bottom: 4px;"><strong>📚 الصفوف النشطة:</strong> {}/{}</div>'
                '<div style="margin-bottom: 4px;"><strong>👥 الطلاب:</strong> {}</div>'
                '<div><strong>📊 الترتيب:</strong> #{}</div>'
                '</div>',
                grades_count,
                total_grades,
                students_count,
                obj.order
            )
        except Exception as e:
            logger.error(f'خطأ في حساب إحصائيات المرحلة {obj.name}: {e}')
            return format_html('<span style="color: #f44336;">خطأ في البيانات</span>')
    statistics_display.short_description = '📊 إحصائيات'

    def order_display(self, obj):
        """عرض ترتيب المرحلة"""
        return format_html(
            '<div style="text-align: center;">'
            '<span style="background: #2196f3; color: white; padding: 4px 8px; border-radius: 50%; font-weight: bold;">'
            '{}'
            '</span>'
            '</div>',
            obj.order
        )
    order_display.short_description = '🔢 الترتيب'

    def status_display(self, obj):
        """عرض حالة المرحلة"""
        if obj.is_active:
            return format_html(
                '<span style="background: #4caf50; color: white; padding: 4px 12px; border-radius: 15px; font-size: 11px;">'
                '✅ نشطة'
                '</span>'
            )
        else:
            return format_html(
                '<span style="background: #f44336; color: white; padding: 4px 12px; border-radius: 15px; font-size: 11px;">'
                '❌ معطلة'
                '</span>'
            )
    status_display.short_description = '⚡ الحالة'

    def get_queryset(self, request):
        """تحسين الاستعلامات مع حساب الإحصائيات"""
        return super().get_queryset(request).prefetch_related('gradelevel_set')

# =====================================================
# إدارة الصفوف الدراسية - مُصححة
# =====================================================

@admin.register(GradeLevel)
class GradeLevelAdmin(admin.ModelAdmin):
    """إدارة الصفوف الدراسية"""
    
    list_display = (
        'name_with_education_level_display',
        'grade_info_display',
        'students_statistics_display',
        'order_and_status_display'
    )
    
    list_filter = (
        'education_level',
        ActiveFilter,
        'typical_age',
        'grade_number',
        'order'
    )
    
    search_fields = ('name', 'name_en', 'education_level__name')
    ordering = ('education_level__order', 'order', 'grade_number')
    list_per_page = 30
    
    fieldsets = (
        ('📚 معلومات الصف الدراسي', {
            'fields': (
                'education_level',
                ('name', 'name_en'),
                ('grade_number', 'typical_age'),
                ('order', 'is_active')
            ),
            'classes': ('wide',)
        }),
    )

    def name_with_education_level_display(self, obj):
        """عرض اسم الصف مع المرحلة التعليمية"""
        # تحديد الرمز المناسب للمرحلة
        age = obj.typical_age or 0
        if age <= 5:
            emoji = '🧒'
        elif age <= 11:
            emoji = '👦'
        elif age <= 14:
            emoji = '👨‍🎓'
        else:
            emoji = '👨‍💼'
        
        return format_html(
            '<div>'
            '<div style="font-weight: bold; color: #1976d2; margin-bottom: 4px;">'
            '{} <strong>{}</strong>'
            '</div>'
            '<div style="color: #666; font-size: 11px; margin-bottom: 2px;">{}</div>'
            '<div style="color: #888; font-size: 10px;">{}</div>'
            '</div>',
            emoji,
            obj.name,
            obj.education_level.name,
            obj.name_en or 'لا يوجد اسم بالإنجليزية'
        )
    name_with_education_level_display.short_description = '📚 الصف والمرحلة'

    def grade_info_display(self, obj):
        """عرض معلومات الصف التفصيلية"""
        return format_html(
            '<div style="text-align: center;">'
            '<div style="background: #e3f2fd; padding: 8px; border-radius: 8px; margin-bottom: 4px;">'
            '<div style="font-weight: bold; color: #1976d2;">رقم الصف: {}</div>'
            '</div>'
            '<div style="background: #f3e5f5; padding: 8px; border-radius: 8px; margin-bottom: 4px;">'
            '<div style="color: #7b1fa2;">العمر المتوقع: {} سنة</div>'
            '</div>'
            '<div style="background: #fff3e0; padding: 6px; border-radius: 6px;">'
            '<div style="color: #ef6c00; font-size: 11px;">ترتيب: #{}</div>'
            '</div>'
            '</div>',
            obj.grade_number or '؟',
            obj.typical_age or '؟',
            obj.order
        )
    grade_info_display.short_description = '📋 معلومات الصف'

    def students_statistics_display(self, obj):
        """عرض إحصائيات الطلاب"""
        try:
            # محاولة حساب عدد الطلاب
            students_count = 0
            groups_count = 0
            
            try:
                from students.models import Student, StudentGroup
                students_count = Student.objects.filter(
                    grade_level=obj,
                    is_active=True
                ).count()
                
                groups_count = StudentGroup.objects.filter(
                    grade_level=obj,
                    is_active=True
                ).count()
            except ImportError:
                pass
            
            # تحديد لون الإحصائية حسب العدد
            if students_count == 0:
                color = '#f44336'
                status = 'فارغ'
            elif students_count < 20:
                color = '#ff9800'
                status = 'قليل'
            elif students_count < 30:
                color = '#4caf50'
                status = 'مثالي'
            else:
                color = '#2196f3'
                status = 'ممتلئ'
            
            return format_html(
                '<div style="text-align: center;">'
                '<div style="background: {}; color: white; padding: 8px; border-radius: 8px; margin-bottom: 4px;">'
                '<div style="font-size: 18px; font-weight: bold;">{}</div>'
                '<div style="font-size: 10px;">طالب</div>'
                '</div>'
                '<div style="font-size: 11px; color: #666; margin-bottom: 2px;">📚 {} مجموعة</div>'
                '<div style="font-size: 10px; color: {}; font-weight: bold;">{}</div>'
                '</div>',
                color,
                students_count,
                groups_count,
                color,
                status
            )
        except Exception as e:
            logger.error(f'خطأ في حساب إحصائيات الصف {obj.name}: {e}')
            return format_html(
                '<div style="color: #f44336; font-size: 11px; text-align: center;">'
                '❌ خطأ في البيانات'
                '</div>'
            )
    students_statistics_display.short_description = '👥 إحصائيات الطلاب'

    def order_and_status_display(self, obj):
        """عرض الترتيب والحالة"""
        status_color = '#4caf50' if obj.is_active else '#f44336'
        status_text = 'نشط' if obj.is_active else 'معطل'
        status_icon = '✅' if obj.is_active else '❌'
        
        return format_html(
            '<div style="text-align: center;">'
            '<div style="background: #e0e0e0; padding: 6px; border-radius: 6px; margin-bottom: 6px;">'
            '<div style="font-weight: bold; color: #424242;">ترتيب #{}</div>'
            '</div>'
            '<div style="background: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px;">'
            '{} {}'
            '</div>'
            '</div>',
            obj.order,
            status_color,
            status_icon,
            status_text
        )
    order_and_status_display.short_description = '📊 ترتيب وحالة'

    def get_queryset(self, request):
        """تحسين الاستعلامات"""
        return super().get_queryset(request).select_related('education_level')

# =====================================================
# إدارة إعدادات المصاريف المدرسية - مُصححة
# =====================================================

@admin.register(SchoolFeesSettings)
class SchoolFeesSettingsAdmin(admin.ModelAdmin):
    """إدارة إعدادات المصروفات المدرسية"""
    
    list_display = (
        'fee_name',
        'grade_and_year_display',
        'fee_type',
        'amount_display',
        'installments_display',
        'status_display'
    )
    
    list_filter = (
        'fee_type',
        'is_mandatory',
        ActiveFilter,
        'academic_year',
        'grade_level__education_level'
    )
    
    search_fields = ('fee_name', 'grade_level__name', 'academic_year__name')
    ordering = ('academic_year__name', 'grade_level__order', 'fee_name')
    
    fieldsets = (
        ('💰 معلومات المصروفات', {
            'fields': (
                ('academic_year', 'grade_level'),
                ('fee_type', 'fee_name'),
                ('is_mandatory', 'is_active')
            )
        }),
        
        ('💵 المبالغ والأقساط', {
            'fields': (
                'total_amount',
                ('installments_count', 'installment_amount'),
                ('first_installment_due_date', 'installment_interval_days')
            )
        })
    )
    
    readonly_fields = ('installment_amount',)

    def grade_and_year_display(self, obj):
        """عرض الصف والسنة الدراسية"""
        return format_html(
            '<div>'
            '<strong>{}</strong><br>'
            '<small style="color: #666;">{}</small>'
            '</div>',
            obj.grade_level.name if obj.grade_level else 'غير محدد',
            obj.academic_year.name if obj.academic_year else 'غير محدد'
        )
    grade_and_year_display.short_description = '📚 الصف والسنة'

    def amount_display(self, obj):
        """عرض المبلغ مع العملة"""
        return format_html(
            '<div style="text-align: center; font-weight: bold; color: #2e7d32;">'
            '{} ج.م'
            '</div>',
            obj.total_amount or 0
        )
    amount_display.short_description = '💰 المبلغ الإجمالي'

    def installments_display(self, obj):
        """عرض معلومات الأقساط"""
        return format_html(
            '<div style="font-size: 12px;">'
            '<div><strong>عدد الأقساط:</strong> {}</div>'
            '<div><strong>قيمة القسط:</strong> {} ج.م</div>'
            '</div>',
            obj.installments_count or 0,
            obj.installment_amount or 0
        )
    installments_display.short_description = '📊 الأقساط'

    def status_display(self, obj):
        """عرض حالة المصروفات"""
        mandatory_color = '#f44336' if obj.is_mandatory else '#4caf50'
        mandatory_text = 'إجبارية' if obj.is_mandatory else 'اختيارية'
        
        active_color = '#4caf50' if obj.is_active else '#9e9e9e'
        active_text = 'نشطة' if obj.is_active else 'معطلة'
        
        return format_html(
            '<div>'
            '<div style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-bottom: 2px;">'
            '{}'
            '</div>'
            '<div style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px;">'
            '{}'
            '</div>'
            '</div>',
            mandatory_color, mandatory_text,
            active_color, active_text
        )
    status_display.short_description = '⚡ الحالة'

# =====================================================
# إدارة سجل التغييرات - جديد
# =====================================================

@admin.register(SettingsLog)
class SettingsLogAdmin(admin.ModelAdmin):
    """إدارة سجل تغييرات الإعدادات"""
    
    list_display = (
        'user_display',
        'action_display',
        'setting_type_display',
        'object_display',
        'timestamp_display',
        'ip_address'
    )
    
    list_filter = (
        'action',
        'setting_type',
        'timestamp',
        'user'
    )
    
    search_fields = (
        'user__username',
        'user__first_name', 
        'user__last_name',
        'object_name',
        'description',
        'ip_address'
    )
    
    ordering = ('-timestamp',)
    list_per_page = 50
    
    readonly_fields = (
        'user', 'action', 'setting_type', 'object_id', 'object_name',
        'old_value', 'new_value', 'description', 'timestamp',
        'ip_address', 'user_agent'
    )
    
    def has_add_permission(self, request):
        """منع إضافة سجلات يدوياً"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """منع تعديل السجلات"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """منع حذف السجلات - للمراجعة فقط"""
        return request.user.is_superuser

    def user_display(self, obj):
        """عرض معلومات المستخدم"""
        if obj.user:
            return format_html(
                '<div>'
                '<strong>{}</strong><br>'
                '<small style="color: #666;">{}</small>'
                '</div>',
                obj.user.get_full_name() or obj.user.username,
                obj.user.email or f'@{obj.user.username}'
            )
        return format_html('<span style="color: #999;">مستخدم محذوف</span>')
    user_display.short_description = '👤 المستخدم'

    def action_display(self, obj):
        """عرض نوع العملية مع أيقونة"""
        action_colors = {
            'CREATE': '#4caf50',
            'UPDATE': '#ff9800',
            'DELETE': '#f44336',
            'VIEW': '#2196f3',
            'LOGIN': '#9c27b0',
            'LOGOUT': '#607d8b'
        }
        
        action_icons = {
            'CREATE': '➕',
            'UPDATE': '✏️',
            'DELETE': '🗑️',
            'VIEW': '👁️',
            'LOGIN': '🔐',
            'LOGOUT': '🚪'
        }
        
        color = action_colors.get(obj.action, '#9e9e9e')
        icon = action_icons.get(obj.action, '❓')
        
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px;">'
            '{} {}'
            '</span>',
            color,
            icon,
            obj.get_action_display()
        )
    action_display.short_description = '⚡ العملية'

    def setting_type_display(self, obj):
        """عرض نوع الإعداد"""
        return format_html(
            '<span style="background: #e3f2fd; color: #1976d2; padding: 3px 8px; border-radius: 8px; font-size: 10px;">'
            '{}'
            '</span>',
            obj.get_setting_type_display()
        )
    setting_type_display.short_description = '📋 نوع الإعداد'

    def object_display(self, obj):
        """عرض معلومات الكائن"""
        if obj.object_name:
            return format_html(
                '<div style="font-size: 12px;">'
                '<strong>#{}</strong><br>'
                '<span style="color: #666;">{}</span>'
                '</div>',
                obj.object_id or '؟',
                obj.object_name[:30] + '...' if len(obj.object_name) > 30 else obj.object_name
            )
        return format_html('<span style="color: #999;">-</span>')
    object_display.short_description = '📦 الكائن'

    def timestamp_display(self, obj):
        """عرض التوقيت"""
        return format_html(
            '<div style="font-size: 11px;">'
            '<div style="color: #333;">{}</div>'
            '<div style="color: #666;">{}</div>'
            '</div>',
            obj.timestamp.strftime('%Y-%m-%d'),
            obj.timestamp.strftime('%H:%M:%S')
        )
    timestamp_display.short_description = '🕒 التوقيت'

logger.info('تم تحميل إعدادات لوحة الإدارة المُصححة بنجاح')
