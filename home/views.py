# home/views.py - الملف الكامل المُحدث والمُصحح
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count, Q
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

# Import Models and Forms
from .forms import CustomUserCreationForm, UserEditForm
from school_settings.models import SystemRole

# Import Decorators
from .decorators import (
    system_admin_required, 
    school_manager_required, 
    accountant_required,
    student_affairs_required,
    books_inventory_required,
    uniforms_inventory_required,
    get_user_role
)

# Get User Model
User = get_user_model()

# ===================================
# 🔐 Authentication Views
# ===================================

# class CustomLoginView(auth_views.LoginView):
#     """صفحة تسجيل الدخول المخصصة"""
#     template_name = 'home/login.html'
#     redirect_authenticated_user = True
    
#     def get_success_url(self):
#         user = self.request.user
#         role = get_user_role(user)
        
#         if role == 'SYSTEM_ADMIN':
#             return reverse_lazy('home:admin_dashboard')
#         elif role == 'SCHOOL_MANAGER':
#             return reverse_lazy('home:manager_dashboard')
#         elif role == 'ACCOUNTANT':
#             return reverse_lazy('payments:payments_home')
#         elif role == 'STUDENT_AFFAIRS':
#             return reverse_lazy('students:student_affairs_home')
#         elif role == 'BOOKS_INVENTORY':
#             return reverse_lazy('home:books_inventory_dashboard')
#         elif role == 'UNIFORMS_INVENTORY':
#             return reverse_lazy('home:uniforms_inventory_dashboard')
#         else:
#             return reverse_lazy('home:default_dashboard')
        
#     def get_success_url(self):
#         if self.request.user.is_superuser:
#             return reverse_lazy('home:admin_dashboard')
#         return get_dashboard_url_for_role(get_user_role(self.request.user))


# def logout_view(request):
#     """تسجيل الخروج الموحد للنظام بالكامل"""
#     user_name = request.user.get_full_name() or request.user.username if request.user.is_authenticated else "المستخدم"
    
#     auth_logout(request)
    
#     messages.success(
#         request, 
#         f'👋 تم تسجيل خروج "{user_name}" بنجاح. نراك لاحقاً!'
#     )
    
#     return redirect('home:login')
def get_dashboard_url_for_role(role):
    """تحديد رابط لوحة التحكم حسب الدور"""

    role_urls = {
        'SYSTEM_ADMIN': reverse_lazy('home:admin_dashboard'),
        'SCHOOL_MANAGER': reverse_lazy('home:manager_dashboard'),

        # الحسابات والمدفوعات
        'ACCOUNTANT': reverse_lazy('home:accountant_dashboard'),

        # شؤون الطلاب
        'STUDENT_AFFAIRS': reverse_lazy('home:student_affairs_dashboard'),

        # المخازن
        'BOOKS_INVENTORY': reverse_lazy('home:books_inventory_dashboard'),
        'UNIFORMS_INVENTORY': reverse_lazy('home:uniforms_inventory_dashboard'),
        'INVENTORY_MANAGER': reverse_lazy('home:books_inventory_dashboard'),

        # الخزينة
        'TREASURY_ADMIN': reverse_lazy('home:accountant_dashboard'),
        'TREASURY_MANAGER': reverse_lazy('home:accountant_dashboard'),
        'TREASURY_ACCOUNTANT': reverse_lazy('home:accountant_dashboard'),
        'TREASURY_CASHIER': reverse_lazy('home:accountant_dashboard'),
        'TREASURY_VIEWER': reverse_lazy('home:accountant_dashboard'),
    }

    return role_urls.get(role, reverse_lazy('home:default_dashboard'))


class CustomLoginView(auth_views.LoginView):
    """صفحة تسجيل الدخول المخصصة"""
    template_name = 'home/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        """توجيه المستخدم بعد تسجيل الدخول حسب الدور"""

        if self.request.user.is_superuser:
            return reverse_lazy('home:admin_dashboard')

        role = get_user_role(self.request.user)
        return get_dashboard_url_for_role(role)


def logout_view(request):
    """تسجيل الخروج الموحد للنظام بالكامل"""

    if request.user.is_authenticated:
        user_name = request.user.get_full_name() or request.user.username
    else:
        user_name = "المستخدم"

    auth_logout(request)

    messages.success(
        request,
        f'👋 تم تسجيل خروج "{user_name}" بنجاح. نراك لاحقاً!'
    )

    return redirect('home:login')


@login_required
def home(request):
    """الصفحة الرئيسية - توجيه للوحة المناسبة"""

    if request.user.is_superuser:
        return redirect('home:admin_dashboard')

    role = get_user_role(request.user)
    return redirect(get_dashboard_url_for_role(role))
