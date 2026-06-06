import csv
import io
from datetime import datetime, date

import openpyxl
from django.core.exceptions import ValidationError
from django.db import transaction

from students.models import Student, validate_egyptian_national_id
from school_settings.models import AcademicYear as SettingsAcademicYear, GradeLevel


class StudentImportPreviewService:
    """
    خدمة معاينة استيراد الطلاب قبل الحفظ.
    تقرأ CSV / Excel وتفحص البيانات وتجهز:
    - valid_rows
    - errors
    - warnings

    لا تحفظ أي بيانات إلا عند استدعاء confirm_import.
    """

    REQUIRED_FIELDS = [
        'name',
        'national_number',
    ]

    ARABIC_FIELD_MAP = {
        'الاسم*': 'name',
        'الاسم': 'name',
        'اسم الطالب': 'name',
        'name': 'name',

        'الرقم القومي*': 'national_number',
        'الرقم القومي': 'national_number',
        'national_number': 'national_number',

        'رقم الهاتف': 'phone_number',
        'phone_number': 'phone_number',

        'العنوان': 'address',
        'address': 'address',

        'الصف الدراسي': 'grade_level',
        'الصف': 'grade_level',
        'grade_level': 'grade_level',
        'grade_level_id': 'grade_level_id',
        'معرف الصف': 'grade_level_id',

        'العام الدراسي': 'academic_year',
        'academic_year': 'academic_year',

        'اسم ولي الأمر': 'parent_name',
        'parent_name': 'parent_name',

        'هاتف ولي الأمر': 'parent_phone',
        'parent_phone': 'parent_phone',

        'بريد ولي الأمر': 'parent_email',
        'parent_email': 'parent_email',

        'تاريخ الميلاد': 'date_of_birth',
        'تاريخ الميلاد (YYYY-MM-DD)': 'date_of_birth',
        'date_of_birth': 'date_of_birth',

        'النوع': 'gender',
        'النوع (M/F)': 'gender',
        'gender': 'gender',
    }

    def __init__(self):
        self.valid_rows = []
        self.errors = []
        self.warnings = []
        self.processed_count = 0

    def preview_file(self, file_obj):
        """
        قراءة الملف وتجهيز نتيجة المعاينة.
        """
        self.valid_rows = []
        self.errors = []
        self.warnings = []
        self.processed_count = 0

        file_name = file_obj.name.lower()

        if file_name.endswith('.csv'):
            rows = self._read_csv(file_obj)
        elif file_name.endswith(('.xlsx', '.xls')):
            rows = self._read_excel(file_obj)
        else:
            raise ValidationError('صيغة الملف غير مدعومة. الصيغ المدعومة: CSV, Excel')

        if not rows:
            raise ValidationError('الملف لا يحتوي على بيانات طلاب')

        existing_national_numbers = set(
            Student.objects.values_list('national_number', flat=True)
        )

        file_national_numbers = set()

        for row_num, raw_row in rows:
            self.processed_count += 1
            normalized_row = self._normalize_row(raw_row)

            result = self._validate_row(
                row=normalized_row,
                row_num=row_num,
                existing_national_numbers=existing_national_numbers,
                file_national_numbers=file_national_numbers,
            )

            if result['is_valid']:
                file_national_numbers.add(result['data']['national_number'])
                self.valid_rows.append(result['data'])
            else:
                self.errors.extend(result['errors'])

            self.warnings.extend(result['warnings'])

        return self.get_summary()

    def get_summary(self):
        return {
            'processed_count': self.processed_count,
            'valid_count': len(self.valid_rows),
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'valid_rows': self.valid_rows,
            'errors': self.errors,
            'warnings': self.warnings,
        }

    def _read_csv(self, file_obj):
        """
        قراءة CSV مع دعم UTF-8 BOM.
        """
        try:
            decoded_file = file_obj.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            file_obj.seek(0)
            decoded_file = file_obj.read().decode('cp1256')

        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)

        if not reader.fieldnames:
            raise ValidationError('ملف CSV لا يحتوي على صف عناوين الأعمدة')

        rows = []

        for index, row in enumerate(reader, start=2):
            if self._row_has_data(row):
                rows.append((index, row))

        return rows

    def _read_excel(self, file_obj):
        """
        قراءة Excel من أول Sheet.
        """
        workbook = openpyxl.load_workbook(file_obj, data_only=True)
        worksheet = workbook.active

        rows = list(worksheet.iter_rows(values_only=True))

        if not rows:
            raise ValidationError('الملف فارغ')

        headers = [
            str(cell).strip() if cell is not None else ''
            for cell in rows[0]
        ]

        if not any(headers):
            raise ValidationError('ملف Excel لا يحتوي على صف عناوين الأعمدة')

        data_rows = []

        for index, row in enumerate(rows[1:], start=2):
            row_data = {}

            for col_index, value in enumerate(row):
                if col_index < len(headers):
                    header = headers[col_index]
                    if header:
                        row_data[header] = value

            if self._row_has_data(row_data):
                data_rows.append((index, row_data))

        return data_rows

    def _row_has_data(self, row):
        """
        التحقق من أن الصف ليس فارغاً.
        """
        if not row:
            return False

        return any(
            value not in [None, '']
            for value in row.values()
        )

    def _normalize_row(self, raw_row):
        """
        تحويل أسماء الأعمدة العربية أو الإنجليزية إلى أسماء موحدة.
        """
        normalized = {}

        for key, value in raw_row.items():
            clean_key = str(key).strip()
            mapped_key = self.ARABIC_FIELD_MAP.get(clean_key)

            if mapped_key:
                normalized[mapped_key] = self._clean_value(value)

        return normalized

    def _clean_value(self, value):
        """
        تنظيف القيم القادمة من CSV أو Excel.
        """
        if value is None:
            return ''

        if isinstance(value, datetime):
            return value.date().isoformat()

        if isinstance(value, date):
            return value.isoformat()

        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            return str(value).strip()

        return str(value).strip()

    def _validate_row(self, row, row_num, existing_national_numbers, file_national_numbers):
        errors = []
        warnings = []

        name = row.get('name', '').strip()
        national_number = row.get('national_number', '').strip()

        if not name:
            errors.append(f'صف {row_num}: اسم الطالب مطلوب')

        if not national_number:
            errors.append(f'صف {row_num}: الرقم القومي مطلوب')
        else:
            is_valid, message = validate_egyptian_national_id(national_number)

            if not is_valid:
                errors.append(f'صف {row_num}: {message}')

            if national_number in existing_national_numbers:
                errors.append(f'صف {row_num}: الرقم القومي {national_number} موجود مسبقاً في النظام')

            if national_number in file_national_numbers:
                errors.append(f'صف {row_num}: الرقم القومي {national_number} مكرر داخل الملف')

        grade_level = self._get_grade_level(
            grade_name=row.get('grade_level', ''),
            grade_level_id=row.get('grade_level_id', ''),
        )

        if (row.get('grade_level') or row.get('grade_level_id')) and not grade_level:
            warnings.append(
                f'صف {row_num}: لم يتم العثور على الصف الدراسي "{row.get("grade_level") or row.get("grade_level_id")}"'
            )

        academic_year = self._get_academic_year(row.get('academic_year', ''))

        if row.get('academic_year') and not academic_year:
            warnings.append(f'صف {row_num}: لم يتم العثور على العام الدراسي "{row.get("academic_year")}"')

        gender = self._normalize_gender(row.get('gender', ''))
        date_of_birth = self._parse_date(row.get('date_of_birth', ''))

        if row.get('date_of_birth') and not date_of_birth:
            warnings.append(f'صف {row_num}: صيغة تاريخ الميلاد غير صحيحة، سيتم تجاهلها')

        data = {
            'row_num': row_num,
            'name': name,
            'national_number': national_number,
            'phone_number': row.get('phone_number', ''),
            'address': row.get('address', ''),
            'parent_name': row.get('parent_name', ''),
            'parent_phone': row.get('parent_phone', ''),
            'parent_email': row.get('parent_email', ''),
            'grade_level_id': grade_level.id if grade_level else None,
            'grade_level_name': grade_level.name if grade_level else '',
            'academic_year_id': academic_year.id if academic_year else None,
            'academic_year_name': academic_year.name if academic_year else '',
            'gender': gender,
            'date_of_birth': date_of_birth.isoformat() if date_of_birth else '',
        }

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'data': data,
        }

    def _get_grade_level(self, grade_name='', grade_level_id=''):
        """
        الحصول على الصف الدراسي بالـ ID أو الاسم.
        """
        grade_level_id = str(grade_level_id or '').strip()
        grade_name = str(grade_name or '').strip()

        if grade_level_id:
            grade = GradeLevel.objects.filter(
                id=grade_level_id,
                is_active=True
            ).select_related('education_level').first()

            if grade:
                return grade

        if not grade_name:
            return None

        grade = GradeLevel.objects.filter(
            name__iexact=grade_name,
            is_active=True
        ).select_related('education_level').first()

        if grade:
            return grade

        return GradeLevel.objects.filter(
            name__icontains=grade_name,
            is_active=True
        ).select_related('education_level').first()

    def _get_academic_year(self, year_name):
        """
        الحصول على العام الدراسي بالاسم أو العام الحالي إذا لم يُرسل.
        """
        year_name = str(year_name or '').strip()

        if not year_name:
            try:
                return SettingsAcademicYear.get_current_year()
            except Exception:
                return None

        academic_year = SettingsAcademicYear.objects.filter(
            name__iexact=year_name,
            is_active=True
        ).first()

        if academic_year:
            return academic_year

        return SettingsAcademicYear.objects.filter(
            name__icontains=year_name,
            is_active=True
        ).first()

    def _normalize_gender(self, gender):
        """
        توحيد قيمة النوع.
        """
        gender = str(gender or '').strip().upper()

        if gender in ['M', 'MALE', 'ذكر']:
            return 'M'

        if gender in ['F', 'FEMALE', 'أنثى', 'انثى']:
            return 'F'

        return ''

    def _parse_date(self, value):
        """
        تحويل النص إلى تاريخ.
        """
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        value = str(value or '').strip()

        if not value:
            return None

        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
        ]

        for date_format in formats:
            try:
                return datetime.strptime(value, date_format).date()
            except ValueError:
                continue

        return None

    @transaction.atomic
    def confirm_import(self, valid_rows):
        """
        حفظ الصفوف الصحيحة فقط بعد تأكيد المستخدم.
        """
        created_students = []
        errors = []

        for row in valid_rows:
            try:
                national_number = row.get('national_number', '').strip()

                if Student.objects.filter(national_number=national_number).exists():
                    errors.append(f'صف {row.get("row_num")}: الرقم القومي موجود مسبقاً وتم تخطيه')
                    continue

                grade_level = None
                if row.get('grade_level_id'):
                    grade_level = GradeLevel.objects.filter(
                        id=row['grade_level_id'],
                        is_active=True
                    ).first()

                academic_year = None
                if row.get('academic_year_id'):
                    academic_year = SettingsAcademicYear.objects.filter(
                        id=row['academic_year_id'],
                        is_active=True
                    ).first()

                date_of_birth = self._parse_date(row.get('date_of_birth'))

                student = Student.objects.create(
                    name=row['name'],
                    national_number=national_number,
                    phone_number=row.get('phone_number', ''),
                    address=row.get('address', ''),
                    parent_name=row.get('parent_name', ''),
                    parent_phone=row.get('parent_phone', ''),
                    parent_email=row.get('parent_email', ''),
                    grade_level=grade_level,
                    academic_year=academic_year,
                    gender=row.get('gender', ''),
                    date_of_birth=date_of_birth,
                    is_active=True,
                )

                created_students.append(student)

            except Exception as e:
                errors.append(f'صف {row.get("row_num")}: خطأ أثناء الحفظ - {str(e)}')

        return {
            'created_count': len(created_students),
            'errors': errors,
            'created_students': created_students,
        }