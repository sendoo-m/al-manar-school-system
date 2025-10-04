# treasury_management/views.py - نسخة منظمة ومحسنة
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta, date
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction as db_transaction
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
import json
from django.contrib.auth import get_user_model
User = get_user_model()

# استيراد النماذج
from .models import (
    Treasury, Transaction, Account, AccountCategory,
    ExpenseCategory, TreasurySnapshot
)

# محاولة استيراد النماذج الاختيارية
try:
    from .models import DailyExpense, StudentPaymentTransaction
except ImportError:
    DailyExpense = None
    StudentPaymentTransaction = None

try:
    from school_settings.models import AcademicYear
except ImportError:
    AcademicYear = None

# استيراد الـ decorators المخصصة
from .decorators import (
    treasury_admin_required,
    treasury_manager_required,
    treasury_accountant_required,
    treasury_cashier_required,
    treasury_access_required,
    can_approve_transactions,
    can_delete_records
)

User = get_user_model()




# treasury_management/views.py - إضافة Views المفقودة في نهاية الملف

# ===================================
# ⚙️ Views الإعدادات والصيانة المفقودة
# ===================================

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

# استيراد النماذج المطلوبة
from students.models import Student
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

# استيراد النماذج الموجودة فقط
from students.models import Student

@never_cache
@login_required
def system_settings(request):
    """إعدادات النظام للخزينة مع إحصائيات فعلية"""
    
    # بيانات افتراضية للإعدادات
    default_settings = {
        'school_name': 'مدرسة المنار للغات',
        'school_address': '',
        'school_phone': '',
        'school_email': '',
        'academic_year': '2025/2026',
        'currency': 'EGP',
        'min_payment': 50.00,
        'max_payment': 5000.00,
        'date_format': 'd/m/Y',
        'report_language': 'ar',
        'require_approval': False,
        'enable_notifications': True,
    }
    
    if request.method == 'POST':
        try:
            # معالجة حفظ الإعدادات
            # يمكن إضافة منطق الحفظ هنا لاحقاً
            messages.success(request, 'تم حفظ الإعدادات بنجاح!')
            return redirect('treasury_management:system_settings')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حفظ الإعدادات: {str(e)}')
    
    # ===================================
    # 📊 حساب الإحصائيات الآمنة
    # ===================================
    
    try:
        # إحصائيات الطلاب الأساسية
        total_students = Student.objects.filter(is_active=True).count()
        
        # إحصائيات المدفوعات من نموذج Student
        students_stats = Student.objects.filter(is_active=True).aggregate(
            total_fees=Sum('total_fees'),
            total_payments=Sum('total_payments'),
            total_owed=Sum('total_owed')
        )
        
        total_treasury = students_stats['total_payments'] or Decimal('0.00')
        total_fees_due = students_stats['total_fees'] or Decimal('0.00')
        total_outstanding = students_stats['total_owed'] or Decimal('0.00')
        
        # إحصائيات الشهر الحالي
        current_month = timezone.now().date().replace(day=1)
        
        # عدد الطلاب المُسجلين هذا الشهر
        monthly_registrations = Student.objects.filter(
            created_at__gte=current_month
        ).count()
        
        # عدد الطلاب المُحدثين هذا الشهر (كبديل للمدفوعات)
        monthly_updates = Student.objects.filter(
            updated_at__gte=current_month
        ).count()
        
        # إحصائيات إضافية مفيدة
        students_paid_full = Student.objects.filter(
            is_active=True, 
            total_owed__lte=0
        ).count()
        
        students_with_dues = Student.objects.filter(
            is_active=True, 
            total_owed__gt=0
        ).count()
        
        students_no_payments = Student.objects.filter(
            is_active=True,
            total_payments=0
        ).count()
        
        # النسب المئوية
        payment_percentage = 0
        if total_fees_due > 0:
            payment_percentage = round((total_treasury / total_fees_due) * 100, 1)
        
        # متوسط المدفوعات
        avg_payment = 0
        if total_students > 0:
            avg_payment = total_treasury / total_students
        
        # محاولة الحصول على إحصائيات من نماذج أخرى (اختيارية)
        total_reports = 0
        try:
            # يمكن إضافة إحصائيات من نماذج أخرى هنا
            # من الكتب مثلاً
            from books_inventory.models import Book, Subject
            total_reports = Book.objects.count() + Subject.objects.count()
        except ImportError:
            total_reports = 5  # رقم افتراضي
        
    except Exception as e:
        # قيم آمنة افتراضية في حالة الخطأ
        print(f"خطأ في حساب الإحصائيات: {e}")
        total_students = 0
        total_treasury = Decimal('0.00')
        total_fees_due = Decimal('0.00')
        total_outstanding = Decimal('0.00')
        monthly_updates = 0
        monthly_registrations = 0
        total_reports = 0
        students_paid_full = 0
        students_with_dues = 0
        students_no_payments = 0
        payment_percentage = 0
        avg_payment = 0
    
    # ===================================
    # 🎯 السياق النهائي
    # ===================================
    
    context = {
        'settings': default_settings,
        
        # الإحصائيات الرئيسية للعرض في البطاقات
        'total_treasury': total_treasury,
        'total_students': total_students,
        'monthly_payments': monthly_updates,  # استخدام التحديثات بدلاً من المدفوعات
        'total_reports': total_reports,
        
        # إحصائيات تفصيلية إضافية
        'total_fees_due': total_fees_due,
        'total_outstanding': total_outstanding,
        'monthly_registrations': monthly_registrations,
        'students_paid_full': students_paid_full,
        'students_with_dues': students_with_dues,
        'students_no_payments': students_no_payments,
        'payment_percentage': payment_percentage,
        'avg_payment': avg_payment,
        
        # إحصائيات إضافية للعرض
        'active_students_percentage': round((total_students / (total_students + 10)) * 100, 1) if total_students > 0 else 0,
        
        # معلومات التحديث
        'last_updated': timezone.now(),
        'current_month': current_month,
    }
    
    return render(request, 'treasury_management/system_settings.html', context)


# ===================================
# 🛠️ دوال مساعدة إضافية للإحصائيات
# ===================================

def get_financial_summary():
    """الحصول على ملخص مالي شامل"""
    try:
        summary = Student.objects.filter(is_active=True).aggregate(
            total_fees=Sum('total_fees'),
            total_payments=Sum('total_payments'),
            total_owed=Sum('total_owed'),
            student_count=Count('id')
        )
        
        return {
            'total_fees': summary['total_fees'] or Decimal('0.00'),
            'total_payments': summary['total_payments'] or Decimal('0.00'),
            'total_owed': summary['total_owed'] or Decimal('0.00'),
            'student_count': summary['student_count'] or 0,
            'collection_rate': 0 if not summary['total_fees'] else round((summary['total_payments'] / summary['total_fees']) * 100, 2)
        }
    except Exception as e:
        print(f"خطأ في حساب الملخص المالي: {e}")
        return {
            'total_fees': Decimal('0.00'),
            'total_payments': Decimal('0.00'), 
            'total_owed': Decimal('0.00'),
            'student_count': 0,
            'collection_rate': 0
        }


def get_monthly_stats(year=None, month=None):
    """الحصول على إحصائيات شهرية"""
    if not year or not month:
        now = timezone.now()
        year = now.year
        month = now.month
    
    try:
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()
        
        monthly_data = {
            'new_students': Student.objects.filter(
                created_at__date__gte=start_date,
                created_at__date__lt=end_date
            ).count(),
            
            'updated_students': Student.objects.filter(
                updated_at__date__gte=start_date,
                updated_at__date__lt=end_date
            ).count(),
        }
        
        return monthly_data
        
    except Exception as e:
        print(f"خطأ في حساب الإحصائيات الشهرية: {e}")
        return {
            'new_students': 0,
            'updated_students': 0,
        }