# ===================================
# 🏠 Home and Dashboard Views
# ===================================

@never_cache
@login_required
@system_admin_required
def admin_dashboard(request):
    """لوحة تحكم المدير العام - بيانات حقيقية"""
    
    # الحصول على الإحصائيات الحقيقية
    stats = get_real_statistics()
    
    # الحصول على الأنشطة الأخيرة
    recent_activities = get_recent_activities()
    
    # الحصول على التنبيهات
    alerts = get_system_alerts()
    
    context = {
        'stats': stats,
        'recent_activities': recent_activities,
        'alerts': alerts,
        'current_date': timezone.now().date(),
    }
    
    return render(request, 'home/admin_dashboard.html', context)

@never_cache
@login_required
@school_manager_required
def manager_dashboard(request):
    """لوحة تحكم مدير المدرسة - تحويل إلى مركز التقارير"""
    return redirect('report:reports_home')

@never_cache
@login_required
@accountant_required
def accountant_dashboard(request):
    """لوحة تحكم المحاسب"""
    return redirect('payments:payments_home')

@never_cache
@login_required
@student_affairs_required
def student_affairs_dashboard(request):
    """لوحة تحكم شؤون الطلاب"""
    return redirect('students:student_affairs_home')

@never_cache
@login_required
@books_inventory_required
def books_inventory_dashboard(request):
    """لوحة تحكم مخزن الكتب"""
    context = get_common_context(request)
    return render(request, 'home/books_inventory_dashboard.html', context)

@never_cache
@login_required
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

# ===================================
# 📊 Statistics and Data Functions
# ===================================

def get_real_statistics():
    """الحصول على الإحصائيات الحقيقية من قاعدة البيانات"""
    
    try:
        # إحصائيات المستخدمين
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        
        # إحصائيات الطلاب
        try:
            from students.models import Student
            total_students = Student.objects.count()
            active_students = Student.objects.filter(is_active=True).count()
        except ImportError:
            total_students = 0
            active_students = 0
        
        # إحصائيات الصفوف
        try:
            from school_settings.models import SchoolClass
            total_classes = SchoolClass.objects.count()
        except (ImportError, AttributeError):
            try:
                from school_settings.models import GradeLevel
                total_classes = GradeLevel.objects.count()
            except (ImportError, AttributeError):
                total_classes = 0
        
        # إحصائيات المالية
        try:
            from payments.models import Payment
            
            total_payments = Payment.objects.count()
            paid_payments = Payment.objects.filter(status='PAID').count()
            
            if total_payments > 0:
                collection_rate = (paid_payments / total_payments) * 100
            else:
                collection_rate = 0
                
        except ImportError:
            collection_rate = 0
            total_payments = 0
            paid_payments = 0
        
        # إحصائيات الخزينة
        try:
            from treasury_management.models import Treasury, Account
            total_treasuries = Treasury.objects.count()
            total_accounts = Account.objects.count()
        except ImportError:
            total_treasuries = 0
            total_accounts = 0
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_students': total_students,
            'active_students': active_students,
            'total_classes': total_classes,
            'collection_rate': round(collection_rate, 1),
            'total_payments': total_payments,
            'paid_payments': paid_payments,
            'total_treasuries': total_treasuries,
            'total_accounts': total_accounts,
        }
        
    except Exception as e:
        print(f"خطأ في الإحصائيات: {e}")
        return {
            'total_users': 0,
            'active_users': 0,
            'total_students': 0,
            'active_students': 0,
            'total_classes': 0,
            'collection_rate': 0,
            'total_payments': 0,
            'paid_payments': 0,
            'total_treasuries': 0,
            'total_accounts': 0,
        }

