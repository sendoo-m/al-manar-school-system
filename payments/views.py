# payments/views.py
# منظم مع الصلاحيات

import csv
import io
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum, Count, Avg, Min, Max
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from students.models import Student

from .decorators import (
    payments_basic_access,
    payments_full_access,
    payments_manager_access,
    payments_admin_access,
    payments_sensitive_operation,
    payments_financial_reports,
)

from .forms import (
    TuitionForm,
    PaymentRecordForm,
    QuickPaymentForm,
    PaymentSearchForm,
    DiscountForm,
    BulkPaymentForm,
)

from .models import (
    Tuition,
    PaymentRecord,
    Discount,
    PaymentSettings,
)

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

def update_student_financial_totals(student):
    """تحديث إجماليات الطالب المالية بناءً على الأقساط غير الملغاة"""
    if not student:
        return False

    try:
        installments = Tuition.objects.filter(
            student=student
        ).exclude(
            payment_status='CANCELLED'
        )

        totals = installments.aggregate(
            total_fees=Sum('amount_tuition'),
            total_payments=Sum('amount_paid'),
        )

        total_fees = totals['total_fees'] or Decimal('0.00')
        total_payments = totals['total_payments'] or Decimal('0.00')
        total_owed = max(Decimal('0.00'), total_fees - total_payments)

        student.total_fees = total_fees
        student.total_payments = total_payments
        student.total_owed = total_owed

        student.save(update_fields=[
            'total_fees',
            'total_payments',
            'total_owed',
        ])

        return True

    except Exception as e:
        print(f"خطأ في تحديث إجماليات الطالب المالية: {e}")
        return False


def recalculate_all_students_financial_totals():
    """إعادة حساب إجماليات كل الطلاب النشطين"""
    students = Student.objects.filter(is_active=True)
    updated_count = 0
    failed_count = 0

    for student in students:
        success = update_student_financial_totals(student)

        if success:
            updated_count += 1
        else:
            failed_count += 1

    return {
        'updated_count': updated_count,
        'failed_count': failed_count,
        'total_count': students.count(),
    }

