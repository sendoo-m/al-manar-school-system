"""
views.py - ملف وظائف العرض لنظام إدارة مخزن الكتب
يحتوي على جميع العمليات الخاصة بإدارة المخزون من كتب وكراسات وأدوات مدرسية
"""

# ============================================================================
# المكتبات والاستيرادات المطلوبة
# ============================================================================

# استيرادات Django الأساسية
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST, require_http_methods, require_GET
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Sum, F
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.db import transaction
from django.template.loader import render_to_string

# مكتبات إضافية
from decimal import Decimal
import csv, json
from datetime import date, datetime, timedelta

# استيراد النماذج المحلية
from .models import (
    Supplier, Subject, Book, Notebook, SchoolSupply,
    StockReceipt, BookReceiptItem, NotebookReceiptItem, SupplyReceiptItem,
    StudentDistribution, BookDistributionItem, NotebookDistributionItem, SupplyDistributionItem,
    StockShortage
)

# استيراد النماذج من التطبيقات الأخرى
from students.models import Student
from payments.models import Tuition
from school_settings.models import GradeLevel, EducationLevel


# ============================================================================
# الصفحة الرئيسية ولوحة المعلومات
# ============================================================================

# @never_cache
# @login_required
# def inventory_home(request):
#     """الصفحة الرئيسية لمخزن الكتب - عرض الإحصائيات والملخصات"""
    
#     try:
#         # إحصائيات عامة للعناصر النشطة
#         total_books = Book.objects.filter(is_active=True).count()
#         total_notebooks = Notebook.objects.filter(is_active=True).count()
#         total_supplies = SchoolSupply.objects.filter(is_active=True).count()
        
#         # إحصائيات المخزون للكتب
#         books_stock = Book.objects.filter(is_active=True).aggregate(
#             total_stock=Sum('total_stock'),
#             available_stock=Sum('available_stock'),
#             distributed=Sum('distributed_count')
#         )
        
#         # إحصائيات المخزون للكراسات
#         notebooks_stock = Notebook.objects.filter(is_active=True).aggregate(
#             total_stock=Sum('total_stock'),
#             available_stock=Sum('available_stock'),
#             distributed=Sum('distributed_count')
#         )
        
#         # إحصائيات المخزون للأدوات المدرسية
#         supplies_stock = SchoolSupply.objects.filter(is_active=True).aggregate(
#             total_stock=Sum('total_stock'),
#             available_stock=Sum('available_stock'),
#             distributed=Sum('distributed_count')
#         )
        
#         # العناصر منخفضة المخزون (أقل من الحد الأدنى)
#         low_stock_books = Book.objects.filter(
#             is_active=True, available_stock__lte=F('minimum_stock_level')
#         ).count()
        
#         low_stock_notebooks = Notebook.objects.filter(
#             is_active=True, available_stock__lte=F('minimum_stock_level')
#         ).count()
        
#         low_stock_supplies = SchoolSupply.objects.filter(
#             is_active=True, available_stock__lte=F('minimum_stock_level')
#         ).count()
        
#         # النواقص المُبلغ عنها والمعلقة
#         pending_shortages = StockShortage.objects.filter(
#             status__in=['REPORTED', 'ACKNOWLEDGED']
#         ).count()
        
#         # إحصائيات يومية وأسبوعية
#         today = timezone.now().date()
#         week_ago = today - timedelta(days=7)
        
#         distributions_today = StudentDistribution.objects.filter(distribution_date=today).count()
#         receipts_this_week = StockReceipt.objects.filter(receipt_date__gte=week_ago).count()
        
#         # أحدث العمليات للعرض السريع
#         recent_receipts = StockReceipt.objects.select_related('supplier').order_by('-receipt_date')[:5]
#         recent_distributions = StudentDistribution.objects.select_related('student').order_by('-distribution_date')[:5]
        
#         # العناصر التي تحتاج إعادة طلب (مخزون منخفض)
#         items_to_reorder = []
        
#         # كتب تحتاج إعادة طلب
#         books_to_reorder = Book.objects.filter(
#             is_active=True, available_stock__lte=F('minimum_stock_level')
#         )[:10]
        
#         for book in books_to_reorder:
#             items_to_reorder.append({
#                 'type': 'كتاب',
#                 'name': book.title,
#                 'current_stock': book.available_stock,
#                 'minimum_level': book.minimum_stock_level,
#                 'subject': book.subject.name
#             })
        
#         # كراسات تحتاج إعادة طلب
#         notebooks_to_reorder = Notebook.objects.filter(
#             is_active=True, available_stock__lte=F('minimum_stock_level')
#         )[:10]
        
#         for notebook in notebooks_to_reorder:
#             items_to_reorder.append({
#                 'type': 'كراسة',
#                 'name': notebook.name,
#                 'current_stock': notebook.available_stock,
#                 'minimum_level': notebook.minimum_stock_level,
#                 'subject': notebook.get_notebook_type_display()
#             })
        
#     except Exception as e:
#         print(f"خطأ في إحصائيات المخزن: {e}")
#         # قيم افتراضية في حالة الخطأ
#         total_books = total_notebooks = total_supplies = 0
#         books_stock = notebooks_stock = supplies_stock = {
#             'total_stock': 0, 'available_stock': 0, 'distributed': 0
#         }
#         low_stock_books = low_stock_notebooks = low_stock_supplies = 0
#         pending_shortages = distributions_today = receipts_this_week = 0
#         recent_receipts = recent_distributions = items_to_reorder = []
    
#     context = {
#         'total_books': total_books,
#         'total_notebooks': total_notebooks,
#         'total_supplies': total_supplies,
#         'books_stock': books_stock,
#         'notebooks_stock': notebooks_stock,
#         'supplies_stock': supplies_stock,
#         'low_stock_books': low_stock_books,
#         'low_stock_notebooks': low_stock_notebooks,
#         'low_stock_supplies': low_stock_supplies,
#         'pending_shortages': pending_shortages,
#         'distributions_today': distributions_today,
#         'receipts_this_week': receipts_this_week,
#         'recent_receipts': recent_receipts,
#         'recent_distributions': recent_distributions,
#         'items_to_reorder': items_to_reorder,
#         'today': today,
#         'page_title': 'الصفحة الرئيسية - مخزن الكتب'
#     }
    
#     return render(request, 'books_inventory/inventory_home.html', context)

@never_cache
@login_required
def inventory_home(request):
    """الصفحة الرئيسية المحسنة لمخزن الكتب - مُصححة"""
    
    try:
        # الإحصائيات الأساسية
        total_books = Book.objects.filter(is_active=True).count()
        total_notebooks = Notebook.objects.filter(is_active=True).count()
        total_supplies = SchoolSupply.objects.filter(is_active=True).count()
        
        # إحصائيات المخزون المفصلة
        books_stock = Book.objects.filter(is_active=True).aggregate(
            total_stock=Sum('total_stock'),
            available_stock=Sum('available_stock'),
            distributed=Sum('distributed_count')
        )
        
        notebooks_stock = Notebook.objects.filter(is_active=True).aggregate(
            total_stock=Sum('total_stock'),
            available_stock=Sum('available_stock'),
            distributed=Sum('distributed_count')
        )
        
        supplies_stock = SchoolSupply.objects.filter(is_active=True).aggregate(
            total_stock=Sum('total_stock'),
            available_stock=Sum('available_stock'),
            distributed=Sum('distributed_count')
        )
        
        # المخزون المنخفض
        low_stock_books = Book.objects.filter(
            is_active=True, available_stock__lte=F('minimum_stock_level')
        ).count()
        
        low_stock_notebooks = Notebook.objects.filter(
            is_active=True, available_stock__lte=F('minimum_stock_level')
        ).count()
        
        low_stock_supplies = SchoolSupply.objects.filter(
            is_active=True, available_stock__lte=F('minimum_stock_level')
        ).count()
        
        # الإحصائيات الزمنية
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # أنشطة اليوم والأسبوع والشهر
        distributions_today = StudentDistribution.objects.filter(distribution_date=today).count()
        receipts_this_week = StockReceipt.objects.filter(receipt_date__gte=week_ago).count()
        
        # 🔧 إصلاح حساب القيمة الإجمالية - استخدام cost_price بدلاً من unit_price
        total_value = 0
        try:
            books_value = Book.objects.filter(is_active=True).aggregate(
                total=Sum(F('available_stock') * F('cost_price'))
            )['total'] or 0
            
            # يمكن إضافة قيمة الكراسات والأدوات إذا كان لها أسعار
            notebooks_value = 0  # إذا كان هناك حقل سعر للكراسات
            supplies_value = 0   # إذا كان هناك حقل سعر للأدوات
            
            total_value = books_value + notebooks_value + supplies_value
            
        except Exception as e:
            print(f"خطأ في حساب القيمة الإجمالية: {e}")
            total_value = 0
        
        # أحدث العمليات
        recent_receipts = StockReceipt.objects.select_related('supplier').order_by('-receipt_date')[:5]
        recent_distributions = StudentDistribution.objects.select_related('student').order_by('-distribution_date')[:5]
        
        # النواقص الحرجة
        critical_items = []
        
        # كتب نفدت تماماً
        out_of_stock_books = Book.objects.filter(is_active=True, available_stock=0)[:5]
        for book in out_of_stock_books:
            critical_items.append({
                'type': 'كتاب',
                'name': book.title,
                'status': 'نفد',
                'subject': book.subject.name if book.subject else 'غير محدد',
                'priority': 'عالية'
            })
        
        # عناصر منخفضة المخزون
        low_books = Book.objects.filter(
            is_active=True, 
            available_stock__gt=0,
            available_stock__lte=F('minimum_stock_level')
        )[:5]
        
        for book in low_books:
            critical_items.append({
                'type': 'كتاب',
                'name': book.title,
                'status': f'متبقي {book.available_stock}',
                'subject': book.subject.name if book.subject else 'غير محدد',
                'priority': 'متوسطة'
            })
        
        # كراسات نفدت أو منخفضة
        try:
            out_of_stock_notebooks = Notebook.objects.filter(is_active=True, available_stock=0)[:3]
            for notebook in out_of_stock_notebooks:
                critical_items.append({
                    'type': 'كراسة',
                    'name': notebook.name,
                    'status': 'نفد',
                    'subject': notebook.get_notebook_type_display(),
                    'priority': 'عالية'
                })
                
            low_notebooks = Notebook.objects.filter(
                is_active=True,
                available_stock__gt=0, 
                available_stock__lte=F('minimum_stock_level')
            )[:3]
            
            for notebook in low_notebooks:
                critical_items.append({
                    'type': 'كراسة',
                    'name': notebook.name,
                    'status': f'متبقي {notebook.available_stock}',
                    'subject': notebook.get_notebook_type_display(),
                    'priority': 'متوسطة'
                })
        except Exception as e:
            print(f"خطأ في معالجة الكراسات: {e}")
        
        # إحصائيات إضافية للرسوم البيانية
        monthly_stats = {
            'receipts': StockReceipt.objects.filter(receipt_date__gte=month_ago).count(),
            'distributions': StudentDistribution.objects.filter(distribution_date__gte=month_ago).count(),
            'shortages_reported': 0  # سيتم تحديثه إذا كان نموذج StockShortage متاح
        }
        
        # محاولة الحصول على إحصائيات النواقص إذا كان النموذج متاحاً
        try:
            monthly_stats['shortages_reported'] = StockShortage.objects.filter(
                report_date__gte=month_ago
            ).count()
        except Exception:
            monthly_stats['shortages_reported'] = 0
        
        # حساب النسب المئوية للمخزون
        books_percentage = 0
        if books_stock['total_stock'] and books_stock['total_stock'] > 0:
            books_percentage = round((books_stock['available_stock'] or 0) * 100 / books_stock['total_stock'], 1)
        
        notebooks_percentage = 0
        if notebooks_stock['total_stock'] and notebooks_stock['total_stock'] > 0:
            notebooks_percentage = round((notebooks_stock['available_stock'] or 0) * 100 / notebooks_stock['total_stock'], 1)
        
        supplies_percentage = 0
        if supplies_stock['total_stock'] and supplies_stock['total_stock'] > 0:
            supplies_percentage = round((supplies_stock['available_stock'] or 0) * 100 / supplies_stock['total_stock'], 1)
        
    except Exception as e:
        print(f"خطأ في إحصائيات المخزن: {e}")
        # قيم افتراضية آمنة
        total_books = total_notebooks = total_supplies = 0
        books_stock = notebooks_stock = supplies_stock = {
            'total_stock': 0, 'available_stock': 0, 'distributed': 0
        }
        low_stock_books = low_stock_notebooks = low_stock_supplies = 0
        distributions_today = receipts_this_week = 0
        total_value = 0
        recent_receipts = recent_distributions = critical_items = []
        monthly_stats = {'receipts': 0, 'distributions': 0, 'shortages_reported': 0}
        books_percentage = notebooks_percentage = supplies_percentage = 0
    
    context = {
        'total_books': total_books,
        'total_notebooks': total_notebooks,
        'total_supplies': total_supplies,
        'books_stock': books_stock,
        'notebooks_stock': notebooks_stock,
        'supplies_stock': supplies_stock,
        'low_stock_books': low_stock_books,
        'low_stock_notebooks': low_stock_notebooks,
        'low_stock_supplies': low_stock_supplies,
        'distributions_today': distributions_today,
        'receipts_this_week': receipts_this_week,
        'total_value': total_value,
        'recent_receipts': recent_receipts,
        'recent_distributions': recent_distributions,
        'critical_items': critical_items,
        'monthly_stats': monthly_stats,
        'books_percentage': books_percentage,
        'notebooks_percentage': notebooks_percentage,
        'supplies_percentage': supplies_percentage,
        'today': today,
        'page_title': 'الصفحة الرئيسية - مخزن الكتب'
    }
    
    return render(request, 'books_inventory/inventory_home.html', context)


# ============================================================================
# إدارة المواد الدراسية
# ============================================================================

@never_cache
@login_required
def subjects_list(request):
    """قائمة المواد الدراسية مع إمكانية البحث والفلترة"""
    
    search_query = request.GET.get('search', '')
    is_active_filter = request.GET.get('is_active', '')
    
    # الحصول على المواد
    subjects = Subject.objects.all().order_by('name')
    
    # تطبيق البحث
    if search_query:
        subjects = subjects.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # تطبيق فلتر الحالة
    if is_active_filter:
        subjects = subjects.filter(is_active=is_active_filter == 'true')
    
    # تقسيم الصفحات
    paginator = Paginator(subjects, 12)
    page_number = request.GET.get('page')
    
    try:
        subjects_page = paginator.page(page_number)
    except PageNotAnInteger:
        subjects_page = paginator.page(1)
    except EmptyPage:
        subjects_page = paginator.page(paginator.num_pages)
    
    context = {
        'subjects': subjects_page,
        'search_query': search_query,
        'is_active_filter': is_active_filter,
        'page_title': 'قائمة المواد الدراسية'
    }
    
    return render(request, 'books_inventory/subjects_list.html', context)


@never_cache
@login_required
def subject_detail(request, pk):
    """تفاصيل المادة الدراسية مع الإحصائيات والكتب المرتبطة"""
    
    subject = get_object_or_404(Subject, pk=pk)
    
    # إحصائيات المادة
    books_count = Book.objects.filter(subject=subject).count()
    active_books = Book.objects.filter(subject=subject, is_active=True).count()
    total_books_stock = Book.objects.filter(subject=subject).aggregate(
        Sum('total_stock')
    )['total_stock__sum'] or 0
    
    # أحدث الكتب للمادة
    recent_books = Book.objects.filter(subject=subject).select_related(
        'subject'
    ).prefetch_related('grade_levels').order_by('-created_at')[:5]
    
    # الكتب حسب الصفوف الدراسية
    books_by_grade = {}
    if hasattr(subject, 'grade_levels'):
        for grade in subject.grade_levels.all():
            grade_books = Book.objects.filter(
                subject=subject,
                grade_levels=grade,
                is_active=True
            ).count()
            if grade_books > 0:
                books_by_grade[grade] = grade_books
    
    context = {
        'subject': subject,
        'books_count': books_count,
        'active_books': active_books,
        'total_books_stock': total_books_stock,
        'recent_books': recent_books,
        'books_by_grade': books_by_grade,
        'grade_levels_count': subject.grade_levels.count() if hasattr(subject, 'grade_levels') else 0,
        'education_levels_count': subject.education_levels.count() if hasattr(subject, 'education_levels') else 0,
        'page_title': f'تفاصيل المادة - {subject.name}'
    }
    
    return render(request, 'books_inventory/subject_detail.html', context)


@never_cache
@login_required
def add_subject(request):
    """إضافة مادة دراسية جديدة مع ربطها بالصفوف والمراحل التعليمية"""
    
    if request.method == 'POST':
        try:
            # استخراج البيانات من النموذج
            name = request.POST.get('name', '').strip()
            name_en = request.POST.get('name_en', '').strip()
            description = request.POST.get('description', '').strip()
            subject_code = request.POST.get('subject_code', '').strip()
            color = request.POST.get('color', '#007bff')
            is_active = request.POST.get('is_active') == 'on'
            is_core_subject = request.POST.get('is_core_subject') == 'on'
            weekly_hours = int(request.POST.get('weekly_hours', 2))
            
            # استخراج الصفوف والمراحل المختارة
            selected_grade_levels = request.POST.getlist('grade_levels')
            selected_education_levels = request.POST.getlist('education_levels')
            
            # التحقق من البيانات المطلوبة
            if not name:
                messages.error(request, 'اسم المادة مطلوب')
                return redirect('books_inventory:add_subject')
            
            # التحقق من عدم التكرار
            if Subject.objects.filter(name=name).exists():
                messages.error(request, f'يوجد مادة بنفس الاسم "{name}" بالفعل')
                return redirect('books_inventory:add_subject')
            
            if subject_code and Subject.objects.filter(subject_code=subject_code).exists():
                messages.error(request, f'يوجد مادة بنفس الكود "{subject_code}" بالفعل')
                return redirect('books_inventory:add_subject')
            
            # إنشاء المادة
            subject = Subject.objects.create(
                name=name,
                name_en=name_en,
                description=description,
                subject_code=subject_code,
                color=color,
                is_active=is_active,
                is_core_subject=is_core_subject,
                weekly_hours=weekly_hours
            )
            
            # ربط الصفوف والمراحل إذا كانت موجودة في النموذج
            if hasattr(subject, 'grade_levels') and selected_grade_levels:
                subject.grade_levels.set(selected_grade_levels)
            
            if hasattr(subject, 'education_levels') and selected_education_levels:
                subject.education_levels.set(selected_education_levels)
            
            messages.success(request, f'تم إضافة المادة "{subject.name}" بنجاح')
            return redirect('books_inventory:subject_detail', pk=subject.pk)
            
        except Exception as e:
            print(f"خطأ في إضافة المادة: {e}")
            messages.error(request, f'حدث خطأ في إضافة المادة: {str(e)}')
            return redirect('books_inventory:add_subject')
    
    # طلب GET - تحضير البيانات للقالب
    context = {
        'grade_levels': GradeLevel.objects.filter(is_active=True).select_related('education_level'),
        'education_levels': EducationLevel.objects.filter(is_active=True),
        'page_title': 'إضافة مادة دراسية جديدة'
    }
    
    return render(request, 'books_inventory/add_subject.html', context)


@never_cache
@login_required
def edit_subject(request, pk):
    """تعديل مادة دراسية مع إدارة الصفوف والمراحل التعليمية"""
    
    subject = get_object_or_404(Subject, pk=pk)
    
    if request.method == 'POST':
        try:
            # استخراج البيانات المحدثة
            name = request.POST.get('name', '').strip()
            name_en = request.POST.get('name_en', '').strip()
            description = request.POST.get('description', '').strip()
            subject_code = request.POST.get('subject_code', '').strip()
            color = request.POST.get('color', '#007bff')
            is_active = request.POST.get('is_active') == 'on'
            is_core_subject = request.POST.get('is_core_subject') == 'on'
            weekly_hours = int(request.POST.get('weekly_hours', 2))
            
            selected_grade_levels = request.POST.getlist('grade_levels')
            selected_education_levels = request.POST.getlist('education_levels')
            
            # التحقق من البيانات
            if not name:
                messages.error(request, 'اسم المادة مطلوب')
                return redirect('books_inventory:edit_subject', pk=pk)
            
            # التحقق من عدم التكرار (عدا المادة الحالية)
            if Subject.objects.filter(name=name).exclude(pk=pk).exists():
                messages.error(request, f'يوجد مادة أخرى بنفس الاسم "{name}" بالفعل')
                return redirect('books_inventory:edit_subject', pk=pk)
            
            if subject_code and Subject.objects.filter(subject_code=subject_code).exclude(pk=pk).exists():
                messages.error(request, f'يوجد مادة أخرى بنفس الكود "{subject_code}" بالفعل')
                return redirect('books_inventory:edit_subject', pk=pk)
            
            # تحديث المادة
            subject.name = name
            subject.name_en = name_en
            subject.description = description
            subject.subject_code = subject_code
            subject.color = color
            subject.is_active = is_active
            subject.is_core_subject = is_core_subject
            subject.weekly_hours = weekly_hours
            subject.save()
            
            # تحديث العلاقات
            if hasattr(subject, 'grade_levels'):
                subject.grade_levels.set(selected_grade_levels)
            
            if hasattr(subject, 'education_levels'):
                subject.education_levels.set(selected_education_levels)
            
            messages.success(request, f'تم تحديث المادة "{subject.name}" بنجاح')
            return redirect('books_inventory:subject_detail', pk=subject.pk)
            
        except Exception as e:
            print(f"خطأ في تحديث المادة: {e}")
            messages.error(request, f'حدث خطأ في تحديث المادة: {str(e)}')
            return redirect('books_inventory:edit_subject', pk=pk)
    
    # طلب GET - تحضير البيانات للتعديل
    context = {
        'subject': subject,
        'grade_levels': GradeLevel.objects.filter(is_active=True).select_related('education_level'),
        'education_levels': EducationLevel.objects.filter(is_active=True),
        'selected_grade_levels': list(subject.grade_levels.values_list('id', flat=True)) if hasattr(subject, 'grade_levels') else [],
        'selected_education_levels': list(subject.education_levels.values_list('id', flat=True)) if hasattr(subject, 'education_levels') else [],
        'page_title': f'تعديل المادة - {subject.name}'
    }
    
    return render(request, 'books_inventory/edit_subject.html', context)


@never_cache
@login_required
def delete_subject(request, pk):
    """حذف مادة دراسية مع التحقق من الكتب المرتبطة"""
    
    subject = get_object_or_404(Subject, pk=pk)
    
    # التحقق من وجود كتب مرتبطة
    books_count = Book.objects.filter(subject=subject).count()
    
    if request.method == 'POST':
        try:
            if books_count > 0:
                messages.error(request, f'لا يمكن حذف المادة لأنها مرتبطة بـ {books_count} كتاب. يرجى حذف الكتب أولاً أو تغيير المادة')
                return redirect('books_inventory:subject_detail', pk=pk)
            
            subject_name = subject.name
            subject.delete()
            messages.success(request, f'تم حذف المادة "{subject_name}" بنجاح')
            return redirect('books_inventory:subjects_list')
            
        except Exception as e:
            messages.error(request, f'لا يمكن حذف المادة: {str(e)}')
            return redirect('books_inventory:subject_detail', pk=pk)
    
    context = {
        'subject': subject,
        'books_count': books_count,
        'page_title': f'حذف المادة - {subject.name}'
    }
    
    return render(request, 'books_inventory/delete_subject.html', context)


# ============================================================================
# إدارة الكتب
# ============================================================================

@never_cache
@login_required
def books_list(request):
    """قائمة الكتب مع الفلاتر والبحث المتقدم"""
    
    # استخراج معاملات البحث والفلترة
    search_query = request.GET.get('search', '')
    subject_filter = request.GET.get('subject', '')
    book_type_filter = request.GET.get('book_type', '')
    term_filter = request.GET.get('term', '')
    stock_status_filter = request.GET.get('stock_status', '')
    grade_level_filter = request.GET.get('grade_level', '')
    
    # الاستعلام الأساسي
    books = Book.objects.filter(is_active=True).select_related('subject').prefetch_related('grade_levels')
    
    # تطبيق فلاتر البحث
    if search_query:
        books = books.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if subject_filter:
        books = books.filter(subject_id=subject_filter)
    
    if book_type_filter:
        books = books.filter(book_type=book_type_filter)
        
    if term_filter:
        books = books.filter(term=term_filter)
    
    if grade_level_filter:
        books = books.filter(grade_levels__id=grade_level_filter)
    
    # فلتر حالة المخزون
    if stock_status_filter:
        if stock_status_filter == 'available':
            books = books.filter(available_stock__gt=F('minimum_stock_level'))
        elif stock_status_filter == 'low_stock':
            books = books.filter(available_stock__lte=F('minimum_stock_level'), available_stock__gt=0)
        elif stock_status_filter == 'out_of_stock':
            books = books.filter(available_stock=0)
    
    # ترتيب النتائج
    books = books.order_by('book_type', 'subject__name', 'title')
    
    # حساب إحصائيات للعرض
    all_books = Book.objects.filter(is_active=True)
    ministry_books_count = all_books.filter(book_type__in=['MINISTRY', 'WORKBOOK']).count()
    manar_books_count = all_books.filter(book_type__startswith='MANAR_').count()
    available_books_count = all_books.filter(available_stock__gt=F('minimum_stock_level')).count()
    low_stock_books_count = all_books.filter(available_stock__lte=F('minimum_stock_level')).count()
    
    # تقسيم الصفحات
    paginator = Paginator(books, 20)
    page_number = request.GET.get('page')
    
    try:
        books_page = paginator.page(page_number)
    except PageNotAnInteger:
        books_page = paginator.page(1)
    except EmptyPage:
        books_page = paginator.page(paginator.num_pages)
    
    # البيانات للفلاتر
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    
    context = {
        'books': books_page,
        'subjects': subjects,
        'grade_levels': grade_levels,
        'search_query': search_query,
        'subject_filter': subject_filter,
        'book_type_filter': book_type_filter,
        'term_filter': term_filter,
        'stock_status_filter': stock_status_filter,
        'grade_level_filter': grade_level_filter,
        'book_type_choices': Book.BOOK_TYPE_CHOICES,
        'ministry_books_count': ministry_books_count,
        'manar_books_count': manar_books_count,
        'available_books_count': available_books_count,
        'low_stock_books_count': low_stock_books_count,
        'page_title': 'إدارة الكتب والملخصات'
    }
    
    return render(request, 'books_inventory/books_list.html', context)


@never_cache
@login_required
def book_detail(request, pk):
    """تفاصيل الكتاب مع الإحصائيات والعمليات الأخيرة"""
    
    book = get_object_or_404(Book, pk=pk)
    
    # أحدث استلامات الكتاب
    recent_receipts = BookReceiptItem.objects.filter(book=book).select_related(
        'receipt__supplier'
    ).order_by('-receipt__receipt_date')[:5]
    
    # أحدث توزيعات الكتاب
    recent_distributions = []
    try:
        recent_distributions = BookDistributionItem.objects.filter(book=book).select_related(
            'distribution__student'
        ).order_by('-distribution__distribution_date')[:5]
    except:
        pass
    
    # حساب الإحصائيات الفعلية من الاستلامات والتوزيعات
    total_received = BookReceiptItem.objects.filter(book=book).aggregate(
        total=Sum('quantity_received')
    )['total'] or 0
    
    total_distributed = 0
    try:
        total_distributed = BookDistributionItem.objects.filter(book=book).aggregate(
            total=Sum('quantity_distributed')
        )['total'] or 0
    except:
        pass
    
    total_damaged = BookReceiptItem.objects.filter(book=book).aggregate(
        total=Sum('quantity_damaged')
    )['total'] or 0
    
    # تحديث مخزون الكتاب إذا لزم الأمر
    if hasattr(book, 'sync_stock_from_receipts'):
        if book.total_stock != total_received:
            book.sync_stock_from_receipts()
            book.refresh_from_db()
    
    context = {
        'book': book,
        'recent_receipts': recent_receipts,
        'recent_distributions': recent_distributions,
        'total_received': total_received,
        'total_distributed': total_distributed,
        'total_damaged': total_damaged,
        'page_title': f'تفاصيل الكتاب - {book.title}'
    }
    
    return render(request, 'books_inventory/book_detail.html', context)


@never_cache
@login_required
def add_book(request):
    """إضافة كتاب جديد مع ربطه بالمادة والصفوف الدراسية"""
    
    if request.method == 'POST':
        try:
            # استخراج البيانات من النموذج
            title = request.POST.get('title', '').strip()
            book_type = request.POST.get('book_type', '')
            subject_id = request.POST.get('subject', '')
            academic_year = request.POST.get('academic_year', '').strip()
            term = request.POST.get('term', 'FULL_YEAR')
            edition_year = request.POST.get('edition_year', '').strip()
            pages_count = request.POST.get('pages_count', '')
            description = request.POST.get('description', '').strip()
            cost_price = request.POST.get('cost_price', '0')
            minimum_stock_level = request.POST.get('minimum_stock_level', '10')
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من البيانات المطلوبة
            if not title:
                messages.error(request, 'عنوان الكتاب مطلوب')
                return redirect('books_inventory:add_book')
            
            if not subject_id:
                messages.error(request, 'المادة الدراسية مطلوبة')
                return redirect('books_inventory:add_book')
            
            # إنشاء الكتاب
            book = Book.objects.create(
                title=title,
                book_type=book_type,
                subject_id=subject_id,
                academic_year=academic_year,
                term=term,
                edition_year=edition_year,
                pages_count=int(pages_count) if pages_count else None,
                description=description,
                cost_price=Decimal(cost_price),
                minimum_stock_level=int(minimum_stock_level),
                is_active=is_active
            )
            
            # ربط الصفوف الدراسية
            grade_levels = request.POST.getlist('grade_levels')
            if grade_levels:
                book.grade_levels.set(grade_levels)
            
            messages.success(request, f'تم إضافة الكتاب "{book.title}" بنجاح')
            return redirect('books_inventory:book_detail', pk=book.pk)
            
        except Exception as e:
            print(f"خطأ في إضافة الكتاب: {e}")
            messages.error(request, f'حدث خطأ في إضافة الكتاب: {str(e)}')
            return redirect('books_inventory:add_book')
    
    # طلب GET - تحضير البيانات
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    
    context = {
        'subjects': subjects,
        'grade_levels': grade_levels,
        'book_type_choices': Book.BOOK_TYPE_CHOICES,
        'term_choices': [
            ('FIRST', 'الترم الأول'),
            ('SECOND', 'الترم الثاني'),
            ('FULL_YEAR', 'السنة كاملة')
        ],
        'page_title': 'إضافة كتاب جديد'
    }
    
    return render(request, 'books_inventory/add_book.html', context)


@never_cache
@login_required
def edit_book(request, pk):
    """تعديل بيانات الكتاب"""
    
    book = get_object_or_404(Book, pk=pk)
    
    if request.method == 'POST':
        try:
            # استخراج البيانات المحدثة
            title = request.POST.get('title', '').strip()
            book_type = request.POST.get('book_type', '')
            subject_id = request.POST.get('subject', '')
            academic_year = request.POST.get('academic_year', '').strip()
            term = request.POST.get('term', 'FULL_YEAR')
            edition_year = request.POST.get('edition_year', '').strip()
            pages_count = request.POST.get('pages_count', '')
            description = request.POST.get('description', '').strip()
            cost_price = request.POST.get('cost_price', '0')
            minimum_stock_level = request.POST.get('minimum_stock_level', '10')
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من البيانات
            if not title:
                messages.error(request, 'عنوان الكتاب مطلوب')
                return redirect('books_inventory:edit_book', pk=pk)
            
            if not subject_id:
                messages.error(request, 'المادة الدراسية مطلوبة')
                return redirect('books_inventory:edit_book', pk=pk)
            
            # تحديث الكتاب
            book.title = title
            book.book_type = book_type
            book.subject_id = subject_id
            book.academic_year = academic_year
            book.term = term
            book.edition_year = edition_year
            book.pages_count = int(pages_count) if pages_count else None
            book.description = description
            book.cost_price = Decimal(cost_price)
            book.minimum_stock_level = int(minimum_stock_level)
            book.is_active = is_active
            book.save()
            
            # تحديث الصفوف الدراسية
            grade_levels = request.POST.getlist('grade_levels')
            book.grade_levels.set(grade_levels)
            
            messages.success(request, f'تم تحديث الكتاب "{book.title}" بنجاح')
            return redirect('books_inventory:book_detail', pk=book.pk)
            
        except Exception as e:
            print(f"خطأ في تحديث الكتاب: {e}")
            messages.error(request, f'حدث خطأ في تحديث الكتاب: {str(e)}')
            return redirect('books_inventory:edit_book', pk=pk)
    
    # طلب GET - تحضير البيانات للتعديل
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    
    context = {
        'book': book,
        'subjects': subjects,
        'grade_levels': grade_levels,
        'book_type_choices': Book.BOOK_TYPE_CHOICES,
        'term_choices': [
            ('FIRST', 'الترم الأول'),
            ('SECOND', 'الترم الثاني'),
            ('FULL_YEAR', 'السنة كاملة')
        ],
        'page_title': f'تعديل الكتاب - {book.title}'
    }
    
    return render(request, 'books_inventory/edit_book.html', context)


