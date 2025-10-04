# payments/views.py - محسن ومنظم مع الصلاحيات
import decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
from django.conf import settings
from django.db.models import Q, Sum, Count, Avg, Min, Max  # ← إضافة Min, Max
from django.db.models.functions import Extract  # ← التصحيح هنا
from decimal import Decimal, InvalidOperation
import json
from django.db.models.functions import Cast, Extract, TruncDay, TruncMonth, TruncWeek
from datetime import date, timedelta, datetime
from django.views.decorators.http import require_GET, require_POST, require_http_methods



# ===================================
# 📦 الاستيراد
# ===================================

# النماذج المحلية
from .models import *

# النماذج الخارجية
from students.models import Student

# الصلاحيات المخصصة
from .decorators import (
    payments_basic_access,
    payments_full_access,
    payments_manager_access,
    payments_admin_access,
    payments_sensitive_operation,
    payments_financial_reports
)

# النماذج (إذا كانت موجودة)
try:
    from .forms import TuitionForm, PaymentRecordForm
except ImportError:
    from django import forms
    
    class TuitionForm(forms.ModelForm):
        class Meta:
            model = Tuition
            fields = ['installment_number', 'amount_tuition', 'amount_paid', 'payment_method', 'notes']
            widgets = {
                'amount_tuition': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
                'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
                'payment_method': forms.Select(attrs={'class': 'form-select'}),
                'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            }

# ===================================
# 🔧 الدوال المساعدة
# ===================================

# في payments/views.py - إضافة دالة آمنة

def get_user_role(user):
    """الحصول على دور المستخدم بشكل آمن"""
    try:
        # محاولة الحصول على الدور من school_settings
        if hasattr(user, 'system_role'):
            return user.system_role.role
        
        # بديل آمن
        if user.is_superuser:
            return 'SYSTEM_ADMIN'
        elif user.is_staff:
            return 'ACCOUNTANT'
        else:
            return 'TEACHER'
            
    except Exception as e:
        print(f"خطأ في الحصول على دور المستخدم: {e}")
        return 'TEACHER'  # افتراضي آمن


def get_payment_permissions(user):
    """الحصول على صلاحيات المدفوعات"""
    user_role = get_user_role(user)
    
    permissions = {
        'can_add': True,
        'can_edit': True,
        'can_delete': False,
        'can_reports': True,
        'can_settings': False,
        'can_discounts': False,
        'can_advanced_reports': True,
        'is_accountant_only': False
    }
    
    if user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
        permissions.update({
            'can_delete': True,
            'can_settings': True,
            'can_discounts': True,
        })
    elif user_role == 'ACCOUNTANT':
        permissions.update({
            'can_delete': False,
            'can_settings': False,
            'can_discounts': True,
            'is_accountant_only': True
        })
    
    return permissions


def calculate_payment_stats():
    """حساب إحصائيات المدفوعات"""
    try:
        today = timezone.now().date()
        
        stats = {
            # إحصائيات اليوم
            'today_payments_count': Tuition.objects.filter(
                payment_date__date=today,
                payment_status='PAID'
            ).count(),
            
            'today_amount': Tuition.objects.filter(
                payment_date__date=today,
                payment_status='PAID'
            ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0'),
            
            # إحصائيات عامة
            'total_overdue': Tuition.objects.filter(payment_status='OVERDUE').count(),
            'total_pending': Tuition.objects.filter(payment_status='PENDING').count(),
            'total_paid': Tuition.objects.filter(payment_status='PAID').count(),
            
            # إحصائيات إضافية
            'total_students_with_payments': Tuition.objects.values('student').distinct().count(),
        }
        
        return stats
    except Exception as e:
        print(f"خطأ في حساب الإحصائيات: {e}")
        return {
            'today_payments_count': 0,
            'today_amount': Decimal('0'),
            'total_overdue': 0,
            'total_pending': 0,
            'total_paid': 0,
            'total_students_with_payments': 0,
        }

# ===================================
# 🏠 الصفحات الرئيسية
# ===================================

@never_cache
@payments_basic_access
def payments_home(request):
    """لوحة تحكم المدفوعات مع الإحصائيات"""
    user_role = get_user_role(request.user)
    permissions = get_payment_permissions(request.user)
    stats = calculate_payment_stats()
    
    # الدفعات الحديثة
    try:
        recent_payments_list = Tuition.objects.filter(
            payment_status='PAID'
        ).select_related('student').order_by('-payment_date')
        
        # Pagination للدفعات الحديثة
        paginator = Paginator(recent_payments_list, 10)
        page_number = request.GET.get('page')
        
        try:
            recent_payments = paginator.page(page_number)
        except PageNotAnInteger:
            recent_payments = paginator.page(1)
        except EmptyPage:
            recent_payments = paginator.page(paginator.num_pages)
            
    except Exception as e:
        print(f"خطأ في جلب الدفعات الحديثة: {e}")
        recent_payments = []
    
    # المتأخرات (للمحاسب والإدارة فقط)
    overdue_payments = []
    if permissions['can_reports']:
        try:
            overdue_payments = Tuition.objects.filter(
                payment_status='OVERDUE'
            ).select_related('student').order_by('due_date')[:10]
        except Exception as e:
            print(f"خطأ في جلب المتأخرات: {e}")
    
    # إحصائيات طرق الدفع
    payment_methods_stats = []
    if permissions['can_reports']:
        try:
            payment_methods_stats = Tuition.objects.filter(
                payment_status='PAID',
                payment_date__date=timezone.now().date()
            ).values('payment_method').annotate(
                count=Count('id'),
                amount=Sum('amount_paid')
            ).order_by('-amount')
        except Exception as e:
            print(f"خطأ في إحصائيات طرق الدفع: {e}")
    
    context = {
        'stats': stats,
        'recent_payments': recent_payments,
        'overdue_payments': overdue_payments,
        'payment_methods_stats': payment_methods_stats,
        'permissions': permissions,
        'user_role': user_role,
        'today': timezone.now().date(),
        'page_title': 'لوحة تحكم المدفوعات'
    }
    
    return render(request, 'payments/payments_home.html', context)

# ===================================
# 💰 إدارة المدفوعات
# ===================================
# في payments/views.py - تحديث all_payments view

@never_cache
@payments_full_access
def all_payments(request):
    """صفحة جميع المدفوعات مع البحث والفلترة"""
    user_role = get_user_role(request.user)
    permissions = get_payment_permissions(request.user)
    
    # معاملات البحث والفلترة
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    payment_method_filter = request.GET.get('payment_method', '')
    payment_user_filter = request.GET.get('payment_user', '')
    
    # بناء الاستعلام
    payments = Tuition.objects.select_related('student').order_by('-payment_date')
    
    # تطبيق الفلاتر
    if search_query:
        payments = payments.filter(
            Q(student__name__icontains=search_query) |
            Q(student__national_number__icontains=search_query) |
            Q(receipt_number__icontains=search_query)
        )
    
    if status_filter:
        payments = payments.filter(payment_status=status_filter)
        
    if date_from:
        try:
            payments = payments.filter(payment_date__date__gte=date_from)
        except:
            pass
            
    if date_to:
        try:
            payments = payments.filter(payment_date__date__lte=date_to)
        except:
            pass
            
    if payment_method_filter:
        payments = payments.filter(payment_method=payment_method_filter)
        
    if payment_user_filter:
        payments = payments.filter(payment_user__icontains=payment_user_filter)
    
    # حساب الإحصائيات للنتائج المفلترة - مُصحح
    stats = {}
    payment_methods_stats = []
    user_stats = []
    
    if permissions['can_reports']:
        try:
            # الإحصائيات الأساسية
            stats = payments.aggregate(
                total_amount=Sum('amount_paid'),
                total_count=Count('id'),
                avg_payment=Avg('amount_paid')
            )
            
            # تنظيف القيم
            stats['total_amount'] = float(stats['total_amount'] or 0)
            stats['avg_payment'] = float(stats['avg_payment'] or 0)
            stats['total_count'] = stats['total_count'] or 0
            
            # إحصائيات طرق الدفع
            payment_methods_stats = list(payments.values('payment_method').annotate(
                count=Count('id'),
                amount=Sum('amount_paid')
            ).order_by('-amount'))
            
            # تحويل القيم للفلوت
            for method in payment_methods_stats:
                method['amount'] = float(method['amount'] or 0)
            
            # إحصائيات الموظفين (أفضل 5)
            user_stats = list(payments.values('payment_user').annotate(
                count=Count('id'),
                amount=Sum('amount_paid')
            ).order_by('-amount')[:5])
            
            # تحويل القيم للفلوت
            for user in user_stats:
                user['amount'] = float(user['amount'] or 0)
                
        except Exception as e:
            print(f"خطأ في حساب الإحصائيات: {e}")
            stats = {
                'total_amount': 0,
                'total_count': 0,
                'avg_payment': 0
            }
    
    # Pagination
    paginator = Paginator(payments, 25)
    page_number = request.GET.get('page')
    
    try:
        payments_page = paginator.page(page_number)
    except PageNotAnInteger:
        payments_page = paginator.page(1)
    except EmptyPage:
        payments_page = paginator.page(paginator.num_pages)
    
    # قوائم للفلاتر
    available_users = Tuition.objects.values_list('payment_user', flat=True).distinct()
    available_users = [user for user in available_users if user and user.strip()]
    
    context = {
        'payments': payments_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'payment_method_filter': payment_method_filter,
        'payment_user_filter': payment_user_filter,
        'available_users': available_users,
        
        # الإحصائيات - مُصحح
        'stats': stats,
        'payment_methods_stats': payment_methods_stats,
        'user_stats': user_stats,
        
        'permissions': permissions,
        'user_role': user_role,
        'page_title': 'جميع المدفوعات'
    }
    
    return render(request, 'payments/all_payments.html', context)

# # في payments/views.py - تحديث دالة advanced_statistics

# @never_cache
# @payments_financial_reports
# def advanced_statistics(request):
#     """الإحصائيات المتقدمة مع رسوم بيانية تفاعلية"""
#     user_role = get_user_role(request.user)
#     permissions = get_payment_permissions(request.user)
    
#     # خيارات التحليل
#     period = request.GET.get('period', 'last_month')
#     chart_type = request.GET.get('chart_type', 'line')
#     group_by = request.GET.get('group_by', 'day')
    
#     # تحديد الفترة الزمنية
#     now = timezone.now()
#     if period == 'last_month':
#         start_date = now - timedelta(days=30)
#         period_display = 'آخر 30 يوم'
#     elif period == 'last_3_months':
#         start_date = now - timedelta(days=90)
#         period_display = 'آخر 3 شهور'
#     elif period == 'last_6_months':
#         start_date = now - timedelta(days=180)
#         period_display = 'آخر 6 شهور'
#     elif period == 'last_year':
#         start_date = now - timedelta(days=365)
#         period_display = 'آخر سنة'
#     else:  # all_time
#         start_date = None
#         period_display = 'جميع الفترات'
    
#     # فلترة المدفوعات
#     payments = Tuition.objects.filter(payment_status='PAID')
#     if start_date:
#         payments = payments.filter(payment_date__gte=start_date)
    
#     # KPI الرئيسية
#     kpi = {}
#     main_chart = {}
#     payment_methods_chart = {}
#     employees_chart = {}
#     growth_chart = {}
#     weekly_pattern = [0] * 7
#     detailed_stats = []
#     insights = []
    
#     try:
#         # KPI الأساسية
#         kpi = {
#             'total_revenue': float(payments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0),
#             'total_transactions': payments.count(),
#             'avg_transaction': float(payments.aggregate(Avg('amount_paid'))['amount_paid__avg'] or 0),
#             'active_students': payments.values('student').distinct().count(),
#             'revenue_change': 15.5,  # يمكن حسابها ديناميكياً
#             'transactions_change': 8.2,
#             'avg_change': 12.1,
#             'students_change': 5.7
#         }
        
#         # بيانات الرسم البياني الرئيسي
#         if group_by == 'day':
#             daily_data = payments.extra({'date': 'date(payment_date)'}).values('date').annotate(
#                 total=Sum('amount_paid')
#             ).order_by('date')
            
#             main_chart = {
#                 'labels': [item['date'] for item in daily_data],
#                 'values': [float(item['total']) for item in daily_data]
#             }
        
#         # بيانات طرق الدفع
#         payment_methods = payments.values('payment_method').annotate(
#             total=Sum('amount_paid'),
#             count=Count('id')
#         ).order_by('-total')
        
#         method_names = {
#             'cash': 'نقدي',
#             'transfer': 'تحويل بنكي', 
#             'card': 'بطاقة ائتمان',
#             'check': 'شيك'
#         }
        
#         colors = ['#28a745', '#007bff', '#17a2b8', '#ffc107', '#dc3545']
        
#         payment_methods_data = []
#         total_amount = sum(float(m['total']) for m in payment_methods)
        
#         for i, method in enumerate(payment_methods):
#             amount = float(method['total'])
#             percentage = (amount / total_amount * 100) if total_amount > 0 else 0
            
#             payment_methods_data.append({
#                 'name': method_names.get(method['payment_method'], method['payment_method']),
#                 'amount': amount,
#                 'percentage': round(percentage, 1),
#                 'color': colors[i % len(colors)]
#             })
        
#         payment_methods_chart = {
#             'labels': [m['name'] for m in payment_methods_data],
#             'values': [m['amount'] for m in payment_methods_data],
#             'colors': [m['color'] for m in payment_methods_data]
#         }
        
#         # بيانات الموظفين
#         employees = payments.values('payment_user').annotate(
#             total=Sum('amount_paid'),
#             count=Count('id')
#         ).order_by('-total')[:10]
        
#         employees_data = []
#         for emp in employees:
#             employees_data.append({
#                 'name': emp['payment_user'] or 'غير محدد',
#                 'amount': float(emp['total']),
#                 'count': emp['count']
#             })
        
#         employees_chart = {
#             'labels': [emp['name'] for emp in employees_data],
#             'values': [emp['amount'] for emp in employees_data]
#         }
        
#         # الأنماط الأسبوعية
#         for i in range(7):  # 0 = الأحد, 6 = السبت
#             day_payments = payments.filter(payment_date__week_day=i+1)
#             day_avg = day_payments.aggregate(Avg('amount_paid'))['amount_paid__avg'] or 0
#             weekly_pattern[i] = float(day_avg)
        
#         # التحليل التفصيلي
#         months = payments.extra({'month': 'date_trunc(\'month\', payment_date)'}).values('month').annotate(
#             total=Sum('amount_paid'),
#             count=Count('id'),
#             avg=Avg('amount_paid'),
#             max=Max('amount_paid'),
#             min=Min('amount_paid')
#         ).order_by('-month')[:6]
        
#         previous_total = None
#         for month in months:
#             growth = 0
#             if previous_total:
#                 growth = ((float(month['total']) - previous_total) / previous_total * 100)
            
#             detailed_stats.append({
#                 'period_name': month['month'].strftime('%B %Y'),
#                 'period_date': month['month'].strftime('%Y-%m'),
#                 'total': float(month['total']),
#                 'count': month['count'],
#                 'average': float(month['avg']),
#                 'max': float(month['max']),
#                 'min': float(month['min']),
#                 'growth': round(growth, 1)
#             })
            
#             previous_total = float(month['total'])
        
#         # النصائح والتوصيات
#         insights = [
#             {
#                 'type': 'positive',
#                 'icon': 'trending-up',
#                 'title': 'نمو في الإيرادات',
#                 'description': f'نمو بنسبة {kpi["revenue_change"]}% مقارنة بالفترة السابقة',
#                 'action': 'استمر في الاتجاه الحالي'
#             },
#             {
#                 'type': 'warning',
#                 'icon': 'clock',
#                 'title': 'أوقات الذروة',
#                 'description': 'معظم المدفوعات تتم في منتصف الأسبوع',
#                 'action': 'فكر في تحفيزات نهاية الأسبوع'
#             },
#             {
#                 'type': 'positive',
#                 'icon': 'users',
#                 'title': 'نشاط الطلاب',
#                 'description': f'{kpi["active_students"]} طالب نشط في الدفع',
#                 'action': 'حافظ على مستوى الخدمة'
#             }
#         ]
        
#     except Exception as e:
#         print(f"خطأ في الإحصائيات المتقدمة: {e}")
#         # قيم افتراضية في حالة الخطأ
#         kpi = {
#             'total_revenue': 0,
#             'total_transactions': 0,
#             'avg_transaction': 0,
#             'active_students': 0,
#             'revenue_change': 0,
#             'transactions_change': 0,
#             'avg_change': 0,
#             'students_change': 0
#         }
    
#     context = {
#         'kpi': kpi,
#         'main_chart': main_chart,
#         'payment_methods_chart': payment_methods_chart,
#         'payment_methods_data': payment_methods_data,
#         'employees_chart': employees_chart,
#         'employees_data': employees_data,
#         'growth_chart': growth_chart,
#         'weekly_pattern': weekly_pattern,
#         'detailed_stats': detailed_stats,
#         'insights': insights,
#         'period': period,
#         'period_display': period_display,
#         'chart_type': chart_type,
#         'group_by': group_by,
#         'permissions': permissions,
#         'user_role': user_role,
#         'page_title': 'الإحصائيات المتقدمة'
#     }
    
#     return render(request, 'payments/advanced_statistics.html', context)

# في payments/views.py - إصلاح دالة advanced_statistics

@never_cache
@payments_financial_reports
def advanced_statistics(request):
    """الإحصائيات المتقدمة مع رسوم بيانية تفاعلية"""
    from django.db.models import Q, Sum, Count, Avg, Max, Min
    from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
    import json
    
    user_role = get_user_role(request.user)
    permissions = get_payment_permissions(request.user)
    
    # خيارات التحليل
    period = request.GET.get('period', 'last_month')
    chart_type = request.GET.get('chart_type', 'line')
    group_by = request.GET.get('group_by', 'day')
    
    # تحديد الفترة الزمنية
    now = timezone.now()
    if period == 'last_month':
        start_date = now - timedelta(days=30)
        period_display = 'آخر 30 يوم'
    elif period == 'last_3_months':
        start_date = now - timedelta(days=90)
        period_display = 'آخر 3 شهور'
    elif period == 'last_6_months':
        start_date = now - timedelta(days=180)
        period_display = 'آخر 6 شهور'
    elif period == 'last_year':
        start_date = now - timedelta(days=365)
        period_display = 'آخر سنة'
    else:  # all_time
        start_date = None
        period_display = 'جميع الفترات'
    
    # فلترة المدفوعات - التأكد من وجود المدفوعات
    payments = Tuition.objects.filter(payment_status='PAID').select_related('student')
    if start_date:
        payments = payments.filter(payment_date__gte=start_date)
    
    print(f"DEBUG: إجمالي المدفوعات: {payments.count()}")
    
    # متغيرات البيانات
    kpi = {}
    main_chart = {'labels': [], 'values': []}
    payment_methods_chart = {'labels': [], 'values': [], 'colors': []}
    payment_methods_data = []
    employees_chart = {'labels': [], 'values': []}
    employees_data = []
    growth_chart = {'labels': [], 'values': []}
    weekly_pattern = [0] * 7
    detailed_stats = []
    insights = []
    
    try:
        # KPI الأساسية
        total_revenue = payments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        total_transactions = payments.count()
        avg_transaction = payments.aggregate(Avg('amount_paid'))['amount_paid__avg'] or 0
        active_students = payments.values('student').distinct().count()
        
        kpi = {
            'total_revenue': float(total_revenue),
            'total_transactions': total_transactions,
            'avg_transaction': float(avg_transaction),
            'active_students': active_students,
            'revenue_change': 15.5,  # يمكن حسابها ديناميكياً
            'transactions_change': 8.2,
            'avg_change': 12.1,
            'students_change': 5.7
        }
        
        print(f"DEBUG: KPI - إجمالي الإيرادات: {kpi['total_revenue']}, المعاملات: {kpi['total_transactions']}")
        
        # بيانات الرسم البياني الرئيسي
        if group_by == 'day':
            # تجميع البيانات يومياً
            daily_data = payments.annotate(
                date=TruncDay('payment_date')
            ).values('date').annotate(
                total=Sum('amount_paid')
            ).order_by('date')
            
            main_chart['labels'] = [item['date'].strftime('%Y-%m-%d') for item in daily_data]
            main_chart['values'] = [float(item['total']) for item in daily_data]
            
        elif group_by == 'month':
            # تجميع البيانات شهرياً
            monthly_data = payments.annotate(
                month=TruncMonth('payment_date')
            ).values('month').annotate(
                total=Sum('amount_paid')
            ).order_by('month')
            
            main_chart['labels'] = [item['month'].strftime('%Y-%m') for item in monthly_data]
            main_chart['values'] = [float(item['total']) for item in monthly_data]
        
        print(f"DEBUG: الرسم الرئيسي - عدد النقاط: {len(main_chart['labels'])}")
        
        # بيانات طرق الدفع
        payment_methods = payments.values('payment_method').annotate(
            total=Sum('amount_paid'),
            count=Count('id')
        ).order_by('-total')
        
        method_names = {
            'cash': 'نقدي',
            'transfer': 'تحويل بنكي', 
            'card': 'بطاقة ائتمان',
            'check': 'شيك'
        }
        
        colors = ['#28a745', '#007bff', '#17a2b8', '#ffc107', '#dc3545']
        
        total_amount = sum(float(m['total']) for m in payment_methods)
        print(f"DEBUG: طرق الدفع - إجمالي: {total_amount}")
        
        if total_amount > 0:
            for i, method in enumerate(payment_methods):
                amount = float(method['total'])
                percentage = (amount / total_amount * 100)
                
                method_data = {
                    'name': method_names.get(method['payment_method'], method['payment_method']),
                    'amount': amount,
                    'percentage': round(percentage, 1),
                    'color': colors[i % len(colors)]
                }
                payment_methods_data.append(method_data)
            
            payment_methods_chart = {
                'labels': json.dumps([m['name'] for m in payment_methods_data]),
                'values': json.dumps([m['amount'] for m in payment_methods_data]),
                'colors': json.dumps([m['color'] for m in payment_methods_data])
            }
        
        # بيانات الموظفين
        employees = payments.values('payment_user').annotate(
            total=Sum('amount_paid'),
            count=Count('id')
        ).order_by('-total')[:10]
        
        for emp in employees:
            if emp['payment_user']:  # تجاهل القيم الفارغة
                employees_data.append({
                    'name': emp['payment_user'],
                    'amount': float(emp['total']),
                    'count': emp['count']
                })
        
        if employees_data:
            employees_chart = {
                'labels': json.dumps([emp['name'] for emp in employees_data]),
                'values': json.dumps([emp['amount'] for emp in employees_data])
            }
        
        print(f"DEBUG: الموظفين - عدد: {len(employees_data)}")
        
        # الأنماط الأسبوعية
        for i in range(7):  # 0 = الأحد, 6 = السبت
            # استخدام week_day من Django (1 = الأحد)
            day_payments = payments.filter(payment_date__week_day=i+1)
            if day_payments.exists():
                day_avg = day_payments.aggregate(Avg('amount_paid'))['amount_paid__avg'] or 0
                weekly_pattern[i] = float(day_avg)
        
        print(f"DEBUG: الأنماط الأسبوعية: {weekly_pattern}")
        
        # التحليل التفصيلي
        months = payments.annotate(
            month=TruncMonth('payment_date')
        ).values('month').annotate(
            total=Sum('amount_paid'),
            count=Count('id'),
            avg=Avg('amount_paid'),
            max=Max('amount_paid'),
            min=Min('amount_paid')
        ).order_by('-month')[:6]
        
        previous_total = None
        for month_data in months:
            if month_data['month']:  # التأكد من وجود التاريخ
                growth = 0
                if previous_total and previous_total > 0:
                    growth = ((float(month_data['total']) - previous_total) / previous_total * 100)
                
                detailed_stats.append({
                    'period_name': month_data['month'].strftime('%B %Y'),
                    'period_date': month_data['month'].strftime('%Y-%m'),
                    'total': float(month_data['total']),
                    'count': month_data['count'],
                    'average': float(month_data['avg']),
                    'max': float(month_data['max']),
                    'min': float(month_data['min']),
                    'growth': round(growth, 1)
                })
                
                previous_total = float(month_data['total'])
        
        # النصائح والتوصيات
        insights = []
        
        if kpi['total_revenue'] > 0:
            insights.append({
                'type': 'positive',
                'icon': 'trending-up',
                'title': 'أداء إيجابي',
                'description': f'تم تحصيل {kpi["total_revenue"]:,.0f} ج.م خلال الفترة المحددة',
                'action': 'استمر في الأداء الجيد'
            })
        
        if payment_methods_data:
            top_method = max(payment_methods_data, key=lambda x: x['amount'])
            insights.append({
                'type': 'info',
                'icon': 'credit-card',
                'title': 'طريقة الدفع المفضلة',
                'description': f'{top_method["name"]} هي الأكثر استخداماً بنسبة {top_method["percentage"]}%',
                'action': 'ركز على تحسين هذه الطريقة'
            })
        
        if employees_data:
            top_employee = employees_data[0]
            insights.append({
                'type': 'positive',
                'icon': 'user-tie',
                'title': 'أفضل موظف',
                'description': f'{top_employee["name"]} سجل أعلى مدفوعات: {top_employee["amount"]:,.0f} ج.م',
                'action': 'قدم له التقدير المناسب'
            })
        else:
            insights.append({
                'type': 'warning',
                'icon': 'exclamation-triangle',
                'title': 'لا توجد بيانات كافية',
                'description': 'قم بإضافة المزيد من المدفوعات للحصول على تحليل أفضل',
                'action': 'ابدأ بتسجيل المدفوعات'
            })
            
    except Exception as e:
        print(f"خطأ في الإحصائيات المتقدمة: {e}")
        import traceback
        traceback.print_exc()
        
        # قيم افتراضية في حالة الخطأ
        kpi = {
            'total_revenue': 0,
            'total_transactions': 0,
            'avg_transaction': 0,
            'active_students': 0,
            'revenue_change': 0,
            'transactions_change': 0,
            'avg_change': 0,
            'students_change': 0
        }
        
        insights = [{
            'type': 'warning',
            'icon': 'database',
            'title': 'لا توجد بيانات',
            'description': 'لا توجد مدفوعات مسجلة في النظام بعد',
            'action': 'ابدأ بتسجيل أول مدفوع'
        }]
    
    # تحويل البيانات لـ JSON آمن
    main_chart_json = {
        'labels': json.dumps(main_chart['labels']),
        'values': json.dumps(main_chart['values'])
    }
    
    weekly_pattern_json = json.dumps(weekly_pattern)
    
    context = {
        'kpi': kpi,
        'main_chart': main_chart_json,
        'payment_methods_chart': payment_methods_chart,
        'payment_methods_data': payment_methods_data,
        'employees_chart': employees_chart,
        'employees_data': employees_data,
        'growth_chart': growth_chart,
        'weekly_pattern': weekly_pattern_json,
        'detailed_stats': detailed_stats,
        'insights': insights,
        'period': period,
        'period_display': period_display,
        'chart_type': chart_type,
        'group_by': group_by,
        'permissions': permissions,
        'user_role': user_role,
        'page_title': 'الإحصائيات المتقدمة'
    }
    
    return render(request, 'payments/advanced_statistics.html', context)


@csrf_protect
@payments_basic_access
def get_payment_details_ajax(request, payment_id):
    """API للحصول على تفاصيل مدفوع محدد"""
    try:
        payment = get_object_or_404(Tuition, id=payment_id)
        
        # إعداد بيانات التفاصيل
        payment_data = {
            'id': payment.id,
            'student_name': payment.student.name,
            'student_national_number': payment.student.national_number,
            'student_grade': getattr(payment.student.grade_level, 'name', 'غير محدد') if hasattr(payment.student, 'grade_level') else 'غير محدد',
            'student_phone': getattr(payment.student, 'phone_number', 'غير محدد'),
            'installment_number': payment.installment_number,
            'receipt_number': payment.receipt_number,
            'amount_tuition': float(payment.amount_tuition),
            'amount_paid': float(payment.amount_paid),
            'remaining_amount': float(payment.remaining_amount),
            'payment_status_code': payment.payment_status,
            'payment_status_display': payment.get_payment_status_display(),
            'payment_method': payment.payment_method,
            'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
            'payment_user': payment.payment_user,
            'notes': payment.notes or '',
            'due_date': payment.due_date.isoformat() if payment.due_date else None,
        }
        
        return JsonResponse({
            'success': True,
            'payment': payment_data
        })
        
    except Exception as e:
        print(f"خطأ في جلب تفاصيل المدفوع: {e}")
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ في جلب التفاصيل'
        })

