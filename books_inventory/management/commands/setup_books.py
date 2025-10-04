from django.core.management.base import BaseCommand
from books_inventory.models import Book, Subject
from students.models import GradeLevel
from decimal import Decimal

class Command(BaseCommand):
    help = 'إنشاء جميع الكتب المدرسية بناءً على المواد الموجودة'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('📖 بدء إنشاء الكتب المدرسية...'))
        
        # أنواع الكتب لكل مادة أساسية
        book_templates = {
            # كتب اللغة العربية
            'اللغة العربية': [
                {
                    'title_template': 'كتاب اللغة العربية',
                    'book_type': 'MINISTRY',
                    'pages': 160,
                    'cost_price': 45.00
                },
                {
                    'title_template': 'كتاب المنار - اللغة العربية',
                    'book_type': 'MANAR_BOOK', 
                    'pages': 152,
                    'cost_price': 67.00
                },
                {
                    'title_template': 'كتاب التمارين - اللغة العربية',
                    'book_type': 'WORKBOOK',
                    'pages': 80,
                    'cost_price': 35.00
                }
            ],
            
            # كتب اللغة الإنجليزية
            'اللغة الإنجليزية': [
                {
                    'title_template': 'كتاب اللغة الإنجليزية',
                    'book_type': 'MINISTRY',
                    'pages': 140,
                    'cost_price': 48.00
                },
                {
                    'title_template': 'كتاب المنار - اللغة الإنجليزية', 
                    'book_type': 'MANAR_BOOK',
                    'pages': 135,
                    'cost_price': 72.00
                },
                {
                    'title_template': 'قاموس إنجليزي عربي',
                    'book_type': 'DICTIONARY',
                    'pages': 400,
                    'cost_price': 85.00
                }
            ],
            
            # كتب الرياضيات
            'الرياضيات': [
                {
                    'title_template': 'كتاب الرياضيات',
                    'book_type': 'MINISTRY',
                    'pages': 180,
                    'cost_price': 52.00
                },
                {
                    'title_template': 'كتاب المنار - الرياضيات',
                    'book_type': 'MANAR_BOOK',
                    'pages': 165,
                    'cost_price': 75.00
                },
                {
                    'title_template': 'تمارين المنار - الرياضيات',
                    'book_type': 'MANAR_EXERCISES',
                    'pages': 95,
                    'cost_price': 42.00
                }
            ],
            
            # كتب العلوم
            'العلوم': [
                {
                    'title_template': 'كتاب العلوم',
                    'book_type': 'MINISTRY', 
                    'pages': 170,
                    'cost_price': 55.00
                },
                {
                    'title_template': 'كتاب المنار - العلوم',
                    'book_type': 'MANAR_BOOK',
                    'pages': 158,
                    'cost_price': 78.00
                },
                {
                    'title_template': 'كتاب التجارب - العلوم',
                    'book_type': 'WORKBOOK',
                    'pages': 65,
                    'cost_price': 38.00
                }
            ],
            
            # كتب الدراسات الاجتماعية
            'الدراسات الاجتماعية': [
                {
                    'title_template': 'كتاب الدراسات الاجتماعية',
                    'book_type': 'MINISTRY',
                    'pages': 145,
                    'cost_price': 44.00
                },
                {
                    'title_template': 'أطلس الدراسات الاجتماعية',
                    'book_type': 'ATLAS',
                    'pages': 85,
                    'cost_price': 62.00
                }
            ],
            
            # كتب التربية الدينية
            'التربية الدينية': [
                {
                    'title_template': 'كتاب التربية الدينية',
                    'book_type': 'MINISTRY',
                    'pages': 120,
                    'cost_price': 32.00
                },
                {
                    'title_template': 'كتاب المنار - التربية الدينية',
                    'book_type': 'MANAR_BOOK',
                    'pages': 110,
                    'cost_price': 48.00
                }
            ],
            
            # باقي المواد
            'التربية الفنية': [
                {
                    'title_template': 'كتاب التربية الفنية',
                    'book_type': 'MINISTRY',
                    'pages': 95,
                    'cost_price': 38.00
                }
            ],
            
            'التربية الموسيقية': [
                {
                    'title_template': 'كتاب التربية الموسيقية',
                    'book_type': 'MINISTRY',
                    'pages': 75,
                    'cost_price': 28.00
                }
            ],
            
            'الحاسوب': [
                {
                    'title_template': 'كتاب الحاسوب',
                    'book_type': 'MINISTRY',
                    'pages': 125,
                    'cost_price': 58.00
                },
                {
                    'title_template': 'كتاب التطبيقات - الحاسوب',
                    'book_type': 'WORKBOOK',
                    'pages': 85,
                    'cost_price': 42.00
                }
            ]
        }
        
        # كتب المواد المتقدمة (إعدادي وثانوي)
        advanced_book_templates = {
            'الفيزياء': [
                {
                    'title_template': 'كتاب الفيزياء',
                    'book_type': 'MINISTRY',
                    'pages': 220,
                    'cost_price': 68.00
                },
                {
                    'title_template': 'كتاب المنار - الفيزياء',
                    'book_type': 'MANAR_BOOK',
                    'pages': 195,
                    'cost_price': 85.00
                }
            ],
            
            'الكيمياء': [
                {
                    'title_template': 'كتاب الكيمياء',
                    'book_type': 'MINISTRY',
                    'pages': 210,
                    'cost_price': 65.00
                },
                {
                    'title_template': 'كتاب المنار - الكيمياء',
                    'book_type': 'MANAR_BOOK',
                    'pages': 185,
                    'cost_price': 82.00
                }
            ],
            
            'الأحياء': [
                {
                    'title_template': 'كتاب الأحياء',
                    'book_type': 'MINISTRY',
                    'pages': 200,
                    'cost_price': 62.00
                },
                {
                    'title_template': 'كتاب المنار - الأحياء',
                    'book_type': 'MANAR_BOOK',
                    'pages': 175,
                    'cost_price': 78.00
                }
            ],
            
            'الجغرافيا': [
                {
                    'title_template': 'كتاب الجغرافيا',
                    'book_type': 'MINISTRY',
                    'pages': 165,
                    'cost_price': 48.00
                },
                {
                    'title_template': 'أطلس الجغرافيا',
                    'book_type': 'ATLAS',
                    'pages': 95,
                    'cost_price': 72.00
                }
            ],
            
            'التاريخ': [
                {
                    'title_template': 'كتاب التاريخ',
                    'book_type': 'MINISTRY',
                    'pages': 175,
                    'cost_price': 52.00
                },
                {
                    'title_template': 'ملخص المنار - التاريخ',
                    'book_type': 'MANAR_SUMMARY',
                    'pages': 95,
                    'cost_price': 38.00
                }
            ],
            
            'الفلسفة': [
                {
                    'title_template': 'كتاب الفلسفة',
                    'book_type': 'MINISTRY',
                    'pages': 185,
                    'cost_price': 55.00
                }
            ],
            
            'علم النفس': [
                {
                    'title_template': 'كتاب علم النفس',
                    'book_type': 'MINISTRY',
                    'pages': 165,
                    'cost_price': 48.00
                }
            ]
        }

        # كتب المناهج الأجنبية
        foreign_curriculum_books = {
            # المنهج الأمريكي
            'اللغة الإنجليزية وآدابها': [
                {
                    'title_template': 'English Language Arts',
                    'book_type': 'MINISTRY',
                    'pages': 285,
                    'cost_price': 120.00
                }
            ],
            'الجبر': [
                {
                    'title_template': 'Algebra Textbook',
                    'book_type': 'MINISTRY',
                    'pages': 320,
                    'cost_price': 135.00
                }
            ],
            'أحياء متقدم': [
                {
                    'title_template': 'AP Biology',
                    'book_type': 'MINISTRY',
                    'pages': 450,
                    'cost_price': 185.00
                }
            ],
            
            # المنهج البريطاني
            'اللغة الإنجليزية IGCSE': [
                {
                    'title_template': 'IGCSE English Language',
                    'book_type': 'MINISTRY',
                    'pages': 265,
                    'cost_price': 145.00
                }
            ],
            'رياضيات IGCSE': [
                {
                    'title_template': 'IGCSE Mathematics',
                    'book_type': 'MINISTRY',
                    'pages': 295,
                    'cost_price': 155.00
                }
            ]
        }

        created_count = 0
        current_year = '2025/2026'
        edition_year = '2025'

        # الحصول على جميع المواد من قاعدة البيانات
        subjects = Subject.objects.all()
        
        for subject in subjects:
            try:
                # تحليل اسم المادة للحصول على المعلومات
                subject_parts = subject.name.split(' - ')
                if len(subject_parts) < 3:
                    continue
                    
                base_subject = subject_parts[0]  # اسم المادة الأساسي
                grade_info = subject_parts[1]    # معلومات الصف
                curriculum = subject_parts[2]    # نوع المنهج
                
                # اختيار قوالب الكتب المناسبة
                books_to_create = []
                
                # البحث في الكتب الأساسية
                for subject_key, book_list in book_templates.items():
                    if subject_key in base_subject:
                        books_to_create.extend(book_list)
                        break
                
                # البحث في الكتب المتقدمة
                for subject_key, book_list in advanced_book_templates.items():
                    if subject_key in base_subject:
                        books_to_create.extend(book_list)
                        break
                
                # البحث في كتب المناهج الأجنبية
                for subject_key, book_list in foreign_curriculum_books.items():
                    if subject_key in base_subject:
                        books_to_create.extend(book_list)
                        break
                
                # إنشاء الكتب
                for book_template in books_to_create:
                    # تكوين عنوان الكتاب
                    book_title = book_template['title_template']
                    
                    # البحث عن الصف المرتبط بالمادة
                    grade_level = None
                    try:
                        # محاولة العثور على الصف من اسم المادة
                        grades = GradeLevel.objects.filter(name__icontains=grade_info.split()[-1])
                        if grades.exists():
                            grade_level = grades.first()
                    except:
                        pass
                    
                    # إنشاء الكتاب
                    book, created = Book.objects.get_or_create(
                        title=book_title,
                        subject=subject,
                        defaults={
                            'book_type': book_template['book_type'],
                            'academic_year': current_year,
                            'term': 'FULL_YEAR',
                            'edition_year': edition_year,
                            'pages_count': book_template['pages'],
                            'cost_price': Decimal(str(book_template['cost_price'])),
                            'description': f"{book_title} - {subject.name}",
                            'minimum_stock_level': 15,
                            'is_active': True,
                            'total_stock': 0,
                            'available_stock': 0,
                            'distributed_count': 0,
                            'damaged_count': 0
                        }
                    )
                    
                    if created:
                        # ربط الكتاب بالصف إن وجد
                        if grade_level:
                            book.grade_levels.add(grade_level)
                        
                        created_count += 1
                        curriculum_emoji = self._get_curriculum_emoji(curriculum)
                        self.stdout.write(f'{curriculum_emoji} تم إنشاء: {book_title} - {subject.name}')
                        
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ تعذر معالجة المادة {subject.name}: {e}')
                )
                continue

        self.stdout.write(
            self.style.SUCCESS(f'🎉 تم إنشاء {created_count} كتاب مدرسي بنجاح!')
        )
        
        # إحصائيات سريعة
        total_books = Book.objects.count()
        total_subjects = Subject.objects.count()
        
        self.stdout.write(
            self.style.SUCCESS(f'''
📊 إحصائيات المخزن:
   📚 إجمالي المواد: {total_subjects}
   📖 إجمالي الكتب: {total_books}
   ✨ الكتب الجديدة: {created_count}
            ''')
        )

    def _get_curriculum_emoji(self, curriculum):
        """الحصول على emoji مناسب لنوع المنهج"""
        if 'أمريكي' in curriculum:
            return '🇺🇸'
        elif 'بريطاني' in curriculum:
            return '🇬🇧'
        else:
            return '📚'
