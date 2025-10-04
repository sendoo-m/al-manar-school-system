from django.core.management.base import BaseCommand
from school_settings.models import migrate_old_students_data

class Command(BaseCommand):
    help = 'نقل بيانات الطلاب من النظام القديم إلى نظام الإعدادات الجديد'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('بدء عملية نقل البيانات...'))
        
        try:
            migrate_old_students_data()
            self.stdout.write(
                self.style.SUCCESS('تم نقل البيانات بنجاح!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'حدث خطأ أثناء النقل: {str(e)}')
            )