@csrf_protect
@payments_basic_access  
def validate_payment_ajax(request):
    """API للتحقق من صحة بيانات المدفوع"""
    try:
        amount_tuition = float(request.POST.get('amount_tuition', 0))
        amount_paid = float(request.POST.get('amount_paid', 0))
        installment_number = int(request.POST.get('installment_number', 0))
        
        errors = []
        
        if installment_number <= 0:
            errors.append('رقم القسط يجب أن يكون أكبر من صفر')
            
        if amount_tuition <= 0:
            errors.append('مبلغ القسط يجب أن يكون أكبر من صفر')
            
        if amount_paid < 0:
            errors.append('المبلغ المدفوع لا يمكن أن يكون سالباً')
            
        if amount_paid > amount_tuition:
            errors.append('المبلغ المدفوع لا يمكن أن يكون أكبر من المطلوب')
        
        return JsonResponse({
            'success': len(errors) == 0,
            'errors': errors,
            'remaining_amount': max(0, amount_tuition - amount_paid)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'errors': ['خطأ في التحقق من البيانات']
        })

@csrf_protect
@payments_basic_access
def calculate_student_total_ajax(request):
    """API لحساب إجمالي مدفوعات طالب"""
    try:
        student_id = request.GET.get('student_id')
        student = get_object_or_404(Student, id=student_id)
        
        payments = Tuition.objects.filter(student=student)
        total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or 0
        total_tuition = payments.aggregate(total=Sum('amount_tuition'))['total'] or 0
        total_remaining = total_tuition - total_paid
        
        return JsonResponse({
            'success': True,
            'total_paid': float(total_paid),
            'total_tuition': float(total_tuition),
            'total_remaining': float(total_remaining),
            'payments_count': payments.count()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# في payments/views.py - إضافة views للحذف والتعديل

@csrf_protect
@payments_admin_access
def delete_payment(request, pk):
    """حذف مدفوع محدد"""
    if request.method == 'POST':
        try:
            payment = get_object_or_404(Tuition, id=pk)
            student_name = payment.student.name
            installment_number = payment.installment_number
            
            # حذف المدفوع
            payment.delete()
            
            messages.success(request, f'تم حذف القسط #{installment_number} للطالب {student_name} بنجاح')
            
        except Exception as e:
            messages.error(request, f'خطأ في الحذف: {str(e)}')
    
    return redirect('payments:all_payments')

@never_cache
@payments_manager_access
def edit_payment(request, payment_id):
    """تعديل مدفوع"""
    try:
        payment = get_object_or_404(Tuition, id=payment_id)
        
        if request.method == 'POST':
            # معالجة التعديل
            try:
                payment.installment_number = int(request.POST.get('installment_number', payment.installment_number))
                payment.amount_tuition = Decimal(str(request.POST.get('amount_tuition', payment.amount_tuition)))
                payment.amount_paid = Decimal(str(request.POST.get('amount_paid', payment.amount_paid)))
                payment.payment_method = request.POST.get('payment_method', payment.payment_method)
                payment.notes = request.POST.get('notes', payment.notes)
                
                # تحديث تاريخ الاستحقاق إذا تم توفيره
                due_date = request.POST.get('due_date')
                if due_date:
                    payment.due_date = due_date
                
                # حفظ التغييرات
                payment.save()
                
                messages.success(request, f'تم تعديل المدفوع للطالب {payment.student.name} بنجاح')
                return redirect('payments:all_payments')
                
            except Exception as e:
                messages.error(request, f'خطأ في حفظ التعديلات: {str(e)}')
        
        # عرض نموذج التعديل
        context = {
            'payment': payment,
            'permissions': get_payment_permissions(request.user),
            'page_title': f'تعديل مدفوع - {payment.student.name}'
        }
        
        return render(request, 'payments/edit_payment.html', context)
        
    except Exception as e:
        messages.error(request, f'خطأ: {str(e)}')
        return redirect('payments:all_payments')

@never_cache
@payments_full_access
def pay_installment(request, pk):
    """دفع قسط لطالب محدد مع ربط المصروفات من school_settings"""
    user_role = get_user_role(request.user)
    permissions = get_payment_permissions(request.user)
    student = get_object_or_404(Student, pk=pk)
    
    # استيراد نماذج الإعدادات من التطبيق الصحيح
    try:
        from school_settings.models import SchoolFeesSettings, AcademicYear, StudentDiscount
    except ImportError:
        messages.error(request, 'لا يمكن الوصول لإعدادات المصروفات')
        return redirect('payments:all_payments')
    
    # الحصول على العام الدراسي الحالي
    current_year = AcademicYear.get_current_year()
    if not current_year:
        messages.warning(request, 'لا يوجد عام دراسي نشط. يرجى إعداد العام الدراسي في الإعدادات')
        current_year = None
    
    # الحصول على المصروفات المستحقة للطالب
    student_fees = []
    available_discounts = []
    
    if current_year and hasattr(student, 'grade_level'):
        try:
            # المصروفات المستحقة حسب الصف والعام الدراسي
            fees_settings = SchoolFeesSettings.objects.filter(
                academic_year=current_year,
                grade_level=student.grade_level,
                is_active=True
            ).order_by('fee_type')
            
            for fee_setting in fees_settings:
                # التحقق من المدفوعات السابقة لهذا النوع من المصروفات
                existing_payments = Tuition.objects.filter(
                    student=student,
                    fee_type=fee_setting.fee_type,
                    academic_year=current_year
                ).aggregate(
                    total_paid=Sum('amount_paid'),
                    installments_count=Count('id')
                )
                
                total_paid = float(existing_payments['total_paid'] or 0)
                remaining_amount = float(fee_setting.total_amount) - total_paid
                
                if remaining_amount > 0:
                    student_fees.append({
                        'setting': fee_setting,
                        'total_amount': float(fee_setting.total_amount),
                        'installment_amount': float(fee_setting.installment_amount),
                        'total_paid': total_paid,
                        'remaining_amount': remaining_amount,
                        'installments_paid': existing_payments['installments_count'] or 0,
                        'installments_remaining': fee_setting.installments_count - (existing_payments['installments_count'] or 0)
                    })
            
            # الحصول على الخصومات المتاحة للطالب
            available_discounts = StudentDiscount.objects.filter(
                student=student,
                academic_year=current_year,
                status='APPROVED'
            ).select_related('discount_setting')
            
        except Exception as e:
            print(f"خطأ في جلب المصروفات: {e}")
            messages.warning(request, 'حدث خطأ في جلب المصروفات المستحقة')
    
    if request.method == 'POST':
        # معالجة دفع القسط - مُحدث
        try:
            fee_type = request.POST.get('fee_type')
            installment_number = request.POST.get('installment_number')
            amount_paid = request.POST.get('amount_paid')
            payment_method = request.POST.get('payment_method', 'cash')
            notes = request.POST.get('notes', '')
            apply_discount_id = request.POST.get('apply_discount')
            
            print(f"البيانات المستلمة: fee_type={fee_type}, installment_number={installment_number}, amount_paid={amount_paid}")
            
            if not fee_type or not installment_number or not amount_paid:
                messages.error(request, 'بيانات غير مكتملة')
                return render(request, 'payments/pay_student_fees.html', {
                    'student': student,
                    'current_year': current_year,
                    'student_fees': student_fees,
                    'available_discounts': available_discounts,
                    'permissions': permissions,
                    'user_role': user_role,
                    'page_title': f'دفع مصروفات للطالب {student.name}'
                })
            
            # التحقق من صحة المبلغ
            try:
                amount_paid = Decimal(str(amount_paid))
                if amount_paid <= 0:
                    messages.error(request, 'يجب إدخال مبلغ أكبر من صفر')
                    raise ValueError("مبلغ غير صحيح")
            except (ValueError, InvalidOperation):
                messages.error(request, 'مبلغ غير صحيح')
                return render(request, 'payments/pay_student_fees.html', {
                    'student': student,
                    'current_year': current_year,
                    'student_fees': student_fees,
                    'available_discounts': available_discounts,
                    'permissions': permissions,
                    'user_role': user_role,
                    'page_title': f'دفع مصروفات للطالب {student.name}'
                })
            
            # العثور على إعدادات المصروفات
            fee_setting = SchoolFeesSettings.objects.get(
                academic_year=current_year,
                grade_level=student.grade_level,
                fee_type=fee_type,
                is_active=True
            )
            
            # حساب المبلغ المطلوب (مع تطبيق الخصم إن وجد)
            base_amount = float(fee_setting.installment_amount)
            discount_amount = 0
            final_amount = base_amount
            applied_discount = None
            
            if apply_discount_id:
                try:
                    student_discount = StudentDiscount.objects.get(
                        id=apply_discount_id,
                        student=student,
                        status='APPROVED'
                    )
                    discount_amount = student_discount.discount_setting.calculate_discount(base_amount)
                    final_amount = base_amount - discount_amount
                    applied_discount = student_discount
                except StudentDiscount.DoesNotExist:
                    pass
            
            # إنشاء سجل المدفوع
            tuition = Tuition.objects.create(
                student=student,
                academic_year=current_year,
                fee_type=fee_type,
                fee_name=fee_setting.fee_name,
                installment_number=int(installment_number),
                amount_tuition=Decimal(str(final_amount)),
                amount_paid=amount_paid,
                payment_method=payment_method,
                payment_user=request.user.get_full_name() or request.user.username,
                payment_date=timezone.now(),
                notes=notes,
                applied_discount=applied_discount,
                discount_amount=Decimal(str(discount_amount)) if discount_amount > 0 else 0
            )
            
            # إنشاء سجل دفع
            if tuition.amount_paid > 0:
                PaymentRecord.objects.create(
                    tuition=tuition,
                    amount_paid=tuition.amount_paid,
                    payment_method=tuition.payment_method,
                    payment_user=tuition.payment_user,
                    notes=tuition.notes
                )
            
            # رسالة نجاح
            success_msg = f'تم تسجيل دفع {fee_setting.get_fee_type_display()} بنجاح!'
            if discount_amount > 0:
                success_msg += f' (تم تطبيق خصم {discount_amount:.2f} ج.م)'
            
            messages.success(request, f'{success_msg} المبلغ: {tuition.amount_paid} ج.م')
            return redirect('payments:receipt', pk=tuition.pk)
            
        except SchoolFeesSettings.DoesNotExist:
            messages.error(request, 'لا توجد إعدادات مصروفات لهذا النوع')
        except Exception as e:
            print(f"خطأ في حفظ المدفوع: {e}")
            messages.error(request, f'حدث خطأ في حفظ المدفوع: {str(e)}')
    
    # الحصول على تاريخ المدفوعات للطالب
    student_payments = Tuition.objects.filter(
        student=student,
        academic_year=current_year
    ).order_by('-payment_date')[:10]
    
    context = {
        'student': student,
        'current_year': current_year,
        'student_fees': student_fees,
        'available_discounts': available_discounts,
        'student_payments': student_payments,
        'permissions': permissions,
        'user_role': user_role,
        'page_title': f'دفع مصروفات للطالب {student.name}'
    }
    
    return render(request, 'payments/pay_student_fees.html', context)



@never_cache
@payments_full_access
def edit_payment(request, payment_id):
    tuition = get_object_or_404(Tuition, id=payment_id)
    student = tuition.student
    permissions = get_payment_permissions(request.user)

    if not permissions['can_edit']:
        messages.error(request, 'لا تملك صلاحية لتعديل المدفوعات')
        return redirect('payments:all_payments')

    if request.method == 'POST':
        try:
            tuition.installment_number = request.POST.get('installment_number')
            tuition.amount_tuition = Decimal(request.POST.get('amount_tuition', '0'))
            tuition.amount_paid = Decimal(request.POST.get('amount_paid', '0'))
            tuition.payment_method = request.POST.get('payment_method', 'cash')
            tuition.notes = request.POST.get('notes', '')

            due_date = request.POST.get('due_date')
            if due_date:
                tuition.due_date = due_date

            tuition.update_payment_status()
            tuition.save()

            payment_record = PaymentRecord.objects.filter(tuition=tuition).first()
            if payment_record:
                payment_record.amount_paid = tuition.amount_paid
                payment_record.payment_method = tuition.payment_method
                payment_record.notes = tuition.notes
                payment_record.save()

            messages.success(request, 'تم تعديل المدفوع بنجاح!')
            # إعادة التوجيه داخل تطبيق المدفوعات
            return redirect('payments:all_payments')
            # أو إلى الإيصال
            # return redirect('payments:receipt', pk=tuition.pk)

        except Exception as e:
            print(f"خطأ في تعديل المدفوع: {e}")
            messages.error(request, f'حدث خطأ في التعديل: {str(e)}')

    from django import forms
    class EditTuitionForm(forms.ModelForm):
        due_date = forms.DateField(
            required=False,
            widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        )
        class Meta:
            model = Tuition
            fields = ['installment_number', 'amount_tuition', 'amount_paid', 'payment_method', 'notes']
            widgets = {
                'installment_number': forms.NumberInput(attrs={'class': 'form-control'}),
                'amount_tuition': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
                'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
                'payment_method': forms.Select(attrs={'class': 'form-select'}),
                'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            }

    student_payments = Tuition.objects.filter(student=student).order_by('-payment_date')[:10]

    context = {
        'student': student,
        'tuition': tuition,
        'installment_form': EditTuitionForm(instance=tuition),
        'student_payments': student_payments,
        'permissions': permissions,
        'page_title': f'تعديل مدفوع للطالب {student.name}',
        'is_edit': True,
    }

    return render(request, 'payments/pay_installment.html', context)

@never_cache
@payments_sensitive_operation
def delete_installment(request, pk):
    tuition = get_object_or_404(Tuition, pk=pk)
    student = tuition.student
    permissions = get_payment_permissions(request.user)

    if request.method == 'POST':
        PaymentRecord.objects.filter(tuition=tuition).delete()
        installment_info = f"قسط رقم {tuition.installment_number} - مبلغ {tuition.amount_paid} ج.م"
        tuition.delete()
        messages.success(request, f'تم حذف {installment_info} بنجاح!')
        # إعادة التوجيه داخل تطبيق المدفوعات
        return redirect('payments:all_payments')

    context = {
        'tuition': tuition,
        'student': student,
        'permissions': permissions,
        'page_title': 'حذف قسط',
        'warning_message': 'هذا الإجراء لا يمكن التراجع عنه! سيتم حذف جميع سجلات الدفع المرتبطة.'
    }
    return render(request, 'payments/delete_installment.html', context)

@never_cache
@payments_basic_access
def receipt(request, pk):
    """طباعة إيصال الدفع"""
    tuition = get_object_or_404(Tuition, pk=pk)
    student = tuition.student
    permissions = get_payment_permissions(request.user)
    
    if tuition.payment_status not in ['PAID', 'PARTIALLY_PAID']:
        messages.warning(request, 'هذا القسط لم يتم دفعه بعد.')
        # تصحيح التوجيه - البقاء داخل تطبيق المدفوعات
        return redirect('payments:all_payments')
    
    # الحصول على سجلات الدفع المرتبطة
    payment_records = PaymentRecord.objects.filter(tuition=tuition).order_by('-payment_date')
    
    context = {
        'tuition': tuition,
        'student': student,
        'payment_records': payment_records,
        'permissions': permissions,
        'today': timezone.now(),
        'page_title': f'إيصال دفع - {student.name}'
    }
    return render(request, 'payments/receipt.html', context)

# ===================================
# 🔌 APIs المساعدة
# ===================================
# في payments/views.py - إضافة دالة print_receipt

@never_cache
@payments_basic_access
def print_receipt(request, payment_id):
    """طباعة إيصال محدد"""
    try:
        payment = get_object_or_404(Tuition, id=payment_id)
        
        # إعادة توجيه لصفحة الإيصال الموجودة
        return redirect('payments:receipt', pk=payment.pk)
        
    except Exception as e:
        messages.error(request, f'خطأ في العثور على الإيصال: {str(e)}')
        return redirect('payments:all_payments')

@csrf_protect
@require_POST
@payments_basic_access
def student_search_ajax(request):
    """API للبحث عن الطلاب"""
    try:
        import json
        data = json.loads(request.body)
        
        query = data.get('query', '').strip()
        grade_id = data.get('grade', '')
        year_id = data.get('year', '')
        
        # بناء الاستعلام
        from students.models import Student
        students = Student.objects.all()
        
        # فلترة حسب النص
        if query:
            students = students.filter(
                Q(name__icontains=query) | 
                Q(national_number__icontains=query)
            )
        
        # فلترة حسب الصف
        if grade_id:
            students = students.filter(grade_level_id=grade_id)
        
        # تحديد عدد النتائج
        students = students.select_related('grade_level')[:50]
        
        # إعداد البيانات للإرسال
        students_data = []
        for student in students:
            # حساب إحصائيات المدفوعات
            payments = Tuition.objects.filter(student=student)
            total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or 0
            total_tuition = payments.aggregate(total=Sum('amount_tuition'))['total'] or 0
            total_remaining = total_tuition - total_paid
            payments_count = payments.count()
            
            students_data.append({
                'id': student.id,
                'name': student.name,
                'national_number': student.national_number,
                'grade_name': getattr(student.grade_level, 'name', 'غير محدد'),
                'total_paid': float(total_paid),
                'total_remaining': float(total_remaining) if total_remaining > 0 else 0,
                'payments_count': payments_count
            })
        
        return JsonResponse({
            'success': True,
            'students': students_data,
            'count': len(students_data)
        })
        
    except Exception as e:
        print(f"خطأ في البحث: {e}")
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ في البحث'
        })

# في payments/views.py - إضافة دالة حذف جميع المدفوعات

@never_cache
@payments_admin_access
def delete_all_payments(request, student_id):
    """حذف جميع مدفوعات طالب محدد"""
    if request.method == 'POST':
        try:
            student = get_object_or_404(Student, id=student_id)
            
            # التأكد من الصلاحيات
            if not get_payment_permissions(request.user)['can_delete']:
                messages.error(request, 'ليس لديك صلاحية لحذف المدفوعات')
                return redirect('payments:all_payments')
            
            # حذف جميع المدفوعات
            deleted_count = Tuition.objects.filter(student=student).count()
            Tuition.objects.filter(student=student).delete()
            
            messages.success(request, f'تم حذف {deleted_count} مدفوع للطالب {student.name} بنجاح')
            
        except Exception as e:
            messages.error(request, f'خطأ في الحذف: {str(e)}')
    
    return redirect('payments:all_payments')


@csrf_protect
@require_POST
@payments_full_access
def record_payment_ajax(request):
    """تسجيل دفع قسط عبر Ajax"""
    try:
        student_id = request.POST.get('student_id')
        amount_paid = Decimal(request.POST.get('amount_paid', '0'))
        payment_method = request.POST.get('payment_method', 'cash')
        notes = request.POST.get('notes', '')

        if not student_id:
            return JsonResponse({'success': False, 'message': 'الطالب غير محدد'})

        if amount_paid <= 0:
            return JsonResponse({'success': False, 'message': 'يجب إدخال مبلغ أكبر من صفر'})

        student = Student.objects.get(id=student_id)

        # البحث عن آخر رقم قسط للطالب
        last_installment = Tuition.objects.filter(student=student).order_by('-installment_number').first()
        next_installment_number = (last_installment.installment_number + 1) if last_installment else 1

        # إنشاء قسط جديد
        tuition = Tuition.objects.create(
            student=student,
            installment_number=next_installment_number,
            amount_tuition=amount_paid,
            amount_paid=amount_paid,
            payment_status='PAID',
            payment_date=timezone.now(),
            due_date=timezone.now().date(),
            payment_method=payment_method,
            payment_user=request.user.get_full_name() or request.user.username,
            notes=notes
        )

        # إنشاء سجل دفع
        payment_record = PaymentRecord.objects.create(
            tuition=tuition,
            amount_paid=amount_paid,
            payment_method=payment_method,
            payment_user=request.user.get_full_name() or request.user.username,
            notes=notes
        )

        return JsonResponse({
            'success': True,
            'message': 'تم تسجيل الدفع بنجاح',
            'data': {
                'student_name': student.name,
                'amount_paid': float(amount_paid),
                'installment_number': next_installment_number,
                'payment_user': request.user.get_full_name() or request.user.username,
                'receipt_number': payment_record.receipt_number,
                'payment_date': tuition.payment_date.strftime('%Y-%m-%d %H:%M')
            }
        })

    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'الطالب غير موجود'})
    except Exception as e:
        print(f"خطأ في تسجيل الدفع: {e}")
        return JsonResponse({'success': False, 'message': f'حدث خطأ: {str(e)}'})

