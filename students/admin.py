from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, path
from django.utils.html import format_html
from django.db import models, transaction
from django.forms import TextInput, Textarea
from django.utils.safestring import mark_safe
from django.contrib.admin import SimpleListFilter
from django.db.models import Count, Sum, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
import csv
import io
import openpyxl
from datetime import datetime
import json

# استيراد النماذج
from .models import Student, UserProfile, ArchiveStudent
from school_settings.models import AcademicYear as SettingsAcademicYear, EducationLevel, GradeLevel

# تخصيص رأس لوحة الإدارة
admin.site.site_header = "نظام إدارة مدرسة المنار"
admin.site.site_title = "إدارة مدرسة المنار"
admin.site.index_title = _('لوحة التحكم الرئيسية')

# مرشحات مخصصة
class GenderFilter(SimpleListFilter):
    title = _('الجنس')
    parameter_name = 'gender'

    def lookups(self, request, model_admin):
        return (
            ('M', _('ذكر')),
            ('F', _('أنثى')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'M':
            return queryset.filter(gender='M')
        if self.value() == 'F':
            return queryset.filter(gender='F')

class FinancialStatusFilter(SimpleListFilter):
    title = _('الحالة المالية')
    parameter_name = 'financial_status'

    def lookups(self, request, model_admin):
        return (
            ('paid', _('مسدد بالكامل')),
            ('partial', _('مسدد جزئياً')),
            ('owing', _('مستحق عليه')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'paid':
            return queryset.filter(total_owed__lte=0)
        elif self.value() == 'partial':
            return queryset.filter(total_owed__gt=0, total_owed__lt=models.F('total_fees'))
        elif self.value() == 'owing':
            return queryset.filter(total_owed__gte=models.F('total_fees'))

class AgeRangeFilter(SimpleListFilter):
    title = _('الفئة العمرية')
    parameter_name = 'age_range'

    def lookups(self, request, model_admin):
        return (
            ('3-6', _('3-6 سنوات (حضانة)')),
            ('6-12', _('6-12 سنة (ابتدائي)')),
            ('12-15', _('12-15 سنة (إعدادي)')),
            ('15-18', _('15-18 سنة (ثانوي)')),
        )

    def queryset(self, request, queryset):
        if self.value() == '3-6':
            return queryset.filter(age__gte=3, age__lte=6)
        elif self.value() == '6-12':
            return queryset.filter(age__gte=6, age__lte=12)
        elif self.value() == '12-15':
            return queryset.filter(age__gte=12, age__lte=15)
        elif self.value() == '15-18':
            return queryset.filter(age__gte=15, age__lte=18)

# إجراءات مخصصة
def export_students_to_csv(modeladmin, request, queryset):
    """تصدير الطلاب المحددين إلى ملف CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="students_export_{datetime.now().strftime("%Y%m%d_%H%M")}.csv"'
    response.write('\ufeff')  # BOM for Arabic support
    
    writer = csv.writer(response)
    # كتابة الرؤوس
    writer.writerow([
        'اسم الطالب', 'الرقم القومي', 'العمر', 'الجنس', 'تاريخ الميلاد',
        'رقم الهاتف', 'العنوان', 'الصف الدراسي', 'المرحلة التعليمية',
        'إجمالي المصروفات', 'إجمالي المدفوعات', 'المستحقات',
        'اسم ولي الأمر', 'هاتف ولي الأمر', 'تاريخ التسجيل'
    ])
    
    # كتابة البيانات
    for student in queryset:
        writer.writerow([
            student.name,
            student.national_number,
            student.age,
            'ذكر' if student.gender == 'M' else 'أنثى' if student.gender == 'F' else '',
            student.date_of_birth.strftime('%Y-%m-%d') if student.date_of_birth else '',
            student.phone_number,
            student.address,
            student.grade_name if hasattr(student, 'grade_name') else '',
            student.education_level_name if hasattr(student, 'education_level_name') else '',
            float(student.total_fees or 0),
            float(student.total_payments or 0),
            float(student.total_owed or 0),
            student.parent_name,
            student.parent_phone,
            student.created_at.strftime('%Y-%m-%d %H:%M') if student.created_at else ''
        ])
    
    return response

export_students_to_csv.short_description = "تصدير الطلاب المحددين إلى CSV"

def archive_selected_students(modeladmin, request, queryset):
    """أرشفة الطلاب المحددين"""
    archived_count = 0
    for student in queryset:
        # إنشاء نسخة في الأرشيف
        ArchiveStudent.objects.create(
            archive_name=student.name,
            archive_national_number=student.national_number,
            archive_age=student.age or 0,
            archive_gender=student.gender,
            archive_date_of_birth=student.date_of_birth,
            archive_academic_year=str(student.academic_year) if student.academic_year else "غير محدد",
            archive_grade_level=student.grade_name if hasattr(student, 'grade_name') else "غير محدد",
            archive_education_level=student.education_level_name if hasattr(student, 'education_level_name') else "غير محدد",
            archive_total_payments=student.total_payments or 0,
            archive_total_fees=student.total_fees or 0,
            archive_total_owed=student.total_owed or 0,
            archived_reason='أرشفة من لوحة الإدارة'
        )
        archived_count += 1
    
    # حذف الطلاب الأصليين
    deleted_count = queryset.count()
    queryset.delete()
    
    modeladmin.message_user(request, f'تم أرشفة {archived_count} طالب وحذفهم من النظام الحالي.')

archive_selected_students.short_description = "أرشفة الطلاب المحددين"

# Mixin للاستيراد والتصدير
class StudentImportExportMixin:
    """Mixin لإضافة وظائف الاستيراد والتصدير للطلاب"""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('export/', self.admin_site.admin_view(self.export_students), name='students_student_export'),
            path('import/', self.admin_site.admin_view(self.import_students_view), name='students_student_import'),
            path('import/process/', self.admin_site.admin_view(self.process_import), name='students_student_import_process'),
            path('export/template/', self.admin_site.admin_view(self.download_template), name='students_student_export_template'),
        ]
        return custom_urls + urls
    
    def export_students(self, request):
        """تصدير بيانات الطلاب"""
        export_format = request.GET.get('format', 'excel')
        grade_filter = request.GET.get('grade')
        
        # فلترة الطلاب
        queryset = Student.objects.filter(is_active=True).select_related(
            'academic_year',
            'grade_level__education_level'
        )
        
        if grade_filter:
            queryset = queryset.filter(grade_level_id=grade_filter)
        
        if export_format == 'csv':
            return self._export_csv(queryset)
        elif export_format == 'excel':
            return self._export_excel(queryset)
        elif export_format == 'json':
            return self._export_json(queryset)
        else:
            messages.error(request, 'صيغة التصدير غير مدعومة')
            return redirect('admin:students_student_changelist')
    
    def _export_csv(self, queryset):
        """تصدير CSV"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="students_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        response.write('\ufeff')  # BOM للدعم العربي
        
        writer = csv.writer(response)
        
        # رأس الجدول
        headers = [
            'الاسم*', 'الرقم القومي*', 'العمر', 'النوع (M/F)', 'تاريخ الميلاد (YYYY-MM-DD)',
            'رقم الهاتف', 'العنوان', 'العام الدراسي', 'الصف الدراسي',
            'اسم ولي الأمر', 'هاتف ولي الأمر', 'بريد ولي الأمر',
            'إجمالي المصروفات', 'إجمالي المدفوعات', 'المستحقات',
            'تاريخ الإنشاء', 'الحالة'
        ]
        writer.writerow(headers)
        
        # البيانات
        for student in queryset:
            row = [
                student.name,
                student.national_number,
                student.age or '',
                student.gender if student.gender else '',
                student.date_of_birth.strftime('%Y-%m-%d') if student.date_of_birth else '',
                student.phone_number or '',
                student.address or '',
                student.academic_year.name if student.academic_year else '',
                student.grade_level.name if student.grade_level else '',
                student.parent_name or '',
                student.parent_phone or '',
                student.parent_email or '',
                float(student.total_fees or 0),
                float(student.total_payments or 0),
                float(student.total_owed or 0),
                student.created_at.strftime('%Y-%m-%d %H:%M:%S') if student.created_at else '',
                'نشط' if student.is_active else 'غير نشط'
            ]
            writer.writerow(row)
        
        return response
    
    def _export_excel(self, queryset):
        """تصدير Excel"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "بيانات الطلاب"
        
        # تنسيق الرؤوس
        headers = [
            'الاسم*', 'الرقم القومي*', 'العمر', 'النوع (M/F)', 'تاريخ الميلاد',
            'رقم الهاتف', 'العنوان', 'العام الدراسي', 'الصف الدراسي',
            'اسم ولي الأمر', 'هاتف ولي الأمر', 'بريد ولي الأمر',
            'إجمالي المصروفات', 'إجمالي المدفوعات', 'المستحقات',
            'تاريخ الإنشاء', 'الحالة'
        ]
        
        # إضافة الرؤوس مع التنسيق
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
            cell.fill = openpyxl.styles.PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            cell.alignment = openpyxl.styles.Alignment(horizontal="center")
        
        # البيانات
        for row_num, student in enumerate(queryset, 2):
            data = [
                student.name,
                student.national_number,
                student.age or '',
                student.gender or '',
                student.date_of_birth.strftime('%Y-%m-%d') if student.date_of_birth else '',
                student.phone_number or '',
                student.address or '',
                student.academic_year.name if student.academic_year else '',
                student.grade_level.name if student.grade_level else '',
                student.parent_name or '',
                student.parent_phone or '',
                student.parent_email or '',
                float(student.total_fees or 0),
                float(student.total_payments or 0),
                float(student.total_owed or 0),
                student.created_at.strftime('%Y-%m-%d %H:%M:%S') if student.created_at else '',
                'نشط' if student.is_active else 'غير نشط'
            ]
            
            for col, value in enumerate(data, 1):
                cell = ws.cell(row=row_num, column=col, value=value)
                if col in [13, 14, 15]:  # الأعمدة المالية
                    cell.number_format = '#,##0.00'
        
        # ضبط عرض الأعمدة
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # حفظ الملف
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="students_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        return response
    
    def _export_json(self, queryset):
        """تصدير JSON"""
        data = []
        for student in queryset:
            student_data = {
                'name': student.name,
                'national_number': student.national_number,
                'age': student.age,
                'gender': student.gender,
                'date_of_birth': student.date_of_birth.isoformat() if student.date_of_birth else None,
                'phone_number': student.phone_number,
                'address': student.address,
                'academic_year': student.academic_year.name if student.academic_year else None,
                'grade_level': student.grade_level.name if student.grade_level else None,
                'parent_name': student.parent_name,
                'parent_phone': student.parent_phone,
                'parent_email': student.parent_email,
                'total_fees': float(student.total_fees or 0),
                'total_payments': float(student.total_payments or 0),
                'total_owed': float(student.total_owed or 0),
                'created_at': student.created_at.isoformat() if student.created_at else None,
                'is_active': student.is_active,
            }
            data.append(student_data)
        
        response = JsonResponse({
            'students': data,
            'export_date': datetime.now().isoformat(),
            'total_count': len(data)
        }, json_dumps_params={'ensure_ascii': False, 'indent': 2})
        
        response['Content-Disposition'] = f'attachment; filename="students_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
        
        return response
    
    def download_template(self, request):
        """تحميل قالب الاستيراد"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "قالب استيراد الطلاب"
        
        # الرؤوس المطلوبة
        headers = [
            'الاسم*', 'الرقم القومي*', 'العمر', 'النوع (M/F)', 'تاريخ الميلاد (YYYY-MM-DD)',
            'رقم الهاتف', 'العنوان', 'العام الدراسي', 'الصف الدراسي',
            'اسم ولي الأمر', 'هاتف ولي الأمر', 'بريد ولي الأمر'
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
            cell.fill = openpyxl.styles.PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            cell.alignment = openpyxl.styles.Alignment(horizontal="center")
        
        # إضافة بيانات تجريبية
        sample_data = [
            'أحمد محمد علي', '30012010012345', '14', 'M', '2010-01-01',
            '01234567890', 'القاهرة، مصر الجديدة', '2024-2025', 'الثاني الإعدادي',
            'محمد علي أحمد', '01098765432', 'ahmed.parent@email.com'
        ]
        
        for col, value in enumerate(sample_data, 1):
            ws.cell(row=2, column=col, value=value)
        
        # إضافة تعليمات
        instructions_row = 4
        instructions = [
            "تعليمات الاستيراد:",
            "1. الحقول المميزة بـ * مطلوبة",
            "2. النوع: M للذكر، F للأنثى",
            "3. تاريخ الميلاد بصيغة: YYYY-MM-DD",
            "4. الرقم القومي يجب أن يكون 14 رقم",
            "5. احذف هذه التعليمات قبل الاستيراد",
            "6. يمكن ترك الحقول الاختيارية فارغة"
        ]
        
        for i, instruction in enumerate(instructions):
            cell = ws.cell(row=instructions_row + i, column=1, value=instruction)
            if i == 0:
                cell.font = openpyxl.styles.Font(bold=True, color="D32F2F")
            else:
                cell.font = openpyxl.styles.Font(color="666666")
        
        # ضبط عرض الأعمدة
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 30)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="student_import_template.xlsx"'
        
        return response
    
    def import_students_view(self, request):
        """صفحة استيراد الطلاب"""
        grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
        academic_years = SettingsAcademicYear.objects.filter(is_active=True).order_by('-start_date')
        
        context = {
            'title': 'استيراد بيانات الطلاب',
            'grade_levels': grade_levels,
            'academic_years': academic_years,
            'opts': Student._meta,
        }
        return render(request, 'admin/students/student/import_students.html', context)
    
    def process_import(self, request):
        """معالجة ملف الاستيراد"""
        if request.method != 'POST':
            return redirect('admin:students_student_import')
        
        file = request.FILES.get('import_file')
        if not file:
            messages.error(request, 'يرجى اختيار ملف للاستيراد')
            return redirect('admin:students_student_import')
        
        try:
            if file.name.endswith('.xlsx'):
                success_count, errors = self._process_excel_import(file, request)
            elif file.name.endswith('.csv'):
                success_count, errors = self._process_csv_import(file, request)
            else:
                messages.error(request, 'صيغة الملف غير مدعومة. يرجى استخدام Excel أو CSV')
                return redirect('admin:students_student_import')
            
            if success_count > 0:
                messages.success(request, f'تم استيراد {success_count} طالب بنجاح')
            
            if errors:
                error_msg = f'حدثت {len(errors)} أخطاء أثناء الاستيراد:\n' + '\n'.join(errors[:5])
                if len(errors) > 5:
                    error_msg += f'\n... و {len(errors) - 5} أخطاء أخرى'
                messages.warning(request, error_msg)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء معالجة الملف: {str(e)}')
        
        return redirect('admin:students_student_changelist')
    
    def _process_excel_import(self, file, request):
        """معالجة ملف Excel"""
        wb = openpyxl.load_workbook(file)
        ws = wb.active
        
        success_count = 0
        errors = []
        
        # الحصول على الرؤوس من الصف الأول
        headers = [cell.value for cell in ws[1]]
        
        with transaction.atomic():
            for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
                if not any(row):  # تخطي الصفوف الفارغة
                    continue
                
                try:
                    student_data = dict(zip(headers, row))
                    student = self._create_student_from_data(student_data, row_num)
                    if student:
                        success_count += 1
                
                except ValidationError as e:
                    errors.append(f'الصف {row_num}: {", ".join(e.messages)}')
                except Exception as e:
                    errors.append(f'الصف {row_num}: {str(e)}')
        
        return success_count, errors
    
    def _process_csv_import(self, file, request):
        """معالجة ملف CSV"""
        success_count = 0
        errors = []
        
        # قراءة الملف مع دعم UTF-8
        file_content = file.read().decode('utf-8-sig')
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        with transaction.atomic():
            for row_num, row in enumerate(csv_reader, 2):
                try:
                    student = self._create_student_from_data(row, row_num)
                    if student:
                        success_count += 1
                
                except ValidationError as e:
                    errors.append(f'الصف {row_num}: {", ".join(e.messages)}')
                except Exception as e:
                    errors.append(f'الصف {row_num}: {str(e)}')
        
        return success_count, errors
    
    def _create_student_from_data(self, data, row_num):
        """إنشاء طالب من البيانات المستوردة"""
        from datetime import datetime
        
        # التحقق من البيانات المطلوبة
        name = str(data.get('الاسم*', '') or data.get('الاسم', '') or data.get('name', '')).strip()
        national_number = str(data.get('الرقم القومي*', '') or data.get('الرقم القومي', '') or data.get('national_number', '')).strip()
        
        if not name or not national_number:
            raise ValidationError('الاسم والرقم القومي مطلوبان')
        
        # التحقق من عدم تكرار الرقم القومي
        if Student.objects.filter(national_number=national_number).exists():
            raise ValidationError(f'الرقم القومي {national_number} موجود مسبقاً')
        
        # معالجة البيانات الاختيارية
        age = data.get('العمر', '') or data.get('age', '')
        if age:
            try:
                age = int(age)
            except (ValueError, TypeError):
                age = None
        
        gender = str(data.get('النوع (M/F)', '') or data.get('النوع', '') or data.get('gender', '')).strip().upper()
        if gender and gender not in ['M', 'F']:
            gender = None
        
        # معالجة تاريخ الميلاد
        date_of_birth = None
        birth_date_str = str(data.get('تاريخ الميلاد (YYYY-MM-DD)', '') or data.get('تاريخ الميلاد', '') or data.get('date_of_birth', '')).strip()
        if birth_date_str:
            try:
                date_of_birth = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            except ValueError:
                try:
                    date_of_birth = datetime.strptime(birth_date_str, '%d/%m/%Y').date()
                except ValueError:
                    pass
        
        # معالجة الصف والعام الدراسي
        grade_level = None
        grade_name = str(data.get('الصف الدراسي', '') or data.get('grade_level', '')).strip()
        if grade_name:
            try:
                grade_level = GradeLevel.objects.filter(name__icontains=grade_name, is_active=True).first()
            except:
                pass
        
        academic_year = None
        year_name = str(data.get('العام الدراسي', '') or data.get('academic_year', '')).strip()
        if year_name:
            try:
                academic_year = SettingsAcademicYear.objects.filter(name__icontains=year_name, is_active=True).first()
            except:
                pass
        
        # إنشاء الطالب
        student = Student.objects.create(
            name=name,
            national_number=national_number,
            age=age,
            gender=gender,
            date_of_birth=date_of_birth,
            phone_number=str(data.get('رقم الهاتف', '') or data.get('phone_number', '')).strip(),
            address=str(data.get('العنوان', '') or data.get('address', '')).strip(),
            grade_level=grade_level,
            academic_year=academic_year,
            parent_name=str(data.get('اسم ولي الأمر', '') or data.get('parent_name', '')).strip(),
            parent_phone=str(data.get('هاتف ولي الأمر', '') or data.get('parent_phone', '')).strip(),
            parent_email=str(data.get('بريد ولي الأمر', '') or data.get('parent_email', '')).strip(),
            is_active=True
        )
        
        return student

# إدارة الطلاب المتقدمة
@admin.register(Student)
class StudentAdmin(StudentImportExportMixin, admin.ModelAdmin):
    # العرض الأساسي
    list_display = (
        'student_avatar',
        'name_with_id', 
        'national_number_formatted',
        'age_with_gender', 
        'academic_info',
        'financial_status_display',
        'contact_info',
        'registration_date',
        'is_active_display'
    )
    
    # الفلاتر
    list_filter = (
        'is_active',
        GenderFilter,
        FinancialStatusFilter,
        AgeRangeFilter,
        'grade_level__education_level',
        'academic_year',
        'created_at',
    )
    
    # البحث
    search_fields = (
        'name', 
        'national_number', 
        'phone_number',
        'parent_name',
        'parent_phone',
        'address'
    )
    
    # الترتيب والترقيم
    ordering = ('-created_at', 'name')
    list_per_page = 25
    
    # الحقول القابلة للقراءة فقط
    readonly_fields = (
        'age', 
        'date_of_birth', 
        'gender',
        'total_payments', 
        'total_fees', 
        'total_owed',
        'created_at', 
        'updated_at',
        'student_detail_link'
    )
    
    # تنظيم الحقول في النموذج
    fieldsets = (
        ('البيانات الأساسية', {
            'fields': (
                'name', 
                'national_number',
                ('age', 'gender', 'date_of_birth'),
                'is_active'
            ),
            'classes': ('wide',)
        }),
        
        ('معلومات الاتصال', {
            'fields': (
                'phone_number',
                'address'
            ),
            'classes': ('wide',)
        }),
        
        ('البيانات الأكاديمية', {
            'fields': (
                'academic_year',
                'grade_level'
            ),
            'classes': ('wide',)
        }),
        
        ('بيانات ولي الأمر', {
            'fields': (
                'parent_name',
                'parent_phone', 
                'parent_email'
            ),
            'classes': ('wide', 'collapse')
        }),
        
        ('البيانات المالية', {
            'fields': (
                ('total_fees', 'total_payments', 'total_owed'),
            ),
            'classes': ('wide',)
        }),
        
        ('معلومات النظام', {
            'fields': (
                ('created_at', 'updated_at'),
                'student_detail_link'
            ),
            'classes': ('collapse',)
        }),
    )
    
    # الإجراءات
    actions = [export_students_to_csv, archive_selected_students]
    
    # تخصيص النماذج
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '40'})},
        models.TextField: {'widget': Textarea(attrs={'rows': 3, 'cols': 40})},
    }

    def student_avatar(self, obj):
        """أيقونة الطالب"""
        gender_icon = 'fa-male text-primary' if obj.gender == 'M' else 'fa-female text-danger' if obj.gender == 'F' else 'fa-user text-secondary'
        return format_html(
            '<i class="fas {} fa-2x" title="{}"></i>',
            gender_icon,
            obj.name
        )
    student_avatar.short_description = ''

    def name_with_id(self, obj):
        """الاسم مع رابط للتفاصيل"""
        return format_html(
            '<strong><a href="{}" title="عرض تفاصيل الطالب">{}</a></strong>',
            reverse('admin:students_student_change', args=[obj.pk]),
            obj.name
        )
    name_with_id.short_description = 'اسم الطالب'
    name_with_id.admin_order_field = 'name'

    def national_number_formatted(self, obj):
        """الرقم القومي منسق"""
        if obj.national_number and len(obj.national_number) == 14:
            formatted = f"{obj.national_number[:2]} {obj.national_number[2:7]} {obj.national_number[7:14]}"
            return format_html('<code>{}</code>', formatted)
        return obj.national_number or '-'
    national_number_formatted.short_description = 'الرقم القومي'
    national_number_formatted.admin_order_field = 'national_number'

    def age_with_gender(self, obj):
        """العمر والجنس"""
        gender_display = 'ذكر' if obj.gender == 'M' else 'أنثى' if obj.gender == 'F' else 'غير محدد'
        age_display = f"{obj.age} سنة" if obj.age else 'غير محدد'
        
        gender_color = 'primary' if obj.gender == 'M' else 'danger' if obj.gender == 'F' else 'secondary'
        
        return format_html(
            '{}<br><span class="badge badge-{}">{}</span>',
            age_display,
            gender_color,
            gender_display
        )
    age_with_gender.short_description = 'العمر والجنس'
    age_with_gender.admin_order_field = 'age'

    def academic_info(self, obj):
        """المعلومات الأكاديمية"""
        grade_info = obj.grade_level.name if obj.grade_level else 'غير محدد'
        education_info = obj.grade_level.education_level.name if (obj.grade_level and obj.grade_level.education_level) else 'غير محدد'
        year_info = str(obj.academic_year) if obj.academic_year else 'غير محدد'
        
        return format_html(
            '<strong>{}</strong><br><small>{}</small><br><small class="text-muted">{}</small>',
            grade_info,
            education_info,
            year_info
        )
    academic_info.short_description = 'المعلومات الأكاديمية'

    def financial_status_display(self, obj):
        """عرض الحالة المالية"""
        try:
            status = obj.get_financial_status()
            color = obj.get_status_color()
        except:
            status = 'غير محدد'
            color = 'secondary'
        
        # تحديد لون Bootstrap
        bootstrap_colors = {
            'success': 'success',
            'warning': 'warning',
            'danger': 'danger',
            'secondary': 'secondary'
        }
        bootstrap_color = bootstrap_colors.get(color, 'secondary')
        
        return format_html(
            '<span class="badge badge-{}">{}</span><br>'
            '<small>مستحق: <strong>{}</strong> ج.م</small>',
            bootstrap_color,
            status,
            obj.total_owed or 0
        )
    financial_status_display.short_description = 'الحالة المالية'
    financial_status_display.admin_order_field = 'total_owed'

    def contact_info(self, obj):
        """معلومات الاتصال"""
        phone = obj.phone_number or obj.parent_phone or 'غير متوفر'
        parent_name = obj.parent_name or 'غير محدد'
        
        return format_html(
            '<i class="fas fa-phone"></i> {}<br>'
            '<i class="fas fa-user"></i> <small>{}</small>',
            phone,
            parent_name
        )
    contact_info.short_description = 'معلومات الاتصال'

    def registration_date(self, obj):
        """تاريخ التسجيل"""
        if obj.created_at:
            return format_html(
                '{}<br><small class="text-muted">{}</small>',
                obj.created_at.strftime('%Y-%m-%d'),
                obj.created_at.strftime('%H:%M')
            )
        return '-'
    registration_date.short_description = 'تاريخ التسجيل'
    registration_date.admin_order_field = 'created_at'

    def is_active_display(self, obj):
        """حالة النشاط مع رابط للتغيير"""
        if obj.is_active:
            status_badge = '<span class="badge badge-success">نشط</span>'
        else:
            status_badge = '<span class="badge badge-secondary">غير نشط</span>'
        
        toggle_url = reverse('admin:students_student_change', args=[obj.pk])
        return format_html(
            '{}<br><small><a href="{}">تغيير الحالة</a></small>',
            status_badge,
            toggle_url
        )
    is_active_display.short_description = 'الحالة'
    is_active_display.admin_order_field = 'is_active'

    def student_detail_link(self, obj):
        """رابط تفاصيل الطالب"""
        if obj.pk:
            try:
                url = reverse('students:student_detail', args=[obj.pk])
                return format_html('<a href="{}" target="_blank">عرض في الموقع</a>', url)
            except:
                return "-"
        return "-"
    student_detail_link.short_description = 'رابط التفاصيل'

    def get_queryset(self, request):
        """تحسين الاستعلامات"""
        return super().get_queryset(request).select_related(
            'academic_year',
            'grade_level__education_level'
        ).prefetch_related(
            'grade_level'
        )

    def changelist_view(self, request, extra_context=None):
        """إضافة إحصائيات للصفحة الرئيسية وتفعيل الاستيراد/التصدير"""
        extra_context = extra_context or {}
        
        # إحصائيات سريعة
        queryset = self.get_queryset(request)
        extra_context['total_students'] = queryset.filter(is_active=True).count()
        extra_context['male_students'] = queryset.filter(gender='M', is_active=True).count()
        extra_context['female_students'] = queryset.filter(gender='F', is_active=True).count()
        extra_context['students_owing'] = queryset.filter(total_owed__gt=0, is_active=True).count()
        extra_context['total_owed'] = queryset.filter(is_active=True).aggregate(
            total=Sum('total_owed')
        )['total'] or 0
        
        # تفعيل أزرار الاستيراد والتصدير
        extra_context['show_import_export'] = True
        
        return super().changelist_view(request, extra_context)

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }

