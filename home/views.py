# home/views.py - النسخة المحدثة
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.views.decorators.cache import never_cache
from datetime import datetime
from django.utils import timezone
from .decorators import (
    system_admin_required, 
    school_manager_required, 
    accountant_required,
    student_affairs_required,
    books_inventory_required,
    uniforms_inventory_required,
    get_user_role
)

# صفحة تسجيل الدخول المخصصة (نفسها)
class CustomLoginView(auth_views.LoginView):
    template_name = 'home/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        user = self.request.user
        role = get_user_role(user)
        
        if role == 'SYSTEM_ADMIN':
            return reverse_lazy('home:admin_dashboard')
        elif role == 'SCHOOL_MANAGER':
            return reverse_lazy('home:manager_dashboard')
        elif role == 'ACCOUNTANT':
            return reverse_lazy('payments:payments_home')
        elif role == 'STUDENT_AFFAIRS':
            return reverse_lazy('students:student_affairs_home')
        elif role == 'BOOKS_INVENTORY':
            return reverse_lazy('home:books_inventory_dashboard')
        elif role == 'UNIFORMS_INVENTORY':
            return reverse_lazy('home:uniforms_inventory_dashboard')
        else:
            return reverse_lazy('home:default_dashboard')

# دالة مساعدة لإضافة Context مشترك
def get_common_context(request):
    return {
        'today': timezone.now().date(),
        'current_time': timezone.now().time(),
        'user_role': get_user_role(request.user),
    }

@never_cache
@system_admin_required
def admin_dashboard(request):
    """لوحة تحكم المدير العام"""
    context = get_common_context(request)
    return render(request, 'home/admin_dashboard.html', context)

@never_cache
@school_manager_required
def manager_dashboard(request):
    """لوحة تحكل مدير المدرسة"""
    context = get_common_context(request)
    return render(request, 'home/manager_dashboard.html', context)

@never_cache
@accountant_required
def accountant_dashboard(request):
    """لوحة تحكم المحاسب"""
    return redirect('payments:payments_home')

@never_cache
@student_affairs_required
def student_affairs_dashboard(request):
    """لوحة تحكم شؤون الطلاب"""
    return redirect('students:student_affairs_home')

@never_cache
@books_inventory_required
def books_inventory_dashboard(request):
    """لوحة تحكم مخزن الكتب"""
    context = get_common_context(request)
    return render(request, 'home/books_inventory_dashboard.html', context)

@never_cache
@uniforms_inventory_required
def uniforms_inventory_dashboard(request):
    """لوحة تحكم مخزن الملابس"""
    context = get_common_context(request)
    return render(request, 'home/uniforms_inventory_dashboard.html', context)

@never_cache
@login_required
def default_dashboard(request):
    """لوحة التحكم الافتراضية"""
    user_role = get_user_role(request.user)
    context = get_common_context(request)
    context.update({
        'user_role_display': get_role_display_name(user_role),
        'message': 'لم يتم تحديد دور مناسب لحسابك. يرجى التواصل مع إدارة النظام.',
        'suggested_actions': get_suggested_actions(user_role),
    })
    return render(request, 'home/default_dashboard.html', context)

def logout_view(request):
    """تسجيل الخروج"""
    auth_logout(request)
    messages.success(request, 'تم تسجيل الخروج بنجاح')
    return redirect('home:login')

def get_role_display_name(role):
    """الحصول على الاسم العربي للدور"""
    role_names = {
        'SYSTEM_ADMIN': 'مدير النظام',
        'SCHOOL_MANAGER': 'مدير المدرسة',
        'ACCOUNTANT': 'محاسب',
        'STUDENT_AFFAIRS': 'شؤون الطلاب',
        'BOOKS_INVENTORY': 'أمين مخزن الكتب',
        'UNIFORMS_INVENTORY': 'أمين مخزن الملابس',
    }
    return role_names.get(role, 'غير محدد')

def get_suggested_actions(role):
    """الحصول على إجراءات مقترحة حسب الدور"""
    actions = {
        'SYSTEM_ADMIN': [
            {'name': 'لوحة التحكل الإدارية', 'url': '/admin/', 'icon': 'fas fa-cogs'},
            {'name': 'إدارة المستخدمين', 'url': '#', 'icon': 'fas fa-users'},
        ],
        'SCHOOL_MANAGER': [
            {'name': 'التقارير الإدارية', 'url': '#', 'icon': 'fas fa-chart-bar'},
            {'name': 'إعدادات المدرسة', 'url': '#', 'icon': 'fas fa-school'},
        ],
        'ACCOUNTANT': [
            {'name': 'نظام المدفوعات', 'url': '/payments/', 'icon': 'fas fa-money-bill'},
            {'name': 'التقارير المالية', 'url': '#', 'icon': 'fas fa-calculator'},
        ],
        'STUDENT_AFFAIRS': [
            {'name': 'إدارة الطلاب', 'url': '/students/', 'icon': 'fas fa-user-graduate'},
            {'name': 'سجلات الطلاب', 'url': '#', 'icon': 'fas fa-file-alt'},
        ],
    }
    return actions.get(role, [])