@payments_basic_access
def get_student_payments_ajax(request):
    """عرض أقساط طالب محدد عبر Ajax"""
    if request.method == 'GET':
        student_id = request.GET.get('student_id')
        
        if not student_id:
            return JsonResponse({'error': 'معرف الطالب غير محدد'})
        
        try:
            student = Student.objects.get(id=student_id)
            payments = Tuition.objects.filter(student=student).order_by('-installment_number')
            
            payments_data = []
            for payment in payments:
                payments_data.append({
                    'id': payment.id,
                    'installment_number': payment.installment_number,
                    'amount_tuition': float(payment.amount_tuition),
                    'amount_paid': float(payment.amount_paid),
                    'remaining_amount': float(payment.remaining_amount),
                    'payment_status': payment.get_payment_status_display(),
                    'payment_status_code': payment.payment_status,
                    'payment_date': payment.payment_date.strftime('%Y-%m-%d %H:%M') if payment.payment_date else None,
                    'due_date': payment.due_date.strftime('%Y-%m-%d') if payment.due_date else None,
                    'payment_method': payment.get_payment_method_display(),
                    'payment_user': payment.payment_user,
                    'receipt_number': payment.receipt_number,
                    'is_overdue': payment.is_overdue,
                })
            
            # إحصائيات الطالب
            student_stats = {
                'total_paid': float(payments.filter(payment_status='PAID').aggregate(total=Sum('amount_paid'))['total'] or 0),
                'total_pending': payments.filter(payment_status__in=['PENDING', 'OVERDUE']).count(),
                'total_overdue': payments.filter(payment_status='OVERDUE').count(),
            }
            
            return JsonResponse({
                'success': True,
                'student_name': student.name,
                'student_stats': student_stats,
                'payments': payments_data,
                'total_payments': len(payments_data)
            })
            
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'الطالب غير موجود'})
        except Exception as e:
            print(f"خطأ في جلب مدفوعات الطالب: {e}")
            return JsonResponse({'success': False, 'error': f'حدث خطأ: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'طريقة طلب غير صحيحة'})

# ===================================
# 📊 التقارير المالية (للمرحلة القادمة)
# ===================================

@never_cache
@payments_financial_reports
def financial_reports(request):
    """التقارير المالية - سيتم تطويرها لاحقاً"""
    permissions = get_payment_permissions(request.user)
    
    context = {
        'permissions': permissions,
        'page_title': 'التقارير المالية',
        'message': 'التقارير المالية المتقدمة قيد التطوير...'
    }
    return render(request, 'payments/financial_reports.html', context)


# payments/views.py - إضافة APIs المفقودة

# ... الكود الموجود ...

# ===================================
# 🔌 APIs الجديدة المطلوبة
# ===================================

@never_cache
@payments_basic_access
def stats_api(request):
    """API الإحصائيات"""
    try:
        stats = calculate_payment_stats()
        return JsonResponse({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@payments_basic_access
def get_payment_details_ajax(request, payment_id):
    """API لجلب تفاصيل مدفوع محدد"""
    if request.method == 'GET':
        try:
            tuition = get_object_or_404(Tuition, id=payment_id)
            student = tuition.student
            
            # بناء بيانات التفاصيل
            payment_data = {
                'id': tuition.id,
                'student_name': student.name,
                'student_national_number': student.national_number,
                'student_grade': getattr(student, 'grade_name', 'غير محدد'),
                'student_phone': student.phone_number or 'غير محدد',
                'installment_number': tuition.installment_number,
                'amount_tuition': float(tuition.amount_tuition),
                'amount_paid': float(tuition.amount_paid),
                'remaining_amount': float(tuition.remaining_amount),
                'payment_status_code': tuition.payment_status,
                'payment_status_display': tuition.get_payment_status_display(),
                'payment_method': tuition.payment_method,
                'payment_date': tuition.payment_date.isoformat() if tuition.payment_date else None,
                'due_date': tuition.due_date.isoformat() if tuition.due_date else None,
                'payment_user': tuition.payment_user,
                'notes': tuition.notes or '',
                'receipt_number': tuition.receipt_number or '',
                'created_date': tuition.created_date.isoformat() if tuition.created_date else None,
            }
            
            return JsonResponse({
                'success': True,
                'payment': payment_data
            })
            
        except Tuition.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'المدفوع غير موجود'
            })
        except Exception as e:
            print(f"خطأ في جلب تفاصيل المدفوع: {e}")
            return JsonResponse({
                'success': False,
                'error': 'حدث خطأ في جلب التفاصيل'
            })
    
    return JsonResponse({'success': False, 'error': 'طريقة طلب غير صحيحة'})

@csrf_protect
@require_POST
@payments_full_access
def validate_payment_ajax(request):
    """API للتحقق من صحة بيانات المدفوع"""
    try:
        student_id = request.POST.get('student_id')
        installment_number = request.POST.get('installment_number')
        amount_tuition = request.POST.get('amount_tuition')
        amount_paid = request.POST.get('amount_paid')
        
        errors = {}
        
        # التحقق من الطالب
        if not student_id:
            errors['student_id'] = 'يجب اختيار طالب'
        else:
            try:
                Student.objects.get(id=student_id)
            except Student.DoesNotExist:
                errors['student_id'] = 'الطالب غير موجود'
        
        # التحقق من رقم القسط
        if not installment_number:
            errors['installment_number'] = 'رقم القسط مطلوب'
        else:
            try:
                inst_num = int(installment_number)
                if inst_num <= 0:
                    errors['installment_number'] = 'رقم القسط يجب أن يكون أكبر من صفر'
                    
                # التحقق من عدم تكرار القسط
                if student_id:
                    existing = Tuition.objects.filter(
                        student_id=student_id,
                        installment_number=inst_num
                    ).first()
                    if existing:
                        errors['installment_number'] = f'القسط رقم {inst_num} موجود مسبقاً لهذا الطالب'
                        
            except (ValueError, TypeError):
                errors['installment_number'] = 'رقم القسط يجب أن يكون رقماً صحيحاً'
        
        # التحقق من المبالغ
        if not amount_tuition:
            errors['amount_tuition'] = 'مبلغ القسط مطلوب'
        else:
            try:
                tuition_val = float(amount_tuition)
                if tuition_val <= 0:
                    errors['amount_tuition'] = 'مبلغ القسط يجب أن يكون أكبر من صفر'
            except (ValueError, TypeError):
                errors['amount_tuition'] = 'مبلغ القسط يجب أن يكون رقماً صحيحاً'
        
        if not amount_paid:
            errors['amount_paid'] = 'المبلغ المدفوع مطلوب'
        else:
            try:
                paid_val = float(amount_paid)
                if paid_val <= 0:
                    errors['amount_paid'] = 'المبلغ المدفوع يجب أن يكون أكبر من صفر'
                    
                # التحقق من أن المدفوع لا يتجاوز المطلوب
                if amount_tuition:
                    tuition_val = float(amount_tuition)
                    if paid_val > tuition_val:
                        errors['amount_paid'] = 'المبلغ المدفوع لا يمكن أن يكون أكبر من المبلغ المطلوب'
                        
            except (ValueError, TypeError):
                errors['amount_paid'] = 'المبلغ المدفوع يجب أن يكون رقماً صحيحاً'
        
        return JsonResponse({
            'success': len(errors) == 0,
            'errors': errors,
            'message': 'البيانات صحيحة' if len(errors) == 0 else 'يوجد أخطاء في البيانات'
        })
        
    except Exception as e:
        print(f"خطأ في التحقق من البيانات: {e}")
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ في التحقق من البيانات'
        })

