from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
import logging

from .models import SystemRole, SystemSettings, SettingsLog

logger = logging.getLogger(__name__)
User = get_user_model()


def get_client_ip(request):
    """الحصول على عنوان IP للمستخدم بطريقة آمنة"""
    try:
        if not request:
            return None

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()[:45]

        remote_addr = request.META.get('REMOTE_ADDR')
        return remote_addr[:45] if remote_addr else None
    except Exception:
        return None


def get_safe_user(user):
    """إرجاع المستخدم فقط لو مسجل دخول فعلاً"""
    try:
        if user and getattr(user, 'is_authenticated', False):
            return user
    except Exception:
        pass
    return None


@receiver(post_save, sender=SystemSettings)
def log_system_settings_change(sender, instance, created, **kwargs):
    """
    تسجيل تغيير إعدادات النظام.

    ملاحظة:
    هذا الـ signal لا يعمل Query عند تحميل Django.
    التسجيل يتم فقط عند حفظ SystemSettings.
    """
    try:
        request = getattr(instance, '_request', None)
        user = get_safe_user(getattr(request, 'user', None)) if request else None

        action = 'CREATE' if created else 'UPDATE'

        # استخدم الدالة الآمنة الموجودة في SettingsLog إن كانت متاحة
        if hasattr(SettingsLog, 'log_action'):
            SettingsLog.log_action(
                user=user,
                action=action,
                setting_type='SYSTEM_SETTING',
                object_id=instance.pk,
                object_name=str(instance),
                new_value=str(instance),
                description='تغيير إعدادات النظام',
                request=request
            )
        else:
            SettingsLog.objects.create(
                user=user,
                action=action,
                setting_type='SYSTEM_SETTING',
                object_id=instance.pk,
                object_name=str(instance)[:200],
                new_value=str(instance)[:1000],
                description='تغيير إعدادات النظام',
                ip_address=get_client_ip(request) if request else None,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''
            )

    except Exception as e:
        logger.error(f"خطأ في تسجيل تغيير إعدادات النظام: {e}")


# خريطة الأدوار والمجموعات.
# تم توحيد أسماء المجموعات مع SystemRole.apply_role_groups في models.py
ROLE_GROUP_MAPPING = {
    # الأدوار الأساسية
    'SYSTEM_ADMIN': ['مدير النظام'],
    'SCHOOL_MANAGER': ['مدير المدرسة'],
    'ACCOUNTANT': ['treasury_accountant'],
    'STUDENT_AFFAIRS': ['موظف شؤون الطلاب'],

    # أدوار الخزينة
    'TREASURY_ADMIN': ['treasury_admin'],
    'TREASURY_MANAGER': ['treasury_manager'],
    'TREASURY_ACCOUNTANT': ['treasury_accountant'],
    'TREASURY_CASHIER': ['treasury_cashier'],
    'TREASURY_VIEWER': ['treasury_viewer'],

    # أدوار المخازن
    'BOOKS_INVENTORY': ['books_inventory_staff'],
    'UNIFORMS_INVENTORY': ['uniforms_inventory_staff'],
    'INVENTORY_MANAGER': [
        'books_inventory_staff',
        'uniforms_inventory_staff',
        'treasury_manager',
    ],
}


def get_permissions_for_role(role):
    """تحديد الصلاحيات المناسبة حسب الدور"""
    if role == 'SYSTEM_ADMIN':
        return Permission.objects.all()

    if role == 'SCHOOL_MANAGER':
        return Permission.objects.filter(
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

    if role in ['ACCOUNTANT', 'TREASURY_ACCOUNTANT', 'TREASURY_CASHIER']:
        return Permission.objects.filter(
            codename__in=[
                'view_student',
                'add_tuition', 'change_tuition', 'view_tuition',
                'add_expense', 'change_expense', 'view_expense',
                'view_systemsettings',
            ]
        )

    if role == 'STUDENT_AFFAIRS':
        return Permission.objects.filter(
            codename__in=[
                'add_student', 'change_student', 'view_student',
                'view_classroom',
                'add_archivestudent', 'change_archivestudent', 'view_archivestudent',
                'view_tuition',
            ]
        )

    if role in ['BOOKS_INVENTORY', 'UNIFORMS_INVENTORY', 'INVENTORY_MANAGER']:
        return Permission.objects.filter(
            codename__icontains='inventory'
        )

    return Permission.objects.filter(
        codename__in=['view_student', 'view_classroom']
    )


def create_missing_group(group_name, role):
    """إنشاء المجموعة المفقودة مع الصلاحيات المناسبة"""
    group, created = Group.objects.get_or_create(name=group_name)

    if created:
        permissions = get_permissions_for_role(role)
        group.permissions.set(permissions)

    return group


@receiver(post_save, sender=SystemRole)
def assign_user_permissions(sender, instance, created, **kwargs):
    """
    تطبيق صلاحيات المجموعة تلقائياً عند إنشاء أو تعديل دور المستخدم.

    ملاحظة مهمة:
    يوجد في models.py دالة apply_role_groups داخل SystemRole.save.
    لذلك هنا جعلنا الكود آمناً ومتكاملاً، بدون كسر التشغيل لو كانت المجموعات غير موجودة.
    """
    try:
        user = instance.user
        role = instance.role

        # لو المستخدم superuser لا نمسح مجموعاته
        should_clear_groups = not user.is_superuser

        if instance.is_active:
            group_names = ROLE_GROUP_MAPPING.get(role, [])

            if should_clear_groups:
                user.groups.clear()

            for group_name in group_names:
                group = create_missing_group(group_name, role)
                user.groups.add(group)

            # أي مستخدم له دور نشط يدخل لوحة الإدارة
            if not user.is_staff:
                user.is_staff = True
                user.save(update_fields=['is_staff'])

        else:
            if should_clear_groups:
                user.groups.clear()

            if not user.is_superuser and user.is_staff:
                user.is_staff = False
                user.save(update_fields=['is_staff'])

    except Exception as e:
        logger.error(f"خطأ في تطبيق صلاحيات المستخدم: {e}")


@receiver(post_delete, sender=SystemRole)
def remove_user_permissions(sender, instance, **kwargs):
    """إزالة صلاحيات المستخدم عند حذف دوره"""
    try:
        user = instance.user

        if not user.is_superuser:
            user.groups.clear()

            if user.is_staff:
                user.is_staff = False
                user.save(update_fields=['is_staff'])

    except Exception as e:
        logger.error(f"خطأ في إزالة صلاحيات المستخدم: {e}")
