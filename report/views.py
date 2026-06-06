from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Sum
from datetime import date, datetime, timedelta
from decimal import Decimal
from home.decorators import report_access_required
# استيراد التقارير والنماذج الجديدة
from .reports import (
    generate_daily_report, 
    generate_monthly_report, 
    generate_financial_report, 
    generate_student_list_report,
    export_students_to_csv,
    generate_student_statistics,
    generate_archived_students_report
)

from students.models import Student, ArchiveStudent
from school_settings.models import (
    AcademicYear as SettingsAcademicYear, 
    EducationLevel, 
    GradeLevel,
    SystemSettings
)


@never_cache
@login_required
@report_access_required
def reports_home(request):
    """لوحة تقارير المدير العامة من مختلف التطبيقات"""

    today = date.today()
    month_start = today.replace(day=1)

    # ============================================================
    # إحصائيات الطلاب
    # ============================================================
    students_qs = Student.objects.filter(is_active=True).select_related(
        'grade_level',
        'grade_level__education_level',
        'academic_year'
    )

    total_students = students_qs.count()
    male_students = students_qs.filter(gender='M').count()
    female_students = students_qs.filter(gender='F').count()

    archived_students_count = ArchiveStudent.objects.count()

    education_levels_stats = EducationLevel.objects.filter(
        is_active=True
    ).annotate(
        student_count=Count('gradelevel__student', filter=Q(gradelevel__student__is_active=True))
    ).order_by('order')

    grade_levels_stats = GradeLevel.objects.filter(
        is_active=True
    ).annotate(
        student_count=Count('student', filter=Q(student__is_active=True))
    ).select_related(
        'education_level'
    ).order_by(
        'education_level__order',
        'order'
    )

    # ============================================================
    # إحصائيات مالية من تطبيق المدفوعات
    # ============================================================
    payments_stats = {
        'total_required': Decimal('0.00'),
        'total_paid': Decimal('0.00'),
        'total_remaining': Decimal('0.00'),
        'today_paid': Decimal('0.00'),
        'month_paid': Decimal('0.00'),
        'overdue_count': 0,
        'overdue_amount': Decimal('0.00'),
        'payments_count': 0,
        'today_payments_count': 0,
    }

    recent_payments = []

    try:
        from payments.models import Tuition

        active_tuitions = Tuition.objects.exclude(payment_status='CANCELLED').select_related(
            'student',
            'student__grade_level',
            'student__grade_level__education_level',
            'academic_year'
        )

        paid_tuitions = active_tuitions.filter(amount_paid__gt=0)

        totals = active_tuitions.aggregate(
            total_required=Sum('amount_tuition'),
            total_paid=Sum('amount_paid'),
            payments_count=Count('id'),
        )

        total_required = totals['total_required'] or Decimal('0.00')
        total_paid = totals['total_paid'] or Decimal('0.00')
        total_remaining = max(Decimal('0.00'), total_required - total_paid)

        today_data = paid_tuitions.filter(
            payment_date__date=today
        ).aggregate(
            amount=Sum('amount_paid'),
            count=Count('id'),
        )

        month_data = paid_tuitions.filter(
            payment_date__date__gte=month_start,
            payment_date__date__lte=today,
        ).aggregate(
            amount=Sum('amount_paid'),
            count=Count('id'),
        )

        overdue_qs = active_tuitions.filter(
            due_date__lt=today
        ).exclude(
            payment_status='PAID'
        )

        overdue_amount = Decimal('0.00')
        for item in overdue_qs:
            try:
                overdue_amount += item.remaining_amount
            except Exception:
                overdue_amount += max(
                    Decimal('0.00'),
                    (item.amount_tuition or Decimal('0.00')) - (item.amount_paid or Decimal('0.00'))
                )

        payments_stats = {
            'total_required': total_required,
            'total_paid': total_paid,
            'total_remaining': total_remaining,
            'today_paid': today_data['amount'] or Decimal('0.00'),
            'month_paid': month_data['amount'] or Decimal('0.00'),
            'overdue_count': overdue_qs.count(),
            'overdue_amount': overdue_amount,
            'payments_count': totals['payments_count'] or 0,
            'today_payments_count': today_data['count'] or 0,
        }

        recent_payments = paid_tuitions.order_by(
            '-payment_date',
            '-created_date'
        )[:8]

    except Exception as e:
        print(f"خطأ في تحميل إحصائيات المدفوعات داخل التقارير: {e}")

    # ============================================================
    # إحصائيات الخزنة إن كان التطبيق موجودًا
    # ============================================================
    treasury_stats = {
        'available': False,
        'today_income': Decimal('0.00'),
        'today_expense': Decimal('0.00'),
        'month_income': Decimal('0.00'),
        'month_expense': Decimal('0.00'),
        'balance': Decimal('0.00'),
    }

    try:
        from treasury_management.models import Transaction

        treasury_stats['available'] = True

        today_income = Transaction.objects.filter(
            transaction_type='INCOME',
            created_date__date=today
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        today_expense = Transaction.objects.filter(
            transaction_type='EXPENSE',
            created_date__date=today
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        month_income = Transaction.objects.filter(
            transaction_type='INCOME',
            created_date__date__gte=month_start,
            created_date__date__lte=today,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        month_expense = Transaction.objects.filter(
            transaction_type='EXPENSE',
            created_date__date__gte=month_start,
            created_date__date__lte=today,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        treasury_stats.update({
            'today_income': today_income,
            'today_expense': today_expense,
            'month_income': month_income,
            'month_expense': month_expense,
            'balance': month_income - month_expense,
        })

    except Exception as e:
        print(f"تطبيق الخزنة غير متاح أو أسماء الحقول مختلفة: {e}")

    # ============================================================
    # روابط التقارير المتاحة
    # ============================================================
    report_cards = [
        {
            'title': 'التقرير اليومي',
            'description': 'ملخص اليوم للطلاب والمدفوعات',
            'icon': 'fas fa-calendar-day',
            'color': 'primary',
            'url_name': 'report:daily_report',
        },
        {
            'title': 'التقرير الشهري',
            'description': 'إحصائيات شهرية للطلاب والمدفوعات',
            'icon': 'fas fa-calendar-alt',
            'color': 'info',
            'url_name': 'report:monthly_report',
        },
        {
            'title': 'التقرير المالي',
            'description': 'ملخص مالي عام من النظام',
            'icon': 'fas fa-chart-line',
            'color': 'success',
            'url_name': 'report:financial_report',
        },
        {
            'title': 'قائمة الطلاب',
            'description': 'تقرير تفصيلي للطلاب مع الفلاتر',
            'icon': 'fas fa-users',
            'color': 'warning',
            'url_name': 'report:student_list_report',
        },
        {
            'title': 'الإحصائيات',
            'description': 'تحليلات الطلاب والمراحل والصفوف',
            'icon': 'fas fa-chart-pie',
            'color': 'secondary',
            'url_name': 'report:statistics_report',
        },
        {
            'title': 'الطلاب المؤرشفون',
            'description': 'تقرير الطلاب المحذوفين أو المؤرشفين',
            'icon': 'fas fa-archive',
            'color': 'danger',
            'url_name': 'report:archived_students_report',
        },
    ]

        # ============================================================
    # طلبات الخصومات المنتظرة
    # ============================================================
    pending_discount_requests = []
    pending_discounts_summary = {
        'count': 0,
        'total_amount': Decimal('0.00'),
    }

    try:
        from school_settings.models import StudentDiscount

        pending_qs = StudentDiscount.objects.filter(
            status='PENDING'
        ).select_related(
            'student',
            'discount_setting',
            'created_by'
        ).order_by('-created_date')

        pending_discounts_summary = {
            'count': pending_qs.count(),
            'total_amount': pending_qs.aggregate(
                total=Sum('applied_amount')
            )['total'] or Decimal('0.00'),
        }

        pending_discount_requests = pending_qs[:5]

    except Exception as e:
        print(f"تعذر تحميل طلبات الخصومات المنتظرة في مركز التقارير: {e}")

    context = {
        'today': today,
        'month_start': month_start,

        'total_students': total_students,
        'male_students': male_students,
        'female_students': female_students,
        'archived_students_count': archived_students_count,

        'education_levels_stats': education_levels_stats,
        'grade_levels_stats': grade_levels_stats,

        'payments_stats': payments_stats,
        'recent_payments': recent_payments,

        'treasury_stats': treasury_stats,
        'report_cards': report_cards,

        'page_title': 'مركز التقارير',
        'title': 'مركز التقارير',

        'pending_discount_requests': pending_discount_requests,
        'pending_discounts_summary': pending_discounts_summary,
    }

    return render(request, 'report/reports_home.html', context)


@never_cache
@login_required
def daily_report(request):
    """التقرير اليومي الموحد للمدير"""

    selected_date_value = request.GET.get('date', '').strip()

    if selected_date_value:
        try:
            target_date = datetime.strptime(selected_date_value, '%Y-%m-%d').date()
        except ValueError:
            messages.warning(request, 'صيغة التاريخ غير صحيحة، تم عرض تقرير اليوم الحالي')
            target_date = date.today()
    else:
        target_date = date.today()

    # ============================================================
    # الطلاب
    # ============================================================
    students_qs = Student.objects.filter(is_active=True).select_related(
        'grade_level',
        'grade_level__education_level',
        'academic_year'
    )

    total_students = students_qs.count()

    # الطلاب المضافون في التاريخ المختار
    new_students_today = []

    try:
        new_students_today = students_qs.filter(
            created_at__date=target_date
        ).order_by('-created_at')[:20]
    except Exception:
        # لو موديل Student لا يحتوي created_at
        new_students_today = []

    new_students_count = 0
    try:
        new_students_count = students_qs.filter(created_at__date=target_date).count()
    except Exception:
        new_students_count = 0

    male_students = students_qs.filter(gender='M').count()
    female_students = students_qs.filter(gender='F').count()

    # ============================================================
    # المدفوعات
    # ============================================================
    payments_stats = {
        'today_amount': Decimal('0.00'),
        'today_count': 0,
        'avg_payment': Decimal('0.00'),
        'max_payment': Decimal('0.00'),
        'overdue_today_count': 0,
        'overdue_today_amount': Decimal('0.00'),
    }

    today_payments = []
    payment_methods_stats = []
    collectors_stats = []

    try:
        from payments.models import Tuition

        active_tuitions = Tuition.objects.exclude(
            payment_status='CANCELLED'
        ).select_related(
            'student',
            'student__grade_level',
            'student__grade_level__education_level',
            'academic_year'
        )

        paid_today = active_tuitions.filter(
            payment_date__date=target_date,
            amount_paid__gt=0
        )

        stats_data = paid_today.aggregate(
            amount=Sum('amount_paid'),
            count=Count('id'),
            avg_payment=Sum('amount_paid'),
        )

        today_amount = stats_data['amount'] or Decimal('0.00')
        today_count = stats_data['count'] or 0
        avg_payment = today_amount / today_count if today_count > 0 else Decimal('0.00')

        max_payment_data = paid_today.aggregate(
            max_amount=Sum('amount_paid')
        )

        # max_payment بطريقة آمنة بدون Max لو الاستيراد غير موجود
        max_payment = Decimal('0.00')
        for item in paid_today:
            if item.amount_paid and item.amount_paid > max_payment:
                max_payment = item.amount_paid

        overdue_today_qs = active_tuitions.filter(
            due_date__lte=target_date
        ).exclude(
            payment_status='PAID'
        )

        overdue_today_amount = Decimal('0.00')
        for item in overdue_today_qs:
            try:
                overdue_today_amount += item.remaining_amount
            except Exception:
                overdue_today_amount += max(
                    Decimal('0.00'),
                    (item.amount_tuition or Decimal('0.00')) - (item.amount_paid or Decimal('0.00'))
                )

        payments_stats = {
            'today_amount': today_amount,
            'today_count': today_count,
            'avg_payment': avg_payment,
            'max_payment': max_payment,
            'overdue_today_count': overdue_today_qs.count(),
            'overdue_today_amount': overdue_today_amount,
        }

        today_payments = paid_today.order_by(
            '-payment_date',
            '-created_date'
        )[:20]

        payment_methods_stats = paid_today.values(
            'payment_method'
        ).annotate(
            count=Count('id'),
            amount=Sum('amount_paid'),
        ).order_by(
            '-amount'
        )

        collectors_stats = paid_today.values(
            'payment_user'
        ).annotate(
            count=Count('id'),
            amount=Sum('amount_paid'),
        ).order_by(
            '-amount'
        )[:10]

    except Exception as e:
        print(f"خطأ في تحميل بيانات المدفوعات للتقرير اليومي الموحد: {e}")

    # ============================================================
    # الخزنة إن وجدت
    # ============================================================
    treasury_stats = {
        'available': False,
        'income': Decimal('0.00'),
        'expense': Decimal('0.00'),
        'net': Decimal('0.00'),
        'transactions_count': 0,
    }

    recent_transactions = []

    try:
        from treasury_management.models import Transaction

        transactions_today = Transaction.objects.filter(
            created_date__date=target_date
        ).order_by('-created_date')

        income = transactions_today.filter(
            transaction_type='INCOME'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        expense = transactions_today.filter(
            transaction_type='EXPENSE'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        treasury_stats = {
            'available': True,
            'income': income,
            'expense': expense,
            'net': income - expense,
            'transactions_count': transactions_today.count(),
        }

        recent_transactions = transactions_today[:10]

    except Exception as e:
        print(f"الخزنة غير متاحة في التقرير اليومي الموحد أو أسماء الحقول مختلفة: {e}")

    context = {
        'target_date': target_date,
        'today': date.today(),

        'total_students': total_students,
        'male_students': male_students,
        'female_students': female_students,
        'new_students_count': new_students_count,
        'new_students_today': new_students_today,

        'payments_stats': payments_stats,
        'today_payments': today_payments,
        'payment_methods_stats': payment_methods_stats,
        'collectors_stats': collectors_stats,

        'treasury_stats': treasury_stats,
        'recent_transactions': recent_transactions,

        'title': f'التقرير اليومي الموحد - {target_date.strftime("%Y-%m-%d")}',
        'page_title': f'التقرير اليومي الموحد - {target_date.strftime("%Y-%m-%d")}',
    }

    return render(request, 'report/daily_report.html', context)


@never_cache
@login_required
def monthly_report(request):
    """التقرير الشهري الموحد للمدير"""

    today = date.today()

    # الحصول على السنة والشهر من الطلب
    year = request.GET.get('year')
    month = request.GET.get('month')

    try:
        year = int(year) if year else today.year
        month = int(month) if month else today.month
    except ValueError:
        year = today.year
        month = today.month

    if month < 1 or month > 12:
        month = today.month

    month_start = date(year, month, 1)

    if month == 12:
        next_month_start = date(year + 1, 1, 1)
    else:
        next_month_start = date(year, month + 1, 1)

    month_end = next_month_start - timedelta(days=1)

    months_ar = {
        1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل',
        5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس',
        9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر',
    }

    current_year = today.year
    years = list(range(current_year - 5, current_year + 2))
    months = [
        (1, 'يناير'), (2, 'فبراير'), (3, 'مارس'), (4, 'أبريل'),
        (5, 'مايو'), (6, 'يونيو'), (7, 'يوليو'), (8, 'أغسطس'),
        (9, 'سبتمبر'), (10, 'أكتوبر'), (11, 'نوفمبر'), (12, 'ديسمبر'),
    ]

    # ============================================================
    # الطلاب
    # ============================================================
    students_qs = Student.objects.filter(is_active=True).select_related(
        'grade_level',
        'grade_level__education_level',
        'academic_year'
    )

    total_students = students_qs.count()
    male_students = students_qs.filter(gender='M').count()
    female_students = students_qs.filter(gender='F').count()

    new_students_month = []
    new_students_count = 0

    try:
        new_students_month = students_qs.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end,
        ).order_by('-created_at')[:20]

        new_students_count = students_qs.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end,
        ).count()
    except Exception:
        new_students_month = []
        new_students_count = 0

    education_levels_stats = EducationLevel.objects.filter(
        is_active=True
    ).annotate(
        student_count=Count('gradelevel__student', filter=Q(gradelevel__student__is_active=True))
    ).order_by('order')

    grade_levels_stats = GradeLevel.objects.filter(
        is_active=True
    ).annotate(
        student_count=Count('student', filter=Q(student__is_active=True))
    ).select_related(
        'education_level'
    ).order_by(
        'education_level__order',
        'order'
    )

    # ============================================================
    # المدفوعات
    # ============================================================
    payments_stats = {
        'month_amount': Decimal('0.00'),
        'month_count': 0,
        'avg_payment': Decimal('0.00'),
        'max_payment': Decimal('0.00'),
        'overdue_count': 0,
        'overdue_amount': Decimal('0.00'),
    }

    month_payments = []
    payment_methods_stats = []
    collectors_stats = []
    daily_payment_summary = []

    try:
        from payments.models import Tuition

        active_tuitions = Tuition.objects.exclude(
            payment_status='CANCELLED'
        ).select_related(
            'student',
            'student__grade_level',
            'student__grade_level__education_level',
            'academic_year'
        )

        paid_month = active_tuitions.filter(
            payment_date__date__gte=month_start,
            payment_date__date__lte=month_end,
            amount_paid__gt=0
        )

        month_data = paid_month.aggregate(
            amount=Sum('amount_paid'),
            count=Count('id'),
        )

        month_amount = month_data['amount'] or Decimal('0.00')
        month_count = month_data['count'] or 0
        avg_payment = month_amount / month_count if month_count > 0 else Decimal('0.00')

        max_payment = Decimal('0.00')
        for item in paid_month:
            if item.amount_paid and item.amount_paid > max_payment:
                max_payment = item.amount_paid

        overdue_qs = active_tuitions.filter(
            due_date__lte=month_end
        ).exclude(
            payment_status='PAID'
        )

        overdue_amount = Decimal('0.00')
        for item in overdue_qs:
            try:
                overdue_amount += item.remaining_amount
            except Exception:
                overdue_amount += max(
                    Decimal('0.00'),
                    (item.amount_tuition or Decimal('0.00')) - (item.amount_paid or Decimal('0.00'))
                )

        payments_stats = {
            'month_amount': month_amount,
            'month_count': month_count,
            'avg_payment': avg_payment,
            'max_payment': max_payment,
            'overdue_count': overdue_qs.count(),
            'overdue_amount': overdue_amount,
        }

        month_payments = paid_month.order_by(
            '-payment_date',
            '-created_date'
        )[:30]

        payment_methods_stats = paid_month.values(
            'payment_method'
        ).annotate(
            count=Count('id'),
            amount=Sum('amount_paid'),
        ).order_by(
            '-amount'
        )

        collectors_stats = paid_month.values(
            'payment_user'
        ).annotate(
            count=Count('id'),
            amount=Sum('amount_paid'),
        ).order_by(
            '-amount'
        )[:10]

        # تجميع يومي آمن
        daily_map = {}

        for payment in paid_month:
            if payment.payment_date:
                payment_day = payment.payment_date.date()

                if payment_day not in daily_map:
                    daily_map[payment_day] = {
                        'date': payment_day,
                        'count': 0,
                        'amount': Decimal('0.00'),
                    }

                daily_map[payment_day]['count'] += 1
                daily_map[payment_day]['amount'] += payment.amount_paid or Decimal('0.00')

        daily_payment_summary = [
            daily_map[day]
            for day in sorted(daily_map.keys())
        ]

    except Exception as e:
        print(f"خطأ في تحميل بيانات المدفوعات للتقرير الشهري الموحد: {e}")

    # ============================================================
    # الخزنة إن وجدت
    # ============================================================
    treasury_stats = {
        'available': False,
        'income': Decimal('0.00'),
        'expense': Decimal('0.00'),
        'net': Decimal('0.00'),
        'transactions_count': 0,
    }

    recent_transactions = []

    try:
        from treasury_management.models import Transaction

        transactions_month = Transaction.objects.filter(
            created_date__date__gte=month_start,
            created_date__date__lte=month_end,
        ).order_by('-created_date')

        income = transactions_month.filter(
            transaction_type='INCOME'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        expense = transactions_month.filter(
            transaction_type='EXPENSE'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        treasury_stats = {
            'available': True,
            'income': income,
            'expense': expense,
            'net': income - expense,
            'transactions_count': transactions_month.count(),
        }

        recent_transactions = transactions_month[:10]

    except Exception as e:
        print(f"الخزنة غير متاحة في التقرير الشهري الموحد أو أسماء الحقول مختلفة: {e}")

    context = {
        'year': year,
        'month': month,
        'month_start': month_start,
        'month_end': month_end,
        'month_name': months_ar.get(month, 'غير محدد'),

        'years': years,
        'months': months,

        'total_students': total_students,
        'male_students': male_students,
        'female_students': female_students,
        'new_students_count': new_students_count,
        'new_students_month': new_students_month,
        'education_levels_stats': education_levels_stats,
        'grade_levels_stats': grade_levels_stats,

        'payments_stats': payments_stats,
        'month_payments': month_payments,
        'payment_methods_stats': payment_methods_stats,
        'collectors_stats': collectors_stats,
        'daily_payment_summary': daily_payment_summary,

        'treasury_stats': treasury_stats,
        'recent_transactions': recent_transactions,

        'title': f'التقرير الشهري الموحد - {months_ar.get(month)} {year}',
        'page_title': f'التقرير الشهري الموحد - {months_ar.get(month)} {year}',
    }

    return render(request, 'report/monthly_report.html', context)



@never_cache
@login_required
def financial_report(request):
    """التقرير المالي الموحد من تطبيق المدفوعات والخزنة"""
    today = date.today()
    month_start = today.replace(day=1)

    financial_data = {
        'total_required': Decimal('0.00'),
        'total_paid': Decimal('0.00'),
        'total_remaining': Decimal('0.00'),
        'collection_percentage': 0,
        'today_paid': Decimal('0.00'),
        'today_count': 0,
        'month_paid': Decimal('0.00'),
        'month_count': 0,
        'overdue_count': 0,
        'overdue_amount': Decimal('0.00'),
        'paid_count': 0,
        'partial_count': 0,
        'pending_count': 0,
        'overdue_status_count': 0,
    }

    payment_methods_stats = []
    collectors_stats = []
    grade_financial_stats = []
    recent_payments = []

    # ============================================================
    # بيانات المدفوعات
    # ============================================================
    try:
        from payments.models import Tuition

        active_tuitions = Tuition.objects.exclude(
            payment_status='CANCELLED'
        ).select_related(
            'student',
            'student__grade_level',
            'student__grade_level__education_level',
            'academic_year',
        )

        paid_tuitions = active_tuitions.filter(amount_paid__gt=0)

        totals = active_tuitions.aggregate(
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

        today_stats = paid_tuitions.filter(
            payment_date__date=today
        ).aggregate(
            amount=Sum('amount_paid'),
            count=Count('id'),
        )

        month_stats = paid_tuitions.filter(
            payment_date__date__gte=month_start,
            payment_date__date__lte=today,
        ).aggregate(
            amount=Sum('amount_paid'),
            count=Count('id'),
        )

        overdue_qs = active_tuitions.filter(
            due_date__lt=today
        ).exclude(
            payment_status='PAID'
        )

        overdue_amount = Decimal('0.00')

        for item in overdue_qs:
            try:
                overdue_amount += item.remaining_amount
            except Exception:
                overdue_amount += max(
                    Decimal('0.00'),
                    (item.amount_tuition or Decimal('0.00')) - (item.amount_paid or Decimal('0.00'))
                )

        financial_data = {
            'total_required': total_required,
            'total_paid': total_paid,
            'total_remaining': total_remaining,
            'collection_percentage': collection_percentage,
            'today_paid': today_stats['amount'] or Decimal('0.00'),
            'today_count': today_stats['count'] or 0,
            'month_paid': month_stats['amount'] or Decimal('0.00'),
            'month_count': month_stats['count'] or 0,
            'overdue_count': overdue_qs.count(),
            'overdue_amount': overdue_amount,
            'paid_count': active_tuitions.filter(payment_status='PAID').count(),
            'partial_count': active_tuitions.filter(payment_status='PARTIALLY_PAID').count(),
            'pending_count': active_tuitions.filter(payment_status='PENDING').count(),
            'overdue_status_count': active_tuitions.filter(payment_status='OVERDUE').count(),
        }

        payment_methods_stats = paid_tuitions.values(
            'payment_method'
        ).annotate(
            count=Count('id'),
            amount=Sum('amount_paid'),
        ).order_by(
            '-amount'
        )

        collectors_stats = paid_tuitions.values(
            'payment_user'
        ).annotate(
            count=Count('id'),
            amount=Sum('amount_paid'),
        ).order_by(
            '-amount'
        )[:10]

        grade_raw_stats = active_tuitions.values(
            'student__grade_level__name',
            'student__grade_level__education_level__name',
            'student__grade_level__order',
            'student__grade_level__education_level__order',
        ).annotate(
            total_required=Sum('amount_tuition'),
            total_paid=Sum('amount_paid'),
            students_count=Count('student', distinct=True),
            installments_count=Count('id'),
        ).order_by(
            'student__grade_level__education_level__order',
            'student__grade_level__order',
        )

        for row in grade_raw_stats:
            required = row['total_required'] or Decimal('0.00')
            paid = row['total_paid'] or Decimal('0.00')
            remaining = max(Decimal('0.00'), required - paid)

            grade_financial_stats.append({
                'education_level': row['student__grade_level__education_level__name'] or 'غير محدد',
                'grade': row['student__grade_level__name'] or 'غير محدد',
                'students_count': row['students_count'] or 0,
                'installments_count': row['installments_count'] or 0,
                'total_required': required,
                'total_paid': paid,
                'total_remaining': remaining,
                'percentage': (paid / required * 100) if required > 0 else 0,
            })

        recent_payments = paid_tuitions.order_by(
            '-payment_date',
            '-created_date'
        )[:10]

    except Exception as e:
        print(f"خطأ في تحميل بيانات التقرير المالي من payments: {e}")

    # ============================================================
    # بيانات الخزنة إن وجدت
    # ============================================================
    treasury_data = {
        'available': False,
        'today_income': Decimal('0.00'),
        'today_expense': Decimal('0.00'),
        'month_income': Decimal('0.00'),
        'month_expense': Decimal('0.00'),
        'month_net': Decimal('0.00'),
    }

    try:
        from treasury_management.models import Transaction

        treasury_data['available'] = True

        today_income = Transaction.objects.filter(
            transaction_type='INCOME',
            created_date__date=today,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        today_expense = Transaction.objects.filter(
            transaction_type='EXPENSE',
            created_date__date=today,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        month_income = Transaction.objects.filter(
            transaction_type='INCOME',
            created_date__date__gte=month_start,
            created_date__date__lte=today,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        month_expense = Transaction.objects.filter(
            transaction_type='EXPENSE',
            created_date__date__gte=month_start,
            created_date__date__lte=today,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        treasury_data.update({
            'today_income': today_income,
            'today_expense': today_expense,
            'month_income': month_income,
            'month_expense': month_expense,
            'month_net': month_income - month_expense,
        })

    except Exception as e:
        print(f"الخزنة غير متاحة داخل التقرير المالي أو أسماء الحقول مختلفة: {e}")

    context = {
        'today': today,
        'month_start': month_start,

        'financial_data': financial_data,
        'payment_methods_stats': payment_methods_stats,
        'collectors_stats': collectors_stats,
        'grade_financial_stats': grade_financial_stats,
        'recent_payments': recent_payments,
        'treasury_data': treasury_data,

        'title': 'التقرير المالي الموحد',
        'page_title': 'التقرير المالي الموحد',
    }

    return render(request, 'report/financial_report.html', context)


@never_cache
@login_required
def student_list_report(request):
    """تقرير قائمة الطلاب مع فلاتر متقدمة"""

    # ============================================================
    # قراءة الفلاتر
    # ============================================================
    search_query = request.GET.get('search', '').strip()
    gender = request.GET.get('gender', '').strip()
    education_level = request.GET.get('education_level', '').strip()
    grade_level = request.GET.get('grade_level', '').strip()
    academic_year = request.GET.get('academic_year', '').strip()
    financial_status = request.GET.get('financial_status', '').strip()
    age_min = request.GET.get('age_min', '').strip()
    age_max = request.GET.get('age_max', '').strip()
    export = request.GET.get('export', '').strip()

    students = Student.objects.filter(
        is_active=True
    ).select_related(
        'grade_level',
        'grade_level__education_level',
        'academic_year'
    ).order_by(
        'grade_level__education_level__order',
        'grade_level__order',
        'name'
    )

    # ============================================================
    # تطبيق الفلاتر
    # ============================================================
    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) |
            Q(national_number__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(parent_name__icontains=search_query) |
            Q(parent_phone__icontains=search_query)
        )

    if gender:
        students = students.filter(gender=gender)

    if education_level:
        try:
            students = students.filter(grade_level__education_level_id=int(education_level))
        except ValueError:
            pass

    if grade_level:
        try:
            students = students.filter(grade_level_id=int(grade_level))
        except ValueError:
            pass

    if academic_year:
        try:
            students = students.filter(academic_year_id=int(academic_year))
        except ValueError:
            pass

    if financial_status:
        if financial_status == 'paid':
            students = students.filter(total_owed__lte=0)
        elif financial_status == 'owing':
            students = students.filter(total_owed__gt=0)
        elif financial_status == 'no_fees':
            students = students.filter(total_fees__lte=0)

    if age_min:
        try:
            students = students.filter(age__gte=int(age_min))
        except ValueError:
            pass

    if age_max:
        try:
            students = students.filter(age__lte=int(age_max))
        except ValueError:
            pass

    # ============================================================
    # تصدير CSV بنفس الفلاتر
    # ============================================================
    if export == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = (
            f'attachment; filename="students_report_{datetime.now().strftime("%Y%m%d_%H%M")}.csv"'
        )

        import csv
        writer = csv.writer(response)

        writer.writerow([
            'اسم الطالب',
            'الرقم القومي',
            'النوع',
            'العمر',
            'تاريخ الميلاد',
            'رقم الهاتف',
            'ولي الأمر',
            'هاتف ولي الأمر',
            'المرحلة التعليمية',
            'الصف الدراسي',
            'العام الدراسي',
            'إجمالي المطلوب',
            'إجمالي المدفوع',
            'المتبقي',
            'الحالة المالية',
        ])

        for student in students:
            grade = getattr(student, 'grade_level', None)
            education = getattr(grade, 'education_level', None) if grade else None
            year_obj = getattr(student, 'academic_year', None)

            if student.total_owed and student.total_owed > 0:
                status_text = 'عليه مستحقات'
            elif student.total_fees and student.total_fees > 0:
                status_text = 'مسدد'
            else:
                status_text = 'لا توجد رسوم'

            writer.writerow([
                student.name or '',
                student.national_number or '',
                'ذكر' if student.gender == 'M' else 'أنثى' if student.gender == 'F' else 'غير محدد',
                student.age or '',
                student.date_of_birth.strftime('%Y-%m-%d') if getattr(student, 'date_of_birth', None) else '',
                student.phone_number or '',
                student.parent_name or '',
                student.parent_phone or '',
                education.name if education else '',
                grade.name if grade else '',
                year_obj.name if year_obj else '',
                float(student.total_fees or 0),
                float(student.total_payments or 0),
                float(student.total_owed or 0),
                status_text,
            ])

        return response

    # ============================================================
    # الإحصائيات
    # ============================================================
    total_count = students.count()
    male_count = students.filter(gender='M').count()
    female_count = students.filter(gender='F').count()
    paid_count = students.filter(total_owed__lte=0, total_fees__gt=0).count()
    owing_count = students.filter(total_owed__gt=0).count()
    no_fees_count = students.filter(total_fees__lte=0).count()

    totals = students.aggregate(
        total_fees=Sum('total_fees'),
        total_payments=Sum('total_payments'),
        total_owed=Sum('total_owed'),
    )

    summary = {
        'total_count': total_count,
        'male_count': male_count,
        'female_count': female_count,
        'paid_count': paid_count,
        'owing_count': owing_count,
        'no_fees_count': no_fees_count,
        'total_fees': totals['total_fees'] or Decimal('0.00'),
        'total_payments': totals['total_payments'] or Decimal('0.00'),
        'total_owed': totals['total_owed'] or Decimal('0.00'),
    }

    # ============================================================
    # بيانات الفلاتر
    # ============================================================
    education_levels = EducationLevel.objects.filter(
        is_active=True
    ).order_by('order')

    grade_levels = GradeLevel.objects.filter(
        is_active=True
    ).select_related(
        'education_level'
    ).order_by(
        'education_level__order',
        'order',
        'name'
    )

    academic_years = SettingsAcademicYear.objects.all().order_by('-start_date', '-id')

    context = {
        'students': students,
        'summary': summary,

        'education_levels': education_levels,
        'grade_levels': grade_levels,
        'academic_years': academic_years,

        'search_query': search_query,
        'selected_gender': gender,
        'selected_education_level': education_level,
        'selected_grade_level': grade_level,
        'selected_academic_year': academic_year,
        'selected_financial_status': financial_status,
        'age_min': age_min,
        'age_max': age_max,

        'today': date.today(),
        'title': 'تقرير قائمة الطلاب',
        'page_title': 'تقرير قائمة الطلاب',
    }

    return render(request, 'report/student_list_report.html', context)


@never_cache
@login_required
def statistics_report(request):
    """تقرير الإحصائيات العام للمدير"""

    today = date.today()

    # ============================================================
    # الطلاب
    # ============================================================
    students_qs = Student.objects.filter(is_active=True).select_related(
        'grade_level',
        'grade_level__education_level',
        'academic_year'
    )

    total_students = students_qs.count()
    male_students = students_qs.filter(gender='M').count()
    female_students = students_qs.filter(gender='F').count()
    unspecified_gender = total_students - male_students - female_students

    male_percentage = (male_students / total_students * 100) if total_students > 0 else 0
    female_percentage = (female_students / total_students * 100) if total_students > 0 else 0

    archived_students_count = ArchiveStudent.objects.count()

    # ============================================================
    # توزيع المراحل
    # ============================================================
    education_levels_stats = EducationLevel.objects.filter(
        is_active=True
    ).annotate(
        student_count=Count(
            'gradelevel__student',
            filter=Q(gradelevel__student__is_active=True)
        )
    ).order_by('order')

    # ============================================================
    # توزيع الصفوف
    # ============================================================
    grade_levels_stats = GradeLevel.objects.filter(
        is_active=True
    ).annotate(
        student_count=Count(
            'student',
            filter=Q(student__is_active=True)
        )
    ).select_related(
        'education_level'
    ).order_by(
        'education_level__order',
        'order'
    )

    top_grades = grade_levels_stats.order_by('-student_count')[:10]

    # ============================================================
    # الحالة المالية من حقول الطلاب
    # ============================================================
    students_paid = students_qs.filter(total_owed__lte=0).count()
    students_owing = students_qs.filter(total_owed__gt=0).count()

    financial_totals = students_qs.aggregate(
        total_fees=Sum('total_fees'),
        total_payments=Sum('total_payments'),
        total_owed=Sum('total_owed'),
    )

    student_financial_stats = {
        'students_paid': students_paid,
        'students_owing': students_owing,
        'paid_percentage': (students_paid / total_students * 100) if total_students > 0 else 0,
        'owing_percentage': (students_owing / total_students * 100) if total_students > 0 else 0,
        'total_fees': financial_totals['total_fees'] or Decimal('0.00'),
        'total_payments': financial_totals['total_payments'] or Decimal('0.00'),
        'total_owed': financial_totals['total_owed'] or Decimal('0.00'),
    }

    # ============================================================
    # إحصائيات من تطبيق المدفوعات إن وجد
    # ============================================================
    payment_overview = {
        'available': False,
        'installments_count': 0,
        'paid_installments': 0,
        'partial_installments': 0,
        'pending_installments': 0,
        'overdue_installments': 0,
        'cancelled_installments': 0,
        'total_required': Decimal('0.00'),
        'total_paid': Decimal('0.00'),
        'total_remaining': Decimal('0.00'),
        'collection_percentage': 0,
    }

    try:
        from payments.models import Tuition

        all_installments = Tuition.objects.all()
        active_installments = all_installments.exclude(payment_status='CANCELLED')

        totals = active_installments.aggregate(
            total_required=Sum('amount_tuition'),
            total_paid=Sum('amount_paid'),
            installments_count=Count('id'),
        )

        total_required = totals['total_required'] or Decimal('0.00')
        total_paid = totals['total_paid'] or Decimal('0.00')
        total_remaining = max(Decimal('0.00'), total_required - total_paid)

        payment_overview = {
            'available': True,
            'installments_count': totals['installments_count'] or 0,
            'paid_installments': active_installments.filter(payment_status='PAID').count(),
            'partial_installments': active_installments.filter(payment_status='PARTIALLY_PAID').count(),
            'pending_installments': active_installments.filter(payment_status='PENDING').count(),
            'overdue_installments': active_installments.filter(payment_status='OVERDUE').count(),
            'cancelled_installments': all_installments.filter(payment_status='CANCELLED').count(),
            'total_required': total_required,
            'total_paid': total_paid,
            'total_remaining': total_remaining,
            'collection_percentage': (total_paid / total_required * 100) if total_required > 0 else 0,
        }

    except Exception as e:
        print(f"تطبيق المدفوعات غير متاح في تقرير الإحصائيات أو يوجد اختلاف حقول: {e}")

    # ============================================================
    # إحصائيات حسب العام الدراسي
    # ============================================================
    academic_year_stats = []

    try:
        academic_years = SettingsAcademicYear.objects.all().order_by('-start_date', '-id')

        for academic_year in academic_years:
            count = students_qs.filter(academic_year=academic_year).count()

            academic_year_stats.append({
                'year': academic_year,
                'student_count': count,
                'percentage': (count / total_students * 100) if total_students > 0 else 0,
            })

    except Exception as e:
        print(f"خطأ في إحصائيات الأعوام الدراسية: {e}")
        academic_year_stats = []

    context = {
        'today': today,

        'total_students': total_students,
        'male_students': male_students,
        'female_students': female_students,
        'unspecified_gender': unspecified_gender,
        'male_percentage': male_percentage,
        'female_percentage': female_percentage,
        'archived_students_count': archived_students_count,

        'education_levels_stats': education_levels_stats,
        'grade_levels_stats': grade_levels_stats,
        'top_grades': top_grades,

        'student_financial_stats': student_financial_stats,
        'payment_overview': payment_overview,
        'academic_year_stats': academic_year_stats,

        'title': 'تقرير الإحصائيات العام',
        'page_title': 'تقرير الإحصائيات العام',
    }

    return render(request, 'report/statistics_report.html', context)


@never_cache
@login_required
def archived_students_report(request):
    """تقرير الطلاب المؤرشفين مع فلاتر وتصدير"""

    search_query = request.GET.get('search', '').strip()
    start_date_value = request.GET.get('start_date', '').strip()
    end_date_value = request.GET.get('end_date', '').strip()
    export = request.GET.get('export', '').strip()

    start_date = None
    end_date = None

    if start_date_value:
        try:
            start_date = datetime.strptime(start_date_value, '%Y-%m-%d').date()
        except ValueError:
            messages.warning(request, 'تاريخ البداية غير صحيح وتم تجاهله')
            start_date = None

    if end_date_value:
        try:
            end_date = datetime.strptime(end_date_value, '%Y-%m-%d').date()
        except ValueError:
            messages.warning(request, 'تاريخ النهاية غير صحيح وتم تجاهله')
            end_date = None

    archived_students = ArchiveStudent.objects.all().order_by('-archived_date')

    if search_query:
        archived_students = archived_students.filter(
            Q(archive_name__icontains=search_query) |
            Q(archive_national_number__icontains=search_query) |
            Q(archived_reason__icontains=search_query)
        )

        # حقول اختيارية لو موجودة في الموديل
        try:
            archived_students = archived_students | ArchiveStudent.objects.filter(
                Q(archive_phone_number__icontains=search_query) |
                Q(archive_parent_name__icontains=search_query) |
                Q(archive_parent_phone__icontains=search_query)
            )
        except Exception:
            pass

    if start_date:
        archived_students = archived_students.filter(archived_date__date__gte=start_date)

    if end_date:
        archived_students = archived_students.filter(archived_date__date__lte=end_date)

    archived_students = archived_students.order_by('-archived_date')

    # ============================================================
    # تصدير CSV
    # ============================================================
    if export == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = (
            f'attachment; filename="archived_students_{datetime.now().strftime("%Y%m%d_%H%M")}.csv"'
        )

        import csv
        writer = csv.writer(response)

        writer.writerow([
            'اسم الطالب المؤرشف',
            'الرقم القومي',
            'العمر',
            'الجنس',
            'الصف الدراسي',
            'المرحلة التعليمية',
            'إجمالي المصروفات',
            'إجمالي المدفوعات',
            'المستحقات',
            'تاريخ الأرشفة',
            'سبب الأرشفة',
        ])

        for student in archived_students:
            writer.writerow([
                student.archive_name or '',
                student.archive_national_number or '',
                student.archive_age or '',
                'ذكر' if student.archive_gender == 'M' else 'أنثى' if student.archive_gender == 'F' else 'غير محدد',
                student.archive_grade_level or '',
                student.archive_education_level or '',
                float(student.archive_total_fees or 0),
                float(student.archive_total_payments or 0),
                float(student.archive_total_owed or 0),
                student.archived_date.strftime('%Y-%m-%d %H:%M') if student.archived_date else '',
                student.archived_reason or '',
            ])

        return response

    # ============================================================
    # الملخص
    # ============================================================
    totals = archived_students.aggregate(
        total_fees=Sum('archive_total_fees'),
        total_payments=Sum('archive_total_payments'),
        total_owed=Sum('archive_total_owed'),
    )

    total_count = archived_students.count()
    male_count = archived_students.filter(archive_gender='M').count()
    female_count = archived_students.filter(archive_gender='F').count()

    summary = {
        'total_count': total_count,
        'male_count': male_count,
        'female_count': female_count,
        'total_fees': totals['total_fees'] or Decimal('0.00'),
        'total_payments': totals['total_payments'] or Decimal('0.00'),
        'total_owed': totals['total_owed'] or Decimal('0.00'),
    }

    context = {
        'archived_students': archived_students,
        'summary': summary,
        'search_query': search_query,
        'start_date': start_date_value,
        'end_date': end_date_value,
        'today': date.today(),
        'title': 'تقرير الطلاب المؤرشفين',
        'page_title': 'تقرير الطلاب المؤرشفين',
    }

    return render(request, 'report/archived_students_report.html', context)

@never_cache
@login_required
def export_csv(request):
    """تصدير البيانات لـ CSV"""
    
    export_type = request.GET.get('type', 'students')
    
    if export_type == 'students':
        # فلاتر مماثلة لتقرير قائمة الطلاب
        filters = {}
        # ... نفس منطق الفلاتر السابق
        
        report_data = generate_student_list_report(filters)
        return export_students_to_csv(report_data['students'])
    
    elif export_type == 'archived':
        # تصدير الطلاب المؤرشفين
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # ... معالجة التواريخ مماثلة للسابق
        
        report_data = generate_archived_students_report(start_date, end_date)
        
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="archived_students_{datetime.now().strftime("%Y%m%d_%H%M")}.csv"'
        
        import csv
        writer = csv.writer(response)
        
        # كتابة الرؤوس
        writer.writerow([
            'اسم الطالب المؤرشف',
            'الرقم القومي',
            'العمر',
            'الجنس',
            'الصف الدراسي',
            'المرحلة التعليمية',
            'إجمالي المصروفات',
            'إجمالي المدفوعات',
            'المستحقات',
            'تاريخ الأرشفة',
            'سبب الأرشفة'
        ])
        
        # كتابة البيانات
        for student in report_data['archived_students']:
            writer.writerow([
                student.archive_name,
                student.archive_national_number,
                student.archive_age,
                'ذكر' if student.archive_gender == 'M' else 'أنثى' if student.archive_gender == 'F' else '',
                student.archive_grade_level,
                student.archive_education_level,
                float(student.archive_total_fees),
                float(student.archive_total_payments),
                float(student.archive_total_owed),
                student.archived_date.strftime('%Y-%m-%d %H:%M'),
                student.archived_reason
            ])
        
        return response
    
    else:
        messages.error(request, 'نوع التصدير غير صحيح')
        return redirect('report:reports_home')


# API للحصول على الصفوف حسب المرحلة التعليمية (للفلاتر)
@never_cache
@login_required
def api_get_grades(request, education_level_id):
    """API للحصول على الصفوف حسب المرحلة التعليمية"""
    
    try:
        grades = GradeLevel.objects.filter(
            education_level_id=education_level_id,
            is_active=True
        ).order_by('order')
        
        grades_data = [
            {
                'id': grade.id,
                'name': grade.name,
                'typical_age': grade.typical_age
            }
            for grade in grades
        ]
        
        return JsonResponse({
            'success': True,
            'grades': grades_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
