from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from school_settings.models import SystemRole

User = get_user_model()

class Command(BaseCommand):
    help = 'تطبيق الصلاحيات على المستخدمين حسب أدوارهم'

    def handle(self, *args, **options):
        # تطبيق المجموعات على المستخدمين حسب أدوارهم
        role_group_mapping = {
            'SYSTEM_ADMIN': 'مدير النظام',
            'SCHOOL_MANAGER': 'مدير المدرسة',
            'ACCOUNTANT': 'موظف الحسابات',
            'STUDENT_AFFAIRS': 'موظف شؤون الطلاب',
            'BOOKS_INVENTORY': 'موظف مخزن الكتب',
            'UNIFORMS_INVENTORY': 'موظف مخزن الملابس',
        }
        
        updated_count = 0
        for system_role in SystemRole.objects.filter(is_active=True):
            user = system_role.user
            role = system_role.role
            
            if role in role_group_mapping:
                group_name = role_group_mapping[role]
                try:
                    group = Group.objects.get(name=group_name)
                    
                    # إزالة المستخدم من جميع المجموعات السابقة
                    user.groups.clear()
                    
                    # إضافة المستخدم للمجموعة الجديدة
                    user.groups.add(group)
                    
                    # تحديد صلاحيات is_staff حسب الدور
                    if role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
                        user.is_staff = True
                    else:
                        user.is_staff = True  # السماح للجميع بالوصول للـ admin
                    
                    user.save()
                    updated_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'تم تطبيق صلاحيات {group_name} على {user.username}')
                    )
                    
                except Group.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'المجموعة {group_name} غير موجودة')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'تم تحديث صلاحيات {updated_count} مستخدم')
        )
