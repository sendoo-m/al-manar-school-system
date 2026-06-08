# students/decorators.py
from home.decorators import role_required

# ============================================================
# صلاحيات تطبيق الطلاب
# ============================================================

# عرض أساسي: قائمة الطلاب، ملف الطالب، البحث
students_basic_access = role_required(
    [
        'SYSTEM_ADMIN',
        'SCHOOL_MANAGER',
        'STUDENT_AFFAIRS',
    ],
    redirect_to='home:access_denied'
)

# إضافة طالب
students_add_only = role_required(
    [
        'SYSTEM_ADMIN',
        'SCHOOL_MANAGER',
        'STUDENT_AFFAIRS',
    ],
    redirect_to='home:access_denied'
)

# تعديل بيانات الطالب
# تم السماح لموظف شئون الطلاب بالتعديل بناءً على احتياج التشغيل الفعلي
students_edit_access = role_required(
    [
        'SYSTEM_ADMIN',
        'SCHOOL_MANAGER',
        'STUDENT_AFFAIRS',
    ],
    redirect_to='home:access_denied'
)

# أرشفة الطالب
# تم السماح لموظف شئون الطلاب بالأرشفة لأنها ليست حذفاً نهائياً
students_archive_access = role_required(
    [
        'SYSTEM_ADMIN',
        'SCHOOL_MANAGER',
        'STUDENT_AFFAIRS',
    ],
    redirect_to='home:access_denied'
)

# صلاحية كاملة قديمة، تُستخدم في أماكن أخرى لو موجودة
students_full_access = role_required(
    [
        'SYSTEM_ADMIN',
        'SCHOOL_MANAGER',
        'STUDENT_AFFAIRS',
    ],
    redirect_to='home:access_denied'
)

# تقارير الطلاب
students_reports_access = role_required(
    [
        'SYSTEM_ADMIN',
        'SCHOOL_MANAGER',
    ],
    redirect_to='home:access_denied'
)

# عمليات إدارية حساسة جداً
students_admin_access = role_required(
    [
        'SYSTEM_ADMIN',
    ],
    redirect_to='home:access_denied'
)


def students_sensitive_operation(view_func):
    """
    العمليات الحساسة داخل الطلاب.

    ملاحظة:
    كانت سابقاً SYSTEM_ADMIN فقط.
    لكن بما أن حذف الطالب عندنا هو أرشفة وليس حذفاً نهائياً،
    أصبح يمكن استخدام students_archive_access مباشرة مع دالة الأرشفة.
    """
    return students_admin_access(view_func)


def students_advanced_reports(view_func):
    """Decorator للتقارير المتقدمة"""
    return students_reports_access(view_func)

# استيراد وتصدير الطلاب
students_import_export_access = role_required(
    [
        'SYSTEM_ADMIN',
        'SCHOOL_MANAGER',
        'STUDENT_AFFAIRS',
    ],
    redirect_to='home:access_denied'
)