@never_cache  
@login_required
def delete_book(request, pk):
    """حذف كتاب مع التحقق من الاستلامات والتوزيعات"""
    
    book = get_object_or_404(Book, pk=pk)
    
    if request.method == 'POST':
        try:
            book_title = book.title
            book.delete()
            messages.success(request, f'تم حذف الكتاب "{book_title}" بنجاح')
            return redirect('books_inventory:books_list')
        except Exception as e:
            messages.error(request, f'لا يمكن حذف الكتاب: {str(e)}')
            return redirect('books_inventory:book_detail', pk=pk)
    
    # إحصائيات الكتاب للتحذير
    total_receipts = BookReceiptItem.objects.filter(book=book).count()
    total_distributions = BookDistributionItem.objects.filter(book=book).count()
    
    context = {
        'book': book,
        'total_receipts': total_receipts,
        'total_distributions': total_distributions,
        'page_title': f'حذف الكتاب - {book.title}'
    }
    
    return render(request, 'books_inventory/delete_book.html', context)


# ============================================================================
# إدارة الكراسات
# ============================================================================

@never_cache
@login_required
def notebooks_list(request):
    """قائمة الكراسات مع الفلاتر والبحث"""
    
    # معاملات البحث والفلترة
    search_query = request.GET.get('search', '')
    notebook_type_filter = request.GET.get('notebook_type', '')
    size_filter = request.GET.get('size', '')
    stock_status_filter = request.GET.get('stock_status', '')
    
    # الاستعلام الأساسي
    notebooks = Notebook.objects.filter(is_active=True).prefetch_related('grade_levels')
    
    # تطبيق الفلاتر
    if search_query:
        notebooks = notebooks.filter(name__icontains=search_query)
    
    if notebook_type_filter:
        notebooks = notebooks.filter(notebook_type=notebook_type_filter)
    
    if size_filter:
        notebooks = notebooks.filter(size=size_filter)
    
    # فلتر حالة المخزون
    if stock_status_filter:
        if stock_status_filter == 'available':
            notebooks = notebooks.filter(available_stock__gt=F('minimum_stock_level'))
        elif stock_status_filter == 'low_stock':
            notebooks = notebooks.filter(available_stock__lte=F('minimum_stock_level'), available_stock__gt=0)
        elif stock_status_filter == 'out_of_stock':
            notebooks = notebooks.filter(available_stock=0)
    
    notebooks = notebooks.order_by('notebook_type', 'name')
    
    # تقسيم الصفحات
    paginator = Paginator(notebooks, 20)
    page_number = request.GET.get('page')
    
    try:
        notebooks_page = paginator.page(page_number)
    except PageNotAnInteger:
        notebooks_page = paginator.page(1)
    except EmptyPage:
        notebooks_page = paginator.page(paginator.num_pages)
    
    context = {
        'notebooks': notebooks_page,
        'search_query': search_query,
        'notebook_type_filter': notebook_type_filter,
        'size_filter': size_filter,
        'stock_status_filter': stock_status_filter,
        'notebook_type_choices': Notebook.NOTEBOOK_TYPE_CHOICES,
        'size_choices': Notebook.SIZE_CHOICES,
        'page_title': 'إدارة الكراسات'
    }
    
    return render(request, 'books_inventory/notebooks_list.html', context)


@never_cache
@login_required
def notebook_detail(request, pk):
    """تفاصيل الكراسة مع الاستلامات والتوزيعات"""
    
    notebook = get_object_or_404(Notebook, pk=pk, is_active=True)
    
    # أحدث استلامات الكراسة
    recent_receipts = NotebookReceiptItem.objects.filter(
        notebook=notebook
    ).select_related('receipt__supplier').order_by('-receipt__receipt_date')[:10]
    
    # أحدث توزيعات الكراسة
    recent_distributions = NotebookDistributionItem.objects.filter(
        notebook=notebook,
        is_distributed=True
    ).select_related('distribution__student').order_by('-distribution_date')[:10]
    
    # النواقص المُبلغ عنها
    shortages = StockShortage.objects.filter(
        notebook=notebook,
        status__in=['REPORTED', 'ACKNOWLEDGED', 'ORDERED']
    ).order_by('-reported_date')
    
    # الصفوف المرتبطة
    associated_grades = notebook.grade_levels.filter(is_active=True).select_related('education_level')
    
    context = {
        'notebook': notebook,
        'recent_receipts': recent_receipts,
        'recent_distributions': recent_distributions,
        'shortages': shortages,
        'associated_grades': associated_grades,
        'page_title': f'تفاصيل الكراسة - {notebook.name}'
    }
    
    return render(request, 'books_inventory/notebook_detail.html', context)


@never_cache
@login_required
def add_notebook(request):
    """إضافة كراسة جديدة"""
    
    if request.method == 'POST':
        try:
            # استخراج البيانات
            name = request.POST.get('name', '').strip()
            notebook_type = request.POST.get('notebook_type', '')
            size = request.POST.get('size', '')
            pages_count = request.POST.get('pages_count', '')
            cost_price = request.POST.get('cost_price', '0')
            minimum_stock_level = request.POST.get('minimum_stock_level', '10')
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من البيانات
            if not name:
                messages.error(request, 'اسم الكراسة مطلوب')
                return redirect('books_inventory:add_notebook')
            
            # إنشاء الكراسة
            notebook = Notebook.objects.create(
                name=name,
                notebook_type=notebook_type,
                size=size,
                pages_count=int(pages_count) if pages_count else 100,
                cost_price=Decimal(cost_price),
                minimum_stock_level=int(minimum_stock_level),
                is_active=is_active
            )
            
            # ربط الصفوف الدراسية
            grade_levels = request.POST.getlist('grade_levels')
            if grade_levels:
                notebook.grade_levels.set(grade_levels)
            
            messages.success(request, f'تم إضافة الكراسة "{notebook.name}" بنجاح')
            return redirect('books_inventory:notebook_detail', pk=notebook.pk)
            
        except Exception as e:
            print(f"خطأ في إضافة الكراسة: {e}")
            messages.error(request, f'حدث خطأ في إضافة الكراسة: {str(e)}')
            return redirect('books_inventory:add_notebook')
    
    # طلب GET
    grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    
    context = {
        'grade_levels': grade_levels,
        'notebook_type_choices': Notebook.NOTEBOOK_TYPE_CHOICES,
        'size_choices': Notebook.SIZE_CHOICES,
        'page_title': 'إضافة كراسة جديدة'
    }
    
    return render(request, 'books_inventory/add_notebook.html', context)


@never_cache
@login_required
def edit_notebook(request, pk):
    """تعديل كراسة"""
    
    notebook = get_object_or_404(Notebook, pk=pk)
    
    if request.method == 'POST':
        try:
            # استخراج البيانات المحدثة
            notebook.name = request.POST.get('name', '').strip()
            notebook.notebook_type = request.POST.get('notebook_type', '')
            notebook.size = request.POST.get('size', '')
            notebook.pages_count = int(request.POST.get('pages_count', '100'))
            notebook.cost_price = Decimal(request.POST.get('cost_price', '0'))
            notebook.minimum_stock_level = int(request.POST.get('minimum_stock_level', '10'))
            notebook.is_active = request.POST.get('is_active') == 'on'
            
            if not notebook.name:
                messages.error(request, 'اسم الكراسة مطلوب')
                return redirect('books_inventory:edit_notebook', pk=pk)
            
            notebook.save()
            
            # تحديث الصفوف الدراسية
            grade_levels = request.POST.getlist('grade_levels')
            notebook.grade_levels.set(grade_levels)
            
            messages.success(request, f'تم تحديث الكراسة "{notebook.name}" بنجاح')
            return redirect('books_inventory:notebook_detail', pk=notebook.pk)
            
        except Exception as e:
            print(f"خطأ في تحديث الكراسة: {e}")
            messages.error(request, f'حدث خطأ في تحديث الكراسة: {str(e)}')
    
    grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    
    context = {
        'notebook': notebook,
        'grade_levels': grade_levels,
        'notebook_type_choices': Notebook.NOTEBOOK_TYPE_CHOICES,
        'size_choices': Notebook.SIZE_CHOICES,
        'page_title': f'تعديل الكراسة - {notebook.name}'
    }
    
    return render(request, 'books_inventory/edit_notebook.html', context)


@never_cache
@login_required
def delete_notebook(request, pk):
    """حذف كراسة"""
    
    notebook = get_object_or_404(Notebook, pk=pk)
    
    if request.method == 'POST':
        try:
            notebook_name = notebook.name
            notebook.delete()
            messages.success(request, f'تم حذف الكراسة "{notebook_name}" بنجاح')
            return redirect('books_inventory:notebooks_list')
        except Exception as e:
            messages.error(request, f'لا يمكن حذف الكراسة: {str(e)}')
            return redirect('books_inventory:notebook_detail', pk=pk)
    
    context = {
        'notebook': notebook,
        'page_title': f'حذف الكراسة - {notebook.name}'
    }
    
    return render(request, 'books_inventory/delete_notebook.html', context)


# ============================================================================
# إدارة الأدوات المدرسية
# ============================================================================

@never_cache
@login_required
def supplies_list(request):
    """قائمة الأدوات المدرسية مع الفلاتر"""
    
    # معاملات البحث والفلترة
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    stock_status_filter = request.GET.get('stock_status', '')
    
    # الاستعلام الأساسي
    supplies = SchoolSupply.objects.filter(is_active=True).prefetch_related('grade_levels')
    
    # تطبيق الفلاتر
    if search_query:
        supplies = supplies.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if category_filter:
        supplies = supplies.filter(category=category_filter)
    
    # فلتر حالة المخزون
    if stock_status_filter:
        if stock_status_filter == 'available':
            supplies = supplies.filter(available_stock__gt=F('minimum_stock_level'))
        elif stock_status_filter == 'low_stock':
            supplies = supplies.filter(available_stock__lte=F('minimum_stock_level'), available_stock__gt=0)
        elif stock_status_filter == 'out_of_stock':
            supplies = supplies.filter(available_stock=0)
    
    supplies = supplies.order_by('category', 'name')
    
    # تقسيم الصفحات
    paginator = Paginator(supplies, 20)
    page_number = request.GET.get('page')
    
    try:
        supplies_page = paginator.page(page_number)
    except PageNotAnInteger:
        supplies_page = paginator.page(1)
    except EmptyPage:
        supplies_page = paginator.page(paginator.num_pages)
    
    context = {
        'supplies': supplies_page,
        'search_query': search_query,
        'category_filter': category_filter,
        'stock_status_filter': stock_status_filter,
        'category_choices': SchoolSupply.SUPPLY_CATEGORY_CHOICES,
        'page_title': 'إدارة الأدوات المدرسية'
    }
    
    return render(request, 'books_inventory/supplies_list.html', context)


@never_cache
@login_required
def supply_detail(request, pk):
    """تفاصيل الأداة المدرسية"""
    
    supply = get_object_or_404(SchoolSupply, pk=pk, is_active=True)
    
    # أحدث استلامات الأداة
    recent_receipts = SupplyReceiptItem.objects.filter(
        supply=supply
    ).select_related('receipt__supplier').order_by('-receipt__receipt_date')[:10]
    
    # أحدث توزيعات الأداة
    recent_distributions = SupplyDistributionItem.objects.filter(
        supply=supply,
        is_distributed=True
    ).select_related('distribution__student').order_by('-distribution_date')[:10]
    
    # النواقص المُبلغ عنها
    shortages = StockShortage.objects.filter(
        supply=supply,
        status__in=['REPORTED', 'ACKNOWLEDGED', 'ORDERED']
    ).order_by('-reported_date')
    
    # الصفوف المرتبطة
    associated_grades = supply.grade_levels.filter(is_active=True).select_related('education_level')
    
    context = {
        'supply': supply,
        'recent_receipts': recent_receipts,
        'recent_distributions': recent_distributions,
        'shortages': shortages,
        'associated_grades': associated_grades,
        'page_title': f'تفاصيل الأداة - {supply.name}'
    }
    
    return render(request, 'books_inventory/supply_detail.html', context)


@never_cache
@login_required
def add_supply(request):
    """إضافة أداة مدرسية جديدة"""
    
    if request.method == 'POST':
        try:
            # استخراج البيانات
            name = request.POST.get('name', '').strip()
            category = request.POST.get('category', '')
            unit = request.POST.get('unit', '').strip()
            description = request.POST.get('description', '').strip()
            cost_price = request.POST.get('cost_price', 0)
            minimum_stock_level = request.POST.get('minimum_stock_level', 10)
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من البيانات المطلوبة
            if not name:
                messages.error(request, 'اسم الأداة المدرسية مطلوب')
                return redirect('books_inventory:add_supply')
            
            if not unit:
                messages.error(request, 'وحدة القياس مطلوبة')
                return redirect('books_inventory:add_supply')
            
            # إنشاء الأداة المدرسية
            supply = SchoolSupply.objects.create(
                name=name,
                category=category,
                unit=unit,
                description=description,
                cost_price=Decimal(cost_price),
                minimum_stock_level=int(minimum_stock_level),
                is_active=is_active
            )
            
            # ربط الصفوف الدراسية
            grade_levels = request.POST.getlist('grade_levels')
            if grade_levels:
                supply.grade_levels.set(grade_levels)
            
            messages.success(request, f'تم إضافة الأداة المدرسية "{supply.name}" بنجاح')
            return redirect('books_inventory:supply_detail', pk=supply.pk)
            
        except Exception as e:
            print(f"خطأ في إضافة الأداة المدرسية: {e}")
            messages.error(request, f'حدث خطأ أثناء إضافة الأداة المدرسية: {str(e)}')
            return redirect('books_inventory:add_supply')
    
    # GET request - عرض النموذج
    from school_settings.models import GradeLevel
    grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    
    context = {
        'grade_levels': grade_levels,
        'category_choices': SchoolSupply.SUPPLY_CATEGORY_CHOICES,  # الإصلاح هنا
        'page_title': 'إضافة أداة مدرسية جديدة'
    }
    
    return render(request, 'books_inventory/add_supply.html', context)

@never_cache
@login_required
def edit_supply(request, pk):
    """تعديل أداة مدرسية"""
    supply = get_object_or_404(SchoolSupply, pk=pk)
    
    if request.method == 'POST':
        try:
            supply.name = request.POST.get('name', '').strip()
            supply.category = request.POST.get('category', '')
            supply.unit = request.POST.get('unit', '').strip()
            supply.description = request.POST.get('description', '').strip()
            supply.cost_price = Decimal(request.POST.get('cost_price', 0))
            supply.minimum_stock_level = int(request.POST.get('minimum_stock_level', 10))
            supply.is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من البيانات المطلوبة
            if not supply.name:
                messages.error(request, 'اسم الأداة المدرسية مطلوب')
                return redirect('books_inventory:edit_supply', pk=pk)
            
            if not supply.unit:
                messages.error(request, 'وحدة القياس مطلوبة')
                return redirect('books_inventory:edit_supply', pk=pk)
            
            supply.save()
            
            # تحديث الصفوف الدراسية
            grade_levels = request.POST.getlist('grade_levels')
            supply.grade_levels.set(grade_levels)
            
            messages.success(request, f'تم تعديل الأداة المدرسية "{supply.name}" بنجاح')
            return redirect('books_inventory:supply_detail', pk=supply.pk)
            
        except Exception as e:
            print(f"خطأ في تعديل الأداة المدرسية: {e}")
            messages.error(request, f'حدث خطأ أثناء تعديل الأداة المدرسية: {str(e)}')
    
    # GET request - عرض النموذج
    from school_settings.models import GradeLevel
    grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    
    context = {
        'supply': supply,
        'grade_levels': grade_levels,
        'category_choices': SchoolSupply.SUPPLY_CATEGORY_CHOICES,  # الإصلاح هنا أيضاً
        'page_title': f'تعديل الأداة المدرسية - {supply.name}'
    }
    
    return render(request, 'books_inventory/edit_supply.html', context)


@never_cache
@login_required
def delete_supply(request, pk):
    """حذف أداة مدرسية"""
    
    supply = get_object_or_404(SchoolSupply, pk=pk)
    
    if request.method == 'POST':
        try:
            supply_name = supply.name
            supply.delete()
            messages.success(request, f'تم حذف الأداة "{supply_name}" بنجاح')
            return redirect('books_inventory:supplies_list')
        except Exception as e:
            messages.error(request, f'لا يمكن حذف الأداة: {str(e)}')
            return redirect('books_inventory:supply_detail', pk=pk)
    
    context = {
        'supply': supply,
        'page_title': f'حذف الأداة - {supply.name}'
    }
    
    return render(request, 'books_inventory/delete_supply.html', context)


# ============================================================================
# إدارة الموردين
# ============================================================================

@never_cache
@login_required
def suppliers_list(request):
    """قائمة الموردين مع البحث"""
    
    search_query = request.GET.get('search', '')
    
    # الحصول على الموردين
    suppliers = Supplier.objects.all().order_by('name')
    
    # تطبيق البحث
    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # تقسيم الصفحات
    paginator = Paginator(suppliers, 12)
    page_number = request.GET.get('page')
    
    try:
        suppliers_page = paginator.page(page_number)
    except PageNotAnInteger:
        suppliers_page = paginator.page(1)
    except EmptyPage:
        suppliers_page = paginator.page(paginator.num_pages)
    
    context = {
        'suppliers': suppliers_page,
        'search_query': search_query,
        'page_title': 'قائمة الموردين'
    }
    
    return render(request, 'books_inventory/suppliers_list.html', context)


@never_cache
@login_required
def supplier_detail(request, pk):
    """تفاصيل المورد مع الإحصائيات"""
    
    supplier = get_object_or_404(Supplier, pk=pk)
    
    # استلامات المورد
    receipts = StockReceipt.objects.filter(supplier=supplier).order_by('-receipt_date')
    
    # إحصائيات المورد
    total_receipts = receipts.count()
    total_items = receipts.aggregate(Sum('total_items'))['total_items__sum'] or 0
    total_cost = receipts.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    
    # أحدث الإيصالات
    recent_receipts = receipts[:5]
    
    context = {
        'supplier': supplier,
        'recent_receipts': recent_receipts,
        'total_receipts': total_receipts,
        'total_items': total_items,
        'total_cost': total_cost,
        'page_title': f'تفاصيل المورد - {supplier.name}'
    }
    
    return render(request, 'books_inventory/supplier_detail.html', context)