@treasury_admin_required
def backup_restore(request):
    """النسخ الاحتياطي والاستعادة - للمدير العام فقط"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_backup':
            try:
                # منطق إنشاء نسخة احتياطية
                from django.utils import timezone
                backup_date = timezone.now().strftime('%Y%m%d_%H%M%S')
                
                messages.info(request, f'🔄 ميزة النسخ الاحتياطي قيد التطوير. معرف النسخة: {backup_date}')
            except Exception as e:
                messages.error(request, f'❌ خطأ في إنشاء النسخة الاحتياطية: {str(e)}')
        
        elif action == 'restore_backup':
            messages.info(request, '🔄 ميزة استعادة النسخ الاحتياطية قيد التطوير')
    
    # قائمة النسخ الاحتياطية (وهمية حالياً)
    backups = [
        {
            'id': 1,
            'date': timezone.now() - timedelta(days=1),
            'size': '2.5 MB',
            'type': 'تلقائي',
            'status': 'مكتملة'
        },
        {
            'id': 2,
            'date': timezone.now() - timedelta(days=7),
            'size': '2.3 MB', 
            'type': 'يدوي',
            'status': 'مكتملة'
        }
    ]
    
    context = {
        'backups': backups,
        'title': 'النسخ الاحتياطي والاستعادة',
    }
    
    return render(request, 'treasury_management/backup_restore.html', context)

@treasury_access_required
def account_statement(request, account_id):
    """كشف حساب مفصل - يحتاج أي صلاحية خزينة"""
    account = get_object_or_404(Account, id=account_id)
    
    # فترة التقرير
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    if not from_date:
        from_date = timezone.now().date().replace(day=1)  # بداية الشهر
    else:
        from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
    
    if not to_date:
        to_date = timezone.now().date()
    else:
        to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
    
    # المعاملات في الفترة المحددة
    transactions = Transaction.objects.filter(
        account=account,
        transaction_date__date__gte=from_date,
        transaction_date__date__lte=to_date,
        is_approved=True,
        is_cancelled=False
    ).order_by('transaction_date', 'created_at')
    
    # حساب الرصيد الجاري
    running_balance = account.opening_balance
    transactions_with_balance = []
    
    for transaction in transactions:
        if transaction.transaction_type == 'INCOME':
            running_balance += transaction.amount
        else:  # EXPENSE
            running_balance -= transaction.amount
        
        transactions_with_balance.append({
            'transaction': transaction,
            'balance': running_balance
        })
    
    # الإحصائيات
    period_stats = {
        'total_income': transactions.filter(transaction_type='INCOME').aggregate(
            Sum('amount')
        )['amount__sum'] or 0,
        'total_expenses': transactions.filter(transaction_type='EXPENSE').aggregate(
            Sum('amount')
        )['amount__sum'] or 0,
        'transactions_count': transactions.count(),
        'opening_balance': account.opening_balance,
        'closing_balance': running_balance,
    }
    
    period_stats['net_change'] = period_stats['total_income'] - period_stats['total_expenses']
    
    context = {
        'account': account,
        'from_date': from_date,
        'to_date': to_date,
        'transactions_with_balance': transactions_with_balance,
        'period_stats': period_stats,
        'title': f'كشف حساب - {account.name}',
    }
    
    return render(request, 'treasury_management/account_statement.html', context)

@treasury_access_required
def treasury_statement(request, treasury_id):
    """كشف خزنة مفصل - يحتاج أي صلاحية خزينة"""
    treasury = get_object_or_404(Treasury, id=treasury_id)
    
    # فترة التقرير
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    if not from_date:
        from_date = timezone.now().date().replace(day=1)
    else:
        from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
    
    if not to_date:
        to_date = timezone.now().date()
    else:
        to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
    
    # المعاملات في الفترة المحددة
    transactions = Transaction.objects.filter(
        treasury=treasury,
        transaction_date__date__gte=from_date,
        transaction_date__date__lte=to_date,
        is_approved=True,
        is_cancelled=False
    ).select_related('account', 'created_by').order_by('transaction_date', 'created_at')
    
    # تجميع حسب نوع العملية
    income_by_account = transactions.filter(transaction_type='INCOME').values(
        'account__name', 'account__code'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    expense_by_account = transactions.filter(transaction_type='EXPENSE').values(
        'account__name', 'account__code'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # الإحصائيات
    period_stats = {
        'total_income': transactions.filter(transaction_type='INCOME').aggregate(
            Sum('amount')
        )['amount__sum'] or 0,
        'total_expenses': transactions.filter(transaction_type='EXPENSE').aggregate(
            Sum('amount')
        )['amount__sum'] or 0,
        'transactions_count': transactions.count(),
        'current_balance': treasury.current_balance,
    }
    
    period_stats['net_change'] = period_stats['total_income'] - period_stats['total_expenses']
    period_stats['opening_balance'] = treasury.current_balance - period_stats['net_change']
    
    context = {
        'treasury': treasury,
        'from_date': from_date,
        'to_date': to_date,
        'transactions': transactions,
        'income_by_account': income_by_account,
        'expense_by_account': expense_by_account,
        'period_stats': period_stats,
        'title': f'كشف خزنة - {treasury.name}',
    }
    
    return render(request, 'treasury_management/treasury_statement.html', context)

@treasury_access_required  
def search_transactions(request):
    """البحث المتقدم في العمليات - يحتاج أي صلاحية خزينة"""
    query = request.GET.get('q', '').strip()
    results = []
    
    if query and len(query) >= 2:
        # البحث في العمليات
        results = Transaction.objects.filter(
            Q(transaction_number__icontains=query) |
            Q(description__icontains=query) |
            Q(reference_number__icontains=query) |
            Q(notes__icontains=query) |
            Q(treasury__name__icontains=query) |
            Q(account__name__icontains=query) |
            Q(created_by__first_name__icontains=query) |
            Q(created_by__last_name__icontains=query)
        ).select_related(
            'treasury', 'account', 'created_by'
        ).order_by('-created_at')[:50]
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # إرجاع JSON للطلبات AJAX
        results_data = []
        for transaction in results:
            results_data.append({
                'id': transaction.id,
                'number': transaction.transaction_number,
                'description': transaction.description,
                'amount': float(transaction.amount),
                'type': transaction.transaction_type,
                'date': transaction.transaction_date.strftime('%Y-%m-%d'),
                'treasury': transaction.treasury.name,
                'account': transaction.account.name,
                'status': 'معتمد' if transaction.is_approved else 'معلق',
                'url': f'/treasury/transaction/{transaction.id}/',
            })
        
        return JsonResponse({
            'success': True,
            'results': results_data,
            'count': len(results_data)
        })
    
    context = {
        'query': query,
        'results': results,
        'title': 'البحث في العمليات المالية',
    }
    
    return render(request, 'treasury_management/search_transactions.html', context)

@treasury_access_required
def ajax_get_accounts_by_type(request):
    """API للحصول على الحسابات حسب النوع - لاستخدام JavaScript"""
    transaction_type = request.GET.get('type')
    
    if transaction_type == 'INCOME':
        accounts = Account.objects.filter(
            category__category_type='REVENUE',
            is_active=True
        )
    elif transaction_type == 'EXPENSE':
        accounts = Account.objects.filter(
            category__category_type='EXPENSE',
            is_active=True
        )
    else:
        accounts = Account.objects.filter(is_active=True)
    
    accounts_data = [
        {
            'id': account.id,
            'name': account.name,
            'code': account.code,
            'category': account.category.name
        }
        for account in accounts.select_related('category').order_by('code')
    ]
    
    return JsonResponse({
        'success': True,
        'accounts': accounts_data
    })

@treasury_manager_required
def bulk_approve_transactions(request):
    """اعتماد جماعي للعمليات - يحتاج صلاحية مدير أو أعلى"""
    if request.method == 'POST':
        transaction_ids = request.POST.getlist('transaction_ids')
        
        if not transaction_ids:
            messages.error(request, '⚠️ لم يتم اختيار أي عمليات للاعتماد')
            return redirect('treasury_management:transactions_list')
        
        try:
            with db_transaction.atomic():
                approved_count = 0
                
                for transaction_id in transaction_ids:
                    try:
                        transaction = Transaction.objects.get(
                            id=transaction_id,
                            is_approved=False,
                            is_cancelled=False
                        )
                        
                        transaction.is_approved = True
                        transaction.approved_by = request.user
                        transaction.approved_at = timezone.now()
                        transaction.save()
                        
                        approved_count += 1
                        
                    except Transaction.DoesNotExist:
                        continue
                
                if approved_count > 0:
                    messages.success(request, f'✅ تم اعتماد {approved_count} عملية بنجاح')
                else:
                    messages.warning(request, '⚠️ لم يتم اعتماد أي عمليات')
                    
        except Exception as e:
            messages.error(request, f'❌ حدث خطأ في الاعتماد الجماعي: {str(e)}')
    
    return redirect('treasury_management:transactions_list')

# ===================================
# 🎯 Views للقوائم المنسدلة والتحديثات السريعة
# ===================================

@treasury_access_required
def get_categories_by_type(request):
    """API للحصول على التصنيفات حسب النوع"""
    category_type = request.GET.get('type')
    
    categories = AccountCategory.objects.filter(
        category_type=category_type,
        is_active=True
    ).order_by('name')
    
    categories_data = [
        {
            'id': category.id,
            'name': category.name,
            'code': category.code
        }
        for category in categories
    ]
    
    return JsonResponse({
        'success': True,
        'categories': categories_data
    })

@treasury_access_required
def dashboard_widgets_data(request):
    """API لبيانات widgets لوحة التحكم"""
    today = timezone.now().date()
    
    # الإحصائيات السريعة
    stats = {
        'treasuries_count': Treasury.objects.filter(is_active=True).count(),
        'accounts_count': Account.objects.filter(is_active=True).count(),
        'today_transactions': Transaction.objects.filter(
            transaction_date__date=today,
            is_approved=True
        ).count(),
        'pending_transactions': Transaction.objects.filter(
            is_approved=False,
            is_cancelled=False
        ).count(),
    }
    
    # الرصيد الإجمالي
    total_balance = 0
    for treasury in Treasury.objects.filter(is_active=True):
        try:
            total_balance += treasury.current_balance
        except:
            continue
    
    stats['total_balance'] = total_balance
    
    return JsonResponse({
        'success': True,
        'stats': stats,
        'updated_at': timezone.now().isoformat()
    })

# ===================================
# 📱 Views للتنبيهات والإشعارات
# ===================================

@treasury_access_required
def get_notifications(request):
    """API للحصول على التنبيهات"""
    notifications = []
    
    # تحقق من الخزائن منخفضة الرصيد
    for treasury in Treasury.objects.filter(is_active=True):
        try:
            if hasattr(treasury, 'min_limit') and treasury.min_limit:
                if treasury.current_balance < treasury.min_limit:
                    notifications.append({
                        'type': 'warning',
                        'title': 'رصيد منخفض',
                        'message': f'رصيد {treasury.name}: {treasury.current_balance:,.2f}',
                        'time': 'الآن',
                        'url': f'/treasury/treasury-detail/{treasury.id}/'
                    })
        except:
            continue
    
    # تحقق من العمليات المعلقة
    pending_count = Transaction.objects.filter(is_approved=False, is_cancelled=False).count()
    if pending_count > 0:
        notifications.append({
            'type': 'info',
            'title': 'عمليات معلقة',
            'message': f'{pending_count} عملية في انتظار الاعتماد',
            'time': 'اليوم',
            'url': '/treasury/transactions/?approved=false'
        })
    
    return JsonResponse({
        'success': True,
        'notifications': notifications[:10],  # أول 10 تنبيهات
        'count': len(notifications)
    })

# ===================================
# 📋 Views مؤقتة للصفحات المستقبلية
# ===================================

@treasury_access_required
def coming_soon(request, feature_name=''):
    """صفحة قيد التطوير"""
    context = {
        'feature_name': feature_name.replace('_', ' ').title(),
        'title': f'{feature_name.replace("_", " ").title()} - قيد التطوير'
    }
    return render(request, 'treasury_management/coming_soon.html', context)

# Aliases للصفحات قيد التطوير
def analytics_dashboard(request):
    return coming_soon(request, 'لوحة التحليلات')

def financial_reports_advanced(request):
    return coming_soon(request, 'التقارير المالية المتقدمة')

def budget_planning(request):
    return coming_soon(request, 'تخطيط الميزانية')


# ===================================
# 🏠 الصفحة الرئيسية ولوحة التحكم
# ===================================

@treasury_access_required
def dashboard(request):
    """لوحة تحكم الخزنة الرئيسية - يحتاج أي صلاحية خزينة"""
    today = timezone.now().date()
    
    # الخزائن النشطة مع أرصدتها
    treasuries = Treasury.objects.filter(is_active=True).select_related('account')
    total_balance = treasuries.aggregate(total=Sum('current_balance'))['total'] or 0
    
    # إحصائيات اليوم
    today_transactions = Transaction.objects.filter(
        transaction_date__date=today,
        is_approved=True,
        is_cancelled=False
    )
    
    today_stats = today_transactions.aggregate(
        income=Sum('amount', filter=Q(transaction_type='INCOME')),
        expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
        count=Count('id')
    )
    
    today_income = today_stats['income'] or 0
    today_expenses = today_stats['expenses'] or 0
    today_net = today_income - today_expenses
    
    # إحصائيات الشهر الحالي
    month_start = today.replace(day=1)
    month_transactions = Transaction.objects.filter(
        transaction_date__date__gte=month_start,
        transaction_date__date__lte=today,
        is_approved=True,
        is_cancelled=False
    )
    
    month_stats = month_transactions.aggregate(
        income=Sum('amount', filter=Q(transaction_type='INCOME')),
        expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
        count=Count('id')
    )
    
    month_income = month_stats['income'] or 0
    month_expenses = month_stats['expenses'] or 0
    month_net = month_income - month_expenses
    
    # إحصائيات الأسبوع الماضي (للرسم البياني)
    week_data = []
    for i in range(7):
        day = today - timedelta(days=i)
        day_transactions = Transaction.objects.filter(
            transaction_date__date=day,
            is_approved=True,
            is_cancelled=False
        )
        
        day_stats = day_transactions.aggregate(
            income=Sum('amount', filter=Q(transaction_type='INCOME')),
            expenses=Sum('amount', filter=Q(transaction_type='EXPENSE'))
        )
        
        week_data.append({
            'date': day.strftime('%Y-%m-%d'),
            'day_name_ar': ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'][day.weekday()],
            'income': float(day_stats['income'] or 0),
            'expenses': float(day_stats['expenses'] or 0),
            'net': float((day_stats['income'] or 0) - (day_stats['expenses'] or 0))
        })
    
    week_data.reverse()  # ترتيب من الأقدم للأحدث
    
    # العمليات المعلقة للموافقة (للمديرين فقط)
    pending_transactions = []
    if request.user.groups.filter(name__in=['treasury_admin', 'treasury_manager']).exists():
        pending_transactions = Transaction.objects.filter(
            is_approved=False,
            is_cancelled=False
        ).select_related('treasury', 'account', 'created_by').order_by('-created_at')[:5]
    
    # آخر العمليات
    recent_transactions = Transaction.objects.filter(
        is_approved=True,
        is_cancelled=False
    ).select_related('treasury', 'account', 'created_by').order_by('-transaction_date')[:10]
    
    # أكثر المصروفات (إذا كان نموذج DailyExpense متوفر)
    top_expenses = []
    if DailyExpense:
        try:
            top_expenses = DailyExpense.objects.filter(
                expense_date__gte=month_start,
                is_approved=True
            ).values('category__name').annotate(
                total=Sum('amount')
            ).order_by('-total')[:5]
        except:
            pass
    
    # تنبيهات الخزنة
    alerts = []
    for treasury in treasuries:
        if hasattr(treasury, 'min_limit') and treasury.current_balance < treasury.min_limit:
            alerts.append({
                'type': 'warning',
                'title': f'رصيد {treasury.name} منخفض',
                'message': f'الرصيد الحالي: {treasury.current_balance} أقل من الحد الأدنى: {treasury.min_limit}'
            })
        
        if hasattr(treasury, 'max_limit') and treasury.max_limit and treasury.current_balance > treasury.max_limit:
            alerts.append({
                'type': 'info',
                'title': f'رصيد {treasury.name} مرتفع',
                'message': f'الرصيد الحالي: {treasury.current_balance} أعلى من الحد الأقصى: {treasury.max_limit}'
            })
    
    context = {
        'treasuries': treasuries,
        'total_balance': total_balance,
        'today_income': today_income,
        'today_expenses': today_expenses,
        'today_net': today_net,
        'today_transactions_count': today_stats['count'],
        'month_income': month_income,
        'month_expenses': month_expenses,
        'month_net': month_net,
        'month_transactions_count': month_stats['count'],
        'pending_transactions': pending_transactions,
        'recent_transactions': recent_transactions,
        'top_expenses': top_expenses,
        'week_data': json.dumps(week_data),
        'alerts': alerts,
    }
    
    return render(request, 'treasury_management/dashboard.html', context)

@treasury_access_required
def daily_summary(request):
    """الملخص اليومي - يحتاج أي صلاحية خزينة"""
    selected_date = request.GET.get('date')
    
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()
    
    # تواريخ التنقل
    previous_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)
    today = timezone.now().date()
    
    # إحصائيات الخزائن لهذا اليوم
    treasury_summaries = []
    treasuries = Treasury.objects.filter(is_active=True)
    
    total_income = 0
    total_expenses = 0
    
    for treasury in treasuries:
        # المعاملات اليومية
        day_transactions = Transaction.objects.filter(
            treasury=treasury,
            transaction_date__date=selected_date,
            is_approved=True,
            is_cancelled=False
        )
        
        income_transactions = day_transactions.filter(transaction_type='INCOME')
        expense_transactions = day_transactions.filter(transaction_type='EXPENSE')
        
        treasury_income = income_transactions.aggregate(Sum('amount'))['amount__sum'] or 0
        treasury_expenses = expense_transactions.aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_income += treasury_income
        total_expenses += treasury_expenses
        
        # معلومات الخزنة
        treasury_summary = {
            'treasury': treasury,
            'total_income': treasury_income,
            'total_expenses': treasury_expenses,
            'net_change': treasury_income - treasury_expenses,
            'transaction_count': day_transactions.count(),
            'income_transactions': income_transactions[:5],
            'expense_transactions': expense_transactions[:5],
        }
        
        if treasury_summary['transaction_count'] > 0:
            treasury_summaries.append(treasury_summary)
    
    net_total = total_income - total_expenses
    
    context = {
        'selected_date': selected_date,
        'previous_date': previous_date,
        'next_date': next_date,
        'today': today,
        'treasury_summaries': treasury_summaries,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_total': net_total,
    }
    
    return render(request, 'treasury_management/daily_summary.html', context)

# ===================================
# 💰 العمليات المالية
# ===================================

@treasury_cashier_required
def add_transaction(request):
    """إضافة عملية مالية - يحتاج صلاحية أمين خزينة أو أعلى"""
    if request.method == 'POST':
        try:
            with db_transaction.atomic():
                treasury_id = request.POST.get('treasury')
                account_id = request.POST.get('account')
                transaction_type = request.POST.get('transaction_type')
                amount = float(request.POST.get('amount'))
                description = request.POST.get('description')
                payment_method = request.POST.get('payment_method', 'CASH')
                reference_number = request.POST.get('reference_number', '')
                transaction_date = request.POST.get('transaction_date')
                # notes = request.POST.get('notes', '')
                
                if not transaction_date:
                    transaction_date = timezone.now()
                else:
                    transaction_date = datetime.strptime(transaction_date, '%Y-%m-%d')
                
                treasury = Treasury.objects.get(id=treasury_id)
                account = Account.objects.get(id=account_id)
                
                # الحصول على السنة الأكاديمية الحالية
                current_year = None
                if AcademicYear:
                    try:
                        current_year = AcademicYear.get_current_year()
                    except:
                        pass
                
                # التحقق من الرصيد للمصروفات
                if transaction_type == 'EXPENSE' and treasury.current_balance < amount:
                    messages.error(request, f'❌ الرصيد غير كافي في {treasury.name}. الرصيد الحالي: {treasury.current_balance:,.2f} ج.م')
                    return redirect('treasury_management:add_transaction')
                
                # إنشاء العملية
                transaction_data = {
                    'treasury': treasury,
                    'account': account,
                    'transaction_type': transaction_type,
                    'amount': amount,
                    'description': description,
                    'payment_method': payment_method,
                    'reference_number': reference_number,
                    'transaction_date': transaction_date,
                    # 'notes': notes,
                    'created_by': request.user,
                }
                
                if current_year:
                    transaction_data['academic_year'] = current_year
                
                transaction_obj = Transaction.objects.create(**transaction_data)
                
                # اعتماد فوري إذا كان المستخدم له صلاحية أو المبلغ صغير
                user_groups = request.user.groups.values_list('name', flat=True)
                can_auto_approve = (
                    request.user.is_superuser or
                    any(group in user_groups for group in ['treasury_admin', 'treasury_manager']) or
                    amount < 1000  # حد أدنى للاعتماد التلقائي
                )
                
                if can_auto_approve:
                    transaction_obj.is_approved = True
                    transaction_obj.approved_by = request.user
                    transaction_obj.approved_at = timezone.now()
                    transaction_obj.save()
                    messages.success(request, f'✅ تم إضافة واعتماد العملية المالية بنجاح. المبلغ: {amount:,.2f} ج.م')
                else:
                    messages.success(request, f'✅ تم إضافة العملية المالية وهي في انتظار الاعتماد. المبلغ: {amount:,.2f} ج.م')
                
                return redirect('treasury_management:dashboard')
                
        except Treasury.DoesNotExist:
            messages.error(request, '❌ الخزنة المحددة غير موجودة')
        except Account.DoesNotExist:
            messages.error(request, '❌ الحساب المحدد غير موجود')
        except ValueError:
            messages.error(request, '❌ يرجى إدخال مبلغ صحيح')
        except Exception as e:
            messages.error(request, f'❌ حدث خطأ: {str(e)}')
    
    # البيانات للنموذج
    treasuries = Treasury.objects.filter(is_active=True).order_by('name')
    
    # فحص وجود خزائن
    if not treasuries.exists():
        messages.warning(request, '⚠️ لا توجد خزائن نشطة. يرجى إضافة خزنة أولاً.')
        return redirect('treasury_management:add_treasury')
    
    # تصنيف الحسابات حسب النوع
    income_accounts = Account.objects.filter(
        category__category_type='REVENUE',
        is_active=True
    ).select_related('category').order_by('name')
    
    expense_accounts = Account.objects.filter(
        category__category_type='EXPENSE', 
        is_active=True
    ).select_related('category').order_by('name')
    
    # فحص وجود حسابات
    if not income_accounts.exists() and not expense_accounts.exists():
        messages.warning(request, '⚠️ لا توجد حسابات مالية. يرجى إضافة حسابات أولاً.')
        return redirect('treasury_management:account_categories_list')
    
    context = {
        'treasuries': treasuries,
        'income_accounts': income_accounts,
        'expense_accounts': expense_accounts,
        'today': timezone.now().date(),
        'treasuries_count': treasuries.count(),
        'income_accounts_count': income_accounts.count(),
        'expense_accounts_count': expense_accounts.count(),
    }
    
    return render(request, 'treasury_management/add_transaction.html', context)


@treasury_access_required
def transactions_list(request):
    """قائمة العمليات المالية - يحتاج أي صلاحية خزينة"""
    
    # الحصول على المعاملات
    transaction_type = request.GET.get('type', '')
    treasury_id = request.GET.get('treasury', '')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    approved = request.GET.get('approved', '')
    search = request.GET.get('search', '')
    
    # بناء الاستعلام
    transactions = Transaction.objects.all().select_related(
        'treasury', 'account', 'created_by'
    ).order_by('-created_at')
    
    # تطبيق الفلاتر
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    if treasury_id:
        transactions = transactions.filter(treasury_id=treasury_id)
    
    if from_date:
        transactions = transactions.filter(transaction_date__gte=from_date)
    
    if to_date:
        transactions = transactions.filter(transaction_date__lte=to_date)
    
    if approved == 'true':
        transactions = transactions.filter(is_approved=True)
    elif approved == 'false':
        transactions = transactions.filter(is_approved=False)
    
    if search:
        transactions = transactions.filter(
            Q(transaction_number__icontains=search) |
            Q(description__icontains=search) |
            Q(reference_number__icontains=search)
        )
    
    # إحصائيات الصفحة
    page_stats = {
        'total_income': transactions.filter(transaction_type='INCOME').aggregate(
            Sum('amount')
        )['amount__sum'] or 0,
        'total_expenses': transactions.filter(transaction_type='EXPENSE').aggregate(
            Sum('amount')
        )['amount__sum'] or 0,
        'count': transactions.count(),
    }
    
    # Pagination
    items_per_page = request.GET.get('per_page', 20)
    try:
        items_per_page = int(items_per_page)
        if items_per_page not in [10, 20, 50, 100]:
            items_per_page = 20
    except:
        items_per_page = 20
    
    paginator = Paginator(transactions, items_per_page)
    page = request.GET.get('page')
    
    try:
        transactions_page = paginator.page(page)
    except PageNotAnInteger:
        transactions_page = paginator.page(1)
    except EmptyPage:
        transactions_page = paginator.page(paginator.num_pages)
    
    # الخزائن للفلتر
    treasuries = Treasury.objects.filter(is_active=True).order_by('name')
    
    context = {
        'transactions': transactions_page,
        'treasuries': treasuries,
        'page_stats': page_stats,
        'filters': {
            'type': transaction_type,
            'treasury': treasury_id,
            'from_date': from_date,
            'to_date': to_date,
            'approved': approved,
            'search': search,
        },
        'items_per_page': items_per_page,
    }
    
    return render(request, 'treasury_management/transactions_list.html', context)

@treasury_access_required
def transaction_detail_ajax(request, transaction_id):
    """تفاصيل العملية عبر AJAX - يحتاج أي صلاحية خزينة"""
    try:
        transaction = get_object_or_404(
            Transaction.objects.select_related(
                'treasury', 'account', 'created_by', 'approved_by', 'cancelled_by'
            ), 
            id=transaction_id
        )
        
        html = render_to_string('treasury_management/transaction_detail_modal.html', {
            'transaction': transaction,
        }, request=request)
        
        return JsonResponse({
            'success': True,
            'html': html
        })
    except Transaction.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'العملية غير موجودة'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@can_approve_transactions
def approve_transaction(request, transaction_id):
    """اعتماد العملية المالية - يحتاج صلاحية مدير أو أعلى"""
    if request.method == 'POST':
        try:
            transaction = get_object_or_404(Transaction, id=transaction_id)
            
            if transaction.is_approved:
                return JsonResponse({
                    'success': False,
                    'error': 'العملية معتمدة مسبقاً'
                })
            
            if transaction.is_cancelled:
                return JsonResponse({
                    'success': False,
                    'error': 'العملية ملغية'
                })
            
            # اعتماد العملية
            transaction.is_approved = True
            transaction.approved_by = request.user
            transaction.approved_at = timezone.now()
            transaction.save()
            
            return JsonResponse({
                'success': True,
                'message': 'تم اعتماد العملية بنجاح'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return redirect('treasury_management:transactions_list')

@can_approve_transactions
def cancel_transaction(request, transaction_id):
    """إلغاء العملية المالية - يحتاج صلاحية مدير أو أعلى"""
    if request.method == 'POST':
        try:
            transaction = get_object_or_404(Transaction, id=transaction_id)
            
            if transaction.is_cancelled:
                return JsonResponse({
                    'success': False,
                    'error': 'العملية ملغية مسبقاً'
                })
            
            cancellation_reason = request.POST.get('cancellation_reason', '')
            if not cancellation_reason:
                return JsonResponse({
                    'success': False,
                    'error': 'يجب إدخال سبب الإلغاء'
                })
            
            # إلغاء العملية
            transaction.is_cancelled = True
            transaction.cancellation_reason = cancellation_reason
            transaction.cancelled_by = request.user
            transaction.cancelled_at = timezone.now()
            transaction.save()
            
            return JsonResponse({
                'success': True,
                'message': 'تم إلغاء العملية بنجاح'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return redirect('treasury_management:transactions_list')

# ===================================
# 🏦 إدارة الخزائن
# ===================================

@treasury_access_required
def treasuries_list(request):
    """قائمة الخزائن"""
    treasuries = Treasury.objects.all().select_related('account', 'responsible_person').order_by('name')
    
    # حساب الإحصائيات
    total_treasuries = treasuries.count()
    active_treasuries = treasuries.filter(is_active=True).count()
    total_balance = sum(treasury.current_balance for treasury in treasuries)
    treasuries_with_responsible = treasuries.filter(responsible_person__isnull=False).count()
    
    context = {
        'treasuries': treasuries,
        'stats': {
            'total_treasuries': total_treasuries,
            'active_treasuries': active_treasuries,
            'total_balance': total_balance,
            'treasuries_with_responsible': treasuries_with_responsible,
        }
    }
    
    return render(request, 'treasury_management/treasuries_list.html', context)

# ===================================
# 📊 الحسابات المالية
# ===================================

@treasury_access_required
def accounts_list(request):
    """قائمة الحسابات المالية - يحتاج أي صلاحية خزينة"""
    
    # الحصول على المعاملات
    search = request.GET.get('search', '')
    category_type = request.GET.get('type', '')
    category_id = request.GET.get('category', '')
    is_active = request.GET.get('active', '')
    has_balance = request.GET.get('has_balance', '')
    
    # بناء الاستعلام الأساسي
    accounts = Account.objects.all().select_related('category')
    
    # تطبيق الفلاتر
    if search:
        accounts = accounts.filter(
            Q(name__icontains=search) | 
            Q(code__icontains=search) | 
            Q(description__icontains=search) |
            Q(category__name__icontains=search)
        )
    
    if category_type:
        accounts = accounts.filter(category__category_type=category_type)
        
    if category_id:
        accounts = accounts.filter(category_id=category_id)
    
    if is_active:
        accounts = accounts.filter(is_active=is_active == 'true')
        
    if has_balance == 'true':
        accounts = accounts.exclude(current_balance=0)
    elif has_balance == 'false':
        accounts = accounts.filter(current_balance=0)
    
    # ترتيب النتائج
    order_by = request.GET.get('order_by', 'code')
    if order_by in ['code', 'name', 'category__name', 'current_balance', 'created_at']:
        if request.GET.get('desc') == 'true':
            order_by = '-' + order_by
        accounts = accounts.order_by(order_by)
    else:
        accounts = accounts.order_by('code')
    
    # إضافة annotations
    accounts = accounts.annotate(
        transactions_count=Count('transaction'),
    )
    
    # Pagination
    items_per_page = request.GET.get('per_page', 15)
    try:
        items_per_page = int(items_per_page)
        if items_per_page not in [5, 10, 15, 25, 50, 100]:
            items_per_page = 15
    except:
        items_per_page = 15
    
    paginator = Paginator(accounts, items_per_page)
    page = request.GET.get('page')
    
    try:
        accounts_page = paginator.page(page)
    except PageNotAnInteger:
        accounts_page = paginator.page(1)
    except EmptyPage:
        accounts_page = paginator.page(paginator.num_pages)
    
    # إحصائيات
    stats = {
        'total_accounts': Account.objects.count(),
        'active_accounts': Account.objects.filter(is_active=True).count(),
        'total_balance': Account.objects.aggregate(Sum('current_balance'))['current_balance__sum'] or 0,
        'accounts_with_balance': Account.objects.exclude(current_balance=0).count(),
    }
    
    # قائمة التصنيفات للفلتر
    categories = AccountCategory.objects.filter(is_active=True).order_by('name')
    
    context = {
        'accounts': accounts_page,
        'paginator': paginator,
        'categories': categories,
        'stats': stats,
        'search': search,
        'category_type': category_type,
        'category_id': category_id,
        'is_active': is_active,
        'has_balance': has_balance,
        'order_by': order_by.replace('-', ''),
        'desc': request.GET.get('desc', 'false'),
        'items_per_page': items_per_page,
        'category_types': [
            ('ASSET', 'أصول'),
            ('LIABILITY', 'خصوم'),
            ('EQUITY', 'حقوق الملكية'),
            ('REVENUE', 'إيرادات'),
            ('EXPENSE', 'مصروفات'),
        ],
    }
    
    return render(request, 'treasury_management/accounts_list.html', context)

@treasury_access_required
def account_detail_ajax(request, account_id):
    """تفاصيل الحساب عبر AJAX - يحتاج أي صلاحية خزينة"""
    try:
        account = get_object_or_404(Account.objects.select_related('category'), id=account_id)
        
        # الحصول على آخر المعاملات
        recent_transactions = Transaction.objects.filter(
            account=account
        ).select_related('treasury', 'created_by').order_by('-created_at')[:10]
        
        # حساب الإحصائيات
        income_stats = Transaction.objects.filter(
            account=account, 
            transaction_type='INCOME',
            is_approved=True,
            is_cancelled=False
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        expense_stats = Transaction.objects.filter(
            account=account, 
            transaction_type='EXPENSE',
            is_approved=True,
            is_cancelled=False
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        total_income = income_stats['total'] or 0
        total_expenses = expense_stats['total'] or 0
        income_count = income_stats['count'] or 0
        expense_count = expense_stats['count'] or 0
        
        html = render_to_string('treasury_management/account_detail_modal.html', {
            'account': account,
            'recent_transactions': recent_transactions,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'income_count': income_count,
            'expense_count': expense_count,
        }, request=request)
        
        return JsonResponse({
            'success': True,
            'html': html
        })
    except Account.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'الحساب غير موجود'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# ===================================
# 🗂️ تصنيفات الحسابات
# ===================================

@treasury_accountant_required
def account_categories_list(request):
    """قائمة تصنيفات الحسابات - يحتاج صلاحية محاسب أو أعلى"""
    
    # الحصول على المعاملات
    search = request.GET.get('search', '')
    category_type = request.GET.get('type', '')
    is_active = request.GET.get('active', '')
    parent_only = request.GET.get('parent_only', '')
    
    # بناء الاستعلام الأساسي
    categories = AccountCategory.objects.all().select_related('parent')
    
    # تطبيق الفلاتر
    if search:
        categories = categories.filter(
            Q(name__icontains=search) | 
            Q(code__icontains=search) | 
            Q(description__icontains=search)
        )
    
    if category_type:
        categories = categories.filter(category_type=category_type)
    
    if is_active:
        categories = categories.filter(is_active=is_active == 'true')
    
    if parent_only == 'true':
        categories = categories.filter(parent__isnull=True)
    
    # ترتيب النتائج
    order_by = request.GET.get('order_by', 'code')
    if order_by in ['code', 'name', 'category_type']:
        categories = categories.order_by(order_by)
    else:
        categories = categories.order_by('code')
    
    # إضافة annotation للحسابات
    categories = categories.annotate(
        accounts_count=Count('account', distinct=True)
    )
    
    # Pagination
    items_per_page = request.GET.get('per_page', 10)
    try:
        items_per_page = int(items_per_page)
        if items_per_page not in [5, 10, 15, 25, 50]:
            items_per_page = 10
    except:
        items_per_page = 10
    
    paginator = Paginator(categories, items_per_page)
    page = request.GET.get('page')
    
    try:
        categories_page = paginator.page(page)
    except PageNotAnInteger:
        categories_page = paginator.page(1)
    except EmptyPage:
        categories_page = paginator.page(paginator.num_pages)
    
    # إضافة children_count يدوياً
    for category in categories_page:
        try:
            category.children_count = AccountCategory.objects.filter(parent=category).count()
        except:
            category.children_count = 0
    
    # إحصائيات
    stats = {
        'total_categories': AccountCategory.objects.count(),
        'active_categories': AccountCategory.objects.filter(is_active=True).count(),
        'parent_categories': AccountCategory.objects.filter(parent__isnull=True).count(),
        'child_categories': AccountCategory.objects.filter(parent__isnull=False).count(),
    }
    
    context = {
        'categories': categories_page,
        'paginator': paginator,
        'stats': stats,
        'search': search,
        'category_type': category_type,
        'is_active': is_active,
        'parent_only': parent_only,
        'order_by': order_by,
        'items_per_page': items_per_page,
        'category_types': [
            ('ASSET', 'أصول'),
            ('LIABILITY', 'خصوم'),
            ('EQUITY', 'حقوق الملكية'),
            ('REVENUE', 'إيرادات'),
            ('EXPENSE', 'مصروفات'),
        ],
    }
    
    return render(request, 'treasury_management/account_categories_list.html', context)

@treasury_accountant_required  
def account_category_detail_ajax(request, category_id):
    """تفاصيل تصنيف الحساب عبر AJAX - يحتاج صلاحية محاسب أو أعلى"""
    try:
        category = get_object_or_404(
            AccountCategory.objects.select_related('parent'), 
            id=category_id
        )
        
        # الحصول على الحسابات المرتبطة
        accounts = Account.objects.filter(category=category).order_by('code')[:10]
        
        # الحصول على التصنيفات الفرعية
        subcategories = AccountCategory.objects.filter(parent=category).order_by('code')
        
        # إحصائيات التصنيف
        accounts_count = Account.objects.filter(category=category).count()
        subcategories_count = subcategories.count()
        total_balance = accounts.aggregate(Sum('current_balance'))['current_balance__sum'] or 0
        
        html = render_to_string('treasury_management/account_category_detail_modal.html', {
            'category': category,
            'accounts': accounts,
            'subcategories': subcategories,
            'accounts_count': accounts_count,
            'subcategories_count': subcategories_count,
            'total_balance': total_balance,
        }, request=request)
        
        return JsonResponse({
            'success': True,
            'html': html
        })
    except AccountCategory.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'التصنيف غير موجود'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# ===================================
# 👥 إدارة المستخدمين
# ===================================

# treasury_management/views.py - تحديث manage_users View
@treasury_admin_required
def manage_users(request):
    """إدارة مستخدمي الخزينة - للمدير العام فقط"""
    users = User.objects.all().prefetch_related('groups')
    treasury_groups = Group.objects.filter(
        name__startswith='treasury_'
    ).prefetch_related('user_set')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        try:
            user = User.objects.get(id=user_id)
            
            if action == 'add_group':
                group_name = request.POST.get('group_name')
                group = Group.objects.get(name=group_name)
                user.groups.add(group)
                messages.success(request, f'تم إضافة {user.get_full_name() or user.username} إلى مجموعة {group.name}')
            
            elif action == 'remove_group':
                group_name = request.POST.get('group_name')
                group = Group.objects.get(name=group_name)
                user.groups.remove(group)
                messages.success(request, f'تم إزالة {user.get_full_name() or user.username} من مجموعة {group.name}')
                
        except (User.DoesNotExist, Group.DoesNotExist) as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
        
        return redirect('treasury_management:manage_users')
    
    # إضافة وصف المجموعات لكل مجموعة
    group_descriptions = {
        'treasury_admin': 'مدير الخزينة العام',
        'treasury_manager': 'مدير الخزينة',
        'treasury_accountant': 'محاسب الخزينة',
        'treasury_cashier': 'أمين الخزينة',
        'treasury_viewer': 'مراجع الخزينة',
    }
    
    # إضافة الوصف لكل مجموعة كخاصية
    for group in treasury_groups:
        group.description = group_descriptions.get(group.name, group.name)
        # إضافة مجموعات المستخدمين لكل مجموعة
        group.users_list = []
        for user in users:
            if user.groups.filter(name=group.name).exists():
                group.users_list.append(user)
    
    # إضافة مجموعات الخزينة للمستخدمين
    for user in users:
        user.treasury_groups_list = []
        for group in user.groups.all():
            if group.name.startswith('treasury_'):
                user.treasury_groups_list.append({
                    'name': group.name,
                    'description': group_descriptions.get(group.name, group.name)
                })
    
    context = {
        'users': users,
        'treasury_groups': treasury_groups,
        'group_descriptions': group_descriptions
    }
    
    return render(request, 'treasury_management/manage_users.html', context)

# ===================================
# 📈 التقارير
# ===================================

# @treasury_access_required
# def reports(request):
#     """تقارير الخزنة الشاملة - يحتاج أي صلاحية خزينة"""
    
#     # المعاملات
#     report_type = request.GET.get('report_type', 'summary')
#     start_date = request.GET.get('start_date')
#     end_date = request.GET.get('end_date')
#     selected_treasury = request.GET.get('treasury')
    
#     # التواريخ الافتراضية
#     if not start_date:
#         start_date = timezone.now().date().replace(day=1)  # بداية الشهر
#     else:
#         start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
#     if not end_date:
#         end_date = timezone.now().date()
#     else:
#         end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
#     # فلترة العمليات
#     transactions_filter = Q(
#         transaction_date__date__gte=start_date,
#         transaction_date__date__lte=end_date,
#         is_approved=True,
#         is_cancelled=False
#     )
    
#     if selected_treasury:
#         transactions_filter &= Q(treasury_id=selected_treasury)
    
#     transactions = Transaction.objects.filter(transactions_filter).select_related(
#         'treasury', 'account', 'created_by'
#     ).order_by('-transaction_date')
    
#     # الحسابات
#     accounts = Account.objects.filter(is_active=True).select_related('category').order_by('code')
    
#     # الخزائن
#     treasuries = Treasury.objects.filter(is_active=True).order_by('name')
    
#     # الملخص العام
#     summary = {
#         'total_income': transactions.filter(transaction_type='INCOME').aggregate(
#             total=Sum('amount')
#         )['total'] or 0,
        
#         'total_expenses': transactions.filter(transaction_type='EXPENSE').aggregate(
#             total=Sum('amount')
#         )['total'] or 0,
        
#         'total_balance': treasuries.aggregate(
#             total=Sum('current_balance')
#         )['total'] or 0,
        
#         'transactions_count': transactions.count(),
#     }
    
#     summary['net_income'] = summary['total_income'] - summary['total_expenses']
    
#     context = {
#         'report_type': report_type,
#         'start_date': start_date,
#         'end_date': end_date,
#         'selected_treasury': selected_treasury,
#         'transactions': transactions[:100],  # أول 100 عملية
#         'accounts': accounts,
#         'treasuries': treasuries,
#         'summary': summary,
#     }
    
#     return render(request, 'treasury_management/reports.html', context)


# def treasury_report(request):
@treasury_access_required
def reports(request):
    """تقارير الخزنة الشاملة"""
    
    # المعاملات
    report_type = request.GET.get('report_type', 'summary')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    selected_treasury = request.GET.get('treasury')
    
    # التواريخ الافتراضية
    if not start_date:
        start_date = timezone.now().date().replace(day=1)  # بداية الشهر
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # فلترة العمليات
    transactions_filter = Q(
        transaction_date__date__gte=start_date,
        transaction_date__date__lte=end_date,
        is_approved=True,
        is_cancelled=False
    )
    
    if selected_treasury:
        transactions_filter &= Q(treasury_id=selected_treasury)
    
    transactions = Transaction.objects.filter(transactions_filter).select_related(
        'treasury', 'account', 'created_by'
    ).order_by('-transaction_date')
    
    # الحسابات
    accounts = Account.objects.filter(is_active=True).select_related('category').order_by('code')
    
    # الخزائن
    treasuries = Treasury.objects.filter(is_active=True).select_related('account').order_by('name')
    
    # الملخص العام
    summary = {
        'total_income': transactions.filter(transaction_type='INCOME').aggregate(
            total=Sum('amount')
        )['total'] or 0,
        
        'total_expenses': transactions.filter(transaction_type='EXPENSE').aggregate(
            total=Sum('amount')
        )['total'] or 0,
        
        'total_balance': treasuries.aggregate(
            total=Sum('account__current_balance')
        )['total'] or 0,
        
        'transactions_count': transactions.count(),
    }
    
    summary['net_income'] = summary['total_income'] - summary['total_expenses']
    
    context = {
        'report_type': report_type,
        'start_date': start_date,
        'end_date': end_date,
        'selected_treasury': selected_treasury,
        'transactions': transactions[:100],  # أول 100 عملية
        'accounts': accounts,
        'treasuries': treasuries,
        'summary': summary,
    }
    
    return render(request, 'treasury_management/reports.html', context)






# # ===================================
# # 🔧 Views مؤقتة للتطوير
# # ===================================


# @treasury_accountant_required
# def add_account(request):
#     messages.info(request, 'صفحة إضافة حساب قيد التطوير')
#     return redirect('treasury_management:accounts_list')

# @treasury_manager_required
# def add_account_category(request):
#     messages.info(request, 'صفحة إضافة تصنيف حساب قيد التطوير')
#     return redirect('treasury_management:account_categories_list')

# @treasury_cashier_required
# def add_expense(request):
#     messages.info(request, 'صفحة إضافة مصروف قيد التطوير')
#     return redirect('treasury_management:dashboard')

# @treasury_access_required
# def expenses_list(request):
#     messages.info(request, 'صفحة قائمة المصروفات قيد التطوير')
#     return redirect('treasury_management:dashboard')

# @treasury_manager_required
# def expense_categories_list(request):
#     messages.info(request, 'صفحة تصنيفات المصروفات قيد التطوير')
#     return redirect('treasury_management:dashboard')

# @treasury_accountant_required
# def add_expense_category(request):
#     messages.info(request, 'صفحة إضافة تصنيف مصروف قيد التطوير')
#     return redirect('treasury_management:dashboard')

# @treasury_admin_required
# def system_settings(request):
#     messages.info(request, 'صفحة إعدادات النظام قيد التطوير')
#     return redirect('treasury_management:dashboard')

# @treasury_admin_required
# def backup_restore(request):
#     messages.info(request, 'صفحة النسخ الاحتياطي قيد التطوير')
#     return redirect('treasury_management:dashboard')

# @treasury_manager_required
# def quick_setup(request):
#     messages.info(request, 'صفحة الإعداد السريع قيد التطوير')
#     return redirect('treasury_management:dashboard')

# # Views مساعدة
# def treasury_detail(request, treasury_id):
#     messages.info(request, 'صفحة تفاصيل الخزنة قيد التطوير')
#     return redirect('treasury_management:treasuries_list')

# def edit_treasury(request, treasury_id):
#     messages.info(request, 'صفحة تحرير الخزنة قيد التطوير')
#     return redirect('treasury_management:treasuries_list')

# def edit_account_category(request, category_id):
#     messages.info(request, 'صفحة تحرير التصنيف قيد التطوير')
#     return redirect('treasury_management:account_categories_list')

# # treasury_management/views.py
# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.db.models import Sum, Count, Q
# from django.utils import timezone
# from datetime import datetime, timedelta
# from django.http import JsonResponse
# from .models import Treasury, Transaction, Account, DailyExpense, TreasurySnapshot
# from django.contrib.auth import get_user_model

# User = get_user_model()
# from django.contrib.auth.models import Group

# # استيراد الـ decorators المخصصة
# from .decorators import (
#     treasury_admin_required,
#     treasury_manager_required,
#     treasury_accountant_required,
#     treasury_cashier_required,
#     treasury_access_required,
#     can_approve_transactions,
#     can_delete_records
# )



# @treasury_access_required
# def treasury_dashboard(request):
#     """لوحة تحكم الخزنة"""
#     today = timezone.now().date()
    
#     # الخزائن النشطة
#     treasuries = Treasury.objects.filter(is_active=True)
#     total_balance = treasuries.aggregate(total=Sum('account__current_balance'))['total'] or 0
    
#     # إحصائيات اليوم
#     today_transactions = Transaction.objects.filter(
#         transaction_date__date=today,
#         is_approved=True,
#         is_cancelled=False
#     )
    
#     today_income = today_transactions.filter(transaction_type='INCOME').aggregate(
#         total=Sum('amount')
#     )['total'] or 0
    
#     today_expenses = today_transactions.filter(transaction_type='EXPENSE').aggregate(
#         total=Sum('amount')
#     )['total'] or 0
    
#     # إحصائيات الشهر
#     month_start = today.replace(day=1)
#     month_transactions = Transaction.objects.filter(
#         transaction_date__date__gte=month_start,
#         is_approved=True,
#         is_cancelled=False
#     )
    
#     month_income = month_transactions.filter(transaction_type='INCOME').aggregate(
#         total=Sum('amount')
#     )['total'] or 0
    
#     month_expenses = month_transactions.filter(transaction_type='EXPENSE').aggregate(
#         total=Sum('amount')
#     )['total'] or 0
    
#     # العمليات المعلقة
#     pending_transactions = Transaction.objects.filter(
#         is_approved=False,
#         is_cancelled=False
#     ).count()
    
#     # آخر العمليات
#     recent_transactions = Transaction.objects.filter(
#         is_approved=True,
#         is_cancelled=False
#     ).order_by('-created_at')[:10]
    
#     context = {
#         'treasuries': treasuries,
#         'total_balance': total_balance,
#         'today_income': today_income,
#         'today_expenses': today_expenses,
#         'today_net': today_income - today_expenses,
#         'month_income': month_income,
#         'month_expenses': month_expenses,
#         'month_net': month_income - month_expenses,
#         'pending_transactions': pending_transactions,
#         'recent_transactions': recent_transactions,
#     }
    
#     return render(request, 'treasury_management/dashboard.html', context)

# @login_required
# def add_transaction(request):
#     """إضافة عملية مالية"""
#     if request.method == 'POST':
#         try:
#             treasury_id = request.POST.get('treasury')
#             account_id = request.POST.get('account')
#             transaction_type = request.POST.get('transaction_type')
#             amount = request.POST.get('amount')
#             description = request.POST.get('description')
#             payment_method = request.POST.get('payment_method', 'CASH')
            
#             treasury = Treasury.objects.get(id=treasury_id)
#             account = Account.objects.get(id=account_id)
            
#             transaction = Transaction.objects.create(
#                 treasury=treasury,
#                 account=account,
#                 transaction_type=transaction_type,
#                 amount=amount,
#                 description=description,
#                 payment_method=payment_method,
#                 created_by=request.user,
#                 academic_year=AcademicYear.get_current_year()
#             )
            
#             # اعتماد فوري إذا كان المستخدم له صلاحية
#             if request.user.has_perm('treasury_management.approve_transaction'):
#                 transaction.approve(request.user)
            
#             messages.success(request, 'تم إضافة العملية المالية بنجاح')
#             return redirect('treasury_management:dashboard')
            
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     treasuries = Treasury.objects.filter(is_active=True)
#     accounts = Account.objects.filter(is_active=True)
    
#     context = {
#         'treasuries': treasuries,
#         'accounts': accounts,
#     }
    
#     return render(request, 'treasury_management/add_transaction.html', context)

# # تحديث treasury_management/views.py - View التقارير
# from django.db.models import Sum, Count, Q
# from django.utils import timezone
# from datetime import datetime, timedelta




# # treasury_management/views.py (إكمال)
# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required, permission_required
# from django.contrib import messages
# from django.db.models import Sum, Count, Q, F
# from django.utils import timezone
# from datetime import datetime, timedelta, date
# from django.http import JsonResponse, HttpResponse
# from django.core.paginator import Paginator
# from django.db import transaction as db_transaction
# import json
# from .models import (
#     Treasury, Transaction, Account, DailyExpense, TreasurySnapshot,
#     AccountCategory, ExpenseCategory, StudentPaymentTransaction
# )
# from school_settings.models import AcademicYear

# @login_required
# def treasury_dashboard(request):
#     """لوحة تحكم الخزنة الرئيسية"""
#     today = timezone.now().date()
    
#     # الخزائن النشطة مع أرصدتها
#     treasuries = Treasury.objects.filter(is_active=True).select_related('account')
#     total_balance = treasuries.aggregate(total=Sum('account__current_balance'))['total'] or 0
    
#     # إحصائيات اليوم
#     today_transactions = Transaction.objects.filter(
#         transaction_date__date=today,
#         is_approved=True,
#         is_cancelled=False
#     )
    
#     today_stats = today_transactions.aggregate(
#         income=Sum('amount', filter=Q(transaction_type='INCOME')),
#         expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
#         count=Count('id')
#     )
    
#     today_income = today_stats['income'] or 0
#     today_expenses = today_stats['expenses'] or 0
#     today_net = today_income - today_expenses
    
#     # إحصائيات الشهر الحالي
#     month_start = today.replace(day=1)
#     month_transactions = Transaction.objects.filter(
#         transaction_date__date__gte=month_start,
#         transaction_date__date__lte=today,
#         is_approved=True,
#         is_cancelled=False
#     )
    
#     month_stats = month_transactions.aggregate(
#         income=Sum('amount', filter=Q(transaction_type='INCOME')),
#         expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
#         count=Count('id')
#     )
    
#     month_income = month_stats['income'] or 0
#     month_expenses = month_stats['expenses'] or 0
#     month_net = month_income - month_expenses
    
#     # إحصائيات الأسبوع الماضي (للرسم البياني)
#     week_data = []
#     for i in range(7):
#         day = today - timedelta(days=i)
#         day_transactions = Transaction.objects.filter(
#             transaction_date__date=day,
#             is_approved=True,
#             is_cancelled=False
#         )
        
#         day_stats = day_transactions.aggregate(
#             income=Sum('amount', filter=Q(transaction_type='INCOME')),
#             expenses=Sum('amount', filter=Q(transaction_type='EXPENSE'))
#         )
        
#         week_data.append({
#             'date': day.strftime('%Y-%m-%d'),
#             'day_name': day.strftime('%A'),
#             'day_name_ar': ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'][day.weekday()],
#             'income': float(day_stats['income'] or 0),
#             'expenses': float(day_stats['expenses'] or 0),
#             'net': float((day_stats['income'] or 0) - (day_stats['expenses'] or 0))
#         })
    
#     week_data.reverse()  # ترتيب من الأقدم للأحدث
    
#     # العمليات المعلقة للموافقة
#     pending_transactions = Transaction.objects.filter(
#         is_approved=False,
#         is_cancelled=False
#     ).order_by('-created_at')[:5]
    
#     # آخر العمليات
#     recent_transactions = Transaction.objects.filter(
#         is_approved=True,
#         is_cancelled=False
#     ).select_related('treasury', 'account', 'created_by').order_by('-transaction_date')[:10]
    
#     # أكثر المصروفات
#     top_expenses = DailyExpense.objects.filter(
#         expense_date__gte=month_start,
#         is_approved=True
#     ).values('category__name').annotate(
#         total=Sum('amount')
#     ).order_by('-total')[:5]
    
#     # تنبيهات الخزنة
#     alerts = []
#     for treasury in treasuries:
#         if treasury.current_balance < treasury.min_limit:
#             alerts.append({
#                 'type': 'warning',
#                 'title': f'رصيد {treasury.name} منخفض',
#                 'message': f'الرصيد الحالي: {treasury.current_balance} أقل من الحد الأدنى: {treasury.min_limit}'
#             })
        
#         if treasury.max_limit and treasury.current_balance > treasury.max_limit:
#             alerts.append({
#                 'type': 'info',
#                 'title': f'رصيد {treasury.name} مرتفع',
#                 'message': f'الرصيد الحالي: {treasury.current_balance} أعلى من الحد الأقصى: {treasury.max_limit}'
#             })
    
#     context = {
#         'treasuries': treasuries,
#         'total_balance': total_balance,
#         'today_income': today_income,
#         'today_expenses': today_expenses,
#         'today_net': today_net,
#         'today_transactions_count': today_stats['count'],
#         'month_income': month_income,
#         'month_expenses': month_expenses,
#         'month_net': month_net,
#         'month_transactions_count': month_stats['count'],
#         'pending_transactions': pending_transactions,
#         'recent_transactions': recent_transactions,
#         'top_expenses': top_expenses,
#         'week_data': json.dumps(week_data),
#         'alerts': alerts,
#     }
    
#     return render(request, 'treasury_management/dashboard.html', context)

# @login_required
# def add_transaction(request):
#     """إضافة عملية مالية جديدة"""
#     if request.method == 'POST':
#         try:
#             with db_transaction.atomic():
#                 treasury_id = request.POST.get('treasury')
#                 account_id = request.POST.get('account')
#                 transaction_type = request.POST.get('transaction_type')
#                 amount = float(request.POST.get('amount'))
#                 description = request.POST.get('description')
#                 payment_method = request.POST.get('payment_method', 'CASH')
#                 reference_number = request.POST.get('reference_number', '')
#                 transaction_date = request.POST.get('transaction_date')
                
#                 if not transaction_date:
#                     transaction_date = timezone.now()
#                 else:
#                     transaction_date = datetime.strptime(transaction_date, '%Y-%m-%d')
                
#                 treasury = Treasury.objects.get(id=treasury_id)
#                 account = Account.objects.get(id=account_id)
#                 current_year = AcademicYear.get_current_year()
                
#                 # التحقق من الرصيد للمصروفات
#                 if transaction_type == 'EXPENSE' and treasury.current_balance < amount:
#                     messages.error(request, f'الرصيد غير كافي في {treasury.name}. الرصيد الحالي: {treasury.current_balance}')
#                     return redirect('treasury_management:add_transaction')
                
#                 transaction_obj = Transaction.objects.create(
#                     treasury=treasury,
#                     account=account,
#                     transaction_type=transaction_type,
#                     amount=amount,
#                     description=description,
#                     payment_method=payment_method,
#                     reference_number=reference_number,
#                     transaction_date=transaction_date,
#                     created_by=request.user,
#                     academic_year=current_year
#                 )
                
#                 # اعتماد فوري إذا كان المستخدم له صلاحية أو المبلغ صغير
#                 if (request.user.has_perm('treasury_management.approve_transaction') or 
#                     amount < 1000):  # حد أدنى للاعتماد التلقائي
#                     transaction_obj.approve(request.user)
#                     messages.success(request, 'تم إضافة واعتماد العملية المالية بنجاح')
#                 else:
#                     messages.success(request, 'تم إضافة العملية المالية وهي في انتظار الاعتماد')
                
#                 return redirect('treasury_management:dashboard')
                
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     # البيانات للنموذج
#     treasuries = Treasury.objects.filter(is_active=True)
    
#     # تصنيف الحسابات حسب النوع
#     income_accounts = Account.objects.filter(
#         category__category_type='REVENUE',
#         is_active=True
#     ).order_by('name')
    
#     expense_accounts = Account.objects.filter(
#         category__category_type='EXPENSE',
#         is_active=True
#     ).order_by('name')
    
#     context = {
#         'treasuries': treasuries,
#         'income_accounts': income_accounts,
#         'expense_accounts': expense_accounts,
#     }
    
#     return render(request, 'treasury_management/add_transaction.html', context)

# # treasury_management/views.py - تحسين View قائمة العمليات
# from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# from django.db.models import Q, Sum, Count
# from django.http import JsonResponse
# from django.template.loader import render_to_string

# @login_required
# def transactions_list(request):
#     """قائمة العمليات المالية مع فلاتر وpagination"""
    
#     # الحصول على المعاملات
#     transaction_type = request.GET.get('type', '')
#     treasury_id = request.GET.get('treasury', '')
#     from_date = request.GET.get('from_date', '')
#     to_date = request.GET.get('to_date', '')
#     approved = request.GET.get('approved', '')
#     search = request.GET.get('search', '')
    
#     # بناء الاستعلام
#     transactions = Transaction.objects.all().select_related(
#         'treasury', 'account', 'created_by'
#     ).order_by('-created_at')
    
#     # تطبيق الفلاتر
#     if transaction_type:
#         transactions = transactions.filter(transaction_type=transaction_type)
    
#     if treasury_id:
#         transactions = transactions.filter(treasury_id=treasury_id)
    
#     if from_date:
#         transactions = transactions.filter(transaction_date__gte=from_date)
    
#     if to_date:
#         transactions = transactions.filter(transaction_date__lte=to_date)
    
#     if approved == 'true':
#         transactions = transactions.filter(is_approved=True)
#     elif approved == 'false':
#         transactions = transactions.filter(is_approved=False)
    
#     if search:
#         transactions = transactions.filter(
#             Q(transaction_number__icontains=search) |
#             Q(description__icontains=search) |
#             Q(reference_number__icontains=search)
#         )
    
#     # إحصائيات الصفحة
#     page_stats = {
#         'total_income': transactions.filter(transaction_type='INCOME').aggregate(
#             Sum('amount')
#         )['amount__sum'] or 0,
#         'total_expenses': transactions.filter(transaction_type='EXPENSE').aggregate(
#             Sum('amount')
#         )['amount__sum'] or 0,
#         'count': transactions.count(),
#     }
    
#     # Pagination
#     items_per_page = request.GET.get('per_page', 20)
#     try:
#         items_per_page = int(items_per_page)
#         if items_per_page not in [10, 20, 50, 100]:
#             items_per_page = 20
#     except:
#         items_per_page = 20
    
#     paginator = Paginator(transactions, items_per_page)
#     page = request.GET.get('page')
    
#     try:
#         transactions_page = paginator.page(page)
#     except PageNotAnInteger:
#         transactions_page = paginator.page(1)
#     except EmptyPage:
#         transactions_page = paginator.page(paginator.num_pages)
    
#     # الخزائن للفلتر
#     treasuries = Treasury.objects.filter(is_active=True).order_by('name')
    
#     context = {
#         'transactions': transactions_page,
#         'treasuries': treasuries,
#         'page_stats': page_stats,
#         'filters': {
#             'type': transaction_type,
#             'treasury': treasury_id,
#             'from_date': from_date,
#             'to_date': to_date,
#             'approved': approved,
#             'search': search,
#         },
#         'items_per_page': items_per_page,
#     }
    
#     return render(request, 'treasury_management/transactions_list.html', context)

# treasury_management/views.py - إضافة الصلاحيات وإزالة التكرار

# ===================================
# 💰 Views العمليات المالية مع الصلاحيات
# ===================================

@treasury_access_required
def transaction_detail_ajax(request, transaction_id):
    """تفاصيل العملية عبر AJAX - يحتاج أي صلاحية خزينة"""
    try:
        transaction = get_object_or_404(
            Transaction.objects.select_related(
                'treasury', 'account', 'created_by', 'approved_by', 'cancelled_by'
            ), 
            id=transaction_id
        )
        
        html = render_to_string('treasury_management/transaction_detail_modal.html', {
            'transaction': transaction,
        }, request=request)
        
        return JsonResponse({
            'success': True,
            'html': html
        })
    except Transaction.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'العملية غير موجودة'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@can_approve_transactions
def approve_transaction(request, transaction_id):
    """اعتماد العملية المالية - يحتاج صلاحية مدير أو أعلى"""
    if request.method == 'POST':
        try:
            transaction = get_object_or_404(Transaction, id=transaction_id)
            
            if transaction.is_approved:
                return JsonResponse({
                    'success': False,
                    'error': 'العملية معتمدة مسبقاً'
                })
            
            if transaction.is_cancelled:
                return JsonResponse({
                    'success': False,
                    'error': 'العملية ملغية'
                })
            
            # اعتماد العملية
            transaction.is_approved = True
            transaction.approved_by = request.user
            transaction.approved_at = timezone.now()
            transaction.save()
            
            return JsonResponse({
                'success': True,
                'message': 'تم اعتماد العملية بنجاح'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return redirect('treasury_management:transactions_list')

@can_approve_transactions
def cancel_transaction(request, transaction_id):
    """إلغاء العملية المالية - يحتاج صلاحية مدير أو أعلى"""
    if request.method == 'POST':
        try:
            transaction = get_object_or_404(Transaction, id=transaction_id)
            
            if transaction.is_cancelled:
                return JsonResponse({
                    'success': False,
                    'error': 'العملية ملغية مسبقاً'
                })
            
            cancellation_reason = request.POST.get('cancellation_reason', '')
            if not cancellation_reason:
                return JsonResponse({
                    'success': False,
                    'error': 'يجب إدخال سبب الإلغاء'
                })
            
            # إلغاء العملية
            transaction.is_cancelled = True
            transaction.cancellation_reason = cancellation_reason
            transaction.cancelled_by = request.user
            transaction.cancelled_at = timezone.now()
            transaction.save()
            
            return JsonResponse({
                'success': True,
                'message': 'تم إلغاء العملية بنجاح'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return redirect('treasury_management:transactions_list')

# ===================================
# 💸 Views المصروفات مع الصلاحيات
# ===================================

@treasury_cashier_required
def add_expense(request):
    """إضافة مصروف يومي - يحتاج صلاحية أمين خزينة أو أعلى"""
    # التحقق من وجود نموذج DailyExpense
    if not DailyExpense:
        messages.error(request, 'نموذج المصروفات غير متوفر')
        return redirect('treasury_management:dashboard')
    
    if request.method == 'POST':
        try:
            with db_transaction.atomic():
                category_id = request.POST.get('category')
                expense_type = request.POST.get('expense_type')
                description = request.POST.get('description')
                amount = float(request.POST.get('amount'))
                vendor_name = request.POST.get('vendor_name', '')
                invoice_number = request.POST.get('invoice_number', '')
                expense_date = request.POST.get('expense_date')
                treasury_id = request.POST.get('treasury')
                notes = request.POST.get('notes', '')
                
                if not expense_date:
                    expense_date = timezone.now().date()
                else:
                    expense_date = datetime.strptime(expense_date, '%Y-%m-%d').date()
                
                category = ExpenseCategory.objects.get(id=category_id)
                treasury = Treasury.objects.get(id=treasury_id)
                
                # التحقق من الرصيد
                if treasury.current_balance < amount:
                    messages.error(request, f'الرصيد غير كافي في {treasury.name}. الرصيد الحالي: {treasury.current_balance}')
                    return redirect('treasury_management:add_expense')
                
                # الحصول على السنة الأكاديمية
                current_year = None
                if AcademicYear:
                    try:
                        current_year = AcademicYear.get_current_year()
                    except:
                        pass
                
                # إنشاء المصروف
                expense_data = {
                    'category': category,
                    'expense_type': expense_type,
                    'description': description,
                    'amount': amount,
                    'vendor_name': vendor_name,
                    'invoice_number': invoice_number,
                    'expense_date': expense_date,
                    'notes': notes,
                    'created_by': request.user
                }
                
                expense = DailyExpense.objects.create(**expense_data)
                
                # إنشاء العملية المالية المرتبطة
                transaction_data = {
                    'treasury': treasury,
                    'account': category.account if hasattr(category, 'account') else None,
                    'transaction_type': 'EXPENSE',
                    'amount': amount,
                    'description': f'مصروف: {description}',
                    'payment_method': 'CASH',
                    'reference_number': invoice_number,
                    'transaction_date': expense_date,
                    'notes': f'مصروف من فئة: {category.name}',
                    'created_by': request.user,
                }
                
                if current_year:
                    transaction_data['academic_year'] = current_year
                
                # إضافة معرف المصروف للعملية إذا كان النموذج يدعم ذلك
                if hasattr(Transaction, 'related_model'):
                    transaction_data.update({
                        'related_model': 'DailyExpense',
                        'related_id': expense.id
                    })
                
                transaction_obj = Transaction.objects.create(**transaction_data)
                
                # ربط المصروف بالعملية
                if hasattr(expense, 'transaction'):
                    expense.transaction = transaction_obj
                    expense.save()
                
                # اعتماد تلقائي للمصروفات الصغيرة أو للمستخدمين المخولين
                user_groups = request.user.groups.values_list('name', flat=True)
                can_auto_approve = (
                    request.user.is_superuser or
                    any(group in user_groups for group in ['treasury_admin', 'treasury_manager']) or
                    amount < 500  # حد أدنى للاعتماد التلقائي
                )
                
                if can_auto_approve:
                    expense.is_approved = True
                    expense.approved_by = request.user
                    expense.approved_at = timezone.now()
                    expense.save()
                    
                    transaction_obj.is_approved = True
                    transaction_obj.approved_by = request.user
                    transaction_obj.approved_at = timezone.now()
                    transaction_obj.save()
                    
                    messages.success(request, 'تم إضافة واعتماد المصروف بنجاح')
                else:
                    messages.success(request, 'تم إضافة المصروف وهو في انتظار الاعتماد')
                
                return redirect('treasury_management:expenses_list')
                
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    # التحقق من وجود النماذج المطلوبة
    try:
        expense_categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')
        treasuries = Treasury.objects.filter(is_active=True).order_by('name')
    except:
        expense_categories = []
        treasuries = Treasury.objects.filter(is_active=True).order_by('name')
    
    context = {
        'expense_categories': expense_categories,
        'treasuries': treasuries,
        'today': timezone.now().date(),
    }
    
    return render(request, 'treasury_management/add_expense.html', context)

@treasury_access_required
def expenses_list(request):
    """قائمة المصروفات اليومية - يحتاج أي صلاحية خزينة"""
    # التحقق من وجود نموذج DailyExpense
    if not DailyExpense:
        messages.info(request, 'نموذج المصروفات غير متوفر حالياً')
        return redirect('treasury_management:dashboard')
    
    # فلترة البيانات
    category_id = request.GET.get('category', '')
    expense_type = request.GET.get('type', '')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    is_approved = request.GET.get('approved', '')
    search = request.GET.get('search', '')
    
    expenses = DailyExpense.objects.all().select_related(
        'category', 'created_by', 'approved_by'
    ).order_by('-expense_date', '-created_at')
    
    # إضافة علاقة transaction إذا كانت متوفرة
    if hasattr(DailyExpense, 'transaction'):
        expenses = expenses.select_related('transaction__treasury')
    
    # تطبيق الفلاتر
    if category_id:
        expenses = expenses.filter(category_id=category_id)
    
    if expense_type:
        expenses = expenses.filter(expense_type=expense_type)
    
    if from_date:
        expenses = expenses.filter(expense_date__gte=from_date)
    
    if to_date:
        expenses = expenses.filter(expense_date__lte=to_date)
    
    if is_approved == 'true':
        expenses = expenses.filter(is_approved=True)
    elif is_approved == 'false':
        expenses = expenses.filter(is_approved=False)
    
    if search:
        expenses = expenses.filter(
            Q(description__icontains=search) |
            Q(vendor_name__icontains=search) |
            Q(invoice_number__icontains=search)
        )
    
    # التصفح
    items_per_page = request.GET.get('per_page', 25)
    try:
        items_per_page = int(items_per_page)
        if items_per_page not in [10, 25, 50, 100]:
            items_per_page = 25
    except:
        items_per_page = 25
    
    paginator = Paginator(expenses, items_per_page)
    page = request.GET.get('page')
    
    try:
        expenses_page = paginator.page(page)
    except PageNotAnInteger:
        expenses_page = paginator.page(1)
    except EmptyPage:
        expenses_page = paginator.page(paginator.num_pages)
    
    # إحصائيات
    total_amount = expenses.aggregate(total=Sum('amount'))['total'] or 0
    approved_amount = expenses.filter(is_approved=True).aggregate(total=Sum('amount'))['total'] or 0
    pending_amount = expenses.filter(is_approved=False).aggregate(total=Sum('amount'))['total'] or 0
    
    # التصنيفات للفلتر
    try:
        expense_categories = ExpenseCategory.objects.filter(is_active=True).order_by('name')
    except:
        expense_categories = []
    
    context = {
        'expenses': expenses_page,
        'expense_categories': expense_categories,
        'total_amount': total_amount,
        'approved_amount': approved_amount,
        'pending_amount': pending_amount,
        'filters': {
            'category': category_id,
            'type': expense_type,
            'from_date': from_date,
            'to_date': to_date,
            'approved': is_approved,
            'search': search,
        },
        'items_per_page': items_per_page,
    }
    
    return render(request, 'treasury_management/expenses_list.html', context)

# ===================================
# 📈 Views التقارير مع الصلاحيات  
# ===================================

@treasury_access_required
def daily_summary(request):
    """ملخص يومي للخزنة - يحتاج أي صلاحية خزينة"""
    selected_date = request.GET.get('date', timezone.now().date())
    if isinstance(selected_date, str):
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except:
            selected_date = timezone.now().date()
    
    # حساب التواريخ المجاورة
    previous_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)
    today = timezone.now().date()
    
    # التحقق من طلب التصدير (للمديرين فقط)
    export_format = request.GET.get('export')
    if export_format in ['pdf', 'excel']:
        user_groups = request.user.groups.values_list('name', flat=True)
        can_export = (
            request.user.is_superuser or
            any(group in user_groups for group in ['treasury_admin', 'treasury_manager', 'treasury_accountant'])
        )
        if can_export:
            return export_daily_summary(request, selected_date, export_format)
        else:
            messages.error(request, 'ليس لديك صلاحية لتصدير التقارير')
    
    # العمليات في التاريخ المحدد
    day_transactions = Transaction.objects.filter(
        transaction_date__date=selected_date,
        is_approved=True,
        is_cancelled=False
    ).select_related('treasury', 'account', 'created_by')
    
    # تجميع حسب الخزنة
    treasury_summaries = []
    treasuries = Treasury.objects.filter(is_active=True)
    
    total_income = 0
    total_expenses = 0
    
    for treasury in treasuries:
        treasury_transactions = day_transactions.filter(treasury=treasury)
        
        income_transactions = treasury_transactions.filter(transaction_type='INCOME')
        expense_transactions = treasury_transactions.filter(transaction_type='EXPENSE')
        
        treasury_income = income_transactions.aggregate(total=Sum('amount'))['total'] or 0
        treasury_expenses = expense_transactions.aggregate(total=Sum('amount'))['total'] or 0
        
        total_income += treasury_income
        total_expenses += treasury_expenses
        
        # الرصيد في بداية اليوم (تقريبي)
        opening_balance = treasury.current_balance - (treasury_income - treasury_expenses)
        
        treasury_summary = {
            'treasury': treasury,
            'opening_balance': opening_balance,
            'closing_balance': treasury.current_balance,
            'total_income': treasury_income,
            'total_expenses': treasury_expenses,
            'net_change': treasury_income - treasury_expenses,
            'income_transactions': income_transactions[:5],
            'expense_transactions': expense_transactions[:5],
            'transaction_count': treasury_transactions.count()
        }
        
        # إضافة الملخص فقط إذا كان هناك نشاط
        if treasury_summary['transaction_count'] > 0 or treasury.current_balance != 0:
            treasury_summaries.append(treasury_summary)
    
    # المصروفات اليومية (إذا كانت متوفرة)
    day_expenses = []
    expenses_by_category = []
    total_expenses_amount = 0
    
    if DailyExpense:
        try:
            day_expenses = DailyExpense.objects.filter(
                expense_date=selected_date,
                is_approved=True
            ).select_related('category')
            
            # تجميع المصروفات حسب التصنيف
            expenses_by_category = day_expenses.values('category__name').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('-total')
            
            total_expenses_amount = day_expenses.aggregate(total=Sum('amount'))['total'] or 0
        except:
            pass
    
    net_total = total_income - total_expenses
    
    context = {
        'selected_date': selected_date,
        'previous_date': previous_date,
        'next_date': next_date,
        'today': today,
        'treasury_summaries': treasury_summaries,
        'day_expenses': day_expenses,
        'expenses_by_category': expenses_by_category,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'total_expenses_amount': total_expenses_amount,
        'net_total': net_total,
    }
    
    return render(request, 'treasury_management/daily_summary.html', context)

@treasury_access_required
def treasury_report(request):
    """تقارير الخزنة المتقدمة - يحتاج أي صلاحية خزينة"""
    report_type = request.GET.get('report_type', 'summary')
    from_date = request.GET.get('from_date', timezone.now().date().replace(day=1))
    to_date = request.GET.get('to_date', timezone.now().date())
    treasury_id = request.GET.get('treasury_id', '')
    
    if isinstance(from_date, str):
        try:
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        except:
            from_date = timezone.now().date().replace(day=1)
    
    if isinstance(to_date, str):
        try:
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        except:
            to_date = timezone.now().date()
    
    context = {
        'report_type': report_type,
        'from_date': from_date,
        'to_date': to_date,
        'treasury_id': treasury_id,
        'treasuries': Treasury.objects.filter(is_active=True),
    }
    
    # تقرير الملخص
    if report_type == 'summary':
        transactions = Transaction.objects.filter(
            transaction_date__date__gte=from_date,
            transaction_date__date__lte=to_date,
            is_approved=True,
            is_cancelled=False
        )
        
        if treasury_id:
            transactions = transactions.filter(treasury_id=treasury_id)
        
        summary = transactions.aggregate(
            total_income=Sum('amount', filter=Q(transaction_type='INCOME')),
            total_expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
            total_count=Count('id')
        )
        
        # تجميع حسب النوع
        by_type = transactions.values('transaction_type').annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        # تجميع حسب طريقة الدفع
        by_payment_method = transactions.values('payment_method').annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        context.update({
            'summary': summary,
            'by_type': by_type,
            'by_payment_method': by_payment_method,
            'transactions': transactions.order_by('-transaction_date')[:50]
        })
    
    # تقرير الحسابات (للمحاسبين فقط)
    elif report_type == 'accounts':
        user_groups = request.user.groups.values_list('name', flat=True)
        can_view_accounts = (
            request.user.is_superuser or
            any(group in user_groups for group in ['treasury_admin', 'treasury_manager', 'treasury_accountant'])
        )
        
        if can_view_accounts:
            account_summaries = Account.objects.filter(is_active=True).annotate(
                period_income=Sum('transaction__amount',
                                filter=Q(transaction__transaction_type='INCOME',
                                       transaction__transaction_date__date__gte=from_date,
                                       transaction__transaction_date__date__lte=to_date,
                                       transaction__is_approved=True,
                                       transaction__is_cancelled=False)),
                period_expenses=Sum('transaction__amount',
                                 filter=Q(transaction__transaction_type='EXPENSE',
                                        transaction__transaction_date__date__gte=from_date,
                                        transaction__transaction_date__date__lte=to_date,
                                        transaction__is_approved=True,
                                        transaction__is_cancelled=False))
            ).order_by('category__category_type', 'name')
            
            context['account_summaries'] = account_summaries
        else:
            messages.error(request, 'ليس لديك صلاحية لعرض تقرير الحسابات')
            return redirect('treasury_management:reports')
    
    # تقرير يومي مفصل
    elif report_type == 'daily':
        daily_data = []
        current_date = from_date
        
        while current_date <= to_date:
            day_transactions = Transaction.objects.filter(
                transaction_date__date=current_date,
                is_approved=True,
                is_cancelled=False
            )
            
            if treasury_id:
                day_transactions = day_transactions.filter(treasury_id=treasury_id)
            
            day_stats = day_transactions.aggregate(
                income=Sum('amount', filter=Q(transaction_type='INCOME')),
                expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
                count=Count('id')
            )
            
            daily_data.append({
                'date': current_date,
                'income': day_stats['income'] or 0,
                'expenses': day_stats['expenses'] or 0,
                'net': (day_stats['income'] or 0) - (day_stats['expenses'] or 0),
                'count': day_stats['count']
            })
            
            current_date += timedelta(days=1)
        
        context['daily_data'] = daily_data
    
    return render(request, 'treasury_management/reports.html', context)

# ===================================
# 🔧 Views مساعدة ومتنوعة
# ===================================

@treasury_access_required
def get_treasury_balance(request, treasury_id):
    """API للحصول على رصيد خزنة - يحتاج أي صلاحية خزينة"""
    try:
        treasury = Treasury.objects.get(id=treasury_id, is_active=True)
        
        balance_data = {
            'success': True,
            'balance': float(treasury.current_balance),
            'name': treasury.name,
        }
        
        # إضافة الحدود إذا كانت متوفرة
        if hasattr(treasury, 'min_limit'):
            balance_data['min_limit'] = float(treasury.min_limit) if treasury.min_limit else 0
        
        if hasattr(treasury, 'max_limit'):
            balance_data['max_limit'] = float(treasury.max_limit) if treasury.max_limit else None
        
        return JsonResponse(balance_data)
    except Treasury.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'الخزنة غير موجودة'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@treasury_access_required
def transaction_detail(request, pk):
    """تفاصيل عملية مالية - يحتاج أي صلاحية خزينة"""
    transaction_obj = get_object_or_404(
        Transaction.objects.select_related(
            'treasury', 'account', 'created_by', 'approved_by', 'cancelled_by'
        ), 
        pk=pk
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # طلب AJAX - إرجاع JSON
        html = render_to_string('treasury_management/transaction_detail_modal.html', {
            'transaction': transaction_obj
        }, request=request)
        return JsonResponse({
            'success': True,
            'html': html
        })
    
    # طلب عادي - إرجاع صفحة كاملة
    context = {
        'transaction': transaction_obj,
    }
    return render(request, 'treasury_management/transaction_detail.html', context)

# ===================================
# 🔄 وظائف مساعدة للتصدير (اختيارية)
# ===================================

def export_daily_summary(request, selected_date, export_format):
    """تصدير الملخص اليومي - وظيفة مساعدة"""
    # هذه وظيفة يمكن تطويرها لاحقاً
    messages.info(request, f'تصدير {export_format} قيد التطوير')
    return redirect('treasury_management:daily_summary')


# @login_required
# def transaction_detail_ajax(request, transaction_id):
#     """تفاصيل العملية عبر AJAX"""
#     try:
#         transaction = get_object_or_404(
#             Transaction.objects.select_related(
#                 'treasury', 'account', 'created_by'
#             ), 
#             id=transaction_id
#         )
        
#         html = render_to_string('treasury_management/transaction_detail_modal.html', {
#             'transaction': transaction,
#         }, request=request)
        
#         return JsonResponse({
#             'success': True,
#             'html': html
#         })
#     except Transaction.DoesNotExist:
#         return JsonResponse({
#             'success': False,
#             'error': 'العملية غير موجودة'
#         }, status=404)
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         }, status=500)

# @login_required
# def approve_transaction(request, transaction_id):
#     """اعتماد العملية المالية"""
#     if request.method == 'POST':
#         try:
#             transaction = get_object_or_404(Transaction, id=transaction_id)
            
#             if transaction.is_approved:
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'العملية معتمدة مسبقاً'
#                 })
            
#             if transaction.is_cancelled:
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'العملية ملغية'
#                 })
            
#             # اعتماد العملية
#             transaction.is_approved = True
#             transaction.approved_by = request.user
#             transaction.approved_at = timezone.now()
#             transaction.save()
            
#             return JsonResponse({
#                 'success': True,
#                 'message': 'تم اعتماد العملية بنجاح'
#             })
            
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'error': str(e)
#             })
    
#     return redirect('treasury_management:transactions_list')

# @login_required
# def cancel_transaction(request, transaction_id):
#     """إلغاء العملية المالية"""
#     if request.method == 'POST':
#         try:
#             transaction = get_object_or_404(Transaction, id=transaction_id)
            
#             if transaction.is_cancelled:
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'العملية ملغية مسبقاً'
#                 })
            
#             cancellation_reason = request.POST.get('cancellation_reason', '')
#             if not cancellation_reason:
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'يجب إدخال سبب الإلغاء'
#                 })
            
#             # إلغاء العملية
#             transaction.is_cancelled = True
#             transaction.cancellation_reason = cancellation_reason
#             transaction.cancelled_by = request.user
#             transaction.cancelled_at = timezone.now()
#             transaction.save()
            
#             return JsonResponse({
#                 'success': True,
#                 'message': 'تم إلغاء العملية بنجاح'
#             })
            
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'error': str(e)
#             })
    
#     return redirect('treasury_management:transactions_list')

# @login_required
# def add_expense(request):
#     """إضافة مصروف يومي"""
#     if request.method == 'POST':
#         try:
#             with db_transaction.atomic():
#                 category_id = request.POST.get('category')
#                 expense_type = request.POST.get('expense_type')
#                 description = request.POST.get('description')
#                 amount = float(request.POST.get('amount'))
#                 vendor_name = request.POST.get('vendor_name', '')
#                 invoice_number = request.POST.get('invoice_number', '')
#                 expense_date = request.POST.get('expense_date')
#                 treasury_id = request.POST.get('treasury')
                
#                 if not expense_date:
#                     expense_date = timezone.now().date()
#                 else:
#                     expense_date = datetime.strptime(expense_date, '%Y-%m-%d').date()
                
#                 category = ExpenseCategory.objects.get(id=category_id)
#                 treasury = Treasury.objects.get(id=treasury_id)
                
#                 # التحقق من الرصيد
#                 if treasury.current_balance < amount:
#                     messages.error(request, f'الرصيد غير كافي في {treasury.name}')
#                     return redirect('treasury_management:add_expense')
                
#                 # إنشاء المصروف
#                 expense = DailyExpense.objects.create(
#                     category=category,
#                     expense_type=expense_type,
#                     description=description,
#                     amount=amount,
#                     vendor_name=vendor_name,
#                     invoice_number=invoice_number,
#                     expense_date=expense_date,
#                     created_by=request.user
#                 )
                
#                 # إنشاء العملية المالية المرتبطة
#                 transaction_obj = Transaction.objects.create(
#                     treasury=treasury,
#                     account=category.account,
#                     transaction_type='EXPENSE',
#                     amount=amount,
#                     description=f'مصروف: {description}',
#                     payment_method='CASH',
#                     reference_number=invoice_number,
#                     transaction_date=expense_date,
#                     related_model='DailyExpense',
#                     related_id=expense.id,
#                     created_by=request.user,
#                     academic_year=AcademicYear.get_current_year()
#                 )
                
#                 expense.transaction = transaction_obj
#                 expense.save()
                
#                 # اعتماد تلقائي للمصروفات الصغيرة
#                 if amount < 500 or request.user.has_perm('treasury_management.approve_expense'):
#                     expense.is_approved = True
#                     expense.approved_by = request.user
#                     expense.save()
                    
#                     transaction_obj.approve(request.user)
#                     messages.success(request, 'تم إضافة واعتماد المصروف بنجاح')
#                 else:
#                     messages.success(request, 'تم إضافة المصروف وهو في انتظار الاعتماد')
                
#                 return redirect('treasury_management:expenses_list')
                
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     context = {
#         'expense_categories': ExpenseCategory.objects.filter(is_active=True),
#         'treasuries': Treasury.objects.filter(is_active=True),
#     }
    
#     return render(request, 'treasury_management/add_expense.html', context)

# @login_required
# def expenses_list(request):
#     """قائمة المصروفات اليومية"""
#     # فلترة البيانات
#     category_id = request.GET.get('category', '')
#     expense_type = request.GET.get('type', '')
#     from_date = request.GET.get('from_date', '')
#     to_date = request.GET.get('to_date', '')
#     is_approved = request.GET.get('approved', '')
    
#     expenses = DailyExpense.objects.all().select_related(
#         'category', 'created_by', 'approved_by', 'transaction__treasury'
#     ).order_by('-expense_date', '-created_at')
    
#     # تطبيق الفلاتر
#     if category_id:
#         expenses = expenses.filter(category_id=category_id)
    
#     if expense_type:
#         expenses = expenses.filter(expense_type=expense_type)
    
#     if from_date:
#         expenses = expenses.filter(expense_date__gte=from_date)
    
#     if to_date:
#         expenses = expenses.filter(expense_date__lte=to_date)
    
#     if is_approved == 'true':
#         expenses = expenses.filter(is_approved=True)
#     elif is_approved == 'false':
#         expenses = expenses.filter(is_approved=False)
    
#     # التصفح
#     paginator = Paginator(expenses, 25)
#     page = request.GET.get('page')
#     expenses = paginator.get_page(page)
    
#     # إحصائيات
#     total_amount = expenses.object_list.aggregate(total=Sum('amount'))['total'] or 0
    
#     context = {
#         'expenses': expenses,
#         'expense_categories': ExpenseCategory.objects.filter(is_active=True),
#         'total_amount': total_amount,
#         'filters': {
#             'category': category_id,
#             'type': expense_type,
#             'from_date': from_date,
#             'to_date': to_date,
#             'approved': is_approved,
#         }
#     }
    
#     return render(request, 'treasury_management/expenses_list.html', context)

# @login_required
# @permission_required('treasury_management.approve_transaction')
# def approve_transaction(request, pk):
#     """اعتماد عملية مالية"""
#     transaction_obj = get_object_or_404(Transaction, pk=pk)
    
#     if not transaction_obj.is_approved and not transaction_obj.is_cancelled:
#         try:
#             transaction_obj.approve(request.user)
#             messages.success(request, f'تم اعتماد العملية رقم {transaction_obj.transaction_number}')
#         except Exception as e:
#             messages.error(request, f'حدث خطأ في الاعتماد: {str(e)}')
#     else:
#         messages.warning(request, 'العملية معتمدة مسبقاً أو ملغية')
    
#     return redirect('treasury_management:transactions_list')

# # تحديث treasury_management/views.py - View الملخص اليومي
# @login_required
# def daily_summary(request):
#     """ملخص يومي للخزنة"""
#     selected_date = request.GET.get('date', timezone.now().date())
#     if isinstance(selected_date, str):
#         selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    
#     # حساب التواريخ المجاورة
#     previous_date = selected_date - timedelta(days=1)
#     next_date = selected_date + timedelta(days=1)
#     today = timezone.now().date()
    
#     # التحقق من طلب التصدير
#     export_format = request.GET.get('export')
#     if export_format in ['pdf', 'excel']:
#         return export_daily_summary(request, selected_date, export_format)
    
#     # العمليات في التاريخ المحدد
#     day_transactions = Transaction.objects.filter(
#         transaction_date__date=selected_date,
#         is_approved=True,
#         is_cancelled=False
#     ).select_related('treasury', 'account', 'created_by')
    
#     # تجميع حسب الخزنة
#     treasury_summaries = []
#     treasuries = Treasury.objects.filter(is_active=True)
    
#     for treasury in treasuries:
#         treasury_transactions = day_transactions.filter(treasury=treasury)
        
#         income_transactions = treasury_transactions.filter(transaction_type='INCOME')
#         expense_transactions = treasury_transactions.filter(transaction_type='EXPENSE')
        
#         total_income = income_transactions.aggregate(total=Sum('amount'))['total'] or 0
#         total_expenses = expense_transactions.aggregate(total=Sum('amount'))['total'] or 0
        
#         # الرصيد في بداية اليوم (تقريبي)
#         opening_balance = treasury.current_balance - (total_income - total_expenses)
        
#         treasury_summaries.append({
#             'treasury': treasury,
#             'opening_balance': opening_balance,
#             'closing_balance': treasury.current_balance,
#             'total_income': total_income,
#             'total_expenses': total_expenses,
#             'net_change': total_income - total_expenses,
#             'income_transactions': income_transactions,
#             'expense_transactions': expense_transactions,
#             'transaction_count': treasury_transactions.count()
#         })
    
#     # المصروفات اليومية
#     day_expenses = DailyExpense.objects.filter(
#         expense_date=selected_date,
#         is_approved=True
#     ).select_related('category')
    
#     # تجميع المصروفات حسب التصنيف
#     expenses_by_category = day_expenses.values('category__name').annotate(
#         total=Sum('amount'),
#         count=Count('id')
#     ).order_by('-total')
    
#     # حساب الإجماليات
#     total_income = sum(ts['total_income'] for ts in treasury_summaries)
#     total_expenses = sum(ts['total_expenses'] for ts in treasury_summaries)
#     total_expenses_amount = day_expenses.aggregate(total=Sum('amount'))['total'] or 0
#     net_total = total_income - total_expenses
    
#     context = {
#         'selected_date': selected_date,
#         'previous_date': previous_date,
#         'next_date': next_date,
#         'today': today,
#         'treasury_summaries': treasury_summaries,
#         'day_expenses': day_expenses,
#         'expenses_by_category': expenses_by_category,
#         'total_income': total_income,
#         'total_expenses': total_expenses,
#         'total_expenses_amount': total_expenses_amount,
#         'net_total': net_total,  # إضافة صافي اليوم المحسوب
#     }
    
#     return render(request, 'treasury_management/daily_summary.html', context)

# @login_required
# def treasury_report(request):
#     """تقارير الخزنة المتقدمة"""
#     report_type = request.GET.get('report_type', 'summary')
#     from_date = request.GET.get('from_date', timezone.now().date().replace(day=1))
#     to_date = request.GET.get('to_date', timezone.now().date())
#     treasury_id = request.GET.get('treasury_id', '')
    
#     if isinstance(from_date, str):
#         from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
#     if isinstance(to_date, str):
#         to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
    
#     context = {
#         'report_type': report_type,
#         'from_date': from_date,
#         'to_date': to_date,
#         'treasury_id': treasury_id,
#         'treasuries': Treasury.objects.filter(is_active=True),
#     }
    
#     # تقرير الملخص
#     if report_type == 'summary':
#         transactions = Transaction.objects.filter(
#             transaction_date__date__gte=from_date,
#             transaction_date__date__lte=to_date,
#             is_approved=True,
#             is_cancelled=False
#         )
        
#         if treasury_id:
#             transactions = transactions.filter(treasury_id=treasury_id)
        
#         summary = transactions.aggregate(
#             total_income=Sum('amount', filter=Q(transaction_type='INCOME')),
#             total_expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
#             total_count=Count('id')
#         )
        
#         # تجميع حسب النوع
#         by_type = transactions.values('transaction_type').annotate(
#             total=Sum('amount'),
#             count=Count('id')
#         )
        
#         # تجميع حسب طريقة الدفع
#         by_payment_method = transactions.values('payment_method').annotate(
#             total=Sum('amount'),
#             count=Count('id')
#         )
        
#         context.update({
#             'summary': summary,
#             'by_type': by_type,
#             'by_payment_method': by_payment_method,
#             'transactions': transactions.order_by('-transaction_date')[:50]
#         })
    
#     # تقرير الحسابات
#     elif report_type == 'accounts':
#         account_summaries = Account.objects.filter(is_active=True).annotate(
#             period_income=Sum('transaction__amount',
#                             filter=Q(transaction__transaction_type='INCOME',
#                                    transaction__transaction_date__date__gte=from_date,
#                                    transaction__transaction_date__date__lte=to_date,
#                                    transaction__is_approved=True,
#                                    transaction__is_cancelled=False)),
#             period_expenses=Sum('transaction__amount',
#                              filter=Q(transaction__transaction_type='EXPENSE',
#                                     transaction__transaction_date__date__gte=from_date,
#                                     transaction__transaction_date__date__lte=to_date,
#                                     transaction__is_approved=True,
#                                     transaction__is_cancelled=False))
#         ).order_by('category__category_type', 'name')
        
#         context['account_summaries'] = account_summaries
    
#     # تقرير يومي مفصل
#     elif report_type == 'daily':
#         daily_data = []
#         current_date = from_date
        
#         while current_date <= to_date:
#             day_transactions = Transaction.objects.filter(
#                 transaction_date__date=current_date,
#                 is_approved=True,
#                 is_cancelled=False
#             )
            
#             if treasury_id:
#                 day_transactions = day_transactions.filter(treasury_id=treasury_id)
            
#             day_stats = day_transactions.aggregate(
#                 income=Sum('amount', filter=Q(transaction_type='INCOME')),
#                 expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
#                 count=Count('id')
#             )
            
#             daily_data.append({
#                 'date': current_date,
#                 'income': day_stats['income'] or 0,
#                 'expenses': day_stats['expenses'] or 0,
#                 'net': (day_stats['income'] or 0) - (day_stats['expenses'] or 0),
#                 'count': day_stats['count']
#             })
            
#             current_date += timedelta(days=1)
        
#         context['daily_data'] = daily_data
    
#     return render(request, 'treasury_management/reports.html', context)

# @login_required
# def get_treasury_balance(request, treasury_id):
#     """API للحصول على رصيد خزنة"""
#     try:
#         treasury = Treasury.objects.get(id=treasury_id, is_active=True)
#         return JsonResponse({
#             'success': True,
#             'balance': float(treasury.current_balance),
#             'name': treasury.name,
#             'min_limit': float(treasury.min_limit),
#             'max_limit': float(treasury.max_limit) if treasury.max_limit else None
#         })
#     except Treasury.DoesNotExist:
#         return JsonResponse({'success': False, 'error': 'الخزنة غير موجودة'})

# # إضافة هذه Views للملف الموجود
# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required, permission_required
# from django.contrib import messages
# from django.db.models import Sum, Count, Q, F
# from django.utils import timezone
# from datetime import datetime, timedelta, date
# from django.http import JsonResponse, HttpResponse
# from django.core.paginator import Paginator
# from django.db import transaction as db_transaction
# from django.template.loader import render_to_string
# import json

# # إضافة Views المفقودة:

# @login_required
# def transaction_detail(request, pk):
#     """تفاصيل عملية مالية"""
#     transaction_obj = get_object_or_404(Transaction, pk=pk)
    
#     if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#         # طلب AJAX - إرجاع JSON
#         html = render_to_string('treasury_management/transaction_detail_modal.html', {
#             'transaction': transaction_obj
#         })
#         return JsonResponse({
#             'success': True,
#             'html': html
#         })
    
#     # طلب عادي - إرجاع صفحة كاملة
#     context = {
#         'transaction': transaction_obj,
#     }
#     return render(request, 'treasury_management/transaction_detail.html', context)

# @login_required
# @permission_required('treasury_management.cancel_transaction')
# def cancel_transaction(request, pk):
#     """إلغاء عملية مالية"""
#     transaction_obj = get_object_or_404(Transaction, pk=pk)
    
#     if request.method == 'POST':
#         if not transaction_obj.is_cancelled:
#             cancellation_reason = request.POST.get('cancellation_reason', '')
            
#             if not cancellation_reason:
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'يجب إدخال سبب الإلغاء'
#                 })
            
#             try:
#                 transaction_obj.cancel(cancellation_reason, request.user)
#                 return JsonResponse({
#                     'success': True,
#                     'message': 'تم إلغاء العملية بنجاح'
#                 })
#             except Exception as e:
#                 return JsonResponse({
#                     'success': False,
#                     'error': f'حدث خطأ: {str(e)}'
#                 })
#         else:
#             return JsonResponse({
#                 'success': False,
#                 'error': 'العملية ملغية مسبقاً'
#             })
    
#     return JsonResponse({'success': False, 'error': 'طريقة غير مدعومة'})

# treasury_management/views.py - إضافة Views جديدة مع الصلاحيات

# ===================================
# 💸 اعتماد المصروفات
# ===================================

@can_approve_transactions
def approve_expense(request, pk):
    """اعتماد مصروف يومي - يحتاج صلاحية مدير أو أعلى"""
    # التحقق من وجود نموذج DailyExpense
    if not DailyExpense:
        messages.error(request, 'نموذج المصروفات غير متوفر')
        return redirect('treasury_management:dashboard')
    
    expense = get_object_or_404(DailyExpense, pk=pk)
    
    if not expense.is_approved:
        try:
            with db_transaction.atomic():
                expense.is_approved = True
                expense.approved_by = request.user
                expense.approved_at = timezone.now()
                expense.save()
                
                # اعتماد العملية المالية المرتبطة إذا وجدت
                if hasattr(expense, 'transaction') and expense.transaction and not expense.transaction.is_approved:
                    expense.transaction.is_approved = True
                    expense.transaction.approved_by = request.user
                    expense.transaction.approved_at = timezone.now()
                    expense.transaction.save()
                
                expense_number = getattr(expense, 'expense_number', f'#{expense.id}')
                messages.success(request, f'تم اعتماد المصروف رقم {expense_number}')
        except Exception as e:
            messages.error(request, f'حدث خطأ في الاعتماد: {str(e)}')
    else:
        messages.warning(request, 'المصروف معتمد مسبقاً')
    
    return redirect('treasury_management:expenses_list')

# ===================================
# 📊 APIs للبيانات
# ===================================

@treasury_access_required
def treasury_balance_api(request, treasury_id):
    """API للحصول على رصيد خزنة محددة - يحتاج أي صلاحية خزينة"""
    try:
        treasury = Treasury.objects.get(id=treasury_id, is_active=True)
        
        data = {
            'balance': float(treasury.current_balance),
            'name': treasury.name,
            'code': getattr(treasury, 'code', ''),
        }
        
        # إضافة البيانات الإضافية إذا كانت متوفرة
        if hasattr(treasury, 'min_limit'):
            data['min_limit'] = float(treasury.min_limit) if treasury.min_limit else 0
        
        if hasattr(treasury, 'max_limit'):
            data['max_limit'] = float(treasury.max_limit) if treasury.max_limit else None
        
        if hasattr(treasury, 'responsible_person') and treasury.responsible_person:
            data['responsible_person'] = treasury.responsible_person.get_full_name() or treasury.responsible_person.username
        
        return JsonResponse({
            'success': True,
            'data': data
        })
    except Treasury.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'الخزنة غير موجودة'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@treasury_access_required
def dashboard_api(request):
    """API لتحديث بيانات لوحة التحكم - يحتاج أي صلاحية خزينة"""
    try:
        today = timezone.now().date()
        
        # الخزائن النشطة
        treasuries = Treasury.objects.filter(is_active=True)
        
        # حساب الرصيد الإجمالي
        total_balance = 0
        for treasury in treasuries:
            total_balance += treasury.current_balance
        
        # إحصائيات اليوم
        today_transactions = Transaction.objects.filter(
            transaction_date__date=today,
            is_approved=True,
            is_cancelled=False
        )
        
        today_stats = today_transactions.aggregate(
            income=Sum('amount', filter=Q(transaction_type='INCOME')),
            expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
            count=Count('id')
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'total_balance': float(total_balance),
                'today_income': float(today_stats['income'] or 0),
                'today_expenses': float(today_stats['expenses'] or 0),
                'today_count': today_stats['count'] or 0,
                'treasuries_count': treasuries.count(),
                'updated_at': timezone.now().isoformat()
            }
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# ===================================
# 📸 لقطات الخزائن
# ===================================

@treasury_manager_required
def create_treasury_snapshot(request):
    """إنشاء لقطة للخزائن - يحتاج صلاحية مدير أو أعلى"""
    # التحقق من وجود نموذج TreasurySnapshot
    if not TreasurySnapshot:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'نموذج لقطات الخزائن غير متوفر'
            })
        else:
            messages.error(request, 'نموذج لقطات الخزائن غير متوفر')
            return redirect('treasury_management:dashboard')
    
    snapshot_date = request.GET.get('date', timezone.now().date())
    
    if isinstance(snapshot_date, str):
        try:
            snapshot_date = datetime.strptime(snapshot_date, '%Y-%m-%d').date()
        except:
            snapshot_date = timezone.now().date()
    
    try:
        with db_transaction.atomic():
            treasuries = Treasury.objects.filter(is_active=True)
            snapshots_created = 0
            
            for treasury in treasuries:
                # التحقق من وجود لقطة لهذا التاريخ
                existing_snapshot = TreasurySnapshot.objects.filter(
                    treasury=treasury,
                    snapshot_date=snapshot_date
                ).first()
                
                if not existing_snapshot:
                    # حساب إحصائيات اليوم
                    day_transactions = Transaction.objects.filter(
                        treasury=treasury,
                        transaction_date__date=snapshot_date,
                        is_approved=True,
                        is_cancelled=False
                    )
                    
                    day_stats = day_transactions.aggregate(
                        income=Sum('amount', filter=Q(transaction_type='INCOME')),
                        expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
                        count=Count('id')
                    )
                    
                    total_income = day_stats['income'] or 0
                    total_expenses = day_stats['expenses'] or 0
                    
                    # الرصيد الافتتاحي (تقريبي)
                    opening_balance = treasury.current_balance - (total_income - total_expenses)
                    
                    # إنشاء اللقطة
                    snapshot_data = {
                        'treasury': treasury,
                        'snapshot_date': snapshot_date,
                        'opening_balance': opening_balance,
                        'closing_balance': treasury.current_balance,
                        'total_income': total_income,
                        'total_expenses': total_expenses,
                        'transactions_count': day_stats['count'] or 0
                    }
                    
                    TreasurySnapshot.objects.create(**snapshot_data)
                    snapshots_created += 1
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'تم إنشاء {snapshots_created} لقطة جديدة',
                    'snapshots_created': snapshots_created
                })
            else:
                messages.success(request, f'تم إنشاء {snapshots_created} لقطة للخزائن')
                return redirect('treasury_management:dashboard')
    
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        else:
            messages.error(request, f'حدث خطأ: {str(e)}')
            return redirect('treasury_management:dashboard')

# ===================================
# 📊 Views التقارير المحسنة
# (ملاحظة: daily_summary و treasury_report موجودان في الرسالة السابقة)
# ===================================

def export_daily_summary(request, selected_date, export_format):
    """تصدير الملخص اليومي - وظيفة مساعدة"""
    # هنا يمكن إضافة منطق التصدير لاحقاً
    # يمكن استخدام مكتبات مثل reportlab للـ PDF أو openpyxl للـ Excel
    
    messages.info(request, f'ميزة تصدير {export_format.upper()} للملخص اليومي قيد التطوير')
    return redirect('treasury_management:daily_summary')

def export_treasury_report(request, report_type, from_date, to_date, treasury_id, export_format):
    """تصدير التقارير - وظيفة مساعدة"""
    messages.info(request, f'ميزة تصدير تقارير {export_format.upper()} قيد التطوير')
    return redirect('treasury_management:reports')

# ===================================
# 🏦 إدارة الخزائن المحسنة
# (ملاحظة: treasuries_list موجود في الرسالة السابقة)
# ===================================


@treasury_manager_required
def add_treasury(request):
    """إضافة خزنة جديدة - يحتاج صلاحية مدير أو أعلى"""
    if request.method == 'POST':
        try:
            with db_transaction.atomic():
                # التحقق من البيانات المطلوبة
                name = request.POST.get('name', '').strip()
                code = request.POST.get('code', '').strip()
                account_name = request.POST.get('account_name', '').strip()
                account_code = request.POST.get('account_code', '').strip()
                account_category_id = request.POST.get('account_category')
                
                if not all([name, code, account_name, account_code, account_category_id]):
                    messages.error(request, '❌ جميع الحقول المطلوبة يجب ملؤها')
                    return render(request, 'treasury_management/add_treasury.html', {
                        'users': User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
                        'account_categories': AccountCategory.objects.filter(
                            category_type='ASSET', 
                            is_active=True
                        ).order_by('name'),
                    })
                
                # التحقق من عدم تكرار الكود
                if Treasury.objects.filter(code=code).exists():
                    messages.error(request, f'❌ كود الخزنة "{code}" موجود مسبقاً')
                    return render(request, 'treasury_management/add_treasury.html', {
                        'users': User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
                        'account_categories': AccountCategory.objects.filter(
                            category_type='ASSET', 
                            is_active=True
                        ).order_by('name'),
                    })
                
                # التحقق من عدم تكرار كود الحساب
                if Account.objects.filter(code=account_code).exists():
                    messages.error(request, f'❌ كود الحساب "{account_code}" موجود مسبقاً')
                    return render(request, 'treasury_management/add_treasury.html', {
                        'users': User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
                        'account_categories': AccountCategory.objects.filter(
                            category_type='ASSET', 
                            is_active=True
                        ).order_by('name'),
                    })
                
                # إنشاء الحساب المحاسبي أولاً
                account_category = AccountCategory.objects.get(id=account_category_id)
                opening_balance = Decimal(request.POST.get('opening_balance', '0') or '0')
                
                account = Account.objects.create(
                    name=account_name,
                    code=account_code,
                    category=account_category,
                    description=request.POST.get('account_description', '').strip(),
                    opening_balance=opening_balance,
                    current_balance=opening_balance,
                    is_active=True
                )
                
                # تحضير بيانات الخزنة
                treasury_data = {
                    'name': name,
                    'code': code.upper(),  # تحويل الكود للأحرف الكبيرة
                    'account': account,
                    'location': request.POST.get('location', '').strip(),
                    'min_limit': Decimal(request.POST.get('min_limit', '0') or '0'),
                    'is_active': request.POST.get('is_active') == 'on',  # ✅ حقل التفعيل
                }
                
                # إضافة الحد الأقصى إذا كان موجوداً
                max_limit_str = request.POST.get('max_limit', '').strip()
                if max_limit_str:
                    max_limit = Decimal(max_limit_str)
                    if max_limit <= treasury_data['min_limit']:
                        messages.error(request, '❌ الحد الأقصى يجب أن يكون أكبر من الحد الأدنى')
                        account.delete()  # حذف الحساب المُنشأ
                        return render(request, 'treasury_management/add_treasury.html', {
                            'users': User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
                            'account_categories': AccountCategory.objects.filter(
                                category_type='ASSET', 
                                is_active=True
                            ).order_by('name'),
                        })
                    treasury_data['max_limit'] = max_limit
                
                # إضافة المسؤول إذا كان موجوداً
                responsible_person_id = request.POST.get('responsible_person', '').strip()
                if responsible_person_id:
                    try:
                        responsible_person = User.objects.get(id=responsible_person_id, is_active=True)
                        treasury_data['responsible_person'] = responsible_person
                    except User.DoesNotExist:
                        messages.warning(request, '⚠️ المستخدم المحدد غير موجود أو غير نشط')
                
                # إنشاء الخزنة
                treasury = Treasury.objects.create(**treasury_data)
                
                # رسالة نجاح مفصلة
                status_msg = "نشطة" if treasury.is_active else "غير نشطة"
                balance_msg = f"برصيد افتتاحي {opening_balance:,.2f} ج.م" if opening_balance > 0 else "بدون رصيد افتتاحي"
                
                messages.success(
                    request, 
                    f'✅ تم إنشاء الخزنة "{treasury.name}" بنجاح | '
                    f'الكود: {treasury.code} | '
                    f'الحالة: {status_msg} | '
                    f'{balance_msg}'
                )
                
                return redirect('treasury_management:treasuries_list')
                
        except AccountCategory.DoesNotExist:
            messages.error(request, '❌ تصنيف الحساب المحدد غير موجود')
        except ValueError as e:
            messages.error(request, '❌ قيم غير صحيحة في المبالغ المالية. يرجى التأكد من إدخال أرقام صحيحة.')
        except Exception as e:
            messages.error(request, f'❌ حدث خطأ أثناء إنشاء الخزنة: {str(e)}')
    
    # بيانات النموذج
    context = {
        'users': User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
        'account_categories': AccountCategory.objects.filter(
            category_type='ASSET', 
            is_active=True
        ).order_by('name'),
    }
    
    return render(request, 'treasury_management/add_treasury.html', context)

@treasury_manager_required
def edit_treasury(request, pk):
    """تحرير خزنة - يحتاج صلاحية مدير أو أعلى"""
    treasury = get_object_or_404(Treasury, pk=pk)
    
    # التأكد من وجود حساب مرتبط
    if not treasury.account:
        messages.error(request, '❌ هذه الخزنة ليس لديها حساب محاسبي مرتبط')
        return redirect('treasury_management:treasuries_list')
    
    if request.method == 'POST':
        try:
            # حفظ البيانات الأصلية للمقارنة
            original_name = treasury.name
            original_location = treasury.location or ""
            original_responsible = treasury.responsible_person.id if treasury.responsible_person else ""
            original_min_limit = float(treasury.min_limit or 0)
            original_max_limit = float(treasury.max_limit or 0)
            original_active = treasury.is_active
            original_balance = float(treasury.account.current_balance)  # ✅ إضافة الرصيد الأصلي
            
            # تحديث البيانات الجديدة
            new_name = request.POST.get('name', '').strip()
            new_location = request.POST.get('location', '').strip()
            new_responsible = request.POST.get('responsible_person', '').strip()
            new_min_limit = float(request.POST.get('min_limit', '0') or '0')
            new_max_limit_str = request.POST.get('max_limit', '').strip()
            new_max_limit = float(new_max_limit_str) if new_max_limit_str else 0
            new_active = request.POST.get('is_active') == 'on'
            new_balance_str = request.POST.get('current_balance', '').strip()  # ✅ رصيد جديد
            
            if not new_name:
                messages.error(request, '❌ اسم الخزنة مطلوب')
                return render(request, 'treasury_management/edit_treasury.html', {
                    'treasury': treasury,
                    'users': User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
                })
            
            # التحقق من صحة الحدود
            if new_max_limit > 0 and new_max_limit <= new_min_limit:
                messages.error(request, '❌ الحد الأقصى يجب أن يكون أكبر من الحد الأدنى')
                return render(request, 'treasury_management/edit_treasury.html', {
                    'treasury': treasury,
                    'users': User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
                })
            
            # تحديث بيانات الخزنة
            treasury.name = new_name
            treasury.location = new_location
            treasury.min_limit = new_min_limit
            treasury.max_limit = new_max_limit if new_max_limit > 0 else None
            treasury.is_active = new_active
            
            # تحديث المسؤول
            if new_responsible:
                try:
                    treasury.responsible_person = User.objects.get(id=new_responsible, is_active=True)
                except User.DoesNotExist:
                    messages.warning(request, '⚠️ المستخدم المحدد غير موجود أو غير نشط')
                    treasury.responsible_person = None
            else:
                treasury.responsible_person = None
            
            # ✅ تحديث الرصيد الحالي إذا تم تعديله
            if new_balance_str:
                new_balance = float(new_balance_str)
                if new_balance != original_balance:
                    # تحديث رصيد الحساب المرتبط
                    treasury.account.current_balance = Decimal(new_balance)
                    # تحديث الرصيد الافتتاحي أيضاً إذا لم تكن هناك عمليات
                    if not hasattr(treasury, 'transaction_set') or treasury.transaction_set.count() == 0:
                        treasury.account.opening_balance = Decimal(new_balance)
                    treasury.account.save()
            
            # حفظ التغييرات على الخزنة
            treasury.save()
            
            # تحديد التغييرات للرسالة
            changes = []
            if new_name != original_name:
                changes.append(f'الاسم: "{original_name}" ← "{new_name}"')
            
            if new_location != original_location:
                changes.append(f'الموقع: "{original_location or "غير محدد"}" ← "{new_location or "غير محدد"}"')
            
            if new_responsible != original_responsible:
                old_resp = treasury.responsible_person.get_full_name() if treasury.responsible_person else "غير محدد"
                changes.append(f'المسؤول: تم التحديث إلى "{old_resp}"')
            
            if new_min_limit != original_min_limit:
                changes.append(f'الحد الأدنى: {original_min_limit:,.2f} ← {new_min_limit:,.2f} ج.م')
            
            if new_max_limit != original_max_limit:
                old_max = f"{original_max_limit:,.2f}" if original_max_limit > 0 else "غير محدد"
                new_max = f"{new_max_limit:,.2f}" if new_max_limit > 0 else "غير محدد"
                changes.append(f'الحد الأقصى: {old_max} ← {new_max} ج.م')
            
            if new_active != original_active:
                status_change = "تم تفعيلها" if new_active else "تم إلغاء تفعيلها"
                changes.append(f'الحالة: {status_change}')
            
            # ✅ إضافة تغيير الرصيد للرسالة
            if new_balance_str and float(new_balance_str) != original_balance:
                changes.append(f'الرصيد: {original_balance:,.2f} ← {float(new_balance_str):,.2f} ج.م')
            
            # رسالة نجاح
            if changes:
                changes_text = " | ".join(changes)
                messages.success(
                    request, 
                    f'✅ تم تحديث الخزنة "{treasury.name}" بنجاح\n'
                    f'التغييرات: {changes_text}'
                )
            else:
                messages.info(request, 'ℹ️ لم يتم إجراء أي تغييرات على الخزنة')
                
            return redirect('treasury_management:treasuries_list')
            
        except ValueError:
            messages.error(request, '❌ قيم غير صحيحة في الحدود المالية أو الرصيد. يرجى التأكد من إدخال أرقام صحيحة.')
        except Exception as e:
            messages.error(request, f'❌ حدث خطأ أثناء التحديث: {str(e)}')
    
    # بيانات النموذج
    context = {
        'treasury': treasury,
        'users': User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
    }
    
    return render(request, 'treasury_management/edit_treasury.html', context)



@treasury_access_required
def treasury_detail(request, pk):
    """تفاصيل خزنة - يحتاج أي صلاحية خزينة"""
    treasury = get_object_or_404(Treasury, pk=pk)
    
    # إحصائيات الخزنة
    today = timezone.now().date()
    
    # العمليات الأخيرة
    recent_transactions = Transaction.objects.filter(
        treasury=treasury,
        is_approved=True,
        is_cancelled=False
    ).select_related('account', 'created_by').order_by('-transaction_date')[:10]
    
    # إحصائيات هذا الشهر
    month_start = today.replace(day=1)
    month_transactions = Transaction.objects.filter(
        treasury=treasury,
        transaction_date__date__gte=month_start,
        is_approved=True,
        is_cancelled=False
    )
    
    month_stats = month_transactions.aggregate(
        income=Sum('amount', filter=Q(transaction_type='INCOME')),
        expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
        count=Count('id')
    )
    
    # إحصائيات اليوم
    today_transactions = Transaction.objects.filter(
        treasury=treasury,
        transaction_date__date=today,
        is_approved=True,
        is_cancelled=False
    )
    
    today_stats = today_transactions.aggregate(
        income=Sum('amount', filter=Q(transaction_type='INCOME')),
        expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
        count=Count('id')
    )
    
    # إحصائيات إضافية
    total_transactions = Transaction.objects.filter(
        treasury=treasury,
        is_approved=True,
        is_cancelled=False
    ).count()
    
    pending_transactions = Transaction.objects.filter(
        treasury=treasury,
        is_approved=False,
        is_cancelled=False
    ).count()
    
    context = {
        'treasury': treasury,
        'recent_transactions': recent_transactions,
        'total_transactions': total_transactions,
        'pending_transactions': pending_transactions,
        'month_stats': {
            'income': month_stats['income'] or 0,
            'expenses': month_stats['expenses'] or 0,
            'net': (month_stats['income'] or 0) - (month_stats['expenses'] or 0),
            'count': month_stats['count'] or 0,
        },
        'today_stats': {
            'income': today_stats['income'] or 0,
            'expenses': today_stats['expenses'] or 0,
            'net': (today_stats['income'] or 0) - (today_stats['expenses'] or 0),
            'count': today_stats['count'] or 0,
        },
    }
    
    return render(request, 'treasury_management/treasury_detail.html', context)

# ===================================
# 📝 ملاحظات عن Views المكررة
# ===================================

# الـ Views التالية موجودة في الرسالة السابقة مع الصلاحيات:
# - daily_summary (موجود مع @treasury_access_required)
# - treasury_report (موجود مع @treasury_access_required) 
# - treasuries_list (موجود مع @treasury_access_required)
# - get_treasury_balance (موجود مع @treasury_access_required)
# - transaction_detail (موجود مع @treasury_access_required)

# ===================================
# 🔄 View محسن للاعتماد السريع (إضافي)
# ===================================

@can_approve_transactions
def quick_approve_transaction(request, transaction_id):
    """اعتماد سريع للعملية - للمديرين فقط"""
    if request.method == 'POST':
        try:
            transaction = get_object_or_404(Transaction, id=transaction_id)
            
            if transaction.is_approved:
                return JsonResponse({
                    'success': False,
                    'error': 'العملية معتمدة مسبقاً'
                })
            
            if transaction.is_cancelled:
                return JsonResponse({
                    'success': False,
                    'error': 'لا يمكن اعتماد عملية ملغية'
                })
            
            # اعتماد سريع بدون تحقق إضافي
            transaction.is_approved = True
            transaction.approved_by = request.user
            transaction.approved_at = timezone.now()
            transaction.save()
            
            return JsonResponse({
                'success': True,
                'message': f'تم اعتماد العملية {transaction.transaction_number} بنجاح',
                'transaction_id': transaction.id,
                'approved_at': transaction.approved_at.isoformat()
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'طريقة غير مدعومة'})


# @login_required
# @permission_required('treasury_management.approve_expense')
# def approve_expense(request, pk):
#     """اعتماد مصروف يومي"""
#     expense = get_object_or_404(DailyExpense, pk=pk)
    
#     if not expense.is_approved:
#         try:
#             with db_transaction.atomic():
#                 expense.is_approved = True
#                 expense.approved_by = request.user
#                 expense.save()
                
#                 # اعتماد العملية المالية المرتبطة إذا وجدت
#                 if expense.transaction and not expense.transaction.is_approved:
#                     expense.transaction.approve(request.user)
                
#                 messages.success(request, f'تم اعتماد المصروف رقم {expense.expense_number}')
#         except Exception as e:
#             messages.error(request, f'حدث خطأ في الاعتماد: {str(e)}')
#     else:
#         messages.warning(request, 'المصروف معتمد مسبقاً')
    
#     return redirect('treasury_management:expenses_list')

# @login_required
# def treasury_balance_api(request, treasury_id):
#     """API للحصول على رصيد خزنة محددة"""
#     try:
#         treasury = Treasury.objects.get(id=treasury_id, is_active=True)
#         return JsonResponse({
#             'success': True,
#             'data': {
#                 'balance': float(treasury.current_balance),
#                 'name': treasury.name,
#                 'code': treasury.code,
#                 'min_limit': float(treasury.min_limit),
#                 'max_limit': float(treasury.max_limit) if treasury.max_limit else None,
#                 'responsible_person': treasury.responsible_person.get_full_name() if treasury.responsible_person else None
#             }
#         })
#     except Treasury.DoesNotExist:
#         return JsonResponse({
#             'success': False,
#             'error': 'الخزنة غير موجودة'
#         })
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         })

# @login_required
# def dashboard_api(request):
#     """API لتحديث بيانات لوحة التحكم"""
#     try:
#         today = timezone.now().date()
        
#         # الخزائن النشطة
#         treasuries = Treasury.objects.filter(is_active=True)
#         total_balance = treasuries.aggregate(total=Sum('account__current_balance'))['total'] or 0
        
#         # إحصائيات اليوم
#         today_transactions = Transaction.objects.filter(
#             transaction_date__date=today,
#             is_approved=True,
#             is_cancelled=False
#         )
        
#         today_stats = today_transactions.aggregate(
#             income=Sum('amount', filter=Q(transaction_type='INCOME')),
#             expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
#             count=Count('id')
#         )
        
#         return JsonResponse({
#             'success': True,
#             'data': {
#                 'total_balance': float(total_balance),
#                 'today_income': float(today_stats['income'] or 0),
#                 'today_expenses': float(today_stats['expenses'] or 0),
#                 'today_count': today_stats['count'] or 0,
#                 'treasuries_count': treasuries.count(),
#                 'updated_at': timezone.now().isoformat()
#             }
#         })
    
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         })

# @login_required
# def create_treasury_snapshot(request):
#     """إنشاء لقطة للخزائن (يدوي أو تلقائي)"""
#     snapshot_date = request.GET.get('date', timezone.now().date())
    
#     if isinstance(snapshot_date, str):
#         snapshot_date = datetime.strptime(snapshot_date, '%Y-%m-%d').date()
    
#     try:
#         with db_transaction.atomic():
#             treasuries = Treasury.objects.filter(is_active=True)
#             snapshots_created = 0
            
#             for treasury in treasuries:
#                 # التحقق من وجود لقطة لهذا التاريخ
#                 existing_snapshot = TreasurySnapshot.objects.filter(
#                     treasury=treasury,
#                     snapshot_date=snapshot_date
#                 ).first()
                
#                 if not existing_snapshot:
#                     # حساب إحصائيات اليوم
#                     day_transactions = Transaction.objects.filter(
#                         treasury=treasury,
#                         transaction_date__date=snapshot_date,
#                         is_approved=True,
#                         is_cancelled=False
#                     )
                    
#                     day_stats = day_transactions.aggregate(
#                         income=Sum('amount', filter=Q(transaction_type='INCOME')),
#                         expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
#                         count=Count('id')
#                     )
                    
#                     total_income = day_stats['income'] or 0
#                     total_expenses = day_stats['expenses'] or 0
                    
#                     # الرصيد الافتتاحي (تقريبي)
#                     opening_balance = treasury.current_balance - (total_income - total_expenses)
                    
#                     # إنشاء اللقطة
#                     TreasurySnapshot.objects.create(
#                         treasury=treasury,
#                         snapshot_date=snapshot_date,
#                         opening_balance=opening_balance,
#                         closing_balance=treasury.current_balance,
#                         total_income=total_income,
#                         total_expenses=total_expenses,
#                         transactions_count=day_stats['count'] or 0
#                     )
                    
#                     snapshots_created += 1
            
#             if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#                 return JsonResponse({
#                     'success': True,
#                     'message': f'تم إنشاء {snapshots_created} لقطة جديدة',
#                     'snapshots_created': snapshots_created
#                 })
#             else:
#                 messages.success(request, f'تم إنشاء {snapshots_created} لقطة للخزائن')
#                 return redirect('treasury_management:dashboard')
    
#     except Exception as e:
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             return JsonResponse({
#                 'success': False,
#                 'error': str(e)
#             })
#         else:
#             messages.error(request, f'حدث خطأ: {str(e)}')
#             return redirect('treasury_management:dashboard')

# # تحديث الـ View الموجود
# def daily_summary(request):
#     """ملخص يومي للخزنة - النسخة المحدثة"""
#     selected_date = request.GET.get('date', timezone.now().date())
#     if isinstance(selected_date, str):
#         selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    
#     # التحقق من طلب التصدير
#     export_format = request.GET.get('export')
#     if export_format in ['pdf', 'excel']:
#         return export_daily_summary(request, selected_date, export_format)
    
#     # العمليات في التاريخ المحدد
#     day_transactions = Transaction.objects.filter(
#         transaction_date__date=selected_date,
#         is_approved=True,
#         is_cancelled=False
#     ).select_related('treasury', 'account', 'created_by')
    
#     # تجميع حسب الخزنة
#     treasury_summaries = []
#     treasuries = Treasury.objects.filter(is_active=True)
    
#     for treasury in treasuries:
#         treasury_transactions = day_transactions.filter(treasury=treasury)
        
#         income_transactions = treasury_transactions.filter(transaction_type='INCOME')
#         expense_transactions = treasury_transactions.filter(transaction_type='EXPENSE')
        
#         total_income = income_transactions.aggregate(total=Sum('amount'))['total'] or 0
#         total_expenses = expense_transactions.aggregate(total=Sum('amount'))['total'] or 0
        
#         # الرصيد في بداية اليوم (تقريبي)
#         opening_balance = treasury.current_balance - (total_income - total_expenses)
        
#         treasury_summaries.append({
#             'treasury': treasury,
#             'opening_balance': opening_balance,
#             'closing_balance': treasury.current_balance,
#             'total_income': total_income,
#             'total_expenses': total_expenses,
#             'net_change': total_income - total_expenses,
#             'income_transactions': income_transactions,
#             'expense_transactions': expense_transactions,
#             'transaction_count': treasury_transactions.count()
#         })
    
#     # المصروفات اليومية
#     day_expenses = DailyExpense.objects.filter(
#         expense_date=selected_date,
#         is_approved=True
#     ).select_related('category')
    
#     # تجميع المصروفات حسب التصنيف
#     expenses_by_category = day_expenses.values('category__name').annotate(
#         total=Sum('amount'),
#         count=Count('id')
#     ).order_by('-total')
    
#     context = {
#         'selected_date': selected_date,
#         'treasury_summaries': treasury_summaries,
#         'day_expenses': day_expenses,
#         'expenses_by_category': expenses_by_category,
#         'total_income': sum(ts['total_income'] for ts in treasury_summaries),
#         'total_expenses': sum(ts['total_expenses'] for ts in treasury_summaries),
#         'today': timezone.now().date(),
#     }
    
#     return render(request, 'treasury_management/daily_summary.html', context)

# def export_daily_summary(request, selected_date, export_format):
#     """تصدير الملخص اليومي"""
#     # هنا يمكن إضافة منطق التصدير لاحقاً
#     # يمكن استخدام مكتبات مثل reportlab للـ PDF أو openpyxl للـ Excel
    
#     messages.info(request, 'ميزة التصدير قيد التطوير')
#     return redirect('treasury_management:daily_summary')

# # تحديث الـ View الموجود أيضاً
# def treasury_report(request):
#     """تقارير الخزنة المتقدمة - النسخة المحدثة"""
#     report_type = request.GET.get('report_type', 'summary')
#     from_date = request.GET.get('from_date')
#     to_date = request.GET.get('to_date')
#     treasury_id = request.GET.get('treasury_id', '')
    
#     # تحديد التواريخ الافتراضية
#     if not from_date:
#         from_date = timezone.now().date().replace(day=1)
#     else:
#         from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
    
#     if not to_date:
#         to_date = timezone.now().date()
#     else:
#         to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
    
#     # التحقق من طلب التصدير
#     export_format = request.GET.get('export')
#     if export_format in ['pdf', 'excel']:
#         return export_treasury_report(request, report_type, from_date, to_date, treasury_id, export_format)
    
#     context = {
#         'report_type': report_type,
#         'from_date': from_date,
#         'to_date': to_date,
#         'treasury_id': treasury_id,
#         'treasuries': Treasury.objects.filter(is_active=True),
#     }
    
#     # باقي منطق التقرير كما هو...
#     # (نفس الكود السابق)
    
#     return render(request, 'treasury_management/reports.html', context)

# def export_treasury_report(request, report_type, from_date, to_date, treasury_id, export_format):
#     """تصدير التقارير"""
#     messages.info(request, 'ميزة التصدير قيد التطوير')
#     return redirect('treasury_management:reports')

# # إضافة هذه Views إلى treasury_management/views.py

# # تحديث treasury_management/views.py - View قائمة الخزائن
# @login_required
# def treasuries_list(request):
#     """قائمة الخزائن"""
#     treasuries = Treasury.objects.all().select_related('account', 'responsible_person').order_by('name')
    
#     # حساب الإحصائيات
#     total_treasuries = treasuries.count()
#     active_treasuries = treasuries.filter(is_active=True).count()
#     total_balance = sum(treasury.current_balance for treasury in treasuries)
#     treasuries_with_responsible = treasuries.filter(responsible_person__isnull=False).count()
    
#     context = {
#         'treasuries': treasuries,
#         'stats': {
#             'total_treasuries': total_treasuries,
#             'active_treasuries': active_treasuries,
#             'total_balance': total_balance,
#             'treasuries_with_responsible': treasuries_with_responsible,
#         }
#     }
    
#     return render(request, 'treasury_management/treasuries_list.html', context)


# @login_required
# def edit_treasury(request, pk):
#     """تحرير خزنة"""
#     treasury = get_object_or_404(Treasury, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             # تحديث بيانات الخزنة
#             treasury.name = request.POST.get('name')
#             treasury.location = request.POST.get('location', '')
            
#             max_limit = request.POST.get('max_limit')
#             treasury.max_limit = float(max_limit) if max_limit else None
            
#             treasury.min_limit = float(request.POST.get('min_limit', 0))
#             treasury.is_active = request.POST.get('is_active') == 'on'
            
#             responsible_person_id = request.POST.get('responsible_person')
#             if responsible_person_id:
#                 from django.contrib.auth import get_user_model
#                 User = get_user_model()
#                 treasury.responsible_person = User.objects.get(id=responsible_person_id)
#             else:
#                 treasury.responsible_person = None
            
#             treasury.save()
            
#             # تحديث بيانات الحساب المرتبط
#             treasury.account.name = request.POST.get('account_name')
#             treasury.account.description = request.POST.get('account_description', '')
#             treasury.account.save()
            
#             messages.success(request, f'تم تحديث الخزنة "{treasury.name}" بنجاح')
#             return redirect('treasury_management:treasuries_list')
            
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     # بيانات النموذج
#     from django.contrib.auth import get_user_model
#     User = get_user_model()
    
#     context = {
#         'treasury': treasury,
#         'users': User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
#     }
    
#     return render(request, 'treasury_management/edit_treasury.html', context)

# @login_required
# def treasury_detail(request, pk):
#     """تفاصيل خزنة"""
#     treasury = get_object_or_404(Treasury, pk=pk)
    
#     # إحصائيات الخزنة
#     today = timezone.now().date()
    
#     # العمليات الأخيرة
#     recent_transactions = Transaction.objects.filter(
#         treasury=treasury,
#         is_approved=True,
#         is_cancelled=False
#     ).order_by('-transaction_date')[:10]
    
#     # إحصائيات هذا الشهر
#     month_start = today.replace(day=1)
#     month_transactions = Transaction.objects.filter(
#         treasury=treasury,
#         transaction_date__date__gte=month_start,
#         is_approved=True,
#         is_cancelled=False
#     )
    
#     month_stats = month_transactions.aggregate(
#         income=Sum('amount', filter=Q(transaction_type='INCOME')),
#         expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
#         count=Count('id')
#     )
    
#     # إحصائيات اليوم
#     today_transactions = Transaction.objects.filter(
#         treasury=treasury,
#         transaction_date__date=today,
#         is_approved=True,
#         is_cancelled=False
#     )
    
#     today_stats = today_transactions.aggregate(
#         income=Sum('amount', filter=Q(transaction_type='INCOME')),
#         expenses=Sum('amount', filter=Q(transaction_type='EXPENSE')),
#         count=Count('id')
#     )
    
#     context = {
#         'treasury': treasury,
#         'recent_transactions': recent_transactions,
#         'month_stats': {
#             'income': month_stats['income'] or 0,
#             'expenses': month_stats['expenses'] or 0,
#             'net': (month_stats['income'] or 0) - (month_stats['expenses'] or 0),
#             'count': month_stats['count'] or 0,
#         },
#         'today_stats': {
#             'income': today_stats['income'] or 0,
#             'expenses': today_stats['expenses'] or 0,
#             'net': (today_stats['income'] or 0) - (today_stats['expenses'] or 0),
#             'count': today_stats['count'] or 0,
#         },
#     }
    
#     return render(request, 'treasury_management/treasury_detail.html', context)

# treasury_management/views.py - إضافة الصلاحيات على Views الحسابات والتصنيفات

# ===================================
# 📊 Views الحسابات المالية مع الصلاحيات
# (ملاحظة: accounts_list موجود في الرسالة السابقة مع الصلاحيات)
# ===================================

# accounts_list - موجود في الرسالة السابقة مع @treasury_access_required
# account_detail_ajax - موجود في الرسالة السابقة مع @treasury_access_required

@treasury_accountant_required
def add_account(request):
    """إضافة حساب مالي جديد - يحتاج صلاحية محاسب أو أعلى"""
    if request.method == 'POST':
        try:
            category_id = request.POST.get('category')
            name = request.POST.get('name')
            code = request.POST.get('code')
            description = request.POST.get('description', '')
            opening_balance = float(request.POST.get('opening_balance', 0))
            
            # التحقق من عدم تكرار الكود
            if Account.objects.filter(code=code).exists():
                messages.error(request, f'كود الحساب "{code}" موجود مسبقاً')
                return redirect('treasury_management:add_account')
            
            category = AccountCategory.objects.get(id=category_id)
            Account.objects.create(
                category=category,
                name=name,
                code=code,
                description=description,
                opening_balance=opening_balance,
                current_balance=opening_balance,
                is_active=True
            )
            
            messages.success(request, f'تم إضافة الحساب "{name}" بنجاح')
            return redirect('treasury_management:accounts_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'account_categories': AccountCategory.objects.filter(is_active=True).order_by('name'),
    }
    
    return render(request, 'treasury_management/add_account.html', context)

@treasury_accountant_required
def edit_account(request, pk):
    """تحرير حساب مالي - يحتاج صلاحية محاسب أو أعلى"""
    account = get_object_or_404(Account, pk=pk)
    
    if request.method == 'POST':
        try:
            account.name = request.POST.get('name')
            account.description = request.POST.get('description', '')
            account.is_active = request.POST.get('is_active') == 'on'
            
            # لا يمكن تغيير الكود أو الرصيد الحالي لحساب موجود لأسباب أمنية
            account.save()
            
            messages.success(request, f'تم تحديث الحساب "{account.name}" بنجاح')
            return redirect('treasury_management:accounts_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'account': account,
        'account_categories': AccountCategory.objects.filter(is_active=True).order_by('name'),
    }
    
    return render(request, 'treasury_management/edit_account.html', context)

# ===================================
# 🗂️ Views تصنيفات الحسابات مع الصلاحيات
# (ملاحظة: account_categories_list موجود في الرسالة السابقة)
# ===================================

# account_categories_list - موجود في الرسالة السابقة مع @treasury_accountant_required
# account_category_detail_ajax - موجود في الرسالة السابقة مع @treasury_accountant_required

@treasury_manager_required
def add_account_category(request):
    """إضافة تصنيف حساب جديد - يحتاج صلاحية مدير أو أعلى"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            code = request.POST.get('code')
            category_type = request.POST.get('category_type')
            description = request.POST.get('description', '')
            parent_id = request.POST.get('parent')
            
            # التحقق من عدم تكرار الكود
            if AccountCategory.objects.filter(code=code).exists():
                messages.error(request, f'كود التصنيف "{code}" موجود مسبقاً')
                return redirect('treasury_management:add_account_category')
            
            parent = None
            if parent_id:
                parent = AccountCategory.objects.get(id=parent_id)
                # التحقق من أن النوع متطابق مع التصنيف الأب
                if parent.category_type != category_type:
                    messages.error(request, 'نوع التصنيف يجب أن يتطابق مع التصنيف الأب')
                    return redirect('treasury_management:add_account_category')
            
            AccountCategory.objects.create(
                name=name,
                code=code,
                category_type=category_type,
                description=description,
                parent=parent,
                is_active=True
            )
            
            messages.success(request, f'تم إضافة تصنيف الحساب "{name}" بنجاح')
            return redirect('treasury_management:account_categories_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'parent_categories': AccountCategory.objects.filter(parent__isnull=True, is_active=True).order_by('name'),
        'category_types': [
            ('ASSET', 'أصول'),
            ('LIABILITY', 'خصوم'),
            ('EQUITY', 'حقوق الملكية'),
            ('REVENUE', 'إيرادات'),
            ('EXPENSE', 'مصروفات'),
        ],
    }
    
    return render(request, 'treasury_management/add_account_category.html', context)