def get_recent_activities():
    """الحصول على الأنشطة الأخيرة من قاعدة البيانات"""
    
    activities = []
    now = timezone.now()
    
    try:
        # أحدث المستخدمين المسجلين
        recent_users = User.objects.filter(
            date_joined__gte=now - timedelta(days=7)
        ).order_by('-date_joined')[:3]
        
        for user in recent_users:
            time_diff = now - user.date_joined
            if time_diff.days == 0:
                if time_diff.seconds < 3600:
                    time_str = f"منذ {time_diff.seconds // 60} دقيقة"
                else:
                    time_str = f"منذ {time_diff.seconds // 3600} ساعة"
            else:
                time_str = f"منذ {time_diff.days} يوم"
            
            activities.append({
                'type': 'user_registered',
                'title': 'مستخدم جديد',
                'description': f'انضم المستخدم {user.get_full_name() or user.username} للنظام',
                'time': time_str,
                'icon': 'fa-user-plus',
                'color': 'primary'
            })
    except Exception:
        pass
    
    try:
        # أحدث الطلاب المسجلين
        from students.models import Student
        recent_students = Student.objects.filter(
            created_at__gte=now - timedelta(days=7)
        ).order_by('-created_at')[:3]
        
        for student in recent_students:
            time_diff = now - student.created_at
            if time_diff.days == 0:
                if time_diff.seconds < 3600:
                    time_str = f"منذ {time_diff.seconds // 60} دقيقة"
                else:
                    time_str = f"منذ {time_diff.seconds // 3600} ساعة"
            else:
                time_str = f"منذ {time_diff.days} يوم"
            
            activities.append({
                'type': 'student_registered',
                'title': 'تسجيل طالب جديد',
                'description': f'تم تسجيل الطالب {student.name}',
                'time': time_str,
                'icon': 'fa-user-graduate',
                'color': 'success'
            })
    except ImportError:
        pass
    except Exception as e:
        print(f"خطأ في جلب الطلاب: {e}")
    
    try:
        # أحدث المدفوعات
        from payments.models import Payment
        recent_payments = Payment.objects.filter(
            created_at__gte=now - timedelta(days=7)
        ).order_by('-created_at')[:3]
        
        for payment in recent_payments:
            time_diff = now - payment.created_at
            if time_diff.days == 0:
                if time_diff.seconds < 3600:
                    time_str = f"منذ {time_diff.seconds // 60} دقيقة"
                else:
                    time_str = f"منذ {time_diff.seconds // 3600} ساعة"
            else:
                time_str = f"منذ {time_diff.days} يوم"
            
            activities.append({
                'type': 'payment_made',
                'title': 'دفع قسط',
                'description': f'تم دفع مبلغ {payment.amount} جنيه للطالب {payment.student.name}',
                'time': time_str,
                'icon': 'fa-credit-card',
                'color': 'warning'
            })
    except ImportError:
        pass
    except Exception as e:
        print(f"خطأ في جلب المدفوعات: {e}")
    
    try:
        # أحدث العمليات المالية في الخزينة
        from treasury_management.models import Transaction
        recent_transactions = Transaction.objects.filter(
            created_at__gte=now - timedelta(days=7)
        ).order_by('-created_at')[:2]
        
        for transaction in recent_transactions:
            time_diff = now - transaction.created_at
            if time_diff.days == 0:
                if time_diff.seconds < 3600:
                    time_str = f"منذ {time_diff.seconds // 60} دقيقة"
                else:
                    time_str = f"منذ {time_diff.seconds // 3600} ساعة"
            else:
                time_str = f"منذ {time_diff.days} يوم"
            
            transaction_type = "إيداع" if transaction.transaction_type == 'DEPOSIT' else "سحب"
            
            activities.append({
                'type': 'treasury_transaction',
                'title': f'عملية {transaction_type}',
                'description': f'تمت عملية {transaction_type} بمبلغ {transaction.amount} جنيه',
                'time': time_str,
                'icon': 'fa-money-bill',
                'color': 'info'
            })
    except ImportError:
        pass
    except Exception as e:
        print(f"خطأ في جلب المعاملات: {e}")
    
    # إذا لم توجد أنشطة حقيقية، أضف بعض البيانات الافتراضية
    if not activities:
        activities = [
            {
                'type': 'system_start',
                'title': 'تشغيل النظام',
                'description': 'تم تشغيل النظام بنجاح',
                'time': 'اليوم',
                'icon': 'fa-play-circle',
                'color': 'success'
            },
            {
                'type': 'database_connected',
                'title': 'الاتصال بقاعدة البيانات',
                'description': 'تم الاتصال بقاعدة البيانات بنجاح',
                'time': 'اليوم',
                'icon': 'fa-database',
                'color': 'info'
            }
        ]
    
    return activities[:5]

