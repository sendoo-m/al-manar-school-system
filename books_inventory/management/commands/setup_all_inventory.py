from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'إعداد جميع بيانات المخزن (المواد والكتب والكراسات)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='حذف البيانات الموجودة وإنشاء جديدة'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 بدء إعداد بيانات المخزن الشاملة...'))
        
        reset_data = options.get('reset', False)
        
        if reset_data:
            self.stdout.write(self.style.WARNING('⚠️ سيتم حذف البيانات الموجودة...'))
            
            # حذف البيانات الموجودة
            from books_inventory.models import Book, Subject, Notebook
            
            Book.objects.all().delete()
            Subject.objects.all().delete() 
            Notebook.objects.all().delete()
            
            self.stdout.write(self.style.SUCCESS('✅ تم حذف البيانات القديمة'))
        
        try:
            # إنشاء المواد الدراسية أولاً
            self.stdout.write('📚 إنشاء المواد الدراسية...')
            call_command('setup_subjects')
            
            # إنشاء الكتب بناءً على المواد
            self.stdout.write('📖 إنشاء الكتب المدرسية...')
            call_command('setup_books')
            
            # إنشاء أنواع الكراسات
            self.stdout.write('📓 إنشاء أنواع الكراسات...')
            call_command('setup_notebooks')
            
            self.stdout.write(
                self.style.SUCCESS('🎉 تم إعداد جميع بيانات المخزن بنجاح!')
            )
            
            # إحصائيات نهائية
            from books_inventory.models import Subject, Book, Notebook
            
            subjects_count = Subject.objects.count()
            books_count = Book.objects.count()
            notebooks_count = Notebook.objects.count()
            
            self.stdout.write(
                self.style.SUCCESS(f'''
📊 الإحصائيات النهائية:
   📚 المواد الدراسية: {subjects_count}
   📖 الكتب المدرسية: {books_count}
   📓 أنواع الكراسات: {notebooks_count}
                ''')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ خطأ في الإعداد: {e}')
            )