# صفحة رفض الوصول الموحدة
def access_denied(request):
    """صفحة رفض الوصول الموحدة لكامل النظام"""
    requested_url = request.session.get('requested_url', '/')
    required_roles = request.session.get('required_roles', [])
    user_current_role = request.session.get('user_current_role')
    view_name = request.session.get('view_name', 'غير محدد')
    
    # ترجمة أسماء الأدوار
    role_names = {
        'SYSTEM_ADMIN': 'مدير النظام',
        'SCHOOL_MANAGER': 'مدير المدرسة', 
        'ACCOUNTANT': 'محاسب',
        'STUDENT_AFFAIRS': 'شؤون الطلاب',
        'BOOKS_INVENTORY': 'أمين مخزن الكتب',
        'UNIFORMS_INVENTORY': 'أمين مخزن الملابس',
    }
    
    required_roles_display = [role_names.get(role, role) for role in required_roles]
    user_current_role_display = role_names.get(user_current_role, 'غير محدد')
    
    # تحديد نوع القسم المطلوب
    section_info = get_section_info(view_name, requested_url)
    
    # مسح البيانات من الجلسة
    for key in ['requested_url', 'required_roles', 'user_current_role', 'view_name']:
        request.session.pop(key, None)
    
    context = {
        'requested_url': requested_url,
        'required_roles': required_roles_display,
        'user_current_role': user_current_role_display,
        'has_role': bool(user_current_role),
        'section_info': section_info,
        'view_name': view_name,
        'suggested_contacts': get_contact_suggestions(required_roles),
        'alternative_sections': get_alternative_sections(user_current_role),
    }
    
    return render(request, 'home/access_denied.html', context)

def get_section_info(view_name, url):
    """معلومات عن القسم المطلوب"""
    sections = {
        'admin_dashboard': {
            'name': 'لوحة تحكم الإدارة',
            'description': 'إدارة عامة للنظام والمستخدمين',
            'icon': 'fas fa-user-shield',
            'color': 'danger'
        },
        'manager_dashboard': {
            'name': 'لوحة تحكم المدير',
            'description': 'إدارة شؤون المدرسة والإشراف العام',
            'icon': 'fas fa-school',
            'color': 'primary'
        },
        'books_inventory_dashboard': {
            'name': 'مخزن الكتب',
            'description': 'إدارة مخزون الكتب والمواد التعليمية',
            'icon': 'fas fa-book',
            'color': 'success'
        },
        'uniforms_inventory_dashboard': {
            'name': 'مخزن الملابس',
            'description': 'إدارة الزي المدرسي والملابس',
            'icon': 'fas fa-tshirt',
            'color': 'info'
        }
    }
    
    # التحقق من URL إذا لم يوجد view_name
    if '/treasury/' in url:
        return {
            'name': 'نظام الخزينة',
            'description': 'إدارة العمليات المالية والخزائن',
            'icon': 'fas fa-coins',
            'color': 'warning'
        }
    elif '/payments/' in url:
        return {
            'name': 'نظام المدفوعات',
            'description': 'إدارة مدفوعات الطلاب والرسوم',
            'icon': 'fas fa-money-bill',
            'color': 'success'
        }
    elif '/students/' in url:
        return {
            'name': 'شؤون الطلاب',
            'description': 'إدارة بيانات وسجلات الطلاب',
            'icon': 'fas fa-user-graduate',
            'color': 'info'
        }
    
    return sections.get(view_name, {
        'name': 'قسم محمي',
        'description': 'هذا القسم يتطلب صلاحيات خاصة',
        'icon': 'fas fa-shield-alt',
        'color': 'secondary'
    })

def get_contact_suggestions(required_roles):
    """اقتراحات للتواصل حسب الأدوار المطلوبة"""
    contacts = []
    
    if 'SYSTEM_ADMIN' in required_roles:
        contacts.append({
            'title': 'مدير النظام',
            'description': 'للحصول على صلاحيات إدارية عليا',
            'icon': 'fas fa-user-shield',
            'action': 'تواصل مع مسؤول تقنية المعلومات'
        })
    
    if 'SCHOOL_MANAGER' in required_roles:
        contacts.append({
            'title': 'إدارة المدرسة',
            'description': 'للحصول على صلاحيات إدارة المدرسة',
            'icon': 'fas fa-school',
            'action': 'راجع مكتب مدير المدرسة'
        })
    
    return contacts

def get_alternative_sections(user_role):
    """أقسام بديلة يمكن للمستخدم الوصول إليها"""
    alternatives = {
        'ACCOUNTANT': [
            {'name': 'نظام المدفوعات', 'url': '/payments/', 'icon': 'fas fa-money-bill'},
            {'name': 'التقارير المالية', 'url': '#', 'icon': 'fas fa-chart-line'}
        ],
        'STUDENT_AFFAIRS': [
            {'name': 'إدارة الطلاب', 'url': '/students/', 'icon': 'fas fa-user-graduate'},
            {'name': 'كشوف الدرجات', 'url': '#', 'icon': 'fas fa-graduation-cap'}
        ],
        'BOOKS_INVENTORY': [
            {'name': 'مخزن الكتب', 'url': '/books/', 'icon': 'fas fa-book'},
            {'name': 'طلبات الكتب', 'url': '#', 'icon': 'fas fa-shopping-cart'}
        ],
        'UNIFORMS_INVENTORY': [
            {'name': 'مخزن الملابس', 'url': '/uniforms/', 'icon': 'fas fa-tshirt'},
            {'name': 'طلبات الزي', 'url': '#', 'icon': 'fas fa-shopping-bag'}
        ]
    }
    
    return alternatives.get(user_role, [
        {'name': 'الصفحة الرئيسية', 'url': '/', 'icon': 'fas fa-home'}
    ])