@payments_basic_access
def calculate_student_total_ajax(request):
    """API لحساب إجمالي مستحقات الطالب"""
    if request.method == 'GET':
        student_id = request.GET.get('student_id')
        
        if not student_id:
            return JsonResponse({'error': 'معرف الطالب مطلوب'})
        
        try:
            student = Student.objects.get(id=student_id)
            
            # حساب الإحصائيات
            payments = Tuition.objects.filter(student=student)
            
            stats = {
                'total_tuition': float(payments.aggregate(total=Sum('amount_tuition'))['total'] or 0),
                'total_paid': float(payments.aggregate(total=Sum('amount_paid'))['total'] or 0),
                'total_remaining': 0,  # سيتم حسابه
                'paid_count': payments.filter(payment_status='PAID').count(),
                'pending_count': payments.filter(payment_status__in=['PENDING', 'OVERDUE']).count(),
                'overdue_count': payments.filter(payment_status='OVERDUE').count(),
                'last_payment_date': None,
            }
            
            # حساب المتبقي
            stats['total_remaining'] = stats['total_tuition'] - stats['total_paid']
            
            # آخر دفع
            last_payment = payments.filter(payment_status='PAID').order_by('-payment_date').first()
            if last_payment and last_payment.payment_date:
                stats['last_payment_date'] = last_payment.payment_date.strftime('%Y-%m-%d')
            
            return JsonResponse({
                'success': True,
                'student_name': student.name,
                'stats': stats
            })
            
        except Student.DoesNotExist:
            return JsonResponse({'error': 'الطالب غير موجود'})
        except Exception as e:
            print(f"خطأ في حساب الإحصائيات: {e}")
            return JsonResponse({'error': 'حدث خطأ في الحساب'})
    
    return JsonResponse({'error': 'طريقة طلب غير صحيحة'})



# @never_cache
# @payments_financial_reports
# def daily_report(request):
#     """تقرير يومي للمدفوعات"""
#     target_date = request.GET.get('date', timezone.now().date())
    
#     try:
#         if isinstance(target_date, str):
#             target_date = timezone.datetime.strptime(target_date, '%Y-%m-%d').date()
#     except:
#         target_date = timezone.now().date()
    
#     # إحصائيات اليوم
#     daily_payments = Tuition.objects.filter(
#         payment_date__date=target_date,
#         payment_status='PAID'
#     )
    
#     stats = daily_payments.aggregate(
#         total_amount=Sum('amount_paid'),
#         total_count=Count('id')
#     )
    
#     # تجميع حسب طريقة الدفع
#     method_stats = daily_payments.values('payment_method').annotate(
#         count=Count('id'),
#         amount=Sum('amount_paid')
#     ).order_by('-amount')
    
#     context = {
#         'target_date': target_date,
#         'daily_payments': daily_payments.select_related('student'),
#         'stats': stats,
#         'method_stats': method_stats,
#         'page_title': f'التقرير اليومي - {target_date.strftime("%Y-%m-%d")}',
#     }
    
#     return render(request, 'payments/daily_report.html', context)

# في payments/views.py - تحسين وتطوير التقرير اليومي

# في payments/views.py - تحديث دالة daily_report مع معالجة أفضل للأخطاء

