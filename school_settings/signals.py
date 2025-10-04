from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

# Import SystemRole بعد تعريف User
from .models import SystemRole, SystemSettings, SettingsLog

@receiver(post_save, sender=SystemSettings)
def log_settings_change(sender, instance, created, **kwargs):
    """تسجيل تغيير الإعدادات في السجل"""
    if hasattr(instance, '_request'):
        request = instance._request
        user = getattr(request, 'user', None)
        ip_address = get_client_ip(request)
        
        action = 'CREATE' if created else 'UPDATE'
        
        SettingsLog.objects.create(
            user=user,
            action=action,
            setting_type='SystemSettings',
            new_value=str(instance),
            ip_address=ip_address
        )

def get_client_ip(request):
    """الحصول على عنوان IP للمستخدم"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@receiver(post_save, sender=SystemRole)
def assign_user_permissions(sender, instance, created, **kwargs):
    """تطبيق صلاحيات المجموعة تلقائياً عند إنشاء أو تعديل دور"""
    
    role_group_mapping = {
        'SYSTEM_ADMIN': 'مدير النظام',
        'SCHOOL_MANAGER': 'مدير المدرسة',
        'ACCOUNTANT': 'موظف الحسابات',
        'STUDENT_AFFAIRS': 'موظف شؤون الطلاب',
        'BOOKS_INVENTORY': 'موظف مخزن الكتب',
        'UNIFORMS_INVENTORY': 'موظف مخزن الملابس',
    }
    
    user = instance.user
    role = instance.role
    
    if instance.is_active and role in role_group_mapping:
        group_name = role_group_mapping[role]
        try:
            group = Group.objects.get(name=group_name)
            
            # إزالة المستخدم من جميع المجموعات السابقة
            user.groups.clear()
            
            # إضافة المستخدم للمجموعة الجديدة
            user.groups.add(group)
            
            # تحديد صلاحية is_staff
            user.is_staff = True
            user.save()
            
        except Group.DoesNotExist:
            # إنشاء المجموعة إذا لم تكن موجودة
            create_missing_group(group_name, role)
            
    elif not instance.is_active:
        # إزالة المستخدم من جميع المجموعات إذا تم إلغاء تفعيل الدور
        user.groups.clear()
        if not user.is_superuser:
            user.is_staff = False
        user.save()

@receiver(post_delete, sender=SystemRole)
def remove_user_permissions(sender, instance, **kwargs):
    """إزالة صلاحيات المستخدم عند حذف دوره"""
    user = instance.user
    user.groups.clear()
    if not user.is_superuser:
        user.is_staff = False
        user.save()

def create_missing_group(group_name, role):
    """إنشاء المجموعة المفقودة مع الصلاحيات المناسبة"""
    from django.contrib.auth.models import Permission
    
    group = Group.objects.create(name=group_name)
    
    # تحديد الصلاحيات حسب الدور
    if role == 'SYSTEM_ADMIN':
        permissions = Permission.objects.all()
    elif role == 'SCHOOL_MANAGER':
        permissions = Permission.objects.filter(
            codename__in=[
                'view_user', 'change_user', 'add_user',
                'add_student', 'change_student', 'view_student', 'delete_student',
                'add_classroom', 'change_classroom', 'view_classroom',
                'view_tuition', 'change_tuition',
                'add_expense', 'change_expense', 'view_expense',
                'view_systemsettings', 'change_systemsettings',
                'view_systemrole', 'change_systemrole', 'add_systemrole',
            ]
        )
    elif role == 'ACCOUNTANT':
        permissions = Permission.objects.filter(
            codename__in=[
                'view_student',
                'add_tuition', 'change_tuition', 'view_tuition',
                'add_expense', 'change_expense', 'view_expense',
                'view_systemsettings',
            ]
        )
    elif role == 'STUDENT_AFFAIRS':
        permissions = Permission.objects.filter(
            codename__in=[
                'add_student', 'change_student', 'view_student',
                'view_classroom',
                'add_archivestudent', 'change_archivestudent', 'view_archivestudent',
                'view_tuition',
            ]
        )
    else:
        permissions = Permission.objects.filter(
            codename__in=['view_student', 'view_classroom']
        )
    
    group.permissions.set(permissions)
    return group
