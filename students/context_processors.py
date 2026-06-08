# students/context_processors.py
from home.decorators import get_user_role


def students_permissions(request):
    """
    صلاحيات تطبيق الطلاب المتاحة لكل قوالب الطلاب تلقائياً.
    هذا يمنع مشكلة ظهور "غير متاح لهذا الحساب" في sidebar
    رغم أن المستخدم عنده صلاحية فعلية.
    """

    user = getattr(request, 'user', None)

    if not user or not user.is_authenticated:
        return {
            'permissions': {},
            'user_role': None,
        }

    if user.is_superuser:
        user_role = 'SYSTEM_ADMIN'
    else:
        user_role = get_user_role(user)

    permissions = {
        # الطلاب
        'can_add': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'STUDENT_AFFAIRS'],
        'can_edit': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'STUDENT_AFFAIRS'],
        'can_delete': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'STUDENT_AFFAIRS'],
        'can_archive': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'STUDENT_AFFAIRS'],

        # الاستيراد والتصدير
        'can_import': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'STUDENT_AFFAIRS'],
        'can_export': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'STUDENT_AFFAIRS'],

        # التقارير والعمليات الحساسة
        'can_reports': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'],
        'can_upgrade': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'],
        'can_financial_sync': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'],

        # معلومات الدور
        'is_student_affairs_only': user_role == 'STUDENT_AFFAIRS',
        'is_manager': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'],
        'is_system_admin': user_role == 'SYSTEM_ADMIN',
    }

    return {
        'permissions': permissions,
        'user_role': user_role,
    }