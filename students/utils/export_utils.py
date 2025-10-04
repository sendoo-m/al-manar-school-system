# students/utils/export_utils.py
import csv
import json
import xlsxwriter
from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum
from datetime import datetime

# إصلاح الاستيراد
from students.models import Student  # تغيير من .models إلى students.models

class StudentExporter:
    """فئة تصدير بيانات الطلاب بصيغ متعددة"""
    
    def __init__(self, queryset=None):
        self.queryset = queryset or Student.objects.filter(is_active=True)
    
    def export_csv(self, request):
        """تصدير CSV مع دعم العربية"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="students_export_{timestamp}.csv"'
        
        # إضافة BOM للدعم العربي
        response.write('\ufeff'.encode('utf8'))
        
        writer = csv.writer(response)
        
        # العناوين
        headers = [
            'رقم الطالب', 'الاسم', 'الرقم القومي', 'تاريخ الميلاد', 'العمر', 'الجنس',
            'رقم الهاتف', 'العنوان', 'المرحلة التعليمية', 'الصف الدراسي', 
            'العام الدراسي', 'اسم ولي الأمر', 'هاتف ولي الأمر', 'بريد ولي الأمر',
            'إجمالي المصروفات', 'إجمالي المدفوعات', 'المستحقات', 'الحالة المالية',
            'تاريخ التسجيل', 'آخر تحديث', 'الحالة'
        ]
        writer.writerow(headers)
        
        # البيانات
        for student in self.queryset.select_related('grade_level__education_level', 'academic_year'):
            row = [
                student.id,
                student.name,
                student.national_number,
                student.date_of_birth.strftime('%Y-%m-%d') if student.date_of_birth else '',
                student.age or 0,
                'ذكر' if student.gender == 'M' else 'أنثى' if student.gender == 'F' else 'غير محدد',
                student.phone_number or '',
                student.address or '',
                student.education_level_name,
                student.grade_name,
                str(student.academic_year) if student.academic_year else '',
                student.parent_name or '',
                student.parent_phone or '',
                student.parent_email or '',
                float(student.total_fees),
                float(student.total_payments),
                float(student.total_owed),
                student.get_financial_status(),
                student.created_at.strftime('%Y-%m-%d %H:%M') if student.created_at else '',
                student.updated_at.strftime('%Y-%m-%d %H:%M') if student.updated_at else '',
                'نشط' if student.is_active else 'غير نشط'
            ]
            writer.writerow(row)
        
        return response
    
    def export_excel(self, request):
        """تصدير Excel متقدم مع تنسيق"""
        try:
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'strings_to_numbers': True})
            
            # أنماط التنسيق
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'align': 'center',
                'border': 1
            })
            
            data_format = workbook.add_format({
                'align': 'right',
                'border': 1
            })
            
            number_format = workbook.add_format({
                'num_format': '#,##0.00',
                'align': 'center',
                'border': 1
            })
            
            # ورقة البيانات الرئيسية
            worksheet = workbook.add_worksheet('بيانات الطلاب')
            worksheet.right_to_left()
            
            # العناوين
            headers = [
                'رقم الطالب', 'الاسم', 'الرقم القومي', 'تاريخ الميلاد', 'العمر', 'الجنس',
                'رقم الهاتف', 'العنوان', 'المرحلة التعليمية', 'الصف الدراسي', 
                'العام الدراسي', 'اسم ولي الأمر', 'هاتف ولي الأمر', 'بريد ولي الأمر',
                'إجمالي المصروفات', 'إجمالي المدفوعات', 'المستحقات', 'الحالة المالية',
                'تاريخ التسجيل', 'الحالة'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # البيانات
            for row, student in enumerate(self.queryset.select_related('grade_level__education_level', 'academic_year'), 1):
                data = [
                    student.id,
                    student.name,
                    student.national_number,
                    student.date_of_birth.strftime('%Y-%m-%d') if student.date_of_birth else '',
                    student.age or 0,
                    'ذكر' if student.gender == 'M' else 'أنثى' if student.gender == 'F' else 'غير محدد',
                    student.phone_number or '',
                    student.address or '',
                    student.education_level_name,
                    student.grade_name,
                    str(student.academic_year) if student.academic_year else '',
                    student.parent_name or '',
                    student.parent_phone or '',
                    student.parent_email or '',
                    float(student.total_fees),
                    float(student.total_payments),
                    float(student.total_owed),
                    student.get_financial_status(),
                    student.created_at.strftime('%Y-%m-%d') if student.created_at else '',
                    'نشط' if student.is_active else 'غير نشط'
                ]
                
                for col, value in enumerate(data):
                    if col in [14, 15, 16]:  # الأعمدة المالية
                        worksheet.write(row, col, value, number_format)
                    else:
                        worksheet.write(row, col, value, data_format)
            
            # تعديل عرض الأعمدة
            worksheet.set_column('A:A', 8)   # رقم الطالب
            worksheet.set_column('B:B', 20)  # الاسم
            worksheet.set_column('C:C', 15)  # الرقم القومي
            worksheet.set_column('D:D', 12)  # تاريخ الميلاد
            worksheet.set_column('E:E', 8)   # العمر
            worksheet.set_column('F:F', 10)  # الجنس
            worksheet.set_column('G:G', 15)  # رقم الهاتف
            worksheet.set_column('H:H', 25)  # العنوان
            worksheet.set_column('I:I', 18)  # المرحلة التعليمية
            worksheet.set_column('J:J', 15)  # الصف الدراسي
            worksheet.set_column('K:K', 15)  # العام الدراسي
            worksheet.set_column('L:L', 20)  # اسم ولي الأمر
            worksheet.set_column('M:M', 15)  # هاتف ولي الأمر
            worksheet.set_column('N:N', 25)  # بريد ولي الأمر
            worksheet.set_column('O:Q', 15)  # الأعمدة المالية
            worksheet.set_column('R:R', 15)  # الحالة المالية
            worksheet.set_column('S:S', 12)  # تاريخ التسجيل
            worksheet.set_column('T:T', 10)  # الحالة
            
            workbook.close()
            output.seek(0)
            
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="students_export_{timestamp}.xlsx"'
            
            return response
            
        except Exception as e:
            # في حالة فشل xlsxwriter، استخدم تصدير CSV
            return self.export_csv(request)