@never_cache
@login_required
def add_supplier(request):
    """إضافة مورد جديد"""
    
    if request.method == 'POST':
        try:
            # استخراج البيانات
            name = request.POST.get('name', '').strip()
            contact_person = request.POST.get('contact_person', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            email = request.POST.get('email', '').strip()
            address = request.POST.get('address', '').strip()
            notes = request.POST.get('notes', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من البيانات
            if not name:
                messages.error(request, 'اسم المورد مطلوب')
                return redirect('books_inventory:add_supplier')
            
            # التحقق من عدم التكرار
            if Supplier.objects.filter(name=name).exists():
                messages.error(request, f'يوجد مورد بنفس الاسم "{name}" بالفعل')
                return redirect('books_inventory:add_supplier')
            
            # إنشاء المورد
            supplier = Supplier.objects.create(
                name=name,
                contact_person=contact_person,
                phone_number=phone_number,
                email=email,
                address=address,
                notes=notes,
                is_active=is_active
            )
            
            messages.success(request, f'تم إضافة المورد "{supplier.name}" بنجاح')
            return redirect('books_inventory:supplier_detail', pk=supplier.pk)
            
        except Exception as e:
            print(f"خطأ في إضافة المورد: {e}")
            messages.error(request, f'حدث خطأ في إضافة المورد: {str(e)}')
            return redirect('books_inventory:add_supplier')
    
    context = {
        'page_title': 'إضافة مورد جديد'
    }
    
    return render(request, 'books_inventory/add_supplier.html', context)


@never_cache
@login_required
def edit_supplier(request, pk):
    """تعديل بيانات المورد"""
    
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        try:
            # استخراج البيانات المحدثة
            name = request.POST.get('name', '').strip()
            contact_person = request.POST.get('contact_person', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            email = request.POST.get('email', '').strip()
            address = request.POST.get('address', '').strip()
            notes = request.POST.get('notes', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من البيانات
            if not name:
                messages.error(request, 'اسم المورد مطلوب')
                return redirect('books_inventory:edit_supplier', pk=pk)
            
            # التحقق من عدم التكرار (عدا المورد الحالي)
            if Supplier.objects.filter(name=name).exclude(pk=pk).exists():
                messages.error(request, f'يوجد مورد آخر بنفس الاسم "{name}" بالفعل')
                return redirect('books_inventory:edit_supplier', pk=pk)
            
            # تحديث المورد
            supplier.name = name
            supplier.contact_person = contact_person
            supplier.phone_number = phone_number
            supplier.email = email
            supplier.address = address
            supplier.notes = notes
            supplier.is_active = is_active
            supplier.save()
            
            messages.success(request, f'تم تحديث بيانات المورد "{supplier.name}" بنجاح')
            return redirect('books_inventory:supplier_detail', pk=supplier.pk)
            
        except Exception as e:
            print(f"خطأ في تحديث المورد: {e}")
            messages.error(request, f'حدث خطأ في تحديث المورد: {str(e)}')
            return redirect('books_inventory:edit_supplier', pk=pk)
    
    context = {
        'supplier': supplier,
        'page_title': f'تعديل المورد - {supplier.name}'
    }
    
    return render(request, 'books_inventory/edit_supplier.html', context)


# ============================================================================
# إدارة إيصالات الاستلام
# ============================================================================

@never_cache
@login_required
def receipts_list(request):
    """قائمة إيصالات الاستلام مع الفلاتر"""
    
    # معاملات البحث والفلترة
    search_query = request.GET.get('search', '')
    supplier_filter = request.GET.get('supplier', '')
    receipt_type_filter = request.GET.get('receipt_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # الاستعلام الأساسي
    receipts = StockReceipt.objects.select_related('supplier', 'received_by').order_by('-receipt_date')
    
    # تطبيق الفلاتر
    if search_query:
        receipts = receipts.filter(
            Q(receipt_number__icontains=search_query) |
            Q(supplier__name__icontains=search_query) |
            Q(invoice_number__icontains=search_query)
        )
    
    if supplier_filter:
        receipts = receipts.filter(supplier_id=supplier_filter)
    
    if receipt_type_filter:
        receipts = receipts.filter(receipt_type=receipt_type_filter)
    
    if date_from:
        receipts = receipts.filter(receipt_date__gte=date_from)
    
    if date_to:
        receipts = receipts.filter(receipt_date__lte=date_to)
    
    # تقسيم الصفحات
    paginator = Paginator(receipts, 15)
    page_number = request.GET.get('page')
    
    try:
        receipts_page = paginator.page(page_number)
    except PageNotAnInteger:
        receipts_page = paginator.page(1)
    except EmptyPage:
        receipts_page = paginator.page(paginator.num_pages)
    
    # البيانات للفلاتر
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
    context = {
        'receipts': receipts_page,
        'suppliers': suppliers,
        'search_query': search_query,
        'supplier_filter': supplier_filter,
        'receipt_type_filter': receipt_type_filter,
        'date_from': date_from,
        'date_to': date_to,
        'receipt_type_choices': StockReceipt.RECEIPT_TYPE_CHOICES,
        'page_title': 'إيصالات الاستلام'
    }
    
    return render(request, 'books_inventory/receipts_list.html', context)


@never_cache
@login_required
def add_receipt(request):
    """إضافة إيصال استلام جديد مع العناصر"""
    
    if request.method == 'POST':
        try:
            # استخراج البيانات الأساسية للإيصال
            supplier_id = request.POST.get('supplier')
            receipt_type = request.POST.get('receipt_type')
            receipt_date = request.POST.get('receipt_date')
            invoice_number = request.POST.get('invoice_number', '').strip()
            notes = request.POST.get('notes', '').strip()
            item_count = int(request.POST.get('item_count', 0))
            
            # التحقق من البيانات المطلوبة
            if not supplier_id or not receipt_type or not receipt_date:
                messages.error(request, 'يجب إدخال جميع البيانات المطلوبة')
                return redirect('books_inventory:add_receipt')
            
            if item_count == 0:
                messages.error(request, 'يجب إضافة عنصر واحد على الأقل للإيصال')
                return redirect('books_inventory:add_receipt')
            
            # إنشاء الإيصال
            supplier = get_object_or_404(Supplier, pk=supplier_id)
            
            # إنشاء رقم الإيصال
            receipt_number = f"REC-{timezone.now().strftime('%Y%m%d')}-{StockReceipt.objects.count() + 1:04d}"
            
            receipt = StockReceipt.objects.create(
                receipt_number=receipt_number,
                supplier=supplier,
                receipt_type=receipt_type,
                receipt_date=receipt_date,
                invoice_number=invoice_number,
                notes=notes,
                received_by=request.user,
                total_items=0,  # سنحدثه لاحقاً
                damaged_items=0,  # سنحدثه لاحقاً
                total_cost=0  # سنحدثه لاحقاً
            )
            
            # إضافة العناصر حسب النوع
            total_items = 0
            total_damaged = 0
            total_cost = Decimal('0.00')
            
            with transaction.atomic():
                for i in range(item_count):
                    if receipt_type == 'BOOKS':
                        # معالجة عناصر الكتب
                        book_id = request.POST.get(f'book_{i}')
                        if book_id:
                            book = get_object_or_404(Book, pk=book_id)
                            quantity = int(request.POST.get(f'quantity_{i}', 0))
                            damaged = int(request.POST.get(f'damaged_{i}', 0))
                            unit_cost = Decimal(request.POST.get(f'unit_cost_{i}', '0'))
                            
                            if quantity > 0:
                                # إنشاء عنصر الإيصال
                                BookReceiptItem.objects.create(
                                    receipt=receipt,
                                    book=book,
                                    quantity_received=quantity,
                                    quantity_damaged=damaged,
                                    unit_cost=unit_cost,
                                    total_cost=quantity * unit_cost
                                )
                                
                                # تحديث مخزون الكتاب
                                book.total_stock += quantity
                                book.damaged_count += damaged
                                if hasattr(book, 'update_stock'):
                                    book.update_stock()
                                
                                total_items += quantity
                                total_damaged += damaged
                                total_cost += quantity * unit_cost
                    
                    elif receipt_type == 'NOTEBOOKS':
                        # معالجة عناصر الكراسات
                        notebook_id = request.POST.get(f'notebook_{i}')
                        if notebook_id:
                            notebook = get_object_or_404(Notebook, pk=notebook_id)
                            quantity = int(request.POST.get(f'quantity_{i}', 0))
                            damaged = int(request.POST.get(f'damaged_{i}', 0))
                            unit_cost = Decimal(request.POST.get(f'unit_cost_{i}', '0'))
                            
                            if quantity > 0:
                                NotebookReceiptItem.objects.create(
                                    receipt=receipt,
                                    notebook=notebook,
                                    quantity_received=quantity,
                                    quantity_damaged=damaged,
                                    unit_cost=unit_cost,
                                    total_cost=quantity * unit_cost
                                )
                                
                                # تحديث مخزون الكراسة
                                notebook.total_stock += quantity
                                notebook.damaged_count += damaged
                                if hasattr(notebook, 'update_stock'):
                                    notebook.update_stock()
                                
                                total_items += quantity
                                total_damaged += damaged
                                total_cost += quantity * unit_cost
                    
                    elif receipt_type == 'SUPPLIES':
                        # معالجة عناصر الأدوات المدرسية
                        supply_id = request.POST.get(f'supply_{i}')
                        if supply_id:
                            supply = get_object_or_404(SchoolSupply, pk=supply_id)
                            quantity = int(request.POST.get(f'quantity_{i}', 0))
                            damaged = int(request.POST.get(f'damaged_{i}', 0))
                            unit_cost = Decimal(request.POST.get(f'unit_cost_{i}', '0'))
                            
                            if quantity > 0:
                                SupplyReceiptItem.objects.create(
                                    receipt=receipt,
                                    supply=supply,
                                    quantity_received=quantity,
                                    quantity_damaged=damaged,
                                    unit_cost=unit_cost,
                                    total_cost=quantity * unit_cost
                                )
                                
                                # تحديث مخزون الأداة المدرسية
                                supply.total_stock += quantity
                                supply.damaged_count += damaged
                                if hasattr(supply, 'update_stock'):
                                    supply.update_stock()
                                
                                total_items += quantity
                                total_damaged += damaged
                                total_cost += quantity * unit_cost
                
                # تحديث إجماليات الإيصال
                receipt.total_items = total_items
                receipt.damaged_items = total_damaged
                receipt.total_cost = total_cost
                receipt.save()
            
            messages.success(request, f'تم إنشاء إيصال الاستلام "{receipt.receipt_number}" بنجاح')
            return redirect('books_inventory:receipt_detail', pk=receipt.pk)
            
        except Exception as e:
            print(f"خطأ في إنشاء الإيصال: {e}")
            messages.error(request, f'حدث خطأ في إنشاء الإيصال: {str(e)}')
            return redirect('books_inventory:add_receipt')
    
    # طلب GET - تحضير البيانات للقالب
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    books = Book.objects.filter(is_active=True).select_related('subject').order_by('title')
    notebooks = Notebook.objects.filter(is_active=True).order_by('name')
    supplies = SchoolSupply.objects.filter(is_active=True).order_by('name')
    
    # تحويل البيانات لـ JSON للاستخدام في JavaScript
    books_json = json.dumps([{
        'id': book.id,
        'title': book.title,
        'subject': book.subject.name,
        'book_type': book.get_book_type_display(),
        'cost_price': float(book.cost_price)
    } for book in books])
    
    notebooks_json = json.dumps([{
        'id': notebook.id,
        'name': notebook.name,
        'type': notebook.get_notebook_type_display(),
        'size': notebook.get_size_display(),
        'pages': notebook.pages_count,
        'cost_price': float(notebook.cost_price)
    } for notebook in notebooks])
    
    supplies_json = json.dumps([{
        'id': supply.id,
        'name': supply.name,
        'category': supply.get_category_display(),
        'unit': supply.unit,
        'cost_price': float(supply.cost_price)
    } for supply in supplies])
    
    context = {
        'suppliers': suppliers,
        'books': books_json,
        'notebooks': notebooks_json,
        'supplies': supplies_json,
        'receipt_type_choices': StockReceipt.RECEIPT_TYPE_CHOICES,
        'today': timezone.now().date(),
        'page_title': 'إضافة إيصال استلام جديد'
    }
    
    return render(request, 'books_inventory/add_receipt.html', context)


@never_cache
@login_required
def receipt_detail(request, pk):
    """تفاصيل إيصال الاستلام مع جميع العناصر"""
    
    receipt = get_object_or_404(StockReceipt, pk=pk)
    
    # الحصول على عناصر الإيصال حسب النوع
    book_items = []
    notebook_items = []
    supply_items = []
    
    if receipt.receipt_type == 'BOOKS':
        book_items = BookReceiptItem.objects.filter(receipt=receipt).select_related('book__subject')
    elif receipt.receipt_type == 'NOTEBOOKS':
        notebook_items = NotebookReceiptItem.objects.filter(receipt=receipt).select_related('notebook')
    elif receipt.receipt_type == 'SUPPLIES':
        supply_items = SupplyReceiptItem.objects.filter(receipt=receipt).select_related('supply')
    
    # حساب متوسط سعر الوحدة
    average_unit_cost = 0
    if receipt.total_items and receipt.total_items > 0:
        average_unit_cost = round(float(receipt.total_cost) / float(receipt.total_items), 2)
    
    context = {
        'receipt': receipt,
        'book_items': book_items,
        'notebook_items': notebook_items,
        'supply_items': supply_items,
        'average_unit_cost': average_unit_cost,
        'page_title': f'إيصال الاستلام {receipt.receipt_number}'
    }
    
    return render(request, 'books_inventory/receipt_detail.html', context)


# ============================================================================
# إدارة توزيعات الطلاب
# ============================================================================

@never_cache
@login_required
def student_distributions_list(request):
    """قائمة توزيعات الطلاب مع دعم AJAX والفلاتر"""
    
    # معاملات البحث والفلترة
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    verified_filter = request.GET.get('verified', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # الاستعلام الأساسي
    distributions = StudentDistribution.objects.select_related(
        'student', 'distributed_by'
    ).prefetch_related(
        'book_items__book',
        'notebook_items__notebook', 
        'supply_items__supply'
    ).order_by('-distribution_date')
    
    # تطبيق فلاتر البحث
    if search_query:
        distributions = distributions.filter(
            Q(student__name__icontains=search_query) |
            Q(student__national_number__icontains=search_query)
        )
    
    if status_filter:
        distributions = distributions.filter(status=status_filter)
    
    if verified_filter == 'verified':
        distributions = distributions.filter(first_installment_verified=True)
    elif verified_filter == 'not_verified':
        distributions = distributions.filter(first_installment_verified=False)
    
    if date_from:
        distributions = distributions.filter(distribution_date__gte=date_from)
    if date_to:
        distributions = distributions.filter(distribution_date__lte=date_to)
    
    # تقسيم الصفحات
    paginator = Paginator(distributions, 15)
    page_number = request.GET.get('page')
    
    try:
        distributions_page = paginator.page(page_number)
    except PageNotAnInteger:
        distributions_page = paginator.page(1)
    except EmptyPage:
        distributions_page = paginator.page(paginator.num_pages)
    
    # إذا كان طلب AJAX
    if request.GET.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('books_inventory/partials/distributions_table.html', {
            'distributions': distributions_page,
            'search_query': search_query,
            'status_filter': status_filter,
            'verified_filter': verified_filter,
            'date_from': date_from,
            'date_to': date_to,
        })
        
        return JsonResponse({
            'html': html,
            'count': paginator.count,
            'page': distributions_page.number,
            'total_pages': paginator.num_pages,
            'has_results': paginator.count > 0,
        })
    
    # طلب عادي
    context = {
        'distributions': distributions_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'verified_filter': verified_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': StudentDistribution.DISTRIBUTION_STATUS_CHOICES,
        'page_title': 'توزيعات الطلاب'
    }
    
    return render(request, 'books_inventory/distributions_list.html', context)


@never_cache
@login_required
def student_distribution_detail(request, pk):
    """تفاصيل توزيع طالب مع جميع العناصر الموزعة"""
    
    distribution = get_object_or_404(StudentDistribution, pk=pk)
    
    # العناصر الموزعة
    book_items = distribution.book_items.select_related('book__subject').all()
    notebook_items = distribution.notebook_items.select_related('notebook').all()
    supply_items = distribution.supply_items.select_related('supply').all()
    
    # إحصائيات أنواع العناصر
    total_books = book_items.count()
    total_notebooks = notebook_items.count()
    total_supplies = supply_items.count()
    
    # إحصائيات الكميات
    total_books_qty = sum(item.quantity_distributed for item in book_items)
    total_notebooks_qty = sum(item.quantity_distributed for item in notebook_items)
    total_supplies_qty = sum(item.quantity_distributed for item in supply_items)
    
    context = {
        'distribution': distribution,
        'book_items': book_items,
        'notebook_items': notebook_items,
        'supply_items': supply_items,
        'total_books': total_books,
        'total_notebooks': total_notebooks,
        'total_supplies': total_supplies,
        'total_books_qty': total_books_qty,
        'total_notebooks_qty': total_notebooks_qty,
        'total_supplies_qty': total_supplies_qty,
        'page_title': f'توزيع الطالب - {distribution.student.name}'
    }
    
    return render(request, 'books_inventory/student_distribution_detail.html', context)


@never_cache
@login_required
def create_student_distribution(request):
    """إنشاء توزيع جديد للطالب مع العناصر المختارة"""
    
    if request.method == 'POST':
        try:
            # استخراج البيانات من النموذج
            student_id = request.POST.get('student_id')
            selected_items_json = request.POST.get('selected_items')
            distribution_date = request.POST.get('distribution_date')
            status = request.POST.get('status', 'PENDING')
            notes = request.POST.get('notes', '')
            mark_as_distributed = request.POST.get('mark_as_distributed') == 'on'
            
            # التحقق من البيانات
            if not student_id or not selected_items_json:
                messages.error(request, 'بيانات غير كاملة')
                return redirect('books_inventory:create_distribution')
            
            # الحصول على الطالب
            student = get_object_or_404(Student, pk=student_id)
            
            # تحويل العناصر المختارة من JSON
            selected_items = json.loads(selected_items_json)
            
            # إنشاء التوزيع
            distribution = StudentDistribution.objects.create(
                student=student,
                distribution_date=distribution_date,
                distributed_by=request.user,
                status=status,
                notes=notes,
                first_installment_verified=True,  # بناءً على فلترة البحث
                verification_date=timezone.now()
            )
            
            total_items = 0
            
            # إضافة الكتب
            for book_data in selected_items.get('books', []):
                book = Book.objects.get(id=book_data['id'])
                BookDistributionItem.objects.create(
                    distribution=distribution,
                    book=book,
                    quantity_requested=book_data['quantity'],
                    quantity_distributed=book_data['quantity'] if mark_as_distributed else 0,
                    is_distributed=mark_as_distributed
                )
                total_items += book_data['quantity']
                
                # تحديث المخزون إذا تم وضع علامة التوزيع
                if mark_as_distributed:
                    book.distributed_count += book_data['quantity']
                    if hasattr(book, 'update_stock'):
                        book.update_stock()
            
            # إضافة الكراسات
            for notebook_data in selected_items.get('notebooks', []):
                notebook = Notebook.objects.get(id=notebook_data['id'])
                NotebookDistributionItem.objects.create(
                    distribution=distribution,
                    notebook=notebook,
                    quantity_requested=notebook_data['quantity'],
                    quantity_distributed=notebook_data['quantity'] if mark_as_distributed else 0,
                    is_distributed=mark_as_distributed
                )
                total_items += notebook_data['quantity']
                
                if mark_as_distributed:
                    notebook.distributed_count += notebook_data['quantity']
                    if hasattr(notebook, 'update_stock'):
                        notebook.update_stock()
            
            # إضافة الأدوات
            for supply_data in selected_items.get('supplies', []):
                supply = SchoolSupply.objects.get(id=supply_data['id'])
                SupplyDistributionItem.objects.create(
                    distribution=distribution,
                    supply=supply,
                    quantity_requested=supply_data['quantity'],
                    quantity_distributed=supply_data['quantity'] if mark_as_distributed else 0,
                    is_distributed=mark_as_distributed
                )
                total_items += supply_data['quantity']
                
                if mark_as_distributed:
                    supply.distributed_count += supply_data['quantity']
                    if hasattr(supply, 'update_stock'):
                        supply.update_stock()
            
            # تحديث إجمالي العناصر
            distribution.total_items = total_items
            distribution.save()
            
            messages.success(request, f'تم إنشاء التوزيع للطالب {student.name} بنجاح!')
            return redirect('books_inventory:student_distribution_detail', pk=distribution.pk)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
            return redirect('books_inventory:create_distribution')
    
    # طلب GET
    context = {
        'page_title': 'إنشاء توزيع جديد',
        'today': timezone.now().date()
    }
    
    return render(request, 'books_inventory/create_distribution.html', context)


@never_cache
@login_required
def verify_payment(request, pk):
    """تأكيد دفع القسط الأول للطالب"""
    
    distribution = get_object_or_404(StudentDistribution, pk=pk)
    
    if request.method == 'POST':
        try:
            notes = request.POST.get('notes', '').strip()
            
            distribution.first_installment_verified = True
            distribution.verification_date = timezone.now()
            distribution.verification_notes = notes
            distribution.save()
            
            messages.success(request, f'تم تأكيد دفع القسط الأول للطالب {distribution.student.name}')
            return redirect('books_inventory:student_distribution_detail', pk=distribution.pk)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'distribution': distribution,
        'page_title': f'تأكيد الدفع - {distribution.student.name}'
    }
    
    return render(request, 'books_inventory/verify_payment.html', context)


@never_cache
@login_required
def edit_distribution(request, pk):
    """تعديل توزيع طالب"""
    
    distribution = get_object_or_404(StudentDistribution, pk=pk)
    
    if request.method == 'POST':
        try:
            # تحديث حالة التوزيع
            status = request.POST.get('status')
            notes = request.POST.get('notes', '').strip()
            verification_notes = request.POST.get('verification_notes', '').strip()
            first_installment_verified = request.POST.get('first_installment_verified') == 'on'
            
            # تحديث الحقول
            if status:
                distribution.status = status
            
            distribution.notes = notes
            distribution.verification_notes = verification_notes
            
            # تحديث حالة التحقق من الدفع
            old_verified = distribution.first_installment_verified
            distribution.first_installment_verified = first_installment_verified
            
            # إذا تم التحقق لأول مرة، تسجيل تاريخ التحقق
            if first_installment_verified and not old_verified:
                distribution.verification_date = timezone.now()
            elif not first_installment_verified and old_verified:
                # إذا تم إلغاء التحقق، مسح تاريخ التحقق
                distribution.verification_date = None
                
            distribution.save()
            
            messages.success(request, f'تم تحديث توزيع الطالب {distribution.student.name} بنجاح')
            return redirect('books_inventory:student_distribution_detail', pk=distribution.pk)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'distribution': distribution,
        'status_choices': StudentDistribution.DISTRIBUTION_STATUS_CHOICES,
        'page_title': f'تعديل التوزيع - {distribution.student.name}'
    }
    
    return render(request, 'books_inventory/edit_distribution.html', context)


# ============================================================================
# وظائف البحث عن الطلاب وإدارة الدفع
# ============================================================================

@never_cache
@login_required
def student_search_for_distribution(request):
    """البحث عن الطلاب للتوزيع مع التحقق من حالة الدفع"""
    
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        results = []
        
        if len(query) >= 2:
            try:
                students = Student.objects.filter(
                    Q(name__icontains=query) |
                    Q(national_number__icontains=query),
                    is_active=True
                ).select_related('grade_level__education_level')[:10]
                
                for student in students:
                    # التحقق من دفع القسط الأول
                    first_installment_paid = Tuition.objects.filter(
                        student=student,
                        installment_number=1,
                        payment_status='PAID'
                    ).exists()
                    
                    # التحقق من وجود توزيع سابق اليوم
                    today_distribution = StudentDistribution.objects.filter(
                        student=student,
                        distribution_date=timezone.now().date()
                    ).exists()
                    
                    results.append({
                        'id': student.id,
                        'name': student.name,
                        'national_number': student.national_number,
                        'grade_level': getattr(student, 'grade_name', 'غير محدد'),
                        'education_level': getattr(student, 'education_level_name', 'غير محدد'),
                        'first_installment_paid': first_installment_paid,
                        'has_distribution_today': today_distribution,
                        'can_distribute': first_installment_paid and not today_distribution
                    })
                    
            except Exception as e:
                return JsonResponse({'error': str(e)})
        
        return JsonResponse({'results': results})
    
    return JsonResponse({'error': 'طريقة طلب غير صحيحة'})


@require_http_methods(["GET"])
@login_required
def student_search_api(request):
    """API للبحث عن الطلاب - AJAX"""
    
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({
            'error': 'يجب إدخال حرفين على الأقل للبحث',
            'results': []
        })
    
    try:
        # البحث في الطلاب النشطين
        students = Student.objects.filter(
            Q(name__icontains=query) | 
            Q(national_number__icontains=query) |
            Q(phone_number__icontains=query),
            is_active=True
        ).select_related(
            'grade_level__education_level',
            'academic_year'
        ).order_by('name')[:20]  # الحد الأقصى 20 نتيجة
        
        results = []
        for student in students:
            try:
                # حالة القسط الأول
                first_installment = Tuition.objects.filter(
                    student=student,
                    installment_number=1
                ).first()
                
                first_installment_paid = bool(
                    first_installment and first_installment.payment_status == 'PAID'
                )
                
                # التحقق من وجود توزيع اليوم
                has_distribution_today = StudentDistribution.objects.filter(
                    student=student,
                    distribution_date=timezone.now().date()
                ).exists()
                
                can_distribute = first_installment_paid and not has_distribution_today
                
                student_data = {
                    'id': student.id,
                    'name': student.name,
                    'national_number': student.national_number,
                    'phone_number': student.phone_number or '',
                    'grade_level': getattr(student.grade_level, 'name', 'غير محدد') if hasattr(student, 'grade_level') and student.grade_level else 'غير محدد',
                    'education_level': getattr(student.grade_level.education_level, 'name', 'غير محدد') if (hasattr(student, 'grade_level') and student.grade_level and hasattr(student.grade_level, 'education_level') and student.grade_level.education_level) else 'غير محدد',
                    'first_installment_paid': first_installment_paid,
                    'can_distribute': can_distribute,
                    'has_distribution_today': has_distribution_today
                }
                
                results.append(student_data)
                
            except Exception as e:
                print(f"خطأ في معالجة بيانات الطالب {student.name}: {e}")
                continue
        
        return JsonResponse({
            'results': results,
            'total_count': len(results)
        })
        
    except Exception as e:
        print(f"خطأ في API البحث: {e}")
        return JsonResponse({
            'error': f'حدث خطأ في البحث: {str(e)}',
            'results': []
        })


@never_cache
@login_required
def student_search_view(request):
    """البحث عن الطلاب (للعرض فقط - موظف المخزن)"""
    
    students = []
    search_query = ''
    total_results = 0
    
    if request.method == 'GET' and 'search' in request.GET:
        search_query = request.GET.get('search', '').strip()
        
        if search_query and len(search_query) >= 2:
            try:
                # البحث في الطلاب النشطين
                students_queryset = Student.objects.filter(
                    Q(name__icontains=search_query) | 
                    Q(national_number__icontains=search_query) |
                    Q(phone_number__icontains=search_query),
                    is_active=True
                ).select_related(
                    'grade_level__education_level',
                    'academic_year'
                ).order_by('name')
                
                total_results = students_queryset.count()
                
                # تقسيم الصفحات
                paginator = Paginator(students_queryset, 15)
                page_number = request.GET.get('page')
                
                try:
                    students = paginator.page(page_number)
                except PageNotAnInteger:
                    students = paginator.page(1)
                except EmptyPage:
                    students = paginator.page(paginator.num_pages)
                
                # إضافة بيانات المدفوعات لكل طالب
                for student in students:
                    try:
                        # حالة القسط الأول
                        first_installment = Tuition.objects.filter(
                            student=student,
                            installment_number=1
                        ).first()
                        
                        student.first_installment_status = 'مدفوع' if (
                            first_installment and first_installment.payment_status == 'PAID'
                        ) else 'غير مدفوع'
                        
                        student.first_installment_date = first_installment.payment_date if (
                            first_installment and first_installment.payment_status == 'PAID'
                        ) else None
                        
                        # إجمالي المدفوعات والمستحقات
                        student.payment_summary = {
                            'total_fees': getattr(student, 'total_fees', 0) or 0,
                            'total_payments': getattr(student, 'total_payments', 0) or 0,
                            'total_owed': getattr(student, 'total_owed', 0) or 0
                        }
                        
                        # حالة التوزيع السابقة
                        latest_distribution = StudentDistribution.objects.filter(
                            student=student
                        ).order_by('-distribution_date').first()
                        
                        student.latest_distribution = latest_distribution
                        
                    except Exception as e:
                        print(f"خطأ في البحث عن بيانات الطالب {student.name}: {e}")
                        student.first_installment_status = 'غير معروف'
                        student.payment_summary = {'total_fees': 0, 'total_payments': 0, 'total_owed': 0}
                        student.latest_distribution = None
                        
            except Exception as e:
                print(f"خطأ في البحث عن الطلاب: {e}")
                messages.error(request, f'حدث خطأ أثناء البحث: {str(e)}')
                students = []
    
    context = {
        'students': students,
        'search_query': search_query,
        'total_results': total_results,
        'page_title': 'البحث عن الطلاب'
    }
    
    return render(request, 'books_inventory/student_search.html', context)


# ============================================================================
# إدارة النواقص والتقارير
# ============================================================================

@never_cache
@login_required
def shortages_list(request):
    """قائمة النواقص في المخزون مع الفلاتر"""
    
    # معاملات الفلترة
    status_filter = request.GET.get('status', '')
    item_type_filter = request.GET.get('item_type', '')
    priority_filter = request.GET.get('priority', '')
    
    # الاستعلام الأساسي
    shortages = StockShortage.objects.select_related(
        'reported_by', 'book__subject', 'notebook', 'supply'
    ).order_by('-reported_date')
    
    # تطبيق الفلاتر
    if status_filter:
        shortages = shortages.filter(status=status_filter)
    
    if item_type_filter:
        shortages = shortages.filter(item_type=item_type_filter)
    
    if priority_filter:
        shortages = shortages.filter(priority=priority_filter)
    
    # تقسيم الصفحات
    paginator = Paginator(shortages, 20)
    page_number = request.GET.get('page')
    
    try:
        shortages_page = paginator.page(page_number)
    except PageNotAnInteger:
        shortages_page = paginator.page(1)
    except EmptyPage:
        shortages_page = paginator.page(paginator.num_pages)
    
    context = {
        'shortages': shortages_page,
        'status_filter': status_filter,
        'item_type_filter': item_type_filter,
        'priority_filter': priority_filter,
        'status_choices': StockShortage.SHORTAGE_STATUS_CHOICES,
        'item_type_choices': StockShortage.ITEM_TYPE_CHOICES,
        'priority_choices': [('HIGH', 'عالي'), ('MEDIUM', 'متوسط'), ('LOW', 'منخفض')],
        'page_title': 'النواقص في المخزون'
    }
    
    return render(request, 'books_inventory/shortages_list.html', context)


@csrf_protect
@require_POST
@login_required
def report_shortage(request):
    """الإبلاغ عن نقص في المخزون"""
    
    try:
        # استخراج البيانات
        item_type = request.POST.get('item_type')
        item_id = request.POST.get('item_id')
        required_quantity = int(request.POST.get('required_quantity', 0))
        priority = request.POST.get('priority', 'MEDIUM')
        notes = request.POST.get('notes', '')
        
        # الحصول على العنصر والمخزون الحالي
        current_stock = 0
        item_name = ''
        book = notebook = supply = None
        
        if item_type == 'BOOK':
            book = get_object_or_404(Book, pk=item_id)
            current_stock = book.available_stock
            item_name = book.title
        elif item_type == 'NOTEBOOK':
            notebook = get_object_or_404(Notebook, pk=item_id)
            current_stock = notebook.available_stock
            item_name = notebook.name
        elif item_type == 'SUPPLY':
            supply = get_object_or_404(SchoolSupply, pk=item_id)
            current_stock = supply.available_stock
            item_name = supply.name
        
        shortage_quantity = max(0, required_quantity - current_stock)
        
        if shortage_quantity > 0:
            # إنشاء بلاغ النقص
            shortage = StockShortage.objects.create(
                item_type=item_type,
                item_name=item_name,
                book=book,
                notebook=notebook,
                supply=supply,
                current_stock=current_stock,
                required_quantity=required_quantity,
                shortage_quantity=shortage_quantity,
                priority=priority,
                reported_by=request.user,
                notes=notes
            )
            
            return JsonResponse({
                'success': True,
                'message': f'تم الإبلاغ عن نقص في {item_name} بنجاح',
                'shortage_id': shortage.id
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'المخزون الحالي كافي للكمية المطلوبة'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


@never_cache
@login_required
def inventory_reports(request):
    """تقارير المخزن الشاملة مع الإحصائيات"""
    
    try:
        # إحصائيات الكتب
        books_stats = {
            'total_books': Book.objects.filter(is_active=True).count(),
            'total_stock': Book.objects.filter(is_active=True).aggregate(Sum('total_stock'))['total_stock__sum'] or 0,
            'available_stock': Book.objects.filter(is_active=True).aggregate(Sum('available_stock'))['available_stock__sum'] or 0,
            'distributed': Book.objects.filter(is_active=True).aggregate(Sum('distributed_count'))['distributed_count__sum'] or 0,
            'damaged': Book.objects.filter(is_active=True).aggregate(Sum('damaged_count'))['damaged_count__sum'] or 0,
            'low_stock_count': Book.objects.filter(is_active=True, available_stock__lte=F('minimum_stock_level')).count()
        }
        
        # إحصائيات الكراسات
        notebooks_stats = {
            'total_notebooks': Notebook.objects.filter(is_active=True).count(),
            'total_stock': Notebook.objects.filter(is_active=True).aggregate(Sum('total_stock'))['total_stock__sum'] or 0,
            'available_stock': Notebook.objects.filter(is_active=True).aggregate(Sum('available_stock'))['available_stock__sum'] or 0,
            'distributed': Notebook.objects.filter(is_active=True).aggregate(Sum('distributed_count'))['distributed_count__sum'] or 0,
            'damaged': Notebook.objects.filter(is_active=True).aggregate(Sum('damaged_count'))['damaged_count__sum'] or 0,
            'low_stock_count': Notebook.objects.filter(is_active=True, available_stock__lte=F('minimum_stock_level')).count()
        }
        
        # إحصائيات الأدوات المدرسية
        supplies_stats = {
            'total_supplies': SchoolSupply.objects.filter(is_active=True).count(),
            'total_stock': SchoolSupply.objects.filter(is_active=True).aggregate(Sum('total_stock'))['total_stock__sum'] or 0,
            'available_stock': SchoolSupply.objects.filter(is_active=True).aggregate(Sum('available_stock'))['available_stock__sum'] or 0,
            'distributed': SchoolSupply.objects.filter(is_active=True).aggregate(Sum('distributed_count'))['distributed_count__sum'] or 0,
            'damaged': SchoolSupply.objects.filter(is_active=True).aggregate(Sum('damaged_count'))['damaged_count__sum'] or 0,
            'low_stock_count': SchoolSupply.objects.filter(is_active=True, available_stock__lte=F('minimum_stock_level')).count()
        }
        
        # إحصائيات التوزيع
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        distribution_stats = {
            'today': StudentDistribution.objects.filter(distribution_date=today).count(),
            'this_week': StudentDistribution.objects.filter(distribution_date__gte=week_ago).count(),
            'this_month': StudentDistribution.objects.filter(distribution_date__gte=month_ago).count(),
            'completed': StudentDistribution.objects.filter(status='COMPLETED').count(),
            'pending': StudentDistribution.objects.filter(status='PENDING').count()
        }
        
        # إحصائيات النواقص
        shortage_stats = {
            'total_shortages': StockShortage.objects.count(),
            'pending_shortages': StockShortage.objects.filter(status__in=['REPORTED', 'ACKNOWLEDGED']).count(),
            'high_priority': StockShortage.objects.filter(priority='HIGH', status__in=['REPORTED', 'ACKNOWLEDGED']).count()
        }
        
        # أحدث الأنشطة
        recent_receipts = StockReceipt.objects.select_related('supplier').order_by('-receipt_date')[:10]
        recent_distributions = StudentDistribution.objects.select_related('student').order_by('-distribution_date')[:10]
        recent_shortages = StockShortage.objects.order_by('-reported_date')[:10]
        
    except Exception as e:
        print(f"خطأ في تقارير المخزن: {e}")
        books_stats = notebooks_stats = supplies_stats = distribution_stats = shortage_stats = {}
        recent_receipts = recent_distributions = recent_shortages = []
    
    context = {
        'books_stats': books_stats,
        'notebooks_stats': notebooks_stats,
        'supplies_stats': supplies_stats,
        'distribution_stats': distribution_stats,
        'shortage_stats': shortage_stats,
        'recent_receipts': recent_receipts,
        'recent_distributions': recent_distributions,
        'recent_shortages': recent_shortages,
        'today': today,
        'page_title': 'تقارير المخزن'
    }
    
    return render(request, 'books_inventory/inventory_reports.html', context)


@never_cache
@login_required
def export_inventory_report(request, export_type):
    """تصدير تقرير المخزن إلى CSV حسب النوع المطلوب"""
    
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="inventory_report_{export_type}_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
    
    writer = csv.writer(response)
    
    try:
        if export_type == 'books':
            # تصدير تقرير الكتب
            writer.writerow([
                'عنوان الكتاب', 'المادة الدراسية', 'نوع الكتاب', 'الترم',
                'إجمالي المخزون', 'المتاح للتوزيع', 'الموزع', 'التالف', 
                'الحد الأدنى', 'حالة المخزون', 'تكلفة الوحدة', 'تاريخ الإضافة'
            ])
            
            books = Book.objects.filter(is_active=True).select_related('subject').order_by('subject__name', 'title')
            
            for book in books:
                # تحديد حالة المخزون
                if book.available_stock <= 0:
                    stock_status = 'نفد المخزون'
                elif book.available_stock <= book.minimum_stock_level:
                    stock_status = 'مخزون منخفض'
                else:
                    stock_status = 'متوفر'
                
                writer.writerow([
                    book.title,
                    book.subject.name,
                    book.get_book_type_display(),
                    book.get_term_display(),
                    book.total_stock,
                    book.available_stock,
                    book.distributed_count,
                    book.damaged_count,
                    book.minimum_stock_level,
                    stock_status,
                    float(book.cost_price),
                    book.created_at.strftime('%Y-%m-%d')
                ])
        
        elif export_type == 'notebooks':
            # تصدير تقرير الكراسات
            writer.writerow([
                'اسم الكراسة', 'النوع', 'الحجم', 'عدد الصفحات',
                'إجمالي المخزون', 'المتاح للتوزيع', 'الموزع', 'التالف', 
                'الحد الأدنى', 'حالة المخزون', 'تكلفة الوحدة', 'تاريخ الإضافة'
            ])
            
            notebooks = Notebook.objects.filter(is_active=True).order_by('notebook_type', 'name')
            
            for notebook in notebooks:
                # تحديد حالة المخزون
                if notebook.available_stock <= 0:
                    stock_status = 'نفد المخزون'
                elif notebook.available_stock <= notebook.minimum_stock_level:
                    stock_status = 'مخزون منخفض'
                else:
                    stock_status = 'متوفر'
                
                writer.writerow([
                    notebook.name,
                    notebook.get_notebook_type_display(),
                    notebook.get_size_display(),
                    notebook.pages_count,
                    notebook.total_stock,
                    notebook.available_stock,
                    notebook.distributed_count,
                    notebook.damaged_count,
                    notebook.minimum_stock_level,
                    stock_status,
                    float(notebook.cost_price),
                    notebook.created_at.strftime('%Y-%m-%d')
                ])
        
        elif export_type == 'supplies':
            # تصدير تقرير الأدوات المدرسية
            writer.writerow([
                'اسم الأداة', 'الفئة', 'الوحدة', 'الوصف',
                'إجمالي المخزون', 'المتاح للتوزيع', 'الموزع', 'التالف', 
                'الحد الأدنى', 'حالة المخزون', 'تكلفة الوحدة', 'تاريخ الإضافة'
            ])
            
            supplies = SchoolSupply.objects.filter(is_active=True).order_by('category', 'name')
            
            for supply in supplies:
                # تحديد حالة المخزون
                if supply.available_stock <= 0:
                    stock_status = 'نفد المخزون'
                elif supply.available_stock <= supply.minimum_stock_level:
                    stock_status = 'مخزون منخفض'
                else:
                    stock_status = 'متوفر'
                
                writer.writerow([
                    supply.name,
                    supply.get_category_display(),
                    supply.unit,
                    supply.description[:100] if supply.description else '',
                    supply.total_stock,
                    supply.available_stock,
                    supply.distributed_count,
                    supply.damaged_count,
                    supply.minimum_stock_level,
                    stock_status,
                    float(supply.cost_price),
                    supply.created_at.strftime('%Y-%m-%d')
                ])
        
        elif export_type == 'distributions':
            # تصدير تقرير التوزيعات
            writer.writerow([
                'اسم الطالب', 'الرقم القومي', 'الصف الدراسي', 'تاريخ التوزيع',
                'إجمالي العناصر', 'عدد الكتب', 'عدد الكراسات', 'عدد الأدوات',
                'القسط الأول مدفوع', 'الحالة', 'موزع بواسطة', 'ملاحظات'
            ])
            
            distributions = StudentDistribution.objects.select_related(
                'student', 'distributed_by'
            ).prefetch_related(
                'book_items', 'notebook_items', 'supply_items'
            ).order_by('-distribution_date')
            
            for dist in distributions:
                # حساب عدد العناصر حسب النوع
                books_count = dist.book_items.count()
                notebooks_count = dist.notebook_items.count()
                supplies_count = dist.supply_items.count()
                
                writer.writerow([
                    dist.student.name,
                    dist.student.national_number or '',
                    getattr(dist.student, 'grade_name', 'غير محدد'),
                    dist.distribution_date.strftime('%Y-%m-%d'),
                    dist.total_items,
                    books_count,
                    notebooks_count,
                    supplies_count,
                    'نعم' if dist.first_installment_verified else 'لا',
                    dist.get_status_display(),
                    dist.distributed_by.get_full_name() or dist.distributed_by.username,
                    dist.notes[:100] if dist.notes else ''
                ])
        
        elif export_type == 'receipts':
            # تصدير تقرير الاستلامات
            writer.writerow([
                'رقم الإيصال', 'المورد', 'نوع الإيصال', 'تاريخ الاستلام',
                'رقم الفاتورة', 'إجمالي العناصر', 'العناصر التالفة', 
                'إجمالي التكلفة', 'استلم بواسطة', 'ملاحظات'
            ])
            
            receipts = StockReceipt.objects.select_related(
                'supplier', 'received_by'
            ).order_by('-receipt_date')
            
            for receipt in receipts:
                writer.writerow([
                    receipt.receipt_number,
                    receipt.supplier.name,
                    receipt.get_receipt_type_display(),
                    receipt.receipt_date.strftime('%Y-%m-%d'),
                    receipt.invoice_number or '',
                    receipt.total_items,
                    receipt.damaged_items,
                    float(receipt.total_cost),
                    receipt.received_by.get_full_name() or receipt.received_by.username,
                    receipt.notes[:100] if receipt.notes else ''
                ])
        
        elif export_type == 'shortages':
            # تصدير تقرير النواقص
            writer.writerow([
                'نوع العنصر', 'اسم العنصر', 'المخزون الحالي', 'الكمية المطلوبة',
                'كمية النقص', 'الأولوية', 'الحالة', 'تاريخ الإبلاغ', 
                'المُبلغ', 'ملاحظات'
            ])
            
            shortages = StockShortage.objects.select_related('reported_by').order_by('-reported_date')
            
            for shortage in shortages:
                writer.writerow([
                    shortage.get_item_type_display(),
                    shortage.item_name,
                    shortage.current_stock,
                    shortage.required_quantity,
                    shortage.shortage_quantity,
                    shortage.get_priority_display(),
                    shortage.get_status_display(),
                    shortage.reported_date.strftime('%Y-%m-%d'),
                    shortage.reported_by.get_full_name() or shortage.reported_by.username,
                    shortage.notes[:100] if shortage.notes else ''
                ])
        
        elif export_type == 'low_stock':
            # تصدير تقرير المخزون المنخفض
            writer.writerow([
                'نوع العنصر', 'اسم العنصر', 'المادة/الفئة', 'المخزون الحالي',
                'الحد الأدنى', 'نسبة المخزون', 'الحالة', 'آخر استلام', 'آخر توزيع'
            ])
            
            # الكتب منخفضة المخزون
            low_books = Book.objects.filter(
                is_active=True,
                available_stock__lte=F('minimum_stock_level')
            ).select_related('subject')
            
            for book in low_books:
                # آخر استلام
                last_receipt = BookReceiptItem.objects.filter(
                    book=book
                ).order_by('-receipt__receipt_date').first()
                last_receipt_date = last_receipt.receipt.receipt_date.strftime('%Y-%m-%d') if last_receipt else 'لا يوجد'
                
                # آخر توزيع
                last_distribution = BookDistributionItem.objects.filter(
                    book=book
                ).order_by('-distribution__distribution_date').first()
                last_dist_date = last_distribution.distribution.distribution_date.strftime('%Y-%m-%d') if last_distribution else 'لا يوجد'
                
                # نسبة المخزون
                stock_percentage = (book.available_stock / book.minimum_stock_level * 100) if book.minimum_stock_level > 0 else 0
                
                writer.writerow([
                    'كتاب',
                    book.title,
                    book.subject.name,
                    book.available_stock,
                    book.minimum_stock_level,
                    f"{stock_percentage:.1f}%",
                    'نفد المخزون' if book.available_stock <= 0 else 'مخزون منخفض',
                    last_receipt_date,
                    last_dist_date
                ])
            
            # الكراسات منخفضة المخزون
            low_notebooks = Notebook.objects.filter(
                is_active=True,
                available_stock__lte=F('minimum_stock_level')
            )
            
            for notebook in low_notebooks:
                last_receipt = NotebookReceiptItem.objects.filter(
                    notebook=notebook
                ).order_by('-receipt__receipt_date').first()
                last_receipt_date = last_receipt.receipt.receipt_date.strftime('%Y-%m-%d') if last_receipt else 'لا يوجد'
                
                last_distribution = NotebookDistributionItem.objects.filter(
                    notebook=notebook
                ).order_by('-distribution__distribution_date').first()
                last_dist_date = last_distribution.distribution.distribution_date.strftime('%Y-%m-%d') if last_distribution else 'لا يوجد'
                
                stock_percentage = (notebook.available_stock / notebook.minimum_stock_level * 100) if notebook.minimum_stock_level > 0 else 0
                
                writer.writerow([
                    'كراسة',
                    notebook.name,
                    notebook.get_notebook_type_display(),
                    notebook.available_stock,
                    notebook.minimum_stock_level,
                    f"{stock_percentage:.1f}%",
                    'نفد المخزون' if notebook.available_stock <= 0 else 'مخزون منخفض',
                    last_receipt_date,
                    last_dist_date
                ])
            
            # الأدوات منخفضة المخزون
            low_supplies = SchoolSupply.objects.filter(
                is_active=True,
                available_stock__lte=F('minimum_stock_level')
            )
            
            for supply in low_supplies:
                last_receipt = SupplyReceiptItem.objects.filter(
                    supply=supply
                ).order_by('-receipt__receipt_date').first()
                last_receipt_date = last_receipt.receipt.receipt_date.strftime('%Y-%m-%d') if last_receipt else 'لا يوجد'
                
                last_distribution = SupplyDistributionItem.objects.filter(
                    supply=supply
                ).order_by('-distribution__distribution_date').first()
                last_dist_date = last_distribution.distribution.distribution_date.strftime('%Y-%m-%d') if last_distribution else 'لا يوجد'
                
                stock_percentage = (supply.available_stock / supply.minimum_stock_level * 100) if supply.minimum_stock_level > 0 else 0
                
                writer.writerow([
                    'أداة مدرسية',
                    supply.name,
                    supply.get_category_display(),
                    supply.available_stock,
                    supply.minimum_stock_level,
                    f"{stock_percentage:.1f}%",
                    'نفد المخزون' if supply.available_stock <= 0 else 'مخزون منخفض',
                    last_receipt_date,
                    last_dist_date
                ])
        
        elif export_type == 'complete':
            # تصدير تقرير شامل مختصر
            writer.writerow([
                'نوع العنصر', 'اسم العنصر', 'المادة/الفئة/النوع', 
                'إجمالي المخزون', 'المتاح للتوزيع', 'الموزع', 'التالف',
                'الحد الأدنى', 'حالة المخزون', 'تكلفة الوحدة'
            ])
            
            # إضافة الكتب
            books = Book.objects.filter(is_active=True).select_related('subject')
            for book in books:
                stock_status = 'نفد المخزون' if book.available_stock <= 0 else ('مخزون منخفض' if book.available_stock <= book.minimum_stock_level else 'متوفر')
                writer.writerow([
                    'كتاب', book.title, book.subject.name,
                    book.total_stock, book.available_stock, book.distributed_count, book.damaged_count,
                    book.minimum_stock_level, stock_status, float(book.cost_price)
                ])
            
            # إضافة الكراسات
            notebooks = Notebook.objects.filter(is_active=True)
            for notebook in notebooks:
                stock_status = 'نفد المخزون' if notebook.available_stock <= 0 else ('مخزون منخفض' if notebook.available_stock <= notebook.minimum_stock_level else 'متوفر')
                writer.writerow([
                    'كراسة', notebook.name, notebook.get_notebook_type_display(),
                    notebook.total_stock, notebook.available_stock, notebook.distributed_count, notebook.damaged_count,
                    notebook.minimum_stock_level, stock_status, float(notebook.cost_price)
                ])
            
            # إضافة الأدوات المدرسية
            supplies = SchoolSupply.objects.filter(is_active=True)
            for supply in supplies:
                stock_status = 'نفد المخزون' if supply.available_stock <= 0 else ('مخزون منخفض' if supply.available_stock <= supply.minimum_stock_level else 'متوفر')
                writer.writerow([
                    'أداة مدرسية', supply.name, supply.get_category_display(),
                    supply.total_stock, supply.available_stock, supply.distributed_count, supply.damaged_count,
                    supply.minimum_stock_level, stock_status, float(supply.cost_price)
                ])
        
        else:
            # نوع تصدير غير معروف
            writer.writerow(['خطأ', 'نوع التصدير غير معروف'])
    
    except Exception as e:
        print(f"خطأ في تصدير التقرير: {e}")
        writer.writerow(['خطأ', f'حدث خطأ في تصدير التقرير: {str(e)}'])
    
    return response


# ============================================================================
# APIs للحصول على البيانات
# ============================================================================

@never_cache
@login_required
def get_items_for_grade(request):
    """جلب العناصر المناسبة للصف الدراسي مع تصنيف أفضل للمواد"""
    
    grade_level_id = request.GET.get('grade_level_id')
    if not grade_level_id:
        return JsonResponse({'error': 'معرف الصف مطلوب'})
    
    try:
        grade_level = GradeLevel.objects.get(id=grade_level_id)
        education_level = grade_level.education_level
        
        # جلب المواد المناسبة للصف أولاً
        relevant_subjects = Subject.objects.filter(
            Q(grade_levels=grade_level) | Q(education_levels=education_level),
            is_active=True
        ).distinct()
        
        # جلب الكتب - الأولوية للمواد المرتبطة بالصف
        books = Book.objects.filter(
            grade_levels=grade_level,
            is_active=True,
            available_stock__gt=0
        ).select_related('subject').order_by('subject__name', 'title')
        
        # جلب الكراسات المناسبة
        notebooks = Notebook.objects.filter(
            grade_levels=grade_level,
            is_active=True,
            available_stock__gt=0
        ).order_by('name')
        
        # جلب الأدوات المناسبة
        supplies = SchoolSupply.objects.filter(
            grade_levels=grade_level,
            is_active=True,
            available_stock__gt=0
        ).order_by('category', 'name')
        
        # تجميع الكتب حسب المادة
        books_by_subject = {}
        for book in books:
            subject_name = book.subject.name
            if subject_name not in books_by_subject:
                books_by_subject[subject_name] = []
            books_by_subject[subject_name].append({
                'id': book.id,
                'title': book.title,
                'subject': book.subject.name,
                'subject_color': book.subject.color,
                'book_type': book.get_book_type_display(),
                'available_stock': book.available_stock,
                'term': book.get_term_display(),
                'description': book.description[:100] if book.description else '',
            })
        
        # تحويل البيانات للإرسال
        books_data = []
        for subject, subject_books in books_by_subject.items():
            books_data.extend(subject_books)
        
        notebooks_data = [
            {
                'id': notebook.id,
                'name': notebook.name,
                'type': notebook.get_notebook_type_display(),
                'size': notebook.get_size_display(),
                'pages_count': notebook.pages_count,
                'available_stock': notebook.available_stock,
            }
            for notebook in notebooks
        ]
        
        supplies_data = [
            {
                'id': supply.id,
                'name': supply.name,
                'category': supply.get_category_display(),
                'unit': supply.unit,
                'available_stock': supply.available_stock,
                'description': supply.description[:100] if supply.description else '',
            }
            for supply in supplies
        ]
        
        return JsonResponse({
            'success': True,
            'grade_level': {
                'id': grade_level.id,
                'name': grade_level.name,
                'education_level': grade_level.education_level.name
            },
            'relevant_subjects': [
                {
                    'id': subject.id,
                    'name': subject.name,
                    'color': subject.color,
                    'books_count': subject.get_books_for_grade(grade_level).count() if hasattr(subject, 'get_books_for_grade') else 0
                }
                for subject in relevant_subjects
            ],
            'books': books_data,
            'books_by_subject': books_by_subject,
            'notebooks': notebooks_data,
            'supplies': supplies_data,
            'total_items': len(books_data) + len(notebooks_data) + len(supplies_data)
        })
        
    except GradeLevel.DoesNotExist:
        return JsonResponse({'error': 'الصف الدراسي غير موجود'})
    except Exception as e:
        return JsonResponse({'error': f'حدث خطأ: {str(e)}'})


# ============================================================================
# دوال إضافة وحذف عناصر التوزيع (للتعديل)
# ============================================================================

@never_cache
@login_required
def add_book_to_distribution(request, pk):
    """إضافة كتاب لتوزيع طالب"""
    
    distribution = get_object_or_404(StudentDistribution, pk=pk)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            book_id = data.get('book_id')
            quantity_requested = int(data.get('quantity_requested', 1))
            quantity_distributed = int(data.get('quantity_distributed', 0))
            is_distributed = data.get('is_distributed', False)
            notes = data.get('notes', '')
            
            book = get_object_or_404(Book, pk=book_id)
            
            # التحقق من عدم تكرار الكتاب
            if BookDistributionItem.objects.filter(distribution=distribution, book=book).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'هذا الكتاب موجود بالفعل في التوزيع'
                })
            
            # التحقق من توفر المخزون
            if quantity_distributed > book.available_stock:
                return JsonResponse({
                    'success': False,
                    'error': f'الكمية المطلوبة ({quantity_distributed}) أكبر من المتاح ({book.available_stock})'
                })
            
            # إنشاء عنصر التوزيع
            book_item = BookDistributionItem.objects.create(
                distribution=distribution,
                book=book,
                quantity_requested=quantity_requested,
                quantity_distributed=quantity_distributed,
                is_distributed=is_distributed,
                notes=notes
            )
            
            # تحديث إجمالي العناصر
            distribution.total_items = (
                distribution.book_items.count() +
                distribution.notebook_items.count() +
                distribution.supply_items.count()
            )
            distribution.save()
            
            return JsonResponse({
                'success': True,
                'message': f'تم إضافة الكتاب "{book.title}" بنجاح'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'طريقة الطلب غير صحيحة'})


@never_cache
@login_required
def add_notebook_to_distribution(request, pk):
    """إضافة كراسة لتوزيع طالب"""
    
    distribution = get_object_or_404(StudentDistribution, pk=pk)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            notebook_id = data.get('notebook_id')
            quantity_requested = int(data.get('quantity_requested', 1))
            quantity_distributed = int(data.get('quantity_distributed', 0))
            is_distributed = data.get('is_distributed', False)
            notes = data.get('notes', '')
            
            notebook = get_object_or_404(Notebook, pk=notebook_id)
            
            # التحقق من عدم تكرار الكراسة
            if NotebookDistributionItem.objects.filter(distribution=distribution, notebook=notebook).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'هذه الكراسة موجودة بالفعل في التوزيع'
                })
            
            # التحقق من توفر المخزون
            if quantity_distributed > notebook.available_stock:
                return JsonResponse({
                    'success': False,
                    'error': f'الكمية المطلوبة ({quantity_distributed}) أكبر من المتاح ({notebook.available_stock})'
                })
            
            # إنشاء عنصر التوزيع
            notebook_item = NotebookDistributionItem.objects.create(
                distribution=distribution,
                notebook=notebook,
                quantity_requested=quantity_requested,
                quantity_distributed=quantity_distributed,
                is_distributed=is_distributed,
                notes=notes
            )
            
            # تحديث إجمالي العناصر
            distribution.total_items = (
                distribution.book_items.count() +
                distribution.notebook_items.count() +
                distribution.supply_items.count()
            )
            distribution.save()
            
            return JsonResponse({
                'success': True,
                'message': f'تم إضافة الكراسة "{notebook.name}" بنجاح'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'طريقة الطلب غير صحيحة'})


@never_cache
@login_required
def add_supply_to_distribution(request, pk):
    """إضافة أداة مدرسية لتوزيع طالب"""
    
    distribution = get_object_or_404(StudentDistribution, pk=pk)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            supply_id = data.get('supply_id')
            quantity_requested = int(data.get('quantity_requested', 1))
            quantity_distributed = int(data.get('quantity_distributed', 0))
            is_distributed = data.get('is_distributed', False)
            notes = data.get('notes', '')
            
            supply = get_object_or_404(SchoolSupply, pk=supply_id)
            
            # التحقق من عدم تكرار الأداة
            if SupplyDistributionItem.objects.filter(distribution=distribution, supply=supply).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'هذه الأداة موجودة بالفعل في التوزيع'
                })
            
            # التحقق من توفر المخزون
            if quantity_distributed > supply.available_stock:
                return JsonResponse({
                    'success': False,
                    'error': f'الكمية المطلوبة ({quantity_distributed}) أكبر من المتاح ({supply.available_stock})'
                })
            
            # إنشاء عنصر التوزيع
            supply_item = SupplyDistributionItem.objects.create(
                distribution=distribution,
                supply=supply,
                quantity_requested=quantity_requested,
                quantity_distributed=quantity_distributed,
                is_distributed=is_distributed,
                notes=notes
            )
            
            # تحديث إجمالي العناصر
            distribution.total_items = (
                distribution.book_items.count() +
                distribution.notebook_items.count() +
                distribution.supply_items.count()
            )
            distribution.save()
            
            return JsonResponse({
                'success': True,
                'message': f'تم إضافة الأداة "{supply.name}" بنجاح'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'طريقة الطلب غير صحيحة'})


