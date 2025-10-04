from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from school_settings.models import SystemRole

User = get_user_model()

class Command(BaseCommand):
    help = 'تعيين أدوار افتراضية للمستخدمين'

    def add_arguments(self, parser):
        parser.add_argument('--create-admin', action='store_true', help='إنشاء مستخدم مدير افتراضي')

    def handle(self, *args, **options):
        if options['create_admin']:
            # إنشاء مستخدم مدير افتراضي
            admin_user, created = User.objects.get_or_create(
                username='admin',
                defaults={
                    'is_staff': True,
                    'is_superuser': True,
                    'is_active': True
                }
            )
            
            if created:
                admin_user.set_password('admin123')
                admin_user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'تم إنشاء المستخدم: admin بكلمة مرور: admin123')
                )
            else:
                self.stdout.write(f'المستخدم admin موجود مسبقاً')
            
            # تعيين دور مدير النظام
            system_role, role_created = SystemRole.objects.get_or_create(
                user=admin_user,
                defaults={
                    'role': 'SYSTEM_ADMIN',
                    'is_active': True
                }
            )
            
            if role_created:
                self.stdout.write(
                    self.style.SUCCESS(f'تم تعيين دور مدير النظام للمستخدم: {admin_user.username}')
                )
            else:
                self.stdout.write(f'الدور موجود مسبقاً للمستخدم: {admin_user.username}')
        
        # تعيين أدوار افتراضية للمستخدمين بدون أدوار
        users_without_roles = User.objects.filter(system_role__isnull=True)
        count = 0
        
        for user in users_without_roles:
            if user.is_superuser:
                role = 'SYSTEM_ADMIN'
            elif user.is_staff:
                role = 'SCHOOL_MANAGER'
            else:
                role = 'STUDENT_AFFAIRS'  # دور افتراضي
            
            SystemRole.objects.create(
                user=user,
                role=role,
                is_active=True
            )
            
            self.stdout.write(f'تم تعيين الدور {role} للمستخدم: {user.username}')
            count += 1
        
        if count == 0:
            self.stdout.write('جميع المستخدمين لديهم أدوار محددة مسبقاً')
        
        self.stdout.write(
            self.style.SUCCESS(f'تم الانتهاء من تعيين الأدوار لـ {count} مستخدم')
        )