@never_cache
@payments_financial_reports
def daily_report(request):
    """التقرير اليومي المتقدم للمدفوعات"""
    
    try:
        # الحصول على التاريخ المطلوب
        target_date = request.GET.get('date')
        if target_date:
            try:
                target_date = timezone.datetime.strptime(target_date, '%Y-%m-%d').date()
            except:
                target_date = timezone.now().date()
        else:
            target_date = timezone.now().date()
        
        # صلاحيات المستخدم
        permissions = get_payment_permissions(request.user)
        
        # === إحصائيات اليوم الأساسية ===
        daily_payments = Tuition.objects.filter(
            payment_date__date=target_date,
            payment_status='PAID'
        ).select_related('student')
        
        # إحصائيات أساسية آمنة
        basic_stats = {
            'total_amount': 0,
            'total_count': 0,
            'avg_payment': 0,
            'min_payment': 0,
            'max_payment': 0
        }
        
        if daily_payments.exists():
            try:
                stats_data = daily_payments.aggregate(
                    total_amount=Sum('amount_paid'),
                    total_count=Count('id'),
                    avg_payment=Avg('amount_paid'),
                    min_payment=Min('amount_paid'),
                    max_payment=Max('amount_paid')
                )
                
                basic_stats = {
                    'total_amount': stats_data['total_amount'] or 0,
                    'total_count': stats_data['total_count'] or 0,
                    'avg_payment': stats_data['avg_payment'] or 0,
                    'min_payment': stats_data['min_payment'] or 0,
                    'max_payment': stats_data['max_payment'] or 0
                }
            except:
                pass  # الاحتفاظ بالقيم الافتراضية
        
        # === إحصائيات طرق الدفع ===
        payment_methods_stats = []
        try:
            payment_methods_stats = daily_payments.values('payment_method').annotate(
                count=Count('id'),
                amount=Sum('amount_paid'),
                avg_amount=Avg('amount_paid')
            ).order_by('-amount')
        except Exception as e:
            print(f"خطأ في إحصائيات طرق الدفع: {e}")
        
        # === إحصائيات الموظفين ===
        staff_stats = []
        try:
            staff_stats = daily_payments.values('payment_user').annotate(
                count=Count('id'),
                amount=Sum('amount_paid'),
                avg_amount=Avg('amount_paid')
            ).order_by('-amount')
        except Exception as e:
            print(f"خطأ في إحصائيات الموظفين: {e}")
        
        # === إحصائيات الساعات ===
        hourly_stats = []
        try:
            # استخدام طريقة آمنة لاستخراج الساعة
            hourly_stats = daily_payments.extra(
                select={'hour': "strftime('%%H', payment_date)"}  # SQLite compatible
            ).values('hour').annotate(
                count=Count('id'),
                amount=Sum('amount_paid')
            ).order_by('hour')
            
            # تحويل لقائمة للتعامل معها
            hourly_stats = list(hourly_stats)
        except Exception as e:
            print(f"خطأ في إحصائيات الساعات: {e}")
            # محاولة بديلة
            try:
                hourly_stats = []
                for hour in range(24):
                    hour_payments = daily_payments.filter(
                        payment_date__hour=hour
                    ).aggregate(
                        count=Count('id'),
                        amount=Sum('amount_paid')
                    )
                    if hour_payments['count'] and hour_payments['count'] > 0:
                        hourly_stats.append({
                            'hour': hour,
                            'count': hour_payments['count'],
                            'amount': hour_payments['amount'] or 0
                        })
            except Exception as e2:
                print(f"خطأ في الطريقة البديلة للساعات: {e2}")
        
        # === المدفوعات الكبيرة ===
        large_payments = []
        try:
            avg_payment = basic_stats['avg_payment']
            if avg_payment > 0:
                large_payments = daily_payments.filter(
                    amount_paid__gt=avg_payment
                ).order_by('-amount_paid')[:10]
        except Exception as e:
            print(f"خطأ في المدفوعات الكبيرة: {e}")
        
        # === مقارنة مع الأيام السابقة ===
        previous_dates = []
        try:
            for i in range(1, 8):  # آخر 7 أيام
                prev_date = target_date - timedelta(days=i)
                prev_stats = Tuition.objects.filter(
                    payment_date__date=prev_date,
                    payment_status='PAID'
                ).aggregate(
                    total_amount=Sum('amount_paid'),
                    total_count=Count('id')
                )
                previous_dates.append({
                    'date': prev_date,
                    'total_amount': float(prev_stats['total_amount'] or 0),
                    'total_count': prev_stats['total_count'] or 0
                })
        except Exception as e:
            print(f"خطأ في بيانات الأيام السابقة: {e}")
        
        # === إحصائيات المقارنة ===
        comparison_stats = {
            'amount_change': 0,
            'count_change': 0,
            'amount_percentage': 0,
            'count_percentage': 0
        }
        
        try:
            yesterday = target_date - timedelta(days=1)
            yesterday_stats = Tuition.objects.filter(
                payment_date__date=yesterday,
                payment_status='PAID'
            ).aggregate(
                total_amount=Sum('amount_paid'),
                total_count=Count('id')
            )
            
            if yesterday_stats['total_amount'] and basic_stats['total_amount']:
                comparison_stats['amount_change'] = float(basic_stats['total_amount']) - float(yesterday_stats['total_amount'])
                if float(yesterday_stats['total_amount']) > 0:
                    comparison_stats['amount_percentage'] = (comparison_stats['amount_change'] / float(yesterday_stats['total_amount'])) * 100
            
            if yesterday_stats['total_count'] and basic_stats['total_count']:
                comparison_stats['count_change'] = basic_stats['total_count'] - yesterday_stats['total_count']
                if yesterday_stats['total_count'] > 0:
                    comparison_stats['count_percentage'] = (comparison_stats['count_change'] / yesterday_stats['total_count']) * 100
        except Exception as e:
            print(f"خطأ في إحصائيات المقارنة: {e}")
        
        # === المتأخرات ===
        overdue_stats = {'count': 0, 'amount': 0}
        try:
            overdue_data = Tuition.objects.filter(
                due_date__lte=target_date,
                payment_status='OVERDUE'
            ).aggregate(
                count=Count('id'),
                amount=Sum('remaining_amount')
            )
            overdue_stats = {
                'count': overdue_data['count'] or 0,
                'amount': float(overdue_data['amount'] or 0)
            }
        except Exception as e:
            print(f"خطأ في إحصائيات المتأخرات: {e}")
        
        # === التقرير الشهري ===
        monthly_stats = {'total_amount': 0, 'total_count': 0}
        try:
            month_start = target_date.replace(day=1)
            monthly_data = Tuition.objects.filter(
                payment_date__date__gte=month_start,
                payment_date__date__lte=target_date,
                payment_status='PAID'
            ).aggregate(
                total_amount=Sum('amount_paid'),
                total_count=Count('id')
            )
            monthly_stats = {
                'total_amount': float(monthly_data['total_amount'] or 0),
                'total_count': monthly_data['total_count'] or 0
            }
        except Exception as e:
            print(f"خطأ في الإحصائيات الشهرية: {e}")
        
        # === أهداف التحصيل ===
        daily_target = 10000  # يمكن جعلها من الإعدادات
        monthly_target = 300000
        
        target_achievement = {
            'daily_percentage': 0,
            'monthly_percentage': 0
        }
        
        try:
            if daily_target > 0:
                target_achievement['daily_percentage'] = (float(basic_stats['total_amount']) / daily_target) * 100
            if monthly_target > 0:
                target_achievement['monthly_percentage'] = (float(monthly_stats['total_amount']) / monthly_target) * 100
        except Exception as e:
            print(f"خطأ في حساب الأهداف: {e}")
        
        # === بيانات الرسوم البيانية ===
        chart_data = {
            'hourly_amounts': [],
            'hourly_hours': [],
            'methods_labels': [],
            'methods_amounts': [],
            'weekly_dates': [],
            'weekly_amounts': []
        }
        
        try:
            # بيانات الساعات
            chart_data['hourly_amounts'] = [float(h.get('amount', 0)) for h in hourly_stats]
            chart_data['hourly_hours'] = [f"{h.get('hour', 0)}:00" for h in hourly_stats]
            
            # بيانات طرق الدفع
            chart_data['methods_labels'] = [get_payment_method_display(m['payment_method']) for m in payment_methods_stats]
            chart_data['methods_amounts'] = [float(m['amount']) for m in payment_methods_stats]
            
            # البيانات الأسبوعية
            chart_data['weekly_dates'] = [d['date'].strftime('%d/%m') for d in previous_dates[::-1]] + [target_date.strftime('%d/%m')]
            chart_data['weekly_amounts'] = [d['total_amount'] for d in previous_dates[::-1]] + [float(basic_stats['total_amount'])]
        except Exception as e:
            print(f"خطأ في بيانات الرسوم البيانية: {e}")
        
        context = {
            'target_date': target_date,
            'daily_payments': daily_payments.order_by('-payment_date'),
            'basic_stats': basic_stats,
            'payment_methods_stats': payment_methods_stats,
            'staff_stats': staff_stats,
            'hourly_stats': hourly_stats,
            'large_payments': large_payments,
            'previous_dates': previous_dates,
            'comparison_stats': comparison_stats,
            'overdue_stats': overdue_stats,
            'monthly_stats': monthly_stats,
            'target_achievement': target_achievement,
            'permissions': permissions,
            'page_title': f'التقرير اليومي - {target_date.strftime("%Y-%m-%d")}',
            'chart_data': chart_data
        }
        
        return render(request, 'payments/daily_report.html', context)
        
    except Exception as e:
        print(f"خطأ عام في التقرير اليومي: {e}")
        messages.error(request, f'حدث خطأ في تحضير التقرير: {str(e)}')
        return redirect('payments:payments_home')

def get_payment_method_display(method):
    """تحويل طريقة الدفع للعرض"""
    methods = {
        'cash': 'نقدي',
        'transfer': 'تحويل بنكي',
        'card': 'بطاقة ائتمان',
        'check': 'شيك'
    }
    return methods.get(method, method)


@never_cache
@payments_financial_reports
def export_payments(request):
    """تصدير المدفوعات إلى CSV"""
    import csv
    from django.http import HttpResponse
    
    # الحصول على المعاملات
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')
    
    # بناء الاستعلام
    payments = Tuition.objects.select_related('student').all()
    
    if date_from:
        payments = payments.filter(payment_date__date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__date__lte=date_to)
    if status:
        payments = payments.filter(payment_status=status)
    
    # إنشاء الاستجابة
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="payments_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # كتابة BOM للعربية
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # رأس الجدول
    writer.writerow([
        'اسم الطالب',
        'الرقم القومي',
        'رقم القسط',
        'المبلغ المطلوب',
        'المبلغ المدفوع',
        'المبلغ المتبقي',
        'حالة الدفع',
        'طريقة الدفع',
        'تاريخ الدفع',
        'المحاسب',
        'ملاحظات'
    ])
    
    # البيانات
    for payment in payments:
        writer.writerow([
            payment.student.name,
            payment.student.national_number,
            payment.installment_number,
            float(payment.amount_tuition),
            float(payment.amount_paid),
            float(payment.remaining_amount),
            payment.get_payment_status_display(),
            payment.get_payment_method_display(),
            payment.payment_date.strftime('%Y-%m-%d %H:%M') if payment.payment_date else '',
            payment.payment_user,
            payment.notes or ''
        ])
    
    return response

# في payments/views.py - إضافة دالة تصدير PDF

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.http import HttpResponse
import io