@never_cache
@login_required
def delete_book_item(request, item_id):
    """حذف عنصر كتاب من التوزيع"""
    
    book_item = get_object_or_404(BookDistributionItem, pk=item_id)
    
    if request.method == 'POST':
        try:
            distribution = book_item.distribution
            book_title = book_item.book.title
            book_item.delete()
            
            # تحديث إجمالي العناصر
            distribution.total_items = (
                distribution.book_items.count() +
                distribution.notebook_items.count() +
                distribution.supply_items.count()
            )
            distribution.save()
            
            return JsonResponse({
                'success': True,
                'message': f'تم حذف الكتاب "{book_title}" من التوزيع'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'طريقة الطلب غير صحيحة'})


@never_cache
@login_required
def delete_notebook_item(request, item_id):
    """حذف عنصر كراسة من التوزيع"""
    
    notebook_item = get_object_or_404(NotebookDistributionItem, pk=item_id)
    
    if request.method == 'POST':
        try:
            distribution = notebook_item.distribution
            notebook_name = notebook_item.notebook.name
            notebook_item.delete()
            
            # تحديث إجمالي العناصر
            distribution.total_items = (
                distribution.book_items.count() +
                distribution.notebook_items.count() +
                distribution.supply_items.count()
            )
            distribution.save()
            
            return JsonResponse({
                'success': True,
                'message': f'تم حذف الكراسة "{notebook_name}" من التوزيع'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'طريقة الطلب غير صحيحة'})


@never_cache
@login_required
def delete_supply_item(request, item_id):
    """حذف عنصر أداة مدرسية من التوزيع"""
    
    supply_item = get_object_or_404(SupplyDistributionItem, pk=item_id)
    
    if request.method == 'POST':
        try:
            distribution = supply_item.distribution
            supply_name = supply_item.supply.name
            supply_item.delete()
            
            # تحديث إجمالي العناصر
            distribution.total_items = (
                distribution.book_items.count() +
                distribution.notebook_items.count() +
                distribution.supply_items.count()
            )
            distribution.save()
            
            return JsonResponse({
                'success': True,
                'message': f'تم حذف الأداة "{supply_name}" من التوزيع'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'طريقة الطلب غير صحيحة'})

# ============================================================================
# دوال إضافية مفقودة لإيصالات الاستلام
# ============================================================================

@never_cache
@login_required
def edit_receipt(request, pk):
    """تعديل إيصال استلام موجود"""
    
    receipt = get_object_or_404(StockReceipt, pk=pk)
    
    if request.method == 'POST':
        try:
            # تحديث البيانات الأساسية
            supplier_id = request.POST.get('supplier')
            receipt_date = request.POST.get('receipt_date')
            invoice_number = request.POST.get('invoice_number', '').strip()
            notes = request.POST.get('notes', '').strip()
            
            if supplier_id:
                receipt.supplier_id = supplier_id
            if receipt_date:
                receipt.receipt_date = receipt_date
            receipt.invoice_number = invoice_number
            receipt.notes = notes
            receipt.save()
            
            messages.success(request, f'تم تحديث الإيصال "{receipt.receipt_number}" بنجاح')
            return redirect('books_inventory:receipt_detail', pk=receipt.pk)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ في التحديث: {str(e)}')
    
    # طلب GET
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
    context = {
        'receipt': receipt,
        'suppliers': suppliers,
        'page_title': f'تعديل الإيصال - {receipt.receipt_number}'
    }
    
    return render(request, 'books_inventory/edit_receipt.html', context)


@never_cache
@login_required
def delete_receipt(request, pk):
    """حذف إيصال استلام"""
    
    receipt = get_object_or_404(StockReceipt, pk=pk)
    
    if request.method == 'POST':
        try:
            receipt_number = receipt.receipt_number
            
            # حذف جميع عناصر الإيصال أولاً
            BookReceiptItem.objects.filter(receipt=receipt).delete()
            NotebookReceiptItem.objects.filter(receipt=receipt).delete()
            SupplyReceiptItem.objects.filter(receipt=receipt).delete()
            
            # حذف الإيصال
            receipt.delete()
            
            messages.success(request, f'تم حذف الإيصال "{receipt_number}" بنجاح')
            return redirect('books_inventory:receipts_list')
            
        except Exception as e:
            messages.error(request, f'لا يمكن حذف الإيصال: {str(e)}')
            return redirect('books_inventory:receipt_detail', pk=pk)
    
    # إحصائيات الإيصال
    book_items_count = BookReceiptItem.objects.filter(receipt=receipt).count()
    notebook_items_count = NotebookReceiptItem.objects.filter(receipt=receipt).count()
    supply_items_count = SupplyReceiptItem.objects.filter(receipt=receipt).count()
    
    context = {
        'receipt': receipt,
        'book_items_count': book_items_count,
        'notebook_items_count': notebook_items_count,
        'supply_items_count': supply_items_count,
        'page_title': f'حذف الإيصال - {receipt.receipt_number}'
    }
    
    return render(request, 'books_inventory/delete_receipt.html', context)


@require_http_methods(["POST"])
@login_required
def report_shortage_api(request):
    """API للإبلاغ عن نقص في المخزون عبر AJAX"""
    
    try:
        data = json.loads(request.body)
        
        item_type = data.get('item_type')
        item_id = data.get('item_id')
        required_quantity = int(data.get('required_quantity', 0))
        priority = data.get('priority', 'MEDIUM')
        notes = data.get('notes', '')
        
        if not item_type or not item_id or required_quantity <= 0:
            return JsonResponse({
                'success': False,
                'error': 'بيانات غير كاملة'
            })
        
        # الحصول على العنصر والمخزون الحالي
        current_stock = 0
        item_name = ''
        book = notebook = supply = None
        
        if item_type == 'BOOK':
            book = get_object_or_404(Book, pk=item_id, is_active=True)
            current_stock = book.available_stock
            item_name = book.title
        elif item_type == 'NOTEBOOK':
            notebook = get_object_or_404(Notebook, pk=item_id, is_active=True)
            current_stock = notebook.available_stock
            item_name = notebook.name
        elif item_type == 'SUPPLY':
            supply = get_object_or_404(SchoolSupply, pk=item_id, is_active=True)
            current_stock = supply.available_stock
            item_name = supply.name
        else:
            return JsonResponse({
                'success': False,
                'error': 'نوع عنصر غير صحيح'
            })
        
        shortage_quantity = max(0, required_quantity - current_stock)
        
        if shortage_quantity > 0:
            # التحقق من عدم وجود بلاغ مشابه
            existing_shortage = StockShortage.objects.filter(
                item_type=item_type,
                book=book,
                notebook=notebook,
                supply=supply,
                status__in=['REPORTED', 'ACKNOWLEDGED']
            ).first()
            
            if existing_shortage:
                return JsonResponse({
                    'success': False,
                    'error': f'يوجد بلاغ نقص سابق لـ "{item_name}" لم يتم حله بعد'
                })
            
            # إنشاء بلاغ النقص
            shortage = StockShortage.objects.create(
                item_type=item_type,
                item_name=item_name,
                book=book,
                notebook=notebook,
                supply=supply,
                current_stock=current_stock,
                required_quantity=required_quantity,
                shortage_quantity=shortage_quantity,
                priority=priority,
                reported_by=request.user,
                notes=notes
            )
            
            return JsonResponse({
                'success': True,
                'message': f'تم الإبلاغ عن نقص في "{item_name}" بنجاح',
                'shortage_id': shortage.id,
                'shortage_quantity': shortage_quantity
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'المخزون الحالي كافي للكمية المطلوبة'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'بيانات JSON غير صحيحة'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'حدث خطأ: {str(e)}'
        })


@never_cache
@login_required
def shortage_detail(request, pk):
    """تفاصيل بلاغ النقص"""
    
    shortage = get_object_or_404(StockShortage, pk=pk)
    
    # الحصول على العنصر المرتبط
    related_item = None
    if shortage.book:
        related_item = shortage.book
    elif shortage.notebook:
        related_item = shortage.notebook
    elif shortage.supply:
        related_item = shortage.supply
    
    context = {
        'shortage': shortage,
        'related_item': related_item,
        'page_title': f'بلاغ النقص - {shortage.item_name}'
    }
    
    return render(request, 'books_inventory/shortage_detail.html', context)


@never_cache
@login_required
def update_shortage_status(request, pk):
    """تحديث حالة بلاغ النقص"""
    
    shortage = get_object_or_404(StockShortage, pk=pk)
    
    if request.method == 'POST':
        try:
            new_status = request.POST.get('status')
            notes = request.POST.get('notes', '').strip()
            
            if new_status and new_status in [choice[0] for choice in StockShortage.SHORTAGE_STATUS_CHOICES]:
                shortage.status = new_status
                shortage.acknowledged_by = request.user
                shortage.acknowledged_date = timezone.now()
                
                if notes:
                    shortage.notes = f"{shortage.notes}\n---\n{notes}" if shortage.notes else notes
                
                shortage.save()
                
                status_display = shortage.get_status_display()
                messages.success(request, f'تم تحديث حالة البلاغ إلى "{status_display}"')
            else:
                messages.error(request, 'حالة غير صحيحة')
            
            return redirect('books_inventory:shortage_detail', pk=shortage.pk)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'shortage': shortage,
        'status_choices': StockShortage.SHORTAGE_STATUS_CHOICES,
        'page_title': f'تحديث حالة البلاغ - {shortage.item_name}'
    }
    
    return render(request, 'books_inventory/update_shortage_status.html', context)


# ============================================================================
# وظائف الطباعة
# ============================================================================

@never_cache
@login_required
def print_distribution(request, pk):
    """طباعة تفاصيل التوزيع"""
    
    distribution = get_object_or_404(StudentDistribution, pk=pk)
    
    # الحصول على العناصر الموزعة
    book_items = distribution.book_items.select_related('book__subject').all()
    notebook_items = distribution.notebook_items.select_related('notebook').all()
    supply_items = distribution.supply_items.select_related('supply').all()
    
    # إحصائيات
    total_books = book_items.count()
    total_notebooks = notebook_items.count()
    total_supplies = supply_items.count()
    total_items = total_books + total_notebooks + total_supplies
    
    # إحصائيات الكميات
    total_books_qty = sum(item.quantity_distributed for item in book_items)
    total_notebooks_qty = sum(item.quantity_distributed for item in notebook_items)
    total_supplies_qty = sum(item.quantity_distributed for item in supply_items)
    total_qty = total_books_qty + total_notebooks_qty + total_supplies_qty
    
    context = {
        'distribution': distribution,
        'book_items': book_items,
        'notebook_items': notebook_items,
        'supply_items': supply_items,
        'total_books': total_books,
        'total_notebooks': total_notebooks,
        'total_supplies': total_supplies,
        'total_items': total_items,
        'total_books_qty': total_books_qty,
        'total_notebooks_qty': total_notebooks_qty,
        'total_supplies_qty': total_supplies_qty,
        'total_qty': total_qty,
        'page_title': f'طباعة التوزيع - {distribution.student.name}'
    }
    
    return render(request, 'books_inventory/print_distribution.html', context)


# ============================================================================
# وظائف إضافية ومساعدة
# ============================================================================

@never_cache
@login_required
def student_detail_view(request, pk):
    """عرض تفاصيل الطالب (للقراءة فقط - موظف المخزن)"""
    
    try:
        student = get_object_or_404(Student, pk=pk)
        
        # أحدث التوزيعات للطالب
        distributions = StudentDistribution.objects.filter(
            student=student
        ).select_related('distributed_by').order_by('-distribution_date')[:10]
        
        # إحصائيات التوزيع
        total_distributions = StudentDistribution.objects.filter(student=student).count()
        completed_distributions = StudentDistribution.objects.filter(
            student=student, status='COMPLETED'
        ).count()
        
        # آخر توزيع
        latest_distribution = distributions.first() if distributions else None
        
        # حالة الدفع الحالية
        payment_status = 'غير معروف'
        try:
            first_installment = Tuition.objects.filter(
                student=student,
                installment_number=1
            ).first()
            
            if first_installment:
                payment_status = 'مدفوع' if first_installment.payment_status == 'PAID' else 'غير مدفوع'
        except:
            pass
        
        context = {
            'student': student,
            'distributions': distributions,
            'total_distributions': total_distributions,
            'completed_distributions': completed_distributions,
            'latest_distribution': latest_distribution,
            'payment_status': payment_status,
            'page_title': f'بيانات الطالب - {student.name}'
        }
        
        return render(request, 'books_inventory/student_detail.html', context)
        
    except Exception as e:
        messages.error(request, f'حدث خطأ في عرض بيانات الطالب: {str(e)}')
        return redirect('books_inventory:student_search_view')


@never_cache
@login_required
def student_payments_view(request):
    """عرض حالة مدفوعات الطلاب (للقراءة فقط)"""
    
    search_query = request.GET.get('search', '')
    payment_status_filter = request.GET.get('payment_status', '')
    
    try:
        # البحث في الطلاب
        students = Student.objects.filter(is_active=True)
        
        if search_query:
            students = students.filter(
                Q(name__icontains=search_query) |
                Q(national_number__icontains=search_query)
            )
        
        # تطبيق فلتر حالة الدفع
        if payment_status_filter == 'paid':
            # الطلاب الذين دفعوا القسط الأول
            paid_student_ids = Tuition.objects.filter(
                installment_number=1,
                payment_status='PAID'
            ).values_list('student_id', flat=True)
            students = students.filter(id__in=paid_student_ids)
            
        elif payment_status_filter == 'unpaid':
            # الطلاب الذين لم يدفعوا القسط الأول
            paid_student_ids = Tuition.objects.filter(
                installment_number=1,
                payment_status='PAID'
            ).values_list('student_id', flat=True)
            students = students.exclude(id__in=paid_student_ids)
        
        students = students.order_by('name')
        
        # تقسيم الصفحات
        paginator = Paginator(students, 20)
        page_number = request.GET.get('page')
        
        try:
            students_page = paginator.page(page_number)
        except PageNotAnInteger:
            students_page = paginator.page(1)
        except EmptyPage:
            students_page = paginator.page(paginator.num_pages)
        
        # إضافة بيانات الدفع لكل طالب
        for student in students_page:
            try:
                first_installment = Tuition.objects.filter(
                    student=student,
                    installment_number=1
                ).first()
                
                if first_installment:
                    student.payment_status = first_installment.payment_status
                    student.payment_date = first_installment.payment_date
                    student.amount_paid = first_installment.amount_paid
                else:
                    student.payment_status = 'NOT_PAID'
                    student.payment_date = None
                    student.amount_paid = 0
                
                # آخر توزيع
                student.latest_distribution = StudentDistribution.objects.filter(
                    student=student
                ).order_by('-distribution_date').first()
                
            except Exception as e:
                print(f"خطأ في معالجة بيانات الطالب {student.name}: {e}")
                student.payment_status = 'UNKNOWN'
        
        context = {
            'students': students_page,
            'search_query': search_query,
            'payment_status_filter': payment_status_filter,
            'page_title': 'حالة مدفوعات الطلاب'
        }
        
        return render(request, 'books_inventory/student_payments.html', context)
        
    except Exception as e:
        messages.error(request, f'حدث خطأ في عرض المدفوعات: {str(e)}')
        return render(request, 'books_inventory/student_payments.html', {
            'students': [],
            'search_query': search_query,
            'payment_status_filter': payment_status_filter,
            'page_title': 'حالة مدفوعات الطلاب'
        })


# ============================================================================
# نهاية الملف
# ============================================================================


# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.views.decorators.cache import never_cache
# from django.views.decorators.csrf import csrf_protect
# from django.views.decorators.http import require_POST
# from django.http import JsonResponse, HttpResponse
# from django.db.models import Q, Count, Sum, F
# from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# from django.utils import timezone
# from django.db import transaction
# from decimal import Decimal
# import csv
# from datetime import date, datetime, timedelta
# from django.views.decorators.http import require_http_methods, require_GET
# import json


# # استيراد النماذج
# from .models import (
#     ShortageReport, Supplier, Subject, Book, Notebook, SchoolSupply,
#     StockReceipt, BookReceiptItem, NotebookReceiptItem, SupplyReceiptItem,
#     StudentDistribution, BookDistributionItem, NotebookDistributionItem, SupplyDistributionItem,
#     StockShortage
# )
# from students.models import Student
# from payments.models import Tuition
# from school_settings.models import GradeLevel, EducationLevel


# # الصفحة الرئيسية لمخزن الكتب
# @never_cache
# @login_required
# def inventory_home(request):
#     """الصفحة الرئيسية لمخزن الكتب"""
    
#     try:
#         # إحصائيات عامة
#         total_books = Book.objects.filter(is_active=True).count()
#         total_notebooks = Notebook.objects.filter(is_active=True).count()
#         total_supplies = SchoolSupply.objects.filter(is_active=True).count()
        
#         # إحصائيات المخزون
#         books_stock = Book.objects.filter(is_active=True).aggregate(
#             total_stock=Sum('total_stock'),
#             available_stock=Sum('available_stock'),
#             distributed=Sum('distributed_count')
#         )
        
#         notebooks_stock = Notebook.objects.filter(is_active=True).aggregate(
#             total_stock=Sum('total_stock'),
#             available_stock=Sum('available_stock'),
#             distributed=Sum('distributed_count')
#         )
        
#         supplies_stock = SchoolSupply.objects.filter(is_active=True).aggregate(
#             total_stock=Sum('total_stock'),
#             available_stock=Sum('available_stock'),
#             distributed=Sum('distributed_count')
#         )
        
#         # العناصر منخفضة المخزون
#         low_stock_books = Book.objects.filter(
#             is_active=True,
#             available_stock__lte=F('minimum_stock_level')
#         ).count()
        
#         low_stock_notebooks = Notebook.objects.filter(
#             is_active=True,
#             available_stock__lte=F('minimum_stock_level')
#         ).count()
        
#         low_stock_supplies = SchoolSupply.objects.filter(
#             is_active=True,
#             available_stock__lte=F('minimum_stock_level')
#         ).count()
        
