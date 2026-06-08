# students/services/import_preview_service.py
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

import openpyxl
from django.db import transaction

from students.models import Student, validate_egyptian_national_id
from school_settings.models import AcademicYear, GradeLevel


class StudentImportPreviewService:
    """خدمة معاينة واستيراد الطلاب بعد توسيع ملف الطالب"""

    REQUIRED_HEADERS = ['الاسم']

    HEADER_ALIASES = {
        'name': ['الاسم', 'اسم الطالب', 'الاسم*', 'اسم الطالب*'],
        'student_type': ['نوع الطالب', 'تصنيف الطالب'],
        'national_number': ['الرقم القومي', 'رقم قومي'],
        'passport_number': ['رقم جواز السفر', 'جواز السفر', 'رقم الجواز'],
        'nationality': ['الجنسية'],
        'religion': ['الديانة', 'الدين'],
        'age': ['العمر'],
        'gender': ['النوع', 'الجنس', 'النوع (M/F)'],
        'date_of_birth': ['تاريخ الميلاد', 'تاريخ الميلاد (YYYY-MM-DD)'],
        'phone_number': ['رقم الهاتف', 'هاتف الطالب', 'تليفون الطالب'],
        'address': ['العنوان'],

        'academic_year': ['العام الدراسي'],
        'grade_level': ['الصف الدراسي', 'الصف'],
        'enrollment_status': ['حالة القيد'],
        'transferred_from_school': ['محول من مدرسة', 'المدرسة المحول منها'],
        'transferred_to_school': ['محول إلى مدرسة', 'المدرسة المحول إليها'],

        'is_integration_student': ['طالب دمج', 'طالب دمج / من ذوي الهمم', 'ذوي الهمم'],
        'disability_type': ['نوع الإعاقة', 'نوع الاعاقة'],
        'exempt_from_arabic': ['إعفاء من العربي', 'إعفاء من اللغة العربية'],
        'exempt_from_english': ['إعفاء من الإنجليزي', 'إعفاء من اللغة الإنجليزية'],
        'exempt_from_french': ['إعفاء من الفرنسي', 'إعفاء من اللغة الفرنسية'],
        'other_subject_exemptions': ['إعفاءات أخرى', 'إعفاءات أخرى من مواد'],

        'is_staff_child': ['من أبناء العاملين', 'ابن عامل', 'أبناء العاملين'],
        'staff_parent_name': ['اسم الموظف', 'اسم الموظف من العاملين'],
        'staff_parent_job': ['وظيفة الموظف', 'وظيفة الموظف داخل المدرسة'],

        'parent_name': ['اسم ولي الأمر', 'ولي الأمر'],
        'parent_phone': ['هاتف ولي الأمر', 'رقم ولي الأمر'],
        'parent_email': ['بريد ولي الأمر', 'إيميل ولي الأمر', 'ايميل ولي الأمر'],
        'father_job': ['وظيفة الأب'],
        'educational_guardian': ['صاحب الولاية التعليمية', 'الولاية التعليمية'],
        'educational_guardian_name': ['اسم صاحب الولاية التعليمية'],
        'educational_guardian_phone': ['هاتف صاحب الولاية التعليمية'],
    }

    TRUE_VALUES = {'1', 'true', 'yes', 'y', 'نعم', 'صح', 'صحيح', 'موجود', '✓'}
    FALSE_VALUES = {'0', 'false', 'no', 'n', 'لا', 'خطأ', 'غير موجود', 'x'}

    STUDENT_TYPE_MAP = {
        'طالب عادي': 'REGULAR',
        'عادي': 'REGULAR',
        'regular': 'REGULAR',
        'REGULAR': 'REGULAR',
        'وافد': 'EXPATRIATE',
        'اجنبي': 'EXPATRIATE',
        'أجنبي': 'EXPATRIATE',
        'expatriate': 'EXPATRIATE',
        'EXPATRIATE': 'EXPATRIATE',
    }

    GENDER_MAP = {
        'ذكر': 'M',
        'male': 'M',
        'm': 'M',
        'M': 'M',
        'أنثى': 'F',
        'انثى': 'F',
        'female': 'F',
        'f': 'F',
        'F': 'F',
    }

    RELIGION_MAP = {
        'مسلم': 'MUSLIM',
        'مسيحي': 'CHRISTIAN',
        'مسيحى': 'CHRISTIAN',
        'أخرى': 'OTHER',
        'اخرى': 'OTHER',
        'other': 'OTHER',
        'MUSLIM': 'MUSLIM',
        'CHRISTIAN': 'CHRISTIAN',
        'OTHER': 'OTHER',
    }

    ENROLLMENT_STATUS_MAP = {
        'مستجد': 'NEW',
        'ناجح ومنقول': 'PROMOTED',
        'منقول': 'PROMOTED',
        'محول': 'TRANSFERRED',
        'باق للإعادة': 'REPEATER',
        'باق للاعادة': 'REPEATER',
        'NEW': 'NEW',
        'PROMOTED': 'PROMOTED',
        'TRANSFERRED': 'TRANSFERRED',
        'REPEATER': 'REPEATER',
    }

    EDUCATIONAL_GUARDIAN_MAP = {
        'الأب': 'FATHER',
        'الاب': 'FATHER',
        'اب': 'FATHER',
        'أب': 'FATHER',
        'father': 'FATHER',
        'FATHER': 'FATHER',
        'الأم': 'MOTHER',
        'الام': 'MOTHER',
        'ام': 'MOTHER',
        'أم': 'MOTHER',
        'mother': 'MOTHER',
        'MOTHER': 'MOTHER',
        'آخر': 'OTHER',
        'اخر': 'OTHER',
        'other': 'OTHER',
        'OTHER': 'OTHER',
    }

    def preview_file(self, file_obj):
        rows = self.read_file(file_obj)

        summary = {
            'processed_count': 0,
            'valid_count': 0,
            'error_count': 0,
            'warning_count': 0,
            'valid_rows': [],
            'preview_rows': [],
            'errors': [],
            'warnings': [],
        }

        seen_national_numbers = set()
        seen_passports = set()

        for index, raw_row in enumerate(rows, start=2):
            if not any(str(value or '').strip() for value in raw_row.values()):
                continue

            summary['processed_count'] += 1
            normalized = self.normalize_row(raw_row)
            row_errors = []
            row_warnings = []

            name = normalized.get('name', '').strip()
            national_number = normalized.get('national_number', '').strip()
            passport_number = normalized.get('passport_number', '').strip()

            if not name:
                row_errors.append('اسم الطالب مطلوب')

            if national_number:
                is_valid, message = validate_egyptian_national_id(national_number)
                if not is_valid:
                    row_errors.append(f'الرقم القومي غير صحيح: {message}')

                if Student.objects.filter(national_number=national_number).exists():
                    row_errors.append('الرقم القومي موجود بالفعل لطالب آخر')

                if national_number in seen_national_numbers:
                    row_errors.append('الرقم القومي مكرر داخل نفس الملف')

                seen_national_numbers.add(national_number)

            if passport_number:
                if Student.objects.filter(passport_number=passport_number).exists():
                    row_errors.append('رقم جواز السفر موجود بالفعل لطالب آخر')

                if passport_number in seen_passports:
                    row_errors.append('رقم جواز السفر مكرر داخل نفس الملف')

                seen_passports.add(passport_number)

            if not national_number and not passport_number:
                row_warnings.append('لا يوجد رقم قومي أو جواز سفر، سيتم إنشاء الطالب بالاسم فقط')

            grade_name = normalized.get('grade_level', '').strip()
            if grade_name and not self.find_grade(grade_name):
                row_warnings.append(f'لم يتم العثور على الصف الدراسي: {grade_name}')

            academic_year_name = normalized.get('academic_year', '').strip()
            if academic_year_name and not self.find_academic_year(academic_year_name):
                row_warnings.append(f'لم يتم العثور على العام الدراسي: {academic_year_name}')

            preview_row = {
                'row_number': index,
                'data': normalized,
                'errors': row_errors,
                'warnings': row_warnings,
                'is_valid': not row_errors,
            }

            summary['preview_rows'].append(preview_row)

            if row_errors:
                summary['error_count'] += 1
                summary['errors'].append(f'صف {index}: ' + ' - '.join(row_errors))
            else:
                summary['valid_count'] += 1
                summary['valid_rows'].append(normalized)

            if row_warnings:
                summary['warning_count'] += len(row_warnings)
                for warning in row_warnings:
                    summary['warnings'].append(f'صف {index}: {warning}')

        return summary

    def confirm_import(self, valid_rows):
        result = {
            'created_count': 0,
            'errors': [],
        }

        with transaction.atomic():
            for index, row in enumerate(valid_rows, start=1):
                try:
                    student = self.build_student(row)
                    student.save()
                    result['created_count'] += 1
                except Exception as exc:
                    result['errors'].append(f'صف صالح رقم {index}: {str(exc)}')

        return result

    def read_file(self, file_obj):
        file_name = (getattr(file_obj, 'name', '') or '').lower()

        if file_name.endswith('.csv'):
            return self.read_csv(file_obj)

        if file_name.endswith('.xlsx'):
            return self.read_excel(file_obj)

        raise ValueError('صيغة الملف غير مدعومة. الصيغ المدعومة: CSV أو XLSX')

    def read_csv(self, file_obj):
        raw = file_obj.read()

        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = raw.decode('cp1256')

        reader = csv.DictReader(io.StringIO(text))
        return [dict(row) for row in reader]

    def read_excel(self, file_obj):
        workbook = openpyxl.load_workbook(file_obj, data_only=True)
        worksheet = workbook.active

        headers = []
        for cell in worksheet[1]:
            headers.append(str(cell.value or '').strip())

        rows = []

        for row in worksheet.iter_rows(min_row=2, values_only=True):
            row_data = {}

            for index, header in enumerate(headers):
                if not header:
                    continue

                row_data[header] = row[index] if index < len(row) else ''

            rows.append(row_data)

        return rows

    def normalize_row(self, raw_row):
        normalized = {}

        for internal_name, aliases in self.HEADER_ALIASES.items():
            normalized[internal_name] = self.get_value(raw_row, aliases)

        normalized['name'] = normalized.get('name', '').strip()
        normalized['student_type'] = self.map_choice(
            normalized.get('student_type'),
            self.STUDENT_TYPE_MAP,
            default='REGULAR'
        )
        normalized['gender'] = self.map_choice(
            normalized.get('gender'),
            self.GENDER_MAP,
            default=''
        )
        normalized['religion'] = self.map_choice(
            normalized.get('religion'),
            self.RELIGION_MAP,
            default=''
        )
        normalized['enrollment_status'] = self.map_choice(
            normalized.get('enrollment_status'),
            self.ENROLLMENT_STATUS_MAP,
            default='NEW'
        )
        normalized['educational_guardian'] = self.map_choice(
            normalized.get('educational_guardian'),
            self.EDUCATIONAL_GUARDIAN_MAP,
            default='FATHER'
        )

        for field in [
            'is_integration_student',
            'exempt_from_arabic',
            'exempt_from_english',
            'exempt_from_french',
            'is_staff_child',
        ]:
            normalized[field] = self.to_bool(normalized.get(field))

        normalized['age'] = self.to_int(normalized.get('age'))
        normalized['date_of_birth'] = self.to_date_string(normalized.get('date_of_birth'))

        return normalized

    def build_student(self, row):
        grade = self.find_grade(row.get('grade_level', ''))
        academic_year = self.find_academic_year(row.get('academic_year', ''))

        if not academic_year:
            try:
                academic_year = AcademicYear.get_current_year()
            except Exception:
                academic_year = None

        student = Student(
            name=row.get('name', '').strip(),
            student_type=row.get('student_type') or 'REGULAR',
            national_number=row.get('national_number') or None,
            passport_number=row.get('passport_number') or None,
            nationality=row.get('nationality') or '',
            religion=row.get('religion') or '',
            age=row.get('age') or None,
            gender=row.get('gender') or '',
            date_of_birth=self.parse_date_object(row.get('date_of_birth')),
            phone_number=row.get('phone_number') or '',
            address=row.get('address') or '',

            academic_year=academic_year,
            grade_level=grade,
            enrollment_status=row.get('enrollment_status') or 'NEW',
            transferred_from_school=row.get('transferred_from_school') or '',
            transferred_to_school=row.get('transferred_to_school') or '',

            is_integration_student=bool(row.get('is_integration_student')),
            disability_type=row.get('disability_type') or '',
            exempt_from_arabic=bool(row.get('exempt_from_arabic')),
            exempt_from_english=bool(row.get('exempt_from_english')),
            exempt_from_french=bool(row.get('exempt_from_french')),
            other_subject_exemptions=row.get('other_subject_exemptions') or '',

            is_staff_child=bool(row.get('is_staff_child')),
            staff_parent_name=row.get('staff_parent_name') or '',
            staff_parent_job=row.get('staff_parent_job') or '',

            parent_name=row.get('parent_name') or '',
            parent_phone=row.get('parent_phone') or '',
            parent_email=row.get('parent_email') or '',
            father_job=row.get('father_job') or '',
            educational_guardian=row.get('educational_guardian') or 'FATHER',
            educational_guardian_name=row.get('educational_guardian_name') or '',
            educational_guardian_phone=row.get('educational_guardian_phone') or '',
        )

        return student

    def get_value(self, raw_row, aliases):
        for alias in aliases:
            if alias in raw_row:
                return self.clean_cell(raw_row.get(alias))

        # دعم لو فيه مسافات أو اختلاف بسيط في اسم العمود
        normalized_keys = {
            str(key or '').strip(): value
            for key, value in raw_row.items()
        }

        for alias in aliases:
            if alias in normalized_keys:
                return self.clean_cell(normalized_keys.get(alias))

        return ''

    def clean_cell(self, value):
        if value is None:
            return ''

        if isinstance(value, float) and value.is_integer():
            return str(int(value))

        return str(value).strip()

    def map_choice(self, value, mapping, default=''):
        value = self.clean_cell(value)

        if not value:
            return default

        return mapping.get(value, mapping.get(value.lower(), default))

    def to_bool(self, value):
        value = self.clean_cell(value).lower()

        if value in self.TRUE_VALUES:
            return True

        if value in self.FALSE_VALUES:
            return False

        return False

    def to_int(self, value):
        value = self.clean_cell(value)

        if not value:
            return None

        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def to_date_string(self, value):
        date_obj = self.parse_date_object(value)

        if date_obj:
            return date_obj.strftime('%Y-%m-%d')

        return ''

    def parse_date_object(self, value):
        if not value:
            return None

        if hasattr(value, 'date'):
            try:
                return value.date()
            except Exception:
                pass

        value = self.clean_cell(value)

        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        return None

    def find_grade(self, grade_name):
        grade_name = self.clean_cell(grade_name)

        if not grade_name:
            return None

        return GradeLevel.objects.filter(name__iexact=grade_name).first() or GradeLevel.objects.filter(name__icontains=grade_name).first()

    def find_academic_year(self, academic_year_name):
        academic_year_name = self.clean_cell(academic_year_name)

        if not academic_year_name:
            return None

        return AcademicYear.objects.filter(name__iexact=academic_year_name).first() or AcademicYear.objects.filter(name__icontains=academic_year_name).first()