@never_cache
@payments_financial_reports
def export_payments_pdf(request):
    """تصدير المدفوعات إلى PDF مع التصميم العربي"""
    
    # الحصول على المعاملات من GET
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    payment_method_filter = request.GET.get('payment_method', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    payment_user_filter = request.GET.get('payment_user', '')
    
    # بناء الاستعلام
    payments = Tuition.objects.select_related('student').all()
    
    # تطبيق الفلاتر
    if search_query:
        payments = payments.filter(
            Q(student__name__icontains=search_query) |
            Q(student__national_number__icontains=search_query) |
            Q(installment_number__icontains=search_query)
        )
    
    if status_filter:
        payments = payments.filter(payment_status=status_filter)
    
    if payment_method_filter:
        payments = payments.filter(payment_method=payment_method_filter)
    
    if date_from:
        payments = payments.filter(payment_date__date__gte=date_from)
    
    if date_to:
        payments = payments.filter(payment_date__date__lte=date_to)
    
    if payment_user_filter:
        payments = payments.filter(payment_user__icontains=payment_user_filter)
    
    payments = payments.order_by('-payment_date')
    
    # إنشاء ملف PDF
    buffer = io.BytesIO()
    
    # إعداد الوثيقة
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20,
        title="تقرير المدفوعات - مدرسة المنار"
    )
    
    # إعداد الأنماط
    styles = getSampleStyleSheet()
    
    # إنشاء أنماط عربية
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontSize=18,
        alignment=1,  # وسط
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2c5aa0'),
        spaceAfter=20
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=1,
        fontName='Helvetica-Bold',
        spaceAfter=10
    )
    
    # المحتوى
    story = []
    
    # العنوان الرئيسي
    title = Paragraph("تقرير المدفوعات - مدرسة المنار", title_style)
    story.append(title)
    
    # معلومات التقرير
    from datetime import datetime
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    report_info = f"تاريخ التقرير: {report_date} | عدد المدفوعات: {payments.count()}"
    
    if date_from or date_to:
        date_range = f"الفترة: من {date_from or 'البداية'} إلى {date_to or 'اليوم'}"
        report_info += f" | {date_range}"
    
    story.append(Paragraph(report_info, header_style))
    story.append(Spacer(1, 20))
    
    # إحصائيات سريعة
    stats = payments.aggregate(
        total_amount=Sum('amount_paid'),
        total_tuition=Sum('amount_tuition'),
        avg_payment=Avg('amount_paid')
    )
    
    stats_data = [
        ['الإحصائيات', ''],
        ['إجمالي المدفوع', f"{float(stats['total_amount'] or 0):,.2f} ج.م"],
        ['إجمالي المطلوب', f"{float(stats['total_tuition'] or 0):,.2f} ج.م"],
        ['متوسط الدفع', f"{float(stats['avg_payment'] or 0):,.2f} ج.م"],
        ['عدد المدفوعات', str(payments.count())]
    ]
    
    stats_table = Table(stats_data, colWidths=[2*inch, 2*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(stats_table)
    story.append(Spacer(1, 20))
    
    # جدول المدفوعات
    data = [
        ['اسم الطالب', 'القسط', 'المطلوب', 'المدفوع', 'الحالة', 'طريقة الدفع', 'التاريخ']
    ]
    
    for payment in payments[:50]:  # أول 50 مدفوع فقط لتجنب الملفات الكبيرة
        status_display = {
            'PAID': 'مدفوع',
            'PENDING': 'معلق',
            'PARTIALLY_PAID': 'جزئي',
            'OVERDUE': 'متأخر'
        }.get(payment.payment_status, payment.payment_status)
        
        method_display = {
            'cash': 'نقدي',
            'transfer': 'تحويل',
            'card': 'بطاقة',
            'check': 'شيك'
        }.get(payment.payment_method, payment.payment_method)
        
        data.append([
            payment.student.name[:20],  # تحديد طول الاسم
            f"#{payment.installment_number}",
            f"{float(payment.amount_tuition):.2f}",
            f"{float(payment.amount_paid):.2f}",
            status_display,
            method_display,
            payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else 'غير محدد'
        ])
    
    # إنشاء الجدول
    table = Table(data, colWidths=[1.5*inch, 0.7*inch, 1*inch, 1*inch, 0.8*inch, 0.8*inch, 1*inch])
    
    table.setStyle(TableStyle([
        # تنسيق الرأس
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # تنسيق الصفوف
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        
        # تلوين صفوف متناوب
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    story.append(table)
    
    # ملاحظة إذا كان هناك المزيد
    if payments.count() > 50:
        story.append(Spacer(1, 20))
        note = Paragraph(
            f"ملاحظة: تم عرض أول 50 مدفوع من أصل {payments.count()} مدفوع. استخدم الفلاتر لتضييق النتائج.",
            header_style
        )
        story.append(note)
    
    # بناء PDF
    doc.build(story)
    
    # إعداد الاستجابة
    buffer.seek(0)
    filename = f"payments_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Content-Length'] = len(buffer.getvalue())
    
    return response

# في payments/views.py - إضافة دالة الطباعة

@never_cache
@payments_financial_reports
def print_payments_report(request):
    """إعداد صفحة الطباعة للمدفوعات"""
    
    # الحصول على المعاملات
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    payment_method_filter = request.GET.get('payment_method', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    payment_user_filter = request.GET.get('payment_user', '')
    
    # بناء الاستعلام
    payments = Tuition.objects.select_related('student').all()
    
    # تطبيق الفلاتر
    if search_query:
        payments = payments.filter(
            Q(student__name__icontains=search_query) |
            Q(student__national_number__icontains=search_query) |
            Q(installment_number__icontains=search_query)
        )
    
    if status_filter:
        payments = payments.filter(payment_status=status_filter)
    
    if payment_method_filter:
        payments = payments.filter(payment_method=payment_method_filter)
    
    if date_from:
        payments = payments.filter(payment_date__date__gte=date_from)
    
    if date_to:
        payments = payments.filter(payment_date__date__lte=date_to)
    
    if payment_user_filter:
        payments = payments.filter(payment_user__icontains=payment_user_filter)
    
    payments = payments.order_by('-payment_date')
    
    # إحصائيات
    stats = payments.aggregate(
        total_amount=Sum('amount_paid'),
        total_tuition=Sum('amount_tuition'),
        avg_payment=Avg('amount_paid'),
        total_count=Count('id')
    )
    
    # إحصائيات طرق الدفع
    method_stats = payments.values('payment_method').annotate(
        count=Count('id'),
        amount=Sum('amount_paid')
    ).order_by('-amount')
    
    # إحصائيات الحالات
    status_stats = payments.values('payment_status').annotate(
        count=Count('id'),
        amount=Sum('amount_paid')
    ).order_by('-amount')
    
    context = {
        'payments': payments[:100],  # أول 100 للطباعة
        'stats': stats,
        'method_stats': method_stats,
        'status_stats': status_stats,
        'filters': {
            'search_query': search_query,
            'status_filter': status_filter,
            'payment_method_filter': payment_method_filter,
            'date_from': date_from,
            'date_to': date_to,
            'payment_user_filter': payment_user_filter,
        },
        'total_payments': payments.count(),
        'report_date': timezone.now(),
        'page_title': 'تقرير طباعة المدفوعات'
    }
    
    return render(request, 'payments/print_report.html', context)

# في payments/views.py - إضافة views جديدة

@never_cache
@payments_basic_access
def student_search(request):
    """صفحة البحث عن الطلاب"""
    context = {
        'page_title': 'البحث عن طالب',
        'permissions': get_payment_permissions(request.user),
    }
    return render(request, 'payments/student_search.html', context)

@never_cache
@payments_full_access
def quick_payment(request):
    """صفحة الدفع السريع"""
    context = {
        'page_title': 'دفع سريع',
        'permissions': get_payment_permissions(request.user),
    }
    return render(request, 'payments/quick_payment.html', context)

# في payments/views.py - تحديث دالة print_receipts

@never_cache
@payments_basic_access
def print_receipts(request):
    """صفحة طباعة الإيصالات مع البحث"""
    user_role = get_user_role(request.user)
    permissions = get_payment_permissions(request.user)
    
    # الحصول على معايير البحث
    student_name = request.GET.get('student_name', '').strip()
    receipt_number = request.GET.get('receipt_number', '').strip()
    payment_date = request.GET.get('payment_date', '').strip()
    
    receipts = None
    
    # إذا كان هناك بحث
    if student_name or receipt_number or payment_date:
        try:
            # بناء الاستعلام
            receipts_query = Tuition.objects.filter(
                payment_status='PAID'
            ).select_related('student')
            
            # فلترة حسب اسم الطالب
            if student_name:
                receipts_query = receipts_query.filter(
                    student__name__icontains=student_name
                )
            
            # فلترة حسب رقم الإيصال
            if receipt_number:
                receipts_query = receipts_query.filter(
                    receipt_number__icontains=receipt_number
                )
            
            # فلترة حسب التاريخ
            if payment_date:
                receipts_query = receipts_query.filter(
                    payment_date__date=payment_date
                )
            
            # ترتيب النتائج
            receipts_query = receipts_query.order_by('-payment_date')
            
            # Pagination
            from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
            paginator = Paginator(receipts_query, 25)
            page_number = request.GET.get('page')
            
            try:
                receipts = paginator.page(page_number)
            except PageNotAnInteger:
                receipts = paginator.page(1)
            except EmptyPage:
                receipts = paginator.page(paginator.num_pages)
                
        except Exception as e:
            print(f"خطأ في البحث: {e}")
            messages.error(request, 'حدث خطأ في البحث')
    
    context = {
        'receipts': receipts,
        'permissions': permissions,
        'user_role': user_role,
        'page_title': 'طباعة الإيصالات'
    }
    
    return render(request, 'payments/print_receipts.html', context)


@never_cache
@payments_financial_reports
def financial_reports(request):
    """التقارير المالية العامة"""
    return redirect('payments:daily_report')

# في payments/views.py - تحديث دالة monthly_report

@never_cache
@payments_financial_reports
def monthly_report(request):
    """التقرير الشهري للمدفوعات"""
    user_role = get_user_role(request.user)
    permissions = get_payment_permissions(request.user)
    
    # الحصول على الشهر والسنة من الطلب
    report_month = request.GET.get('month', str(timezone.now().month))
    report_year = request.GET.get('year', str(timezone.now().year))
    
    try:
        month = int(report_month)
        year = int(report_year)
    except ValueError:
        month = timezone.now().month
        year = timezone.now().year
    
    # إعداد السنوات المتاحة
    current_year = timezone.now().year
    available_years = list(range(current_year - 2, current_year + 2))
    
    # فلترة المدفوعات حسب الشهر والسنة
    payments = Tuition.objects.filter(
        payment_date__year=year,
        payment_date__month=month,
        payment_status='PAID'
    ).select_related('student').order_by('-payment_date')
    
    # حساب الإحصائيات الشهرية
    monthly_stats = {}
    daily_data = {}
    payment_methods = []
    top_users = []
    
    try:
        # الإحصائيات الأساسية
        monthly_stats = payments.aggregate(
            total_amount=Sum('amount_paid'),
            total_count=Count('id'),
            avg_payment=Avg('amount_paid'),
            unique_students=Count('student', distinct=True)
        )
        
        # تنظيف القيم
        monthly_stats['total_amount'] = float(monthly_stats['total_amount'] or 0)
        monthly_stats['avg_payment'] = float(monthly_stats['avg_payment'] or 0)
        monthly_stats['total_count'] = monthly_stats['total_count'] or 0
        monthly_stats['unique_students'] = monthly_stats['unique_students'] or 0
        
        # حساب الأيام النشطة
        active_days = payments.dates('payment_date', 'day').count()
        monthly_stats['active_days'] = active_days
        
        # البيانات اليومية للرسم البياني
        daily_payments = payments.extra({'day': 'date(payment_date)'}).values('day').annotate(
            daily_total=Sum('amount_paid')
        ).order_by('day')
        
        if daily_payments:
            daily_data = {
                'labels': [item['day'] for item in daily_payments],
                'values': [float(item['daily_total']) for item in daily_payments],
                'highest_day': max(daily_payments, key=lambda x: x['daily_total']),
                'daily_average': monthly_stats['total_amount'] / max(active_days, 1)
            }
        
        # إحصائيات طرق الدفع
        payment_methods = list(payments.values('payment_method').annotate(
            count=Count('id'),
            amount=Sum('amount_paid')
        ).order_by('-amount'))
        
        # تحويل القيم للفلوت
        for method in payment_methods:
            method['amount'] = float(method['amount'] or 0)
        
        # أفضل الموظفين
        top_users = list(payments.values('payment_user').annotate(
            count=Count('id'),
            amount=Sum('amount_paid')
        ).order_by('-amount')[:5])
        
        # تحويل القيم للفلوت
        for user in top_users:
            user['amount'] = float(user['amount'] or 0)
            
    except Exception as e:
        print(f"خطأ في حساب إحصائيات التقرير الشهري: {e}")
        monthly_stats = {
            'total_amount': 0,
            'total_count': 0,
            'avg_payment': 0,
            'unique_students': 0,
            'active_days': 0
        }
    
    # أسماء الشهور بالعربية
    months_ar = {
        1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل',
        5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس',
        9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
    }
    
    context = {
        'payments': payments,
        'monthly_stats': monthly_stats,
        'daily_data': daily_data,
        'payment_methods': payment_methods,
        'top_users': top_users,
        'report_month': report_month,
        'report_year': report_year,
        'report_month_name': months_ar.get(month, 'غير محدد'),
        'available_years': available_years,
        'permissions': permissions,
        'user_role': user_role,
        'page_title': f'التقرير الشهري - {months_ar.get(month)} {year}'
    }
    
    return render(request, 'payments/monthly_report.html', context)


# في payments/views.py - تحديث دالة manage_discounts

# في payments/views.py - تحديث دالة manage_discounts

from school_settings.models import DiscountSettings, StudentDiscount, AcademicYear

@never_cache
@payments_manager_access
def manage_discounts(request):
    """إدارة الخصومات - مع استخدام DiscountSettings"""
    user_role = get_user_role(request.user)
    permissions = get_payment_permissions(request.user)
    
    # معالجة إضافة خصم جديد
    if request.method == 'POST':
        try:
            student_id = request.POST.get('student_id')
            discount_setting_id = request.POST.get('discount_setting_id')
            original_amount = request.POST.get('original_amount')
            application_reason = request.POST.get('application_reason')
            
            if not all([student_id, discount_setting_id, original_amount, application_reason]):
                return JsonResponse({'success': False, 'message': 'بيانات غير مكتملة'})
            
            student = Student.objects.get(id=student_id)
            discount_setting = DiscountSettings.objects.get(id=discount_setting_id)
            original_amount = Decimal(str(original_amount))
            
            # الحصول على العام الدراسي الحالي
            try:
                current_academic_year = AcademicYear.objects.filter(is_active=True).first()
                if not current_academic_year:
                    return JsonResponse({'success': False, 'message': 'لا يوجد عام دراسي نشط'})
            except Exception:
                return JsonResponse({'success': False, 'message': 'خطأ في العام الدراسي'})
            
            # التحقق من وجود خصم مسبق للطالب
            existing_discount = StudentDiscount.objects.filter(
                student=student,
                discount_setting=discount_setting,
                academic_year=current_academic_year
            ).first()
            
            if existing_discount:
                return JsonResponse({'success': False, 'message': 'الطالب لديه خصم من هذا النوع بالفعل'})
            
            # حساب قيمة الخصم
            applied_amount = discount_setting.calculate_discount(original_amount)
            final_amount = original_amount - applied_amount
            
            if applied_amount <= 0:
                return JsonResponse({'success': False, 'message': 'لا يستحق الطالب خصم بهذا المبلغ'})
            
            # إنشاء خصم الطالب
            student_discount = StudentDiscount.objects.create(
                student=student,
                discount_setting=discount_setting,
                academic_year=current_academic_year,
                applied_amount=applied_amount,
                original_amount=original_amount,
                final_amount=final_amount,
                application_reason=application_reason,
                created_by=request.user,
                status='APPROVED' if not discount_setting.requires_approval else 'PENDING'
            )
            
            status_text = 'وفي انتظار الموافقة' if discount_setting.requires_approval else 'وتم تفعيله'
            
            return JsonResponse({
                'success': True, 
                'message': f'تم إضافة خصم {discount_setting.name} للطالب {student.name} بقيمة {applied_amount} ج.م {status_text}'
            })
            
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'الطالب غير موجود'})
        except DiscountSettings.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'نوع الخصم غير موجود'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'خطأ: {str(e)}'})
    
    # فلترة وبحث الخصومات
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    category = request.GET.get('category', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    student_discounts = StudentDiscount.objects.select_related(
        'student', 'discount_setting', 'academic_year', 'approved_by'
    ).order_by('-created_date')
    
    if search:
        student_discounts = student_discounts.filter(
            Q(student__name__icontains=search) |
            Q(discount_setting__name__icontains=search) |
            Q(application_reason__icontains=search)
        )
    
    if status:
        student_discounts = student_discounts.filter(status=status)
    
    if category:
        student_discounts = student_discounts.filter(discount_setting__category=category)
    
    if date_from:
        try:
            student_discounts = student_discounts.filter(created_date__date__gte=date_from)
        except:
            pass
    
    if date_to:
        try:
            student_discounts = student_discounts.filter(created_date__date__lte=date_to)
        except:
            pass
    
    # حساب إحصائيات الخصومات
    discount_stats = {}
    try:
        approved_discounts = student_discounts.filter(status='APPROVED')
        
        discount_stats = {
            'total_amount': float(approved_discounts.aggregate(Sum('applied_amount'))['applied_amount__sum'] or 0),
            'total_count': student_discounts.count(),
            'approved_count': approved_discounts.count(),
            'pending_count': student_discounts.filter(status='PENDING').count(),
            'avg_amount': float(approved_discounts.aggregate(Avg('applied_amount'))['applied_amount__avg'] or 0),
            'beneficiary_students': approved_discounts.values('student').distinct().count()
        }
    except Exception as e:
        print(f"خطأ في إحصائيات الخصومات: {e}")
        discount_stats = {
            'total_amount': 0,
            'total_count': 0,
            'approved_count': 0,
            'pending_count': 0,
            'avg_amount': 0,
            'beneficiary_students': 0
        }
    
    # الحصول على إعدادات الخصومات النشطة
    available_discount_settings = DiscountSettings.objects.filter(
        is_active=True,
        valid_from_date__lte=timezone.now().date(),
        valid_to_date__gte=timezone.now().date()
    ).order_by('category', 'name')
    
    # فئات الخصومات للفلترة
    discount_categories = DiscountSettings.DISCOUNT_CATEGORY_CHOICES
    
    # Pagination
    paginator = Paginator(student_discounts, 20)
    page_number = request.GET.get('page')
    
    try:
        discounts_page = paginator.page(page_number)
    except PageNotAnInteger:
        discounts_page = paginator.page(1)
    except EmptyPage:
        discounts_page = paginator.page(paginator.num_pages)
    
    context = {
        'student_discounts': discounts_page,
        'discount_stats': discount_stats,
        'available_discount_settings': available_discount_settings,
        'discount_categories': discount_categories,
        'permissions': permissions,
        'user_role': user_role,
        'page_title': 'إدارة الخصومات'
    }
    
    return render(request, 'payments/manage_discounts.html', context)

# في payments/views.py - إضافة APIs للخصومات

@csrf_protect
@payments_basic_access
def approve_discount_ajax(request, discount_id):
    """API لموافقة على خصم"""
    try:
        student_discount = get_object_or_404(StudentDiscount, id=discount_id)
        
        if student_discount.status != 'PENDING':
            return JsonResponse({'success': False, 'message': 'الخصم ليس في حالة انتظار'})
        
        student_discount.status = 'APPROVED'
        student_discount.approved_by = request.user
        student_discount.approval_date = timezone.now()
        student_discount.save()
        
        return JsonResponse({
            'success': True,
            'message': f'تم الموافقة على خصم {student_discount.discount_setting.name} للطالب {student_discount.student.name}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'خطأ: {str(e)}'})

@csrf_protect
@payments_basic_access
def reject_discount_ajax(request, discount_id):
    """API لرفض خصم"""
    try:
        student_discount = get_object_or_404(StudentDiscount, id=discount_id)
        admin_notes = request.POST.get('admin_notes', '')
        
        if student_discount.status != 'PENDING':
            return JsonResponse({'success': False, 'message': 'الخصم ليس في حالة انتظار'})
        
        student_discount.status = 'REJECTED'
        student_discount.approved_by = request.user
        student_discount.approval_date = timezone.now()
        student_discount.admin_notes = admin_notes
        student_discount.save()
        
        return JsonResponse({
            'success': True,
            'message': f'تم رفض خصم {student_discount.discount_setting.name} للطالب {student_discount.student.name}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'خطأ: {str(e)}'})


# في payments/views.py - إضافة دالة get_discount_details_ajax

@csrf_protect
@payments_basic_access
def get_discount_details_ajax(request, discount_id):
    """API للحصول على تفاصيل خصم محدد"""
    try:
        student_discount = get_object_or_404(
            StudentDiscount.objects.select_related('student', 'discount_setting', 'academic_year', 'approved_by'),
            id=discount_id
        )
        
        # إعداد بيانات التفاصيل
        discount_data = {
            'id': student_discount.id,
            'student_name': student_discount.student.name,
            'student_national_number': student_discount.student.national_number,
            'student_grade': getattr(student_discount.student.grade_level, 'name', 'غير محدد') if hasattr(student_discount.student, 'grade_level') else 'غير محدد',
            'discount_setting_name': student_discount.discount_setting.name,
            'discount_category': student_discount.discount_setting.get_category_display(),
            'discount_type': student_discount.discount_setting.get_discount_type_display(),
            'applied_amount': float(student_discount.applied_amount),
            'original_amount': float(student_discount.original_amount),
            'final_amount': float(student_discount.final_amount),
            'status': student_discount.get_status_display(),
            'status_code': student_discount.status,
            'application_reason': student_discount.application_reason,
            'admin_notes': student_discount.admin_notes,
            'created_date': student_discount.created_date.isoformat(),
            'created_by': student_discount.created_by.get_full_name() or student_discount.created_by.username,
            'academic_year': str(student_discount.academic_year) if student_discount.academic_year else 'غير محدد',
            'approved_by': student_discount.approved_by.get_full_name() if student_discount.approved_by else None,
            'approval_date': student_discount.approval_date.isoformat() if student_discount.approval_date else None,
            
            # تفاصيل إعدادات الخصم
            'discount_setting': {
                'percentage_value': float(student_discount.discount_setting.percentage_value) if student_discount.discount_setting.percentage_value else None,
                'fixed_amount': float(student_discount.discount_setting.fixed_amount) if student_discount.discount_setting.fixed_amount else None,
                'max_discount_amount': float(student_discount.discount_setting.max_discount_amount) if student_discount.discount_setting.max_discount_amount else None,
                'min_payment_amount': float(student_discount.discount_setting.min_payment_amount) if student_discount.discount_setting.min_payment_amount else None,
                'description': student_discount.discount_setting.description,
                'valid_from_date': student_discount.discount_setting.valid_from_date.isoformat(),
                'valid_to_date': student_discount.discount_setting.valid_to_date.isoformat(),
                'requires_approval': student_discount.discount_setting.requires_approval
            }
        }
        
        return JsonResponse({
            'success': True,
            'discount': discount_data
        })
        
    except Exception as e:
        print(f"خطأ في جلب تفاصيل الخصم: {e}")
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ في جلب التفاصيل'
        })


# في payments/views.py - نسخة مبسطة من overdue_payments
# في payments/views.py - overdue_payments محدث مع إعدادات المصاريف

@never_cache
@payments_financial_reports
def overdue_payments(request):
    """صفحة المدفوعات المتأخرة - مع إعدادات المصاريف"""
    from datetime import date, timedelta
    from school_settings.models import SchoolFeesSettings, AcademicYear, SystemSettings
    from decimal import Decimal
    
    user_role = get_user_role(request.user)
    permissions = get_payment_permissions(request.user)
    
    # معاملات البحث والفلترة
    search_query = request.GET.get('search', '').strip()
    overdue_period = request.GET.get('overdue_period', '')
    sort_by = request.GET.get('sort_by', 'overdue_days')
    grade_filter = request.GET.get('grade_filter', '')
    min_amount = request.GET.get('min_amount', '')
    
    today = date.today()
    
    try:
        print(f"DEBUG: بداية معالجة المدفوعات المتأخرة - {today}")
        
        # الحصول على العام الدراسي الحالي
        current_year = AcademicYear.get_current_year()
        if not current_year:
            print("DEBUG: لا يوجد عام دراسي نشط")
            # إنشاء صفحة فارغة
            overdue_payments_page = Paginator([], 25).page(1)
            overdue_stats = {
                'total_overdue_amount': 0,
                'total_overdue_count': 0,
                'severe_overdue_count': 0,
                'moderate_overdue_count': 0,
                'overdue_students_count': 0
            }
        else:
            print(f"DEBUG: العام الدراسي الحالي: {current_year.name}")
            
            # الحصول على الطلاب المسجلين في العام الحالي
            from students.models import Student
            students_query = Student.objects.filter(is_active=True)
            
            # تطبيق فلتر البحث
            if search_query:
                students_query = students_query.filter(
                    Q(name__icontains=search_query) |
                    Q(national_number__icontains=search_query)
                )
                print(f"DEBUG: فلتر البحث: {search_query}, الطلاب: {students_query.count()}")
            
            # تطبيق فلتر الصف
            if grade_filter:
                students_query = students_query.filter(grade_level_id=grade_filter)
                print(f"DEBUG: فلتر الصف: {grade_filter}")
            
            students_query = students_query.select_related('grade_level')
            
            # قوائم لتجميع البيانات
            overdue_list = []
            total_overdue_amount = 0
            severe_count = 0  # أكثر من 30 يوم
            moderate_count = 0  # 7-30 يوم
            mild_count = 0  # 1-7 أيام
            unique_students = set()
            
            # معالجة كل طالب
            for student in students_query:
                try:
                    print(f"DEBUG: معالجة الطالب: {student.name}")
                    
                    # الحصول على إعدادات المصاريف للطالب
                    fees_settings = SchoolFeesSettings.objects.filter(
                        academic_year=current_year,
                        grade_level=student.grade_level,
                        is_active=True
                    )
                    
                    print(f"DEBUG: إعدادات المصاريف للطالب {student.name}: {fees_settings.count()}")
                    
                    # معالجة كل نوع مصروفات
                    for fee_setting in fees_settings:
                        print(f"DEBUG: معالجة مصروفات: {fee_setting.fee_name}")
                        
                        # حساب تواريخ استحقاق الأقساط
                        installment_dates = []
                        current_due_date = fee_setting.first_installment_due_date
                        
                        for i in range(fee_setting.installments_count):
                            installment_dates.append(current_due_date)
                            current_due_date += timedelta(days=fee_setting.installment_interval_days)
                        
                        print(f"DEBUG: تواريخ الاستحقاق: {installment_dates}")
                        
                        # التحقق من كل قسط
                        for installment_num, due_date in enumerate(installment_dates, 1):
                            if due_date >= today:  # تجاهل الأقساط غير المستحقة بعد
                                continue
                            
                            # حساب أيام التأخير
                            overdue_days = (today - due_date).days
                            if overdue_days <= 0:
                                continue
                            
                            # تطبيق فلتر فترة التأخير
                            if overdue_period:
                                if overdue_period == '1-7' and overdue_days > 7:
                                    continue
                                elif overdue_period == '7-30' and (overdue_days <= 7 or overdue_days > 30):
                                    continue
                                elif overdue_period == '30+' and overdue_days <= 30:
                                    continue
                            
                            # البحث عن مدفوعات هذا القسط
                            existing_payments = Tuition.objects.filter(
                                student=student,
                                academic_year=current_year,
                                fee_type=fee_setting.fee_type,
                                installment_number=installment_num,
                                payment_status__in=['PAID', 'PARTIAL']
                            )
                            
                            # حساب المبلغ المدفوع لهذا القسط
                            paid_amount = sum(payment.amount_paid for payment in existing_payments)
                            remaining_amount = fee_setting.installment_amount - paid_amount
                            
                            print(f"DEBUG: القسط {installment_num} - مستحق: {fee_setting.installment_amount}, مدفوع: {paid_amount}, متبقي: {remaining_amount}")
                            
                            # إذا كان هناك مبلغ متبقي
                            if remaining_amount > 0:
                                # تطبيق فلتر المبلغ الأدنى
                                if min_amount:
                                    try:
                                        min_amount_decimal = float(min_amount)
                                        if remaining_amount < min_amount_decimal:
                                            continue
                                    except ValueError:
                                        pass
                                
                                # إنشاء كائن مدفوع متأخر (محاكاة)
                                overdue_payment = type('OverduePayment', (), {
                                    'id': f"{student.id}_{fee_setting.id}_{installment_num}",
                                    'student': student,
                                    'fee_setting': fee_setting,
                                    'installment_number': installment_num,
                                    'due_date': due_date,
                                    'overdue_days': overdue_days,
                                    'amount_tuition': fee_setting.installment_amount,
                                    'amount_paid': paid_amount,
                                    'remaining_amount': remaining_amount,
                                    'payment_status': 'PENDING' if paid_amount == 0 else 'PARTIAL',
                                    'last_reminder_date': None,
                                    'fee_type': fee_setting.fee_type,
                                    'fee_name': fee_setting.fee_name
                                })()
                                
                                # تصنيف حسب شدة التأخير
                                if overdue_days > 30:
                                    severe_count += 1
                                elif overdue_days >= 7:
                                    moderate_count += 1
                                else:
                                    mild_count += 1
                                
                                # إضافة للإحصائيات
                                total_overdue_amount += float(remaining_amount)
                                unique_students.add(student.id)
                                
                                overdue_list.append(overdue_payment)
                                
                                print(f"DEBUG: أضيف مدفوع متأخر: {student.name} - {fee_setting.fee_name} - قسط {installment_num} - {overdue_days} يوم")
                
                except Exception as e:
                    print(f"DEBUG: خطأ في معالجة الطالب {student.name}: {e}")
                    continue
            
            print(f"DEBUG: إجمالي المدفوعات المتأخرة: {len(overdue_list)}")
            
            # ترتيب النتائج
            if sort_by == 'overdue_days':
                overdue_list.sort(key=lambda x: x.overdue_days, reverse=True)
            elif sort_by == 'amount':
                overdue_list.sort(key=lambda x: x.remaining_amount, reverse=True)
            elif sort_by == 'student_name':
                overdue_list.sort(key=lambda x: x.student.name)
            elif sort_by == 'due_date':
                overdue_list.sort(key=lambda x: x.due_date)
            
            # إعداد الإحصائيات
            overdue_stats = {
                'total_overdue_amount': total_overdue_amount,
                'total_overdue_count': len(overdue_list),
                'severe_overdue_count': severe_count,
                'moderate_overdue_count': moderate_count,
                'mild_overdue_count': mild_count,
                'overdue_students_count': len(unique_students)
            }
            
            print(f"DEBUG: الإحصائيات النهائية: {overdue_stats}")
            
            # Pagination
            paginator = Paginator(overdue_list, 25)
            page_number = request.GET.get('page')
            
            try:
                overdue_payments_page = paginator.page(page_number)
            except PageNotAnInteger:
                overdue_payments_page = paginator.page(1)
            except EmptyPage:
                overdue_payments_page = paginator.page(paginator.num_pages)
        
        # الحصول على قائمة الصفوف للفلتر
        from school_settings.models import GradeLevel
        available_grades = GradeLevel.objects.filter(is_active=True).order_by('education_level__order', 'order')
        
    except Exception as e:
        print(f"DEBUG: خطأ عام في المدفوعات المتأخرة: {e}")
        import traceback
        traceback.print_exc()
        
        # قيم افتراضية في حالة الخطأ
        overdue_payments_page = Paginator([], 25).page(1)
        overdue_stats = {
            'total_overdue_amount': 0,
            'total_overdue_count': 0,
            'severe_overdue_count': 0,
            'moderate_overdue_count': 0,
            'mild_overdue_count': 0,
            'overdue_students_count': 0
        }
        available_grades = []
    
    context = {
        'overdue_payments': overdue_payments_page,
        'overdue_stats': overdue_stats,
        'available_grades': available_grades,
        'permissions': permissions,
        'user_role': user_role,
        'page_title': 'المدفوعات المتأخرة',
        # إضافة متغيرات للفلاتر
        'search_query': search_query,
        'overdue_period': overdue_period,
        'sort_by': sort_by,
        'grade_filter': grade_filter,
        'min_amount': min_amount,
        'current_year': current_year,
    }
    
    return render(request, 'payments/overdue_payments.html', context)

# في payments/views.py - إضافة APIs للبيانات الحقيقية

# في payments/views.py - تأكد من وجود جميع هذه الدوال

@csrf_protect
@require_GET  
@payments_basic_access
def student_contact_details_api(request, student_id):
    """API للحصول على بيانات اتصال الطالب"""
    try:
        from students.models import Student
        
        student = Student.objects.select_related('grade_level').get(
            id=student_id, 
            is_active=True
        )
        
        student_data = {
            'id': student.id,
            'name': student.name,
            'national_number': student.national_number,
            'grade_name': student.grade_name,
            'age_display': student.get_age_display(),
            'phone_number': student.phone_number or '',
            'parent_name': student.parent_name or '',
            'parent_phone': student.parent_phone or '',
            'parent_email': student.parent_email or '',
            'address': student.address or '',
        }
        
        return JsonResponse({
            'success': True,
            'student': student_data
        })
        
    except Student.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'الطالب غير موجود'
        })
    except Exception as e:
        print(f"خطأ في جلب بيانات الطالب: {e}")
        return JsonResponse({
            'success': False,
            'message': 'حدث خطأ في جلب البيانات'
        })


@csrf_protect
@require_GET
@payments_basic_access  
def student_payment_history_api(request, student_id):
    """API لجلب تاريخ مدفوعات الطالب"""
    try:
        from students.models import Student
        from school_settings.models import AcademicYear
        from datetime import date
        
        student = Student.objects.get(id=student_id, is_active=True)
        current_year = AcademicYear.get_current_year()
        today = date.today()
        
        # جلب جميع المدفوعات للطالب
        payments = Tuition.objects.filter(
            student=student,
            academic_year=current_year
        ).order_by('installment_number')
        
        history = []
        summary = {
            'total_installments': 0,
            'paid_installments': 0,
            'overdue_installments': 0,
            'upcoming_installments': 0,
            'total_paid': 0,
            'total_overdue': 0,
            'total_upcoming': 0
        }
        
        for payment in payments:
            overdue_days = 0
            status = 'UPCOMING'
            
            if payment.due_date:
                if payment.due_date < today:
                    overdue_days = (today - payment.due_date).days
                    if payment.payment_status == 'PAID':
                        status = 'PAID'
                    else:
                        status = 'OVERDUE'
                elif payment.payment_status == 'PAID':
                    status = 'PAID'
                else:
                    status = 'PENDING'
            
            payment_data = {
                'installment_number': payment.installment_number,
                'fee_name': 'مصروفات دراسية',  # يمكن تحسينها
                'amount': float(payment.amount_tuition),
                'due_date': payment.due_date.strftime('%d %B %Y') if payment.due_date else '-',
                'payment_date': payment.payment_date.strftime('%d %B %Y') if payment.payment_date else None,
                'status': status,
                'overdue_days': overdue_days if status == 'OVERDUE' else 0
            }
            
            history.append(payment_data)
            
            # تحديث الملخص
            summary['total_installments'] += 1
            if status == 'PAID':
                summary['paid_installments'] += 1
                summary['total_paid'] += float(payment.amount_paid)
            elif status == 'OVERDUE':
                summary['overdue_installments'] += 1
                summary['total_overdue'] += float(payment.amount_tuition - payment.amount_paid)
            else:
                summary['upcoming_installments'] += 1
                summary['total_upcoming'] += float(payment.amount_tuition)
        
        return JsonResponse({
            'success': True,
            'history': history,
            'summary': summary
        })
        
    except Student.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'الطالب غير موجود'
        })
    except Exception as e:
        print(f"خطأ في جلب تاريخ المدفوعات: {e}")
        return JsonResponse({
            'success': False,
            'message': 'حدث خطأ في جلب التاريخ'
        })

@csrf_protect
@require_GET
@payments_basic_access
def student_details_api(request, student_id):
    """API للحصول على تفاصيل الطالب"""
    try:
        from students.models import Student
        
        student = Student.objects.select_related('grade_level').get(
            id=student_id, 
            is_active=True
        )
        
        student_data = {
            'id': student.id,
            'name': student.name,
            'national_number': student.national_number,
            'grade_name': student.grade_name,
            'phone_number': student.phone_number,
            'parent_phone': student.parent_phone,
            'parent_email': student.parent_email,
        }
        
        return JsonResponse({
            'success': True,
            'student': student_data
        })
        
    except Student.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'الطالب غير موجود'
        })
    except Exception as e:
        print(f"خطأ في جلب تفاصيل الطالب: {e}")
        return JsonResponse({
            'success': False,
            'message': 'حدث خطأ في جلب البيانات'
        })


