from django.core.management.base import BaseCommand
from books_inventory.models import Subject, Notebook
from django.db import transaction
import sys

class Command(BaseCommand):
    help = 'إضافة جميع المواد الدراسية والكراسات لمدرسة المنار'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='حذف المواد والكراسات الموجودة قبل الإضافة',
        )
        
        parser.add_argument(
            '--subjects-only',
            action='store_true',
            help='إضافة المواد الدراسية فقط',
        )
        
        parser.add_argument(
            '--notebooks-only',
            action='store_true',
            help='إضافة الكراسات فقط',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🏫 مرحباً بك في منظومة إضافة مواد مدرسة المنار')
        )
        
        try:
            with transaction.atomic():
                # حذف البيانات الموجودة إذا طُلب ذلك
                if options['clear_existing']:
                    self.clear_existing_data()
                
                # إضافة المواد الدراسية
                if not options['notebooks_only']:
                    self.create_subjects()
                
                # إضافة الكراسات
                if not options['subjects_only']:
                    self.create_notebooks()
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ خطأ في العملية: {str(e)}')
            )
            sys.exit(1)
        
        self.stdout.write(
            self.style.SUCCESS('✅ تم إكمال العملية بنجاح!')
        )

    def clear_existing_data(self):
        """حذف البيانات الموجودة"""
        self.stdout.write('🗑️  حذف البيانات الموجودة...')
        
        notebooks_count = Notebook.objects.count()
        subjects_count = Subject.objects.count()
        
        Notebook.objects.all().delete()
        Subject.objects.all().delete()
        
        self.stdout.write(
            f'   تم حذف {subjects_count} مادة دراسية و {notebooks_count} كراسة'
        )

    def create_subjects(self):
        """إنشاء جميع المواد الدراسية"""
        self.stdout.write('📚 إضافة المواد الدراسية...')
        
        # هيكل المدرسة
        school_structure = {
            'kg': {
                'name': 'رياض الأطفال',
                'levels': ['تمهيدي', 'الأول', 'الثاني'],
                'curricula': ['لغات', 'منهج أمريكي']
            },
            'primary': {
                'name': 'المرحلة الابتدائية', 
                'levels': ['الأول', 'الثاني', 'الثالث', 'الرابع', 'الخامس', 'السادس'],
                'curricula': ['لغات', 'منهج أمريكي']
            },
            'preparatory': {
                'name': 'المرحلة الإعدادية',
                'levels': ['الأول', 'الثاني', 'الثالث'],
                'curricula': ['لغات', 'منهج أمريكي', 'منهج بريطاني']  # البريطاني من الثالث فقط
            },
            'secondary': {
                'name': 'المرحلة الثانوية',
                'levels': ['الأول', 'الثاني', 'الثالث'],
                'curricula': ['لغات', 'منهج أمريكي', 'منهج بريطاني']
            }
        }
        
        # المواد الأساسية لكل منهج
        subjects_by_curriculum = {
            'لغات': [
                'اللغة العربية', 'اللغة الإنجليزية', 'الرياضيات', 'العلوم',
                'الدراسات الاجتماعية', 'التربية الدينية الإسلامية', 'التربية الدينية المسيحية',
                'الحاسب الآلي', 'التربية الفنية', 'التربية الموسيقية', 'التربية الرياضية',
                'اللغة الفرنسية', 'الاقتصاد المنزلي', 'الأنشطة العملية'
            ],
            'منهج أمريكي': [
                'اللغة العربية', 'English Language Arts', 'Mathematics', 'Science',
                'Social Studies', 'Islamic Studies', 'Christian Studies',
                'Computer Science', 'Art', 'Music', 'Physical Education',
                'French Language', 'Health Education', 'STEM'
            ],
            'منهج بريطاني': [
                'اللغة العربية', 'English Language', 'Mathematics', 'Science',
                'Geography', 'History', 'Islamic Studies', 'Christian Studies',
                'ICT', 'Art & Design', 'Music', 'Physical Education',
                'French Language', 'Business Studies', 'Economics'
            ]
        }
        
        # إضافة مواد إضافية للمراحل المتقدمة
        advanced_subjects = {
            'preparatory': {
                'لغات': ['الجبر', 'الهندسة', 'الفيزياء', 'الكيمياء', 'الأحياء'],
                'منهج أمريكي': ['Algebra', 'Geometry', 'Physics', 'Chemistry', 'Biology'],
                'منهج بريطاني': ['Pure Mathematics', 'Physics', 'Chemistry', 'Biology', 'Extended Mathematics']
            },
            'secondary': {
                'لغات': [
                    'الجبر والهندسة الفراغية', 'التفاضل والتكامل', 'الإحصاء',
                    'الفيزياء', 'الكيمياء', 'الأحياء', 'الجيولوجيا',
                    'التاريخ', 'الجغرافيا', 'الفلسفة والمنطق', 'علم النفس والاجتماع'
                ],
                'منهج أمريكي': [
                    'Calculus', 'Statistics', 'AP Physics', 'AP Chemistry', 'AP Biology',
                    'World History', 'US History', 'Psychology', 'Sociology', 'Economics'
                ],
                'منهج بريطاني': [
                    'Further Mathematics', 'Statistics', 'A-Level Physics', 'A-Level Chemistry',
                    'A-Level Biology', 'World History', 'Geography', 'Psychology', 'Economics',
                    'Business Studies', 'English Literature'
                ]
            }
        }
        
        subjects_created = 0
        
        for stage_key, stage_data in school_structure.items():
            self.stdout.write(f'  📖 {stage_data["name"]}')
            
            for level in stage_data['levels']:
                for curriculum in stage_data['curricula']:
                    
                    # تحديد المواد المناسبة
                    base_subjects = subjects_by_curriculum[curriculum].copy()
                    
                    # إضافة المواد المتقدمة للمراحل المناسبة
                    if stage_key in advanced_subjects and curriculum in advanced_subjects[stage_key]:
                        if stage_key == 'preparatory' and level == 'الثالث':
                            base_subjects.extend(advanced_subjects[stage_key][curriculum])
                        elif stage_key == 'secondary':
                            base_subjects.extend(advanced_subjects[stage_key][curriculum])
                    
                    # معالجة خاصة للمنهج البريطاني (من الثالث الإعدادي فقط)
                    if curriculum == 'منهج بريطاني':
                        if stage_key == 'preparatory' and level in ['الأول', 'الثاني']:
                            continue
                        if stage_key in ['kg', 'primary']:
                            continue
                    
                    for subject_name in base_subjects:
                        full_subject_name = f"{subject_name} - {level} {stage_data['name'].replace('المرحلة ', '')} {curriculum}"
                        
                        # تبسيط الاسم قليلاً
                        full_subject_name = full_subject_name.replace('المرحلة ', '')
                        
                        try:
                            subject, created = Subject.objects.get_or_create(
                                name=full_subject_name,
                                defaults={
                                    'is_active': True,
                                    'code': self.generate_subject_code(subject_name, level, stage_key, curriculum)
                                }
                            )
                            
                            if created:
                                subjects_created += 1
                                
                        except Exception as e:
                            self.stdout.write(
                                self.style.WARNING(f'    ⚠️  خطأ في إنشاء: {full_subject_name} - {str(e)}')
                            )
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ تم إنشاء {subjects_created} مادة دراسية')
        )

    def generate_subject_code(self, subject, level, stage, curriculum):
        """إنشاء كود مختصر للمادة"""
        stage_codes = {
            'kg': 'KG',
            'primary': 'PR', 
            'preparatory': 'PP',
            'secondary': 'SC'
        }
        
        curriculum_codes = {
            'لغات': 'AR',
            'منهج أمريكي': 'US', 
            'منهج بريطاني': 'UK'
        }
        
        # أخذ أول 3 أحرف من المادة
        subject_code = ''.join([c for c in subject if c.isalpha()])[:3].upper()
        
        level_num = ['تمهيدي', 'الأول', 'الثاني', 'الثالث', 'الرابع', 'الخامس', 'السادس'].index(level) + 1
        
        return f"{stage_codes[stage]}{level_num}{curriculum_codes[curriculum]}{subject_code}"

    def create_notebooks(self):
        """إنشاء جميع أنواع الكراسات"""
        self.stdout.write('📝 إضافة الكراسات...')
        
        # أنواع الكراسات
        notebook_types = [
            # كراسات المواد الأساسية
            {
                'name': 'كراسة عربي مسطر',
                'type': 'LINED_NOTEBOOK',
                'description': 'كراسة مسطرة للغة العربية والإملاء',
                'pages': 40
            },
            {
                'name': 'كراسة عربي مسطر كبير',
                'type': 'LINED_NOTEBOOK',
                'description': 'كراسة مسطرة كبيرة للغة العربية',
                'pages': 60
            },
            {
                'name': 'كراسة انجليزي مسطر',
                'type': 'LINED_NOTEBOOK', 
                'description': 'كراسة مسطرة للغة الإنجليزية',
                'pages': 40
            },
            {
                'name': 'كراسة انجليزي 2 سطر',
                'type': 'TWO_LINE_NOTEBOOK',
                'description': 'كراسة بسطرين للغة الإنجليزية للمبتدئين',
                'pages': 40
            },
            {
                'name': 'كراسة انجليزي 4 سطور',
                'type': 'FOUR_LINE_NOTEBOOK',
                'description': 'كراسة بأربعة سطور للغة الإنجليزية للأطفال',
                'pages': 40
            },
            
            # كراسات العلوم والرياضيات
            {
                'name': 'كراسة علوم وجه واحد',
                'type': 'SINGLE_SIDE_NOTEBOOK',
                'description': 'كراسة وجه واحد للعلوم والرسم العلمي',
                'pages': 40
            },
            {
                'name': 'كراسة رياضيات مربعات',
                'type': 'SQUARED_NOTEBOOK',
                'description': 'كراسة مربعات للرياضيات والهندسة',
                'pages': 40
            },
            {
                'name': 'كراسة رياضيات مربعات كبير',
                'type': 'SQUARED_NOTEBOOK',
                'description': 'كراسة مربعات كبيرة للرياضيات',
                'pages': 60
            },
            {
                'name': 'كراسة هندسة مربعات صغيرة',
                'type': 'SMALL_SQUARED_NOTEBOOK',
                'description': 'كراسة مربعات صغيرة للهندسة والرسم الهندسي',
                'pages': 40
            },
            
            # كراسات متخصصة
            {
                'name': 'كراسة رسم بيضاء',
                'type': 'DRAWING_NOTEBOOK',
                'description': 'كراسة بيضاء للرسم والتربية الفنية',
                'pages': 30
            },
            {
                'name': 'كراسة موسيقى',
                'type': 'MUSIC_NOTEBOOK',
                'description': 'كراسة بخطوط موسيقية للتربية الموسيقية',
                'pages': 30
            },
            {
                'name': 'كراسة مذكرات',
                'type': 'NOTES_NOTEBOOK',
                'description': 'كراسة للمذكرات والملاحظات الشخصية',
                'pages': 50
            },
            {
                'name': 'كراسة امتحانات',
                'type': 'EXAM_NOTEBOOK',
                'description': 'كراسة إجابة للامتحانات',
                'pages': 16
            },
            
            # كراسات خاصة بالمناهج المختلفة
            {
                'name': 'كراسة إنجليزي منهج أمريكي',
                'type': 'LINED_NOTEBOOK',
                'description': 'كراسة مخصصة للمنهج الأمريكي',
                'pages': 50
            },
            {
                'name': 'كراسة إنجليزي منهج بريطاني',
                'type': 'LINED_NOTEBOOK',
                'description': 'كراسة مخصصة للمنهج البريطاني',
                'pages': 50
            },
            {
                'name': 'كراسة فرنسي مسطر',
                'type': 'LINED_NOTEBOOK',
                'description': 'كراسة مسطرة للغة الفرنسية',
                'pages': 40
            },
            
            # كراسات بأحجام مختلفة
            {
                'name': 'كراسة صغيرة مسطر',
                'type': 'SMALL_LINED_NOTEBOOK',
                'description': 'كراسة صغيرة للملاحظات السريعة',
                'pages': 25
            },
            {
                'name': 'كراسة كبيرة مسطر',
                'type': 'LARGE_LINED_NOTEBOOK',
                'description': 'كراسة كبيرة للمشاريع والأنشطة',
                'pages': 80
            },
            {
                'name': 'كراسة تحضير المعلم',
                'type': 'TEACHER_NOTEBOOK',
                'description': 'كراسة خاصة بتحضير الدروس للمعلمين',
                'pages': 100
            },
            
            # كراسات متنوعة
            {
                'name': 'كراسة ألوان وأنشطة',
                'type': 'ACTIVITY_NOTEBOOK',
                'description': 'كراسة للأنشطة والتلوين للأطفال',
                'pages': 30
            },
            {
                'name': 'كراسة خط عربي',
                'type': 'CALLIGRAPHY_NOTEBOOK',
                'description': 'كراسة لتعلم الخط العربي',
                'pages': 40
            },
            {
                'name': 'كراسة تدريبات',
                'type': 'EXERCISE_NOTEBOOK',
                'description': 'كراسة للتدريبات والتمارين المختلفة',
                'pages': 50
            }
        ]
        
        notebooks_created = 0
        
        for notebook_data in notebook_types:
            try:
                notebook, created = Notebook.objects.get_or_create(
                    name=notebook_data['name'],
                    defaults={
                        'notebook_type': notebook_data['type'],
                        'description': notebook_data['description'],
                        'pages_count': notebook_data.get('pages', 40),
                        'is_active': True,
                        'minimum_stock_level': 20,
                        'total_stock': 0,
                        'available_stock': 0,
                        'distributed_count': 0
                    }
                )
                
                if created:
                    notebooks_created += 1
                    self.stdout.write(f'    ✅ {notebook_data["name"]}')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'    ⚠️  خطأ في إنشاء: {notebook_data["name"]} - {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ تم إنشاء {notebooks_created} نوع كراسة')
        )

    def success(self, message):
        return self.style.SUCCESS(message)
    
    def error(self, message):
        return self.style.ERROR(message)
    
    def warning(self, message):
        return self.style.WARNING(message)