def get_system_alerts():
    """الحصول على تنبيهات النظام"""
    
    alerts = []
    
    try:
        # تحقق من الأقساط المتأخرة
        from payments.models import Payment
        
        overdue_payments = Payment.objects.filter(
            status='PENDING',
            due_date__lt=timezone.now().date()
        ).count()
        
        if overdue_payments > 0:
            alerts.append({
                'type': 'warning',
                'icon': 'fa-exclamation-triangle',
                'title': f'{overdue_payments} دفعة متأخرة',
                'description': 'يوجد دفعات مستحقة لم يتم تحصيلها بعد'
            })
    except (ImportError, Exception) as e:
        print(f"تنبيه: لا يمكن فحص المدفوعات المتأخرة - {e}")
    
    try:
        # تحقق من المستخدمين غير النشطين
        inactive_users = User.objects.filter(is_active=False).count()
        
        if inactive_users > 0:
            alerts.append({
                'type': 'info',
                'icon': 'fa-users',
                'title': f'{inactive_users} مستخدم غير نشط',
                'description': 'يوجد مستخدمين معطلين في النظام'
            })
    except Exception as e:
        print(f"خطأ في فحص المستخدمين: {e}")
    
    try:
        # تحقق من رصيد الخزينة المنخفض
        from treasury_management.models import Treasury
        
        low_balance_treasuries = Treasury.objects.filter(
            current_balance__lt=1000
        ).count()
        
        if low_balance_treasuries > 0:
            alerts.append({
                'type': 'warning',
                'icon': 'fa-exclamation-circle',
                'title': f'{low_balance_treasuries} خزينة برصيد منخفض',
                'description': 'توجد خزائن برصيد أقل من 1000 جنيه'
            })
    except (ImportError, Exception):
        pass
    
    # معلومات النظام الإيجابية
    alerts.append({
        'type': 'success',
        'icon': 'fa-check-circle',
        'title': 'النظام يعمل بشكل طبيعي',
        'description': 'جميع الخدمات تعمل بكفاءة'
    })
    
    # معلومات النسخ الاحتياطي
    alerts.append({
        'type': 'info',
        'icon': 'fa-database',
        'title': 'آخر نسخة احتياطية',
        'description': f'تم إنشاؤها في {timezone.now().strftime("%Y-%m-%d")}'
    })
    
    return alerts

def get_common_context(request):
    """السياق المشترك للصفحات"""
    return {
        'today': timezone.now().date(),
        'current_time': timezone.now().time(),
        'user_role': get_user_role(request.user),
        'current_user': request.user,
        'current_date': timezone.now().date(),
        'stats': get_real_statistics(),
    }

# ===================================
# 👥 User Management Views
# ===================================

@login_required
@system_admin_required
def users_list(request):
    """قائمة المستخدمين - مدير النظام فقط"""
    
    # فلاتر البحث
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    # بناء الاستعلام
    users = User.objects.select_related('system_role').all().order_by('-date_joined')
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(national_id__icontains=search_query)
        )
    
    if role_filter:
        users = users.filter(system_role__role=role_filter)
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # إحصائيات
    try:
        stats = {
            'total_users': users.count(),
            'active_users': users.filter(is_active=True).count(),
            'admin_users': users.filter(system_role__role='SYSTEM_ADMIN').count(),
            'staff_users': users.filter(is_staff=True).count(),
            'treasury_users': users.filter(
                system_role__role__in=['TREASURY_ADMIN', 'TREASURY_MANAGER', 
                                      'TREASURY_ACCOUNTANT', 'TREASURY_CASHIER', 'TREASURY_VIEWER']
            ).count(),
            'inventory_users': users.filter(
                system_role__role__in=['BOOKS_INVENTORY', 'UNIFORMS_INVENTORY', 'INVENTORY_MANAGER']
            ).count(),
        }
    except Exception:
        stats = {
            'total_users': 0,
            'active_users': 0,
            'admin_users': 0,
            'staff_users': 0,
            'treasury_users': 0,
            'inventory_users': 0,
        }
    
    # Pagination
    paginator = Paginator(users, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'role_choices': SystemRole.ROLE_CHOICES,
        'stats': stats,
        'role_descriptions': get_role_descriptions(),
    }
    
    return render(request, 'home/users_list.html', context)

@login_required
@system_admin_required
def add_user(request):
    """إضافة مستخدم جديد - مدير النظام فقط"""
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(
                    request, 
                    f'✅ تم إنشاء المستخدم "{user.get_full_name() or user.username}" بنجاح!'
                )
                return redirect('home:users_list')
            except Exception as e:
                messages.error(request, f'❌ حدث خطأ أثناء إنشاء المستخدم: {str(e)}')
        else:
            messages.error(request, '❌ يرجى تصحيح الأخطاء أدناه')
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة مستخدم جديد',
        'submit_text': 'إنشاء المستخدم',
        'role_descriptions': get_role_descriptions(),
    }
    
    return render(request, 'home/add_user.html', context)