@never_cache
@payments_admin_access
def payment_settings(request):
    """إعدادات المدفوعات"""
    context = {
        'page_title': 'إعدادات المدفوعات',
        'permissions': get_payment_permissions(request.user),
    }
    return render(request, 'payments/payment_settings.html', context)

@never_cache
@payments_basic_access
def user_guide(request):
    """دليل الاستخدام"""
    context = {
        'page_title': 'دليل الاستخدام',
        'permissions': get_payment_permissions(request.user),
    }
    return render(request, 'payments/user_guide.html', context)

@never_cache
@payments_basic_access
def payment_calculator(request):
    """حاسبة المدفوعات"""
    context = {
        'page_title': 'حاسبة المدفوعات',
        'permissions': get_payment_permissions(request.user),
    }
    return render(request, 'payments/payment_calculator.html', context)

@never_cache
@payments_basic_access
def technical_support(request):
    """الدعم الفني"""
    context = {
        'page_title': 'الدعم الفني',
        'permissions': get_payment_permissions(request.user),
    }
    return render(request, 'payments/technical_support.html', context)


# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.views.decorators.cache import never_cache
# from django.views.decorators.csrf import csrf_protect
# from django.views.decorators.http import require_POST
# from django.http import JsonResponse
# from django.db.models import Q
# from django.utils import timezone
# from decimal import Decimal
# from students.models import Student
# from .models import Tuition
# # من الملف الأصلي - استيراد النماذج الموجودة
# try:
#     from .forms import TuitionForm
# except ImportError:
#     # إذا لم تكن النماذج موجودة بعد، سنستخدم النماذج الأساسية
#     from django import forms
    
#     class TuitionForm(forms.ModelForm):
#         class Meta:
#             model = Tuition
#             fields = ['installment_number', 'amount_tuition', 'amount_paid']


# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.views.decorators.cache import never_cache
# from django.views.decorators.csrf import csrf_protect
# from django.views.decorators.http import require_POST
# from django.http import JsonResponse
# from django.db.models import Q, Sum
# from django.utils import timezone
# from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# from decimal import Decimal
# from students.models import Student
# from .models import Tuition