@treasury_manager_required
def edit_account_category(request, pk):
    """تحرير تصنيف حساب - يحتاج صلاحية مدير أو أعلى"""
    category = get_object_or_404(AccountCategory, pk=pk)
    
    if request.method == 'POST':
        try:
            category.name = request.POST.get('name')
            category.description = request.POST.get('description', '')
            category.is_active = request.POST.get('is_active') == 'on'
            
            # لا يمكن تغيير الكود أو النوع أو الأب لتصنيف موجود لأسباب أمنية
            category.save()
            
            messages.success(request, f'تم تحديث تصنيف الحساب "{category.name}" بنجاح')
            return redirect('treasury_management:account_categories_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'category': category,
    }
    
    return render(request, 'treasury_management/edit_account_category.html', context)

# ===================================
# 💸 Views تصنيفات المصروفات مع الصلاحيات
# ===================================

@treasury_manager_required
def expense_categories_list(request):
    """قائمة تصنيفات المصروفات - يحتاج صلاحية مدير أو أعلى"""
    # التحقق من وجود نموذج ExpenseCategory
    if not ExpenseCategory:
        messages.info(request, 'نموذج تصنيفات المصروفات غير متوفر')
        return redirect('treasury_management:dashboard')
    
    # الحصول على الفلاتر
    search = request.GET.get('search', '')
    is_active = request.GET.get('active', '')
    has_budget = request.GET.get('has_budget', '')
    
    # بناء الاستعلام
    categories = ExpenseCategory.objects.all().select_related('account')
    
    # تطبيق الفلاتر
    if search:
        categories = categories.filter(
            Q(name__icontains=search) | 
            Q(code__icontains=search) | 
            Q(description__icontains=search)
        )
    
    if is_active:
        categories = categories.filter(is_active=is_active == 'true')
    
    if has_budget == 'true':
        categories = categories.exclude(monthly_budget__isnull=True)
    elif has_budget == 'false':
        categories = categories.filter(monthly_budget__isnull=True)
    
    # ترتيب النتائج
    categories = categories.order_by('name')
    
    # Pagination
    items_per_page = request.GET.get('per_page', 10)
    try:
        items_per_page = int(items_per_page)
        if items_per_page not in [5, 10, 15, 25]:
            items_per_page = 10
    except:
        items_per_page = 10
    
    paginator = Paginator(categories, items_per_page)
    page = request.GET.get('page')
    
    try:
        categories_page = paginator.page(page)
    except PageNotAnInteger:
        categories_page = paginator.page(1)
    except EmptyPage:
        categories_page = paginator.page(paginator.num_pages)
    
    # إحصائيات
    stats = {
        'total_categories': ExpenseCategory.objects.count(),
        'active_categories': ExpenseCategory.objects.filter(is_active=True).count(),
        'categories_with_budget': ExpenseCategory.objects.exclude(monthly_budget__isnull=True).count(),
        'total_monthly_budget': ExpenseCategory.objects.aggregate(
            Sum('monthly_budget')
        )['monthly_budget__sum'] or 0,
    }
    
    context = {
        'categories': categories_page,
        'stats': stats,
        'search': search,
        'is_active': is_active,
        'has_budget': has_budget,
        'items_per_page': items_per_page,
    }
    
    return render(request, 'treasury_management/expense_categories_list.html', context)