def calculate_payment_stats():
    """حساب إحصائيات لوحة المدفوعات"""
    today = timezone.now().date()
    month_start = today.replace(day=1)

    paid_payments = Tuition.objects.filter(
        payment_status='PAID'
    )

    today_paid = paid_payments.filter(
        payment_date__date=today
    )

    month_paid = paid_payments.filter(
        payment_date__date__gte=month_start
    )

    pending_payments = Tuition.objects.filter(
        payment_status='PENDING'
    )

    partial_payments = Tuition.objects.filter(
        payment_status='PARTIALLY_PAID'
    )

    overdue_payments = Tuition.objects.filter(
        payment_status='OVERDUE'
    )

    total_today_amount = today_paid.aggregate(
        total=Sum('amount_paid')
    )['total'] or Decimal('0.00')

    total_month_amount = month_paid.aggregate(
        total=Sum('amount_paid')
    )['total'] or Decimal('0.00')

    total_paid_amount = paid_payments.aggregate(
        total=Sum('amount_paid')
    )['total'] or Decimal('0.00')

    total_required_amount = Tuition.objects.exclude(
        payment_status='CANCELLED'
    ).aggregate(
        total=Sum('amount_tuition')
    )['total'] or Decimal('0.00')

    total_remaining_amount = max(
        Decimal('0.00'),
        total_required_amount - total_paid_amount
    )

    return {
        'today_payments_count': today_paid.count(),
        'today_amount': total_today_amount,

        'month_payments_count': month_paid.count(),
        'month_amount': total_month_amount,

        'total_paid_count': paid_payments.count(),
        'total_paid_amount': total_paid_amount,

        'total_required_amount': total_required_amount,
        'total_remaining_amount': total_remaining_amount,

        'total_pending': pending_payments.count(),
        'total_partial': partial_payments.count(),
        'total_overdue': overdue_payments.count(),

        'total_students_with_payments': Tuition.objects.values(
            'student'
        ).distinct().count(),

        'collection_percentage': (
            total_paid_amount / total_required_amount * 100
        ) if total_required_amount > 0 else 0,
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

    today = timezone.now().date()

    # أحدث المدفوعات
    recent_payments_qs = Tuition.objects.filter(
        amount_paid__gt=0
    ).exclude(
        payment_status='CANCELLED'
    ).select_related(
        'student',
        'student__grade_level',
        'student__grade_level__education_level',
        'academic_year',
    ).order_by(
        '-payment_date',
        '-created_date'
    )

    paginator = Paginator(recent_payments_qs, 10)
    page_number = request.GET.get('page')

    try:
        recent_payments = paginator.page(page_number)
    except PageNotAnInteger:
        recent_payments = paginator.page(1)
    except EmptyPage:
        recent_payments = paginator.page(paginator.num_pages)

    # المتأخرات
    overdue_payments = Tuition.objects.filter(
        payment_status='OVERDUE'
    ).select_related(
        'student',
        'student__grade_level',
        'student__grade_level__education_level',
        'academic_year',
    ).order_by(
        'due_date',
        'student__name'
    )[:10]

    # مدفوعات اليوم حسب طريقة الدفع
    payment_methods_stats = Tuition.objects.filter(
        amount_paid__gt=0,
        payment_date__date=today
    ).exclude(
        payment_status='CANCELLED'
    ).values(
        'payment_method'
    ).annotate(
        count=Count('id'),
        amount=Sum('amount_paid')
    ).order_by(
        '-amount'
    )

    # أفضل المحصلين اليوم
    collectors_stats = Tuition.objects.filter(
        amount_paid__gt=0,
        payment_date__date=today
    ).exclude(
        payment_status='CANCELLED'
    ).values(
        'payment_user'
    ).annotate(
        count=Count('id'),
        amount=Sum('amount_paid')
    ).order_by(
        '-amount'
    )[:5]

    # طلاب عليهم متبقي جزئي
    partial_payments = Tuition.objects.filter(
        payment_status='PARTIALLY_PAID'
    ).select_related(
        'student',
        'student__grade_level',
        'academic_year',
    ).order_by(
        '-updated_date'
    )[:10]

    context = {
        'stats': stats,
        'recent_payments': recent_payments,
        'overdue_payments': overdue_payments,
        'partial_payments': partial_payments,
        'payment_methods_stats': payment_methods_stats,
        'collectors_stats': collectors_stats,

        'permissions': permissions,
        'user_role': user_role,
        'today': today,
        'page_title': 'لوحة تحكم المدفوعات',
    }

    return render(request, 'payments/payments_home.html', context)

# ===================================
# 💰 إدارة المدفوعات
# ===================================
# في payments/views.py - تحديث all_payments view

@never_cache
@payments_basic_access
def all_payments(request):
    """عرض كل المدفوعات والأقساط مع البحث والفلاتر"""
    user_role = get_user_role(request.user)
    permissions = get_payment_permissions(request.user)

    search_query = request.GET.get('search', '').strip()
    payment_status = request.GET.get('payment_status', '').strip()
    fee_type = request.GET.get('fee_type', '').strip()
    payment_method = request.GET.get('payment_method', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    payments_qs = Tuition.objects.select_related(
        'student',
        'student__grade_level',
        'student__grade_level__education_level',
        'academic_year',
    ).order_by(
        '-payment_date',
        '-created_date'
    )

    if search_query:
        payments_qs = payments_qs.filter(
            Q(student__name__icontains=search_query) |
            Q(student__national_number__icontains=search_query) |
            Q(student__phone_number__icontains=search_query) |
            Q(receipt_number__icontains=search_query) |
            Q(payment_user__icontains=search_query)
        )

    if payment_status:
        payments_qs = payments_qs.filter(payment_status=payment_status)

    if fee_type:
        payments_qs = payments_qs.filter(fee_type=fee_type)

    if payment_method:
        payments_qs = payments_qs.filter(payment_method=payment_method)

    if date_from:
        try:
            parsed_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            payments_qs = payments_qs.filter(payment_date__date__gte=parsed_from)
        except ValueError:
            messages.warning(request, 'تاريخ البداية غير صحيح وتم تجاهله')

    if date_to:
        try:
            parsed_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            payments_qs = payments_qs.filter(payment_date__date__lte=parsed_to)
        except ValueError:
            messages.warning(request, 'تاريخ النهاية غير صحيح وتم تجاهله')

    summary = payments_qs.exclude(
        payment_status='CANCELLED'
    ).aggregate(
        total_required=Sum('amount_tuition'),
        total_paid=Sum('amount_paid'),
        count=Count('id'),
    )

    total_required = summary['total_required'] or Decimal('0.00')
    total_paid = summary['total_paid'] or Decimal('0.00')
    total_remaining = max(Decimal('0.00'), total_required - total_paid)

    paginator = Paginator(payments_qs, 25)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'payments': page_obj,
        'page_obj': page_obj,

        'search_query': search_query,
        'selected_payment_status': payment_status,
        'selected_fee_type': fee_type,
        'selected_payment_method': payment_method,
        'date_from': date_from,
        'date_to': date_to,

        'payment_status_choices': Tuition.PAYMENT_STATUS_CHOICES,
        'fee_type_choices': Tuition.FEE_TYPE_CHOICES,
        'payment_method_choices': Tuition.PAYMENT_METHOD_CHOICES,

        'total_required': total_required,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'filtered_count': summary['count'] or 0,

        'permissions': permissions,
        'user_role': user_role,
        'title': 'كل المدفوعات',
    }

    return render(request, 'payments/all_payments.html', context)

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



# @never_cache
# @payments_full_access
# def pay_installment(request, pk):
#     """دفع قسط لطالب محدد مع ربط المصروفات من school_settings"""
#     user_role = get_user_role(request.user)
#     permissions = get_payment_permissions(request.user)
#     student = get_object_or_404(Student, pk=pk)
    
#     # استيراد نماذج الإعدادات من التطبيق الصحيح
#     try:
#         from school_settings.models import SchoolFeesSettings, AcademicYear, StudentDiscount
#     except ImportError:
#         messages.error(request, 'لا يمكن الوصول لإعدادات المصروفات')
#         return redirect('payments:all_payments')
    
#     # الحصول على العام الدراسي الحالي
#     current_year = AcademicYear.get_current_year()
#     if not current_year:
#         messages.warning(request, 'لا يوجد عام دراسي نشط. يرجى إعداد العام الدراسي في الإعدادات')
#         current_year = None
    
#     # الحصول على المصروفات المستحقة للطالب
#     student_fees = []
#     available_discounts = []
    
#     if current_year and hasattr(student, 'grade_level'):
#         try:
#             # المصروفات المستحقة حسب الصف والعام الدراسي
#             fees_settings = SchoolFeesSettings.objects.filter(
#                 academic_year=current_year,
#                 grade_level=student.grade_level,
#                 is_active=True
#             ).order_by('fee_type')
            
#             for fee_setting in fees_settings:
#                 # التحقق من المدفوعات السابقة لهذا النوع من المصروفات
#                 existing_payments = Tuition.objects.filter(
#                     student=student,
#                     fee_type=fee_setting.fee_type,
#                     academic_year=current_year
#                 ).aggregate(
#                     total_paid=Sum('amount_paid'),
#                     installments_count=Count('id')
#                 )
                
#                 total_paid = float(existing_payments['total_paid'] or 0)
#                 remaining_amount = float(fee_setting.total_amount) - total_paid
                
#                 if remaining_amount > 0:
#                     student_fees.append({
#                         'setting': fee_setting,
#                         'total_amount': float(fee_setting.total_amount),
#                         'installment_amount': float(fee_setting.installment_amount),
#                         'total_paid': total_paid,
#                         'remaining_amount': remaining_amount,
#                         'installments_paid': existing_payments['installments_count'] or 0,
#                         'installments_remaining': fee_setting.installments_count - (existing_payments['installments_count'] or 0)
#                     })
            
#             # الحصول على الخصومات المتاحة للطالب
#             available_discounts = StudentDiscount.objects.filter(
#                 student=student,
#                 academic_year=current_year,
#                 status='APPROVED'
#             ).select_related('discount_setting')
            
#         except Exception as e:
#             print(f"خطأ في جلب المصروفات: {e}")
#             messages.warning(request, 'حدث خطأ في جلب المصروفات المستحقة')
    
#     if request.method == 'POST':
#         # معالجة دفع القسط - مُحدث
#         try:
#             fee_type = request.POST.get('fee_type')
#             installment_number = request.POST.get('installment_number')
#             amount_paid = request.POST.get('amount_paid')
#             payment_method = request.POST.get('payment_method', 'cash')
#             notes = request.POST.get('notes', '')
#             apply_discount_id = request.POST.get('apply_discount')
            
#             print(f"البيانات المستلمة: fee_type={fee_type}, installment_number={installment_number}, amount_paid={amount_paid}")
            
#             if not fee_type or not installment_number or not amount_paid:
#                 messages.error(request, 'بيانات غير مكتملة')
#                 return render(request, 'payments/pay_student_fees.html', {
#                     'student': student,
#                     'current_year': current_year,
#                     'student_fees': student_fees,
#                     'available_discounts': available_discounts,
#                     'permissions': permissions,
#                     'user_role': user_role,
#                     'page_title': f'دفع مصروفات للطالب {student.name}'
#                 })
            
#             # التحقق من صحة المبلغ
#             try:
#                 amount_paid = Decimal(str(amount_paid))
#                 if amount_paid <= 0:
#                     messages.error(request, 'يجب إدخال مبلغ أكبر من صفر')
#                     raise ValueError("مبلغ غير صحيح")
#             except (ValueError, InvalidOperation):
#                 messages.error(request, 'مبلغ غير صحيح')
#                 return render(request, 'payments/pay_student_fees.html', {
#                     'student': student,
#                     'current_year': current_year,
#                     'student_fees': student_fees,
#                     'available_discounts': available_discounts,
#                     'permissions': permissions,
#                     'user_role': user_role,
#                     'page_title': f'دفع مصروفات للطالب {student.name}'
#                 })
            
#             # العثور على إعدادات المصروفات
#             fee_setting = SchoolFeesSettings.objects.get(
#                 academic_year=current_year,
#                 grade_level=student.grade_level,
#                 fee_type=fee_type,
#                 is_active=True
#             )
            
#             # حساب المبلغ المطلوب (مع تطبيق الخصم إن وجد)
#             base_amount = float(fee_setting.installment_amount)
#             discount_amount = 0
#             final_amount = base_amount
#             applied_discount = None
            
#             if apply_discount_id:
#                 try:
#                     student_discount = StudentDiscount.objects.get(
#                         id=apply_discount_id,
#                         student=student,
#                         status='APPROVED'
#                     )
#                     discount_amount = student_discount.discount_setting.calculate_discount(base_amount)
#                     final_amount = base_amount - discount_amount
#                     applied_discount = student_discount
#                 except StudentDiscount.DoesNotExist:
#                     pass
            
#             # إنشاء سجل المدفوع
#             tuition = Tuition.objects.create(
#                 student=student,
#                 academic_year=current_year,
#                 fee_type=fee_type,
#                 fee_name=fee_setting.fee_name,
#                 installment_number=int(installment_number),
#                 amount_tuition=Decimal(str(final_amount)),
#                 amount_paid=amount_paid,
#                 payment_method=payment_method,
#                 payment_user=request.user.get_full_name() or request.user.username,
#                 payment_date=timezone.now(),
#                 notes=notes,
#                 applied_discount=applied_discount,
#                 discount_amount=Decimal(str(discount_amount)) if discount_amount > 0 else 0
#             )
            
#             # إنشاء سجل دفع
#             if tuition.amount_paid > 0:
#                 PaymentRecord.objects.create(
#                     tuition=tuition,
#                     amount_paid=tuition.amount_paid,
#                     payment_method=tuition.payment_method,
#                     payment_user=tuition.payment_user,
#                     notes=tuition.notes
#                 )
            
#             # رسالة نجاح
#             success_msg = f'تم تسجيل دفع {fee_setting.get_fee_type_display()} بنجاح!'
#             if discount_amount > 0:
#                 success_msg += f' (تم تطبيق خصم {discount_amount:.2f} ج.م)'
            
#             messages.success(request, f'{success_msg} المبلغ: {tuition.amount_paid} ج.م')
#             return redirect('payments:receipt', pk=tuition.pk)
            
#         except SchoolFeesSettings.DoesNotExist:
#             messages.error(request, 'لا توجد إعدادات مصروفات لهذا النوع')
#         except Exception as e:
#             print(f"خطأ في حفظ المدفوع: {e}")
#             messages.error(request, f'حدث خطأ في حفظ المدفوع: {str(e)}')
    
#     # الحصول على تاريخ المدفوعات للطالب
#     student_payments = Tuition.objects.filter(
#         student=student,
#         academic_year=current_year
#     ).order_by('-payment_date')[:10]
    
#     context = {
#         'student': student,
#         'current_year': current_year,
#         'student_fees': student_fees,
#         'available_discounts': available_discounts,
#         'student_payments': student_payments,
#         'permissions': permissions,
#         'user_role': user_role,
#         'page_title': f'دفع مصروفات للطالب {student.name}'
#     }
    
#     return render(request, 'payments/pay_student_fees.html', context)

# @never_cache
# @payments_full_access
# def pay_installment(request, pk):
#     """عرض مدفوعات طالب وتسجيل دفعة على قسط"""
#     student = get_object_or_404(
#         Student.objects.select_related(
#             'grade_level__education_level',
#             'academic_year'
#         ),
#         pk=pk
#     )

#     user_role = get_user_role(request.user)
#     permissions = get_payment_permissions(request.user)

#     # العام الدراسي الحالي من بيانات الطالب أو آخر عام نشط
#     current_year = getattr(student, 'academic_year', None)

#     if not current_year:
#         try:
#             from school_settings.models import AcademicYear
#             current_year = AcademicYear.objects.filter(is_active=True).order_by('-id').first()
#         except Exception:
#             current_year = None

#     # إنشاء قسط جديد للطالب
#     if request.method == 'POST' and request.POST.get('action') == 'create_installment':
#         form = TuitionForm(
#             request.POST,
#             student=student,
#             academic_year=current_year
#         )

#         if form.is_valid():
#             tuition = form.save(commit=False)
#             tuition.student = student
#             tuition.academic_year = current_year
#             tuition.payment_user = request.user.get_full_name() or request.user.username
#             tuition.save()

#             messages.success(request, 'تم إنشاء القسط بنجاح')

#             if tuition.amount_paid > 0:
#                 PaymentRecord.objects.create(
#                     tuition=tuition,
#                     amount_paid=tuition.amount_paid,
#                     payment_method=tuition.payment_method,
#                     payment_user=request.user.get_full_name() or request.user.username,
#                     notes=tuition.notes or ''
#                 )

#             return redirect('payments:pay_installment', pk=student.pk)

#         messages.error(request, 'يرجى مراجعة بيانات القسط')

#     # تسجيل دفعة على قسط موجود
#     elif request.method == 'POST' and request.POST.get('action') == 'record_payment':
#         tuition_id = request.POST.get('tuition_id')

#         tuition = get_object_or_404(
#             Tuition,
#             pk=tuition_id,
#             student=student
#         )

#         form = PaymentRecordForm(
#             request.POST,
#             tuition=tuition,
#             payment_user=request.user.get_full_name() or request.user.username
#         )

#         if form.is_valid():
#             form.save()
#             messages.success(request, 'تم تسجيل الدفعة بنجاح')
#             return redirect('payments:pay_installment', pk=student.pk)

#         messages.error(request, 'يرجى مراجعة بيانات الدفعة')

#     else:
#         form = TuitionForm(
#             student=student,
#             academic_year=current_year
#         )

#     # أقساط الطالب
#     installments = Tuition.objects.filter(
#         student=student
#     ).select_related(
#         'academic_year',
#         'applied_discount'
#     ).prefetch_related(
#         'payment_records'
#     ).order_by(
#         'academic_year__id',
#         'fee_type',
#         'installment_number'
#     )

#     # سجلات الدفع
#     payment_records = PaymentRecord.objects.filter(
#         tuition__student=student
#     ).select_related(
#         'tuition',
#         'tuition__student'
#     ).order_by(
#         '-payment_date'
#     )

#     # الملخص المالي
#     active_installments = installments.exclude(payment_status='CANCELLED')

#     totals = active_installments.aggregate(
#         total_required=Sum('amount_tuition'),
#         total_paid=Sum('amount_paid'),
#         total_discounts=Sum('discount_amount'),
#         installments_count=Count('id'),
#     )

#     total_required = totals['total_required'] or Decimal('0.00')
#     total_paid = totals['total_paid'] or Decimal('0.00')
#     total_discounts = totals['total_discounts'] or Decimal('0.00')
#     total_remaining = max(Decimal('0.00'), total_required - total_paid)

#     paid_count = active_installments.filter(payment_status='PAID').count()
#     partial_count = active_installments.filter(payment_status='PARTIALLY_PAID').count()
#     pending_count = active_installments.filter(payment_status='PENDING').count()
#     overdue_count = active_installments.filter(payment_status='OVERDUE').count()

#     collection_percentage = (
#         total_paid / total_required * 100
#     ) if total_required > 0 else 0

#     summary = {
#         'total_required': total_required,
#         'total_paid': total_paid,
#         'total_remaining': total_remaining,
#         'total_discounts': total_discounts,
#         'installments_count': totals['installments_count'] or 0,
#         'paid_count': paid_count,
#         'partial_count': partial_count,
#         'pending_count': pending_count,
#         'overdue_count': overdue_count,
#         'collection_percentage': collection_percentage,
#     }

#     context = {
#         'student': student,
#         'installments': installments,
#         'payment_records': payment_records,
#         'summary': summary,
#         'form': form,
#         'payment_form': PaymentRecordForm(),
#         'current_year': current_year,

#         'fee_type_choices': Tuition.FEE_TYPE_CHOICES,
#         'payment_method_choices': Tuition.PAYMENT_METHOD_CHOICES,

#         'permissions': permissions,
#         'user_role': user_role,
#         'title': f'مدفوعات الطالب - {student.name}',
#     }

#     return render(request, 'payments/pay_installment.html', context)

# @never_cache
# @payments_manager_access
# def edit_payment(request, payment_id):
#     """تعديل قسط / مدفوع"""
#     tuition = get_object_or_404(
#         Tuition.objects.select_related(
#             'student',
#             'student__grade_level',
#             'student__grade_level__education_level',
#             'academic_year',
#         ),
#         id=payment_id
#     )

#     student = tuition.student
#     permissions = get_payment_permissions(request.user)
#     user_role = get_user_role(request.user)

#     can_edit = permissions.get('can_edit', False) if isinstance(permissions, dict) else False

#     if not can_edit:
#         messages.error(request, 'لا تملك صلاحية لتعديل المدفوعات')
#         return redirect('payments:all_payments')

#     if request.method == 'POST':
#         try:
#             installment_number = request.POST.get('installment_number', '').strip()
#             fee_type = request.POST.get('fee_type', '').strip()
#             fee_name = request.POST.get('fee_name', '').strip()
#             amount_tuition = request.POST.get('amount_tuition', '').strip()
#             amount_paid = request.POST.get('amount_paid', '').strip()
#             discount_amount = request.POST.get('discount_amount', '0').strip()
#             payment_method = request.POST.get('payment_method', 'cash').strip()
#             receipt_number = request.POST.get('receipt_number', '').strip()
#             due_date = request.POST.get('due_date', '').strip()
#             payment_date = request.POST.get('payment_date', '').strip()
#             notes = request.POST.get('notes', '').strip()

#             if not installment_number:
#                 messages.error(request, 'رقم القسط مطلوب')
#                 return redirect('payments:edit_payment', payment_id=tuition.id)

#             try:
#                 installment_number = int(installment_number)
#             except ValueError:
#                 messages.error(request, 'رقم القسط يجب أن يكون رقم صحيح')
#                 return redirect('payments:edit_payment', payment_id=tuition.id)

#             try:
#                 amount_tuition = Decimal(str(amount_tuition or '0'))
#                 amount_paid = Decimal(str(amount_paid or '0'))
#                 discount_amount = Decimal(str(discount_amount or '0'))
#             except Exception:
#                 messages.error(request, 'يرجى إدخال مبالغ صحيحة')
#                 return redirect('payments:edit_payment', payment_id=tuition.id)

#             if amount_tuition <= 0:
#                 messages.error(request, 'مبلغ القسط المطلوب يجب أن يكون أكبر من صفر')
#                 return redirect('payments:edit_payment', payment_id=tuition.id)

#             if amount_paid < 0:
#                 messages.error(request, 'المبلغ المدفوع لا يمكن أن يكون أقل من صفر')
#                 return redirect('payments:edit_payment', payment_id=tuition.id)

#             if amount_paid > amount_tuition:
#                 messages.error(request, 'المبلغ المدفوع لا يمكن أن يكون أكبر من مبلغ القسط المطلوب')
#                 return redirect('payments:edit_payment', payment_id=tuition.id)

#             if discount_amount < 0:
#                 messages.error(request, 'قيمة الخصم لا يمكن أن تكون أقل من صفر')
#                 return redirect('payments:edit_payment', payment_id=tuition.id)

#             old_amount_paid = tuition.amount_paid or Decimal('0.00')

#             tuition.installment_number = installment_number
#             tuition.fee_type = fee_type or tuition.fee_type
#             tuition.fee_name = fee_name
#             tuition.amount_tuition = amount_tuition
#             tuition.amount_paid = amount_paid
#             tuition.discount_amount = discount_amount
#             tuition.payment_method = payment_method or tuition.payment_method
#             tuition.receipt_number = receipt_number
#             tuition.notes = notes

#             if due_date:
#                 tuition.due_date = due_date
#             else:
#                 tuition.due_date = None

#             if payment_date:
#                 try:
#                     parsed_payment_date = datetime.strptime(payment_date, '%Y-%m-%dT%H:%M')
#                     tuition.payment_date = timezone.make_aware(parsed_payment_date)
#                 except ValueError:
#                     messages.warning(request, 'صيغة تاريخ الدفع غير صحيحة، تم تجاهله')
#             elif amount_paid <= 0:
#                 tuition.payment_date = None

#             tuition.payment_user = request.user.get_full_name() or request.user.username
#             tuition.save()

#             # مزامنة سجل الدفع الأساسي مع إجمالي المدفوع
#             payment_records = PaymentRecord.objects.filter(tuition=tuition).order_by('payment_date')
#             records_total = payment_records.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

#             if amount_paid > 0:
#                 if payment_records.exists():
#                     latest_record = payment_records.last()
#                     difference = amount_paid - records_total

#                     if difference != 0:
#                         new_record_amount = (latest_record.amount_paid or Decimal('0.00')) + difference

#                         if new_record_amount > 0:
#                             latest_record.amount_paid = new_record_amount
#                             latest_record.payment_method = tuition.payment_method
#                             latest_record.payment_user = tuition.payment_user
#                             latest_record.notes = notes
#                             latest_record.save()
#                         else:
#                             # في حالة التخفيض الكبير، نوحد السجلات في سجل واحد
#                             payment_records.exclude(id=latest_record.id).delete()
#                             latest_record.amount_paid = amount_paid
#                             latest_record.payment_method = tuition.payment_method
#                             latest_record.payment_user = tuition.payment_user
#                             latest_record.notes = notes
#                             latest_record.save()
#                 else:
#                     PaymentRecord.objects.create(
#                         tuition=tuition,
#                         amount_paid=amount_paid,
#                         payment_method=tuition.payment_method,
#                         payment_user=tuition.payment_user,
#                         notes=notes,
#                     )
#             else:
#                 payment_records.delete()

#             messages.success(request, f'تم تعديل مدفوع الطالب {student.name} بنجاح')

#             next_url = request.POST.get('next', 'all')

#             if next_url == 'receipt' and tuition.amount_paid > 0:
#                 return redirect('payments:receipt', pk=tuition.pk)

#             if next_url == 'student':
#                 return redirect('payments:pay_installment', pk=student.pk)

#             return redirect('payments:all_payments')

#         except Exception as e:
#             print(f"خطأ في تعديل المدفوع: {e}")
#             messages.error(request, f'حدث خطأ أثناء تعديل المدفوع: {str(e)}')

#     payment_records = PaymentRecord.objects.filter(
#         tuition=tuition
#     ).order_by(
#         '-payment_date'
#     )

#     student_payments = Tuition.objects.filter(
#         student=student
#     ).exclude(
#         id=tuition.id
#     ).order_by(
#         '-payment_date',
#         '-created_date'
#     )[:8]

#     payment_date_value = ''
#     if tuition.payment_date:
#         payment_date_value = timezone.localtime(tuition.payment_date).strftime('%Y-%m-%dT%H:%M')

#     context = {
#         'tuition': tuition,
#         'payment': tuition,
#         'student': student,
#         'payment_records': payment_records,
#         'student_payments': student_payments,

#         'payment_status_choices': Tuition.PAYMENT_STATUS_CHOICES,
#         'payment_method_choices': Tuition.PAYMENT_METHOD_CHOICES,
#         'fee_type_choices': Tuition.FEE_TYPE_CHOICES,
#         'payment_date_value': payment_date_value,

#         'permissions': permissions,
#         'user_role': user_role,
#         'page_title': f'تعديل مدفوع - {student.name}',
#         'title': f'تعديل مدفوع - {student.name}',
#     }

#     return render(request, 'payments/edit_payment.html', context)

def calculate_discount_for_installment(original_amount, discount_amount=None, discount_percentage=None):
    """حساب صافي القسط بعد الخصم"""
    try:
        original_amount = Decimal(str(original_amount or '0'))
    except Exception:
        original_amount = Decimal('0.00')

    try:
        discount_amount = Decimal(str(discount_amount or '0'))
    except Exception:
        discount_amount = Decimal('0.00')

    try:
        discount_percentage = Decimal(str(discount_percentage or '0'))
    except Exception:
        discount_percentage = Decimal('0.00')

    if original_amount < 0:
        original_amount = Decimal('0.00')

    if discount_amount < 0:
        discount_amount = Decimal('0.00')

    if discount_percentage < 0:
        discount_percentage = Decimal('0.00')

    if discount_percentage > 100:
        discount_percentage = Decimal('100.00')

    percentage_discount_value = Decimal('0.00')

    if discount_percentage > 0 and original_amount > 0:
        percentage_discount_value = (original_amount * discount_percentage) / Decimal('100.00')

    final_discount = discount_amount + percentage_discount_value

    if final_discount > original_amount:
        final_discount = original_amount

    final_amount = original_amount - final_discount

    return {
        'original_amount': original_amount.quantize(Decimal('0.01')),
        'discount_amount': final_discount.quantize(Decimal('0.01')),
        'final_amount': final_amount.quantize(Decimal('0.01')),
    }


@never_cache
@payments_full_access
def pay_installment(request, pk):
    """عرض مدفوعات طالب وتسجيل دفعة على قسط"""
    student = get_object_or_404(
        Student.objects.select_related(
            'grade_level__education_level',
            'academic_year'
        ),
        pk=pk
    )

    user_role = get_user_role(request.user)
    permissions = get_payment_permissions(request.user)

    current_year = getattr(student, 'academic_year', None)

    if not current_year:
        try:
            from school_settings.models import AcademicYear
            current_year = AcademicYear.objects.filter(is_active=True).order_by('-id').first()
        except Exception:
            current_year = None

    payment_user = request.user.get_full_name() or request.user.username
    try:
        payment_settings = PaymentSettings.get_settings()
    except Exception:
        payment_settings = None
    # ============================================================
    # إنشاء قسط جديد
    # ============================================================
    if request.method == 'POST' and request.POST.get('action') == 'create_installment':
        form = TuitionForm(
            request.POST,
            student=student,
            academic_year=current_year
        )

        if form.is_valid():
            try:
                tuition = form.save(commit=False)

                original_amount = (
                    request.POST.get('original_amount')
                    or request.POST.get('amount_tuition')
                    or tuition.amount_tuition
                    or '0'
                )

                discount_amount = request.POST.get('discount_amount', '0')
                discount_percentage = request.POST.get('discount_percentage', '0')

                discount_result = calculate_discount_for_installment(
                    original_amount=original_amount,
                    discount_amount=discount_amount,
                    discount_percentage=discount_percentage,
                )

                tuition.student = student
                tuition.academic_year = current_year

                # المبلغ المطلوب النهائي بعد الخصم
                tuition.amount_tuition = discount_result['final_amount']

                # إجمالي الخصم
                tuition.discount_amount = discount_result['discount_amount']

                tuition.payment_user = payment_user

                if not tuition.payment_method:
                    if payment_settings:
                        tuition.payment_method = request.POST.get(
                            'payment_method',
                            payment_settings.default_payment_method
                        )
                    else:
                        tuition.payment_method = request.POST.get('payment_method', 'cash')

                if tuition.amount_paid is None:
                    tuition.amount_paid = Decimal('0.00')

                if tuition.amount_paid < 0:
                    messages.error(request, 'المبلغ المدفوع لا يمكن أن يكون أقل من صفر')
                    return redirect('payments:pay_installment', pk=student.pk)

                if tuition.amount_paid > tuition.amount_tuition and not (
                    payment_settings and payment_settings.allow_overpayment
                ):
                    messages.error(
                        request,
                        f'المبلغ المدفوع لا يمكن أن يتجاوز المطلوب بعد الخصم. المطلوب بعد الخصم: {tuition.amount_tuition} ج.م'
                    )
                    return redirect('payments:pay_installment', pk=student.pk)

                if tuition.amount_paid > 0 and not tuition.payment_date:
                    tuition.payment_date = timezone.now()

                tuition.save()

                if tuition.amount_paid > 0:
                    PaymentRecord.objects.create(
                        tuition=tuition,
                        amount_paid=tuition.amount_paid,
                        payment_method=tuition.payment_method,
                        payment_user=payment_user,
                        notes=tuition.notes or ''
                    )

                messages.success(request, 'تم إنشاء القسط بنجاح')
                return redirect('payments:pay_installment', pk=student.pk)

            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء إنشاء القسط: {str(e)}')

        else:
            messages.error(request, 'يرجى مراجعة بيانات القسط')

    # ============================================================
    # تسجيل دفعة على قسط موجود
    # ============================================================
    elif request.method == 'POST' and request.POST.get('action') == 'record_payment':
        tuition_id = request.POST.get('tuition_id')

        tuition = get_object_or_404(
            Tuition,
            pk=tuition_id,
            student=student
        )

        form = PaymentRecordForm(
            request.POST,
            tuition=tuition,
            payment_user=payment_user
        )

        if form.is_valid():
            try:
                record = form.save(commit=False)
                record.tuition = tuition
                record.payment_user = payment_user
                if not (payment_settings and payment_settings.allow_overpayment):
                    if record.amount_paid > tuition.remaining_amount:
                        messages.error(
                            request,
                            f'المبلغ المدفوع لا يمكن أن يتجاوز المتبقي: {tuition.remaining_amount} ج.م'
                        )
                        return redirect('payments:pay_installment', pk=student.pk)
                record.save()

                tuition.amount_paid = (tuition.amount_paid or Decimal('0.00')) + record.amount_paid
                tuition.payment_method = record.payment_method
                tuition.payment_user = payment_user

                if not tuition.payment_date:
                    tuition.payment_date = timezone.now()

                if record.notes:
                    old_notes = tuition.notes or ''
                    tuition.notes = f'{old_notes}\n{record.notes}'.strip()

                tuition.save()

                messages.success(request, 'تم تسجيل الدفعة بنجاح')
                return redirect('payments:pay_installment', pk=student.pk)

            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء تسجيل الدفعة: {str(e)}')

        else:
            messages.error(request, 'يرجى مراجعة بيانات الدفعة')

    else:
        form = TuitionForm(
            student=student,
            academic_year=current_year
        )

    # ============================================================
    # بيانات الصفحة
    # ============================================================
    installments = Tuition.objects.filter(
        student=student
    ).select_related(
        'academic_year',
        'applied_discount'
    ).order_by(
        'academic_year__id',
        'fee_type',
        'installment_number'
    )

    payment_records = PaymentRecord.objects.filter(
        tuition__student=student
    ).select_related(
        'tuition',
        'tuition__student'
    ).order_by(
        '-payment_date'
    )

    active_installments = installments.exclude(payment_status='CANCELLED')

    totals = active_installments.aggregate(
        total_required=Sum('amount_tuition'),
        total_paid=Sum('amount_paid'),
        total_discounts=Sum('discount_amount'),
        installments_count=Count('id'),
    )

    total_required = totals['total_required'] or Decimal('0.00')
    total_paid = totals['total_paid'] or Decimal('0.00')
    total_discounts = totals['total_discounts'] or Decimal('0.00')
    total_remaining = max(Decimal('0.00'), total_required - total_paid)

    paid_count = active_installments.filter(payment_status='PAID').count()
    partial_count = active_installments.filter(payment_status='PARTIALLY_PAID').count()
    pending_count = active_installments.filter(payment_status='PENDING').count()
    overdue_count = active_installments.filter(payment_status='OVERDUE').count()

    collection_percentage = (
        total_paid / total_required * 100
    ) if total_required > 0 else 0

    summary = {
        'total_required': total_required,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'total_discounts': total_discounts,
        'installments_count': totals['installments_count'] or 0,
        'paid_count': paid_count,
        'partial_count': partial_count,
        'pending_count': pending_count,
        'overdue_count': overdue_count,
        'collection_percentage': collection_percentage,
    }

    context = {
        'student': student,
        'installments': installments,
        'payment_records': payment_records,
        'summary': summary,
        'form': form,
        'payment_form': PaymentRecordForm(),
        'current_year': current_year,

        'fee_type_choices': Tuition.FEE_TYPE_CHOICES,
        'payment_method_choices': Tuition.PAYMENT_METHOD_CHOICES,
        'payment_settings': payment_settings,

        'permissions': permissions,
        'user_role': user_role,
        'title': f'مدفوعات الطالب - {student.name}',
    }

    return render(request, 'payments/pay_installment.html', context)


@never_cache
@payments_manager_access
def edit_payment(request, payment_id):
    """تعديل قسط / مدفوع"""
    tuition = get_object_or_404(
        Tuition.objects.select_related(
            'student',
            'student__grade_level',
            'student__grade_level__education_level',
            'academic_year',
        ),
        id=payment_id
    )

    student = tuition.student
    permissions = get_payment_permissions(request.user)
    user_role = get_user_role(request.user)

    can_edit = permissions.get('can_edit', False) if isinstance(permissions, dict) else False

    if not can_edit:
        messages.error(request, 'لا تملك صلاحية لتعديل المدفوعات')
        return redirect('payments:all_payments')

    payment_user = request.user.get_full_name() or request.user.username
    try:
        payment_settings = PaymentSettings.get_settings()
    except Exception:
        payment_settings = None

    if request.method == 'POST':
        try:
            installment_number = request.POST.get('installment_number', '').strip()
            fee_type = request.POST.get('fee_type', '').strip()
            fee_name = request.POST.get('fee_name', '').strip()

            original_amount = request.POST.get('original_amount', '').strip()
            amount_tuition = request.POST.get('amount_tuition', '').strip()
            amount_paid = request.POST.get('amount_paid', '').strip()

            discount_amount = request.POST.get('discount_amount', '0').strip()
            discount_percentage = request.POST.get('discount_percentage', '0').strip()

            payment_method = request.POST.get('payment_method', 'cash').strip()
            receipt_number = request.POST.get('receipt_number', '').strip()
            due_date = request.POST.get('due_date', '').strip()
            payment_date = request.POST.get('payment_date', '').strip()
            notes = request.POST.get('notes', '').strip()

            if not installment_number:
                messages.error(request, 'رقم القسط مطلوب')
                return redirect('payments:edit_payment', payment_id=tuition.id)

            try:
                installment_number = int(installment_number)
            except ValueError:
                messages.error(request, 'رقم القسط يجب أن يكون رقم صحيح')
                return redirect('payments:edit_payment', payment_id=tuition.id)

            try:
                amount_paid = Decimal(str(amount_paid or '0'))
            except Exception:
                messages.error(request, 'يرجى إدخال مبلغ مدفوع صحيح')
                return redirect('payments:edit_payment', payment_id=tuition.id)

            if not original_amount:
                original_amount = amount_tuition or tuition.amount_tuition

            discount_result = calculate_discount_for_installment(
                original_amount=original_amount,
                discount_amount=discount_amount,
                discount_percentage=discount_percentage,
            )

            final_amount_tuition = discount_result['final_amount']
            final_discount_amount = discount_result['discount_amount']

            if final_amount_tuition <= 0:
                messages.error(request, 'مبلغ القسط بعد الخصم يجب أن يكون أكبر من صفر')
                return redirect('payments:edit_payment', payment_id=tuition.id)

            if amount_paid < 0:
                messages.error(request, 'المبلغ المدفوع لا يمكن أن يكون أقل من صفر')
                return redirect('payments:edit_payment', payment_id=tuition.id)

            if amount_paid > final_amount_tuition and not (
                payment_settings and payment_settings.allow_overpayment
            ):
                messages.error(
                    request,
                    f'المبلغ المدفوع لا يمكن أن يكون أكبر من مبلغ القسط بعد الخصم. المطلوب بعد الخصم: {final_amount_tuition} ج.م'
                )
                return redirect('payments:edit_payment', payment_id=tuition.id)

            tuition.installment_number = installment_number
            tuition.fee_type = fee_type or tuition.fee_type
            tuition.fee_name = fee_name

            tuition.amount_tuition = final_amount_tuition
            tuition.discount_amount = final_discount_amount
            tuition.amount_paid = amount_paid

            tuition.payment_method = payment_method or tuition.payment_method
            tuition.receipt_number = receipt_number
            tuition.notes = notes
            tuition.payment_user = payment_user

            if due_date:
                tuition.due_date = due_date
            else:
                tuition.due_date = None

            if payment_date:
                try:
                    parsed_payment_date = datetime.strptime(payment_date, '%Y-%m-%dT%H:%M')
                    tuition.payment_date = timezone.make_aware(parsed_payment_date)
                except ValueError:
                    messages.warning(request, 'صيغة تاريخ الدفع غير صحيحة، تم تجاهله')
            elif amount_paid <= 0:
                tuition.payment_date = None
            elif amount_paid > 0 and not tuition.payment_date:
                tuition.payment_date = timezone.now()

            tuition.save()

            # ============================================================
            # مزامنة سجلات الدفع مع إجمالي المدفوع
            # ============================================================
            payment_records = PaymentRecord.objects.filter(tuition=tuition).order_by('payment_date')
            records_total = payment_records.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

            if amount_paid > 0:
                if payment_records.exists():
                    latest_record = payment_records.last()
                    difference = amount_paid - records_total

                    if difference != 0:
                        new_record_amount = (latest_record.amount_paid or Decimal('0.00')) + difference

                        if new_record_amount > 0:
                            latest_record.amount_paid = new_record_amount
                            latest_record.payment_method = tuition.payment_method
                            latest_record.payment_user = tuition.payment_user
                            latest_record.notes = notes
                            latest_record.save()
                        else:
                            payment_records.exclude(id=latest_record.id).delete()
                            latest_record.amount_paid = amount_paid
                            latest_record.payment_method = tuition.payment_method
                            latest_record.payment_user = tuition.payment_user
                            latest_record.notes = notes
                            latest_record.save()
                else:
                    PaymentRecord.objects.create(
                        tuition=tuition,
                        amount_paid=amount_paid,
                        payment_method=tuition.payment_method,
                        payment_user=tuition.payment_user,
                        notes=notes,
                    )
            else:
                payment_records.delete()

            messages.success(request, f'تم تعديل مدفوع الطالب {student.name} بنجاح')

            next_url = request.POST.get('next', 'all')

            if next_url == 'receipt' and tuition.amount_paid > 0:
                return redirect('payments:receipt', pk=tuition.pk)

            if next_url == 'student':
                return redirect('payments:pay_installment', pk=student.pk)

            return redirect('payments:all_payments')

        except Exception as e:
            print(f"خطأ في تعديل المدفوع: {e}")
            messages.error(request, f'حدث خطأ أثناء تعديل المدفوع: {str(e)}')

    payment_records = PaymentRecord.objects.filter(
        tuition=tuition
    ).order_by(
        '-payment_date'
    )

    student_payments = Tuition.objects.filter(
        student=student
    ).exclude(
        id=tuition.id
    ).order_by(
        '-payment_date',
        '-created_date'
    )[:8]

    payment_date_value = ''
    if tuition.payment_date:
        payment_date_value = timezone.localtime(tuition.payment_date).strftime('%Y-%m-%dT%H:%M')

    original_amount_value = (tuition.amount_tuition or Decimal('0.00')) + (tuition.discount_amount or Decimal('0.00'))

    context = {
        'tuition': tuition,
        'payment': tuition,
        'student': student,
        'payment_records': payment_records,
        'student_payments': student_payments,

        'payment_status_choices': Tuition.PAYMENT_STATUS_CHOICES,
        'payment_method_choices': Tuition.PAYMENT_METHOD_CHOICES,
        'fee_type_choices': Tuition.FEE_TYPE_CHOICES,
        'payment_date_value': payment_date_value,
        'original_amount_value': original_amount_value,

        'permissions': permissions,
        'user_role': user_role,
        'page_title': f'تعديل مدفوع - {student.name}',
        'title': f'تعديل مدفوع - {student.name}',
    }

    return render(request, 'payments/edit_payment.html', context)

@never_cache
@payments_sensitive_operation
def delete_installment(request, pk):
    """إلغاء قسط / مدفوع بشكل آمن بدون حذف فعلي"""
    tuition = get_object_or_404(
        Tuition.objects.select_related(
            'student',
            'student__grade_level',
            'student__grade_level__education_level',
            'academic_year',
        ),
        pk=pk
    )

    student = tuition.student
    permissions = get_payment_permissions(request.user)
    user_role = get_user_role(request.user)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        delete_records = request.POST.get('delete_records') == 'on'

        if not reason:
            messages.error(request, 'يجب كتابة سبب الإلغاء')
            return redirect('payments:delete_installment', pk=tuition.pk)

        try:
            old_notes = tuition.notes or ''
            cancel_note = (
                f'\n\n--- إلغاء القسط ---\n'
                f'تم الإلغاء بواسطة: {request.user.get_full_name() or request.user.username}\n'
                f'سبب الإلغاء: {reason}\n'
                f'تاريخ الإلغاء: {timezone.now().strftime("%Y-%m-%d %H:%M")}'
            )

            tuition.notes = f'{old_notes}{cancel_note}'.strip()
            tuition.payment_status = 'CANCELLED'
            tuition.amount_paid = Decimal('0.00')
            tuition.payment_user = request.user.get_full_name() or request.user.username
            tuition.save()

            if delete_records:
                PaymentRecord.objects.filter(tuition=tuition).delete()

            messages.success(request, f'تم إلغاء القسط الخاص بالطالب {student.name} بنجاح')
            return redirect('payments:pay_installment', pk=student.pk)

        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إلغاء القسط: {str(e)}')

    payment_records = PaymentRecord.objects.filter(
        tuition=tuition
    ).order_by(
        '-payment_date'
    )

    context = {
        'tuition': tuition,
        'student': student,
        'payment_records': payment_records,
        'permissions': permissions,
        'user_role': user_role,
        'title': f'إلغاء قسط - {student.name}',
        'page_title': f'إلغاء قسط - {student.name}',
    }

    return render(request, 'payments/delete_installment.html', context)

# @never_cache
# @payments_basic_access
# def receipt(request, pk):
#     """طباعة إيصال الدفع"""
#     tuition = get_object_or_404(Tuition, pk=pk)
#     student = tuition.student
#     permissions = get_payment_permissions(request.user)
    
#     if tuition.payment_status not in ['PAID', 'PARTIALLY_PAID']:
#         messages.warning(request, 'هذا القسط لم يتم دفعه بعد.')
#         # تصحيح التوجيه - البقاء داخل تطبيق المدفوعات
#         return redirect('payments:all_payments')
    
#     # الحصول على سجلات الدفع المرتبطة
#     payment_records = PaymentRecord.objects.filter(tuition=tuition).order_by('-payment_date')
    
#     context = {
#         'tuition': tuition,
#         'student': student,
#         'payment_records': payment_records,
#         'permissions': permissions,
#         'today': timezone.now(),
#         'page_title': f'إيصال دفع - {student.name}'
#     }
#     return render(request, 'payments/receipt.html', context)
@never_cache
@payments_basic_access
def receipt(request, pk):
    """عرض وطباعة إيصال الدفع"""
    tuition = get_object_or_404(
        Tuition.objects.select_related(
            'student',
            'student__grade_level',
            'student__grade_level__education_level',
            'academic_year',
        ),
        pk=pk
    )

    student = tuition.student
    permissions = get_payment_permissions(request.user)
    user_role = get_user_role(request.user)

    if tuition.amount_paid <= 0 or tuition.payment_status not in ['PAID', 'PARTIALLY_PAID']:
        messages.warning(request, 'هذا القسط لم يتم دفعه بعد، ولا يمكن طباعة إيصال له.')
        return redirect('payments:pay_installment', pk=student.pk)

    payment_records = PaymentRecord.objects.filter(
        tuition=tuition
    ).order_by(
        '-payment_date'
    )

    latest_record = payment_records.first()

    current_year = tuition.academic_year or getattr(student, 'academic_year', None)

    grade_level = getattr(student, 'grade_level', None)
    education_level = getattr(grade_level, 'education_level', None) if grade_level else None

    # إعدادات المدفوعات
    try:
        payment_settings = PaymentSettings.get_settings()
    except Exception:
        payment_settings = None

    context = {
        'tuition': tuition,
        'student': student,
        'payment_records': payment_records,
        'latest_record': latest_record,

        'grade_level': grade_level,
        'education_level': education_level,
        'current_year': current_year,

        'payment_settings': payment_settings,

        'permissions': permissions,
        'user_role': user_role,
        'today': timezone.now(),
        'page_title': f'إيصال دفع - {student.name}',
        'title': f'إيصال دفع - {student.name}',
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

# @csrf_protect
# @require_POST
# @payments_basic_access
# def student_search_ajax(request):
#     """API للبحث عن الطلاب"""
#     try:
#         import json
#         data = json.loads(request.body)
        
#         query = data.get('query', '').strip()
#         grade_id = data.get('grade', '')
#         year_id = data.get('year', '')
        
#         # بناء الاستعلام
#         from students.models import Student
#         students = Student.objects.all()
        
#         # فلترة حسب النص
#         if query:
#             students = students.filter(
#                 Q(name__icontains=query) | 
#                 Q(national_number__icontains=query)
#             )
        
#         # فلترة حسب الصف
#         if grade_id:
#             students = students.filter(grade_level_id=grade_id)
        
#         # تحديد عدد النتائج
#         students = students.select_related('grade_level')[:50]
        
#         # إعداد البيانات للإرسال
#         students_data = []
#         for student in students:
#             # حساب إحصائيات المدفوعات
#             payments = Tuition.objects.filter(student=student)
#             total_paid = payments.aggregate(total=Sum('amount_paid'))['total'] or 0
#             total_tuition = payments.aggregate(total=Sum('amount_tuition'))['total'] or 0
#             total_remaining = total_tuition - total_paid
#             payments_count = payments.count()
            
#             students_data.append({
#                 'id': student.id,
#                 'name': student.name,
#                 'national_number': student.national_number,
#                 'grade_name': getattr(student.grade_level, 'name', 'غير محدد'),
#                 'total_paid': float(total_paid),
#                 'total_remaining': float(total_remaining) if total_remaining > 0 else 0,
#                 'payments_count': payments_count
#             })
        
#         return JsonResponse({
#             'success': True,
#             'students': students_data,
#             'count': len(students_data)
#         })
        
#     except Exception as e:
#         print(f"خطأ في البحث: {e}")
#         return JsonResponse({
#             'success': False,
#             'error': 'حدث خطأ في البحث'
#         })

@csrf_protect
@payments_basic_access
def student_search_ajax(request):
    """API للبحث عن الطلاب - يدعم GET و POST"""
    try:
        # =========================
        # قراءة بيانات البحث
        # =========================
        if request.method == 'POST':
            try:
                data = json.loads(request.body.decode('utf-8') or '{}')
            except Exception:
                data = request.POST

            query = data.get('query', data.get('q', '')).strip()
            grade_id = data.get('grade', data.get('grade_id', ''))
            year_id = data.get('year', data.get('year_id', ''))

        else:
            query = request.GET.get('q', request.GET.get('query', '')).strip()
            grade_id = request.GET.get('grade', request.GET.get('grade_id', ''))
            year_id = request.GET.get('year', request.GET.get('year_id', ''))

        if len(query) < 2 and not grade_id and not year_id:
            return JsonResponse({
                'success': True,
                'students': [],
                'results': [],
                'count': 0,
            })

        # =========================
        # بناء الاستعلام
        # =========================
        students = Student.objects.filter(
            is_active=True
        ).select_related(
            'grade_level',
            'grade_level__education_level',
            'academic_year',
        )

        if query:
            students = students.filter(
                Q(name__icontains=query) |
                Q(national_number__icontains=query) |
                Q(phone_number__icontains=query) |
                Q(parent_name__icontains=query) |
                Q(parent_phone__icontains=query)
            )

        if grade_id:
            students = students.filter(grade_level_id=grade_id)

        if year_id:
            students = students.filter(academic_year_id=year_id)

        students = students.order_by(
            'grade_level__education_level__order',
            'grade_level__order',
            'name'
        )[:50]

        students_data = []

        for student in students:
            payments = Tuition.objects.filter(
                student=student
            ).exclude(
                payment_status='CANCELLED'
            )

            total_paid = payments.aggregate(
                total=Sum('amount_paid')
            )['total'] or Decimal('0.00')

            total_tuition = payments.aggregate(
                total=Sum('amount_tuition')
            )['total'] or Decimal('0.00')

            total_remaining = max(
                Decimal('0.00'),
                total_tuition - total_paid
            )

            grade_name = ''
            education_level_name = ''

            if student.grade_level:
                grade_name = student.grade_level.name

                if student.grade_level.education_level:
                    education_level_name = student.grade_level.education_level.name

            students_data.append({
                'id': student.id,
                'name': student.name or '',
                'national_number': student.national_number or '',
                'phone_number': student.phone_number or '',
                'parent_name': student.parent_name or '',
                'parent_phone': student.parent_phone or '',

                # أسماء متعددة للتوافق مع أي JavaScript قديم أو جديد
                'grade_level': grade_name,
                'grade_name': grade_name,
                'grade': grade_name,
                'education_level': education_level_name,
                'education_level_name': education_level_name,

                'academic_year': student.academic_year.name if student.academic_year else '',
                'total_paid': float(total_paid),
                'total_tuition': float(total_tuition),
                'total_remaining': float(total_remaining),
                'payments_count': payments.count(),

                'detail_url': reverse('students:student_detail', kwargs={'pk': student.pk}),
                'pay_url': reverse('payments:pay_installment', kwargs={'pk': student.pk}),
            })

        return JsonResponse({
            'success': True,
            'students': students_data,
            'results': students_data,
            'count': len(students_data),
            'query': query,
        })

    except Exception as e:
        print(f"خطأ في البحث عن الطلاب في المدفوعات: {e}")

        return JsonResponse({
            'success': False,
            'students': [],
            'results': [],
            'count': 0,
            'error': 'حدث خطأ في البحث',
        }, status=500)

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
    """لوحة التقارير المالية العامة"""
    permissions = get_payment_permissions(request.user)
    user_role = get_user_role(request.user)

    today = timezone.now().date()
    month_start = today.replace(day=1)

    # كل الأقساط غير الملغاة
    active_installments = Tuition.objects.exclude(
        payment_status='CANCELLED'
    ).select_related(
        'student',
        'student__grade_level',
        'student__grade_level__education_level',
        'academic_year',
    )

    # المدفوعات الفعلية
    paid_installments = active_installments.filter(
        amount_paid__gt=0
    )

    # إحصائيات عامة
    totals = active_installments.aggregate(
        total_required=Sum('amount_tuition'),
        total_paid=Sum('amount_paid'),
        total_count=Count('id'),
    )

    total_required = totals['total_required'] or Decimal('0.00')
    total_paid = totals['total_paid'] or Decimal('0.00')
    total_remaining = max(Decimal('0.00'), total_required - total_paid)

    collection_percentage = (
        total_paid / total_required * 100
    ) if total_required > 0 else 0

    # تحصيل اليوم
    today_data = paid_installments.filter(
        payment_date__date=today
    ).aggregate(
        amount=Sum('amount_paid'),
        count=Count('id'),
    )

    # تحصيل الشهر
    month_data = paid_installments.filter(
        payment_date__date__gte=month_start,
        payment_date__date__lte=today,
    ).aggregate(
        amount=Sum('amount_paid'),
        count=Count('id'),
    )

    # الحالات
    status_stats = {
        'paid_count': active_installments.filter(payment_status='PAID').count(),
        'partial_count': active_installments.filter(payment_status='PARTIALLY_PAID').count(),
        'pending_count': active_installments.filter(payment_status='PENDING').count(),
        'overdue_count': active_installments.filter(payment_status='OVERDUE').count(),
    }

    # المتأخرات الفعلية
    overdue_qs = active_installments.filter(
        due_date__lt=today
    ).exclude(
        payment_status='PAID'
    )

    overdue_amount = Decimal('0.00')
    for item in overdue_qs:
        overdue_amount += item.remaining_amount

    overdue_stats = {
        'count': overdue_qs.count(),
        'amount': overdue_amount,
    }

    # طرق الدفع
    payment_methods_stats = paid_installments.values(
        'payment_method'
    ).annotate(
        count=Count('id'),
        amount=Sum('amount_paid'),
    ).order_by(
        '-amount'
    )

    # المحاسبون
    collectors_stats = paid_installments.values(
        'payment_user'
    ).annotate(
        count=Count('id'),
        amount=Sum('amount_paid'),
    ).order_by(
        '-amount'
    )[:8]

    # إحصائيات الصفوف
    grade_stats = active_installments.values(
        'student__grade_level__name',
        'student__grade_level__education_level__name',
        'student__grade_level__order',
        'student__grade_level__education_level__order',
    ).annotate(
        total_required=Sum('amount_tuition'),
        total_paid=Sum('amount_paid'),
        installments_count=Count('id'),
        students_count=Count('student', distinct=True),
    ).order_by(
        'student__grade_level__education_level__order',
        'student__grade_level__order',
    )

    grade_stats_list = []
    for item in grade_stats:
        required = item['total_required'] or Decimal('0.00')
        paid = item['total_paid'] or Decimal('0.00')
        remaining = max(Decimal('0.00'), required - paid)

        grade_stats_list.append({
            'education_level_name': item['student__grade_level__education_level__name'] or 'غير محدد',
            'grade_name': item['student__grade_level__name'] or 'غير محدد',
            'total_required': required,
            'total_paid': paid,
            'total_remaining': remaining,
            'installments_count': item['installments_count'] or 0,
            'students_count': item['students_count'] or 0,
            'percentage': (paid / required * 100) if required > 0 else 0,
        })

    # آخر المدفوعات
    recent_payments = paid_installments.order_by(
        '-payment_date',
        '-created_date'
    )[:10]

    # أعلى مدفوعات
    top_payments = paid_installments.order_by(
        '-amount_paid'
    )[:10]

    # روابط سريعة
    current_month = today.month
    current_year = today.year

    context = {
        'permissions': permissions,
        'user_role': user_role,

        'total_required': total_required,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'collection_percentage': collection_percentage,
        'total_installments': totals['total_count'] or 0,

        'today_amount': today_data['amount'] or Decimal('0.00'),
        'today_count': today_data['count'] or 0,
        'month_amount': month_data['amount'] or Decimal('0.00'),
        'month_count': month_data['count'] or 0,

        'status_stats': status_stats,
        'overdue_stats': overdue_stats,
        'payment_methods_stats': payment_methods_stats,
        'collectors_stats': collectors_stats,
        'grade_stats': grade_stats_list,
        'recent_payments': recent_payments,
        'top_payments': top_payments,

        'today': today,
        'current_month': current_month,
        'current_year': current_year,

        'page_title': 'التقارير المالية',
        'title': 'التقارير المالية',
    }

    return render(request, 'payments/financial_reports.html', context)

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


@never_cache
@payments_financial_reports
def daily_report(request):
    """التقرير اليومي للمدفوعات"""
    try:
        # التاريخ المطلوب
        target_date_value = request.GET.get('date', '').strip()

        if target_date_value:
            try:
                target_date = datetime.strptime(target_date_value, '%Y-%m-%d').date()
            except ValueError:
                messages.warning(request, 'صيغة التاريخ غير صحيحة، تم عرض تقرير اليوم الحالي')
                target_date = timezone.now().date()
        else:
            target_date = timezone.now().date()

        permissions = get_payment_permissions(request.user)
        user_role = get_user_role(request.user)

        # مدفوعات اليوم الفعلية: أي قسط عليه مبلغ مدفوع في هذا اليوم وليس ملغيًا
        daily_payments = Tuition.objects.filter(
            payment_date__date=target_date,
            amount_paid__gt=0,
        ).exclude(
            payment_status='CANCELLED'
        ).select_related(
            'student',
            'student__grade_level',
            'student__grade_level__education_level',
            'academic_year',
        ).order_by(
            '-payment_date',
            '-created_date'
        )

        # إحصائيات أساسية
        stats_data = daily_payments.aggregate(
            total_amount=Sum('amount_paid'),
            total_count=Count('id'),
            avg_payment=Avg('amount_paid'),
            min_payment=Min('amount_paid'),
            max_payment=Max('amount_paid'),
        )

        basic_stats = {
            'total_amount': stats_data['total_amount'] or Decimal('0.00'),
            'total_count': stats_data['total_count'] or 0,
            'avg_payment': stats_data['avg_payment'] or Decimal('0.00'),
            'min_payment': stats_data['min_payment'] or Decimal('0.00'),
            'max_payment': stats_data['max_payment'] or Decimal('0.00'),
        }

        # طرق الدفع
        payment_methods_stats = daily_payments.values(
            'payment_method'
        ).annotate(
            count=Count('id'),
            amount=Sum('amount_paid'),
            avg_amount=Avg('amount_paid'),
        ).order_by(
            '-amount'
        )

        # المحاسبون
        staff_stats = daily_payments.values(
            'payment_user'
        ).annotate(
            count=Count('id'),
            amount=Sum('amount_paid'),
            avg_amount=Avg('amount_paid'),
        ).order_by(
            '-amount'
        )

        # إحصائيات الساعات بطريقة آمنة على Python بدل extra/strftime
        hourly_map = {}

        for payment in daily_payments:
            if payment.payment_date:
                local_dt = timezone.localtime(payment.payment_date)
                hour = local_dt.hour

                if hour not in hourly_map:
                    hourly_map[hour] = {
                        'hour': hour,
                        'count': 0,
                        'amount': Decimal('0.00'),
                    }

                hourly_map[hour]['count'] += 1
                hourly_map[hour]['amount'] += payment.amount_paid or Decimal('0.00')

        hourly_stats = [
            hourly_map[hour]
            for hour in sorted(hourly_map.keys())
        ]

        # المدفوعات الكبيرة: أكبر من متوسط اليوم
        large_payments = []

        if basic_stats['avg_payment'] and basic_stats['avg_payment'] > 0:
            large_payments = daily_payments.filter(
                amount_paid__gt=basic_stats['avg_payment']
            ).order_by(
                '-amount_paid'
            )[:10]

        # آخر 7 أيام قبل اليوم المختار
        previous_dates = []

        for i in range(1, 8):
            prev_date = target_date - timedelta(days=i)

            prev_data = Tuition.objects.filter(
                payment_date__date=prev_date,
                amount_paid__gt=0,
            ).exclude(
                payment_status='CANCELLED'
            ).aggregate(
                total_amount=Sum('amount_paid'),
                total_count=Count('id'),
            )

            previous_dates.append({
                'date': prev_date,
                'total_amount': float(prev_data['total_amount'] or 0),
                'total_count': prev_data['total_count'] or 0,
            })

        # مقارنة بالأمس
        yesterday = target_date - timedelta(days=1)

        yesterday_data = Tuition.objects.filter(
            payment_date__date=yesterday,
            amount_paid__gt=0,
        ).exclude(
            payment_status='CANCELLED'
        ).aggregate(
            total_amount=Sum('amount_paid'),
            total_count=Count('id'),
        )

        yesterday_amount = yesterday_data['total_amount'] or Decimal('0.00')
        yesterday_count = yesterday_data['total_count'] or 0

        amount_change = basic_stats['total_amount'] - yesterday_amount
        count_change = basic_stats['total_count'] - yesterday_count

        comparison_stats = {
            'amount_change': amount_change,
            'count_change': count_change,
            'amount_percentage': (
                amount_change / yesterday_amount * 100
            ) if yesterday_amount > 0 else 0,
            'count_percentage': (
                count_change / yesterday_count * 100
            ) if yesterday_count > 0 else 0,
        }

        # المتأخرات حتى التاريخ المختار
        overdue_qs = Tuition.objects.filter(
            due_date__lte=target_date,
        ).exclude(
            payment_status__in=['PAID', 'CANCELLED']
        ).select_related(
            'student'
        )

        overdue_count = overdue_qs.count()
        overdue_amount = Decimal('0.00')

        for item in overdue_qs:
            overdue_amount += item.remaining_amount

        overdue_stats = {
            'count': overdue_count,
            'amount': overdue_amount,
        }

        # إحصائيات الشهر حتى التاريخ المختار
        month_start = target_date.replace(day=1)

        monthly_data = Tuition.objects.filter(
            payment_date__date__gte=month_start,
            payment_date__date__lte=target_date,
            amount_paid__gt=0,
        ).exclude(
            payment_status='CANCELLED'
        ).aggregate(
            total_amount=Sum('amount_paid'),
            total_count=Count('id'),
        )

        monthly_stats = {
            'total_amount': monthly_data['total_amount'] or Decimal('0.00'),
            'total_count': monthly_data['total_count'] or 0,
        }

        # أهداف التحصيل من إعدادات المدفوعات
        try:
            payment_settings = PaymentSettings.get_settings()
            daily_target = payment_settings.daily_collection_target or Decimal('0.00')
            monthly_target = payment_settings.monthly_collection_target or Decimal('0.00')
        except Exception:
            payment_settings = None
            daily_target = Decimal('10000.00')
            monthly_target = Decimal('300000.00')

        target_achievement = {
            'daily_percentage': (
                basic_stats['total_amount'] / daily_target * 100
            ) if daily_target > 0 else 0,
            'monthly_percentage': (
                monthly_stats['total_amount'] / monthly_target * 100
            ) if monthly_target > 0 else 0,
        }

        # تجهيز بيانات الرسوم البيانية بصيغة JSON صحيحة
        chart_data = {
            'hourly_hours': json.dumps(
                [f"{item['hour']:02d}:00" for item in hourly_stats],
                ensure_ascii=False
            ),
            'hourly_amounts': json.dumps(
                [float(item['amount']) for item in hourly_stats],
                ensure_ascii=False
            ),
            'methods_labels': json.dumps(
                [
                    get_payment_method_display(item['payment_method'])
                    for item in payment_methods_stats
                ],
                ensure_ascii=False
            ),
            'methods_amounts': json.dumps(
                [float(item['amount'] or 0) for item in payment_methods_stats],
                ensure_ascii=False
            ),
            'weekly_dates': json.dumps(
                [item['date'].strftime('%d/%m') for item in previous_dates[::-1]] +
                [target_date.strftime('%d/%m')],
                ensure_ascii=False
            ),
            'weekly_amounts': json.dumps(
                [item['total_amount'] for item in previous_dates[::-1]] +
                [float(basic_stats['total_amount'] or 0)],
                ensure_ascii=False
            ),
        }

        context = {
            'target_date': target_date,
            'daily_payments': daily_payments,

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
            'user_role': user_role,
            'chart_data': chart_data,
            'payment_settings': payment_settings,
            'daily_target': daily_target,
            'monthly_target': monthly_target,
            'page_title': f'التقرير اليومي - {target_date.strftime("%Y-%m-%d")}',
            'title': f'التقرير اليومي - {target_date.strftime("%Y-%m-%d")}',
        }

        return render(request, 'payments/daily_report.html', context)

    except Exception as e:
        print(f"خطأ عام في التقرير اليومي: {e}")
        messages.error(request, f'حدث خطأ في تحضير التقرير: {str(e)}')
        return redirect('payments:payments_home')

@never_cache
@payments_financial_reports
def print_daily_report(request):
    """نسخة طباعة A4 للتقرير اليومي"""
    return _render_daily_report_print(request, auto_print=True)


@never_cache
@payments_financial_reports
def export_daily_report_pdf(request):
    """
    تصدير التقرير اليومي PDF.
    بدون مكتبات خارجية: يفتح صفحة A4 جاهزة للحفظ كـ PDF من المتصفح.
    """
    return _render_daily_report_print(request, auto_print=True)


def _render_daily_report_print(request, auto_print=False):
    """تحضير بيانات نسخة الطباعة للتقرير اليومي"""
    try:
        target_date_value = request.GET.get('date', '').strip()

        if target_date_value:
            try:
                target_date = datetime.strptime(target_date_value, '%Y-%m-%d').date()
            except ValueError:
                target_date = timezone.now().date()
        else:
            target_date = timezone.now().date()

        daily_payments = Tuition.objects.filter(
            payment_date__date=target_date,
            amount_paid__gt=0,
        ).exclude(
            payment_status='CANCELLED'
        ).select_related(
            'student',
            'student__grade_level',
            'student__grade_level__education_level',
            'academic_year',
        ).order_by(
            'payment_date',
            'student__name'
        )

        stats_data = daily_payments.aggregate(
            total_amount=Sum('amount_paid'),
            total_count=Count('id'),
            avg_payment=Avg('amount_paid'),
            min_payment=Min('amount_paid'),
            max_payment=Max('amount_paid'),
        )

        basic_stats = {
            'total_amount': stats_data['total_amount'] or Decimal('0.00'),
            'total_count': stats_data['total_count'] or 0,
            'avg_payment': stats_data['avg_payment'] or Decimal('0.00'),
            'min_payment': stats_data['min_payment'] or Decimal('0.00'),
            'max_payment': stats_data['max_payment'] or Decimal('0.00'),
        }

        payment_methods_stats = daily_payments.values(
            'payment_method'
        ).annotate(
            count=Count('id'),
            amount=Sum('amount_paid'),
        ).order_by(
            '-amount'
        )

        staff_stats = daily_payments.values(
            'payment_user'
        ).annotate(
            count=Count('id'),
            amount=Sum('amount_paid'),
        ).order_by(
            '-amount'
        )

        # المتأخرات حتى التاريخ
        overdue_qs = Tuition.objects.filter(
            due_date__lte=target_date,
        ).exclude(
            payment_status__in=['PAID', 'CANCELLED']
        )

        overdue_amount = Decimal('0.00')
        for item in overdue_qs:
            overdue_amount += item.remaining_amount

        overdue_stats = {
            'count': overdue_qs.count(),
            'amount': overdue_amount,
        }

        # ملخص الشهر
        month_start = target_date.replace(day=1)

        monthly_data = Tuition.objects.filter(
            payment_date__date__gte=month_start,
            payment_date__date__lte=target_date,
            amount_paid__gt=0,
        ).exclude(
            payment_status='CANCELLED'
        ).aggregate(
            total_amount=Sum('amount_paid'),
            total_count=Count('id'),
        )

        monthly_stats = {
            'total_amount': monthly_data['total_amount'] or Decimal('0.00'),
            'total_count': monthly_data['total_count'] or 0,
        }

        context = {
            'target_date': target_date,
            'daily_payments': daily_payments,
            'basic_stats': basic_stats,
            'payment_methods_stats': payment_methods_stats,
            'staff_stats': staff_stats,
            'overdue_stats': overdue_stats,
            'monthly_stats': monthly_stats,
            'today': timezone.now(),
            'auto_print': auto_print,
            'title': f'تقرير يومي - {target_date.strftime("%Y-%m-%d")}',
        }

        return render(request, 'payments/print_daily_report.html', context)

    except Exception as e:
        print(f"خطأ في طباعة التقرير اليومي: {e}")
        messages.error(request, f'حدث خطأ أثناء تجهيز التقرير للطباعة: {str(e)}')
        return redirect('payments:daily_report')

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
    """تسجيل دفع سريع لطالب"""
    user_role = get_user_role(request.user)
    permissions = get_payment_permissions(request.user)

    current_year = None
    try:
        from school_settings.models import AcademicYear
        current_year = AcademicYear.objects.filter(is_active=True).order_by('-id').first()
    except Exception:
        current_year = None

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        fee_type = request.POST.get('fee_type')
        amount_paid = request.POST.get('amount_paid')
        payment_method = request.POST.get('payment_method')
        notes = request.POST.get('notes', '').strip()

        if not student_id:
            messages.error(request, 'يرجى اختيار الطالب من نتائج البحث')
            return redirect('payments:quick_payment')

        student = get_object_or_404(Student, pk=student_id, is_active=True)

        try:
            amount_paid = Decimal(str(amount_paid or '0'))
        except Exception:
            amount_paid = Decimal('0.00')

        if amount_paid <= 0:
            messages.error(request, 'يرجى إدخال مبلغ دفع أكبر من صفر')
            return redirect('payments:quick_payment')

        if not fee_type:
            messages.error(request, 'يرجى اختيار نوع المصروف')
            return redirect('payments:quick_payment')

        payment_user = request.user.get_full_name() or request.user.username

        existing_installment = Tuition.objects.filter(
            student=student,
            fee_type=fee_type,
        ).exclude(
            payment_status__in=['PAID', 'CANCELLED']
        ).order_by(
            'due_date',
            'installment_number',
            'created_date'
        ).first()

        if existing_installment:
            remaining = existing_installment.remaining_amount

            if amount_paid > remaining:
                messages.error(
                    request,
                    f'المبلغ المدفوع أكبر من المتبقي على القسط. المتبقي: {remaining} ج.م'
                )
                return redirect('payments:quick_payment')

            PaymentRecord.objects.create(
                tuition=existing_installment,
                amount_paid=amount_paid,
                payment_method=payment_method,
                payment_user=payment_user,
                notes=notes,
            )

            existing_installment.amount_paid = (
                existing_installment.amount_paid or Decimal('0.00')
            ) + amount_paid
            existing_installment.payment_method = payment_method
            existing_installment.payment_user = payment_user

            if notes:
                old_notes = existing_installment.notes or ''
                existing_installment.notes = f'{old_notes}\n{notes}'.strip()

            existing_installment.save()

            messages.success(
                request,
                f'تم تسجيل دفعة بقيمة {amount_paid} ج.م للطالب {student.name}'
            )

            return redirect('payments:receipt', pk=existing_installment.pk)

        last_installment = Tuition.objects.filter(
            student=student,
            fee_type=fee_type,
            academic_year=current_year,
        ).order_by(
            '-installment_number'
        ).first()

        next_installment_number = (
            last_installment.installment_number + 1
            if last_installment
            else 1
        )

        tuition = Tuition.objects.create(
            student=student,
            academic_year=current_year,
            fee_type=fee_type,
            installment_number=next_installment_number,
            amount_tuition=amount_paid,
            amount_paid=amount_paid,
            payment_method=payment_method,
            payment_user=payment_user,
            notes=notes,
        )

        PaymentRecord.objects.create(
            tuition=tuition,
            amount_paid=amount_paid,
            payment_method=payment_method,
            payment_user=payment_user,
            notes=notes,
        )

        messages.success(
            request,
            f'تم إنشاء قسط جديد وتسجيل دفعة بقيمة {amount_paid} ج.م للطالب {student.name}'
        )

        return redirect('payments:receipt', pk=tuition.pk)

    context = {
        'permissions': permissions,
        'user_role': user_role,
        'current_year': current_year,
        'fee_type_choices': Tuition.FEE_TYPE_CHOICES,
        'payment_method_choices': Tuition.PAYMENT_METHOD_CHOICES,
        'title': 'دفع سريع',
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

    now = timezone.now()

    try:
        month = int(request.GET.get('month', now.month))
        year = int(request.GET.get('year', now.year))
    except ValueError:
        month = now.month
        year = now.year

    if month < 1 or month > 12:
        month = now.month

    current_year = now.year
    available_years = list(range(current_year - 3, current_year + 2))

    months_ar = {
        1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل',
        5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس',
        9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر',
    }

    payments = Tuition.objects.filter(
        payment_date__year=year,
        payment_date__month=month,
        amount_paid__gt=0,
    ).exclude(
        payment_status='CANCELLED'
    ).select_related(
        'student',
        'student__grade_level',
        'student__grade_level__education_level',
        'academic_year',
    ).order_by(
        '-payment_date',
        'student__name'
    )

    stats_data = payments.aggregate(
        total_amount=Sum('amount_paid'),
        total_count=Count('id'),
        avg_payment=Avg('amount_paid'),
        min_payment=Min('amount_paid'),
        max_payment=Max('amount_paid'),
        unique_students=Count('student', distinct=True),
    )

    monthly_stats = {
        'total_amount': stats_data['total_amount'] or Decimal('0.00'),
        'total_count': stats_data['total_count'] or 0,
        'avg_payment': stats_data['avg_payment'] or Decimal('0.00'),
        'min_payment': stats_data['min_payment'] or Decimal('0.00'),
        'max_payment': stats_data['max_payment'] or Decimal('0.00'),
        'unique_students': stats_data['unique_students'] or 0,
        'active_days': 0,
    }

    try:
        payment_settings = PaymentSettings.get_settings()
        monthly_target = payment_settings.monthly_collection_target or Decimal('0.00')
    except Exception:
        payment_settings = None
        monthly_target = Decimal('300000.00')

    monthly_target_percentage = (
        monthly_stats['total_amount'] / monthly_target * 100
    ) if monthly_target > 0 else 0

    # تجميع يومي آمن بدون extra
    daily_map = {}

    for payment in payments:
        if payment.payment_date:
            local_date = timezone.localtime(payment.payment_date).date()

            if local_date not in daily_map:
                daily_map[local_date] = Decimal('0.00')

            daily_map[local_date] += payment.amount_paid or Decimal('0.00')

    daily_items = [
        {
            'date': day,
            'label': day.strftime('%d/%m'),
            'amount': amount,
        }
        for day, amount in sorted(daily_map.items())
    ]

    monthly_stats['active_days'] = len(daily_items)

    highest_day = None
    daily_average = Decimal('0.00')

    if daily_items:
        highest_day = max(daily_items, key=lambda item: item['amount'])
        daily_average = monthly_stats['total_amount'] / max(monthly_stats['active_days'], 1)

    daily_data = {
        'labels': json.dumps([item['label'] for item in daily_items], ensure_ascii=False),
        'values': json.dumps([float(item['amount']) for item in daily_items], ensure_ascii=False),
        'highest_day': highest_day,
        'daily_average': daily_average,
    } if daily_items else {}

    payment_methods = payments.values(
        'payment_method'
    ).annotate(
        count=Count('id'),
        amount=Sum('amount_paid'),
        avg_amount=Avg('amount_paid'),
    ).order_by(
        '-amount'
    )

    top_users = payments.values(
        'payment_user'
    ).annotate(
        count=Count('id'),
        amount=Sum('amount_paid'),
        avg_amount=Avg('amount_paid'),
    ).order_by(
        '-amount'
    )[:5]

    context = {
        'payments': payments,
        'monthly_stats': monthly_stats,
        'daily_data': daily_data,
        'payment_methods': payment_methods,
        'top_users': top_users,

        'report_month': str(month),
        'report_year': str(year),
        'report_month_int': month,
        'report_year_int': year,
        'report_month_name': months_ar.get(month, 'غير محدد'),
        'available_years': available_years,

        'payment_settings': payment_settings,
        'monthly_target': monthly_target,
        'monthly_target_percentage': monthly_target_percentage,

        'permissions': permissions,
        'user_role': user_role,
        'page_title': f'التقرير الشهري - {months_ar.get(month)} {year}',
        'title': f'التقرير الشهري - {months_ar.get(month)} {year}',
    }

    return render(request, 'payments/monthly_report.html', context)

@never_cache
@payments_financial_reports
def print_monthly_report(request):
    """نسخة طباعة A4 للتقرير الشهري"""
    return _render_monthly_report_print(request, auto_print=True)


@never_cache
@payments_financial_reports
def export_monthly_report_pdf(request):
    """تصدير التقرير الشهري PDF من المتصفح"""
    return _render_monthly_report_print(request, auto_print=True)


def _render_monthly_report_print(request, auto_print=False):
    """تحضير نسخة طباعة التقرير الشهري"""
    try:
        now = timezone.now()

        try:
            month = int(request.GET.get('month', now.month))
            year = int(request.GET.get('year', now.year))
        except ValueError:
            month = now.month
            year = now.year

        if month < 1 or month > 12:
            month = now.month

        months_ar = {
            1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل',
            5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس',
            9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر',
        }

        payments = Tuition.objects.filter(
            payment_date__year=year,
            payment_date__month=month,
            amount_paid__gt=0,
        ).exclude(
            payment_status='CANCELLED'
        ).select_related(
            'student',
            'student__grade_level',
            'student__grade_level__education_level',
            'academic_year',
        ).order_by(
            'payment_date',
            'student__name'
        )

        stats_data = payments.aggregate(
            total_amount=Sum('amount_paid'),
            total_count=Count('id'),
            avg_payment=Avg('amount_paid'),
            unique_students=Count('student', distinct=True),
        )

        monthly_stats = {
            'total_amount': stats_data['total_amount'] or Decimal('0.00'),
            'total_count': stats_data['total_count'] or 0,
            'avg_payment': stats_data['avg_payment'] or Decimal('0.00'),
            'unique_students': stats_data['unique_students'] or 0,
        }

        daily_map = {}

        for payment in payments:
            if payment.payment_date:
                local_date = timezone.localtime(payment.payment_date).date()

                if local_date not in daily_map:
                    daily_map[local_date] = {
                        'date': local_date,
                        'count': 0,
                        'amount': Decimal('0.00'),
                    }

                daily_map[local_date]['count'] += 1
                daily_map[local_date]['amount'] += payment.amount_paid or Decimal('0.00')

        daily_summary = [
            daily_map[day]
            for day in sorted(daily_map.keys())
        ]

        monthly_stats['active_days'] = len(daily_summary)

        payment_methods = payments.values(
            'payment_method'
        ).annotate(
            count=Count('id'),
            amount=Sum('amount_paid'),
        ).order_by(
            '-amount'
        )

        top_users = payments.values(
            'payment_user'
        ).annotate(
            count=Count('id'),
            amount=Sum('amount_paid'),
        ).order_by(
            '-amount'
        )[:6]

        context = {
            'payments': payments,
            'monthly_stats': monthly_stats,
            'daily_summary': daily_summary,
            'payment_methods': payment_methods,
            'top_users': top_users,

            'report_month': month,
            'report_year': year,
            'report_month_name': months_ar.get(month, 'غير محدد'),

            'today': timezone.now(),
            'auto_print': auto_print,
            'title': f'التقرير الشهري - {months_ar.get(month)} {year}',
        }

        return render(request, 'payments/print_monthly_report.html', context)

    except Exception as e:
        print(f"خطأ في طباعة التقرير الشهري: {e}")
        messages.error(request, f'حدث خطأ أثناء تجهيز التقرير الشهري للطباعة: {str(e)}')
        return redirect('payments:monthly_report')
    
# في payments/views.py - تحديث دالة manage_discounts

from school_settings.models import DiscountSettings, StudentDiscount, AcademicYear

@never_cache
@payments_manager_access
def manage_discounts(request):
    """إدارة خصومات الطلاب"""
    permissions = get_payment_permissions(request.user)
    user_role = get_user_role(request.user)

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    year_filter = request.GET.get('academic_year', '').strip()

    # العام الدراسي الحالي
    current_year = None
    try:
        from school_settings.models import AcademicYear
        current_year = AcademicYear.objects.filter(is_active=True).order_by('-id').first()
        academic_years = AcademicYear.objects.all().order_by('-id')
    except Exception:
        academic_years = []
        current_year = None

    if request.method == 'POST':
        student_id = request.POST.get('student_id', '').strip()
        discount_amount = request.POST.get('discount_amount', '0').strip()
        discount_percentage = request.POST.get('discount_percentage', '0').strip()
        reason = request.POST.get('reason', '').strip()
        academic_year_id = request.POST.get('academic_year', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        if not student_id:
            messages.error(request, 'يجب اختيار الطالب')
            return redirect('payments:manage_discounts')

        student = get_object_or_404(Student, pk=student_id, is_active=True)

        try:
            discount_amount = Decimal(str(discount_amount or '0'))
            discount_percentage = Decimal(str(discount_percentage or '0'))
        except Exception:
            messages.error(request, 'يرجى إدخال قيمة خصم صحيحة')
            return redirect('payments:manage_discounts')

        if discount_amount < 0 or discount_percentage < 0:
            messages.error(request, 'قيمة الخصم أو النسبة لا يمكن أن تكون أقل من صفر')
            return redirect('payments:manage_discounts')

        if discount_amount == 0 and discount_percentage == 0:
            messages.error(request, 'يجب إدخال مبلغ خصم أو نسبة خصم')
            return redirect('payments:manage_discounts')

        selected_year = current_year
        if academic_year_id:
            try:
                from school_settings.models import AcademicYear
                selected_year = AcademicYear.objects.filter(pk=academic_year_id).first()
            except Exception:
                selected_year = current_year

        Discount.objects.create(
            student=student,
            discount_amount=discount_amount,
            discount_percentage=discount_percentage,
            reason=reason or 'خصم عام',
            academic_year=selected_year,
            is_active=is_active,
        )

        messages.success(request, f'تم إضافة خصم للطالب {student.name} بنجاح')
        return redirect('payments:manage_discounts')

    discounts_qs = Discount.objects.select_related(
        'student',
        'student__grade_level',
        'student__grade_level__education_level',
        'academic_year',
    ).order_by(
        '-created_date'
    )

    if search_query:
        discounts_qs = discounts_qs.filter(
            Q(student__name__icontains=search_query) |
            Q(student__national_number__icontains=search_query) |
            Q(student__phone_number__icontains=search_query) |
            Q(reason__icontains=search_query)
        )

    if status_filter == 'active':
        discounts_qs = discounts_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        discounts_qs = discounts_qs.filter(is_active=False)

    if year_filter:
        discounts_qs = discounts_qs.filter(academic_year_id=year_filter)

    totals = discounts_qs.aggregate(
        total_amount=Sum('discount_amount'),
        total_count=Count('id'),
    )

    total_amount = totals['total_amount'] or Decimal('0.00')
    total_count = totals['total_count'] or 0
    active_count = discounts_qs.filter(is_active=True).count()
    inactive_count = discounts_qs.filter(is_active=False).count()

    paginator = Paginator(discounts_qs, 25)
    page_number = request.GET.get('page')

    try:
        discounts = paginator.page(page_number)
    except PageNotAnInteger:
        discounts = paginator.page(1)
    except EmptyPage:
        discounts = paginator.page(paginator.num_pages)

    context = {
        'discounts': discounts,
        'page_obj': discounts,

        'total_amount': total_amount,
        'total_count': total_count,
        'active_count': active_count,
        'inactive_count': inactive_count,

        'academic_years': academic_years,
        'current_year': current_year,

        'search_query': search_query,
        'selected_status': status_filter,
        'selected_year': year_filter,

        'permissions': permissions,
        'user_role': user_role,
        'page_title': 'إدارة الخصومات',
        'title': 'إدارة الخصومات',
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

@never_cache
@payments_financial_reports
def overdue_payments(request):
    """صفحة متابعة الأقساط المتأخرة وغير المسددة"""
    permissions = get_payment_permissions(request.user)
    user_role = get_user_role(request.user)

    today = timezone.now().date()

    search_query = request.GET.get('search', '').strip()
    grade_filter = request.GET.get('grade_level', '').strip()
    status_filter = request.GET.get('status', '').strip()
    sort_by = request.GET.get('sort', 'due_date').strip()

    overdue_qs = Tuition.objects.filter(
        due_date__lt=today,
    ).exclude(
        payment_status__in=['PAID', 'CANCELLED']
    ).select_related(
        'student',
        'student__grade_level',
        'student__grade_level__education_level',
        'academic_year',
    )

    if search_query:
        overdue_qs = overdue_qs.filter(
            Q(student__name__icontains=search_query) |
            Q(student__national_number__icontains=search_query) |
            Q(student__phone_number__icontains=search_query) |
            Q(student__parent_name__icontains=search_query) |
            Q(student__parent_phone__icontains=search_query)
        )

    if grade_filter:
        overdue_qs = overdue_qs.filter(student__grade_level_id=grade_filter)

    if status_filter:
        overdue_qs = overdue_qs.filter(payment_status=status_filter)

    if sort_by == 'amount_desc':
        overdue_qs = overdue_qs.order_by('-amount_tuition', 'due_date')
    elif sort_by == 'student':
        overdue_qs = overdue_qs.order_by('student__name', 'due_date')
    elif sort_by == 'oldest':
        overdue_qs = overdue_qs.order_by('due_date')
    else:
        overdue_qs = overdue_qs.order_by('due_date', 'student__name')

    overdue_items = []
    total_required = Decimal('0.00')
    total_paid = Decimal('0.00')
    total_remaining = Decimal('0.00')

    for item in overdue_qs:
        remaining = item.remaining_amount
        delay_days = (today - item.due_date).days if item.due_date else 0

        total_required += item.amount_tuition or Decimal('0.00')
        total_paid += item.amount_paid or Decimal('0.00')
        total_remaining += remaining

        overdue_items.append({
            'tuition': item,
            'student': item.student,
            'remaining': remaining,
            'delay_days': delay_days,
        })

    # الصفوف للفلاتر
    try:
        from school_settings.models import GradeLevel
        grade_levels = GradeLevel.objects.filter(
            is_active=True
        ).select_related(
            'education_level'
        ).order_by(
            'education_level__order',
            'order',
            'name'
        )
    except Exception:
        grade_levels = []

    # توزيع حسب الصفوف
    grade_summary = {}
    for row in overdue_items:
        student = row['student']
        grade = getattr(student, 'grade_level', None)
        grade_name = grade.name if grade else 'غير محدد'

        if grade_name not in grade_summary:
            grade_summary[grade_name] = {
                'grade_name': grade_name,
                'count': 0,
                'amount': Decimal('0.00'),
            }

        grade_summary[grade_name]['count'] += 1
        grade_summary[grade_name]['amount'] += row['remaining']

    paginator = Paginator(overdue_items, 25)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'overdue_items': page_obj,
        'page_obj': page_obj,

        'total_required': total_required,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'total_count': len(overdue_items),

        'grade_summary': grade_summary.values(),
        'grade_levels': grade_levels,

        'search_query': search_query,
        'selected_grade': grade_filter,
        'selected_status': status_filter,
        'selected_sort': sort_by,

        'today': today,
        'permissions': permissions,
        'user_role': user_role,
        'page_title': 'الأقساط المتأخرة',
        'title': 'الأقساط المتأخرة',
    }

    return render(request, 'payments/overdue_payments.html', context)
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
    permissions = get_payment_permissions(request.user)
    user_role = get_user_role(request.user)

    settings_obj = PaymentSettings.get_settings()

    if request.method == 'POST':
        action = request.POST.get('action', 'save_settings')

        # ============================================================
        # إعادة حساب إجماليات الطلاب المالية
        # ============================================================
        if action == 'recalculate_student_finances':
            try:
                result = recalculate_all_students_financial_totals()

                messages.success(
                    request,
                    f"تم تحديث إجماليات {result['updated_count']} طالب بنجاح."
                )

                if result['failed_count'] > 0:
                    messages.warning(
                        request,
                        f"تعذر تحديث {result['failed_count']} طالب. راجع سجل التشغيل."
                    )

                return redirect('payments:payment_settings')

            except Exception as e:
                messages.error(
                    request,
                    f'حدث خطأ أثناء إعادة حساب إجماليات الطلاب: {str(e)}'
                )
                return redirect('payments:payment_settings')

        # ============================================================
        # حفظ إعدادات المدفوعات
        # ============================================================
        try:
            settings_obj.school_name_ar = request.POST.get(
                'school_name_ar',
                settings_obj.school_name_ar
            ).strip()

            settings_obj.school_name_en = request.POST.get(
                'school_name_en',
                settings_obj.school_name_en
            ).strip()

            settings_obj.receipt_prefix = request.POST.get(
                'receipt_prefix',
                settings_obj.receipt_prefix
            ).strip() or 'REC'

            settings_obj.receipt_footer_text = request.POST.get(
                'receipt_footer_text',
                ''
            ).strip()

            settings_obj.default_payment_method = request.POST.get(
                'default_payment_method',
                settings_obj.default_payment_method
            )

            daily_target = request.POST.get('daily_collection_target', '0')
            monthly_target = request.POST.get('monthly_collection_target', '0')

            try:
                settings_obj.daily_collection_target = Decimal(str(daily_target or '0'))
                settings_obj.monthly_collection_target = Decimal(str(monthly_target or '0'))
            except Exception:
                messages.error(request, 'يرجى إدخال أهداف تحصيل صحيحة')
                return redirect('payments:payment_settings')

            if settings_obj.daily_collection_target < 0:
                settings_obj.daily_collection_target = Decimal('0.00')

            if settings_obj.monthly_collection_target < 0:
                settings_obj.monthly_collection_target = Decimal('0.00')

            settings_obj.allow_overpayment = request.POST.get('allow_overpayment') == 'on'
            settings_obj.auto_generate_receipt_number = request.POST.get('auto_generate_receipt_number') == 'on'
            settings_obj.show_school_name_on_receipt = request.POST.get('show_school_name_on_receipt') == 'on'
            settings_obj.show_payment_records_on_receipt = request.POST.get('show_payment_records_on_receipt') == 'on'
            settings_obj.is_active = request.POST.get('is_active') == 'on'

            settings_obj.save()

            messages.success(request, 'تم حفظ إعدادات المدفوعات بنجاح')
            return redirect('payments:payment_settings')

        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حفظ الإعدادات: {str(e)}')

    context = {
        'settings_obj': settings_obj,
        'payment_method_choices': Tuition.PAYMENT_METHOD_CHOICES,
        'permissions': permissions,
        'user_role': user_role,
        'page_title': 'إعدادات المدفوعات',
        'title': 'إعدادات المدفوعات',
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