# @never_cache
# @login_required
# def payments_home(request):
#     """الصفحة الرئيسية لموظف الحسابات مع Pagination"""
#     from students.models import Student
    
#     # إحصائيات بسيطة
#     try:
#         total_payments_today = Tuition.objects.filter(
#             payment_date__date=timezone.now().date(),
#             payment_status='PAID'
#         ).count()
        
#         total_amount_today = Tuition.objects.filter(
#             payment_date__date=timezone.now().date(),
#             payment_status='PAID'
#         ).aggregate(total=Sum('amount_paid'))['total'] or 0
        
#     except:
#         total_payments_today = 0
#         total_amount_today = 0
    
#     try:
#         total_overdue = Tuition.objects.filter(payment_status='OVERDUE').count()
#     except:
#         total_overdue = 0
    
#     try:
#         receipts_today = Tuition.objects.filter(
#             payment_date__date=timezone.now().date(),
#             payment_status='PAID'
#         ).count()
#     except:
#         receipts_today = 0
    
#     try:
#         total_students = Student.objects.count()
#     except:
#         total_students = 0
    
#     # جلب المدفوعات مع Pagination
#     try:
#         payments_list = Tuition.objects.filter(
#             payment_status='PAID'
#         ).select_related('student').order_by('-payment_date')
        
#         # إعداد Pagination
#         paginator = Paginator(payments_list, 10)  # 10 عناصر لكل صفحة
#         page_number = request.GET.get('page')
        
#         try:
#             recent_payments = paginator.page(page_number)
#         except PageNotAnInteger:
#             recent_payments = paginator.page(1)
#         except EmptyPage:
#             recent_payments = paginator.page(paginator.num_pages)
            
#     except:
#         recent_payments = []
    
#     context = {
#         'total_payments_today': total_payments_today,
#         'total_amount_today': total_amount_today,
#         'total_overdue': total_overdue,
#         'receipts_today': receipts_today,
#         'total_students': total_students,
#         'recent_payments': recent_payments,
#         'today': timezone.now().date(),
#         'page_title': 'لوحة تحكم المدفوعات'
#     }
#     return render(request, 'payments/payments_home.html', context)


# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.views.decorators.cache import never_cache
# from django.views.decorators.csrf import csrf_protect
# from django.views.decorators.http import require_POST
# from django.http import JsonResponse
# from django.db.models import Q, Sum
# from django.utils import timezone
# from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# from decimal import Decimal
# from students.models import Student
# from .models import Tuition

# # ... باقي الدوال الموجودة ...

# def get_student_payments_ajax(request):
#     """عرض أقساط طالب محدد عبر Ajax"""
#     if request.method == 'GET':
#         student_id = request.GET.get('student_id')
        
#         if not student_id:
#             return JsonResponse({'error': 'معرف الطالب غير محدد'})
        
#         try:
#             student = Student.objects.get(id=student_id)
#             payments = Tuition.objects.filter(student=student).order_by('-installment_number')
            
#             payments_data = []
#             for payment in payments:
#                 payments_data.append({
#                     'id': payment.id,
#                     'installment_number': payment.installment_number,
#                     'amount_tuition': float(payment.amount_tuition),
#                     'amount_paid': float(payment.amount_paid),
#                     'payment_status': payment.payment_status,
#                     'payment_date': payment.payment_date.strftime('%Y-%m-%d %H:%M') if payment.payment_date else None,
#                     'due_date': payment.due_date.strftime('%Y-%m-%d') if payment.due_date else None,
#                     'payment_method': payment.payment_method,
#                     'payment_user': payment.payment_user,
#                     'remaining_amount': float(payment.remaining_amount) if hasattr(payment, 'remaining_amount') else 0
#                 })
            
#             return JsonResponse({
#                 'student_name': student.name,
#                 'payments': payments_data,
#                 'total_payments': len(payments_data)
#             })
            
#         except Student.DoesNotExist:
#             return JsonResponse({'error': 'الطالب غير موجود'})
#         except Exception as e:
#             return JsonResponse({'error': f'حدث خطأ: {str(e)}'})
    
#     return JsonResponse({'error': 'طريقة طلب غير صحيحة'})


# @never_cache
# @login_required
# def all_payments(request):
#     """صفحة جميع المدفوعات مع البحث والفلترة والإحصائيات الشاملة"""
#     from django.db.models import Sum, Count, Avg
    
#     # البحث والفلترة
#     search_query = request.GET.get('search', '')
#     status_filter = request.GET.get('status', '')
#     date_from = request.GET.get('date_from', '')
#     date_to = request.GET.get('date_to', '')
#     payment_method_filter = request.GET.get('payment_method', '')
#     payment_user_filter = request.GET.get('payment_user', '')
    
#     payments = Tuition.objects.select_related('student').order_by('-payment_date')
    
#     if search_query:
#         payments = payments.filter(
#             Q(student__name__icontains=search_query) |
#             Q(student__national_number__icontains=search_query) |
#             Q(installment_number__icontains=search_query)
#         )
    
#     if status_filter:
#         payments = payments.filter(payment_status=status_filter)
        
#     if date_from:
#         payments = payments.filter(payment_date__date__gte=date_from)
        
#     if date_to:
#         payments = payments.filter(payment_date__date__lte=date_to)
        
#     if payment_method_filter:
#         payments = payments.filter(payment_method=payment_method_filter)
        
#     if payment_user_filter:
#         payments = payments.filter(payment_user__icontains=payment_user_filter)
    
#     # حساب الإحصائيات
#     try:
#         stats = payments.aggregate(
#             total_amount=Sum('amount_paid'),
#             total_count=Count('id'),
#             avg_payment=Avg('amount_paid')
#         )
        
#         # إحصائيات حسب طريقة الدفع
#         payment_methods_stats = payments.values('payment_method').annotate(
#             count=Count('id'),
#             amount=Sum('amount_paid')
#         ).order_by('-amount')
        
#         # إحصائيات حسب الحالة
#         status_stats = payments.values('payment_status').annotate(
#             count=Count('id'),
#             amount=Sum('amount_paid')
#         ).order_by('-count')
        
#         # إحصائيات حسب الموظف
#         user_stats = payments.values('payment_user').annotate(
#             count=Count('id'),
#             amount=Sum('amount_paid')
#         ).order_by('-amount')[:5]  # أفضل 5 موظفين
        
#         # إحصائيات شهرية (آخر 6 شهور)
#         from django.utils import timezone
#         from datetime import timedelta
#         six_months_ago = timezone.now() - timedelta(days=180)
        
#         monthly_stats = payments.filter(
#             payment_date__gte=six_months_ago
#         ).extra(
#             select={'month': "DATE_FORMAT(payment_date, '%%Y-%%m')"}
#         ).values('month').annotate(
#             count=Count('id'),
#             amount=Sum('amount_paid')
#         ).order_by('month')
        
#     except Exception as e:
#         stats = {'total_amount': 0, 'total_count': 0, 'avg_payment': 0}
#         payment_methods_stats = []
#         status_stats = []
#         user_stats = []
#         monthly_stats = []
    
#     # Pagination
#     paginator = Paginator(payments, 20)  # 20 عنصر لكل صفحة
#     page_number = request.GET.get('page')
    
#     try:
#         payments_page = paginator.page(page_number)
#     except PageNotAnInteger:
#         payments_page = paginator.page(1)
#     except EmptyPage:
#         payments_page = paginator.page(paginator.num_pages)
    
#     # قائمة الموظفين المتاحين للفلترة
#     available_users = Tuition.objects.values_list('payment_user', flat=True).distinct()
#     available_users = [user for user in available_users if user and user.strip()]
    
#     context = {
#         'payments': payments_page,
#         'search_query': search_query,
#         'status_filter': status_filter,
#         'date_from': date_from,
#         'date_to': date_to,
#         'payment_method_filter': payment_method_filter,
#         'payment_user_filter': payment_user_filter,
#         'available_users': available_users,
#         'stats': stats,
#         'payment_methods_stats': payment_methods_stats,
#         'status_stats': status_stats,
#         'user_stats': user_stats,
#         'monthly_stats': monthly_stats,
#         'page_title': 'جميع المدفوعات'
#     }
#     return render(request, 'payments/all_payments.html', context)



# @never_cache
# @login_required
# def pay_installment(request, pk):
#     """دفع قسط لطالب محدد"""
#     user = request.user
#     student = get_object_or_404(Student, pk=pk)
    
#     if request.method == 'POST':
#         installment_form = TuitionForm(request.POST)
#         if installment_form.is_valid():
#             installment = installment_form.save(commit=False)
#             installment.student = student
#             installment.payment_user = user.get_full_name() or user.username
#             installment.payment_status = 'PAID'
#             installment.payment_date = timezone.now()
#             installment.save()
            
#             messages.success(request, 'تم دفع القسط بنجاح!')
#             return redirect('students:student_detail', pk=pk)
#     else:
#         installment_form = TuitionForm()

#     context = {
#         'student': student,
#         'installment_form': installment_form,
#         'page_title': f'دفع قسط للطالب {student.name}'
#     }
#     return render(request, 'payments/pay_installment.html', context)


# def student_search_ajax(request):
#     """البحث عن الطلاب عبر Ajax للمدفوعات"""
#     if request.method == 'GET':
#         query = request.GET.get('q', '')
#         students = []
        
#         if len(query) >= 2:
#             try:
#                 student_list = Student.objects.filter(
#                     Q(name__icontains=query) | 
#                     Q(national_number__icontains=query)
#                 )[:10]
                
#                 for student in student_list:
#                     # حساب المستحق بطريقة آمنة
#                     try:
#                         total_owed = student.calculate_total_owed() if hasattr(student, 'calculate_total_owed') else 0
#                     except:
#                         total_owed = 0
                    
#                     students.append({
#                         'id': student.id,
#                         'name': student.name,
#                         'national_number': student.national_number,
#                         'classroom': ', '.join([classroom.name for classroom in student.classroom.all()]),
#                         'total_owed': float(total_owed),
#                         'phone_number': student.phone_number or 'غير محدد'
#                     })
#             except Exception as e:
#                 return JsonResponse({'error': f'خطأ في البحث: {str(e)}'})
        
#         return JsonResponse({'students': students})
    
#     return JsonResponse({'error': 'طريقة طلب غير صحيحة'})


# @csrf_protect
# @require_POST
# @login_required
# def record_payment_ajax(request):
#     """تسجيل دفع قسط عبر Ajax - محسن لتجنب التكرار"""
#     try:
#         student_id = request.POST.get('student_id')
#         amount_paid = Decimal(request.POST.get('amount_paid', '0'))
#         payment_method = request.POST.get('payment_method', 'cash')
#         notes = request.POST.get('notes', '')

#         if not student_id:
#             return JsonResponse({'success': False, 'message': 'الطالب غير محدد'})

#         if amount_paid <= 0:
#             return JsonResponse({'success': False, 'message': 'يجب إدخال مبلغ أكبر من صفر'})

#         student = Student.objects.get(id=student_id)

#         # البحث عن آخر رقم قسط للطالب
#         last_installment = Tuition.objects.filter(student=student).order_by('-installment_number').first()
        
#         if last_installment:
#             next_installment_number = last_installment.installment_number + 1
#         else:
#             next_installment_number = 1

#         # إنشاء قسط جديد
#         tuition = Tuition.objects.create(
#             student=student,
#             installment_number=next_installment_number,
#             amount_tuition=amount_paid,
#             amount_paid=amount_paid,
#             payment_status='PAID',
#             payment_date=timezone.now(),
#             due_date=timezone.now().date(),  # تاريخ الاستحقاق نفس تاريخ الدفع للمدفوعات الفورية
#             payment_method=payment_method,
#             payment_user=request.user.get_full_name() or request.user.username,
#             notes=notes
#         )

#         # تحديث إجماليات الطالب (إذا كانت الحقول موجودة)
#         try:
#             if hasattr(student, 'total_payments'):
#                 student.total_payments = (student.total_payments or 0) + amount_paid
#                 student.save()
#         except Exception as e:
#             print(f"خطأ في تحديث إجماليات الطالب: {e}")

#         return JsonResponse({
#             'success': True,
#             'message': 'تم تسجيل الدفع بنجاح',
#             'student_name': student.name,
#             'total_paid': float(amount_paid),
#             'installment_number': next_installment_number,
#             'payment_user': request.user.get_full_name() or request.user.username
#         })

#     except Student.DoesNotExist:
#         return JsonResponse({'success': False, 'message': 'الطالب غير موجود'})
#     except Exception as e:
#         print(f"خطأ في تسجيل الدفع: {e}")
#         return JsonResponse({'success': False, 'message': f'حدث خطأ: {str(e)}'})


# @never_cache
# @login_required
# def receipt(request, pk):
#     """طباعة إيصال الدفع"""
#     tuition = get_object_or_404(Tuition, pk=pk)
#     student = tuition.student
    
#     if tuition.payment_status != 'PAID':
#         messages.warning(request, 'هذا القسط لم يتم دفعه بعد.')
#         return redirect('students:student_detail', pk=student.pk)
    
#     context = {
#         'tuition': tuition,
#         'student': student,
#         'today': timezone.now(),
#         'page_title': f'إيصال دفع - {student.name}'
#     }
#     return render(request, 'payments/receipt.html', context)



# @never_cache
# @login_required
# def delete_installment(request, pk):
#     """حذف قسط"""
#     tuition = get_object_or_404(Tuition, pk=pk)
    
#     if request.method == 'POST':
#         student_pk = tuition.student.pk
#         tuition.delete()
#         messages.success(request, 'تم حذف القسط بنجاح!')
#         return redirect('students:student_detail', pk=student_pk)
    
#     context = {
#         'tuition': tuition,
#         'page_title': 'حذف قسط'
#     }
#     return render(request, 'payments/delete_installment.html', context)


# def student_search_ajax(request):
#     """البحث عن الطلاب عبر Ajax للمدفوعات"""
#     if request.method == 'GET':
#         query = request.GET.get('q', '').strip()
        
#         # إرجاع استجابة فارغة إذا كان الاستعلام قصير جداً
#         if len(query) < 2:
#             return JsonResponse({'students': []})
        
#         students = []
        
#         try:
#             # البحث في قاعدة البيانات
#             student_list = Student.objects.filter(
#                 Q(name__icontains=query) | 
#                 Q(national_number__icontains=query)
#             )[:10]  # أول 10 نتائج فقط
            
#             for student in student_list:
#                 # حساب المستحق بطريقة آمنة
#                 try:
#                     if hasattr(student, 'calculate_total_owed'):
#                         total_owed = student.calculate_total_owed()
#                     else:
#                         # حساب بسيط إذا لم تكن الدالة موجودة
#                         total_owed = float(student.total_owed or 0)
#                 except Exception as e:
#                     print(f"خطأ في حساب المستحق للطالب {student.name}: {e}")
#                     total_owed = 0
                
#                 # الحصول على أسماء الفصول
#                 try:
#                     classroom_names = [classroom.name for classroom in student.classroom.all()]
#                     classroom_text = ', '.join(classroom_names) if classroom_names else 'غير محدد'
#                 except:
#                     classroom_text = 'غير محدد'
                
#                 students.append({
#                     'id': student.id,
#                     'name': student.name,
#                     'national_number': str(student.national_number),
#                     'classroom': classroom_text,
#                     'total_owed': float(total_owed),
#                     'phone_number': student.phone_number or 'غير محدد'
#                 })
        
#         except Exception as e:
#             print(f"خطأ في البحث: {e}")
#             return JsonResponse({
#                 'error': f'خطأ في البحث: {str(e)}',
#                 'students': []
#             })
        
#         return JsonResponse({'students': students})
    
#     return JsonResponse({'error': 'طريقة طلب غير صحيحة'})