#         # النواقص المُبلغ عنها
#         pending_shortages = StockShortage.objects.filter(
#             status__in=['REPORTED', 'ACKNOWLEDGED']
#         ).count()
        
#         # التوزيعات اليوم
#         today = timezone.now().date()
#         distributions_today = StudentDistribution.objects.filter(
#             distribution_date=today
#         ).count()
        
#         # الاستلامات هذا الأسبوع
#         week_ago = today - timedelta(days=7)
#         receipts_this_week = StockReceipt.objects.filter(
#             receipt_date__gte=week_ago
#         ).count()
        
#         # أحدث الاستلامات
#         recent_receipts = StockReceipt.objects.select_related('supplier').order_by('-receipt_date')[:5]
        
#         # أحدث التوزيعات
#         recent_distributions = StudentDistribution.objects.select_related(
#             'student'
#         ).order_by('-distribution_date')[:5]
        
#         # العناصر التي تحتاج إعادة طلب
#         items_to_reorder = []
        
#         # كتب تحتاج إعادة طلب
#         books_to_reorder = Book.objects.filter(
#             is_active=True,
#             available_stock__lte=F('minimum_stock_level')
#         )[:10]
        
#         for book in books_to_reorder:
#             items_to_reorder.append({
#                 'type': 'كتاب',
#                 'name': book.title,
#                 'current_stock': book.available_stock,
#                 'minimum_level': book.minimum_stock_level,
#                 'subject': book.subject.name
#             })
        
#         # كراسات تحتاج إعادة طلب
#         notebooks_to_reorder = Notebook.objects.filter(
#             is_active=True,
#             available_stock__lte=F('minimum_stock_level')
#         )[:10]
        
#         for notebook in notebooks_to_reorder:
#             items_to_reorder.append({
#                 'type': 'كراسة',
#                 'name': notebook.name,
#                 'current_stock': notebook.available_stock,
#                 'minimum_level': notebook.minimum_stock_level,
#                 'subject': notebook.get_notebook_type_display()
#             })
        
#     except Exception as e:
#         print(f"خطأ في إحصائيات المخزن: {e}")
#         # قيم افتراضية في حالة الخطأ
#         total_books = total_notebooks = total_supplies = 0
#         books_stock = notebooks_stock = supplies_stock = {'total_stock': 0, 'available_stock': 0, 'distributed': 0}
#         low_stock_books = low_stock_notebooks = low_stock_supplies = 0
#         pending_shortages = distributions_today = receipts_this_week = 0
#         recent_receipts = recent_distributions = items_to_reorder = []
    
#     context = {
#         'total_books': total_books,
#         'total_notebooks': total_notebooks,
#         'total_supplies': total_supplies,
#         'books_stock': books_stock,
#         'notebooks_stock': notebooks_stock,
#         'supplies_stock': supplies_stock,
#         'low_stock_books': low_stock_books,
#         'low_stock_notebooks': low_stock_notebooks,
#         'low_stock_supplies': low_stock_supplies,
#         'pending_shortages': pending_shortages,
#         'distributions_today': distributions_today,
#         'receipts_this_week': receipts_this_week,
#         'recent_receipts': recent_receipts,
#         'recent_distributions': recent_distributions,
#         'items_to_reorder': items_to_reorder,
#         'today': today,
#         'page_title': 'الصفحة الرئيسية - مخزن الكتب'
#     }
    
#     return render(request, 'books_inventory/inventory_home.html', context)


# # إدارة الكتب
# # تحديث دالة books_list
# @never_cache
# @login_required
# def books_list(request):
#     """قائمة الكتب والملخصات"""
    
#     # الفلاتر
#     search_query = request.GET.get('search', '')
#     subject_filter = request.GET.get('subject', '')
#     book_type_filter = request.GET.get('book_type', '')
#     term_filter = request.GET.get('term', '')
#     stock_status_filter = request.GET.get('stock_status', '')
#     grade_level_filter = request.GET.get('grade_level', '')
    
#     books = Book.objects.filter(is_active=True).select_related('subject').prefetch_related('grade_levels')
    
#     # تطبيق الفلاتر
#     if search_query:
#         books = books.filter(
#             Q(title__icontains=search_query) |
#             Q(description__icontains=search_query)
#         )
    
#     if subject_filter:
#         books = books.filter(subject_id=subject_filter)
    
#     if book_type_filter:
#         books = books.filter(book_type=book_type_filter)
        
#     if term_filter:
#         books = books.filter(term=term_filter)
    
#     if grade_level_filter:
#         books = books.filter(grade_levels__id=grade_level_filter)
    
#     if stock_status_filter:
#         if stock_status_filter == 'available':
#             books = books.filter(available_stock__gt=F('minimum_stock_level'))
#         elif stock_status_filter == 'low_stock':
#             books = books.filter(available_stock__lte=F('minimum_stock_level'), available_stock__gt=0)
#         elif stock_status_filter == 'out_of_stock':
#             books = books.filter(available_stock=0)
    
#     # الترتيب
#     books = books.order_by('book_type', 'subject__name', 'title')
    
#     # إحصائيات للعرض
#     all_books = Book.objects.filter(is_active=True)
#     ministry_books_count = all_books.filter(book_type__in=['MINISTRY', 'WORKBOOK']).count()
#     manar_books_count = all_books.filter(book_type__startswith='MANAR_').count()
#     available_books_count = all_books.filter(available_stock__gt=F('minimum_stock_level')).count()
#     low_stock_books_count = all_books.filter(available_stock__lte=F('minimum_stock_level')).count()
    
#     # Pagination
#     paginator = Paginator(books, 20)
#     page_number = request.GET.get('page')
    
#     try:
#         books_page = paginator.page(page_number)
#     except PageNotAnInteger:
#         books_page = paginator.page(1)
#     except EmptyPage:
#         books_page = paginator.page(paginator.num_pages)
    
#     # البيانات للفلاتر
#     subjects = Subject.objects.filter(is_active=True).order_by('name')
#     grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    
#     context = {
#         'books': books_page,
#         'subjects': subjects,
#         'grade_levels': grade_levels,
#         'search_query': search_query,
#         'subject_filter': subject_filter,
#         'book_type_filter': book_type_filter,
#         'term_filter': term_filter,
#         'stock_status_filter': stock_status_filter,
#         'grade_level_filter': grade_level_filter,
#         'book_type_choices': Book.BOOK_TYPE_CHOICES,
#         'ministry_books_count': ministry_books_count,
#         'manar_books_count': manar_books_count,
#         'available_books_count': available_books_count,
#         'low_stock_books_count': low_stock_books_count,
#         'page_title': 'إدارة الكتب والملخصات'
#     }
    
#     return render(request, 'books_inventory/books_list.html', context)

# @never_cache
# @login_required
# def book_detail(request, pk):
#     """تفاصيل الكتاب"""
    
#     book = get_object_or_404(Book, pk=pk)
    
#     # إحصائيات أساسية
#     try:
#         # احدث الاستلامات
#         recent_receipts = BookReceiptItem.objects.filter(book=book).select_related(
#             'receipt__supplier'
#         ).order_by('-receipt__receipt_date')[:5]
#     except:
#         recent_receipts = []
    
#     try:
#         # أحدث التوزيعات  
#         recent_distributions = []
#         if hasattr(book, 'bookdistributionitem_set'):
#             recent_distributions = book.bookdistributionitem_set.select_related(
#                 'distribution__student'
#             ).order_by('-distribution__distribution_date')[:5]
#     except:
#         recent_distributions = []
    
#     # إحصائيات من إيصالات الاستلام الفعلية
#     total_received = book.actual_total_stock
#     total_damaged = book.actual_damaged_count
#     total_distributed = book.actual_distributed_count
    
#     # تحديث مخزون الكتاب إذا كان مختلف
#     if book.total_stock != total_received:
#         book.sync_stock_from_receipts()
#         # إعادة تحديث الكائن من قاعدة البيانات
#         book.refresh_from_db()
    
#     context = {
#         'book': book,
#         'recent_receipts': recent_receipts,
#         'recent_distributions': recent_distributions,
#         'total_received': total_received,
#         'total_distributed': total_distributed,
#         'total_damaged': total_damaged,
#         # استخدام القيم الفعلية بدلاً من الحقول
#         'actual_total_stock': book.actual_total_stock,
#         'actual_available_stock': book.actual_available_stock,
#         'actual_damaged_count': book.actual_damaged_count,
#         'page_title': f'تفاصيل الكتاب - {book.title}'
#     }
    
#     return render(request, 'books_inventory/book_detail.html', context)



# # إدارة الكراسات
# @never_cache
# @login_required
# def notebooks_list(request):
#     """قائمة الكراسات"""
    
#     # الفلاتر
#     search_query = request.GET.get('search', '')
#     notebook_type_filter = request.GET.get('notebook_type', '')
#     size_filter = request.GET.get('size', '')
#     stock_status_filter = request.GET.get('stock_status', '')
    
#     notebooks = Notebook.objects.filter(is_active=True).prefetch_related('grade_levels')
    
#     # تطبيق الفلاتر
#     if search_query:
#         notebooks = notebooks.filter(name__icontains=search_query)
    
#     if notebook_type_filter:
#         notebooks = notebooks.filter(notebook_type=notebook_type_filter)
    
#     if size_filter:
#         notebooks = notebooks.filter(size=size_filter)
    
#     if stock_status_filter:
#         if stock_status_filter == 'available':
#             notebooks = notebooks.filter(available_stock__gt=F('minimum_stock_level'))
#         elif stock_status_filter == 'low_stock':
#             notebooks = notebooks.filter(available_stock__lte=F('minimum_stock_level'), available_stock__gt=0)
#         elif stock_status_filter == 'out_of_stock':
#             notebooks = notebooks.filter(available_stock=0)
    
#     notebooks = notebooks.order_by('notebook_type', 'name')
    
#     # Pagination
#     paginator = Paginator(notebooks, 20)
#     page_number = request.GET.get('page')
    
#     try:
#         notebooks_page = paginator.page(page_number)
#     except PageNotAnInteger:
#         notebooks_page = paginator.page(1)
#     except EmptyPage:
#         notebooks_page = paginator.page(paginator.num_pages)
    
#     context = {
#         'notebooks': notebooks_page,
#         'search_query': search_query,
#         'notebook_type_filter': notebook_type_filter,
#         'size_filter': size_filter,
#         'stock_status_filter': stock_status_filter,
#         'notebook_type_choices': Notebook.NOTEBOOK_TYPE_CHOICES,
#         'size_choices': Notebook.SIZE_CHOICES,
#         'page_title': 'إدارة الكراسات'
#     }
    
#     return render(request, 'books_inventory/notebooks_list.html', context)


# # إدارة الأدوات المدرسية
# @never_cache
# @login_required
# def supplies_list(request):
#     """قائمة الأدوات المدرسية"""
    
#     # الفلاتر
#     search_query = request.GET.get('search', '')
#     category_filter = request.GET.get('category', '')
#     stock_status_filter = request.GET.get('stock_status', '')
    
#     supplies = SchoolSupply.objects.filter(is_active=True).prefetch_related('grade_levels')
    
#     # تطبيق الفلاتر
#     if search_query:
#         supplies = supplies.filter(
#             Q(name__icontains=search_query) |
#             Q(description__icontains=search_query)
#         )
    
#     if category_filter:
#         supplies = supplies.filter(category=category_filter)
    
#     if stock_status_filter:
#         if stock_status_filter == 'available':
#             supplies = supplies.filter(available_stock__gt=F('minimum_stock_level'))
#         elif stock_status_filter == 'low_stock':
#             supplies = supplies.filter(available_stock__lte=F('minimum_stock_level'), available_stock__gt=0)
#         elif stock_status_filter == 'out_of_stock':
#             supplies = supplies.filter(available_stock=0)
    
#     supplies = supplies.order_by('category', 'name')
    
#     # Pagination
#     paginator = Paginator(supplies, 20)
#     page_number = request.GET.get('page')
    
#     try:
#         supplies_page = paginator.page(page_number)
#     except PageNotAnInteger:
#         supplies_page = paginator.page(1)
#     except EmptyPage:
#         supplies_page = paginator.page(paginator.num_pages)
    
#     context = {
#         'supplies': supplies_page,
#         'search_query': search_query,
#         'category_filter': category_filter,
#         'stock_status_filter': stock_status_filter,
#         'category_choices': SchoolSupply.SUPPLY_CATEGORY_CHOICES,
#         'page_title': 'إدارة الأدوات المدرسية'
#     }
    
#     return render(request, 'books_inventory/supplies_list.html', context)


# # إدارة الموردين
# @never_cache
# @login_required
# def suppliers_list(request):
#     """قائمة الموردين"""
    
#     search_query = request.GET.get('search', '')
    
#     suppliers = Supplier.objects.filter(is_active=True)
    
#     if search_query:
#         suppliers = suppliers.filter(
#             Q(name__icontains=search_query) |
#             Q(contact_person__icontains=search_query) |
#             Q(phone_number__icontains=search_query)
#         )
    
#     suppliers = suppliers.order_by('name')
    
#     # Pagination
#     paginator = Paginator(suppliers, 15)
#     page_number = request.GET.get('page')
    
#     try:
#         suppliers_page = paginator.page(page_number)
#     except PageNotAnInteger:
#         suppliers_page = paginator.page(1)
#     except EmptyPage:
#         suppliers_page = paginator.page(paginator.num_pages)
    
#     context = {
#         'suppliers': suppliers_page,
#         'search_query': search_query,
#         'page_title': 'إدارة الموردين'
#     }
    
#     return render(request, 'books_inventory/suppliers_list.html', context)


# # إدارة الاستلام
# @never_cache
# @login_required
# def receipts_list(request):
#     """قائمة إيصالات الاستلام"""
    
#     # الفلاتر
#     search_query = request.GET.get('search', '')
#     supplier_filter = request.GET.get('supplier', '')
#     receipt_type_filter = request.GET.get('receipt_type', '')
#     date_from = request.GET.get('date_from', '')
#     date_to = request.GET.get('date_to', '')
    
#     receipts = StockReceipt.objects.select_related('supplier', 'received_by').order_by('-receipt_date')
    
#     # تطبيق الفلاتر
#     if search_query:
#         receipts = receipts.filter(
#             Q(receipt_number__icontains=search_query) |
#             Q(supplier__name__icontains=search_query) |
#             Q(invoice_number__icontains=search_query)
#         )
    
#     if supplier_filter:
#         receipts = receipts.filter(supplier_id=supplier_filter)
    
#     if receipt_type_filter:
#         receipts = receipts.filter(receipt_type=receipt_type_filter)
    
#     if date_from:
#         receipts = receipts.filter(receipt_date__gte=date_from)
    
#     if date_to:
#         receipts = receipts.filter(receipt_date__lte=date_to)
    
#     # Pagination
#     paginator = Paginator(receipts, 15)
#     page_number = request.GET.get('page')
    
#     try:
#         receipts_page = paginator.page(page_number)
#     except PageNotAnInteger:
#         receipts_page = paginator.page(1)
#     except EmptyPage:
#         receipts_page = paginator.page(paginator.num_pages)
    
#     # البيانات للفلاتر
#     suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
#     context = {
#         'receipts': receipts_page,
#         'suppliers': suppliers,
#         'search_query': search_query,
#         'supplier_filter': supplier_filter,
#         'receipt_type_filter': receipt_type_filter,
#         'date_from': date_from,
#         'date_to': date_to,
#         'receipt_type_choices': StockReceipt.RECEIPT_TYPE_CHOICES,
#         'page_title': 'إيصالات الاستلام'
#     }
    
#     return render(request, 'books_inventory/receipts_list.html', context)


# @never_cache
# @login_required
# def add_receipt(request):
#     """إضافة إيصال استلام جديد مع العناصر"""
    
#     if request.method == 'POST':
#         try:
#             # البيانات الأساسية للإيصال
#             supplier_id = request.POST.get('supplier')
#             receipt_type = request.POST.get('receipt_type')
#             receipt_date = request.POST.get('receipt_date')
#             invoice_number = request.POST.get('invoice_number', '').strip()
#             notes = request.POST.get('notes', '').strip()
#             item_count = int(request.POST.get('item_count', 0))
            
#             # التحقق من البيانات المطلوبة
#             if not supplier_id or not receipt_type or not receipt_date:
#                 messages.error(request, 'يجب إدخال جميع البيانات المطلوبة')
#                 return redirect('books_inventory:add_receipt')
            
#             if item_count == 0:
#                 messages.error(request, 'يجب إضافة عنصر واحد على الأقل للإيصال')
#                 return redirect('books_inventory:add_receipt')
            
#             # إنشاء الإيصال
#             supplier = get_object_or_404(Supplier, pk=supplier_id)
            
#             # إنشاء رقم الإيصال
#             receipt_number = f"REC-{timezone.now().strftime('%Y%m%d')}-{StockReceipt.objects.count() + 1:04d}"
            
#             receipt = StockReceipt.objects.create(
#                 receipt_number=receipt_number,
#                 supplier=supplier,
#                 receipt_type=receipt_type,
#                 receipt_date=receipt_date,
#                 invoice_number=invoice_number,
#                 notes=notes,
#                 received_by=request.user,
#                 total_items=0,  # سنحدثه لاحقاً
#                 damaged_items=0,  # سنحدثه لاحقاً
#                 total_cost=0  # سنحدثه لاحقاً
#             )
            
#             # إضافة العناصر حسب النوع
#             total_items = 0
#             total_damaged = 0
#             total_cost = Decimal('0.00')
            
#             with transaction.atomic():
#                 for i in range(item_count):
#                     if receipt_type == 'BOOKS':
#                         # عناصر الكتب
#                         book_id = request.POST.get(f'book_{i}')
#                         if book_id:
#                             book = get_object_or_404(Book, pk=book_id)
#                             quantity = int(request.POST.get(f'quantity_{i}', 0))
#                             damaged = int(request.POST.get(f'damaged_{i}', 0))
#                             unit_cost = Decimal(request.POST.get(f'unit_cost_{i}', '0'))
                            
#                             if quantity > 0:
#                                 # إنشاء عنصر الإيصال
#                                 BookReceiptItem.objects.create(
#                                     receipt=receipt,
#                                     book=book,
#                                     quantity_received=quantity,
#                                     quantity_damaged=damaged,
#                                     unit_cost=unit_cost,
#                                     total_cost=quantity * unit_cost
#                                 )
                                
#                                 # تحديث مخزون الكتاب
#                                 book.total_stock += quantity
#                                 book.damaged_count += damaged
#                                 book.update_stock()
                                
#                                 total_items += quantity
#                                 total_damaged += damaged
#                                 total_cost += quantity * unit_cost
                    
#                     elif receipt_type == 'NOTEBOOKS':
#                         # عناصر الكراسات
#                         notebook_id = request.POST.get(f'notebook_{i}')
#                         if notebook_id:
#                             notebook = get_object_or_404(Notebook, pk=notebook_id)
#                             quantity = int(request.POST.get(f'quantity_{i}', 0))
#                             damaged = int(request.POST.get(f'damaged_{i}', 0))
#                             unit_cost = Decimal(request.POST.get(f'unit_cost_{i}', '0'))
                            
#                             if quantity > 0:
#                                 # إنشاء عنصر الإيصال
#                                 NotebookReceiptItem.objects.create(
#                                     receipt=receipt,
#                                     notebook=notebook,
#                                     quantity_received=quantity,
#                                     quantity_damaged=damaged,
#                                     unit_cost=unit_cost,
#                                     total_cost=quantity * unit_cost
#                                 )
                                
#                                 # تحديث مخزون الكراسة
#                                 notebook.total_stock += quantity
#                                 notebook.damaged_count += damaged
#                                 notebook.update_stock()
                                
#                                 total_items += quantity
#                                 total_damaged += damaged
#                                 total_cost += quantity * unit_cost
                    
#                     elif receipt_type == 'SUPPLIES':
#                         # عناصر الأدوات المدرسية
#                         supply_id = request.POST.get(f'supply_{i}')
#                         if supply_id:
#                             supply = get_object_or_404(SchoolSupply, pk=supply_id)
#                             quantity = int(request.POST.get(f'quantity_{i}', 0))
#                             damaged = int(request.POST.get(f'damaged_{i}', 0))
#                             unit_cost = Decimal(request.POST.get(f'unit_cost_{i}', '0'))
                            
#                             if quantity > 0:
#                                 # إنشاء عنصر الإيصال
#                                 SupplyReceiptItem.objects.create(
#                                     receipt=receipt,
#                                     supply=supply,
#                                     quantity_received=quantity,
#                                     quantity_damaged=damaged,
#                                     unit_cost=unit_cost,
#                                     total_cost=quantity * unit_cost
#                                 )
                                
#                                 # تحديث مخزون الأداة المدرسية
#                                 supply.total_stock += quantity
#                                 supply.damaged_count += damaged
#                                 supply.update_stock()
                                
#                                 total_items += quantity
#                                 total_damaged += damaged
#                                 total_cost += quantity * unit_cost
                
#                 # تحديث إجماليات الإيصال
#                 receipt.total_items = total_items
#                 receipt.damaged_items = total_damaged
#                 receipt.total_cost = total_cost
#                 receipt.save()
            
#             messages.success(request, f'تم إنشاء إيصال الاستلام "{receipt.receipt_number}" بنجاح')
#             return redirect('books_inventory:receipt_detail', pk=receipt.pk)
            
#         except Exception as e:
#             print(f"خطأ في إنشاء الإيصال: {e}")
#             messages.error(request, f'حدث خطأ في إنشاء الإيصال: {str(e)}')
#             return redirect('books_inventory:add_receipt')
    
#     # GET request - تحضير البيانات للقالب
#     suppliers = Supplier.objects.filter(is_active=True).order_by('name')
#     books = Book.objects.filter(is_active=True).select_related('subject').order_by('title')
#     notebooks = Notebook.objects.filter(is_active=True).order_by('name')
#     supplies = SchoolSupply.objects.filter(is_active=True).order_by('name')
    
#     # تحويل البيانات لـ JSON للاستخدام في JavaScript
#     books_json = json.dumps([{
#         'id': book.id,
#         'title': book.title,
#         'subject': book.subject.name,
#         'book_type': book.get_book_type_display(),
#         'cost_price': float(book.cost_price)
#     } for book in books])
    
#     notebooks_json = json.dumps([{
#         'id': notebook.id,
#         'name': notebook.name,
#         'type': notebook.get_notebook_type_display(),
#         'size': notebook.get_size_display(),
#         'pages': notebook.pages_count,
#         'cost_price': float(notebook.cost_price)
#     } for notebook in notebooks])
    
#     supplies_json = json.dumps([{
#         'id': supply.id,
#         'name': supply.name,
#         'category': supply.get_category_display(),
#         'unit': supply.unit,
#         'cost_price': float(supply.cost_price)
#     } for supply in supplies])
    
#     context = {
#         'suppliers': suppliers,
#         'books': books_json,
#         'notebooks': notebooks_json,
#         'supplies': supplies_json,
#         'receipt_type_choices': StockReceipt.RECEIPT_TYPE_CHOICES,
#         'today': timezone.now().date(),
#         'page_title': 'إضافة إيصال استلام جديد'
#     }
    
#     return render(request, 'books_inventory/add_receipt.html', context)



# @never_cache
# @login_required
# def receipt_detail(request, pk):
#     """تفاصيل إيصال الاستلام"""
    
#     receipt = get_object_or_404(StockReceipt, pk=pk)
    
#     # الحصول على عناصر الإيصال حسب النوع
#     book_items = []
#     notebook_items = []
#     supply_items = []
    
#     if receipt.receipt_type == 'BOOKS':
#         book_items = BookReceiptItem.objects.filter(receipt=receipt).select_related('book__subject')
#     elif receipt.receipt_type == 'NOTEBOOKS':
#         notebook_items = NotebookReceiptItem.objects.filter(receipt=receipt).select_related('notebook')
#     elif receipt.receipt_type == 'SUPPLIES':
#         supply_items = SupplyReceiptItem.objects.filter(receipt=receipt).select_related('supply')
    
#     # حساب متوسط سعر الوحدة
#     average_unit_cost = 0
#     if receipt.total_items and receipt.total_items > 0:
#         average_unit_cost = round(float(receipt.total_cost) / float(receipt.total_items), 2)
    
#     context = {
#         'receipt': receipt,
#         'book_items': book_items,
#         'notebook_items': notebook_items,
#         'supply_items': supply_items,
#         'average_unit_cost': average_unit_cost,
#         'page_title': f'إيصال الاستلام {receipt.receipt_number}'
#     }
    
#     return render(request, 'books_inventory/receipt_detail.html', context)



# # توزيع المواد على الطلاب
# import json
# from django.http import JsonResponse
# from django.template.loader import render_to_string

# @never_cache
# @login_required
# def student_distributions_list(request):
#     """قائمة توزيعات الطلاب مع دعم AJAX"""
    
#     # معاملات البحث
#     search_query = request.GET.get('search', '')
#     status_filter = request.GET.get('status', '')
#     verified_filter = request.GET.get('verified', '')
#     date_from = request.GET.get('date_from', '')
#     date_to = request.GET.get('date_to', '')
    
#     # استخدام النموذج الصحيح - StudentDistribution
#     distributions = StudentDistribution.objects.select_related(
#         'student', 'distributed_by'
#     ).prefetch_related(
#         'book_items__book',
#         'notebook_items__notebook', 
#         'supply_items__supply'
#     ).order_by('-distribution_date')
    
#     # تطبيق البحث
#     if search_query:
#         distributions = distributions.filter(
#             Q(student__name__icontains=search_query) |
#             Q(student__national_number__icontains=search_query)
#         )
    
#     # تطبيق فلتر الحالة
#     if status_filter:
#         distributions = distributions.filter(status=status_filter)
    
#     # تطبيق فلتر حالة الدفع
#     if verified_filter == 'verified':
#         distributions = distributions.filter(first_installment_verified=True)
#     elif verified_filter == 'not_verified':
#         distributions = distributions.filter(first_installment_verified=False)
    
#     # تطبيق فلتر التاريخ
#     if date_from:
#         distributions = distributions.filter(distribution_date__gte=date_from)
#     if date_to:
#         distributions = distributions.filter(distribution_date__lte=date_to)
    
#     # Pagination
#     paginator = Paginator(distributions, 15)
#     page_number = request.GET.get('page')
    
#     try:
#         distributions_page = paginator.page(page_number)
#     except PageNotAnInteger:
#         distributions_page = paginator.page(1)
#     except EmptyPage:
#         distributions_page = paginator.page(paginator.num_pages)
    
#     # إذا كان طلب AJAX
#     if request.GET.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#         html = render_to_string('books_inventory/partials/distributions_table.html', {
#             'distributions': distributions_page,
#             'search_query': search_query,
#             'status_filter': status_filter,
#             'verified_filter': verified_filter,
#             'date_from': date_from,
#             'date_to': date_to,
#         })
        
#         return JsonResponse({
#             'html': html,
#             'count': paginator.count,
#             'page': distributions_page.number,
#             'total_pages': paginator.num_pages,
#             'has_results': paginator.count > 0,
#         })
    
#     # طلب عادي
#     context = {
#         'distributions': distributions_page,
#         'search_query': search_query,
#         'status_filter': status_filter,
#         'verified_filter': verified_filter,
#         'date_from': date_from,
#         'date_to': date_to,
#         'status_choices': StudentDistribution.DISTRIBUTION_STATUS_CHOICES,
#         'page_title': 'توزيعات الطلاب'
#     }
    
#     return render(request, 'books_inventory/distributions_list.html', context)




# @never_cache
# @login_required
# def student_distribution_detail(request, pk):
#     """تفاصيل توزيع طالب"""
    
#     distribution = get_object_or_404(StudentDistribution, pk=pk)
    
#     # العناصر الموزعة
#     book_items = distribution.book_items.select_related('book__subject').all()
#     notebook_items = distribution.notebook_items.select_related('notebook').all()
#     supply_items = distribution.supply_items.select_related('supply').all()
    
#     # إحصائيات
#     total_books = book_items.count()
#     total_notebooks = notebook_items.count()
#     total_supplies = supply_items.count()
    
#     # إحصائيات الكميات
#     total_books_qty = sum(item.quantity_distributed for item in book_items)
#     total_notebooks_qty = sum(item.quantity_distributed for item in notebook_items)
#     total_supplies_qty = sum(item.quantity_distributed for item in supply_items)
    
#     context = {
#         'distribution': distribution,
#         'book_items': book_items,
#         'notebook_items': notebook_items,
#         'supply_items': supply_items,
#         'total_books': total_books,
#         'total_notebooks': total_notebooks,
#         'total_supplies': total_supplies,
#         'total_books_qty': total_books_qty,
#         'total_notebooks_qty': total_notebooks_qty,
#         'total_supplies_qty': total_supplies_qty,
#         'page_title': f'توزيع الطالب - {distribution.student.name}'
#     }
    
#     return render(request, 'books_inventory/student_distribution_detail.html', context)


# @never_cache
# @login_required
# def verify_payment(request, pk):
#     """تأكيد دفع القسط الأول"""
    
#     distribution = get_object_or_404(StudentDistribution, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             notes = request.POST.get('notes', '').strip()
            
#             distribution.first_installment_verified = True
#             distribution.verification_date = timezone.now()
#             distribution.verification_notes = notes
#             distribution.save()
            
