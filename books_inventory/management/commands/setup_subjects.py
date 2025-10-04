from django.core.management.base import BaseCommand
from books_inventory.models import Subject
from students.models import EducationLevel, GradeLevel

class Command(BaseCommand):
    help = 'إنشاء جميع المواد الدراسية للأنظمة التعليمية المختلفة'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🏫 بدء إنشاء المواد الدراسية...'))
        
        # المواد الأساسية لكل نظام
        basic_subjects = {
            'arabic': 'اللغة العربية',
            'english': 'اللغة الإنجليزية', 
            'math': 'الرياضيات',
            'science': 'العلوم',
            'social': 'الدراسات الاجتماعية',
            'religion': 'التربية الدينية',
            'art': 'التربية الفنية',
            'music': 'التربية الموسيقية',
            'pe': 'التربية الرياضية',
            'computer': 'الحاسوب'
        }
        
        # مواد إضافية للمراحل المتقدمة
        advanced_subjects = {
            'physics': 'الفيزياء',
            'chemistry': 'الكيمياء', 
            'biology': 'الأحياء',
            'geography': 'الجغرافيا',
            'history': 'التاريخ',
            'philosophy': 'الفلسفة',
            'psychology': 'علم النفس',
            'french': 'اللغة الفرنسية',
            'german': 'اللغة الألمانية'
        }
        
        # مواد المنهج الأمريكي الخاصة
        american_subjects = {
            'ela': 'اللغة الإنجليزية وآدابها',
            'algebra': 'الجبر',
            'geometry': 'الهندسة',
            'calculus': 'التفاضل والتكامل',
            'biology_ap': 'أحياء متقدم',
            'chemistry_ap': 'كيمياء متقدم',
            'physics_ap': 'فيزياء متقدم',
            'us_history': 'تاريخ الولايات المتحدة',
            'world_history': 'التاريخ العالمي'
        }
        
        # مواد المنهج البريطاني الخاصة
        british_subjects = {
            'igcse_english': 'اللغة الإنجليزية IGCSE',
            'igcse_math': 'رياضيات IGCSE',
            'igcse_physics': 'فيزياء IGCSE',
            'igcse_chemistry': 'كيمياء IGCSE',
            'igcse_biology': 'أحياء IGCSE',
            'as_level': 'مستوى AS',
            'a_level': 'مستوى A'
        }

        # إنشاء المواد لكل نظام وصف
        created_count = 0
        
        try:
            # الحصول على جميع المراحل والصفوف
            education_levels = EducationLevel.objects.all().order_by('order')
            
            for level in education_levels:
                grades = GradeLevel.objects.filter(education_level=level).order_by('order')
                
                for grade in grades:
                    grade_name = grade.name
                    level_name = level.name
                    
                    # تحديد المواد المناسبة لكل مرحلة
                    subjects_to_create = basic_subjects.copy()
                    
                    # إضافة المواد المتقدمة للمراحل العليا
                    if 'إعدادي' in level_name or 'ثانوي' in level_name:
                        subjects_to_create.update(advanced_subjects)
                    
                    # إنشاء مواد النظام العادي (اللغات)
                    for subject_key, subject_name in subjects_to_create.items():
                        full_name = f"{subject_name} - {grade_name} - لغات"
                        subject, created = Subject.objects.get_or_create(
                            name=full_name,
                            defaults={
                                'description': f'مادة {subject_name} للصف {grade_name} - نظام اللغات',
                                'is_active': True
                            }
                        )
                        if created:
                            created_count += 1
                            self.stdout.write(f'✅ تم إنشاء: {full_name}')
                    
                    # إنشاء مواد المنهج الأمريكي
                    american_subjects_for_grade = basic_subjects.copy()
                    american_subjects_for_grade.update(american_subjects)
                    
                    for subject_key, subject_name in american_subjects_for_grade.items():
                        full_name = f"{subject_name} - {grade_name} - منهج أمريكي"
                        subject, created = Subject.objects.get_or_create(
                            name=full_name,
                            defaults={
                                'description': f'مادة {subject_name} للصف {grade_name} - المنهج الأمريكي',
                                'is_active': True
                            }
                        )
                        if created:
                            created_count += 1
                            self.stdout.write(f'🇺🇸 تم إنشاء: {full_name}')
                    
                    # إنشاء مواد المنهج البريطاني (من الثالث الإعدادي فقط)
                    if ('إعدادي' in level_name and 'ثالث' in grade_name) or 'ثانوي' in level_name:
                        british_subjects_for_grade = basic_subjects.copy()
                        british_subjects_for_grade.update(british_subjects)
                        
                        for subject_key, subject_name in british_subjects_for_grade.items():
                            full_name = f"{subject_name} - {grade_name} - منهج بريطاني"
                            subject, created = Subject.objects.get_or_create(
                                name=full_name,
                                defaults={
                                    'description': f'مادة {subject_name} للصف {grade_name} - المنهج البريطاني',
                                    'is_active': True
                                }
                            )
                            if created:
                                created_count += 1
                                self.stdout.write(f'🇬🇧 تم إنشاء: {full_name}')

            self.stdout.write(
                self.style.SUCCESS(f'🎉 تم إنشاء {created_count} مادة دراسية بنجاح!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ خطأ في إنشاء المواد: {e}')
            )