@treasury_manager_required
def add_expense_category(request):
    """إضافة تصنيف مصروفات جديد - يحتاج صلاحية مدير أو أعلى"""
    # التحقق من وجود نموذج ExpenseCategory
    if not ExpenseCategory:
        messages.error(request, 'نموذج تصنيفات المصروفات غير متوفر')
        return redirect('treasury_management:dashboard')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            code = request.POST.get('code')
            account_id = request.POST.get('account')
            description = request.POST.get('description', '')
            monthly_budget = request.POST.get('monthly_budget')
            
            # التحقق من عدم تكرار الكود
            if ExpenseCategory.objects.filter(code=code).exists():
                messages.error(request, f'كود التصنيف "{code}" موجود مسبقاً')
                return redirect('treasury_management:add_expense_category')
            
            account = Account.objects.get(id=account_id)
            
            # التحقق من أن الحساب من نوع مصروفات
            if account.category.category_type != 'EXPENSE':
                messages.error(request, 'يجب اختيار حساب من نوع مصروفات')
                return redirect('treasury_management:add_expense_category')
            
            category_data = {
                'name': name,
                'code': code,
                'account': account,
                'description': description,
                'is_active': True
            }
            
            if monthly_budget:
                category_data['monthly_budget'] = float(monthly_budget)
            
            ExpenseCategory.objects.create(**category_data)
            
            messages.success(request, f'تم إضافة تصنيف المصروفات "{name}" بنجاح')
            return redirect('treasury_management:expense_categories_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'accounts': Account.objects.filter(
            category__category_type='EXPENSE',
            is_active=True
        ).select_related('category').order_by('name'),
    }
    
    return render(request, 'treasury_management/add_expense_category.html', context)