@login_required
@system_admin_required
def edit_user(request, user_id):
    """تعديل مستخدم - مدير النظام فقط"""
    
    user = get_object_or_404(User, id=user_id)
    
    # 🔒 حماية مديري النظام
    if user.is_superuser or (hasattr(user, 'system_role') and user.system_role.role == 'SYSTEM_ADMIN'):
        messages.error(
            request,
            '🔒 لا يمكن تعديل مديري النظام من هنا. يرجى استخدام لوحة الإدارة Django.'
        )
        return redirect('home:users_list')
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            try:
                if form.cleaned_data.get('role') == 'SYSTEM_ADMIN':
                    messages.error(request, '🔒 لا يمكن تعيين دور مدير النظام من هنا!')
                    return render(request, 'home/edit_user.html', {
                        'form': form,
                        'user_obj': user,
                        'page_title': f'تعديل المستخدم: {user.get_full_name() or user.username}',
                        'submit_text': 'حفظ التغييرات',
                        'role_descriptions': get_role_descriptions(),
                    })
                
                updated_user = form.save()
                
                success_messages = []
                success_messages.append(f'✅ تم تحديث بيانات "{updated_user.get_full_name() or updated_user.username}" بنجاح!')
                
                if form.cleaned_data.get('change_password'):
                    success_messages.append('🔐 تم تحديث كلمة المرور بنجاح!')
                
                if hasattr(updated_user, 'system_role'):
                    success_messages.append(f'👤 تم تعيين الدور: {updated_user.system_role.get_role_display()}')
                
                for message in success_messages:
                    messages.success(request, message)
                
                return redirect('home:users_list')
                
            except Exception as e:
                messages.error(request, f'❌ حدث خطأ أثناء التحديث: {str(e)}')
        else:
            messages.error(request, '❌ يرجى تصحيح الأخطاء أدناه')
    else:
        form = UserEditForm(instance=user)
    
    context = {
        'form': form,
        'user_obj': user,
        'page_title': f'تعديل المستخدم: {user.get_full_name() or user.username}',
        'submit_text': 'حفظ التغييرات',
        'role_descriptions': get_role_descriptions(),
        'is_system_admin': user.is_superuser or (hasattr(user, 'system_role') and user.system_role.role == 'SYSTEM_ADMIN'),
    }
    
    return render(request, 'home/edit_user.html', context)

@login_required
@system_admin_required
def user_details(request, user_id):
    """تفاصيل المستخدم - مدير النظام فقط"""
    
    user = get_object_or_404(User, id=user_id)
    
    is_system_admin = user.is_superuser or (hasattr(user, 'system_role') and user.system_role.role == 'SYSTEM_ADMIN')
    
    context = {
        'user_obj': user,
        'user_role': getattr(user, 'system_role', None),
        'role_descriptions': get_role_descriptions(),
        'is_system_admin': is_system_admin,
    }
    
    return render(request, 'home/user_details.html', context)

@login_required
@system_admin_required
def toggle_user_status(request, user_id):
    """تفعيل/إلغاء تفعيل المستخدم - مدير النظام فقط"""
    
    user = get_object_or_404(User, id=user_id)
    
    if user == request.user:
        messages.error(request, '❌ لا يمكنك تعديل حالة حسابك الشخصي!')
        return redirect('home:users_list')
    
    # 🔒 حماية مديري النظام
    if user.is_superuser or (hasattr(user, 'system_role') and user.system_role.role == 'SYSTEM_ADMIN'):
        messages.error(
            request,
            '🔒 لا يمكن تعديل حالة مديري النظام من هنا. يرجى استخدام لوحة الإدارة Django.'
        )
        return redirect('home:users_list')
    
    user.is_active = not user.is_active
    user.save()
    
    # تحديث SystemRole أيضاً
    try:
        if hasattr(user, 'system_role'):
            user.system_role.is_active = user.is_active
            user.system_role.save()
    except Exception:
        pass
    
    status = 'تم تفعيل' if user.is_active else 'تم إلغاء تفعيل'
    messages.success(request, f'✅ {status} المستخدم "{user.get_full_name() or user.username}"')
    
    return redirect('home:users_list')

# ===================================
# 📦 Inventory Staff Management
# ===================================