#             messages.success(request, f'تم تأكيد دفع القسط الأول للطالب {distribution.student.name}')
#             return redirect('books_inventory:student_distribution_detail', pk=distribution.pk)
            
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     context = {
#         'distribution': distribution,
#         'page_title': f'تأكيد الدفع - {distribution.student.name}'
#     }
    
#     return render(request, 'books_inventory/verify_payment.html', context)


# @never_cache
# @login_required
# def edit_distribution(request, pk):
#     """تعديل توزيع طالب"""
    
#     distribution = get_object_or_404(StudentDistribution, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             # تحديث حالة التوزيع
#             status = request.POST.get('status')
#             notes = request.POST.get('notes', '').strip()
#             verification_notes = request.POST.get('verification_notes', '').strip()
#             first_installment_verified = request.POST.get('first_installment_verified') == 'on'
            
#             # تحديث الحقول
#             if status:
#                 distribution.status = status
            
#             distribution.notes = notes
#             distribution.verification_notes = verification_notes
            
#             # تحديث حالة التحقق من الدفع
#             old_verified = distribution.first_installment_verified
#             distribution.first_installment_verified = first_installment_verified
            
#             # إذا تم التحقق لأول مرة، تسجيل تاريخ التحقق
#             if first_installment_verified and not old_verified:
#                 distribution.verification_date = timezone.now()
#             elif not first_installment_verified and old_verified:
#                 # إذا تم إلغاء التحقق، مسح تاريخ التحقق
#                 distribution.verification_date = None
                
#             distribution.save()
            
#             messages.success(request, f'تم تحديث توزيع الطالب {distribution.student.name} بنجاح')
#             return redirect('books_inventory:student_distribution_detail', pk=distribution.pk)
            
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     context = {
#         'distribution': distribution,
#         'status_choices': StudentDistribution.DISTRIBUTION_STATUS_CHOICES,
#         'page_title': f'تعديل التوزيع - {distribution.student.name}'
#     }
    
#     return render(request, 'books_inventory/edit_distribution.html', context)

# @never_cache
# @login_required
# def create_student_distribution(request):
#     """إنشاء توزيع جديد للطالب مع العناصر المختارة"""
    
#     if request.method == 'POST':
#         try:
#             student_id = request.POST.get('student_id')
#             selected_items_json = request.POST.get('selected_items')
#             distribution_date = request.POST.get('distribution_date')
#             status = request.POST.get('status', 'PENDING')
#             notes = request.POST.get('notes', '')
#             mark_as_distributed = request.POST.get('mark_as_distributed') == 'on'
            
#             # التحقق من البيانات
#             if not student_id or not selected_items_json:
#                 messages.error(request, 'بيانات غير كاملة')
#                 return redirect('books_inventory:create_distribution')
            
#             # الحصول على الطالب
#             student = get_object_or_404(Student, pk=student_id)
            
#             # تحويل العناصر المختارة من JSON
#             import json
#             selected_items = json.loads(selected_items_json)
            
#             # إنشاء التوزيع
#             distribution = StudentDistribution.objects.create(
#                 student=student,
#                 distribution_date=distribution_date,
#                 distributed_by=request.user,
#                 status=status,
#                 notes=notes,
#                 first_installment_verified=True,  # بناءً على فلترة البحث
#                 verification_date=timezone.now()
#             )
            
#             total_items = 0
            
#             # إضافة الكتب
#             for book_data in selected_items.get('books', []):
#                 book = Book.objects.get(id=book_data['id'])
#                 BookDistributionItem.objects.create(
#                     distribution=distribution,
#                     book=book,
#                     quantity_requested=book_data['quantity'],
#                     quantity_distributed=book_data['quantity'] if mark_as_distributed else 0,
#                     is_distributed=mark_as_distributed
#                 )
#                 total_items += book_data['quantity']
                
#                 # تحديث المخزون إذا تم وضع علامة التوزيع
#                 if mark_as_distributed:
#                     book.distributed_count += book_data['quantity']
#                     book.update_stock()
            
#             # إضافة الكراسات
#             for notebook_data in selected_items.get('notebooks', []):
#                 notebook = Notebook.objects.get(id=notebook_data['id'])
#                 NotebookDistributionItem.objects.create(
#                     distribution=distribution,
#                     notebook=notebook,
#                     quantity_requested=notebook_data['quantity'],
#                     quantity_distributed=notebook_data['quantity'] if mark_as_distributed else 0,
#                     is_distributed=mark_as_distributed
#                 )
#                 total_items += notebook_data['quantity']
                
#                 if mark_as_distributed:
#                     notebook.distributed_count += notebook_data['quantity']
#                     notebook.update_stock()
            
#             # إضافة الأدوات
#             for supply_data in selected_items.get('supplies', []):
#                 supply = SchoolSupply.objects.get(id=supply_data['id'])
#                 SupplyDistributionItem.objects.create(
#                     distribution=distribution,
#                     supply=supply,
#                     quantity_requested=supply_data['quantity'],
#                     quantity_distributed=supply_data['quantity'] if mark_as_distributed else 0,
#                     is_distributed=mark_as_distributed
#                 )
#                 total_items += supply_data['quantity']
                
#                 if mark_as_distributed:
#                     supply.distributed_count += supply_data['quantity']
#                     supply.update_stock()
            
#             # تحديث إجمالي العناصر
#             distribution.total_items = total_items
#             distribution.save()
            
#             messages.success(request, f'تم إنشاء التوزيع للطالب {student.name} بنجاح!')
#             return redirect('books_inventory:student_distribution_detail', pk=distribution.pk)
            
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
#             return redirect('books_inventory:create_distribution')
    
#     # GET request
#     context = {
#         'page_title': 'إنشاء توزيع جديد',
#         'today': timezone.now().date()
#     }
    
#     return render(request, 'books_inventory/create_distribution.html', context)



# # البحث عن الطلاب للتوزيع
# @never_cache
# @login_required
# def student_search_for_distribution(request):
#     """البحث عن الطلاب للتوزيع"""
    
#     if request.method == 'GET':
#         query = request.GET.get('q', '').strip()
#         results = []
        
#         if len(query) >= 2:
#             try:
#                 students = Student.objects.filter(
#                     Q(name__icontains=query) |
#                     Q(national_number__icontains=query),
#                     is_active=True
#                 ).select_related('grade_level__education_level')[:10]
                
#                 for student in students:
#                     # التحقق من دفع القسط الأول
#                     first_installment_paid = Tuition.objects.filter(
#                         student=student,
#                         installment_number=1,
#                         payment_status='PAID'
#                     ).exists()
                    
#                     # التحقق من وجود توزيع سابق اليوم
#                     today_distribution = StudentDistribution.objects.filter(
#                         student=student,
#                         distribution_date=timezone.now().date()
#                     ).exists()
                    
#                     results.append({
#                         'id': student.id,
#                         'name': student.name,
#                         'national_number': student.national_number,
#                         'grade_level': student.grade_name,
#                         'education_level': student.education_level_name,
#                         'first_installment_paid': first_installment_paid,
#                         'has_distribution_today': today_distribution,
#                         'can_distribute': first_installment_paid and not today_distribution
#                     })
                    
#             except Exception as e:
#                 return JsonResponse({'error': str(e)})
        
#         return JsonResponse({'results': results})
    
#     return JsonResponse({'error': 'طريقة طلب غير صحيحة'})


# # إدارة النواقص
# @never_cache
# @login_required
# def shortages_list(request):
#     """قائمة النواقص في المخزون"""
    
#     # الفلاتر
#     status_filter = request.GET.get('status', '')
#     item_type_filter = request.GET.get('item_type', '')
#     priority_filter = request.GET.get('priority', '')
    
#     shortages = StockShortage.objects.select_related(
#         'reported_by', 'book__subject', 'notebook', 'supply'
#     ).order_by('-reported_date')
    
#     # تطبيق الفلاتر
#     if status_filter:
#         shortages = shortages.filter(status=status_filter)
    
#     if item_type_filter:
#         shortages = shortages.filter(item_type=item_type_filter)
    
#     if priority_filter:
#         shortages = shortages.filter(priority=priority_filter)
    
#     # Pagination
#     paginator = Paginator(shortages, 20)
#     page_number = request.GET.get('page')
    
#     try:
#         shortages_page = paginator.page(page_number)
#     except PageNotAnInteger:
#         shortages_page = paginator.page(1)
#     except EmptyPage:
#         shortages_page = paginator.page(paginator.num_pages)
    
#     context = {
#         'shortages': shortages_page,
#         'status_filter': status_filter,
#         'item_type_filter': item_type_filter,
#         'priority_filter': priority_filter,
#         'status_choices': StockShortage.SHORTAGE_STATUS_CHOICES,
#         'item_type_choices': StockShortage.ITEM_TYPE_CHOICES,
#         'priority_choices': [('HIGH', 'عالي'), ('MEDIUM', 'متوسط'), ('LOW', 'منخفض')],
#         'page_title': 'النواقص في المخزون'
#     }
    
#     return render(request, 'books_inventory/shortages_list.html', context)


# @csrf_protect
# @require_POST
# @login_required
# def report_shortage(request):
#     """الإبلاغ عن نقص في المخزون"""
    
#     try:
#         item_type = request.POST.get('item_type')
#         item_id = request.POST.get('item_id')
#         required_quantity = int(request.POST.get('required_quantity', 0))
#         priority = request.POST.get('priority', 'MEDIUM')
#         notes = request.POST.get('notes', '')
        
#         # الحصول على العنصر والمخزون الحالي
#         current_stock = 0
#         item_name = ''
#         book = notebook = supply = None
        
#         if item_type == 'BOOK':
#             book = get_object_or_404(Book, pk=item_id)
#             current_stock = book.available_stock
#             item_name = book.title
#         elif item_type == 'NOTEBOOK':
#             notebook = get_object_or_404(Notebook, pk=item_id)
#             current_stock = notebook.available_stock
#             item_name = notebook.name
#         elif item_type == 'SUPPLY':
#             supply = get_object_or_404(SchoolSupply, pk=item_id)
#             current_stock = supply.available_stock
#             item_name = supply.name
        
#         shortage_quantity = max(0, required_quantity - current_stock)
        
#         if shortage_quantity > 0:
#             # إنشاء بلاغ النقص
#             shortage = StockShortage.objects.create(
#                 item_type=item_type,
#                 item_name=item_name,
#                 book=book,
#                 notebook=notebook,
#                 supply=supply,
#                 current_stock=current_stock,
#                 required_quantity=required_quantity,
#                 shortage_quantity=shortage_quantity,
#                 priority=priority,
#                 reported_by=request.user,
#                 notes=notes
#             )
            
#             return JsonResponse({
#                 'success': True,
#                 'message': f'تم الإبلاغ عن نقص في {item_name} بنجاح',
#                 'shortage_id': shortage.id
#             })
#         else:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'المخزون الحالي كافي للكمية المطلوبة'
#             })
            
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'message': f'حدث خطأ: {str(e)}'
#         })


# # تقارير المخزن
# @never_cache
# @login_required
# def inventory_reports(request):
#     """تقارير المخزن"""
    
#     # إحصائيات شاملة
#     try:
#         # إحصائيات الكتب
#         books_stats = {
#             'total_books': Book.objects.filter(is_active=True).count(),
#             'total_stock': Book.objects.filter(is_active=True).aggregate(Sum('total_stock'))['total_stock__sum'] or 0,
#             'available_stock': Book.objects.filter(is_active=True).aggregate(Sum('available_stock'))['available_stock__sum'] or 0,
#             'distributed': Book.objects.filter(is_active=True).aggregate(Sum('distributed_count'))['distributed_count__sum'] or 0,
#             'damaged': Book.objects.filter(is_active=True).aggregate(Sum('damaged_count'))['damaged_count__sum'] or 0,
#             'low_stock_count': Book.objects.filter(is_active=True, available_stock__lte=F('minimum_stock_level')).count()
#         }
        
#         # إحصائيات الكراسات
#         notebooks_stats = {
#             'total_notebooks': Notebook.objects.filter(is_active=True).count(),
#             'total_stock': Notebook.objects.filter(is_active=True).aggregate(Sum('total_stock'))['total_stock__sum'] or 0,
#             'available_stock': Notebook.objects.filter(is_active=True).aggregate(Sum('available_stock'))['available_stock__sum'] or 0,
#             'distributed': Notebook.objects.filter(is_active=True).aggregate(Sum('distributed_count'))['distributed_count__sum'] or 0,
#             'damaged': Notebook.objects.filter(is_active=True).aggregate(Sum('damaged_count'))['damaged_count__sum'] or 0,
#             'low_stock_count': Notebook.objects.filter(is_active=True, available_stock__lte=F('minimum_stock_level')).count()
#         }
        
#         # إحصائيات الأدوات المدرسية
#         supplies_stats = {
#             'total_supplies': SchoolSupply.objects.filter(is_active=True).count(),
#             'total_stock': SchoolSupply.objects.filter(is_active=True).aggregate(Sum('total_stock'))['total_stock__sum'] or 0,
#             'available_stock': SchoolSupply.objects.filter(is_active=True).aggregate(Sum('available_stock'))['available_stock__sum'] or 0,
#             'distributed': SchoolSupply.objects.filter(is_active=True).aggregate(Sum('distributed_count'))['distributed_count__sum'] or 0,
#             'damaged': SchoolSupply.objects.filter(is_active=True).aggregate(Sum('damaged_count'))['damaged_count__sum'] or 0,
#             'low_stock_count': SchoolSupply.objects.filter(is_active=True, available_stock__lte=F('minimum_stock_level')).count()
#         }
        
#         # إحصائيات التوزيع
#         today = timezone.now().date()
#         week_ago = today - timedelta(days=7)
#         month_ago = today - timedelta(days=30)
        
#         distribution_stats = {
#             'today': StudentDistribution.objects.filter(distribution_date=today).count(),
#             'this_week': StudentDistribution.objects.filter(distribution_date__gte=week_ago).count(),
#             'this_month': StudentDistribution.objects.filter(distribution_date__gte=month_ago).count(),
#             'completed': StudentDistribution.objects.filter(status='COMPLETED').count(),
#             'pending': StudentDistribution.objects.filter(status='PENDING').count()
#         }
        
#         # النواقص
#         shortage_stats = {
#             'total_shortages': StockShortage.objects.count(),
#             'pending_shortages': StockShortage.objects.filter(status__in=['REPORTED', 'ACKNOWLEDGED']).count(),
#             'high_priority': StockShortage.objects.filter(priority='HIGH', status__in=['REPORTED', 'ACKNOWLEDGED']).count()
#         }
        
#         # أحدث الأنشطة
#         recent_receipts = StockReceipt.objects.select_related('supplier').order_by('-receipt_date')[:10]
#         recent_distributions = StudentDistribution.objects.select_related('student').order_by('-distribution_date')[:10]
#         recent_shortages = StockShortage.objects.order_by('-reported_date')[:10]
        
#     except Exception as e:
#         print(f"خطأ في تقارير المخزن: {e}")
#         books_stats = notebooks_stats = supplies_stats = distribution_stats = shortage_stats = {}
#         recent_receipts = recent_distributions = recent_shortages = []
    
#     context = {
#         'books_stats': books_stats,
#         'notebooks_stats': notebooks_stats,
#         'supplies_stats': supplies_stats,
#         'distribution_stats': distribution_stats,
#         'shortage_stats': shortage_stats,
#         'recent_receipts': recent_receipts,
#         'recent_distributions': recent_distributions,
#         'recent_shortages': recent_shortages,
#         'today': today,
#         'page_title': 'تقارير المخزن'
#     }
    
#     return render(request, 'books_inventory/inventory_reports.html', context)


# # تصدير التقارير
# @never_cache
# @login_required
# def export_inventory_report(request):
#     """تصدير تقرير المخزن إلى CSV"""
    
#     export_type = request.GET.get('type', 'complete')
    
#     response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
#     response['Content-Disposition'] = f'attachment; filename="inventory_report_{datetime.now().strftime("%Y%m%d_%H%M")}.csv"'
    
#     writer = csv.writer(response)
    
#     if export_type == 'books':
#         # تصدير تقرير الكتب
#         writer.writerow([
#             'عنوان الكتاب', 'المؤلف', 'الناشر', 'المادة الدراسية', 'نوع الكتاب',
#             'إجمالي المخزون', 'المتاح للتوزيع', 'الموزع', 'التالف', 'الحد الأدنى', 'حالة المخزون'
#         ])
        
#         books = Book.objects.filter(is_active=True).select_related('subject').order_by('subject__name', 'title')
        
#         for book in books:
#             writer.writerow([
#                 book.title,
#                 book.author,
#                 book.publisher,
#                 book.subject.name,
#                 book.get_book_type_display(),
#                 book.total_stock,
#                 book.available_stock,
#                 book.distributed_count,
#                 book.damaged_count,
#                 book.minimum_stock_level,
#                 book.stock_status
#             ])
    
#     elif export_type == 'notebooks':
#         # تصدير تقرير الكراسات
#         writer.writerow([
#             'اسم الكراسة', 'النوع', 'الحجم', 'عدد الصفحات',
#             'إجمالي المخزون', 'المتاح للتوزيع', 'الموزع', 'التالف', 'الحد الأدنى', 'حالة المخزون'
#         ])
        
#         notebooks = Notebook.objects.filter(is_active=True).order_by('notebook_type', 'name')
        
#         for notebook in notebooks:
#             writer.writerow([
#                 notebook.name,
#                 notebook.get_notebook_type_display(),
#                 notebook.get_size_display(),
#                 notebook.pages_count,
#                 notebook.total_stock,
#                 notebook.available_stock,
#                 notebook.distributed_count,
#                 notebook.damaged_count,
#                 notebook.minimum_stock_level,
#                 notebook.stock_status
#             ])
    
#     elif export_type == 'supplies':
#         # تصدير تقرير الأدوات المدرسية
#         writer.writerow([
#             'اسم الأداة', 'الفئة', 'الوحدة',
#             'إجمالي المخزون', 'المتاح للتوزيع', 'الموزع', 'التالف', 'الحد الأدنى', 'حالة المخزون'
#         ])
        
#         supplies = SchoolSupply.objects.filter(is_active=True).order_by('category', 'name')
        
#         for supply in supplies:
#             writer.writerow([
#                 supply.name,
#                 supply.get_category_display(),
#                 supply.unit,
#                 supply.total_stock,
#                 supply.available_stock,
#                 supply.distributed_count,
#                 supply.damaged_count,
#                 supply.minimum_stock_level,
#                 supply.stock_status
#             ])
    
#     elif export_type == 'distributions':
#         # تصدير تقرير التوزيعات
#         writer.writerow([
#             'اسم الطالب', 'الرقم القومي', 'الصف الدراسي', 'تاريخ التوزيع',
#             'إجمالي العناصر', 'القسط الأول مدفوع', 'الحالة', 'موزع بواسطة'
#         ])
        
#         distributions = StudentDistribution.objects.select_related(
#             'student', 'distributed_by'
#         ).order_by('-distribution_date')
        
#         for dist in distributions:
#             writer.writerow([
#                 dist.student.name,
#                 dist.student.national_number,
#                 dist.student.grade_name,
#                 dist.distribution_date.strftime('%Y-%m-%d'),
#                 dist.total_items,
#                 'نعم' if dist.first_installment_verified else 'لا',
#                 dist.get_status_display(),
#                 dist.distributed_by.get_full_name() or dist.distributed_by.username
#             ])
    
#     elif export_type == 'shortages':
#         # تصدير تقرير النواقص
#         writer.writerow([
#             'اسم العنصر', 'النوع', 'المخزون الحالي', 'الكمية المطلوبة',
#             'كمية النقص', 'الأولوية', 'الحالة', 'تاريخ البلاغ', 'مُبلغ بواسطة'
#         ])
        
#         shortages = StockShortage.objects.select_related('reported_by').order_by('-reported_date')
        
#         for shortage in shortages:
#             writer.writerow([
#                 shortage.item_name,
#                 shortage.get_item_type_display(),
#                 shortage.current_stock,
#                 shortage.required_quantity,
#                 shortage.shortage_quantity,
#                 shortage.get_priority_display(),
#                 shortage.get_status_display(),
#                 shortage.reported_date.strftime('%Y-%m-%d %H:%M'),
#                 shortage.reported_by.get_full_name() or shortage.reported_by.username
#             ])
    
#     return response


# @never_cache
# @login_required
# def notebook_detail(request, pk):
#     """تفاصيل الكراسة"""
#     notebook = get_object_or_404(Notebook, pk=pk, is_active=True)
    
#     # إحصائيات الكراسة
#     recent_receipts = NotebookReceiptItem.objects.filter(
#         notebook=notebook
#     ).select_related('receipt__supplier').order_by('-receipt__receipt_date')[:10]
    
#     recent_distributions = NotebookDistributionItem.objects.filter(
#         notebook=notebook,
#         is_distributed=True
#     ).select_related('distribution__student').order_by('-distribution_date')[:10]
    
#     # النواقص المُبلغ عنها
#     shortages = StockShortage.objects.filter(
#         notebook=notebook,
#         status__in=['REPORTED', 'ACKNOWLEDGED', 'ORDERED']
#     ).order_by('-reported_date')
    
#     # الصفوف المرتبطة
#     associated_grades = notebook.grade_levels.filter(is_active=True).select_related('education_level')
    
#     context = {
#         'notebook': notebook,
#         'recent_receipts': recent_receipts,
#         'recent_distributions': recent_distributions,
#         'shortages': shortages,
#         'associated_grades': associated_grades,
#         'page_title': f'تفاصيل الكراسة - {notebook.name}'
#     }
    
#     return render(request, 'books_inventory/notebook_detail.html', context)


# @never_cache
# @login_required
# def supply_detail(request, pk):
#     """تفاصيل الأداة المدرسية"""
#     supply = get_object_or_404(SchoolSupply, pk=pk, is_active=True)
    
#     # إحصائيات الأداة المدرسية
#     recent_receipts = SupplyReceiptItem.objects.filter(
#         supply=supply
#     ).select_related('receipt__supplier').order_by('-receipt__receipt_date')[:10]
    
#     recent_distributions = SupplyDistributionItem.objects.filter(
#         supply=supply,
#         is_distributed=True
#     ).select_related('distribution__student').order_by('-distribution_date')[:10]
    
#     # النواقص المُبلغ عنها
#     shortages = StockShortage.objects.filter(
#         supply=supply,
#         status__in=['REPORTED', 'ACKNOWLEDGED', 'ORDERED']
#     ).order_by('-reported_date')
    
#     # الصفوف المرتبطة
#     associated_grades = supply.grade_levels.filter(is_active=True).select_related('education_level')
    
#     context = {
#         'supply': supply,
#         'recent_receipts': recent_receipts,
#         'recent_distributions': recent_distributions,
#         'shortages': shortages,
#         'associated_grades': associated_grades,
#         'page_title': f'تفاصيل الأداة - {supply.name}'
#     }
    
#     return render(request, 'books_inventory/supply_detail.html', context)


# @never_cache
# @login_required
# def supplier_detail(request, pk):
#     """تفاصيل المورد"""
#     supplier = get_object_or_404(Supplier, pk=pk, is_active=True)
    
#     # إحصائيات المورد
#     receipts = StockReceipt.objects.filter(supplier=supplier).order_by('-receipt_date')
    
#     # إجماليات المورد
#     total_receipts = receipts.count()
#     total_cost = receipts.aggregate(total=Sum('total_cost'))['total'] or 0
#     total_items = receipts.aggregate(total=Sum('total_items'))['total'] or 0
    
#     # أحدث الإيصالات
#     recent_receipts = receipts[:10]
    
#     # إحصائيات حسب النوع
#     receipts_by_type = receipts.values('receipt_type').annotate(
#         count=Count('id'),
#         total_cost=Sum('total_cost'),
#         total_items=Sum('total_items')
#     ).order_by('-count')
    
#     # إحصائيات شهرية (آخر 6 أشهر)
#     from django.db.models import Q
#     from datetime import date, timedelta
#     import calendar
    
#     today = timezone.now().date()
#     six_months_ago = today - timedelta(days=180)
    
#     monthly_stats = []
#     for i in range(6):
#         month_start = date(today.year, today.month - i, 1) if today.month > i else date(today.year - 1, today.month - i + 12, 1)
#         if month_start < six_months_ago:
#             break
            
#         month_end = date(month_start.year, month_start.month, calendar.monthrange(month_start.year, month_start.month)[1])
        
#         month_receipts = receipts.filter(
#             receipt_date__gte=month_start,
#             receipt_date__lte=month_end
#         ).aggregate(
#             count=Count('id'),
#             total_cost=Sum('total_cost'),
#             total_items=Sum('total_items')
#         )
        
#         monthly_stats.append({
#             'month': month_start.strftime('%Y-%m'),
#             'month_name': f"{calendar.month_name[month_start.month]} {month_start.year}",
#             'count': month_receipts['count'] or 0,
#             'total_cost': month_receipts['total_cost'] or 0,
#             'total_items': month_receipts['total_items'] or 0
#         })
    
#     context = {
#         'supplier': supplier,
#         'recent_receipts': recent_receipts,
#         'total_receipts': total_receipts,
#         'total_cost': total_cost,
#         'total_items': total_items,
#         'receipts_by_type': receipts_by_type,
#         'monthly_stats': monthly_stats,
#         'page_title': f'تفاصيل المورد - {supplier.name}'
#     }
    
#     return render(request, 'books_inventory/supplier_detail.html', context)

# # إضافة هذه الـ views إلى نهاية الملف

# @never_cache
# @login_required
# def student_search_view(request):
#     """البحث عن الطلاب (للعرض فقط - موظف المخزن)"""
    
#     students = []
#     search_query = ''
#     total_results = 0
    
#     if request.method == 'GET' and 'search' in request.GET:
#         search_query = request.GET.get('search', '').strip()
        
#         if search_query and len(search_query) >= 2:
#             try:
#                 # البحث في الطلاب النشطين
#                 from students.models import Student
#                 students_queryset = Student.objects.filter(
#                     Q(name__icontains=search_query) | 
#                     Q(national_number__icontains=search_query) |
#                     Q(phone_number__icontains=search_query),
#                     is_active=True
#                 ).select_related(
#                     'grade_level__education_level',
#                     'academic_year'
#                 ).order_by('name')
                
#                 total_results = students_queryset.count()
                
#                 # Pagination
#                 paginator = Paginator(students_queryset, 15)
#                 page_number = request.GET.get('page')
                
#                 try:
#                     students = paginator.page(page_number)
#                 except PageNotAnInteger:
#                     students = paginator.page(1)
#                 except EmptyPage:
#                     students = paginator.page(paginator.num_pages)
                
#                 # إضافة بيانات المدفوعات لكل طالب
#                 for student in students:
#                     try:
#                         # حالة القسط الأول
#                         from payments.models import Tuition
#                         first_installment = Tuition.objects.filter(
#                             student=student,
#                             installment_number=1
#                         ).first()
                        
#                         student.first_installment_status = 'مدفوع' if (
#                             first_installment and first_installment.payment_status == 'PAID'
#                         ) else 'غير مدفوع'
                        
#                         student.first_installment_date = first_installment.payment_date if (
#                             first_installment and first_installment.payment_status == 'PAID'
#                         ) else None
                        
#                         # إجمالي المدفوعات والمستحقات
#                         student.payment_summary = {
#                             'total_fees': student.total_fees or 0,
#                             'total_payments': student.total_payments or 0,
#                             'total_owed': student.total_owed or 0
#                         }
                        
#                         # حالة التوزيع السابقة
#                         latest_distribution = StudentDistribution.objects.filter(
#                             student=student
#                         ).order_by('-distribution_date').first()
                        
#                         student.latest_distribution = latest_distribution
                        
#                     except Exception as e:
#                         print(f"خطأ في البحث عن بيانات الطالب {student.name}: {e}")
#                         student.first_installment_status = 'غير معروف'
#                         student.payment_summary = {'total_fees': 0, 'total_payments': 0, 'total_owed': 0}
#                         student.latest_distribution = None
                        
#             except Exception as e:
#                 print(f"خطأ في البحث عن الطلاب: {e}")
#                 messages.error(request, f'حدث خطأ أثناء البحث: {str(e)}')
#                 students = []
    
#     context = {
#         'students': students,
#         'search_query': search_query,
#         'total_results': total_results,
#         'page_title': 'البحث عن الطلاب'
#     }
    
#     return render(request, 'books_inventory/student_search.html', context)


# @never_cache
# @login_required
# def student_payments_view(request):
#     """عرض حالة مدفوعات الطلاب (للعرض فقط)"""
    
#     # فلاتر
#     grade_filter = request.GET.get('grade', '')
#     payment_status_filter = request.GET.get('payment_status', '')
    
#     try:
#         from students.models import Student
#         from payments.models import Tuition
        
#         # الحصول على الطلاب مع بياناتهم المالية
#         students = Student.objects.filter(is_active=True).select_related(
#             'grade_level__education_level',
#             'academic_year'
#         )
        
#         # تطبيق الفلاتر
#         if grade_filter:
#             students = students.filter(grade_level_id=grade_filter)
        
#         # إضافة بيانات المدفوعات
#         students_with_payments = []
        
#         for student in students:
#             try:
#                 # حالة القسط الأول
#                 first_installment = Tuition.objects.filter(
#                     student=student,
#                     installment_number=1
#                 ).first()
                
#                 first_installment_paid = bool(
#                     first_installment and first_installment.payment_status == 'PAID'
#                 )
                
#                 # تطبيق فلتر حالة الدفع
#                 if payment_status_filter:
#                     if payment_status_filter == 'paid' and not first_installment_paid:
#                         continue
#                     elif payment_status_filter == 'unpaid' and first_installment_paid:
#                         continue
                
#                 # حساب إجماليات المدفوعات
#                 tuitions = Tuition.objects.filter(student=student)
                
#                 # إجمالي المصروفات (مجموع amount_tuition)
#                 total_fees = tuitions.aggregate(Sum('amount_tuition'))['amount_tuition__sum'] or 0
                
#                 # إجمالي المدفوع (مجموع amount_paid)
#                 total_payments = tuitions.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
                
#                 # المتبقي
#                 total_owed = total_fees - total_payments
                
#                 # إضافة البيانات المالية
#                 student_data = {
#                     'student': student,
#                     'first_installment_paid': first_installment_paid,
#                     'first_installment_date': first_installment.payment_date if (first_installment_paid and first_installment) else None,
#                     'total_fees': total_fees,
#                     'total_payments': total_payments,
#                     'total_owed': total_owed,
#                     'payment_percentage': (
#                         (total_payments / total_fees * 100) 
#                         if total_fees and total_fees > 0 else 0
#                     )
#                 }
                
#                 # حالة التوزيع الأخيرة
#                 latest_distribution = StudentDistribution.objects.filter(
#                     student=student
#                 ).order_by('-distribution_date').first()
                
#                 student_data['latest_distribution'] = latest_distribution
#                 student_data['can_distribute'] = first_installment_paid
                
#                 students_with_payments.append(student_data)
                
#             except Exception as e:
#                 print(f"خطأ في معالجة بيانات الطالب {student.name}: {e}")
        
#         # ترتيب النتائج
#         students_with_payments.sort(key=lambda x: x['student'].name)
        
#         # Pagination
#         paginator = Paginator(students_with_payments, 20)
#         page_number = request.GET.get('page')
        
#         try:
#             students_page = paginator.page(page_number)
#         except PageNotAnInteger:
#             students_page = paginator.page(1)
#         except EmptyPage:
#             students_page = paginator.page(paginator.num_pages)
        
#         # بيانات للفلاتر
#         from school_settings.models import GradeLevel
#         grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
        
#         # إحصائيات سريعة
#         total_students = len(students_with_payments)
#         paid_students = sum(1 for s in students_with_payments if s['first_installment_paid'])
#         unpaid_students = total_students - paid_students
        
#         context = {
#             'students_page': students_page,
#             'grade_levels': grade_levels,
#             'grade_filter': grade_filter,
#             'payment_status_filter': payment_status_filter,
#             'stats': {
#                 'total': total_students,
#                 'paid': paid_students,
#                 'unpaid': unpaid_students
#             },
#             'page_title': 'حالة مدفوعات الطلاب'
#         }
        
#     except Exception as e:
#         print(f"خطأ في عرض مدفوعات الطلاب: {e}")
#         context = {
#             'students_page': [],
#             'grade_levels': [],
#             'stats': {'total': 0, 'paid': 0, 'unpaid': 0},
#             'error_message': f'حدث خطأ في تحميل البيانات: {str(e)}',
#             'page_title': 'حالة مدفوعات الطلاب'
#         }
    
#     return render(request, 'books_inventory/student_payments.html', context)

# @never_cache
# @login_required
# def student_detail_view(request, pk):
#     """عرض تفاصيل الطالب (للعرض فقط - موظف المخزن)"""
    
#     try:
#         from students.models import Student
#         from payments.models import Tuition
        
#         student = get_object_or_404(Student, pk=pk, is_active=True)
        
#         # بيانات المدفوعات
#         tuitions = Tuition.objects.filter(student=student).order_by('installment_number')
        
#         # إنشاء قائمة بالأقساط مع حساب المتبقي
#         tuitions_with_remaining = []
#         for tuition in tuitions:
#             # إنشاء dictionary للقسط مع البيانات المطلوبة
#             tuition_data = {
#                 'tuition': tuition,
#                 'installment_number': tuition.installment_number,
#                 'amount_tuition': tuition.amount_tuition or 0,
#                 'amount_paid': tuition.amount_paid or 0,
#                 'remaining_amount': (tuition.amount_tuition or 0) - (tuition.amount_paid or 0),
#                 'due_date': tuition.due_date,
#                 'payment_date': tuition.payment_date,
#                 'payment_status': tuition.payment_status,
#                 'payment_method': tuition.payment_method,
#                 'notes': tuition.notes,
#                 'get_payment_status_display': tuition.get_payment_status_display(),
#                 'get_payment_method_display': tuition.get_payment_method_display(),
#             }
#             tuitions_with_remaining.append(tuition_data)
        
#         # حالة القسط الأول
#         first_installment = tuitions.filter(installment_number=1).first()
#         first_installment_paid = bool(
#             first_installment and first_installment.payment_status == 'PAID'
#         )
        
#         # إحصائيات المدفوعات
#         payment_stats = {
#             'total_installments': tuitions.count(),
#             'paid_installments': tuitions.filter(payment_status='PAID').count(),
#             'pending_installments': tuitions.filter(payment_status='PENDING').count(),
#             'overdue_installments': tuitions.filter(payment_status='OVERDUE').count(),
#             'partially_paid_installments': tuitions.filter(payment_status='PARTIALLY_PAID').count(),
#         }
        
#         # إضافة المبالغ المالية
#         total_fees = tuitions.aggregate(Sum('amount_tuition'))['amount_tuition__sum'] or 0
#         total_payments = tuitions.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
#         total_owed = total_fees - total_payments
#         payment_percentage = round((total_payments / total_fees * 100) if total_fees > 0 else 0, 1)
        
#         # تاريخ التوزيعات
#         distributions = StudentDistribution.objects.filter(
#             student=student
#         ).order_by('-distribution_date')
        
#         # آخر توزيع
#         latest_distribution = distributions.first()
        
#         # إمكانية التوزيع
#         can_distribute = first_installment_paid and not StudentDistribution.objects.filter(
#             student=student,
#             distribution_date=timezone.now().date()
#         ).exists()
        
#         context = {
#             'student': student,
#             'tuitions_with_remaining': tuitions_with_remaining,
#             'first_installment_paid': first_installment_paid,
#             'first_installment_date': first_installment.payment_date if first_installment_paid else None,
#             'payment_stats': payment_stats,
#             'total_fees': total_fees,
#             'total_payments': total_payments,
#             'total_owed': total_owed,
#             'payment_percentage': payment_percentage,
#             'distributions': distributions,
#             'latest_distribution': latest_distribution,
#             'can_distribute': can_distribute,
#             'page_title': f'تفاصيل الطالب - {student.name}'
#         }
        
#     except Exception as e:
#         print(f"خطأ في عرض تفاصيل الطالب: {e}")
#         messages.error(request, f'حدث خطأ في تحميل بيانات الطالب: {str(e)}')
#         return redirect('books_inventory:student_search_view')
    
#     return render(request, 'books_inventory/student_detail_view.html', context)

# @require_http_methods(["GET"])
# @login_required
# def student_search_api(request):
#     """API للبحث عن الطلاب - AJAX"""
    
#     query = request.GET.get('q', '').strip()
    
#     if len(query) < 2:
#         return JsonResponse({
#             'error': 'يجب إدخال حرفين على الأقل للبحث',
#             'results': []
#         })
    
#     try:
#         from students.models import Student
#         from payments.models import Tuition
#         from django.db.models import Q
        
#         # البحث في الطلاب النشطين
#         students = Student.objects.filter(
#             Q(name__icontains=query) | 
#             Q(national_number__icontains=query) |
#             Q(phone_number__icontains=query),
#             is_active=True
#         ).select_related(
#             'grade_level__education_level',
#             'academic_year'
#         ).order_by('name')[:20]  # الحد الأقصى 20 نتيجة
        
#         results = []
#         for student in students:
#             try:
#                 # حالة القسط الأول
#                 first_installment = Tuition.objects.filter(
#                     student=student,
#                     installment_number=1
#                 ).first()
                
#                 first_installment_paid = bool(
#                     first_installment and first_installment.payment_status == 'PAID'
#                 )
                
#                 # التحقق من وجود توزيع اليوم
#                 has_distribution_today = StudentDistribution.objects.filter(
#                     student=student,
#                     distribution_date=timezone.now().date()
#                 ).exists()
                
#                 can_distribute = first_installment_paid and not has_distribution_today
                
#                 student_data = {
#                     'id': student.id,
#                     'name': student.name,
#                     'national_number': student.national_number,
#                     'phone_number': student.phone_number or '',
#                     'grade_level': student.grade_level.name if student.grade_level else 'غير محدد',
#                     'education_level': student.grade_level.education_level.name if (student.grade_level and student.grade_level.education_level) else 'غير محدد',
#                     'first_installment_paid': first_installment_paid,
#                     'can_distribute': can_distribute,
#                     'has_distribution_today': has_distribution_today
#                 }
                
#                 results.append(student_data)
                
#             except Exception as e:
#                 print(f"خطأ في معالجة بيانات الطالب {student.name}: {e}")
#                 continue
        
#         return JsonResponse({
#             'results': results,
#             'total_count': len(results)
#         })
        
#     except Exception as e:
#         print(f"خطأ في API البحث: {e}")
#         return JsonResponse({
#             'error': f'حدث خطأ في البحث: {str(e)}',
#             'results': []
#         })

# @never_cache
# @login_required
# def suppliers_list(request):
#     """قائمة الموردين"""
    
#     search_query = request.GET.get('search', '')
    
#     # الحصول على الموردين
#     suppliers = Supplier.objects.all().order_by('name')
    
#     # تطبيق البحث
#     if search_query:
#         suppliers = suppliers.filter(
#             Q(name__icontains=search_query) |
#             Q(contact_person__icontains=search_query) |
#             Q(phone_number__icontains=search_query) |
#             Q(email__icontains=search_query)
#         )
    
#     # Pagination
#     paginator = Paginator(suppliers, 12)
#     page_number = request.GET.get('page')
    
#     try:
#         suppliers_page = paginator.page(page_number)
#     except PageNotAnInteger:
#         suppliers_page = paginator.page(1)
#     except EmptyPage:
#         suppliers_page = paginator.page(paginator.num_pages)
    
#     context = {
#         'suppliers': suppliers_page,
#         'search_query': search_query,
#         'page_title': 'قائمة الموردين'
#     }
    
#     return render(request, 'books_inventory/suppliers_list.html', context)


# @never_cache
# @login_required
# def supplier_detail(request, pk):
#     """تفاصيل المورد"""
    
#     supplier = get_object_or_404(Supplier, pk=pk)
    
#     # إحصائيات المورد
#     receipts = StockReceipt.objects.filter(supplier=supplier).order_by('-receipt_date')
    
#     # إجماليات
#     total_receipts = receipts.count()
#     total_items = receipts.aggregate(Sum('total_items'))['total_items__sum'] or 0
#     total_cost = receipts.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    
#     # آخر الإيصالات
#     recent_receipts = receipts[:5]
    
#     context = {
#         'supplier': supplier,
#         'recent_receipts': recent_receipts,
#         'total_receipts': total_receipts,
#         'total_items': total_items,
#         'total_cost': total_cost,
#         'page_title': f'تفاصيل المورد - {supplier.name}'
#     }
    
#     return render(request, 'books_inventory/supplier_detail.html', context)


# @never_cache
# @login_required
# def add_supplier(request):
#     """إضافة مورد جديد"""
    
#     if request.method == 'POST':
#         try:
#             # البيانات الأساسية
#             name = request.POST.get('name', '').strip()
#             contact_person = request.POST.get('contact_person', '').strip()
#             phone_number = request.POST.get('phone_number', '').strip()
#             email = request.POST.get('email', '').strip()
#             address = request.POST.get('address', '').strip()
#             notes = request.POST.get('notes', '').strip()
#             is_active = request.POST.get('is_active') == 'on'
            
#             # التحقق من البيانات المطلوبة
#             if not name:
#                 messages.error(request, 'اسم المورد مطلوب')
#                 return redirect('books_inventory:add_supplier')
            
#             # التحقق من عدم التكرار
#             if Supplier.objects.filter(name=name).exists():
#                 messages.error(request, f'يوجد مورد بنفس الاسم "{name}" بالفعل')
#                 return redirect('books_inventory:add_supplier')
            
#             # إنشاء المورد
#             supplier = Supplier.objects.create(
#                 name=name,
#                 contact_person=contact_person,
#                 phone_number=phone_number,
#                 email=email,
#                 address=address,
#                 notes=notes,
#                 is_active=is_active
#             )
            
#             messages.success(request, f'تم إضافة المورد "{supplier.name}" بنجاح')
#             return redirect('books_inventory:supplier_detail', pk=supplier.pk)
            
#         except Exception as e:
#             print(f"خطأ في إضافة المورد: {e}")
#             messages.error(request, f'حدث خطأ في إضافة المورد: {str(e)}')
#             return redirect('books_inventory:add_supplier')
    
#     context = {
#         'page_title': 'إضافة مورد جديد'
#     }
    
#     return render(request, 'books_inventory/add_supplier.html', context)


# @never_cache
# @login_required
# def edit_supplier(request, pk):
#     """تعديل بيانات المورد"""
    
#     supplier = get_object_or_404(Supplier, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             # البيانات الأساسية
#             name = request.POST.get('name', '').strip()
#             contact_person = request.POST.get('contact_person', '').strip()
#             phone_number = request.POST.get('phone_number', '').strip()
#             email = request.POST.get('email', '').strip()
#             address = request.POST.get('address', '').strip()
#             notes = request.POST.get('notes', '').strip()
#             is_active = request.POST.get('is_active') == 'on'
            
#             # التحقق من البيانات المطلوبة
#             if not name:
#                 messages.error(request, 'اسم المورد مطلوب')
#                 return redirect('books_inventory:edit_supplier', pk=pk)
            
#             # التحقق من عدم التكرار (عدا المورد الحالي)
#             if Supplier.objects.filter(name=name).exclude(pk=pk).exists():
#                 messages.error(request, f'يوجد مورد آخر بنفس الاسم "{name}" بالفعل')
#                 return redirect('books_inventory:edit_supplier', pk=pk)
            
#             # تحديث المورد
#             supplier.name = name
#             supplier.contact_person = contact_person
#             supplier.phone_number = phone_number
#             supplier.email = email
#             supplier.address = address
#             supplier.notes = notes
#             supplier.is_active = is_active
#             supplier.save()
            
#             messages.success(request, f'تم تحديث بيانات المورد "{supplier.name}" بنجاح')
#             return redirect('books_inventory:supplier_detail', pk=supplier.pk)
            
#         except Exception as e:
#             print(f"خطأ في تحديث المورد: {e}")
#             messages.error(request, f'حدث خطأ في تحديث المورد: {str(e)}')
#             return redirect('books_inventory:edit_supplier', pk=pk)
    
#     context = {
#         'supplier': supplier,
#         'page_title': f'تعديل المورد - {supplier.name}'
#     }
    
#     return render(request, 'books_inventory/edit_supplier.html', context)

# @never_cache
# @login_required
# def add_book(request):
#     """إضافة كتاب جديد"""
    
#     if request.method == 'POST':
#         try:
#             # البيانات الأساسية
#             title = request.POST.get('title', '').strip()
#             book_type = request.POST.get('book_type', '')
#             subject_id = request.POST.get('subject', '')
#             academic_year = request.POST.get('academic_year', '').strip()
#             term = request.POST.get('term', 'FULL_YEAR')
#             edition_year = request.POST.get('edition_year', '').strip()
#             pages_count = request.POST.get('pages_count', '')
#             description = request.POST.get('description', '').strip()
#             cost_price = request.POST.get('cost_price', '0')
#             minimum_stock_level = request.POST.get('minimum_stock_level', '10')
#             is_active = request.POST.get('is_active') == 'on'
            
#             # التحقق من البيانات المطلوبة
#             if not title:
#                 messages.error(request, 'عنوان الكتاب مطلوب')
#                 return redirect('books_inventory:add_book')
            
#             if not subject_id:
#                 messages.error(request, 'المادة الدراسية مطلوبة')
#                 return redirect('books_inventory:add_book')
            
#             # إنشاء الكتاب
#             book = Book.objects.create(
#                 title=title,
#                 book_type=book_type,
#                 subject_id=subject_id,
#                 academic_year=academic_year,
#                 term=term,
#                 edition_year=edition_year,
#                 pages_count=int(pages_count) if pages_count else None,
#                 description=description,
#                 cost_price=Decimal(cost_price),
#                 minimum_stock_level=int(minimum_stock_level),
#                 is_active=is_active
#             )
            
#             # إضافة الصفوف الدراسية
#             grade_levels = request.POST.getlist('grade_levels')
#             if grade_levels:
#                 book.grade_levels.set(grade_levels)
            
#             messages.success(request, f'تم إضافة الكتاب "{book.title}" بنجاح')
#             return redirect('books_inventory:book_detail', pk=book.pk)
            
#         except Exception as e:
#             print(f"خطأ في إضافة الكتاب: {e}")
#             messages.error(request, f'حدث خطأ في إضافة الكتاب: {str(e)}')
#             return redirect('books_inventory:add_book')
    
#     # GET request
#     subjects = Subject.objects.filter(is_active=True).order_by('name')
#     from school_settings.models import GradeLevel
#     grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    
#     context = {
#         'subjects': subjects,
#         'grade_levels': grade_levels,
#         'book_type_choices': Book.BOOK_TYPE_CHOICES,
#         'term_choices': [
#             ('FIRST', 'الترم الأول'),
#             ('SECOND', 'الترم الثاني'),
#             ('FULL_YEAR', 'السنة كاملة')
#         ],
#         'page_title': 'إضافة كتاب جديد'
#     }
    
#     return render(request, 'books_inventory/add_book.html', context)


# @never_cache
# @login_required
# def add_notebook(request):
#     """إضافة كراسة جديدة"""
    
#     if request.method == 'POST':
#         try:
#             # البيانات الأساسية
#             name = request.POST.get('name', '').strip()
#             notebook_type = request.POST.get('notebook_type', '')
#             size = request.POST.get('size', '')
#             pages_count = request.POST.get('pages_count', '')
#             cost_price = request.POST.get('cost_price', '0')
#             minimum_stock_level = request.POST.get('minimum_stock_level', '10')
#             is_active = request.POST.get('is_active') == 'on'
            
#             # التحقق من البيانات المطلوبة
#             if not name:
#                 messages.error(request, 'اسم الكراسة مطلوب')
#                 return redirect('books_inventory:add_notebook')
            
#             # إنشاء الكراسة
#             notebook = Notebook.objects.create(
#                 name=name,
#                 notebook_type=notebook_type,
#                 size=size,
#                 pages_count=int(pages_count) if pages_count else 100,
#                 cost_price=Decimal(cost_price),
#                 minimum_stock_level=int(minimum_stock_level),
#                 is_active=is_active
#             )
            
#             # إضافة الصفوف الدراسية
#             grade_levels = request.POST.getlist('grade_levels')
#             if grade_levels:
#                 notebook.grade_levels.set(grade_levels)
            
#             messages.success(request, f'تم إضافة الكراسة "{notebook.name}" بنجاح')
#             return redirect('books_inventory:notebook_detail', pk=notebook.pk)
            
#         except Exception as e:
#             print(f"خطأ في إضافة الكراسة: {e}")
#             messages.error(request, f'حدث خطأ في إضافة الكراسة: {str(e)}')
#             return redirect('books_inventory:add_notebook')
    
#     # GET request
#     from school_settings.models import GradeLevel
#     grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    
#     context = {
#         'grade_levels': grade_levels,
#         'notebook_type_choices': Notebook.NOTEBOOK_TYPE_CHOICES,
#         'size_choices': Notebook.SIZE_CHOICES,
#         'page_title': 'إضافة كراسة جديدة'
#     }
    
#     return render(request, 'books_inventory/add_notebook.html', context)


# @never_cache
# @login_required
# def add_supply(request):
#     """إضافة أداة مدرسية جديدة"""
    
#     if request.method == 'POST':
#         try:
#             # البيانات الأساسية
#             name = request.POST.get('name', '').strip()
#             category = request.POST.get('category', '')
#             unit = request.POST.get('unit', '').strip()
#             description = request.POST.get('description', '').strip()
#             cost_price = request.POST.get('cost_price', '0')
#             minimum_stock_level = request.POST.get('minimum_stock_level', '10')
#             is_active = request.POST.get('is_active') == 'on'
            
#             # التحقق من البيانات المطلوبة
#             if not name:
#                 messages.error(request, 'اسم الأداة المدرسية مطلوب')
#                 return redirect('books_inventory:add_supply')
            
#             if not unit:
#                 messages.error(request, 'وحدة القياس مطلوبة')
#                 return redirect('books_inventory:add_supply')
            
#             # إنشاء الأداة المدرسية
#             supply = SchoolSupply.objects.create(
#                 name=name,
#                 category=category,
#                 unit=unit,
#                 description=description,
#                 cost_price=Decimal(cost_price),
#                 minimum_stock_level=int(minimum_stock_level),
#                 is_active=is_active
#             )
            
#             # إضافة الصفوف الدراسية
#             grade_levels = request.POST.getlist('grade_levels')
#             if grade_levels:
#                 supply.grade_levels.set(grade_levels)
            
#             messages.success(request, f'تم إضافة الأداة المدرسية "{supply.name}" بنجاح')
#             return redirect('books_inventory:supply_detail', pk=supply.pk)
            
#         except Exception as e:
#             print(f"خطأ في إضافة الأداة المدرسية: {e}")
#             messages.error(request, f'حدث خطأ في إضافة الأداة المدرسية: {str(e)}')
#             return redirect('books_inventory:add_supply')
    
#     # GET request
#     from school_settings.models import GradeLevel
#     grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    
#     context = {
#         'grade_levels': grade_levels,
#         'category_choices': SchoolSupply.CATEGORY_CHOICES,
#         'page_title': 'إضافة أداة مدرسية جديدة'
#     }
    
#     return render(request, 'books_inventory/add_supply.html', context)

# # إضافة views التحديث والحذف للكراسات
# @never_cache
# @login_required
# def edit_notebook(request, pk):
#     """تعديل كراسة"""
#     notebook = get_object_or_404(Notebook, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             notebook.name = request.POST.get('name', '').strip()
#             notebook.notebook_type = request.POST.get('notebook_type', '')
#             notebook.size = request.POST.get('size', '')
#             notebook.pages_count = int(request.POST.get('pages_count', '100'))
#             notebook.cost_price = Decimal(request.POST.get('cost_price', '0'))
#             notebook.minimum_stock_level = int(request.POST.get('minimum_stock_level', '10'))
#             notebook.is_active = request.POST.get('is_active') == 'on'
            
#             if not notebook.name:
#                 messages.error(request, 'اسم الكراسة مطلوب')
#                 return redirect('books_inventory:edit_notebook', pk=pk)
            
#             notebook.save()
            
#             # تحديث الصفوف الدراسية
#             grade_levels = request.POST.getlist('grade_levels')
#             notebook.grade_levels.set(grade_levels)
            
#             messages.success(request, f'تم تحديث الكراسة "{notebook.name}" بنجاح')
#             return redirect('books_inventory:notebook_detail', pk=notebook.pk)
            
#         except Exception as e:
#             print(f"خطأ في تحديث الكراسة: {e}")
#             messages.error(request, f'حدث خطأ في تحديث الكراسة: {str(e)}')
    
#     from school_settings.models import GradeLevel
#     grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    
#     context = {
#         'notebook': notebook,
#         'grade_levels': grade_levels,
#         'notebook_type_choices': Notebook.NOTEBOOK_TYPE_CHOICES,
#         'size_choices': Notebook.SIZE_CHOICES,
#         'page_title': f'تعديل الكراسة - {notebook.name}'
#     }
    
#     return render(request, 'books_inventory/edit_notebook.html', context)


# @never_cache
# @login_required
# def delete_notebook(request, pk):
#     """حذف كراسة"""
#     notebook = get_object_or_404(Notebook, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             notebook_name = notebook.name
#             notebook.delete()
#             messages.success(request, f'تم حذف الكراسة "{notebook_name}" بنجاح')
#             return redirect('books_inventory:notebooks_list')
#         except Exception as e:
#             messages.error(request, f'لا يمكن حذف الكراسة: {str(e)}')
#             return redirect('books_inventory:notebook_detail', pk=pk)
    
#     context = {
#         'notebook': notebook,
#         'page_title': f'حذف الكراسة - {notebook.name}'
#     }
    
#     return render(request, 'books_inventory/delete_notebook.html', context)


# # إضافة views التحديث والحذف للأدوات المدرسية
# @never_cache
# @login_required
# def edit_supply(request, pk):
#     """تعديل أداة مدرسية"""
#     supply = get_object_or_404(SchoolSupply, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             supply.name = request.POST.get('name', '').strip()
#             supply.category = request.POST.get('category', '')
#             supply.unit = request.POST.get('unit', '').strip()
#             supply.description = request.POST.get('description', '').strip()
#             supply.cost_price = Decimal(request.POST.get('cost_price', '0'))
#             supply.minimum_stock_level = int(request.POST.get('minimum_stock_level', '10'))
#             supply.is_active = request.POST.get('is_active') == 'on'
            
#             if not supply.name:
#                 messages.error(request, 'اسم الأداة مطلوب')
#                 return redirect('books_inventory:edit_supply', pk=pk)
            
#             if not supply.unit:
#                 messages.error(request, 'وحدة القياس مطلوبة')
#                 return redirect('books_inventory:edit_supply', pk=pk)
            
#             supply.save()
            
#             # تحديث الصفوف الدراسية
#             grade_levels = request.POST.getlist('grade_levels')
#             supply.grade_levels.set(grade_levels)
            
#             messages.success(request, f'تم تحديث الأداة "{supply.name}" بنجاح')
#             return redirect('books_inventory:supply_detail', pk=supply.pk)
            
#         except Exception as e:
#             print(f"خطأ في تحديث الأداة: {e}")
#             messages.error(request, f'حدث خطأ في تحديث الأداة: {str(e)}')
    
#     from school_settings.models import GradeLevel
#     grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    
#     context = {
#         'supply': supply,
#         'grade_levels': grade_levels,
#         'category_choices': SchoolSupply.CATEGORY_CHOICES,
#         'page_title': f'تعديل الأداة - {supply.name}'
#     }
    
#     return render(request, 'books_inventory/edit_supply.html', context)


# @never_cache
# @login_required
# def delete_supply(request, pk):
#     """حذف أداة مدرسية"""
#     supply = get_object_or_404(SchoolSupply, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             supply_name = supply.name
#             supply.delete()
#             messages.success(request, f'تم حذف الأداة "{supply_name}" بنجاح')
#             return redirect('books_inventory:supplies_list')
#         except Exception as e:
#             messages.error(request, f'لا يمكن حذف الأداة: {str(e)}')
#             return redirect('books_inventory:supply_detail', pk=pk)
    
#     context = {
#         'supply': supply,
#         'page_title': f'حذف الأداة - {supply.name}'
#     }
    
#     return render(request, 'books_inventory/delete_supply.html', context)

# @never_cache
# @login_required
# def subjects_list(request):
#     """قائمة المواد الدراسية"""
    
#     search_query = request.GET.get('search', '')
#     is_active_filter = request.GET.get('is_active', '')
    
#     # الحصول على المواد
#     subjects = Subject.objects.all().order_by('name')
    
#     # تطبيق البحث
#     if search_query:
#         subjects = subjects.filter(
#             Q(name__icontains=search_query) |
#             Q(description__icontains=search_query)
#         )
    
#     # تطبيق فلتر الحالة
#     if is_active_filter:
#         subjects = subjects.filter(is_active=is_active_filter == 'true')
    
#     # Pagination
#     paginator = Paginator(subjects, 12)
#     page_number = request.GET.get('page')
    
#     try:
#         subjects_page = paginator.page(page_number)
#     except PageNotAnInteger:
#         subjects_page = paginator.page(1)
#     except EmptyPage:
#         subjects_page = paginator.page(paginator.num_pages)
    
#     context = {
#         'subjects': subjects_page,
#         'search_query': search_query,
#         'is_active_filter': is_active_filter,
#         'page_title': 'قائمة المواد الدراسية'
#     }
    
#     return render(request, 'books_inventory/subjects_list.html', context)


# @never_cache
# @login_required
# def subject_detail(request, pk):
#     """تفاصيل المادة الدراسية"""
    
#     subject = get_object_or_404(Subject, pk=pk)
    
#     # إحصائيات المادة
#     books_count = Book.objects.filter(subject=subject).count()
#     active_books = Book.objects.filter(subject=subject, is_active=True).count()
#     total_books_stock = Book.objects.filter(subject=subject).aggregate(Sum('total_stock'))['total_stock__sum'] or 0
    
#     # أحدث الكتب للمادة
#     recent_books = Book.objects.filter(subject=subject).order_by('-created_at')[:5]
    
#     context = {
#         'subject': subject,
#         'books_count': books_count,
#         'active_books': active_books,
#         'total_books_stock': total_books_stock,
#         'recent_books': recent_books,
#         'page_title': f'تفاصيل المادة - {subject.name}'
#     }
    
#     return render(request, 'books_inventory/subject_detail.html', context)


# @never_cache
# @login_required
# def add_subject(request):
#     """إضافة مادة دراسية جديدة مع ربطها بالصفوف"""
    
#     if request.method == 'POST':
#         try:
#             # البيانات الأساسية
#             name = request.POST.get('name', '').strip()
#             name_en = request.POST.get('name_en', '').strip()
#             description = request.POST.get('description', '').strip()
#             subject_code = request.POST.get('subject_code', '').strip()
#             color = request.POST.get('color', '#007bff')
#             is_active = request.POST.get('is_active') == 'on'
#             is_core_subject = request.POST.get('is_core_subject') == 'on'
#             weekly_hours = int(request.POST.get('weekly_hours', 2))
            
#             # الصفوف الدراسية المختارة
#             selected_grade_levels = request.POST.getlist('grade_levels')
#             selected_education_levels = request.POST.getlist('education_levels')
            
#             # التحقق من البيانات المطلوبة
#             if not name:
#                 messages.error(request, 'اسم المادة مطلوب')
#                 return redirect('books_inventory:add_subject')
            
#             # التحقق من عدم التكرار
#             if Subject.objects.filter(name=name).exists():
#                 messages.error(request, f'يوجد مادة بنفس الاسم "{name}" بالفعل')
#                 return redirect('books_inventory:add_subject')
            
#             if subject_code and Subject.objects.filter(subject_code=subject_code).exists():
#                 messages.error(request, f'يوجد مادة بنفس الكود "{subject_code}" بالفعل')
#                 return redirect('books_inventory:add_subject')
            
#             # إنشاء المادة
#             subject = Subject.objects.create(
#                 name=name,
#                 name_en=name_en,
#                 description=description,
#                 subject_code=subject_code,
#                 color=color,
#                 is_active=is_active,
#                 is_core_subject=is_core_subject,
#                 weekly_hours=weekly_hours
#             )
            
#             # ربط الصفوف الدراسية
#             if selected_grade_levels:
#                 subject.grade_levels.set(selected_grade_levels)
            
#             # ربط المراحل التعليمية
#             if selected_education_levels:
#                 subject.education_levels.set(selected_education_levels)
            
#             messages.success(request, f'تم إضافة المادة "{subject.name}" بنجاح')
#             return redirect('books_inventory:subject_detail', pk=subject.pk)
            
#         except Exception as e:
#             print(f"خطأ في إضافة المادة: {e}")
#             messages.error(request, f'حدث خطأ في إضافة المادة: {str(e)}')
#             return redirect('books_inventory:add_subject')
    
#     # GET request - جلب البيانات المطلوبة
#     from school_settings.models import GradeLevel, EducationLevel
    
#     context = {
#         'grade_levels': GradeLevel.objects.filter(is_active=True).select_related('education_level'),
#         'education_levels': EducationLevel.objects.filter(is_active=True),
#         'page_title': 'إضافة مادة دراسية جديدة'
#     }
    
#     return render(request, 'books_inventory/add_subject.html', context)


# @never_cache
# @login_required
# def edit_subject(request, pk):
#     """تعديل مادة دراسية مع إدارة الصفوف"""
    
#     subject = get_object_or_404(Subject, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             # البيانات الأساسية
#             name = request.POST.get('name', '').strip()
#             name_en = request.POST.get('name_en', '').strip()
#             description = request.POST.get('description', '').strip()
#             subject_code = request.POST.get('subject_code', '').strip()
#             color = request.POST.get('color', '#007bff')
#             is_active = request.POST.get('is_active') == 'on'
#             is_core_subject = request.POST.get('is_core_subject') == 'on'
#             weekly_hours = int(request.POST.get('weekly_hours', 2))
            
#             # الصفوف والمراحل المختارة
#             selected_grade_levels = request.POST.getlist('grade_levels')
#             selected_education_levels = request.POST.getlist('education_levels')
            
#             # التحقق من البيانات المطلوبة
#             if not name:
#                 messages.error(request, 'اسم المادة مطلوب')
#                 return redirect('books_inventory:edit_subject', pk=pk)
            
#             # التحقق من عدم التكرار (عدا المادة الحالية)
#             if Subject.objects.filter(name=name).exclude(pk=pk).exists():
#                 messages.error(request, f'يوجد مادة أخرى بنفس الاسم "{name}" بالفعل')
#                 return redirect('books_inventory:edit_subject', pk=pk)
            
#             if subject_code and Subject.objects.filter(subject_code=subject_code).exclude(pk=pk).exists():
#                 messages.error(request, f'يوجد مادة أخرى بنفس الكود "{subject_code}" بالفعل')
#                 return redirect('books_inventory:edit_subject', pk=pk)
            
#             # تحديث المادة
#             subject.name = name
#             subject.name_en = name_en
#             subject.description = description
#             subject.subject_code = subject_code
#             subject.color = color
#             subject.is_active = is_active
#             subject.is_core_subject = is_core_subject
#             subject.weekly_hours = weekly_hours
#             subject.save()
            
#             # تحديث الصفوف الدراسية
#             subject.grade_levels.set(selected_grade_levels)
            
#             # تحديث المراحل التعليمية
#             subject.education_levels.set(selected_education_levels)
            
#             messages.success(request, f'تم تحديث المادة "{subject.name}" بنجاح')
#             return redirect('books_inventory:subject_detail', pk=subject.pk)
            
#         except Exception as e:
#             print(f"خطأ في تحديث المادة: {e}")
#             messages.error(request, f'حدث خطأ في تحديث المادة: {str(e)}')
#             return redirect('books_inventory:edit_subject', pk=pk)
    
#     # GET request
#     from school_settings.models import GradeLevel, EducationLevel
    
#     context = {
#         'subject': subject,
#         'grade_levels': GradeLevel.objects.filter(is_active=True).select_related('education_level'),
#         'education_levels': EducationLevel.objects.filter(is_active=True),
#         'selected_grade_levels': list(subject.grade_levels.values_list('id', flat=True)),
#         'selected_education_levels': list(subject.education_levels.values_list('id', flat=True)),
#         'page_title': f'تعديل المادة - {subject.name}'
#     }
    
#     return render(request, 'books_inventory/edit_subject.html', context)


# @never_cache
# @login_required
# def subject_detail(request, pk):
#     """تفاصيل المادة الدراسية مع الصفوف"""
    
#     subject = get_object_or_404(Subject, pk=pk)
    
#     # إحصائيات المادة
#     books_count = Book.objects.filter(subject=subject).count()
#     active_books = Book.objects.filter(subject=subject, is_active=True).count()
#     total_books_stock = Book.objects.filter(subject=subject).aggregate(Sum('total_stock'))['total_stock__sum'] or 0
    
#     # أحدث الكتب للمادة
#     recent_books = Book.objects.filter(subject=subject).select_related('subject').prefetch_related('grade_levels').order_by('-created_at')[:5]
    
#     # الكتب حسب الصفوف
#     books_by_grade = {}
#     for grade in subject.grade_levels.all():
#         grade_books = Book.objects.filter(
#             subject=subject,
#             grade_levels=grade,
#             is_active=True
#         ).count()
#         if grade_books > 0:
#             books_by_grade[grade] = grade_books
    
#     context = {
#         'subject': subject,
#         'books_count': books_count,
#         'active_books': active_books,
#         'total_books_stock': total_books_stock,
#         'recent_books': recent_books,
#         'books_by_grade': books_by_grade,
#         'grade_levels_count': subject.grade_levels.count(),
#         'education_levels_count': subject.education_levels.count(),
#         'page_title': f'تفاصيل المادة - {subject.name}'
#     }
    
#     return render(request, 'books_inventory/subject_detail.html', context)

# @never_cache
# @login_required
# def subjects_list(request):
#     """قائمة المواد الدراسية"""
    
#     search_query = request.GET.get('search', '')
#     is_active_filter = request.GET.get('is_active', '')
    
#     # الحصول على المواد
#     subjects = Subject.objects.all().order_by('name')
    
#     # تطبيق البحث
#     if search_query:
#         subjects = subjects.filter(
#             Q(name__icontains=search_query) |
#             Q(description__icontains=search_query)
#         )
    
#     # تطبيق فلتر الحالة
#     if is_active_filter:
#         subjects = subjects.filter(is_active=is_active_filter == 'true')
    
#     # Pagination
#     paginator = Paginator(subjects, 12)
#     page_number = request.GET.get('page')
    
#     try:
#         subjects_page = paginator.page(page_number)
#     except PageNotAnInteger:
#         subjects_page = paginator.page(1)
#     except EmptyPage:
#         subjects_page = paginator.page(paginator.num_pages)
    
#     context = {
#         'subjects': subjects_page,
#         'search_query': search_query,
#         'is_active_filter': is_active_filter,
#         'page_title': 'قائمة المواد الدراسية'
#     }
    
#     return render(request, 'books_inventory/subjects_list.html', context)


# @never_cache
# @login_required
# def delete_subject(request, pk):
#     """حذف مادة دراسية"""
    
#     subject = get_object_or_404(Subject, pk=pk)
    
#     # التحقق من وجود كتب مرتبطة
#     books_count = Book.objects.filter(subject=subject).count()
    
#     if request.method == 'POST':
#         try:
#             if books_count > 0:
#                 messages.error(request, f'لا يمكن حذف المادة لأنها مرتبطة بـ {books_count} كتاب. يرجى حذف الكتب أولاً أو تغيير المادة')
#                 return redirect('books_inventory:subject_detail', pk=pk)
            
#             subject_name = subject.name
#             subject.delete()
#             messages.success(request, f'تم حذف المادة "{subject_name}" بنجاح')
#             return redirect('books_inventory:subjects_list')
            
#         except Exception as e:
#             messages.error(request, f'لا يمكن حذف المادة: {str(e)}')
#             return redirect('books_inventory:subject_detail', pk=pk)
    
#     context = {
#         'subject': subject,
#         'books_count': books_count,
#         'page_title': f'حذف المادة - {subject.name}'
#     }
    
#     return render(request, 'books_inventory/delete_subject.html', context)

# @never_cache
# @login_required
# def edit_book(request, pk):
#     """تعديل كتاب"""
    
#     book = get_object_or_404(Book, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             # البيانات الأساسية
#             title = request.POST.get('title', '').strip()
#             book_type = request.POST.get('book_type', '')
#             subject_id = request.POST.get('subject', '')
#             academic_year = request.POST.get('academic_year', '').strip()
#             term = request.POST.get('term', 'FULL_YEAR')
#             edition_year = request.POST.get('edition_year', '').strip()
#             pages_count = request.POST.get('pages_count', '')
#             description = request.POST.get('description', '').strip()
#             cost_price = request.POST.get('cost_price', '0')
#             minimum_stock_level = request.POST.get('minimum_stock_level', '10')
#             is_active = request.POST.get('is_active') == 'on'
            
#             # التحقق من البيانات المطلوبة
#             if not title:
#                 messages.error(request, 'عنوان الكتاب مطلوب')
#                 return redirect('books_inventory:edit_book', pk=pk)
            
#             if not subject_id:
#                 messages.error(request, 'المادة الدراسية مطلوبة')
#                 return redirect('books_inventory:edit_book', pk=pk)
            
#             # تحديث الكتاب
#             book.title = title
#             book.book_type = book_type
#             book.subject_id = subject_id
#             book.academic_year = academic_year
#             book.term = term
#             book.edition_year = edition_year
#             book.pages_count = int(pages_count) if pages_count else None
#             book.description = description
#             book.cost_price = Decimal(cost_price)
#             book.minimum_stock_level = int(minimum_stock_level)
#             book.is_active = is_active
#             book.save()
            
#             # تحديث الصفوف الدراسية
#             grade_levels = request.POST.getlist('grade_levels')
#             book.grade_levels.set(grade_levels)
            
#             messages.success(request, f'تم تحديث الكتاب "{book.title}" بنجاح')
#             return redirect('books_inventory:book_detail', pk=book.pk)
            
#         except Exception as e:
#             print(f"خطأ في تحديث الكتاب: {e}")
#             messages.error(request, f'حدث خطأ في تحديث الكتاب: {str(e)}')
#             return redirect('books_inventory:edit_book', pk=pk)
    
#     # GET request - تحضير البيانات
#     subjects = Subject.objects.filter(is_active=True).order_by('name')
#     from school_settings.models import GradeLevel
#     grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    
#     context = {
#         'book': book,
#         'subjects': subjects,
#         'grade_levels': grade_levels,
#         'book_type_choices': Book.BOOK_TYPE_CHOICES,
#         'term_choices': [
#             ('FIRST', 'الترم الأول'),
#             ('SECOND', 'الترم الثاني'),
#             ('FULL_YEAR', 'السنة كاملة')
#         ],
#         'page_title': f'تعديل الكتاب - {book.title}'
#     }
    
#     return render(request, 'books_inventory/edit_book.html', context)


# @never_cache  
# @login_required
# def delete_book(request, pk):
#     """حذف كتاب"""
    
#     book = get_object_or_404(Book, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             book_title = book.title
#             book.delete()
#             messages.success(request, f'تم حذف الكتاب "{book_title}" بنجاح')
#             return redirect('books_inventory:books_list')
#         except Exception as e:
#             messages.error(request, f'لا يمكن حذف الكتاب: {str(e)}')
#             return redirect('books_inventory:book_detail', pk=pk)
    
#     # إحصائيات الكتاب للتحذير
#     total_receipts = BookReceiptItem.objects.filter(book=book).count()
#     total_distributions = BookDistributionItem.objects.filter(book=book).count()
    
#     context = {
#         'book': book,
#         'total_receipts': total_receipts,
#         'total_distributions': total_distributions,
#         'page_title': f'حذف الكتاب - {book.title}'
#     }
    
#     return render(request, 'books_inventory/delete_book.html', context)

# @never_cache
# @login_required
# def book_detail(request, pk):
#     """تفاصيل الكتاب"""
    
#     book = get_object_or_404(Book, pk=pk)
    
#     # احدث الاستلامات
#     recent_receipts = BookReceiptItem.objects.filter(book=book).select_related(
#         'receipt__supplier'
#     ).order_by('-receipt__receipt_date')[:5]
    
#     # أحدث التوزيعات
#     try:
#         recent_distributions = BookDistributionItem.objects.filter(book=book).select_related(
#             'distribution__student'
#         ).order_by('-distribution__distribution_date')[:5]
#     except:
#         recent_distributions = []
    
#     # إحصائيات
#     total_received = BookReceiptItem.objects.filter(book=book).aggregate(
#         total=Sum('quantity_received')
#     )['total'] or 0
    
#     total_distributed = 0
#     try:
#         total_distributed = BookDistributionItem.objects.filter(book=book).aggregate(
#             total=Sum('quantity_distributed')
#         )['total'] or 0
#     except:
#         pass
    
#     total_damaged = BookReceiptItem.objects.filter(book=book).aggregate(
#         total=Sum('quantity_damaged')
#     )['total'] or 0
    
#     context = {
#         'book': book,
#         'recent_receipts': recent_receipts,
#         'recent_distributions': recent_distributions, 
#         'total_received': total_received,
#         'total_distributed': total_distributed,
#         'total_damaged': total_damaged,
#         'page_title': f'تفاصيل الكتاب - {book.title}'
#     }
    
#     return render(request, 'books_inventory/book_detail.html', context)


# @never_cache
# @login_required
# def edit_receipt(request, pk):
#     """تعديل إيصال استلام"""
    
#     receipt = get_object_or_404(StockReceipt, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             # البيانات الأساسية للإيصال
#             supplier_id = request.POST.get('supplier')
#             receipt_date = request.POST.get('receipt_date')
#             invoice_number = request.POST.get('invoice_number', '').strip()
#             notes = request.POST.get('notes', '').strip()
#             item_count = int(request.POST.get('item_count', 0))
            
#             # التحقق من البيانات المطلوبة
#             if not supplier_id or not receipt_date:
#                 messages.error(request, 'يجب إدخال المورد وتاريخ الاستلام')
#                 return redirect('books_inventory:edit_receipt', pk=pk)
            
#             if item_count == 0:
#                 messages.error(request, 'يجب إضافة عنصر واحد على الأقل للإيصال')
#                 return redirect('books_inventory:edit_receipt', pk=pk)
            
#             with transaction.atomic():
#                 # تحديث الإيصال الأساسي
#                 supplier = get_object_or_404(Supplier, pk=supplier_id)
#                 receipt.supplier = supplier
#                 receipt.receipt_date = receipt_date
#                 receipt.invoice_number = invoice_number
#                 receipt.notes = notes
                
#                 # إعادة تعيين مخزون العناصر القديمة (إلغاء التأثير السابق)
#                 if receipt.receipt_type == 'BOOKS':
#                     old_items = BookReceiptItem.objects.filter(receipt=receipt)
#                     for old_item in old_items:
#                         book = old_item.book
#                         book.total_stock -= old_item.quantity_received
#                         book.damaged_count -= old_item.quantity_damaged
#                         book.update_stock()
#                     old_items.delete()
                    
#                 elif receipt.receipt_type == 'NOTEBOOKS':
#                     old_items = NotebookReceiptItem.objects.filter(receipt=receipt)
#                     for old_item in old_items:
#                         notebook = old_item.notebook
#                         notebook.total_stock -= old_item.quantity_received
#                         notebook.damaged_count -= old_item.quantity_damaged
#                         notebook.update_stock()
#                     old_items.delete()
                    
#                 elif receipt.receipt_type == 'SUPPLIES':
#                     old_items = SupplyReceiptItem.objects.filter(receipt=receipt)
#                     for old_item in old_items:
#                         supply = old_item.supply
#                         supply.total_stock -= old_item.quantity_received
#                         supply.damaged_count -= old_item.quantity_damaged
#                         supply.update_stock()
#                     old_items.delete()
                
#                 # إضافة العناصر الجديدة
#                 total_items = 0
#                 total_damaged = 0
#                 total_cost = Decimal('0.00')
                
#                 for i in range(item_count):
#                     if receipt.receipt_type == 'BOOKS':
#                         book_id = request.POST.get(f'book_{i}')
#                         if book_id:
#                             book = get_object_or_404(Book, pk=book_id)
#                             quantity = int(request.POST.get(f'quantity_{i}', 0))
#                             damaged = int(request.POST.get(f'damaged_{i}', 0))
#                             unit_cost = Decimal(request.POST.get(f'unit_cost_{i}', '0'))
                            
#                             if quantity > 0:
#                                 BookReceiptItem.objects.create(
#                                     receipt=receipt,
#                                     book=book,
#                                     quantity_received=quantity,
#                                     quantity_damaged=damaged,
#                                     unit_cost=unit_cost,
#                                     total_cost=quantity * unit_cost
#                                 )
                                
#                                 book.total_stock += quantity
#                                 book.damaged_count += damaged
#                                 book.update_stock()
                                
#                                 total_items += quantity
#                                 total_damaged += damaged
#                                 total_cost += quantity * unit_cost
                    
#                     elif receipt.receipt_type == 'NOTEBOOKS':
#                         notebook_id = request.POST.get(f'notebook_{i}')
#                         if notebook_id:
#                             notebook = get_object_or_404(Notebook, pk=notebook_id)
#                             quantity = int(request.POST.get(f'quantity_{i}', 0))
#                             damaged = int(request.POST.get(f'damaged_{i}', 0))
#                             unit_cost = Decimal(request.POST.get(f'unit_cost_{i}', '0'))
                            
#                             if quantity > 0:
#                                 NotebookReceiptItem.objects.create(
#                                     receipt=receipt,
#                                     notebook=notebook,
#                                     quantity_received=quantity,
#                                     quantity_damaged=damaged,
#                                     unit_cost=unit_cost,
#                                     total_cost=quantity * unit_cost
#                                 )
                                
#                                 notebook.total_stock += quantity
#                                 notebook.damaged_count += damaged
#                                 notebook.update_stock()
                                
#                                 total_items += quantity
#                                 total_damaged += damaged
#                                 total_cost += quantity * unit_cost
                    
#                     elif receipt.receipt_type == 'SUPPLIES':
#                         supply_id = request.POST.get(f'supply_{i}')
#                         if supply_id:
#                             supply = get_object_or_404(SchoolSupply, pk=supply_id)
#                             quantity = int(request.POST.get(f'quantity_{i}', 0))
#                             damaged = int(request.POST.get(f'damaged_{i}', 0))
#                             unit_cost = Decimal(request.POST.get(f'unit_cost_{i}', '0'))
                            
#                             if quantity > 0:
#                                 SupplyReceiptItem.objects.create(
#                                     receipt=receipt,
#                                     supply=supply,
#                                     quantity_received=quantity,
#                                     quantity_damaged=damaged,
#                                     unit_cost=unit_cost,
#                                     total_cost=quantity * unit_cost
#                                 )
                                
#                                 supply.total_stock += quantity
#                                 supply.damaged_count += damaged
#                                 supply.update_stock()
                                
#                                 total_items += quantity
#                                 total_damaged += damaged
#                                 total_cost += quantity * unit_cost
                
#                 # تحديث إجماليات الإيصال
#                 receipt.total_items = total_items
#                 receipt.damaged_items = total_damaged
#                 receipt.total_cost = total_cost
#                 receipt.save()
            
#             messages.success(request, f'تم تحديث إيصال الاستلام "{receipt.receipt_number}" بنجاح')
#             return redirect('books_inventory:receipt_detail', pk=receipt.pk)
            
#         except Exception as e:
#             print(f"خطأ في تحديث الإيصال: {e}")
#             messages.error(request, f'حدث خطأ في تحديث الإيصال: {str(e)}')
#             return redirect('books_inventory:edit_receipt', pk=pk)
    
#     # GET request - تحضير البيانات للقالب
#     suppliers = Supplier.objects.filter(is_active=True).order_by('name')
#     books = Book.objects.filter(is_active=True).select_related('subject').order_by('title')
#     notebooks = Notebook.objects.filter(is_active=True).order_by('name')
#     supplies = SchoolSupply.objects.filter(is_active=True).order_by('name')
    
#     # الحصول على عناصر الإيصال الحالية
#     current_items = []
#     if receipt.receipt_type == 'BOOKS':
#         book_items = BookReceiptItem.objects.filter(receipt=receipt).select_related('book__subject')
#         for item in book_items:
#             current_items.append({
#                 'type': 'book',
#                 'id': item.book.id,
#                 'name': f"{item.book.title} - {item.book.subject.name}",
#                 'quantity_received': item.quantity_received,
#                 'quantity_damaged': item.quantity_damaged,
#                 'unit_cost': float(item.unit_cost),
#                 'total_cost': float(item.total_cost)
#             })
#     elif receipt.receipt_type == 'NOTEBOOKS':
#         notebook_items = NotebookReceiptItem.objects.filter(receipt=receipt).select_related('notebook')
#         for item in notebook_items:
#             current_items.append({
#                 'type': 'notebook',
#                 'id': item.notebook.id,
#                 'name': f"{item.notebook.name} - {item.notebook.get_notebook_type_display()}",
#                 'quantity_received': item.quantity_received,
#                 'quantity_damaged': item.quantity_damaged,
#                 'unit_cost': float(item.unit_cost),
#                 'total_cost': float(item.total_cost)
#             })
#     elif receipt.receipt_type == 'SUPPLIES':
#         supply_items = SupplyReceiptItem.objects.filter(receipt=receipt).select_related('supply')
#         for item in supply_items:
#             current_items.append({
#                 'type': 'supply',
#                 'id': item.supply.id,
#                 'name': f"{item.supply.name} - {item.supply.get_category_display()}",
#                 'quantity_received': item.quantity_received,
#                 'quantity_damaged': item.quantity_damaged,
#                 'unit_cost': float(item.unit_cost),
#                 'total_cost': float(item.total_cost)
#             })
    
#     # تحويل البيانات لـ JSON
#     books_json = json.dumps([{
#         'id': book.id,
#         'title': book.title,
#         'subject': book.subject.name,
#         'book_type': book.get_book_type_display(),
#         'cost_price': float(book.cost_price)
#     } for book in books])
    
#     notebooks_json = json.dumps([{
#         'id': notebook.id,
#         'name': notebook.name,
#         'type': notebook.get_notebook_type_display(),
#         'size': notebook.get_size_display(),
#         'pages': notebook.pages_count,
#         'cost_price': float(notebook.cost_price)
#     } for notebook in notebooks])
    
#     supplies_json = json.dumps([{
#         'id': supply.id,
#         'name': supply.name,
#         'category': supply.get_category_display(),
#         'unit': supply.unit,
#         'cost_price': float(supply.cost_price)
#     } for supply in supplies])
    
#     context = {
#         'receipt': receipt,
#         'suppliers': suppliers,
#         'books': books_json,
#         'notebooks': notebooks_json,
#         'supplies': supplies_json,
#         'current_items': json.dumps(current_items),
#         'receipt_type_choices': StockReceipt.RECEIPT_TYPE_CHOICES,
#         'page_title': f'تعديل إيصال الاستلام - {receipt.receipt_number}'
#     }
    
#     return render(request, 'books_inventory/edit_receipt.html', context)


# @never_cache
# @login_required
# def add_book_to_distribution(request, pk):
#     """إضافة كتاب لتوزيع طالب"""
    
#     distribution = get_object_or_404(StudentDistribution, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             import json
#             data = json.loads(request.body)
            
#             book_id = data.get('book_id')
#             quantity_requested = int(data.get('quantity_requested', 1))
#             quantity_distributed = int(data.get('quantity_distributed', 0))
#             is_distributed = data.get('is_distributed', False)
#             notes = data.get('notes', '')
            
#             book = get_object_or_404(Book, pk=book_id)
            
#             # التحقق من عدم تكرار الكتاب
#             if BookDistributionItem.objects.filter(distribution=distribution, book=book).exists():
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'هذا الكتاب موجود بالفعل في التوزيع'
#                 })
            
#             # التحقق من توفر المخزون
#             if quantity_distributed > book.available_stock:
#                 return JsonResponse({
#                     'success': False,
#                     'error': f'الكمية المطلوبة ({quantity_distributed}) أكبر من المتاح ({book.available_stock})'
#                 })
            
#             # إنشاء عنصر التوزيع
#             book_item = BookDistributionItem.objects.create(
#                 distribution=distribution,
#                 book=book,
#                 quantity_requested=quantity_requested,
#                 quantity_distributed=quantity_distributed,
#                 is_distributed=is_distributed,
#                 notes=notes
#             )
            
#             # تحديث إجمالي العناصر
#             distribution.total_items = (
#                 distribution.book_items.count() +
#                 distribution.notebook_items.count() +
#                 distribution.supply_items.count()
#             )
#             distribution.save()
            
#             return JsonResponse({
#                 'success': True,
#                 'message': f'تم إضافة الكتاب "{book.title}" بنجاح'
#             })
            
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'error': str(e)
#             })
    
#     return JsonResponse({'success': False, 'error': 'طريقة الطلب غير صحيحة'})


# @never_cache
# @login_required
# def delete_book_item(request, item_id):
#     """حذف عنصر كتاب من التوزيع"""
    
#     book_item = get_object_or_404(BookDistributionItem, pk=item_id)
    
#     if request.method == 'POST':
#         try:
#             distribution = book_item.distribution
#             book_item.delete()
            
#             # تحديث إجمالي العناصر
#             distribution.total_items = (
#                 distribution.book_items.count() +
#                 distribution.notebook_items.count() +
#                 distribution.supply_items.count()
#             )
#             distribution.save()
            
#             return JsonResponse({
#                 'success': True,
#                 'message': 'تم حذف الكتاب من التوزيع'
#             })
            
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'error': str(e)
#             })
    
#     return JsonResponse({'success': False, 'error': 'طريقة الطلب غير صحيحة'})


# # تحديث view edit_distribution لتمرير الكتب المتاحة
# @never_cache
# @login_required
# def edit_distribution(request, pk):
#     """تعديل توزيع طالب"""
    
#     distribution = get_object_or_404(StudentDistribution, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             # نفس الكود السابق...
#             status = request.POST.get('status')
#             notes = request.POST.get('notes', '').strip()
#             verification_notes = request.POST.get('verification_notes', '').strip()
#             first_installment_verified = request.POST.get('first_installment_verified') == 'on'
            
#             if status:
#                 distribution.status = status
            
#             distribution.notes = notes
#             distribution.verification_notes = verification_notes
            
#             old_verified = distribution.first_installment_verified
#             distribution.first_installment_verified = first_installment_verified
            
#             if first_installment_verified and not old_verified:
#                 distribution.verification_date = timezone.now()
#             elif not first_installment_verified and old_verified:
#                 distribution.verification_date = None
                
#             distribution.save()
            
#             messages.success(request, f'تم تحديث توزيع الطالب {distribution.student.name} بنجاح')
#             return redirect('books_inventory:student_distribution_detail', pk=distribution.pk)
            
#         except Exception as e:
#             messages.error(request, f'حدث خطأ: {str(e)}')
    
#     # الحصول على الكتب المتاحة (غير الموجودة في التوزيع)
#     distributed_books = distribution.book_items.values_list('book_id', flat=True)
#     available_books = Book.objects.filter(
#         is_active=True,
#         available_stock__gt=0
#     ).exclude(id__in=distributed_books).select_related('subject')
    
#     # الحصول على الكراسات المتاحة
#     distributed_notebooks = distribution.notebook_items.values_list('notebook_id', flat=True)
#     available_notebooks = Notebook.objects.filter(
#         is_active=True,
#         available_stock__gt=0
#     ).exclude(id__in=distributed_notebooks)
    
#     # الحصول على الأدوات المتاحة
#     distributed_supplies = distribution.supply_items.values_list('supply_id', flat=True)
#     available_supplies = SchoolSupply.objects.filter(
#         is_active=True,
#         available_stock__gt=0
#     ).exclude(id__in=distributed_supplies)
    
#     context = {
#         'distribution': distribution,
#         'status_choices': StudentDistribution.DISTRIBUTION_STATUS_CHOICES,
#         'available_books': available_books,
#         'available_notebooks': available_notebooks,
#         'available_supplies': available_supplies,
#         'page_title': f'تعديل التوزيع - {distribution.student.name}'
#     }
    
#     return render(request, 'books_inventory/edit_distribution.html', context)

# @never_cache
# @login_required
# def add_notebook_to_distribution(request, pk):
#     """إضافة كراسة لتوزيع طالب"""
    
#     distribution = get_object_or_404(StudentDistribution, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             import json
#             data = json.loads(request.body)
            
#             notebook_id = data.get('notebook_id')
#             quantity_requested = int(data.get('quantity_requested', 1))
#             quantity_distributed = int(data.get('quantity_distributed', 0))
#             is_distributed = data.get('is_distributed', False)
#             notes = data.get('notes', '')
            
#             notebook = get_object_or_404(Notebook, pk=notebook_id)
            
#             # التحقق من عدم تكرار الكراسة
#             if NotebookDistributionItem.objects.filter(distribution=distribution, notebook=notebook).exists():
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'هذه الكراسة موجودة بالفعل في التوزيع'
#                 })
            
#             # التحقق من توفر المخزون
#             if quantity_distributed > notebook.available_stock:
#                 return JsonResponse({
#                     'success': False,
#                     'error': f'الكمية المطلوبة ({quantity_distributed}) أكبر من المتاح ({notebook.available_stock})'
#                 })
            
#             # إنشاء عنصر التوزيع
#             notebook_item = NotebookDistributionItem.objects.create(
#                 distribution=distribution,
#                 notebook=notebook,
#                 quantity_requested=quantity_requested,
#                 quantity_distributed=quantity_distributed,
#                 is_distributed=is_distributed,
#                 notes=notes
#             )
            
#             # تحديث إجمالي العناصر
#             distribution.total_items = (
#                 distribution.book_items.count() +
#                 distribution.notebook_items.count() +
#                 distribution.supply_items.count()
#             )
#             distribution.save()
            
#             return JsonResponse({
#                 'success': True,
#                 'message': f'تم إضافة الكراسة "{notebook.name}" بنجاح'
#             })
            
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'error': str(e)
#             })
    
#     return JsonResponse({'success': False, 'error': 'طريقة الطلب غير صحيحة'})


# @never_cache
# @login_required
# def add_supply_to_distribution(request, pk):
#     """إضافة أداة مدرسية لتوزيع طالب"""
    
#     distribution = get_object_or_404(StudentDistribution, pk=pk)
    
#     if request.method == 'POST':
#         try:
#             import json
#             data = json.loads(request.body)
            
#             supply_id = data.get('supply_id')
#             quantity_requested = int(data.get('quantity_requested', 1))
#             quantity_distributed = int(data.get('quantity_distributed', 0))
#             is_distributed = data.get('is_distributed', False)
#             notes = data.get('notes', '')
            
#             supply = get_object_or_404(SchoolSupply, pk=supply_id)
            
#             # التحقق من عدم تكرار الأداة
#             if SupplyDistributionItem.objects.filter(distribution=distribution, supply=supply).exists():
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'هذه الأداة موجودة بالفعل في التوزيع'
#                 })
            
#             # التحقق من توفر المخزون
#             if quantity_distributed > supply.available_stock:
#                 return JsonResponse({
#                     'success': False,
#                     'error': f'الكمية المطلوبة ({quantity_distributed}) أكبر من المتاح ({supply.available_stock})'
#                 })
            
#             # إنشاء عنصر التوزيع
#             supply_item = SupplyDistributionItem.objects.create(
#                 distribution=distribution,
#                 supply=supply,
#                 quantity_requested=quantity_requested,
#                 quantity_distributed=quantity_distributed,
#                 is_distributed=is_distributed,
#                 notes=notes
#             )
            
#             # تحديث إجمالي العناصر
#             distribution.total_items = (
#                 distribution.book_items.count() +
#                 distribution.notebook_items.count() +
#                 distribution.supply_items.count()
#             )
#             distribution.save()
            
#             return JsonResponse({
#                 'success': True,
#                 'message': f'تم إضافة الأداة "{supply.name}" بنجاح'
#             })
            
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'error': str(e)
#             })
    
#     return JsonResponse({'success': False, 'error': 'طريقة الطلب غير صحيحة'})


# @never_cache
# @login_required
# def delete_notebook_item(request, item_id):
#     """حذف عنصر كراسة من التوزيع"""
    
#     notebook_item = get_object_or_404(NotebookDistributionItem, pk=item_id)
    
#     if request.method == 'POST':
#         try:
#             distribution = notebook_item.distribution
#             notebook_name = notebook_item.notebook.name
#             notebook_item.delete()
            
#             # تحديث إجمالي العناصر
#             distribution.total_items = (
#                 distribution.book_items.count() +
#                 distribution.notebook_items.count() +
#                 distribution.supply_items.count()
#             )
#             distribution.save()
            
#             return JsonResponse({
#                 'success': True,
#                 'message': f'تم حذف الكراسة "{notebook_name}" من التوزيع'
#             })
            
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'error': str(e)
#             })
    
#     return JsonResponse({'success': False, 'error': 'طريقة الطلب غير صحيحة'})


# @never_cache
# @login_required
# def delete_supply_item(request, item_id):
#     """حذف عنصر أداة مدرسية من التوزيع"""
    
#     supply_item = get_object_or_404(SupplyDistributionItem, pk=item_id)
    
#     if request.method == 'POST':
#         try:
#             distribution = supply_item.distribution
#             supply_name = supply_item.supply.name
#             supply_item.delete()
            
#             # تحديث إجمالي العناصر
#             distribution.total_items = (
#                 distribution.book_items.count() +
#                 distribution.notebook_items.count() +
#                 distribution.supply_items.count()
#             )
#             distribution.save()
            
#             return JsonResponse({
#                 'success': True,
#                 'message': f'تم حذف الأداة "{supply_name}" من التوزيع'
#             })
            
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'error': str(e)
#             })
    
#     return JsonResponse({'success': False, 'error': 'طريقة الطلب غير صحيحة'})

# @never_cache
# @login_required
# def get_items_for_grade(request):
#     """جلب العناصر المناسبة للصف الدراسي مع تصنيف أفضل للمواد"""
    
#     grade_level_id = request.GET.get('grade_level_id')
#     if not grade_level_id:
#         return JsonResponse({'error': 'معرف الصف مطلوب'})
    
#     try:
#         grade_level = GradeLevel.objects.get(id=grade_level_id)
#         education_level = grade_level.education_level
        
#         # جلب المواد المناسبة للصف أولاً
#         relevant_subjects = Subject.objects.filter(
#             Q(grade_levels=grade_level) | Q(education_levels=education_level),
#             is_active=True
#         ).distinct()
        
#         # جلب الكتب - الأولوية للمواد المرتبطة بالصف
#         books = Book.objects.filter(
#             grade_levels=grade_level,
#             is_active=True,
#             available_stock__gt=0
#         ).select_related('subject').order_by('subject__name', 'title')
        
#         # جلب الكراسات المناسبة
#         notebooks = Notebook.objects.filter(
#             grade_levels=grade_level,
#             is_active=True,
#             available_stock__gt=0
#         ).order_by('name')
        
#         # جلب الأدوات المناسبة
#         supplies = SchoolSupply.objects.filter(
#             grade_levels=grade_level,
#             is_active=True,
#             available_stock__gt=0
#         ).order_by('category', 'name')
        
#         # تجميع الكتب حسب المادة
#         books_by_subject = {}
#         for book in books:
#             subject_name = book.subject.name
#             if subject_name not in books_by_subject:
#                 books_by_subject[subject_name] = []
#             books_by_subject[subject_name].append({
#                 'id': book.id,
#                 'title': book.title,
#                 'subject': book.subject.name,
#                 'subject_color': book.subject.color,
#                 'book_type': book.get_book_type_display(),
#                 'available_stock': book.available_stock,
#                 'term': book.get_term_display(),
#                 'description': book.description[:100] if book.description else '',
#             })
        
#         # تحويل البيانات للإرسال
#         books_data = []
#         for subject, subject_books in books_by_subject.items():
#             books_data.extend(subject_books)
        
#         notebooks_data = [
#             {
#                 'id': notebook.id,
#                 'name': notebook.name,
#                 'type': notebook.get_notebook_type_display(),
#                 'size': notebook.get_size_display(),
#                 'pages_count': notebook.pages_count,
#                 'available_stock': notebook.available_stock,
#             }
#             for notebook in notebooks
#         ]
        
#         supplies_data = [
#             {
#                 'id': supply.id,
#                 'name': supply.name,
#                 'category': supply.get_category_display(),
#                 'unit': supply.unit,
#                 'available_stock': supply.available_stock,
#                 'description': supply.description[:100] if supply.description else '',
#             }
#             for supply in supplies
#         ]
        
#         return JsonResponse({
#             'success': True,
#             'grade_level': {
#                 'id': grade_level.id,
#                 'name': grade_level.name,
#                 'education_level': grade_level.education_level.name
#             },
#             'relevant_subjects': [
#                 {
#                     'id': subject.id,
#                     'name': subject.name,
#                     'color': subject.color,
#                     'books_count': subject.get_books_for_grade(grade_level).count()
#                 }
#                 for subject in relevant_subjects
#             ],
#             'books': books_data,
#             'books_by_subject': books_by_subject,
#             'notebooks': notebooks_data,
#             'supplies': supplies_data,
#             'total_items': len(books_data) + len(notebooks_data) + len(supplies_data)
#         })
        
#     except GradeLevel.DoesNotExist:
#         return JsonResponse({'error': 'الصف الدراسي غير موجود'})
#     except Exception as e:
#         return JsonResponse({'error': f'حدث خطأ: {str(e)}'})


# @never_cache
# @login_required
# def print_distribution(request, pk):
#     """طباعة تفاصيل التوزيع"""
    
#     distribution = get_object_or_404(StudentDistribution, pk=pk)
    
#     # الحصول على العناصر الموزعة
#     book_items = distribution.book_items.select_related('book__subject').all()
#     notebook_items = distribution.notebook_items.select_related('notebook').all()
#     supply_items = distribution.supply_items.select_related('supply').all()
    
#     # إحصائيات
#     total_books = book_items.count()
#     total_notebooks = notebook_items.count()
#     total_supplies = supply_items.count()
#     total_items = total_books + total_notebooks + total_supplies
    
#     # إحصائيات الكميات
#     total_books_qty = sum(item.quantity_distributed for item in book_items)
#     total_notebooks_qty = sum(item.quantity_distributed for item in notebook_items)
#     total_supplies_qty = sum(item.quantity_distributed for item in supply_items)
#     total_qty = total_books_qty + total_notebooks_qty + total_supplies_qty
    
#     context = {
#         'distribution': distribution,
#         'book_items': book_items,
#         'notebook_items': notebook_items,
#         'supply_items': supply_items,
#         'total_books': total_books,
#         'total_notebooks': total_notebooks,
#         'total_supplies': total_supplies,
#         'total_items': total_items,
#         'total_books_qty': total_books_qty,
#         'total_notebooks_qty': total_notebooks_qty,
#         'total_supplies_qty': total_supplies_qty,
#         'total_qty': total_qty,
#         'page_title': f'طباعة التوزيع - {distribution.student.name}'
#     }
    
#     return render(request, 'books_inventory/print_distribution.html', context)