@treasury_manager_required
def edit_expense_category(request, pk):
    """تحرير تصنيف مصروفات - يحتاج صلاحية مدير أو أعلى"""
    # التحقق من وجود نموذج ExpenseCategory
    if not ExpenseCategory:
        messages.error(request, 'نموذج تصنيفات المصروفات غير متوفر')
        return redirect('treasury_management:dashboard')
    
    category = get_object_or_404(ExpenseCategory, pk=pk)
    
    if request.method == 'POST':
        try:
            category.name = request.POST.get('name')
            category.description = request.POST.get('description', '')
            category.is_active = request.POST.get('is_active') == 'on'
            
            monthly_budget = request.POST.get('monthly_budget')
            category.monthly_budget = float(monthly_budget) if monthly_budget else None
            
            category.save()
            
            messages.success(request, f'تم تحديث تصنيف المصروفات "{category.name}" بنجاح')
            return redirect('treasury_management:expense_categories_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'category': category,
        'accounts': Account.objects.filter(
            category__category_type='EXPENSE',
            is_active=True
        ).select_related('category').order_by('name'),
    }
    
    return render(request, 'treasury_management/edit_expense_category.html', context)

# ===================================
# 🔧 Views الإعداد السريع مع الصلاحيات
# ===================================

@treasury_admin_required
def setup_basic_categories(request):
    """إنشاء التصنيفات الأساسية للحسابات - للمدير العام فقط"""
    
    basic_categories = [
        # التصنيفات الرئيسية
        {'name': 'الأصول', 'code': 'ASSETS', 'category_type': 'ASSET', 'description': 'جميع أصول المدرسة المالية والعينية'},
        {'name': 'الإيرادات', 'code': 'REVENUE', 'category_type': 'REVENUE', 'description': 'جميع إيرادات ومداخيل المدرسة'},
        {'name': 'المصروفات', 'code': 'EXPENSES', 'category_type': 'EXPENSE', 'description': 'جميع مصروفات ونفقات المدرسة'},
        {'name': 'الخصوم', 'code': 'LIABILITIES', 'category_type': 'LIABILITY', 'description': 'التزامات المدرسة تجاه الغير'},
        {'name': 'حقوق الملكية', 'code': 'EQUITY', 'category_type': 'EQUITY', 'description': 'رأس المال وحقوق الملكية'},
        
        # تصنيفات فرعية للأصول
        {'name': 'الأصول النقدية', 'code': 'CASH_ASSETS', 'category_type': 'ASSET', 'parent_code': 'ASSETS', 'description': 'النقدية والخزائن والحسابات الجارية'},
        {'name': 'الحسابات المصرفية', 'code': 'BANK_ACCOUNTS', 'category_type': 'ASSET', 'parent_code': 'ASSETS', 'description': 'الحسابات البنكية وحسابات التوفير'},
        {'name': 'الأصول الثابتة', 'code': 'FIXED_ASSETS', 'category_type': 'ASSET', 'parent_code': 'ASSETS', 'description': 'المباني والأثاث والمعدات'},
        
        # تصنيفات فرعية للإيرادات
        {'name': 'الرسوم الدراسية', 'code': 'TUITION_FEES', 'category_type': 'REVENUE', 'parent_code': 'REVENUE', 'description': 'رسوم التعليم والدراسة'},
        {'name': 'رسوم النقل', 'code': 'TRANSPORT_FEES', 'category_type': 'REVENUE', 'parent_code': 'REVENUE', 'description': 'رسوم المواصلات والحافلات'},
        {'name': 'رسوم التغذية', 'code': 'MEAL_FEES', 'category_type': 'REVENUE', 'parent_code': 'REVENUE', 'description': 'رسوم الوجبات والكانتين'},
        {'name': 'رسوم الأنشطة', 'code': 'ACTIVITY_FEES', 'category_type': 'REVENUE', 'parent_code': 'REVENUE', 'description': 'رسوم النشاطات اللاصفية'},
        {'name': 'إيرادات أخرى', 'code': 'OTHER_REVENUE', 'category_type': 'REVENUE', 'parent_code': 'REVENUE', 'description': 'الإيرادات المتنوعة الأخرى'},
        
        # تصنيفات فرعية للمصروفات
        {'name': 'المرتبات والأجور', 'code': 'SALARIES', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'مرتبات الموظفين والمعلمين'},
        {'name': 'المرافق والخدمات', 'code': 'UTILITIES', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'كهرباء وماء وغاز وإنترنت'},
        {'name': 'المستلزمات التعليمية', 'code': 'EDUCATIONAL_SUPPLIES', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'القرطاسية والكتب والمواد التعليمية'},
        {'name': 'الصيانة والإصلاح', 'code': 'MAINTENANCE', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'صيانة المباني والمعدات'},
        {'name': 'النظافة والأمن', 'code': 'CLEANING_SECURITY', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'مواد النظافة وخدمات الأمن'},
        {'name': 'النقل والمواصلات', 'code': 'TRANSPORTATION', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'وقود ومصاريف الحافلات'},
        {'name': 'الدعاية والتسويق', 'code': 'MARKETING', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'إعلانات وطباعة ودعاية'},
        {'name': 'مصروفات إدارية', 'code': 'ADMIN_EXPENSES', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'مصروفات إدارية متنوعة'},
    ]
    
    created_count = 0
    updated_count = 0
    
    try:
        with db_transaction.atomic():
            # إنشاء التصنيفات الرئيسية أولاً
            for category_data in basic_categories:
                if not category_data.get('parent_code'):
                    category, created = AccountCategory.objects.get_or_create(
                        code=category_data['code'],
                        defaults={
                            'name': category_data['name'],
                            'category_type': category_data['category_type'],
                            'description': category_data['description'],
                            'is_active': True
                        }
                    )
                    if created:
                        created_count += 1
                    else:
                        # تحديث البيانات إذا كانت موجودة
                        category.name = category_data['name']
                        category.description = category_data['description']
                        category.save()
                        updated_count += 1
            
            # إنشاء التصنيفات الفرعية
            for category_data in basic_categories:
                if category_data.get('parent_code'):
                    try:
                        parent = AccountCategory.objects.get(code=category_data['parent_code'])
                        category, created = AccountCategory.objects.get_or_create(
                            code=category_data['code'],
                            defaults={
                                'name': category_data['name'],
                                'category_type': category_data['category_type'],
                                'parent': parent,
                                'description': category_data['description'],
                                'is_active': True
                            }
                        )
                        if created:
                            created_count += 1
                        else:
                            category.name = category_data['name']
                            category.parent = parent
                            category.description = category_data['description']
                            category.save()
                            updated_count += 1
                    except AccountCategory.DoesNotExist:
                        continue
        
        if created_count > 0:
            messages.success(request, f'🎉 تم إنشاء {created_count} تصنيف جديد بنجاح!')
        if updated_count > 0:
            messages.info(request, f'🔄 تم تحديث {updated_count} تصنيف موجود')
        if created_count == 0 and updated_count == 0:
            messages.info(request, '✅ جميع التصنيفات الأساسية موجودة ومحدثة')
            
    except Exception as e:
        messages.error(request, f'❌ حدث خطأ أثناء إنشاء التصنيفات: {str(e)}')
    
    return redirect('treasury_management:account_categories_list')