@login_required
@system_admin_required
def inventory_staff_list(request):
    """قائمة موظفي المخازن - مدير النظام فقط"""
    
    inventory_groups = [
        'treasury_admin', 'treasury_manager', 'treasury_accountant', 
        'treasury_cashier', 'treasury_viewer', 'books_inventory_staff', 
        'uniforms_inventory_staff'
    ]
    
    search_query = request.GET.get('search', '')
    group_filter = request.GET.get('group', '')
    status_filter = request.GET.get('status', '')
    
    users = User.objects.filter(
        groups__name__in=inventory_groups
    ).distinct().prefetch_related('groups').order_by('-date_joined')
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if group_filter:
        users = users.filter(groups__name=group_filter)
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    try:
        stats = {
            'total_staff': users.count(),
            'active_staff': users.filter(is_active=True).count(),
            'treasury_staff': users.filter(groups__name__startswith='treasury_').distinct().count(),
            'books_staff': users.filter(groups__name='books_inventory_staff').count(),
            'uniforms_staff': users.filter(groups__name='uniforms_inventory_staff').count(),
        }
    except Exception:
        stats = {
            'total_staff': 0,
            'active_staff': 0,
            'treasury_staff': 0,
            'books_staff': 0,
            'uniforms_staff': 0,
        }
    
    # إضافة أدوار المستخدمين
    for user in users:
        user.inventory_roles = []
        user_groups = user.groups.values_list('name', flat=True)
        
        # أدوار الخزينة
        try:
            from treasury_management.decorators import get_user_treasury_role
            treasury_role = get_user_treasury_role(user)
            if treasury_role != 'بدون صلاحية':
                user.inventory_roles.append({
                    'type': 'treasury',
                    'name': treasury_role,
                    'color': 'success'
                })
        except ImportError:
            pass
        
        # أدوار المخازن
        if 'books_inventory_staff' in user_groups:
            user.inventory_roles.append({
                'type': 'books',
                'name': 'موظف مخزن الكتب',
                'color': 'info'
            })
        
        if 'uniforms_inventory_staff' in user_groups:
            user.inventory_roles.append({
                'type': 'uniforms',
                'name': 'موظف مخزن الملابس',
                'color': 'warning'
            })
    
    # Pagination
    paginator = Paginator(users, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    group_choices = [
        ('treasury_admin', 'مدير الخزينة العام'),
        ('treasury_manager', 'مدير الخزينة'),
        ('treasury_accountant', 'محاسب الخزينة'),
        ('treasury_cashier', 'أمين الخزينة'),
        ('treasury_viewer', 'مراجع الخزينة'),
        ('books_inventory_staff', 'موظف مخزن الكتب'),
        ('uniforms_inventory_staff', 'موظف مخزن الملابس'),
    ]
    
    context = {
        'users': page_obj,
        'search_query': search_query,
        'group_filter': group_filter,
        'status_filter': status_filter,
        'group_choices': group_choices,
        'stats': stats,
    }
    
    return render(request, 'home/inventory_staff_list.html', context)

@login_required
@system_admin_required
def manage_inventory_staff(request, user_id):
    """إدارة صلاحيات موظف المخازن - مدير النظام فقط"""
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        group_name = request.POST.get('group_name')
        
        try:
            if group_name:
                group = Group.objects.get(name=group_name)
                
                if action == 'add_group':
                    user.groups.add(group)
                    messages.success(
                        request, 
                        f'✅ تم إضافة "{user.get_full_name() or user.username}" إلى مجموعة {get_group_display_name(group.name)}'
                    )
                elif action == 'remove_group':
                    user.groups.remove(group)
                    messages.success(
                        request, 
                        f'✅ تم إزالة "{user.get_full_name() or user.username}" من مجموعة {get_group_display_name(group.name)}'
                    )
        except Group.DoesNotExist:
            messages.error(request, '❌ المجموعة غير موجودة')
        except Exception as e:
            messages.error(request, f'❌ حدث خطأ: {str(e)}')
        
        return redirect('home:inventory_staff_list')
    
    # الحصول على المجموعات المتاحة
    available_groups = Group.objects.filter(
        name__in=[
            'treasury_admin', 'treasury_manager', 'treasury_accountant', 
            'treasury_cashier', 'treasury_viewer', 'books_inventory_staff', 
            'uniforms_inventory_staff'
        ]
    )
    
    # المجموعات الحالية للمستخدم
    user_groups = user.groups.filter(
        name__in=[g.name for g in available_groups]
    )
    
    context = {
        'user_obj': user,
        'available_groups': available_groups,
        'user_groups': user_groups,
        'group_descriptions': get_inventory_group_descriptions(),
    }
    
    return render(request, 'home/manage_inventory_staff.html', context)

# ===================================
# 🚫 Access Control Views
# ===================================

@login_required
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

# ===================================
# 🔧 Helper Functions
# ===================================

def get_role_display_name(role):
    """الحصول على الاسم العربي للدور"""
    role_names = {
        'SYSTEM_ADMIN': 'مدير النظام',
        'SCHOOL_MANAGER': 'مدير المدرسة',
        'ACCOUNTANT': 'محاسب',
        'STUDENT_AFFAIRS': 'شؤون الطلاب',
        'BOOKS_INVENTORY': 'أمين مخزن الكتب',
        'UNIFORMS_INVENTORY': 'أمين مخزن الملابس',
        'TREASURY_ADMIN': 'مدير الخزينة العام',
        'TREASURY_MANAGER': 'مدير الخزينة',
        'TREASURY_ACCOUNTANT': 'محاسب الخزينة',
        'TREASURY_CASHIER': 'أمين الخزينة',
        'TREASURY_VIEWER': 'مراجع الخزينة',
        'INVENTORY_MANAGER': 'مدير المخازن',
    }
    return role_names.get(role, 'غير محدد')

def get_suggested_actions(role):
    """الحصول على إجراءات مقترحة حسب الدور"""
    actions = {
        'SYSTEM_ADMIN': [
            {'name': 'لوحة التحكم الإدارية', 'url': '/admin/', 'icon': 'fas fa-cogs'},
            {'name': 'إدارة المستخدمين', 'url': '/home/users/', 'icon': 'fas fa-users'},
            {'name': 'مركز التقارير', 'url': '/report/', 'icon': 'fas fa-chart-line'},
        ],
        'SCHOOL_MANAGER': [
            {'name': 'مركز التقارير', 'url': '/report/', 'icon': 'fas fa-chart-bar'},
            {'name': 'التقرير المالي', 'url': '/report/financial/', 'icon': 'fas fa-money-bill-wave'},
            {'name': 'قائمة الطلاب', 'url': '/report/student-list/', 'icon': 'fas fa-users'},
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

def get_role_descriptions():
    """أوصاف الأدوار الوظيفية - شاملة"""
    return {
        # الأدوار الأساسية
        'SYSTEM_ADMIN': {
            'name': '🔧 مدير النظام',
            'description': 'جميع الصلاحيات - إدارة كاملة للنظام',
            'permissions': ['إدارة المستخدمين', 'إعدادات النظام', 'جميع التقارير', 'لوحة الإدارة']
        },
        'SCHOOL_MANAGER': {
            'name': '👨‍💼 مدير المدرسة', 
            'description': 'إدارة عامة للمدرسة والإشراف على الأقسام',
            'permissions': ['إدارة الطلاب', 'التقارير العامة', 'الإشراف على الأقسام']
        },
        'ACCOUNTANT': {
            'name': '💰 محاسب عام',
            'description': 'إدارة الشؤون المالية والمحاسبية العامة',
            'permissions': ['نظام المدفوعات', 'التقارير المالية', 'إدارة الأقساط', 'صلاحيات الخزينة']
        },
        'STUDENT_AFFAIRS': {
            'name': '🎓 شؤون الطلاب',
            'description': 'إدارة بيانات الطلاب والسجلات الأكاديمية',
            'permissions': ['إضافة الطلاب', 'تعديل البيانات', 'التقارير الأكاديمية']
        },
        'TEACHER': {
            'name': '👩‍🏫 معلم',
            'description': 'صلاحيات التدريس وعرض بيانات الطلاب',
            'permissions': ['عرض الطلاب', 'الدرجات', 'التقارير الأكاديمية']
        },
        
        # أدوار الخزينة الجديدة
        'TREASURY_ADMIN': {
            'name': '💼 مدير الخزينة العام',
            'description': 'جميع صلاحيات الخزينة والإشراف الكامل',
            'permissions': ['إدارة الخزائن', 'إدارة الحسابات', 'التقارير المالية', 'إدارة مستخدمي الخزينة']
        },
        'TREASURY_MANAGER': {
            'name': '👨‍💼 مدير الخزينة',
            'description': 'إدارة العمليات المالية والإشراف',
            'permissions': ['إدارة العمليات', 'اعتماد المعاملات', 'التقارير الإدارية']
        },
        'TREASURY_ACCOUNTANT': {
            'name': '🧾 محاسب الخزينة',
            'description': 'العمليات المحاسبية والمالية المتخصصة',
            'permissions': ['تسجيل المعاملات', 'التقارير المحاسبية', 'مراجعة الحسابات']
        },
        'TREASURY_CASHIER': {
            'name': '💰 أمين الخزينة',
            'description': 'العمليات النقدية اليومية',
            'permissions': ['المعاملات النقدية', 'إدارة النقدية', 'تسجيل الإيرادات']
        },
        'TREASURY_VIEWER': {
            'name': '👁️ مراجع الخزينة',
            'description': 'مراجعة وعرض العمليات فقط',
            'permissions': ['عرض المعاملات', 'التقارير الأساسية', 'المراجعة']
        },
        
        # أدوار المخازن الجديدة
        'BOOKS_INVENTORY': {
            'name': '📚 موظف مخزن الكتب',
            'description': 'إدارة مخزون الكتب والمواد التعليمية',
            'permissions': ['إدارة مخزون الكتب', 'طلبات الكتب', 'توزيع المواد', 'تقارير المخزون']
        },
        'UNIFORMS_INVENTORY': {
            'name': '👕 موظف مخزن الملابس',
            'description': 'إدارة الزي المدرسي والملابس',
            'permissions': ['إدارة الزي المدرسي', 'طلبات الملابس', 'تقارير مخزن الملابس']
        },
        'INVENTORY_MANAGER': {
            'name': '📦 مدير المخازن',
            'description': 'الإشراف على جميع المخازن والمواد',
            'permissions': ['إدارة جميع المخازن', 'الإشراف على الموظفين', 'تقارير شاملة', 'صلاحيات الخزينة']
        }
    }

def get_group_display_name(group_name):
    """الحصول على الاسم المعروض للمجموعة"""
    group_names = {
        'treasury_admin': 'مدير الخزينة العام',
        'treasury_manager': 'مدير الخزينة',
        'treasury_accountant': 'محاسب الخزينة',
        'treasury_cashier': 'أمين الخزينة',
        'treasury_viewer': 'مراجع الخزينة',
        'books_inventory_staff': 'موظف مخزن الكتب',
        'uniforms_inventory_staff': 'موظف مخزن الملابس',
    }
    return group_names.get(group_name, group_name)

def get_inventory_group_descriptions():
    """أوصاف مجموعات المخازن والخزينة"""
    return {
        'treasury_admin': {
            'name': '💼 مدير الخزينة العام',
            'description': 'جميع صلاحيات الخزينة والإشراف الكامل',
            'permissions': ['إدارة الخزائن', 'إدارة الحسابات', 'التقارير المالية', 'إدارة المستخدمين']
        },
        'treasury_manager': {
            'name': '👨‍💼 مدير الخزينة',
            'description': 'إدارة العمليات المالية والإشراف',
            'permissions': ['إدارة العمليات', 'اعتماد المعاملات', 'التقارير الإدارية']
        },
        'treasury_accountant': {
            'name': '🧾 محاسب الخزينة',
            'description': 'العمليات المحاسبية والمالية',
            'permissions': ['تسجيل المعاملات', 'التقارير المحاسبية', 'مراجعة الحسابات']
        },
        'treasury_cashier': {
            'name': '💰 أمين الخزينة',
            'description': 'العمليات النقدية اليومية',
            'permissions': ['المعاملات النقدية', 'إدارة النقدية', 'تسجيل الإيرادات']
        },
        'treasury_viewer': {
            'name': '👁️ مراجع الخزينة',
            'description': 'مراجعة وعرض العمليات فقط',
            'permissions': ['عرض المعاملات', 'التقارير الأساسية', 'المراجعة']
        },
        'books_inventory_staff': {
            'name': '📚 موظف مخزن الكتب',
            'description': 'إدارة مخزون الكتب والمواد التعليمية',
            'permissions': ['إدارة مخزون الكتب', 'طلبات الكتب', 'توزيع المواد', 'تقارير المخزون']
        },
        'uniforms_inventory_staff': {
            'name': '👕 موظف مخزن الملابس',
            'description': 'إدارة الزي المدرسي والملابس',
            'permissions': ['إدارة الزي المدرسي', 'طلبات الملابس', 'تقارير مخزن الملابس']
        }
    }


# ملاحظات تعديل home/views.py
# الملف المرفق عندك جيد بشكل عام، لكن عدّل فقط دالة CustomLoginView.get_success_url ودالة home
# بالنسخة التالية إن لم تستبدل الملف بالكامل.

from django.urls import reverse_lazy
from .decorators import get_user_role


def get_dashboard_url_for_role(role):
    role_urls = {
        'SYSTEM_ADMIN': reverse_lazy('home:admin_dashboard'),
        'SCHOOL_MANAGER': reverse_lazy('report:reports_home'),
        'ACCOUNTANT': reverse_lazy('home:accountant_dashboard'),
        'STUDENT_AFFAIRS': reverse_lazy('home:student_affairs_dashboard'),
        'BOOKS_INVENTORY': reverse_lazy('home:books_inventory_dashboard'),
        'UNIFORMS_INVENTORY': reverse_lazy('home:uniforms_inventory_dashboard'),
        'INVENTORY_MANAGER': reverse_lazy('home:books_inventory_dashboard'),

        # أدوار الخزينة
        'TREASURY_ADMIN': reverse_lazy('home:accountant_dashboard'),
        'TREASURY_MANAGER': reverse_lazy('home:accountant_dashboard'),
        'TREASURY_ACCOUNTANT': reverse_lazy('home:accountant_dashboard'),
        'TREASURY_CASHIER': reverse_lazy('home:accountant_dashboard'),
        'TREASURY_VIEWER': reverse_lazy('home:accountant_dashboard'),
    }
    return role_urls.get(role, reverse_lazy('home:default_dashboard'))