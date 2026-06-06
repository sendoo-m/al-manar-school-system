import csv
import io
import json
from datetime import datetime
from students.services.financial_service import StudentFinancialService
import openpyxl
from django.http import HttpResponse, JsonResponse
from openpyxl.styles import Font, PatternFill, Alignment


class StudentExportService:
    """
    خدمة موحدة لتصدير بيانات الطلاب بصيغ:
    CSV - Excel - JSON
    """

    HEADERS = [
        'الرقم الطلابي',
        'اسم الطالب',
        'الرقم القومي',
        'العمر',
        'الجنس',
        'تاريخ الميلاد',
        'المرحلة التعليمية',
        'الصف الدراسي',
        'العام الدراسي',
        'رقم الهاتف',
        'العنوان',
        'اسم ولي الأمر',
        'هاتف ولي الأمر',
        'بريد ولي الأمر',
        'إجمالي المصروفات',
        'إجمالي المدفوعات',
        'المستحقات',
        'الحالة المالية',
        'تاريخ التسجيل',
        'الحالة',
    ]

    @classmethod
    def export(cls, queryset, export_format='csv'):
        export_format = (export_format or 'csv').lower()

        if export_format == 'csv':
            return cls.export_csv(queryset)

        if export_format in ['excel', 'xlsx']:
            return cls.export_excel(queryset)

        if export_format == 'json':
            return cls.export_json(queryset)

        raise ValueError('صيغة التصدير غير مدعومة')

    @classmethod
    def get_filename(cls, extension):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f'students_export_{timestamp}.{extension}'

    @classmethod
    def get_student_row(cls, student):
        financial_summary = StudentFinancialService.get_student_balance(student)

        return [
            student.id,
            student.name or '',
            student.national_number or '',
            student.age or '',
            'ذكر' if student.gender == 'M' else 'أنثى' if student.gender == 'F' else 'غير محدد',
            student.date_of_birth.strftime('%Y-%m-%d') if student.date_of_birth else '',
            student.education_level_name if hasattr(student, 'education_level_name') else '',
            student.grade_name if hasattr(student, 'grade_name') else '',
            student.academic_year.name if student.academic_year else '',
            student.phone_number or '',
            student.address or '',
            student.parent_name or '',
            student.parent_phone or '',
            student.parent_email or '',
            float(financial_summary['required_fees'] or 0),
            float(financial_summary['paid_amount'] or 0),
            float(financial_summary['owed_amount'] or 0),
            'مسدد بالكامل' if financial_summary['is_paid'] else 'عليه مستحقات',
            student.created_at.strftime('%Y-%m-%d %H:%M:%S') if student.created_at else '',
            'نشط' if student.is_active else 'غير نشط',
        ]

    @classmethod
    def export_csv(cls, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="{cls.get_filename("csv")}"'

        response.write('\ufeff')
        writer = csv.writer(response)

        writer.writerow(cls.HEADERS)

        for student in queryset:
            writer.writerow(cls.get_student_row(student))

        return response

    @classmethod
    def export_excel(cls, queryset):
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = 'بيانات الطلاب'
        worksheet.sheet_view.rightToLeft = True

        header_fill = PatternFill(
            start_color='366092',
            end_color='366092',
            fill_type='solid'
        )
        header_font = Font(
            bold=True,
            color='FFFFFF'
        )
        header_alignment = Alignment(
            horizontal='center',
            vertical='center'
        )

        for col_num, header in enumerate(cls.HEADERS, 1):
            cell = worksheet.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment

        for row_num, student in enumerate(queryset, 2):
            row_data = cls.get_student_row(student)

            for col_num, value in enumerate(row_data, 1):
                cell = worksheet.cell(row=row_num, column=col_num, value=value)
                cell.alignment = Alignment(horizontal='center', vertical='center')

                if col_num in [15, 16, 17]:
                    cell.number_format = '#,##0.00'

        for column_cells in worksheet.columns:
            max_length = 0
            column_letter = column_cells[0].column_letter

            for cell in column_cells:
                try:
                    cell_length = len(str(cell.value)) if cell.value is not None else 0
                    if cell_length > max_length:
                        max_length = cell_length
                except Exception:
                    pass

            worksheet.column_dimensions[column_letter].width = min(max_length + 3, 45)

        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{cls.get_filename("xlsx")}"'

        return response

    @classmethod
    def export_json(cls, queryset):
        data = []
        financial_summary = StudentFinancialService.get_student_balance(student)
        for student in queryset:
            financial_summary = StudentFinancialService.get_student_balance(student)
            data.append({
                'id': student.id,
                'name': student.name or '',
                'national_number': student.national_number or '',
                'age': student.age,
                'gender': student.gender,
                'gender_display': 'ذكر' if student.gender == 'M' else 'أنثى' if student.gender == 'F' else 'غير محدد',
                'date_of_birth': student.date_of_birth.isoformat() if student.date_of_birth else None,
                'education_level': student.education_level_name if hasattr(student, 'education_level_name') else None,
                'grade_level': student.grade_name if hasattr(student, 'grade_name') else None,
                'academic_year': student.academic_year.name if student.academic_year else None,
                'phone_number': student.phone_number or '',
                'address': student.address or '',
                'parent_name': student.parent_name or '',
                'parent_phone': student.parent_phone or '',
                'parent_email': student.parent_email or '',
                'total_fees': float(financial_summary['required_fees'] or 0),
                'total_payments': float(financial_summary['paid_amount'] or 0),
                'total_owed': float(financial_summary['owed_amount'] or 0),
                'financial_status': 'مسدد بالكامل' if financial_summary['is_paid'] else 'عليه مستحقات',
                'collection_percentage': float(financial_summary['collection_percentage'] or 0),
                'created_at': student.created_at.isoformat() if student.created_at else None,
                'is_active': student.is_active,
            })

        response = JsonResponse({
            'success': True,
            'export_date': datetime.now().isoformat(),
            'total_count': len(data),
            'students': data,
        }, json_dumps_params={
            'ensure_ascii': False,
            'indent': 2,
        })

        response['Content-Disposition'] = f'attachment; filename="{cls.get_filename("json")}"'

        return response