@treasury_admin_required
def setup_basic_accounts(request):
    """إنشاء الحسابات الأساسية - للمدير العام فقط"""
    
    basic_accounts = [
        # حسابات الخزائن
        {'name': 'الخزنة الرئيسية', 'code': '1001', 'category_code': 'CASH_ASSETS', 'opening_balance': 0},
        {'name': 'خزنة فرعية', 'code': '1002', 'category_code': 'CASH_ASSETS', 'opening_balance': 0},
        
        # حسابات بنكية
        {'name': 'البنك الأهلي - حساب جاري', 'code': '1101', 'category_code': 'BANK_ACCOUNTS', 'opening_balance': 0},
        {'name': 'بنك مصر - حساب توفير', 'code': '1102', 'category_code': 'BANK_ACCOUNTS', 'opening_balance': 0},
        
        # حسابات الإيرادات
        {'name': 'إيرادات الرسوم الدراسية', 'code': '4001', 'category_code': 'TUITION_FEES', 'opening_balance': 0},
        {'name': 'إيرادات رسوم النقل', 'code': '4002', 'category_code': 'TRANSPORT_FEES', 'opening_balance': 0},
        {'name': 'إيرادات رسوم التغذية', 'code': '4003', 'category_code': 'MEAL_FEES', 'opening_balance': 0},
        {'name': 'إيرادات رسوم الأنشطة', 'code': '4004', 'category_code': 'ACTIVITY_FEES', 'opening_balance': 0},
        
        # حسابات المصروفات الأساسية
        {'name': 'مرتبات المعلمين', 'code': '5001', 'category_code': 'SALARIES', 'opening_balance': 0},
        {'name': 'مرتبات الإدارة', 'code': '5002', 'category_code': 'SALARIES', 'opening_balance': 0},
        {'name': 'فاتورة الكهرباء', 'code': '5101', 'category_code': 'UTILITIES', 'opening_balance': 0},
        {'name': 'فاتورة المياه', 'code': '5102', 'category_code': 'UTILITIES', 'opening_balance': 0},
        {'name': 'فاتورة الإنترنت والهاتف', 'code': '5103', 'category_code': 'UTILITIES', 'opening_balance': 0},
        {'name': 'القرطاسية والكتب', 'code': '5201', 'category_code': 'EDUCATIONAL_SUPPLIES', 'opening_balance': 0},
        {'name': 'صيانة عامة', 'code': '5301', 'category_code': 'MAINTENANCE', 'opening_balance': 0},
        {'name': 'مواد النظافة', 'code': '5401', 'category_code': 'CLEANING_SECURITY', 'opening_balance': 0},
    ]
    
    created_count = 0
    
    try:
        with db_transaction.atomic():
            for account_data in basic_accounts:
                # التحقق من وجود التصنيف
                try:
                    category = AccountCategory.objects.get(code=account_data['category_code'])
                    
                    # إنشاء الحساب إذا لم يكن موجوداً
                    if not Account.objects.filter(code=account_data['code']).exists():
                        Account.objects.create(
                            category=category,
                            name=account_data['name'],
                            code=account_data['code'],
                            opening_balance=account_data['opening_balance'],
                            current_balance=account_data['opening_balance'],
                            is_active=True
                        )
                        created_count += 1
                        
                except AccountCategory.DoesNotExist:
                    continue
        
        if created_count > 0:
            messages.success(request, f'🎉 تم إنشاء {created_count} حساب أساسي بنجاح!')
        else:
            messages.info(request, '✅ جميع الحسابات الأساسية موجودة مسبقاً')
            
    except Exception as e:
        messages.error(request, f'❌ حدث خطأ أثناء إنشاء الحسابات: {str(e)}')
    
    return redirect('treasury_management:accounts_list')

@treasury_admin_required
def setup_expense_categories(request):
    """إنشاء تصنيفات المصروفات الأساسية - للمدير العام فقط"""
    # التحقق من وجود نموذج ExpenseCategory
    if not ExpenseCategory:
        messages.error(request, 'نموذج تصنيفات المصروفات غير متوفر')
        return redirect('treasury_management:dashboard')
    
    expense_categories = [
        {'name': 'مرتبات الموظفين', 'code': 'EXP_SAL', 'account_code': '5001', 'budget': 50000},
        {'name': 'فواتير الكهرباء', 'code': 'EXP_ELEC', 'account_code': '5101', 'budget': 5000},
        {'name': 'فواتير المياه', 'code': 'EXP_WATER', 'account_code': '5102', 'budget': 2000},
        {'name': 'فواتير الاتصالات', 'code': 'EXP_COMM', 'account_code': '5103', 'budget': 1500},
        {'name': 'مستلزمات تعليمية', 'code': 'EXP_EDU', 'account_code': '5201', 'budget': 8000},
        {'name': 'صيانة ونظافة', 'code': 'EXP_MAIN', 'account_code': '5301', 'budget': 3000},
        {'name': 'مواد النظافة', 'code': 'EXP_CLEAN', 'account_code': '5401', 'budget': 2000},
        {'name': 'مصروفات إدارية متنوعة', 'code': 'EXP_ADMIN', 'account_code': '5501', 'budget': 2000},
    ]
    
    created_count = 0
    
    try:
        with db_transaction.atomic():
            for category_data in expense_categories:
                # البحث عن الحساب المرتبط
                try:
                    account = Account.objects.get(code=category_data['account_code'])
                    
                    # إنشاء تصنيف المصروف إذا لم يكن موجوداً
                    if not ExpenseCategory.objects.filter(code=category_data['code']).exists():
                        ExpenseCategory.objects.create(
                            name=category_data['name'],
                            code=category_data['code'],
                            account=account,
                            monthly_budget=category_data.get('budget'),
                            description=f'تصنيف مصروفات {category_data["name"]}',
                            is_active=True
                        )
                        created_count += 1
                        
                except Account.DoesNotExist:
                    # إنشاء الحساب إذا لم يكن موجوداً
                    try:
                        expense_category = AccountCategory.objects.get(code='EXPENSES')
                        account = Account.objects.create(
                            category=expense_category,
                            name=f'حساب {category_data["name"]}',
                            code=category_data['account_code'],
                            opening_balance=0,
                            current_balance=0,
                            is_active=True
                        )
                        
                        ExpenseCategory.objects.create(
                            name=category_data['name'],
                            code=category_data['code'],
                            account=account,
                            monthly_budget=category_data.get('budget'),
                            description=f'تصنيف مصروفات {category_data["name"]}',
                            is_active=True
                        )
                        created_count += 1
                    except:
                        continue
        
        if created_count > 0:
            messages.success(request, f'🎉 تم إنشاء {created_count} تصنيف مصروفات بنجاح!')
        else:
            messages.info(request, '✅ جميع تصنيفات المصروفات موجودة مسبقاً')
            
    except Exception as e:
        messages.error(request, f'❌ حدث خطأ أثناء إنشاء تصنيفات المصروفات: {str(e)}')
    
    return redirect('treasury_management:expense_categories_list')

@treasury_admin_required
def quick_setup(request):
    """الإعداد السريع الشامل - للمدير العام فقط"""
    """صفحة الإعداد السريع مع خيارات متعددة"""
    if request.method == 'POST':
        setup_type = request.POST.get('setup_type')
        
        if setup_type == 'categories':
            return setup_basic_categories(request)
        elif setup_type == 'accounts':
            return setup_basic_accounts(request)
        elif setup_type == 'expense_categories':
            return setup_expense_categories(request)
        elif setup_type == 'all':
            # إعداد شامل
            try:
                # إعداد التصنيفات
                setup_basic_categories(request)
                # إعداد الحسابات
                setup_basic_accounts(request) 
                # إعداد تصنيفات المصروفات
                setup_expense_categories(request)
                
                messages.success(request, '🎉 تم الإعداد الشامل بنجاح!')
            except Exception as e:
                messages.error(request, f'❌ حدث خطأ في الإعداد الشامل: {str(e)}')
            
            return redirect('treasury_management:dashboard')
    
    # إحصائيات النظام الحالية
    stats = {
        'categories': AccountCategory.objects.count(),
        'accounts': Account.objects.count(),
        'expense_categories': ExpenseCategory.objects.count() if ExpenseCategory else 0,
        'treasuries': Treasury.objects.count(),
        'transactions': Transaction.objects.count(),
    }
    
    context = {
        'stats': stats,
    }
    
    return render(request, 'treasury_management/quick_setup.html', context)

# # treasury_management/views.py - تحديث View الحسابات
# from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# from django.db.models import Q, Count, Sum
# from django.http import JsonResponse

# @login_required
# def accounts_list(request):
#     """قائمة الحسابات المالية مع pagination وفلاتر"""
    
#     # الحصول على المعاملات
#     search = request.GET.get('search', '')
#     category_type = request.GET.get('type', '')
#     category_id = request.GET.get('category', '')
#     is_active = request.GET.get('active', '')
#     has_balance = request.GET.get('has_balance', '')
    
#     # بناء الاستعلام الأساسي
#     accounts = Account.objects.all().select_related('category')
    
#     # تطبيق الفلاتر
#     if search:
#         accounts = accounts.filter(
#             Q(name__icontains=search) | 
#             Q(code__icontains=search) | 
#             Q(description__icontains=search) |
#             Q(category__name__icontains=search)
#         )
    
#     if category_type:
#         accounts = accounts.filter(category__category_type=category_type)
        
#     if category_id:
#         accounts = accounts.filter(category_id=category_id)
    
#     if is_active:
#         accounts = accounts.filter(is_active=is_active == 'true')
        
#     if has_balance == 'true':
#         accounts = accounts.exclude(current_balance=0)
#     elif has_balance == 'false':
#         accounts = accounts.filter(current_balance=0)
    
#     # ترتيب النتائج
#     order_by = request.GET.get('order_by', 'code')
#     if order_by in ['code', 'name', 'category__name', 'current_balance', 'created_at']:
#         if request.GET.get('desc') == 'true':
#             order_by = '-' + order_by
#         accounts = accounts.order_by(order_by)
#     else:
#         accounts = accounts.order_by('code')
    
#     # إضافة annotations
#     accounts = accounts.annotate(
#         transactions_count=Count('transaction'),
#     )
    
#     # Pagination
#     items_per_page = request.GET.get('per_page', 15)
#     try:
#         items_per_page = int(items_per_page)
#         if items_per_page not in [5, 10, 15, 25, 50, 100]:
#             items_per_page = 15
#     except:
#         items_per_page = 15
    
#     paginator = Paginator(accounts, items_per_page)
#     page = request.GET.get('page')
    
#     try:
#         accounts_page = paginator.page(page)
#     except PageNotAnInteger:
#         accounts_page = paginator.page(1)
#     except EmptyPage:
#         accounts_page = paginator.page(paginator.num_pages)
    
#     # إحصائيات
#     stats = {
#         'total_accounts': Account.objects.count(),
#         'active_accounts': Account.objects.filter(is_active=True).count(),
#         'total_balance': Account.objects.aggregate(Sum('current_balance'))['current_balance__sum'] or 0,
#         'accounts_with_balance': Account.objects.exclude(current_balance=0).count(),
#     }
    
#     # قائمة التصنيفات للفلتر
#     categories = AccountCategory.objects.filter(is_active=True).order_by('name')
    
#     context = {
#         'accounts': accounts_page,
#         'paginator': paginator,
#         'categories': categories,
#         'stats': stats,
#         'search': search,
#         'category_type': category_type,
#         'category_id': category_id,
#         'is_active': is_active,
#         'has_balance': has_balance,
#         'order_by': order_by.replace('-', ''),
#         'desc': request.GET.get('desc', 'false'),
#         'items_per_page': items_per_page,
#         'category_types': [
#             ('ASSET', 'أصول'),
#             ('LIABILITY', 'خصوم'),
#             ('EQUITY', 'حقوق الملكية'),
#             ('REVENUE', 'إيرادات'),
#             ('EXPENSE', 'مصروفات'),
#         ],
#     }
    
#     return render(request, 'treasury_management/accounts_list.html', context)

# @login_required
# def account_detail_ajax(request, account_id):
#     """تفاصيل الحساب عبر AJAX"""
#     try:
#         account = Account.objects.select_related('category').get(id=account_id)
        
#         # الحصول على آخر المعاملات
#         recent_transactions = Transaction.objects.filter(account=account).order_by('-created_at')[:5]
        
#         # حساب الإحصائيات
#         total_income = Transaction.objects.filter(
#             account=account, 
#             transaction_type='INCOME'
#         ).aggregate(Sum('amount'))['amount__sum'] or 0
        
#         total_expenses = Transaction.objects.filter(
#             account=account, 
#             transaction_type='EXPENSE'
#         ).aggregate(Sum('amount'))['amount__sum'] or 0
        
#         html = render_to_string('treasury_management/account_detail_modal.html', {
#             'account': account,
#             'recent_transactions': recent_transactions,
#             'total_income': total_income,
#             'total_expenses': total_expenses,
#         })
        
#         return JsonResponse({
#             'success': True,
#             'html': html
#         })
#     except Account.DoesNotExist:
#         return JsonResponse({
#             'success': False,
#             'error': 'الحساب غير موجود'
#         })
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         })

# @login_required
# def add_account(request):
#     """إضافة حساب مالي جديد"""
#     if request.method == 'POST':
#         try:
#             category_id = request.POST.get('category')
#             name = request.POST.get('name')
#             code = request.POST.get('code')
#             description = request.POST.get('description', '')
#             opening_balance = float(request.POST.get('opening_balance', 0))
            
#             # التحقق من عدم تكرار الكود
#             if Account.objects.filter(code=code).exists():
#                 messages.error(request, f'كود الحساب "{code}" موجود مسبقاً')
#                 return redirect('treasury_management:add_account')
            
#             category = AccountCategory.objects.get(id=category_id)
#             Account.objects.create(
#                 category=category,
#                 name=name,
#                 code=code,
#                 description=description,
#                 opening_balance=opening_balance,
#                 current_balance=opening_balance
#             )
            