# باقي فئات الإدارة
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('get_user_full_name', 'get_username', 'phone_number', 'address', 'get_user_status')
    list_filter = ('user__is_active', 'user__is_staff')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone_number', 'address')
    readonly_fields = ('user',)

    def get_user_full_name(self, obj):
        full_name = obj.user.get_full_name()
        if full_name:
            return format_html('<strong>{}</strong>', full_name)
        return format_html('<em>{}</em>', obj.user.username)
    get_user_full_name.short_description = 'الاسم الكامل'

    def get_username(self, obj):
        return format_html('<code>{}</code>', obj.user.username)
    get_username.short_description = 'اسم المستخدم'

    def get_user_status(self, obj):
        if obj.user.is_superuser:
            return format_html('<span class="badge badge-danger">مدير عام</span>')
        elif obj.user.is_staff:
            return format_html('<span class="badge badge-warning">موظف</span>')
        elif obj.user.is_active:
            return format_html('<span class="badge badge-success">نشط</span>')
        else:
            return format_html('<span class="badge badge-secondary">غير نشط</span>')
    get_user_status.short_description = 'حالة المستخدم'


@admin.register(ArchiveStudent)
class ArchiveStudentAdmin(admin.ModelAdmin):
    list_display = (
        'archive_name', 
        'archive_national_number', 
        'archive_age_gender',
        'archive_academic_info',
        'archive_financial_summary',
        'archived_date',
        'archived_reason'
    )
    list_filter = (
        'archive_gender', 
        'archived_date',
        'archived_reason'
    )
    search_fields = ('archive_name', 'archive_national_number', 'archived_reason')
    readonly_fields = ('archived_date',)
    date_hierarchy = 'archived_date'
    ordering = ('-archived_date',)

    def archive_age_gender(self, obj):
        gender_display = 'ذكر' if obj.archive_gender == 'M' else 'أنثى' if obj.archive_gender == 'F' else 'غير محدد'
        gender_color = 'primary' if obj.archive_gender == 'M' else 'danger' if obj.archive_gender == 'F' else 'secondary'
        
        return format_html(
            '{} سنة<br><span class="badge badge-{}">{}</span>',
            obj.archive_age,
            gender_color,
            gender_display
        )
    archive_age_gender.short_description = 'العمر والجنس'

    def archive_academic_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.archive_grade_level,
            obj.archive_education_level
        )
    archive_academic_info.short_description = 'المعلومات الأكاديمية'

    def archive_financial_summary(self, obj):
        return format_html(
            'مدفوع: <strong>{}</strong> ج.م<br>'
            'مستحق: <strong>{}</strong> ج.م',
            obj.archive_total_payments,
            obj.archive_total_owed
        )
    archive_financial_summary.short_description = 'الملخص المالي'

    def has_add_permission(self, request):
        """منع الإضافة المباشرة - الأرشفة تتم تلقائياً"""
        return False
