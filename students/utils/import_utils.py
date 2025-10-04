# students/utils/import_utils.py
import csv
import json
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal, InvalidOperation

# إصلاح الاستيراد
from students.models import Student, validate_egyptian_national_id
from school_settings.models import AcademicYear, GradeLevel

# استيراد pandas بأمان
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

class StudentImporter:
    """فئة استيراد بيانات الطلاب"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.processed_count = 0
    
    def validate_row_data(self, row_data, row_number):
        """التحقق من صحة بيانات الصف"""
        errors = []
        
        # التحقق من الاسم
        if not row_data.get('name', '').strip():
            errors.append(f'الصف {row_number}: الاسم مطلوب')
        
        # التحقق من الرقم القومي
        national_number = row_data.get('national_number', '').strip()
        if not national_number:
            errors.append(f'الصف {row_number}: الرقم القومي مطلوب')
        else:
            is_valid, message = validate_egyptian_national_id(national_number)
            if not is_valid:
                errors.append(f'الصف {row_number}: {message}')
            
            # التحقق من عدم التكرار
            if Student.objects.filter(national_number=national_number).exists():
                errors.append(f'الصف {row_number}: يوجد طالب آخر بنفس الرقم القومي')
        
        return errors
    
    def process_csv_file(self, file_obj, current_user):
        """معالجة ملف CSV"""
        try:
            # قراءة الملف
            file_content = file_obj.read().decode('utf-8-sig')  # دعم BOM
            csv_data = csv.DictReader(file_content.splitlines())
            
            expected_headers = [
                'name', 'national_number', 'phone_number', 'address',
                'parent_name', 'parent_phone', 'parent_email', 'grade_level_id'
            ]
            
            # التحقق من العناوين
            if not all(header in csv_data.fieldnames for header in expected_headers[:2]):
                self.errors.append('ملف CSV غير صحيح - العناوين المطلوبة مفقودة')
                return False
            
            # معالجة البيانات
            with transaction.atomic():
                for row_num, row in enumerate(csv_data, 1):
                    self.processed_count += 1
                    
                    # التحقق من البيانات
                    row_errors = self.validate_row_data(row, row_num)
                    if row_errors:
                        self.errors.extend(row_errors)
                        continue
                    
                    try:
                        # إنشاء الطالب
                        student_data = {
                            'name': row['name'].strip(),
                            'national_number': row['national_number'].strip(),
                            'phone_number': row.get('phone_number', '').strip(),
                            'address': row.get('address', '').strip(),
                            'parent_name': row.get('parent_name', '').strip(),
                            'parent_phone': row.get('parent_phone', '').strip(),
                            'parent_email': row.get('parent_email', '').strip(),
                        }
                        
                        # ربط الصف الدراسي
                        grade_level_id = row.get('grade_level_id', '').strip()
                        if grade_level_id:
                            try:
                                grade_level = GradeLevel.objects.get(id=int(grade_level_id), is_active=True)
                                student_data['grade_level'] = grade_level
                            except (ValueError, GradeLevel.DoesNotExist):
                                self.warnings.append(f'الصف {row_num}: الصف الدراسي غير صحيح')
                        
                        # إنشاء الطالب
                        student = Student.objects.create(**student_data)
                        self.success_count += 1
                        
                    except Exception as e:
                        self.errors.append(f'الصف {row_num}: خطأ في إنشاء الطالب - {str(e)}')
            
            return True
            
        except Exception as e:
            self.errors.append(f'خطأ في معالجة ملف CSV: {str(e)}')
            return False
    
    def process_excel_file(self, file_obj, current_user):
        """معالجة ملف Excel"""
        if not PANDAS_AVAILABLE:
            self.errors.append('مكتبة pandas غير متوفرة لمعالجة ملفات Excel')
            return False
            
        try:
            # قراءة الملف باستخدام pandas
            df = pd.read_excel(file_obj, sheet_name=0)
            
            # التحقق من العناوين
            required_columns = ['name', 'national_number']
            if not all(col in df.columns for col in required_columns):
                self.errors.append('ملف Excel غير صحيح - الأعمدة المطلوبة مفقودة')
                return False
            
            # معالجة البيانات
            with transaction.atomic():
                for index, row in df.iterrows():
                    self.processed_count += 1
                    row_num = index + 2  # +2 لأن pandas يبدأ من 0 والصف الأول عناوين
                    
                    # تحويل البيانات لقاموس
                    row_data = {
                        'name': str(row.get('name', '')).strip(),
                        'national_number': str(row.get('national_number', '')).strip(),
                        'phone_number': str(row.get('phone_number', '')).strip(),
                        'address': str(row.get('address', '')).strip(),
                        'parent_name': str(row.get('parent_name', '')).strip(),
                        'parent_phone': str(row.get('parent_phone', '')).strip(),
                        'parent_email': str(row.get('parent_email', '')).strip(),
                        'grade_level_id': str(row.get('grade_level_id', '')).strip(),
                    }
                    
                    # تنظيف البيانات من NaN
                    for key, value in row_data.items():
                        if value == 'nan' or pd.isna(value):
                            row_data[key] = ''
                    
                    # التحقق من البيانات
                    row_errors = self.validate_row_data(row_data, row_num)
                    if row_errors:
                        self.errors.extend(row_errors)
                        continue
                    
                    try:
                        # إنشاء الطالب (نفس منطق CSV)
                        student_data = {
                            'name': row_data['name'],
                            'national_number': row_data['national_number'],
                            'phone_number': row_data['phone_number'],
                            'address': row_data['address'],
                            'parent_name': row_data['parent_name'],
                            'parent_phone': row_data['parent_phone'],
                            'parent_email': row_data['parent_email'],
                        }
                        
                        # ربط الصف الدراسي
                        if row_data['grade_level_id']:
                            try:
                                grade_level = GradeLevel.objects.get(id=int(row_data['grade_level_id']), is_active=True)
                                student_data['grade_level'] = grade_level
                            except (ValueError, GradeLevel.DoesNotExist):
                                self.warnings.append(f'الصف {row_num}: الصف الدراسي غير صحيح')
                        
                        student = Student.objects.create(**student_data)
                        self.success_count += 1
                        
                    except Exception as e:
                        self.errors.append(f'الصف {row_num}: خطأ في إنشاء الطالب - {str(e)}')
            
            return True
            
        except Exception as e:
            self.errors.append(f'خطأ في معالجة ملف Excel: {str(e)}')
            return False
    
    def get_import_summary(self):
        """الحصول على ملخص عملية الاستيراد"""
        return {
            'processed_count': self.processed_count,
            'success_count': self.success_count,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': self.errors,
            'warnings': self.warnings,
            'success_rate': (self.success_count / self.processed_count * 100) if self.processed_count > 0 else 0
        }