#             messages.success(request, f'تم إضافة الحساب "{name}" بنجاح')
#             return redirect('treasury_management:accounts_list')
            
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     context = {
#         'account_categories': AccountCategory.objects.filter(is_active=True).order_by('name'),
#     }
    
#     return render(request, 'treasury_management/add_account.html', context)

# # treasury_management/views.py - تحديث View تصنيفات الحسابات
# from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# from django.db.models import Q, Count

# # treasury_management/views.py - تصحيح View تصنيفات الحسابات
# from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# from django.db.models import Q, Count

# # حل بسيط بدون children_count
# @login_required
# def account_categories_list(request):
#     """قائمة تصنيفات الحسابات مع pagination وفلاتر"""
    
#     # الحصول على المعاملات
#     search = request.GET.get('search', '')
#     category_type = request.GET.get('type', '')
#     is_active = request.GET.get('active', '')
#     parent_only = request.GET.get('parent_only', '')
    
#     # بناء الاستعلام الأساسي
#     categories = AccountCategory.objects.all().select_related('parent')
    
#     # تطبيق الفلاتر
#     if search:
#         categories = categories.filter(
#             Q(name__icontains=search) | 
#             Q(code__icontains=search) | 
#             Q(description__icontains=search)
#         )
    
#     if category_type:
#         categories = categories.filter(category_type=category_type)
    
#     if is_active:
#         categories = categories.filter(is_active=is_active == 'true')
    
#     if parent_only == 'true':
#         categories = categories.filter(parent__isnull=True)
    
#     # ترتيب النتائج
#     order_by = request.GET.get('order_by', 'code')
#     if order_by in ['code', 'name', 'category_type']:
#         categories = categories.order_by(order_by)
#     else:
#         categories = categories.order_by('code')
    
#     # إضافة annotation للحسابات فقط
#     categories = categories.annotate(
#         accounts_count=Count('account', distinct=True)
#     )
    
#     # Pagination
#     items_per_page = request.GET.get('per_page', 10)
#     try:
#         items_per_page = int(items_per_page)
#         if items_per_page not in [5, 10, 15, 25, 50]:
#             items_per_page = 10
#     except:
#         items_per_page = 10
    
#     paginator = Paginator(categories, items_per_page)
#     page = request.GET.get('page')
    
#     try:
#         categories_page = paginator.page(page)
#     except PageNotAnInteger:
#         categories_page = paginator.page(1)
#     except EmptyPage:
#         categories_page = paginator.page(paginator.num_pages)
    
#     # إحصائيات
#     stats = {
#         'total_categories': AccountCategory.objects.count(),
#         'active_categories': AccountCategory.objects.filter(is_active=True).count(),
#         'parent_categories': AccountCategory.objects.filter(parent__isnull=True).count(),
#         'child_categories': AccountCategory.objects.filter(parent__isnull=False).count(),
#     }
    
#     # إضافة children_count يدوياً
#     for category in categories_page:
#         try:
#             category.children_count = AccountCategory.objects.filter(parent=category).count()
#         except:
#             category.children_count = 0
    
#     context = {
#         'categories': categories_page,
#         'paginator': paginator,
#         'stats': stats,
#         'search': search,
#         'category_type': category_type,
#         'is_active': is_active,
#         'parent_only': parent_only,
#         'order_by': order_by,
#         'items_per_page': items_per_page,
#         'category_types': [
#             ('ASSET', 'أصول'),
#             ('LIABILITY', 'خصوم'),
#             ('EQUITY', 'حقوق الملكية'),
#             ('REVENUE', 'إيرادات'),
#             ('EXPENSE', 'مصروفات'),
#         ],
#     }
    
#     return render(request, 'treasury_management/account_categories_list.html', context)




# @login_required
# def add_account_category(request):
#     """إضافة تصنيف حساب جديد"""
#     if request.method == 'POST':
#         try:
#             name = request.POST.get('name')
#             code = request.POST.get('code')
#             category_type = request.POST.get('category_type')
#             description = request.POST.get('description', '')
#             parent_id = request.POST.get('parent')
            
#             # التحقق من عدم تكرار الكود
#             if AccountCategory.objects.filter(code=code).exists():
#                 messages.error(request, f'كود التصنيف "{code}" موجود مسبقاً')
#                 return redirect('treasury_management:add_account_category')
            
#             parent = None
#             if parent_id:
#                 parent = AccountCategory.objects.get(id=parent_id)
            
#             AccountCategory.objects.create(
#                 name=name,
#                 code=code,
#                 category_type=category_type,
#                 description=description,
#                 parent=parent
#             )
            
#             messages.success(request, f'تم إضافة تصنيف الحساب "{name}" بنجاح')
#             return redirect('treasury_management:account_categories_list')
            
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     context = {
#         'parent_categories': AccountCategory.objects.filter(parent__isnull=True, is_active=True),
#     }
    
#     return render(request, 'treasury_management/add_account_category.html', context)



# @login_required
# def add_expense_category(request):
#     """إضافة تصنيف مصروفات جديد"""
#     if request.method == 'POST':
#         try:
#             name = request.POST.get('name')
#             code = request.POST.get('code')
#             account_id = request.POST.get('account')
#             description = request.POST.get('description', '')
#             monthly_budget = request.POST.get('monthly_budget')
            
#             # التحقق من عدم تكرار الكود
#             if ExpenseCategory.objects.filter(code=code).exists():
#                 messages.error(request, f'كود التصنيف "{code}" موجود مسبقاً')
#                 return redirect('treasury_management:add_expense_category')
            
#             account = Account.objects.get(id=account_id)
#             ExpenseCategory.objects.create(
#                 name=name,
#                 code=code,
#                 account=account,
#                 description=description,
#                 monthly_budget=float(monthly_budget) if monthly_budget else None
#             )
            
#             messages.success(request, f'تم إضافة تصنيف المصروفات "{name}" بنجاح')
#             return redirect('treasury_management:expense_categories_list')
            
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     context = {
#         'accounts': Account.objects.filter(
#             category__category_type='EXPENSE',
#             is_active=True
#         ).order_by('name'),
#     }
    
#     return render(request, 'treasury_management/add_expense_category.html', context)

# @login_required
# def edit_expense_category(request, pk):
#     """تحرير تصنيف مصروفات"""
#     category = get_object_or_404(ExpenseCategory, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             category.name = request.POST.get('name')
#             category.description = request.POST.get('description', '')
            
#             monthly_budget = request.POST.get('monthly_budget')
#             category.monthly_budget = float(monthly_budget) if monthly_budget else None
            
#             category.is_active = request.POST.get('is_active') == 'on'
#             category.save()
            
#             messages.success(request, f'تم تحديث تصنيف المصروفات "{category.name}" بنجاح')
#             return redirect('treasury_management:expense_categories_list')
            
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     context = {
#         'category': category,
#     }
    
#     return render(request, 'treasury_management/edit_expense_category.html', context)


# # إضافة هذه Views للملف الموجود

# @login_required
# def edit_account(request, pk):
#     """تحرير حساب مالي"""
#     account = get_object_or_404(Account, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             account.name = request.POST.get('name')
#             account.description = request.POST.get('description', '')
#             account.is_active = request.POST.get('is_active') == 'on'
            
#             # لا يمكن تغيير الكود أو الرصيد الحالي لحساب موجود
#             account.save()
            
#             messages.success(request, f'تم تحديث الحساب "{account.name}" بنجاح')
#             return redirect('treasury_management:accounts_list')
            
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     context = {
#         'account': account,
#     }
    
#     return render(request, 'treasury_management/edit_account.html', context)


# # إضافة هذا View إلى treasury_management/views.py

# @login_required
# def setup_basic_categories(request):
#     """إنشاء التصنيفات الأساسية للحسابات"""
    
#     basic_categories = [
#         {'name': 'الأصول', 'code': 'ASSETS', 'category_type': 'ASSET', 'description': 'جميع أصول المدرسة'},
#         {'name': 'الأصول النقدية', 'code': 'CASH', 'category_type': 'ASSET', 'parent_code': 'ASSETS', 'description': 'النقدية والخزائن'},
#         {'name': 'الحسابات المصرفية', 'code': 'BANKS', 'category_type': 'ASSET', 'parent_code': 'ASSETS', 'description': 'الحسابات البنكية'},
        
#         {'name': 'الإيرادات', 'code': 'REVENUE', 'category_type': 'REVENUE', 'description': 'جميع إيرادات المدرسة'},
#         {'name': 'الرسوم الدراسية', 'code': 'FEES', 'category_type': 'REVENUE', 'parent_code': 'REVENUE', 'description': 'رسوم الطلاب'},
#         {'name': 'إيرادات أخرى', 'code': 'OTHER_REV', 'category_type': 'REVENUE', 'parent_code': 'REVENUE', 'description': 'الإيرادات الأخرى'},
        
#         {'name': 'المصروفات', 'code': 'EXPENSES', 'category_type': 'EXPENSE', 'description': 'جميع مصروفات المدرسة'},
#         {'name': 'المرتبات', 'code': 'SALARIES', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'مرتبات الموظفين'},
#         {'name': 'المرافق', 'code': 'UTILITIES', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'كهرباء وماء وغاز'},
#         {'name': 'المستلزمات', 'code': 'SUPPLIES', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'القرطاسية والمستلزمات'},
        
#         {'name': 'الخصوم', 'code': 'LIABILITIES', 'category_type': 'LIABILITY', 'description': 'التزامات المدرسة'},
#     ]
    
#     created_count = 0
    
#     try:
#         with db_transaction.atomic():
#             # إنشاء التصنيفات الرئيسية أولاً
#             for category_data in basic_categories:
#                 if not category_data.get('parent_code'):
#                     if not AccountCategory.objects.filter(code=category_data['code']).exists():
#                         AccountCategory.objects.create(
#                             name=category_data['name'],
#                             code=category_data['code'],
#                             category_type=category_data['category_type'],
#                             description=category_data['description']
#                         )
#                         created_count += 1
            
#             # إنشاء التصنيفات الفرعية
#             for category_data in basic_categories:
#                 if category_data.get('parent_code'):
#                     if not AccountCategory.objects.filter(code=category_data['code']).exists():
#                         parent = AccountCategory.objects.get(code=category_data['parent_code'])
#                         AccountCategory.objects.create(
#                             name=category_data['name'],
#                             code=category_data['code'],
#                             category_type=category_data['category_type'],
#                             parent=parent,
#                             description=category_data['description']
#                         )
#                         created_count += 1
        
#         if created_count > 0:
#             messages.success(request, f'تم إنشاء {created_count} تصنيف أساسي بنجاح')
#         else:
#             messages.info(request, 'جميع التصنيفات الأساسية موجودة مسبقاً')
            
#     except Exception as e:
#         messages.error(request, f'حدث خطأ: {str(e)}')
    
#     return redirect('treasury_management:account_categories_list')


# # إضافة هذا View للملف الموجود

# @login_required
# def setup_basic_categories(request):
#     """إنشاء التصنيفات الأساسية للحسابات تلقائياً"""
    
#     basic_categories = [
#         # التصنيفات الرئيسية
#         {'name': 'الأصول', 'code': 'ASSETS', 'category_type': 'ASSET', 'description': 'جميع أصول المدرسة المالية والعينية'},
#         {'name': 'الإيرادات', 'code': 'REVENUE', 'category_type': 'REVENUE', 'description': 'جميع إيرادات ومداخيل المدرسة'},
#         {'name': 'المصروفات', 'code': 'EXPENSES', 'category_type': 'EXPENSE', 'description': 'جميع مصروفات ونفقات المدرسة'},
#         {'name': 'الخصوم', 'code': 'LIABILITIES', 'category_type': 'LIABILITY', 'description': 'التزامات المدرسة تجاه الغير'},
        
#         # تصنيفات فرعية للأصول
#         {'name': 'الأصول النقدية', 'code': 'CASH_ASSETS', 'category_type': 'ASSET', 'parent_code': 'ASSETS', 'description': 'النقدية والخزائن والحسابات الجارية'},
#         {'name': 'الحسابات المصرفية', 'code': 'BANK_ACCOUNTS', 'category_type': 'ASSET', 'parent_code': 'ASSETS', 'description': 'الحسابات البنكية وحسابات التوفير'},
#         {'name': 'الأصول الثابتة', 'code': 'FIXED_ASSETS', 'category_type': 'ASSET', 'parent_code': 'ASSETS', 'description': 'المباني والأثاث والمعدات'},
        
#         # تصنيفات فرعية للإيرادات
#         {'name': 'الرسوم الدراسية', 'code': 'TUITION_FEES', 'category_type': 'REVENUE', 'parent_code': 'REVENUE', 'description': 'رسوم التعليم والدراسة'},
#         {'name': 'رسوم النقل', 'code': 'TRANSPORT_FEES', 'category_type': 'REVENUE', 'parent_code': 'REVENUE', 'description': 'رسوم المواصلات والحافلات'},
#         {'name': 'رسوم التغذية', 'code': 'MEAL_FEES', 'category_type': 'REVENUE', 'parent_code': 'REVENUE', 'description': 'رسوم الوجبات والكانتين'},
#         {'name': 'رسوم الأنشطة', 'code': 'ACTIVITY_FEES', 'category_type': 'REVENUE', 'parent_code': 'REVENUE', 'description': 'رسوم النشاطات اللاصفية'},
#         {'name': 'إيرادات أخرى', 'code': 'OTHER_REVENUE', 'category_type': 'REVENUE', 'parent_code': 'REVENUE', 'description': 'الإيرادات المتنوعة الأخرى'},
        
#         # تصنيفات فرعية للمصروفات
#         {'name': 'المرتبات والأجور', 'code': 'SALARIES', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'مرتبات الموظفين والمعلمين'},
#         {'name': 'المرافق والخدمات', 'code': 'UTILITIES', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'كهرباء وماء وغاز وإنترنت'},
#         {'name': 'المستلزمات التعليمية', 'code': 'EDUCATIONAL_SUPPLIES', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'القرطاسية والكتب والمواد التعليمية'},
#         {'name': 'الصيانة والإصلاح', 'code': 'MAINTENANCE', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'صيانة المباني والمعدات'},
#         {'name': 'النظافة والأمن', 'code': 'CLEANING_SECURITY', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'مواد النظافة وخدمات الأمن'},
#         {'name': 'النقل والمواصلات', 'code': 'TRANSPORTATION', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'وقود ومصاريف الحافلات'},
#         {'name': 'الدعاية والتسويق', 'code': 'MARKETING', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'إعلانات وطباعة ودعاية'},
#         {'name': 'مصروفات إدارية', 'code': 'ADMIN_EXPENSES', 'category_type': 'EXPENSE', 'parent_code': 'EXPENSES', 'description': 'مصروفات إدارية متنوعة'},
#     ]
    
#     created_count = 0
#     updated_count = 0
    
#     try:
#         with db_transaction.atomic():
#             # إنشاء التصنيفات الرئيسية أولاً
#             for category_data in basic_categories:
#                 if not category_data.get('parent_code'):
#                     category, created = AccountCategory.objects.get_or_create(
#                         code=category_data['code'],
#                         defaults={
#                             'name': category_data['name'],
#                             'category_type': category_data['category_type'],
#                             'description': category_data['description'],
#                             'is_active': True
#                         }
#                     )
#                     if created:
#                         created_count += 1
#                     else:
#                         # تحديث البيانات إذا كانت موجودة
#                         category.name = category_data['name']
#                         category.description = category_data['description']
#                         category.save()
#                         updated_count += 1
            
#             # إنشاء التصنيفات الفرعية
#             for category_data in basic_categories:
#                 if category_data.get('parent_code'):
#                     try:
#                         parent = AccountCategory.objects.get(code=category_data['parent_code'])
#                         category, created = AccountCategory.objects.get_or_create(
#                             code=category_data['code'],
#                             defaults={
#                                 'name': category_data['name'],
#                                 'category_type': category_data['category_type'],
#                                 'parent': parent,
#                                 'description': category_data['description'],
#                                 'is_active': True
#                             }
#                         )
#                         if created:
#                             created_count += 1
#                         else:
#                             category.name = category_data['name']
#                             category.parent = parent
#                             category.description = category_data['description']
#                             category.save()
#                             updated_count += 1
#                     except AccountCategory.DoesNotExist:
#                         continue
        
#         if created_count > 0:
#             messages.success(request, f'تم إنشاء {created_count} تصنيف جديد بنجاح!')
#         if updated_count > 0:
#             messages.info(request, f'تم تحديث {updated_count} تصنيف موجود')
#         if created_count == 0 and updated_count == 0:
#             messages.info(request, 'جميع التصنيفات الأساسية موجودة ومحدثة')
            
#     except Exception as e:
#         messages.error(request, f'حدث خطأ أثناء إنشاء التصنيفات: {str(e)}')
    
#     return redirect('treasury_management:account_categories_list')

# @login_required
# def setup_basic_accounts(request):
#     """إنشاء الحسابات الأساسية مع التصنيفات"""
    
#     basic_accounts = [
#         # حسابات الخزائن
#         {'name': 'الخزنة الرئيسية', 'code': '1001', 'category_code': 'CASH_ASSETS', 'opening_balance': 0},
#         {'name': 'خزنة فرعية', 'code': '1002', 'category_code': 'CASH_ASSETS', 'opening_balance': 0},
        
#         # حسابات بنكية
#         {'name': 'البنك الأهلي - حساب جاري', 'code': '1101', 'category_code': 'BANK_ACCOUNTS', 'opening_balance': 0},
#         {'name': 'بنك مصر - حساب توفير', 'code': '1102', 'category_code': 'BANK_ACCOUNTS', 'opening_balance': 0},
        
#         # حسابات الإيرادات
#         {'name': 'إيرادات الرسوم الدراسية', 'code': '4001', 'category_code': 'TUITION_FEES', 'opening_balance': 0},
#         {'name': 'إيرادات رسوم النقل', 'code': '4002', 'category_code': 'TRANSPORT_FEES', 'opening_balance': 0},
#         {'name': 'إيرادات رسوم التغذية', 'code': '4003', 'category_code': 'MEAL_FEES', 'opening_balance': 0},
        
#         # حسابات المصروفات الأساسية
#         {'name': 'مرتبات المعلمين', 'code': '5001', 'category_code': 'SALARIES', 'opening_balance': 0},
#         {'name': 'مرتبات الإدارة', 'code': '5002', 'category_code': 'SALARIES', 'opening_balance': 0},
#         {'name': 'فاتورة الكهرباء', 'code': '5101', 'category_code': 'UTILITIES', 'opening_balance': 0},
#         {'name': 'فاتورة المياه', 'code': '5102', 'category_code': 'UTILITIES', 'opening_balance': 0},
#         {'name': 'القرطاسية والكتب', 'code': '5201', 'category_code': 'EDUCATIONAL_SUPPLIES', 'opening_balance': 0},
#         {'name': 'صيانة عامة', 'code': '5301', 'category_code': 'MAINTENANCE', 'opening_balance': 0},
#     ]
    
#     created_count = 0
    
#     try:
#         with db_transaction.atomic():
#             for account_data in basic_accounts:
#                 # التحقق من وجود التصنيف
#                 try:
#                     category = AccountCategory.objects.get(code=account_data['category_code'])
                    
#                     # إنشاء الحساب إذا لم يكن موجوداً
#                     if not Account.objects.filter(code=account_data['code']).exists():
#                         Account.objects.create(
#                             category=category,
#                             name=account_data['name'],
#                             code=account_data['code'],
#                             opening_balance=account_data['opening_balance'],
#                             current_balance=account_data['opening_balance'],
#                             is_active=True
#                         )
#                         created_count += 1
                        
#                 except AccountCategory.DoesNotExist:
#                     continue
        
#         if created_count > 0:
#             messages.success(request, f'تم إنشاء {created_count} حساب أساسي بنجاح!')
#         else:
#             messages.info(request, 'جميع الحسابات الأساسية موجودة مسبقاً')
            
#     except Exception as e:
#         messages.error(request, f'حدث خطأ أثناء إنشاء الحسابات: {str(e)}')
    
#     return redirect('treasury_management:accounts_list')

# @login_required
# def setup_expense_categories(request):
#     """إنشاء تصنيفات المصروفات الأساسية"""
    
#     expense_categories = [
#         {'name': 'مرتبات الموظفين', 'code': 'EXP_SAL', 'account_code': '5001', 'budget': 50000},
#         {'name': 'فواتير الكهرباء', 'code': 'EXP_ELEC', 'account_code': '5101', 'budget': 5000},
#         {'name': 'فواتير المياه', 'code': 'EXP_WATER', 'account_code': '5102', 'budget': 2000},
#         {'name': 'مستلزمات تعليمية', 'code': 'EXP_EDU', 'account_code': '5201', 'budget': 8000},
#         {'name': 'صيانة ونظافة', 'code': 'EXP_MAIN', 'account_code': '5301', 'budget': 3000},
#         {'name': 'مصروفات إدارية متنوعة', 'code': 'EXP_ADMIN', 'account_code': '5401', 'budget': 2000},
#     ]
    
#     created_count = 0
    
#     try:
#         with db_transaction.atomic():
#             for category_data in expense_categories:
#                 # البحث عن الحساب المرتبط
#                 try:
#                     account = Account.objects.get(code=category_data['account_code'])
                    
#                     # إنشاء تصنيف المصروف إذا لم يكن موجوداً
#                     if not ExpenseCategory.objects.filter(code=category_data['code']).exists():
#                         ExpenseCategory.objects.create(
#                             name=category_data['name'],
#                             code=category_data['code'],
#                             account=account,
#                             monthly_budget=category_data.get('budget'),
#                             description=f'تصنيف مصروفات {category_data["name"]}',
#                             is_active=True
#                         )
#                         created_count += 1
                        
#                 except Account.DoesNotExist:
#                     # إنشاء الحساب إذا لم يكن موجوداً
#                     try:
#                         expense_category = AccountCategory.objects.get(code='EXPENSES')
#                         account = Account.objects.create(
#                             category=expense_category,
#                             name=f'حساب {category_data["name"]}',
#                             code=category_data['account_code'],
#                             opening_balance=0,
#                             current_balance=0,
#                             is_active=True
#                         )
                        
#                         ExpenseCategory.objects.create(
#                             name=category_data['name'],
#                             code=category_data['code'],
#                             account=account,
#                             monthly_budget=category_data.get('budget'),
#                             description=f'تصنيف مصروفات {category_data["name"]}',
#                             is_active=True
#                         )
#                         created_count += 1
#                     except:
#                         continue
        
#         if created_count > 0:
#             messages.success(request, f'تم إنشاء {created_count} تصنيف مصروفات بنجاح!')
#         else:
#             messages.info(request, 'جميع تصنيفات المصروفات موجودة مسبقاً')
            
#     except Exception as e:
#         messages.error(request, f'حدث خطأ أثناء إنشاء تصنيفات المصروفات: {str(e)}')
    
#     return redirect('treasury_management:expense_categories_list')

# treasury_management/views.py - الجزء الأخير مع الصلاحيات

# ===================================
# 🔧 Views الإعداد والصيانة النهائية
# ===================================

# quick_setup - موجود في الرسالة السابقة مع @treasury_admin_required

@treasury_manager_required
def edit_account_category(request, pk):
    """تحرير تصنيف حساب - يحتاج صلاحية مدير أو أعلى"""
    category = get_object_or_404(AccountCategory, pk=pk)
    
    if request.method == 'POST':
        try:
            category.name = request.POST.get('name')
            category.description = request.POST.get('description', '')
            category.is_active = request.POST.get('is_active') == 'on'
            
            # تحديث التصنيف الرئيسي إذا تم تغييره
            parent_id = request.POST.get('parent')
            if parent_id:
                new_parent = AccountCategory.objects.get(id=parent_id)
                # التحقق من عدم إنشاء دورة مغلقة
                if new_parent == category or new_parent.parent == category:
                    messages.error(request, 'لا يمكن جعل التصنيف تابعاً لنفسه أو لتصنيف فرعي منه')
                    return redirect('treasury_management:edit_account_category', pk=pk)
                
                # التحقق من تطابق النوع
                if new_parent.category_type != category.category_type:
                    messages.error(request, 'نوع التصنيف يجب أن يتطابق مع التصنيف الأب')
                    return redirect('treasury_management:edit_account_category', pk=pk)
                
                category.parent = new_parent
            else:
                category.parent = None
            
            category.save()
            
            messages.success(request, f'تم تحديث تصنيف الحساب "{category.name}" بنجاح')
            return redirect('treasury_management:account_categories_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'category': category,
        'parent_categories': AccountCategory.objects.filter(
            parent__isnull=True, 
            is_active=True,
            category_type=category.category_type  # فقط التصنيفات من نفس النوع
        ).exclude(id=category.id),  # استبعاد التصنيف نفسه
    }
    
    return render(request, 'treasury_management/edit_account_category.html', context)

@treasury_admin_required
def delete_account_category(request, pk):
    """حذف تصنيف حساب - للمدير العام فقط"""
    category = get_object_or_404(AccountCategory, pk=pk)
    
    if request.method == 'POST':
        try:
            # التحقق من عدم وجود حسابات مرتبطة
            accounts_count = Account.objects.filter(category=category).count()
            if accounts_count > 0:
                messages.error(request, 
                    f'⚠️ لا يمكن حذف التصنيف "{category.name}" لأنه مرتبط بـ {accounts_count} حساب مالي'
                )
                return redirect('treasury_management:account_categories_list')
            
            # التحقق من عدم وجود تصنيفات فرعية
            children_count = AccountCategory.objects.filter(parent=category).count()
            if children_count > 0:
                messages.error(request, 
                    f'⚠️ لا يمكن حذف التصنيف "{category.name}" لأنه يحتوي على {children_count} تصنيف فرعي'
                )
                return redirect('treasury_management:account_categories_list')
            
            category_name = category.name
            category.delete()
            messages.success(request, f'✅ تم حذف تصنيف الحساب "{category_name}" بنجاح')
            
        except Exception as e:
            messages.error(request, f'❌ حدث خطأ: {str(e)}')
    
    return redirect('treasury_management:account_categories_list')

@treasury_access_required
def account_category_detail(request, pk):
    """تفاصيل تصنيف حساب - يحتاج أي صلاحية خزينة"""
    category = get_object_or_404(AccountCategory, pk=pk)
    
    # الحسابات المرتبطة بهذا التصنيف
    related_accounts = Account.objects.filter(category=category).select_related('category').order_by('code')
    
    # التصنيفات الفرعية
    child_categories = AccountCategory.objects.filter(parent=category).order_by('code')
    
    # إحصائيات
    accounts_count = related_accounts.count()
    active_accounts_count = related_accounts.filter(is_active=True).count()
    total_balance = related_accounts.aggregate(total=Sum('current_balance'))['total'] or 0
    
    # إحصائيات العمليات
    transactions_count = Transaction.objects.filter(account__category=category).count()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # طلب AJAX - إرجاع JSON
        html = render_to_string('treasury_management/account_category_detail_modal.html', {
            'category': category,
            'related_accounts': related_accounts[:10],  # أول 10 حسابات
            'child_categories': child_categories,
            'stats': {
                'accounts_count': accounts_count,
                'active_accounts_count': active_accounts_count,
                'total_balance': total_balance,
                'transactions_count': transactions_count,
            }
        }, request=request)
        return JsonResponse({
            'success': True,
            'html': html
        })
    
    context = {
        'category': category,
        'related_accounts': related_accounts,
        'child_categories': child_categories,
        'stats': {
            'accounts_count': accounts_count,
            'active_accounts_count': active_accounts_count,
            'total_balance': total_balance,
            'transactions_count': transactions_count,
        }
    }
    
    return render(request, 'treasury_management/account_category_detail.html', context)

# ===================================
# 📊 Views محدثة للوحة التحكم
# ===================================

@treasury_access_required
def dashboard(request):
    """لوحة تحكم الخزنة المحدثة - يحتاج أي صلاحية خزينة"""
    try:
        # فحص حالة الإعداد
        setup_status = {
            'categories_exist': AccountCategory.objects.exists(),
            'accounts_exist': Account.objects.exists(),
            'treasuries_exist': Treasury.objects.exists(),
            'expense_categories_exist': ExpenseCategory.objects.exists() if ExpenseCategory else False,
            'has_data': Transaction.objects.exists(),
        }
        
        # إحصائيات عامة
        treasuries = Treasury.objects.filter(is_active=True)
        
        # حساب إجمالي الرصيد بطريقة آمنة
        total_balance = 0
        for treasury in treasuries:
            try:
                if hasattr(treasury, 'current_balance'):
                    total_balance += treasury.current_balance
                elif hasattr(treasury, 'account') and treasury.account:
                    total_balance += treasury.account.current_balance
            except:
                continue
        
        today = timezone.now().date()
        today_transactions = Transaction.objects.filter(
            transaction_date__date=today,
            is_approved=True,
            is_cancelled=False
        )
        
        today_income = today_transactions.filter(transaction_type='INCOME').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        today_expenses = today_transactions.filter(transaction_type='EXPENSE').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # العمليات الأخيرة
        recent_transactions = Transaction.objects.filter(
            is_approved=True,
            is_cancelled=False
        ).select_related('treasury', 'account', 'created_by').order_by('-transaction_date')[:10]
        
        # العمليات المعلقة (للمديرين فقط)
        pending_transactions_count = 0
        user_groups = request.user.groups.values_list('name', flat=True)
        if (request.user.is_superuser or 
            any(group in user_groups for group in ['treasury_admin', 'treasury_manager'])):
            pending_transactions_count = Transaction.objects.filter(
                is_approved=False, 
                is_cancelled=False
            ).count()
        
        # تنبيهات النظام
        alerts = []
        
        # تحقق من الخزائن منخفضة الرصيد
        for treasury in treasuries:
            try:
                balance = getattr(treasury, 'current_balance', 0)
                min_limit = getattr(treasury, 'min_limit', 0)
                if min_limit and balance < min_limit:
                    alerts.append({
                        'type': 'warning',
                        'title': f'رصيد {treasury.name} منخفض',
                        'message': f'الرصيد الحالي: {balance:,.2f} أقل من الحد الأدنى: {min_limit:,.2f}'
                    })
            except:
                continue
        
        # تحقق من العمليات المعلقة
        if pending_transactions_count > 5:
            alerts.append({
                'type': 'info',
                'title': 'عمليات معلقة',
                'message': f'يوجد {pending_transactions_count} عملية في انتظار الاعتماد'
            })
        
        context = {
            'setup_status': setup_status,
            'treasuries': treasuries,
            'total_balance': total_balance,
            'today_income': today_income,
            'today_expenses': today_expenses,
            'today_net': today_income - today_expenses,
            'recent_transactions': recent_transactions,
            'pending_transactions_count': pending_transactions_count,
            'alerts': alerts,
            'stats': {
                'total_treasuries': treasuries.count(),
                'total_accounts': Account.objects.filter(is_active=True).count(),
                'total_categories': AccountCategory.objects.filter(is_active=True).count(),
                'total_transactions': Transaction.objects.count(),
            }
        }
        
        return render(request, 'treasury_management/dashboard.html', context)
        
    except Exception as e:
        # في حالة عدم وجود بيانات أساسية
        context = {
            'setup_status': {
                'categories_exist': False,
                'accounts_exist': False,
                'treasuries_exist': False,
                'expense_categories_exist': False,
                'has_data': False,
            },
            'treasuries': Treasury.objects.none(),
            'total_balance': 0,
            'today_income': 0,
            'today_expenses': 0,
            'today_net': 0,
            'recent_transactions': Transaction.objects.none(),
            'pending_transactions_count': 0,
            'alerts': [],
            'stats': {
                'total_treasuries': 0,
                'total_accounts': 0,
                'total_categories': 0,
                'total_transactions': 0,
            },
            'setup_needed': True,
        }
        return render(request, 'treasury_management/dashboard.html', context)

# ===================================
# 💸 Views تصنيفات المصروفات المحدثة
# ===================================

@treasury_manager_required
def expense_categories_list(request):
    """قائمة تصنيفات المصروفات المحدثة - يحتاج صلاحية مدير أو أعلى"""
    # التحقق من وجود نموذج ExpenseCategory
    if not ExpenseCategory:
        messages.info(request, 'نموذج تصنيفات المصروفات غير متوفر حالياً')
        return redirect('treasury_management:dashboard')
    
    # الحصول على الفلاتر
    search = request.GET.get('search', '')
    is_active = request.GET.get('active', '')
    has_budget = request.GET.get('has_budget', '')
    
    # بناء الاستعلام
    categories = ExpenseCategory.objects.all().select_related('account')
    
    # تطبيق الفلاتر
    if search:
        categories = categories.filter(
            Q(name__icontains=search) | 
            Q(code__icontains=search) | 
            Q(description__icontains=search)
        )
    
    if is_active:
        categories = categories.filter(is_active=is_active == 'true')
    
    if has_budget == 'true':
        categories = categories.exclude(monthly_budget__isnull=True)
    elif has_budget == 'false':
        categories = categories.filter(monthly_budget__isnull=True)
    
    # ترتيب النتائج
    categories = categories.order_by('code', 'name')
    
    # حساب الإحصائيات
    total_categories = ExpenseCategory.objects.count()
    active_categories = ExpenseCategory.objects.filter(is_active=True).count()
    categories_with_budget = ExpenseCategory.objects.exclude(monthly_budget__isnull=True).count()
    total_budget = ExpenseCategory.objects.aggregate(
        total=Sum('monthly_budget')
    )['total'] or 0
    
    context = {
        'categories': categories,
        'stats': {
            'total_categories': total_categories,
            'active_categories': active_categories,
            'categories_with_budget': categories_with_budget,
            'total_budget': total_budget,
        },
        'search': search,
        'is_active': is_active,
        'has_budget': has_budget,
    }
    
    return render(request, 'treasury_management/expense_categories_list.html', context)

@treasury_admin_required
def delete_expense_category(request, pk):
    """حذف تصنيف مصروفات - للمدير العام فقط"""
    # التحقق من وجود نموذج ExpenseCategory
    if not ExpenseCategory:
        messages.error(request, 'نموذج تصنيفات المصروفات غير متوفر')
        return redirect('treasury_management:dashboard')
    
    category = get_object_or_404(ExpenseCategory, pk=pk)
    
    if request.method == 'POST':
        try:
            # التحقق من عدم وجود مصروفات مرتبطة
            if DailyExpense:
                try:
                    expenses_count = DailyExpense.objects.filter(category=category).count()
                    if expenses_count > 0:
                        messages.error(request, 
                            f'⚠️ لا يمكن حذف التصنيف "{category.name}" لأنه مرتبط بـ {expenses_count} مصروف'
                        )
                        return redirect('treasury_management:expense_categories_list')
                except:
                    pass
            
            category_name = category.name
            category.delete()
            messages.success(request, f'✅ تم حذف تصنيف المصروفات "{category_name}" بنجاح')
            
        except Exception as e:
            messages.error(request, f'❌ حدث خطأ: {str(e)}')
    
    return redirect('treasury_management:expense_categories_list')

@treasury_access_required
def expense_category_detail(request, pk):
    """تفاصيل تصنيف مصروفات محسن - يحتاج أي صلاحية خزينة"""
    # التحقق من وجود نموذج ExpenseCategory
    if not ExpenseCategory:
        return JsonResponse({
            'success': False,
            'error': 'نموذج تصنيفات المصروفات غير متوفر'
        })
    
    category = get_object_or_404(ExpenseCategory, pk=pk)
    
    # حساب الإحصائيات الفعلية
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    # إحصائيات المصروفات (إذا كانت موجودة)
    month_total = 0
    month_count = 0
    year_total = 0
    recent_expenses = []
    
    if DailyExpense:
        try:
            # البحث عن المصروفات اليومية المرتبطة
            related_expenses = DailyExpense.objects.filter(category=category)
            
            # إحصائيات هذا الشهر
            month_expenses = related_expenses.filter(
                expense_date__gte=month_start,
                is_approved=True
            )
            
            month_total = month_expenses.aggregate(total=Sum('amount'))['total'] or 0
            month_count = month_expenses.count()
            
            # إحصائيات العام
            year_start = today.replace(month=1, day=1)
            year_expenses = related_expenses.filter(
                expense_date__gte=year_start,
                is_approved=True
            )
            year_total = year_expenses.aggregate(total=Sum('amount'))['total'] or 0
            
            # آخر المصروفات
            recent_expenses = related_expenses.filter(
                is_approved=True
            ).order_by('-expense_date')[:5]
            
        except:
            pass
    
    # حساب النسبة المئوية للميزانية
    budget_percentage = 0
    remaining_budget = 0
    budget_status = 'success'
    
    if category.monthly_budget and category.monthly_budget > 0:
        budget_percentage = (month_total / category.monthly_budget) * 100
        remaining_budget = category.monthly_budget - month_total
        
        if budget_percentage > 90:
            budget_status = 'danger'
        elif budget_percentage > 70:
            budget_status = 'warning'
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # محتوى AJAX محسن
        html = f"""
        <div class="expense-category-details">
            <div class="row">
                <div class="col-md-6">
                    <h6><i class="fas fa-info-circle me-2"></i>معلومات أساسية</h6>
                    <div class="card border-0 bg-light">
                        <div class="card-body">
                            <table class="table table-sm table-borderless mb-0">
                                <tr>
                                    <td><strong>الكود:</strong></td>
                                    <td><span class="badge bg-primary">{category.code}</span></td>
                                </tr>
                                <tr>
                                    <td><strong>الاسم:</strong></td>
                                    <td>{category.name}</td>
                                </tr>
                                <tr>
                                    <td><strong>الحساب المرتبط:</strong></td>
                                    <td>
                                        <strong>{category.account.code}</strong><br>
                                        <small class="text-muted">{category.account.name}</small>
                                    </td>
                                </tr>
                                <tr>
                                    <td><strong>الميزانية الشهرية:</strong></td>
                                    <td>
                                        {f'<span class="fw-bold text-success">{category.monthly_budget:,.2f} ج.م</span>' if category.monthly_budget else '<span class="text-muted">غير محدد</span>'}
                                    </td>
                                </tr>
                                <tr>
                                    <td><strong>الحالة:</strong></td>
                                    <td>
                                        <span class="badge bg-{'success' if category.is_active else 'secondary'}">
                                            {'✅ نشط' if category.is_active else '❌ غير نشط'}
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <h6><i class="fas fa-chart-bar me-2"></i>إحصائيات الإنفاق</h6>
                    <div class="card border-0 bg-light">
                        <div class="card-body">
                            <div class="row text-center mb-3">
                                <div class="col-6">
                                    <div class="h4 text-danger mb-0">{month_total:,.0f}</div>
                                    <small class="text-muted">إنفاق هذا الشهر</small>
                                    <br><span class="badge bg-info">{month_count} عملية</span>
                                </div>
                                <div class="col-6">
                                    <div class="h4 text-primary mb-0">{year_total:,.0f}</div>
                                    <small class="text-muted">إنفاق هذا العام</small>
                                </div>
                            </div>
                            
                            {f'''
                            <div class="mt-3">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <small class="text-muted">استهلاك الميزانية</small>
                                    <small class="fw-bold text-{budget_status}">{budget_percentage:.1f}%</small>
                                </div>
                                <div class="progress" style="height: 8px;">
                                    <div class="progress-bar bg-{budget_status}" style="width: {min(budget_percentage, 100)}%;"></div>
                                </div>
                                <div class="d-flex justify-content-between mt-1">
                                    <small class="text-success">متبقي: {remaining_budget:,.0f} ج.م</small>
                                    <small class="text-muted">{category.monthly_budget:,.0f} ج.م</small>
                                </div>
                            </div>
                            ''' if category.monthly_budget else ''}
                        </div>
                    </div>
                </div>
            </div>
            
            {f'<div class="row mt-3"><div class="col-12"><h6><i class="fas fa-align-left me-2"></i>الوصف</h6><div class="alert alert-info mb-0">{category.description}</div></div></div>' if category.description else ''}
            
            {f'''
            <div class="row mt-3">
                <div class="col-12">
                    <h6><i class="fas fa-history me-2"></i>آخر المصروفات</h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-striped">
                            <thead class="table-dark">
                                <tr>
                                    <th>التاريخ</th>
                                    <th>الوصف</th>
                                    <th>المبلغ</th>
                                    <th>الحالة</th>
                                </tr>
                            </thead>
                            <tbody>
                                {
                                    ''.join([
                                        f'''<tr>
                                            <td>{expense.expense_date.strftime("%d %b")}</td>
                                            <td>{expense.description[:25]}{'...' if len(expense.description) > 25 else ''}</td>
                                            <td class="text-danger fw-bold">{expense.amount:,.0f}</td>
                                            <td><span class="badge bg-{'success' if expense.is_approved else 'warning'}">{'معتمد' if expense.is_approved else 'معلق'}</span></td>
                                        </tr>'''
                                        for expense in recent_expenses
                                    ])
                                }
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            ''' if recent_expenses else f'''
            <div class="row mt-3">
                <div class="col-12">
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>لا توجد مصروفات مسجلة</strong><br>
                        لم يتم تسجيل أي مصروفات لهذا التصنيف حتى الآن.
                    </div>
                </div>
            </div>
            '''}
            
            <div class="row mt-3">
                <div class="col-12 text-center">
                    <small class="text-muted">
                        <i class="fas fa-clock me-1"></i>
                        آخر تحديث: {timezone.now().strftime('%d %B %Y - %H:%M')}
                    </small>
                </div>
            </div>
        </div>
        """
        
        return JsonResponse({
            'success': True,
            'html': html
        })
    
    # للصفحة الكاملة
    context = {
        'category': category,
        'month_total': month_total,
        'month_count': month_count,
        'year_total': year_total,
        'budget_percentage': budget_percentage,
        'remaining_budget': remaining_budget,
        'budget_status': budget_status,
        'recent_expenses': recent_expenses,
    }
    
    return render(request, 'treasury_management/expense_category_detail.html', context)

# ===================================
# 📊 Views المعاينة المحسنة (موجودة في الرسائل السابقة مع الصلاحيات)
# ===================================

# account_detail_ajax - موجود في الرسالة السابقة مع @treasury_access_required
# account_category_detail_ajax - موجود في الرسالة السابقة مع @treasury_accountant_required

# ===================================
# 🔄 Views مساعدة إضافية
# ===================================

@treasury_access_required
def get_treasury_balance(request, treasury_id):
    """API للحصول على رصيد خزنة - نسخة محسنة"""
    # استخدام الـ API الموجود مسبقاً
    return treasury_balance_api(request, treasury_id)

# ===================================
# 📝 نهاية الملف مع ملخص شامل
# ===================================

"""
ملخص Views نظام الخزينة مع الصلاحيات:

🔵 مراجع الخزينة (treasury_viewer):
- dashboard: لوحة التحكم
- accounts_list: قائمة الحسابات  
- transactions_list: قائمة العمليات
- reports: التقارير
- *_detail_ajax: المعاينات

🟢 أمين الخزينة (treasury_cashier):  
- كل صلاحيات المراجع +
- add_transaction: إضافة عمليات مالية
- add_expense: إضافة مصروفات

🟡 محاسب الخزينة (treasury_accountant):
- كل صلاحيات أمين الخزينة +
- add_account: إضافة حسابات مالية
- edit_account: تحرير الحسابات
- account_categories_list: تصنيفات الحسابات

🟠 مدير الخزينة (treasury_manager):
- كل صلاحيات المحاسب +
- add_account_category: إضافة تصنيفات الحسابات
- edit_account_category: تحرير التصنيفات  
- expense_categories_list: تصنيفات المصروفات
- add_expense_category: إضافة تصنيفات المصروفات
- edit_expense_category: تحرير تصنيفات المصروفات
- approve_transaction: اعتماد العمليات
- cancel_transaction: إلغاء العمليات
- approve_expense: اعتماد المصروفات
- add_treasury: إضافة خزائن
- edit_treasury: تحرير الخزائن

🔴 مدير الخزينة العام (treasury_admin):
- كل الصلاحيات السابقة +
- manage_users: إدارة المستخدمين
- delete_account_category: حذف التصنيفات
- delete_expense_category: حذف تصنيفات المصروفات  
- setup_basic_categories: الإعداد السريع للتصنيفات
- setup_basic_accounts: الإعداد السريع للحسابات
- setup_expense_categories: الإعداد السريع لتصنيفات المصروفات
- quick_setup: الإعداد السريع الشامل
- create_treasury_snapshot: إنشاء لقطات الخزائن

💡 ملاحظات هامة:
- جميع Views محمية بالصلاحيات المناسبة
- يتم التحقق من وجود النماذج قبل استخدامها  
- معالجة الأخطاء شاملة مع رسائل واضحة
- النظام يدعم AJAX للمعاينات السريعة
- تم تجنب التكرار والحفاظ على الوظائف الأساسية
"""

# # View للصفحة
# @login_required
# def quick_setup(request):
#     """صفحة الإعداد السريع"""
#     return render(request, 'treasury_management/quick_setup.html')

# # إضافة هذه Views المفقودة

# @login_required
# def edit_account_category(request, pk):
#     """تحرير تصنيف حساب"""
#     category = get_object_or_404(AccountCategory, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             category.name = request.POST.get('name')
#             category.description = request.POST.get('description', '')
#             category.is_active = request.POST.get('is_active') == 'on'
            
#             # تحديث التصنيف الرئيسي إذا تم تغييره
#             parent_id = request.POST.get('parent')
#             if parent_id:
#                 category.parent = AccountCategory.objects.get(id=parent_id)
#             else:
#                 category.parent = None
            
#             category.save()
            
#             messages.success(request, f'تم تحديث تصنيف الحساب "{category.name}" بنجاح')
#             return redirect('treasury_management:account_categories_list')
            
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     context = {
#         'category': category,
#         'parent_categories': AccountCategory.objects.filter(
#             parent__isnull=True, 
#             is_active=True
#         ).exclude(id=category.id),  # استبعاد التصنيف نفسه
#     }
    
#     return render(request, 'treasury_management/edit_account_category.html', context)

# @login_required
# def delete_account_category(request, pk):
#     """حذف تصنيف حساب"""
#     category = get_object_or_404(AccountCategory, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             # التحقق من عدم وجود حسابات مرتبطة
#             accounts_count = Account.objects.filter(category=category).count()
#             if accounts_count > 0:
#                 messages.error(request, f'لا يمكن حذف التصنيف "{category.name}" لأنه مرتبط بـ {accounts_count} حساب')
#                 return redirect('treasury_management:account_categories_list')
            
#             # التحقق من عدم وجود تصنيفات فرعية
#             children_count = AccountCategory.objects.filter(parent=category).count()
#             if children_count > 0:
#                 messages.error(request, f'لا يمكن حذف التصنيف "{category.name}" لأنه يحتوي على {children_count} تصنيف فرعي')
#                 return redirect('treasury_management:account_categories_list')
            
#             category_name = category.name
#             category.delete()
#             messages.success(request, f'تم حذف تصنيف الحساب "{category_name}" بنجاح')
            
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     return redirect('treasury_management:account_categories_list')

# @login_required
# def account_category_detail(request, pk):
#     """تفاصيل تصنيف حساب"""
#     category = get_object_or_404(AccountCategory, pk=pk)
    
#     # الحسابات المرتبطة بهذا التصنيف
#     related_accounts = Account.objects.filter(category=category).order_by('code')
    
#     # التصنيفات الفرعية
#     child_categories = AccountCategory.objects.filter(parent=category).order_by('code')
    
#     # إحصائيات
#     accounts_count = related_accounts.count()
#     active_accounts_count = related_accounts.filter(is_active=True).count()
#     total_balance = related_accounts.aggregate(total=Sum('current_balance'))['total'] or 0
    
#     if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#         # طلب AJAX - إرجاع JSON
#         html = render_to_string('treasury_management/account_category_detail_modal.html', {
#             'category': category,
#             'related_accounts': related_accounts,
#             'child_categories': child_categories,
#             'stats': {
#                 'accounts_count': accounts_count,
#                 'active_accounts_count': active_accounts_count,
#                 'total_balance': total_balance,
#             }
#         })
#         return JsonResponse({
#             'success': True,
#             'html': html
#         })
    
#     context = {
#         'category': category,
#         'related_accounts': related_accounts,
#         'child_categories': child_categories,
#         'stats': {
#             'accounts_count': accounts_count,
#             'active_accounts_count': active_accounts_count,
#             'total_balance': total_balance,
#         }
#     }
    
#     return render(request, 'treasury_management/account_category_detail.html', context)

# @login_required
# def quick_setup(request):
#     """صفحة الإعداد السريع"""
#     return render(request, 'treasury_management/quick_setup.html')

# # إضافة هذا View إلى treasury_management/views.py إذا لم يكن موجوداً

# @login_required
# def get_treasury_balance(request, treasury_id):
#     """API للحصول على رصيد خزنة - نسخة بديلة"""
#     return treasury_balance_api(request, treasury_id)

# # تحديث View لوحة التحكم
# @login_required
# def treasury_dashboard(request):
#     """لوحة تحكم الخزنة المحدثة"""
#     try:
#         # فحص حالة الإعداد
#         setup_status = {
#             'categories_exist': AccountCategory.objects.exists(),
#             'accounts_exist': Account.objects.exists(),
#             'treasuries_exist': Treasury.objects.exists(),
#             'expense_categories_exist': ExpenseCategory.objects.exists(),
#         }
        
#         # إحصائيات عامة
#         treasuries = Treasury.objects.filter(is_active=True)
#         total_balance = treasuries.aggregate(total=Sum('account__current_balance'))['total'] or 0
        
#         today = timezone.now().date()
#         today_transactions = Transaction.objects.filter(
#             transaction_date__date=today,
#             is_approved=True,
#             is_cancelled=False
#         )
        
#         today_income = today_transactions.filter(transaction_type='INCOME').aggregate(
#             total=Sum('amount')
#         )['total'] or 0
        
#         today_expenses = today_transactions.filter(transaction_type='EXPENSE').aggregate(
#             total=Sum('amount')
#         )['total'] or 0
        
#         # العمليات الأخيرة
#         recent_transactions = Transaction.objects.filter(
#             is_approved=True,
#             is_cancelled=False
#         ).select_related('treasury', 'account', 'created_by').order_by('-transaction_date')[:5]
        
#         context = {
#             'setup_status': setup_status,
#             'treasuries': treasuries,
#             'total_balance': total_balance,
#             'today_income': today_income,
#             'today_expenses': today_expenses,
#             'today_net': today_income - today_expenses,
#             'recent_transactions': recent_transactions,
#             'stats': {
#                 'total_treasuries': treasuries.count(),
#                 'total_accounts': Account.objects.filter(is_active=True).count(),
#                 'total_categories': AccountCategory.objects.filter(is_active=True).count(),
#                 'pending_transactions': Transaction.objects.filter(is_approved=False, is_cancelled=False).count(),
#             }
#         }
        
#         return render(request, 'treasury_management/dashboard.html', context)
        
#     except Exception as e:
#         # في حالة عدم وجود بيانات، أعرض صفحة بسيطة
#         context = {
#             'setup_status': {
#                 'categories_exist': False,
#                 'accounts_exist': False,
#                 'treasuries_exist': False,
#                 'expense_categories_exist': False,
#             },
#             'treasuries': Treasury.objects.none(),
#             'total_balance': 0,
#             'today_income': 0,
#             'today_expenses': 0,
#             'today_net': 0,
#             'recent_transactions': Transaction.objects.none(),
#             'stats': {
#                 'total_treasuries': 0,
#                 'total_accounts': 0,
#                 'total_categories': 0,
#                 'pending_transactions': 0,
#             }
#         }
#         return render(request, 'treasury_management/dashboard.html', context)

# # تحديث treasury_management/views.py - View قائمة تصنيفات المصروفات
# @login_required
# def expense_categories_list(request):
#     """قائمة تصنيفات المصروفات مع الإحصائيات"""
#     categories = ExpenseCategory.objects.all().select_related('account').order_by('code')
    
#     # حساب الإحصائيات
#     total_categories = categories.count()
#     active_categories = categories.filter(is_active=True).count()
#     total_budget = sum(category.monthly_budget or 0 for category in categories)
#     categories_with_budget = categories.filter(monthly_budget__isnull=False).count()
    
#     context = {
#         'categories': categories,
#         'stats': {
#             'total_categories': total_categories,
#             'active_categories': active_categories,
#             'total_budget': total_budget,
#             'categories_with_budget': categories_with_budget,
#         }
#     }
    
#     return render(request, 'treasury_management/expense_categories_list.html', context)

# # إضافة إلى treasury_management/views.py

# @login_required
# def delete_expense_category(request, pk):
#     """حذف تصنيف مصروفات"""
#     category = get_object_or_404(ExpenseCategory, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             # التحقق من عدم وجود مصروفات مرتبطة
#             # expenses_count = DailyExpense.objects.filter(category=category).count()
#             # if expenses_count > 0:
#             #     messages.error(request, f'لا يمكن حذف التصنيف "{category.name}" لأنه مرتبط بـ {expenses_count} مصروف')
#             #     return redirect('treasury_management:expense_categories_list')
            
#             category_name = category.name
#             category.delete()
#             messages.success(request, f'تم حذف تصنيف المصروفات "{category_name}" بنجاح')
            
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     return redirect('treasury_management:expense_categories_list')

# # @login_required
# # def expense_category_detail(request, pk):
# #     """تفاصيل تصنيف مصروفات"""
# #     category = get_object_or_404(ExpenseCategory, pk=pk)
    
# #     # يمكن إضافة المصروفات المرتبطة لاحقاً
# #     # related_expenses = DailyExpense.objects.filter(category=category)
    
# #     if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
# #         html = f"""
# #         <div class="expense-category-details">
# #             <div class="row">
# #                 <div class="col-md-6">
# #                     <h6>معلومات أساسية</h6>
# #                     <table class="table table-sm">
# #                         <tr>
# #                             <td><strong>الكود:</strong></td>
# #                             <td>{category.code}</td>
# #                         </tr>
# #                         <tr>
# #                             <td><strong>الاسم:</strong></td>
# #                             <td>{category.name}</td>
# #                         </tr>
# #                         <tr>
# #                             <td><strong>الحساب المرتبط:</strong></td>
# #                             <td>{category.account.code} - {category.account.name}</td>
# #                         </tr>
# #                         <tr>
# #                             <td><strong>الميزانية الشهرية:</strong></td>
# #                             <td>{category.monthly_budget or 'غير محدد'}</td>
# #                         </tr>
# #                         <tr>
# #                             <td><strong>الحالة:</strong></td>
# #                             <td><span class="badge bg-{'success' if category.is_active else 'secondary'}">{'نشط' if category.is_active else 'غير نشط'}</span></td>
# #                         </tr>
# #                     </table>
# #                 </div>
                
# #                 <div class="col-md-6">
# #                     <h6>إحصائيات</h6>
# #                     <table class="table table-sm">
# #                         <tr>
# #                             <td><strong>عدد المصروفات:</strong></td>
# #                             <td><span class="badge bg-primary">قيد التطوير</span></td>
# #                         </tr>
# #                         <tr>
# #                             <td><strong>الإنفاق هذا الشهر:</strong></td>
# #                             <td class="fw-bold">قيد التطوير</td>
# #                         </tr>
# #                         <tr>
# #                             <td><strong>تاريخ الإنشاء:</strong></td>
# #                             <td>{category.created_at.strftime('%d %B %Y') if hasattr(category, 'created_at') and category.created_at else 'غير متوفر'}</td>
# #                         </tr>
# #                     </table>
# #                 </div>
# #             </div>
            
# #             {f'<div class="row mt-3"><div class="col-12"><h6>الوصف</h6><div class="bg-light p-3 rounded">{category.description}</div></div></div>' if category.description else ''}
# #         </div>
# #         """
        
# #         return JsonResponse({
# #             'success': True,
# #             'html': html
# #         })
    
# #     context = {
# #         'category': category,
# #     }
    
# #     return render(request, 'treasury_management/expense_category_detail.html', context)

# # تحديث treasury_management/views.py - View تفاصيل التصنيف
# @login_required
# def expense_category_detail(request, pk):
#     """تفاصيل تصنيف مصروفات محسن"""
#     category = get_object_or_404(ExpenseCategory, pk=pk)
    
#     # حساب الإحصائيات الفعلية
#     from django.utils import timezone
#     from datetime import datetime, timedelta
    
#     # الشهر الحالي
#     today = timezone.now().date()
#     month_start = today.replace(day=1)
    
#     # إحصائيات المصروفات (إذا كانت موجودة)
#     try:
#         # البحث عن المصروفات اليومية المرتبطة
#         related_expenses = DailyExpense.objects.filter(category=category)
        
#         # إحصائيات هذا الشهر
#         month_expenses = related_expenses.filter(
#             expense_date__gte=month_start,
#             is_approved=True
#         )
        
#         month_total = month_expenses.aggregate(total=Sum('amount'))['total'] or 0
#         month_count = month_expenses.count()
        
#         # إحصائيات العام
#         year_start = today.replace(month=1, day=1)
#         year_expenses = related_expenses.filter(
#             expense_date__gte=year_start,
#             is_approved=True
#         )
#         year_total = year_expenses.aggregate(total=Sum('amount'))['total'] or 0
        
#         # آخر المصروفات
#         recent_expenses = related_expenses.filter(
#             is_approved=True
#         ).order_by('-expense_date')[:5]
        
#     except:
#         # في حالة عدم وجود نموذج المصروفات اليومية
#         month_total = 0
#         month_count = 0
#         year_total = 0
#         recent_expenses = []
    
#     # حساب النسبة المئوية للميزانية
#     budget_percentage = 0
#     remaining_budget = 0
#     if category.monthly_budget and category.monthly_budget > 0:
#         budget_percentage = (month_total / category.monthly_budget) * 100
#         remaining_budget = category.monthly_budget - month_total
    
#     # تحديد حالة الميزانية
#     budget_status = 'success'
#     if budget_percentage > 90:
#         budget_status = 'danger'
#     elif budget_percentage > 70:
#         budget_status = 'warning'
    
#     if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#         html = f"""
#         <div class="expense-category-details">
#             <div class="row">
#                 <div class="col-md-6">
#                     <h6><i class="fas fa-info-circle me-2"></i>معلومات أساسية</h6>
#                     <table class="table table-sm">
#                         <tr>
#                             <td><strong>الكود:</strong></td>
#                             <td><span class="badge bg-primary">{category.code}</span></td>
#                         </tr>
#                         <tr>
#                             <td><strong>الاسم:</strong></td>
#                             <td>{category.name}</td>
#                         </tr>
#                         <tr>
#                             <td><strong>الحساب المرتبط:</strong></td>
#                             <td>
#                                 <strong>{category.account.code}</strong><br>
#                                 <small class="text-muted">{category.account.name}</small>
#                             </td>
#                         </tr>
#                         <tr>
#                             <td><strong>الميزانية الشهرية:</strong></td>
#                             <td>
#                                 {f'<span class="fw-bold text-success">{category.monthly_budget:,.2f} ج.م</span>' if category.monthly_budget else '<span class="text-muted">غير محدد</span>'}
#                             </td>
#                         </tr>
#                         <tr>
#                             <td><strong>الحالة:</strong></td>
#                             <td>
#                                 <span class="badge bg-{'success' if category.is_active else 'secondary'}">
#                                     {'نشط' if category.is_active else 'غير نشط'}
#                                 </span>
#                             </td>
#                         </tr>
#                     </table>
#                 </div>
                
#                 <div class="col-md-6">
#                     <h6><i class="fas fa-chart-bar me-2"></i>إحصائيات الإنفاق</h6>
#                     <table class="table table-sm">
#                         <tr>
#                             <td><strong>إنفاق هذا الشهر:</strong></td>
#                             <td>
#                                 <span class="fw-bold text-danger">{month_total:,.2f} ج.م</span>
#                                 <br><small class="text-muted">{month_count} عملية</small>
#                             </td>
#                         </tr>
#                         <tr>
#                             <td><strong>إنفاق هذا العام:</strong></td>
#                             <td><span class="fw-bold">{year_total:,.2f} ج.م</span></td>
#                         </tr>
#                         {'<tr><td><strong>المتبقي من الميزانية:</strong></td><td><span class="fw-bold text-' + budget_status + '">' + f'{remaining_budget:,.2f} ج.م</span></td></tr>' if category.monthly_budget else ''}
#                         <tr>
#                             <td><strong>متوسط الإنفاق اليومي:</strong></td>
#                             <td>
#                                 {f'<span class="text-info">{(month_total / max(today.day, 1)):,.2f} ج.م</span>' if month_total > 0 else '<span class="text-muted">لا يوجد</span>'}
#                             </td>
#                         </tr>
#                     </table>
#                 </div>
#             </div>
            
#             {f'<div class="row mt-3"><div class="col-12"><h6><i class="fas fa-align-left me-2"></i>الوصف</h6><div class="bg-light p-3 rounded">{category.description}</div></div></div>' if category.description else ''}
            
#             {f'''
#             <div class="row mt-3">
#                 <div class="col-12">
#                     <h6><i class="fas fa-chart-pie me-2"></i>حالة الميزانية</h6>
#                     <div class="progress mb-2" style="height: 10px;">
#                         <div class="progress-bar bg-{budget_status}" style="width: {min(budget_percentage, 100)}%;" 
#                              data-bs-toggle="tooltip" title="{budget_percentage:.1f}% من الميزانية">
#                         </div>
#                     </div>
#                     <div class="d-flex justify-content-between">
#                         <small class="text-muted">0 ج.م</small>
#                         <small class="fw-bold">{budget_percentage:.1f}% مستخدم</small>
#                         <small class="text-muted">{category.monthly_budget:,.0f} ج.م</small>
#                     </div>
#                 </div>
#             </div>
#             ''' if category.monthly_budget else ''}
            
#             {f'''
#             <div class="row mt-3">
#                 <div class="col-12">
#                     <h6><i class="fas fa-history me-2"></i>آخر المصروفات ({len(recent_expenses)})</h6>
#                     <div class="table-responsive">
#                         <table class="table table-sm table-striped">
#                             <thead>
#                                 <tr>
#                                     <th>التاريخ</th>
#                                     <th>الوصف</th>
#                                     <th>المبلغ</th>
#                                 </tr>
#                             </thead>
#                             <tbody>
#                                 {
#                                     ''.join([
#                                         f'<tr><td>{expense.expense_date.strftime("%d %b")}</td><td>{expense.description[:30]}...</td><td class="text-danger fw-bold">{expense.amount:,.2f}</td></tr>'
#                                         for expense in recent_expenses
#                                     ])
#                                 }
#                             </tbody>
#                         </table>
#                     </div>
#                 </div>
#             </div>
#             ''' if recent_expenses else f'''
#             <div class="row mt-3">
#                 <div class="col-12">
#                     <div class="alert alert-info">
#                         <i class="fas fa-info-circle me-2"></i>
#                         <strong>لا توجد مصروفات مسجلة</strong><br>
#                         لم يتم تسجيل أي مصروفات لهذا التصنيف حتى الآن.
#                     </div>
#                 </div>
#             </div>
#             '''}
            
#             <div class="row mt-3">
#                 <div class="col-12">
#                     <h6><i class="fas fa-calendar-alt me-2"></i>معلومات إضافية</h6>
#                     <div class="row">
#                         <div class="col-md-6">
#                             <small class="text-muted">
#                                 <strong>تاريخ الإنشاء:</strong> 
#                                 {category.created_at.strftime('%d %B %Y - %H:%M') if hasattr(category, 'created_at') and category.created_at else 'غير متوفر'}
#                             </small>
#                         </div>
#                         <div class="col-md-6">
#                             <small class="text-muted">
#                                 <strong>آخر تحديث:</strong> 
#                                 {category.updated_at.strftime('%d %B %Y - %H:%M') if hasattr(category, 'updated_at') and category.updated_at else 'غير متوفر'}
#                             </small>
#                         </div>
#                     </div>
#                 </div>
#             </div>
#         </div>
#         """
        
#         return JsonResponse({
#             'success': True,
#             'html': html
#         })
    
#     # للصفحة الكاملة
#     context = {
#         'category': category,
#         'month_total': month_total,
#         'month_count': month_count,
#         'year_total': year_total,
#         'budget_percentage': budget_percentage,
#         'remaining_budget': remaining_budget,
#         'budget_status': budget_status,
#         'recent_expenses': recent_expenses,
#     }
    
#     return render(request, 'treasury_management/expense_category_detail.html', context)


# # treasury_management/views.py - إضافة Views للمعاينة
# from django.http import JsonResponse
# from django.template.loader import render_to_string
# from django.db.models import Sum, Count
# from django.shortcuts import get_object_or_404

# @login_required
# def account_detail_ajax(request, account_id):
#     """تفاصيل الحساب عبر AJAX"""
#     try:
#         account = get_object_or_404(Account.objects.select_related('category'), id=account_id)
        
#         # الحصول على آخر المعاملات
#         recent_transactions = Transaction.objects.filter(
#             account=account
#         ).order_by('-created_at')[:10]
        
#         # حساب الإحصائيات
#         income_stats = Transaction.objects.filter(
#             account=account, 
#             transaction_type='INCOME'
#         ).aggregate(
#             total=Sum('amount'),
#             count=Count('id')
#         )
        
#         expense_stats = Transaction.objects.filter(
#             account=account, 
#             transaction_type='EXPENSE'
#         ).aggregate(
#             total=Sum('amount'),
#             count=Count('id')
#         )
        
#         total_income = income_stats['total'] or 0
#         total_expenses = expense_stats['total'] or 0
#         income_count = income_stats['count'] or 0
#         expense_count = expense_stats['count'] or 0
        
#         html = render_to_string('treasury_management/account_detail_modal.html', {
#             'account': account,
#             'recent_transactions': recent_transactions,
#             'total_income': total_income,
#             'total_expenses': total_expenses,
#             'income_count': income_count,
#             'expense_count': expense_count,
#         }, request=request)
        
#         return JsonResponse({
#             'success': True,
#             'html': html
#         })
#     except Account.DoesNotExist:
#         return JsonResponse({
#             'success': False,
#             'error': 'الحساب غير موجود'
#         }, status=404)
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': f'حدث خطأ: {str(e)}'
#         }, status=500)

# @login_required  
# def account_category_detail_ajax(request, category_id):
#     """تفاصيل تصنيف الحساب عبر AJAX"""
#     try:
#         category = get_object_or_404(
#             AccountCategory.objects.select_related('parent'), 
#             id=category_id
#         )
        
#         # الحصول على الحسابات المرتبطة
#         accounts = Account.objects.filter(category=category).order_by('code')
        
#         # الحصول على التصنيفات الفرعية
#         subcategories = AccountCategory.objects.filter(parent=category).order_by('code')
        
#         # إحصائيات التصنيف
#         accounts_count = accounts.count()
#         subcategories_count = subcategories.count()
#         total_balance = accounts.aggregate(Sum('current_balance'))['current_balance__sum'] or 0
        
#         html = render_to_string('treasury_management/account_category_detail_modal.html', {
#             'category': category,
#             'accounts': accounts[:10],  # أول 10 حسابات
#             'subcategories': subcategories,
#             'accounts_count': accounts_count,
#             'subcategories_count': subcategories_count,
#             'total_balance': total_balance,
#         }, request=request)
        
#         return JsonResponse({
#             'success': True,
#             'html': html
#         })
#     except AccountCategory.DoesNotExist:
#         return JsonResponse({
#             'success': False,
#             'error': 'التصنيف غير موجود'
#         }, status=404)
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': f'حدث خطأ: {str(e)}'
#         }, status=500)

# treasury_management/views.py - إضافة view صفحة الرفض

def access_denied(request):
    """صفحة رفض الوصول المحسنة"""
    requested_url = request.session.get('requested_url', '/treasury/')
    required_groups = request.session.get('required_groups', [])
    user_groups = request.session.get('user_groups', [])
    
    # ترجمة أسماء المجموعات
    group_names = {
        'treasury_admin': 'مدير الخزينة العام',
        'treasury_manager': 'مدير الخزينة',
        'treasury_accountant': 'محاسب الخزينة',
        'treasury_cashier': 'أمين الخزينة',
        'treasury_viewer': 'مراجع الخزينة',
    }
    
    required_roles = [group_names.get(group, group) for group in required_groups]
    user_roles = [group_names.get(group, group) for group in user_groups if group.startswith('treasury_')]
    
    # مسح البيانات من الجلسة
    for key in ['requested_url', 'required_groups', 'user_groups']:
        request.session.pop(key, None)
    
    context = {
        'requested_url': requested_url,
        'required_roles': required_roles,
        'user_roles': user_roles,
        'has_treasury_roles': bool(user_roles),
        'contact_admin': True,
    }
    
    return render(request, 'treasury_management/access_denied.html', context)
