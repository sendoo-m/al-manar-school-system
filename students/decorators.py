# students/decorators.py - إنشاء ملف جديد
from home.decorators import role_required

# decorators مخصصة لتطبيق الطلاب
students_basic_access = role_required(
    ['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'STUDENT_AFFAIRS'],
    redirect_to='home:access_denied'
)

students_add_only = role_required(
    ['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'STUDENT_AFFAIRS'],
    redirect_to='home:access_denied'
)

students_full_access = role_required(
    ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'],
    redirect_to='home:access_denied'
)

students_reports_access = role_required(
    ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'],
    redirect_to='home:access_denied'
)

students_admin_access = role_required(
    ['SYSTEM_ADMIN'],
    redirect_to='home:access_denied'
)

# decorator مخصص للعمليات الحساسة
def students_sensitive_operation(view_func):
    """decorator للعمليات الحساسة مثل الحذف والتصدير"""
    return students_admin_access(view_func)

# decorator للتقارير المتقدمة
def students_advanced_reports(view_func):
    """decorator للتقارير المتقدمة"""
    return students_reports_access(view_func)
