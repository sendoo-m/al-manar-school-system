# students/utils/upgrade_utils.py
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

# إصلاح الاستيراد
from students.models import Student, ArchiveStudent
from school_settings.models import AcademicYear, GradeLevel, EducationLevel

class StudentUpgradeManager:
    """مدير ترقية الطلاب للعام الجديد"""
    
    def __init__(self):
        self.upgraded_count = 0
        self.graduated_count = 0
        self.archived_count = 0
        self.errors = []
        self.warnings = []
    
    def can_perform_upgrade(self):
        """التحقق من إمكانية تنفيذ الترقية"""
        current_year = AcademicYear.get_current_year()
        
        if not current_year:
            return False, "لا يوجد عام دراسي حالي محدد"
        
        # التحقق من انتهاء العام الحالي
        if current_year.end_date > timezone.now().date():
            return False, f"العام الدراسي الحالي لم ينته بعد. ينتهي في {current_year.end_date}"
        
        # التحقق من وجود عام جديد
        next_year = AcademicYear.objects.filter(
            start_date__gt=current_year.end_date,
            is_active=True
        ).order_by('start_date').first()
        
        if not next_year:
            return False, "لا يوجد عام دراسي جديد مُعرَّف"
        
        return True, "يمكن تنفيذ الترقية"
    
    def get_upgrade_preview(self):
        """معاينة عملية الترقية"""
        current_year = AcademicYear.get_current_year()
        if not current_year:
            return {}
        
        # تجميع الطلاب حسب الصفوف
        upgrade_data = {}
        
        for grade in GradeLevel.objects.filter(is_active=True).select_related('education_level'):
            students_count = Student.objects.filter(
                grade_level=grade,
                academic_year=current_year,
                is_active=True
            ).count()
            
            if students_count > 0:
                # تحديد الصف التالي
                next_grade = self.get_next_grade(grade)
                
                upgrade_data[grade.id] = {
                    'current_grade': grade,
                    'student_count': students_count,
                    'next_grade': next_grade,
                    'action': 'upgrade' if next_grade else 'graduate'
                }
        
        return upgrade_data
    
    def get_next_grade(self, current_grade):
        """الحصول على الصف التالي"""
        # البحث عن الصف التالي في نفس المرحلة
        next_grade = GradeLevel.objects.filter(
            education_level=current_grade.education_level,
            order__gt=current_grade.order,
            is_active=True
        ).order_by('order').first()
        
        if next_grade:
            return next_grade
        
        # البحث عن أول صف في المرحلة التالية
        next_education_level = EducationLevel.objects.filter(
            order__gt=current_grade.education_level.order,
            is_active=True
        ).order_by('order').first()
        
        if next_education_level:
            return GradeLevel.objects.filter(
                education_level=next_education_level,
                is_active=True
            ).order_by('order').first()
        
        return None  # تخرج
    
    def perform_upgrade(self, selected_grades=None, upgrade_options=None):
        """تنفيذ عملية الترقية"""
        can_upgrade, message = self.can_perform_upgrade()
        if not can_upgrade:
            self.errors.append(message)
            return False
        
        current_year = AcademicYear.get_current_year()
        next_year = AcademicYear.objects.filter(
            start_date__gt=current_year.end_date,
            is_active=True
        ).order_by('start_date').first()
        
        upgrade_options = upgrade_options or {}
        
        try:
            with transaction.atomic():
                # معالجة كل صف
                for grade in GradeLevel.objects.filter(is_active=True):
                    if selected_grades and grade.id not in selected_grades:
                        continue
                    
                    students = Student.objects.filter(
                        grade_level=grade,
                        academic_year=current_year,
                        is_active=True
                    )
                    
                    if not students.exists():
                        continue
                    
                    next_grade = self.get_next_grade(grade)
                    
                    for student in students:
                        try:
                            if next_grade:
                                # ترقية للصف التالي
                                student.grade_level = next_grade
                                student.academic_year = next_year
                                
                                # إعادة تعيين الرسوم حسب الإعدادات
                                if upgrade_options.get('reset_fees', False):
                                    student.total_fees = Decimal('0.00')
                                    student.total_payments = Decimal('0.00')
                                    student.total_owed = Decimal('0.00')
                                
                                student.save()
                                self.upgraded_count += 1
                                
                            else:
                                # تخرج - نقل للأرشيف
                                if upgrade_options.get('archive_graduates', True):
                                    ArchiveStudent.objects.create(
                                        archive_name=student.name,
                                        archive_national_number=student.national_number,
                                        archive_age=student.age or 0,
                                        archive_gender=student.gender,
                                        archive_date_of_birth=student.date_of_birth,
                                        archive_academic_year=str(current_year),
                                        archive_grade_level=student.grade_name,
                                        archive_education_level=student.education_level_name,
                                        archive_total_payments=student.total_payments,
                                        archive_total_fees=student.total_fees,
                                        archive_total_owed=student.total_owed,
                                        archived_reason='تخرج - ترقية آلية',
                                        archived_by=None
                                    )
                                    
                                    student.delete()
                                    self.archived_count += 1
                                else:
                                    # إبقاء كطالب متخرج
                                    student.is_active = False
                                    student.save()
                                    self.graduated_count += 1
                        
                        except Exception as e:
                            self.errors.append(f'خطأ في ترقية الطالب {student.name}: {str(e)}')
            
            return True
            
        except Exception as e:
            self.errors.append(f'خطأ عام في عملية الترقية: {str(e)}')
            return False
    
    def get_upgrade_summary(self):
        """ملخص عملية الترقية"""
        return {
            'upgraded_count': self.upgraded_count,
            'graduated_count': self.graduated_count,
            'archived_count': self.archived_count,
            'total_processed': self.upgraded_count + self.graduated_count + self.archived_count,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': self.errors,
            'warnings': self.warnings
        }
