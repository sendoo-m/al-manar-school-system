# students/views.py - منظم مع الصلاحيات
import decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache
from django.db.models import Q, Sum, Count, Avg, Max, Min
from django.http import JsonResponse
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from school_settings.models import (
    SchoolFeesSettings,
    StudentDiscount,
    DiscountSettings,
)

try:
    from .utils.export_utils import StudentExporter
    EXPORT_AVAILABLE = True
except ImportError:
    EXPORT_AVAILABLE = False
    StudentExporter = None

try:
    from .utils.import_utils import StudentImporter
    IMPORT_AVAILABLE = True
except ImportError:
    IMPORT_AVAILABLE = False
    StudentImporter = None

try:
    from .utils.upgrade_utils import StudentUpgradeManager
    UPGRADE_AVAILABLE = True
except ImportError:
    UPGRADE_AVAILABLE = False
    StudentUpgradeManager = None

# ===================================
# 📦 الاستيراد
# ===================================

# النماذج المحلية
from .models import Student, ArchiveStudent, UserProfile

# نماذج الإعدادات
from school_settings.models import (
    AcademicYear as SettingsAcademicYear, 
    EducationLevel, 
    GradeLevel,
    SystemSettings
)

# الصلاحيات المخصصة
from .decorators import (
    students_basic_access,
    students_add_only, 
    students_full_access,
    students_reports_access,
    students_admin_access,
    students_sensitive_operation,
    students_advanced_reports
)

# ===================================
# 🔧 الدوال المساعدة
# ===================================

def get_user_role(user):
    """الحصول على دور المستخدم"""
    if hasattr(user, 'system_role'):
        return user.system_role.role
    return None

def get_system_data():
    """الحصول على بيانات النظام الأساسية"""
    try:
        system_settings = SystemSettings.get_current_settings()
    except:
        system_settings = None
        
    try:
        current_year = SettingsAcademicYear.get_current_year()
    except:
        current_year = None
        
    return system_settings, current_year

def get_education_data():
    """الحصول على البيانات التعليمية"""
    education_levels = EducationLevel.objects.filter(is_active=True).order_by('order')
    return education_levels

# ===================================
# 🏠 الصفحات الرئيسية
# ===================================

@never_cache
@students_basic_access
def home(request):
    """الصفحة الرئيسية - تحويل للوحة التحكم"""
    return redirect('students:student_affairs_home')

@never_cache
@students_basic_access
def student_affairs_home(request):
    """لوحة تحكم شؤون الطلاب مع الإحصائيات"""
    user_role = get_user_role(request.user)
    system_settings, current_year = get_system_data()
    
    # إحصائيات عامة
    total_students = Student.objects.filter(is_active=True).count()
    male_students = Student.objects.filter(gender='M', is_active=True).count()
    female_students = Student.objects.filter(gender='F', is_active=True).count()
    
    # إحصائيات مالية
    students_paid = Student.objects.filter(total_owed__lte=0, is_active=True).count()
    students_owing = Student.objects.filter(total_owed__gt=0, is_active=True).count()
    total_outstanding = Student.objects.filter(is_active=True).aggregate(
        total=Sum('total_owed')
    )['total'] or Decimal('0')
    
    # الطلاب المضافون مؤخراً
    recent_students = Student.objects.filter(is_active=True).order_by('-created_at')[:10]
    
    # توزيع الطلاب حسب المراحل التعليمية
    education_levels_stats = EducationLevel.objects.filter(is_active=True).annotate(
        student_count=Count('gradelevel__student', filter=Q(gradelevel__student__is_active=True))
    ).order_by('order')
    
    # توزيع الطلاب حسب الصفوف
    grade_levels_stats = GradeLevel.objects.filter(is_active=True).annotate(
        student_count=Count('student', filter=Q(student__is_active=True))
    ).select_related('education_level').order_by('education_level__order', 'order')
    
    # صلاحيات المستخدم للقالب
    permissions = {
        'can_add': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'STUDENT_AFFAIRS'],
        'can_edit': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'],
        'can_delete': user_role in ['SYSTEM_ADMIN'],
        'can_reports': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'],
        'can_export': user_role in ['SYSTEM_ADMIN'],
        'is_student_affairs_only': user_role == 'STUDENT_AFFAIRS',
    }
    
    context = {
        'system_settings': system_settings,
        'current_year': current_year,
        'total_students': total_students,
        'male_students': male_students,
        'female_students': female_students,
        'students_paid': students_paid,
        'students_owing': students_owing,
        'total_outstanding': total_outstanding,
        'recent_students': recent_students,
        'education_levels_stats': education_levels_stats,
        'grade_levels_stats': grade_levels_stats,
        'today': timezone.now().date(),
        'permissions': permissions,
        'user_role': user_role,
    }
    
    return render(request, 'students/student_affairs_home.html', context)

# ===================================
# 👥 إدارة الطلاب
# ===================================

@never_cache
@students_basic_access
def student_list(request):
    """قائمة الطلاب مع البحث والفلاتر"""
    user_role = get_user_role(request.user)
    
    # إزالة prefetch_related اللي بيسبب مشكلة
    students = Student.objects.filter(is_active=True).select_related(
        'grade_level__education_level'
    )
    # لا تضع prefetch_related حتى نعرف أسماء العلاقات الصحيحة
    
    # البحث
    search_query = request.GET.get('search_query', '').strip()
    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) | 
            Q(national_number__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    # فلتر الجنس
    gender = request.GET.get('gender', '')
    if gender:
        students = students.filter(gender=gender)
    
    # فلتر المرحلة التعليمية
    education_level = request.GET.get('education_level', '')
    if education_level:
        students = students.filter(grade_level__education_level_id=education_level)
    
    # فلتر الصف الدراسي
    grade_level = request.GET.get('grade_level', '')
    if grade_level:
        students = students.filter(grade_level_id=grade_level)
    
    # الإحصائيات
    total_male_students = students.filter(gender='M').count()
    total_female_students = students.filter(gender='F').count()
    
    # الترقيم
    students = students.order_by('name')
    paginator = Paginator(students, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # للفلاتر
    education_levels = EducationLevel.objects.filter(is_active=True).order_by('order')
    
    # صلاحيات للقالب
    permissions = {
        'can_view_details': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'STUDENT_AFFAIRS'],
        'can_edit': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'],
        'can_delete': user_role in ['SYSTEM_ADMIN'],
        'can_add': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER', 'STUDENT_AFFAIRS'],
        'can_export': user_role in ['SYSTEM_ADMIN'],
    }
    
    context = {
        'page_obj': page_obj,
        'total_male_students': total_male_students,
        'total_female_students': total_female_students,
        'education_levels': education_levels,
        'search_query': search_query,
        'selected_gender': gender,
        'selected_education_level': education_level,
        'selected_grade_level': grade_level,
        'permissions': permissions,
        'user_role': user_role,
    }
    return render(request, 'students/student_list.html', context)

@never_cache
@students_add_only
def add_student(request):
    """إضافة طالب جديد - متاح لموظف شؤون الطلاب"""
    user_role = get_user_role(request.user)
    system_settings, current_academic_year = get_system_data()
    education_levels = get_education_data()
    
    if request.method == 'POST':
        try:
            # البيانات الأساسية
            name = request.POST.get('name', '').strip()
            national_number = request.POST.get('national_number', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            address = request.POST.get('address', '').strip()
            
            # بيانات ولي الأمر
            parent_name = request.POST.get('parent_name', '').strip()
            parent_phone = request.POST.get('parent_phone', '').strip()
            parent_email = request.POST.get('parent_email', '').strip()
            
            # التحقق من البيانات المطلوبة
            if not name or not national_number:
                messages.error(request, 'الاسم والرقم القومي مطلوبان')
                return redirect('students:add_student')
            
            # التحقق من عدم تكرار الرقم القومي
            if Student.objects.filter(national_number=national_number).exists():
                messages.error(request, 'يوجد طالب آخر بنفس الرقم القومي')
                return redirect('students:add_student')
            
            # إنشاء الطالب
            student = Student.objects.create(
                name=name,
                national_number=national_number,
                phone_number=phone_number,
                address=address,
                parent_name=parent_name,
                parent_phone=parent_phone,
                parent_email=parent_email,
                academic_year=current_academic_year,
            )
            
            # ربط الصف الدراسي
            grade_level_id = request.POST.get('grade_level')
            if grade_level_id:
                try:
                    grade_level = GradeLevel.objects.get(id=grade_level_id, is_active=True)
                    student.grade_level = grade_level
                    student.save()
                except GradeLevel.DoesNotExist:
                    messages.warning(request, 'الصف الدراسي المختار غير صحيح')
            
            messages.success(request, f'تم إضافة الطالب {student.name} بنجاح!')
            
            # توجيه حسب الدور
            if user_role == 'STUDENT_AFFAIRS':
                return redirect('students:student_affairs_home')
            else:
                return redirect('students:student_detail', pk=student.pk)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إضافة الطالب: {str(e)}')
            return redirect('students:add_student')
    
    context = {
        'current_academic_year': current_academic_year,
        'education_levels': education_levels,
        'title': 'إضافة طالب جديد',
        'user_role': user_role,
    }
    return render(request, 'students/add_student.html', context)

@never_cache
@students_basic_access  
def student_detail(request, pk):
    """تفاصيل الطالب - عرض للجميع، تحرير حسب الصلاحية"""
    student = get_object_or_404(Student, pk=pk)
    user_role = get_user_role(request.user)
    
    # صلاحيات التفاصيل
    permissions = {
        'can_edit': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'],
        'can_delete': user_role in ['SYSTEM_ADMIN'],
        'can_view_financial': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'],
        'can_view_sensitive_data': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'],
    }
    
    context = {
        'student': student,
        'permissions': permissions,
        'user_role': user_role,
        'title': f'تفاصيل الطالب - {student.name}',
    }
    return render(request, 'students/student_detail.html', context)

@never_cache
@students_full_access
def edit_student(request, pk):
    """تعديل بيانات الطالب - للمدير والإدارة فقط"""
    student = get_object_or_404(Student, pk=pk)
    user_role = get_user_role(request.user)
    system_settings, current_academic_year = get_system_data()
    education_levels = get_education_data()
    
    if request.method == 'POST':
        try:
            # البيانات الأساسية
            student.name = request.POST.get('name', student.name)
            student.national_number = request.POST.get('national_number', student.national_number)
            student.phone_number = request.POST.get('phone_number', student.phone_number)
            student.address = request.POST.get('address', student.address)
            
            # بيانات ولي الأمر
            student.parent_name = request.POST.get('parent_name', student.parent_name)
            student.parent_phone = request.POST.get('parent_phone', student.parent_phone)
            student.parent_email = request.POST.get('parent_email', student.parent_email)
            
            # الصف الدراسي
            grade_level_id = request.POST.get('grade_level')
            if grade_level_id:
                try:
                    grade_level = GradeLevel.objects.get(id=grade_level_id, is_active=True)
                    student.grade_level = grade_level
                except GradeLevel.DoesNotExist:
                    messages.warning(request, 'الصف الدراسي المختار غير صحيح')
            
            student.save()
            
            messages.success(request, 'تم تحديث بيانات الطالب بنجاح!')
            return redirect('students:student_detail', pk=student.pk)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تحديث البيانات: {str(e)}')
    
    context = {
        'student': student,
        'current_academic_year': current_academic_year,
        'education_levels': education_levels,
        'user_role': user_role,
        'title': f'تعديل بيانات الطالب - {student.name}',
    }
    return render(request, 'students/edit_student_form.html', context)

@never_cache
@students_sensitive_operation
def confirm_delete_student(request, student_id):
    """حذف الطالب - للمدير العام فقط"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        try:
            # نقل إلى الأرشيف قبل الحذف
            ArchiveStudent.objects.create(
                archive_name=student.name,
                archive_national_number=student.national_number,
                archive_age=student.age or 0,
                archive_gender=student.gender,
                archive_date_of_birth=student.date_of_birth,
                archive_academic_year=str(student.academic_year) if student.academic_year else "غير محدد",
                archive_grade_level=student.grade_name,
                archive_education_level=student.education_level_name,
                archive_total_payments=student.total_payments,
                archive_total_fees=student.total_fees,
                archive_total_owed=student.total_owed,
                archived_reason='حذف من النظام'
            )
            
            student_name = student.name
            student.delete()
            messages.success(request, f'تم حذف الطالب {student_name} ونقله للأرشيف بنجاح!')
            return redirect('students:student_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ في الحذف: {str(e)}')
    
    context = {
        'student': student,
        'title': f'حذف الطالب - {student.name}',
        'warning_message': 'هذا الإجراء لا يمكن التراجع عنه! سيتم نقل الطالب للأرشيف.',
    }
    return render(request, 'students/confirm_delete_student.html', context)

# ===================================
# 🔍 البحث والتصفح
# ===================================

@never_cache
@students_basic_access
def search_student(request):
    """صفحة البحث المتقدم"""
    user_role = get_user_role(request.user)
    
    context = {
        'user_role': user_role,
        'education_levels': EducationLevel.objects.filter(is_active=True).order_by('order'),
    }
    return render(request, 'students/search_student.html', context)

@never_cache
@students_basic_access
def ajax_student_search(request):
    """البحث السريع عبر AJAX"""
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        query = request.GET.get('q', '').strip()
        user_role = get_user_role(request.user)
        
        if len(query) < 3:
            return JsonResponse({'students': []})
        
        # البحث في الاسم والرقم القومي
        students = Student.objects.filter(
            Q(name__icontains=query) | Q(national_number__icontains=query),
            is_active=True
        ).select_related('grade_level__education_level')[:20]
        
        # تحويل النتائج لـ JSON
        results = []
        for student in students:
            result_data = {
                'id': student.id,
                'name': student.name,
                'national_number': student.national_number,
                'age': student.age,
                'gender': 'ذكر' if student.gender == 'M' else 'أنثى' if student.gender == 'F' else 'غير محدد',
                'gender_icon': 'male' if student.gender == 'M' else 'female' if student.gender == 'F' else 'question',
                'grade_name': student.grade_name,
                'education_level_name': student.education_level_name,
                'detail_url': f"/students/student_detail/{student.pk}/",
            }
            
            # إضافة روابط حسب الصلاحية
            if user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
                result_data['edit_url'] = f"/students/edit_student/{student.pk}/"
            
            if user_role in ['SYSTEM_ADMIN']:
                result_data['delete_url'] = f"/students/students/confirm_delete_student/{student.pk}/"
            
            # إضافة البيانات المالية حسب الصلاحية
            if user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
                result_data.update({
                    'financial_status': student.get_financial_status(),
                    'status_color': student.get_status_color(),
                    'total_owed': float(student.total_owed or 0),
                })
        
            results.append(result_data)
        
        return JsonResponse({
            'students': results,
            'permissions': {
                'can_edit': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'],
                'can_delete': user_role in ['SYSTEM_ADMIN'],
                'can_view_financial': user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'],
            }
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

# ===================================
# 🔌 APIs المساعدة
# ===================================

@never_cache
@students_basic_access
def get_grades_by_level(request, level_id):
    """API لجلب الصفوف الدراسية حسب المرحلة التعليمية"""
    try:
        education_level = get_object_or_404(EducationLevel, id=level_id, is_active=True)
        grades = GradeLevel.objects.filter(
            education_level=education_level, 
            is_active=True
        ).order_by('order')
        
        grades_data = []
        for grade in grades:
            grades_data.append({
                'id': grade.id,
                'name': grade.name,
                'name_en': grade.name_en or '',
                'typical_age': grade.typical_age,
                'grade_number': grade.grade_number,
            })
        
        return JsonResponse({
            'success': True,
            'grades': grades_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# ===================================
# 📊 التقارير (حسب الصلاحية)
# ===================================

@never_cache
@students_reports_access
def report(request):
    """التقرير العام - للمدير والإدارة فقط"""
    user_role = get_user_role(request.user)
    
    # إحصائيات شاملة
    stats = {
        'total_students': Student.objects.filter(is_active=True).count(),
        'male_students': Student.objects.filter(gender='M', is_active=True).count(),
        'female_students': Student.objects.filter(gender='F', is_active=True).count(),
        'students_paid': Student.objects.filter(total_owed__lte=0, is_active=True).count(),
        'students_owing': Student.objects.filter(total_owed__gt=0, is_active=True).count(),
    }
    
    context = {
        'stats': stats,
        'user_role': user_role,
        'title': 'التقرير العام للطلاب',
    }
    return render(request, 'students/report.html', context)

# إضافة imports في أول الملف
from school_settings.models import (
    SchoolFeesSettings,
    StudentDiscount,
    AcademicYear as SettingsAcademicYear,
    EducationLevel, 
    GradeLevel,
    SystemSettings
)

@never_cache
@students_advanced_reports
def all_reports(request):
    """جميع التقارير المتقدمة - للمدير والإدارة فقط"""
    user_role = get_user_role(request.user)
    system_settings, current_year = get_system_data()
    
    # الإحصائيات العامة
    total_students = Student.objects.filter(is_active=True).count()
    male_students = Student.objects.filter(gender='M', is_active=True).count()
    female_students = Student.objects.filter(gender='F', is_active=True).count()
    
    # الإحصائيات المالية من إعدادات المصروفات
    financial_stats = {}
    if user_role == 'SYSTEM_ADMIN' and current_year:
        try:
            # حساب إجمالي المصروفات من إعدادات المصروفات
            total_fees_from_settings = SchoolFeesSettings.objects.filter(
                academic_year=current_year,
                is_active=True
            ).aggregate(
                total_fees=Sum('total_amount')
            )['total_fees'] or 0
            
            # حساب المصروفات لكل طالب بناءً على صفه
            students_fees_data = []
            for student in Student.objects.filter(is_active=True).select_related('grade_level'):
                student_fees = SchoolFeesSettings.objects.filter(
                    academic_year=current_year,
                    grade_level=student.grade_level,
                    is_active=True
                ).aggregate(
                    total=Sum('total_amount')
                )['total'] or 0
                
                students_fees_data.append({
                    'student': student,
                    'fees': student_fees,
                    'payments': student.total_payments or 0,
                    'owed': student_fees - (student.total_payments or 0)
                })
            
            # حساب الإجماليات
            total_calculated_fees = sum(item['fees'] for item in students_fees_data)
            total_payments = sum(item['payments'] for item in students_fees_data)
            total_owed = sum(item['owed'] for item in students_fees_data)
            
            # عدد الطلاب المدفوعين والمتأخرين
            paid_students = sum(1 for item in students_fees_data if item['owed'] <= 0)
            unpaid_students = sum(1 for item in students_fees_data if item['owed'] > 0)
            
            financial_stats = {
                'total_fees_from_settings': total_fees_from_settings,
                'total_calculated_fees': total_calculated_fees,
                'total_payments': total_payments,
                'total_owed': total_owed,
                'paid_students': paid_students,
                'unpaid_students': unpaid_students,
                'collection_percentage': (total_payments / total_calculated_fees * 100) if total_calculated_fees > 0 else 0,
            }
            
        except Exception as e:
            print(f"خطأ في حساب الإحصائيات المالية: {e}")
            financial_stats = {
                'total_fees_from_settings': 0,
                'total_calculated_fees': 0,
                'total_payments': 0,
                'total_owed': 0,
                'paid_students': 0,
                'unpaid_students': 0,
                'collection_percentage': 0,
            }
    
    # إحصائيات المراحل التعليمية
    education_levels_stats = []
    for level in EducationLevel.objects.filter(is_active=True).order_by('order'):
        students_count = Student.objects.filter(
            grade_level__education_level=level,
            is_active=True
        ).count()
        
        # إحصائيات الجنس لكل مرحلة
        level_male = Student.objects.filter(
            grade_level__education_level=level,
            gender='M',
            is_active=True
        ).count()
        
        level_female = Student.objects.filter(
            grade_level__education_level=level,
            gender='F',
            is_active=True
        ).count()
        
        # الإحصائيات المالية للمرحلة (للمدير العام فقط)
        level_financial = {}
        if user_role == 'SYSTEM_ADMIN' and current_year:
            try:
                # حساب مصروفات المرحلة
                level_grades = GradeLevel.objects.filter(
                    education_level=level,
                    is_active=True
                )
                
                level_fees_total = SchoolFeesSettings.objects.filter(
                    academic_year=current_year,
                    grade_level__in=level_grades,
                    is_active=True
                ).aggregate(
                    total=Sum('total_amount')
                )['total'] or 0
                
                # حساب مدفوعات طلاب المرحلة
                level_students = Student.objects.filter(
                    grade_level__education_level=level,
                    is_active=True
                )
                
                level_payments = level_students.aggregate(
                    total=Sum('total_payments')
                )['total'] or 0
                
                level_financial = {
                    'total_fees': level_fees_total,
                    'total_payments': level_payments,
                    'total_owed': level_fees_total - level_payments,
                }
                
            except Exception as e:
                print(f"خطأ في حساب مالية المرحلة {level.name}: {e}")
                level_financial = {
                    'total_fees': 0,
                    'total_payments': 0,
                    'total_owed': 0,
                }
        
        education_levels_stats.append({
            'level': level,
            'total_students': students_count,
            'male_students': level_male,
            'female_students': level_female,
            'percentage': round((students_count * 100 / total_students) if total_students > 0 else 0, 1),
            'financial': level_financial
        })
    
    # إحصائيات الصفوف الدراسية
    grade_levels_stats = []
    for grade in GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order'):
        students_count = Student.objects.filter(grade_level=grade, is_active=True).count()
        
        grade_financial = {}
        if user_role == 'SYSTEM_ADMIN' and current_year:
            try:
                # مصروفات الصف
                grade_fees = SchoolFeesSettings.objects.filter(
                    academic_year=current_year,
                    grade_level=grade,
                    is_active=True
                ).aggregate(
                    total=Sum('total_amount')
                )['total'] or 0
                
                # مدفوعات طلاب الصف
                grade_students = Student.objects.filter(
                    grade_level=grade,
                    is_active=True
                )
                
                grade_payments = grade_students.aggregate(
                    total=Sum('total_payments')
                )['total'] or 0
                
                grade_financial = {
                    'total_fees': grade_fees * students_count,  # مضروب في عدد الطلاب
                    'total_payments': grade_payments,
                    'total_owed': (grade_fees * students_count) - grade_payments,
                }
                
            except Exception as e:
                print(f"خطأ في حساب مالية الصف {grade.name}: {e}")
                grade_financial = {
                    'total_fees': 0,
                    'total_payments': 0,
                    'total_owed': 0,
                }
        
        if students_count > 0:  # عرض الصفوف التي بها طلاب فقط
            grade_levels_stats.append({
                'grade': grade,
                'total_students': students_count,
                'education_level': grade.education_level.name,
                'financial': grade_financial
            })
    
    # إحصائيات زمنية
    from datetime import timedelta
    today = timezone.now().date()
    
    time_stats = {
        'today': Student.objects.filter(created_at__date=today, is_active=True).count(),
        'this_week': Student.objects.filter(
            created_at__date__gte=today - timedelta(days=7),
            is_active=True
        ).count(),
        'this_month': Student.objects.filter(
            created_at__date__gte=today.replace(day=1),
            is_active=True
        ).count(),
        'this_year': Student.objects.filter(
            created_at__year=today.year,
            is_active=True
        ).count(),
    }
    
    # إحصائيات إعدادات المصروفات
    fees_settings_stats = {}
    if current_year:
        try:
            fees_settings_stats = {
                'total_fee_types': SchoolFeesSettings.objects.filter(
                    academic_year=current_year,
                    is_active=True
                ).count(),
                'grades_with_fees': SchoolFeesSettings.objects.filter(
                    academic_year=current_year,
                    is_active=True
                ).values('grade_level').distinct().count(),
                'average_fee_per_grade': SchoolFeesSettings.objects.filter(
                    academic_year=current_year,
                    is_active=True
                ).aggregate(avg=Avg('total_amount'))['avg'] or 0,
                'max_fee': SchoolFeesSettings.objects.filter(
                    academic_year=current_year,
                    is_active=True
                ).aggregate(max=Max('total_amount'))['max'] or 0,
                'min_fee': SchoolFeesSettings.objects.filter(
                    academic_year=current_year,
                    is_active=True
                ).aggregate(min=Min('total_amount'))['min'] or 0,
            }
        except Exception as e:
            print(f"خطأ في إحصائيات المصروفات: {e}")
            fees_settings_stats = {
                'total_fee_types': 0,
                'grades_with_fees': 0,
                'average_fee_per_grade': 0,
                'max_fee': 0,
                'min_fee': 0,
            }
    
    context = {
        'user_role': user_role,
        'system_settings': system_settings,
        'current_year': current_year,
        'total_students': total_students,
        'male_students': male_students,
        'female_students': female_students,
        'financial_stats': financial_stats,
        'education_levels_stats': education_levels_stats,
        'grade_levels_stats': grade_levels_stats,
        'time_stats': time_stats,
        'fees_settings_stats': fees_settings_stats,
        'title': 'التقارير الشاملة',
        'report_date': today,
    }
    return render(request, 'students/all_reports.html', context)


@never_cache
@students_reports_access
def report(request):
    """التقرير العام - للمدير والإدارة فقط"""
    user_role = get_user_role(request.user)
    system_settings, current_year = get_system_data()
    
    # إحصائيات أساسية
    total_students = Student.objects.filter(is_active=True).count()
    male_students = Student.objects.filter(gender='M', is_active=True).count()
    female_students = Student.objects.filter(gender='F', is_active=True).count()
    
    # إحصائيات المراحل التعليمية
    stage_stats = []
    for level in EducationLevel.objects.filter(is_active=True).order_by('order'):
        level_students = Student.objects.filter(
            grade_level__education_level=level,
            is_active=True
        ).count()
        
        level_male = Student.objects.filter(
            grade_level__education_level=level,
            gender='M',
            is_active=True
        ).count()
        
        level_female = Student.objects.filter(
            grade_level__education_level=level,
            gender='F',
            is_active=True
        ).count()
        
        # حساب مصروفات المرحلة من إعدادات المصروفات
        level_expenses = []
        if current_year:
            try:
                level_grades = GradeLevel.objects.filter(
                    education_level=level,
                    is_active=True
                )
                
                fees_by_grade = SchoolFeesSettings.objects.filter(
                    academic_year=current_year,
                    grade_level__in=level_grades,
                    is_active=True
                ).values(
                    'grade_level__name',
                    'fee_name',
                    'total_amount'
                ).order_by('grade_level__order', 'fee_type')
                
                for fee in fees_by_grade:
                    level_expenses.append({
                        'grade': fee['grade_level__name'],
                        'name': fee['fee_name'],
                        'amount': fee['total_amount']
                    })
                    
            except Exception as e:
                print(f"خطأ في حساب مصروفات المرحلة {level.name}: {e}")
        
        stage_stats.append({
            'stage': level,
            'total_stage_students': level_students,
            'male_students': level_male,
            'female_students': level_female,
            'percentage': round((level_students * 100 / total_students) if total_students > 0 else 0, 1),
            'expenses': level_expenses
        })
    
    # إحصائيات زمنية
    from datetime import timedelta
    today = timezone.now().date()
    
    stats = {
        'total_students': total_students,
        'male_students': male_students,
        'female_students': female_students,
        'registered_students': total_students,  # للتوافق مع القالب القديم
        'total_male_students': male_students,   # للتوافق مع القالب القديم
        'total_female_students': female_students,  # للتوافق مع القالب القديم
        'new_today': Student.objects.filter(created_at__date=today, is_active=True).count(),
        'new_this_week': Student.objects.filter(
            created_at__date__gte=today - timedelta(days=7),
            is_active=True
        ).count(),
        'new_this_month': Student.objects.filter(
            created_at__date__gte=today.replace(day=1),
            is_active=True
        ).count(),
    }
    
    # الإحصائيات المالية من إعدادات المصروفات
    if user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER'] and current_year:
        try:
            # حساب إجمالي المصروفات المتوقعة
            total_fees_settings = SchoolFeesSettings.objects.filter(
                academic_year=current_year,
                is_active=True
            ).aggregate(
                total=Sum('total_amount')
            )['total'] or 0
            
            # حساب المدفوعات الفعلية
            actual_payments = Student.objects.filter(
                is_active=True
            ).aggregate(
                total=Sum('total_payments')
            )['total'] or 0
            
            # حساب المبالغ المستحقة
            total_owed = Student.objects.filter(
                is_active=True
            ).aggregate(
                total=Sum('total_owed')
            )['total'] or 0
            
            # عدد الطلاب المدفوعين والمتأخرين
            paid_students_count = Student.objects.filter(
                total_owed__lte=0,
                is_active=True
            ).count()
            
            unpaid_students_count = Student.objects.filter(
                total_owed__gt=0,
                is_active=True
            ).count()
            
            stats.update({
                'students_paid': paid_students_count,
                'students_owing': unpaid_students_count,
                'total_paid_installments': actual_payments,
                'total_unpaid_students': unpaid_students_count,
                'total_tuitions': total_fees_settings,
                'expected_total_collection': total_fees_settings * total_students,  # إجمالي متوقع
                'collection_rate': (actual_payments / (total_fees_settings * total_students) * 100) if (total_fees_settings * total_students) > 0 else 0,
            })
            
        except Exception as e:
            print(f"خطأ في حساب الإحصائيات المالية: {e}")
            stats.update({
                'students_paid': 0,
                'students_owing': 0,
                'total_paid_installments': 0,
                'total_unpaid_students': 0,
                'total_tuitions': 0,
                'expected_total_collection': 0,
                'collection_rate': 0,
            })
    
    context = {
        'stats': stats,
        'stage_stats': stage_stats,
        'user_role': user_role,
        'system_settings': system_settings,
        'current_year': current_year,
        'title': 'التقرير العام للطلاب',
        'report_date': today,
    }
    return render(request, 'students/report.html', context)



@never_cache
@students_reports_access
def daily_report(request):
    """التقرير اليومي المحسن - للمدير والإدارة فقط"""
    today = timezone.now().date()
    user_role = get_user_role(request.user)
    system_settings, current_year = get_system_data()
    
    # تاريخ مخصص إذا تم اختياره
    selected_date = request.GET.get('date')
    if selected_date:
        try:
            today = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            today = timezone.now().date()
    
    # إحصائيات اليوم الأساسية
    today_stats = {
        'new_students': Student.objects.filter(created_at__date=today, is_active=True).count(),
        'total_active': Student.objects.filter(is_active=True).count(),
        'total_male_today': Student.objects.filter(created_at__date=today, gender='M', is_active=True).count(),
        'total_female_today': Student.objects.filter(created_at__date=today, gender='F', is_active=True).count(),
    }
    
    # الطلاب المضافون اليوم مع التفاصيل
    new_students_today = Student.objects.filter(
        created_at__date=today,
        is_active=True
    ).select_related(
        'grade_level__education_level'
    ).order_by('-created_at')
    
    # إحصائيات المدفوعات اليومية (إذا كان هناك نظام مدفوعات)
    daily_payments_stats = {}
    if user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
        try:
            # يمكن إضافة إحصائيات المدفوعات هنا إذا كان هناك نظام دفع
            # daily_payments = Payment.objects.filter(receipt_date__date=today)
            # لكن حالياً سنستخدم البيانات من Student model
            
            students_with_payments = Student.objects.filter(
                total_payments__gt=0,
                is_active=True
            )
            
            daily_payments_stats = {
                'total_collected_today': 0,  # يحتاج نظام مدفوعات منفصل
                'payments_count_today': 0,   # يحتاج نظام مدفوعات منفصل
                'students_with_payments': students_with_payments.count(),
                'total_outstanding': Student.objects.filter(
                    total_owed__gt=0,
                    is_active=True
                ).aggregate(total=Sum('total_owed'))['total'] or 0,
                'total_collected_all': Student.objects.filter(
                    is_active=True
                ).aggregate(total=Sum('total_payments'))['total'] or 0,
            }
            
        except Exception as e:
            print(f"خطأ في حساب إحصائيات المدفوعات: {e}")
            daily_payments_stats = {
                'total_collected_today': 0,
                'payments_count_today': 0,
                'students_with_payments': 0,
                'total_outstanding': 0,
                'total_collected_all': 0,
            }
    
    # إحصائيات الفصول والمراحل لليوم
    education_levels_today = []
    for level in EducationLevel.objects.filter(is_active=True).order_by('order'):
        level_students_today = Student.objects.filter(
            created_at__date=today,
            grade_level__education_level=level,
            is_active=True
        ).count()
        
        if level_students_today > 0:
            education_levels_today.append({
                'level': level,
                'students_count': level_students_today,
                'percentage': round((level_students_today * 100 / today_stats['new_students']) if today_stats['new_students'] > 0 else 0, 1)
            })
    

    # إحصائيات الأسبوع للمقارنة
    from datetime import timedelta
    week_start = today - timedelta(days=6)
    week_stats = []

    # حساب أقصى عدد طلاب لضبط الارتفاع
    max_students_in_week = 0
    week_data = []

    for i in range(7):
        day = week_start + timedelta(days=i)
        day_students = Student.objects.filter(
            created_at__date=day,
            is_active=True
        ).count()
        
        week_data.append({
            'date': day,
            'students_count': day_students,
            'is_today': day == today,
            'day_name': day.strftime('%A'),
            'day_name_ar': get_arabic_day_name(day.strftime('%A'))
        })
        
        if day_students > max_students_in_week:
            max_students_in_week = day_students

    # حساب الارتفاع النسبي لكل عمود
    for day_data in week_data:
        if max_students_in_week > 0:
            # ارتفاع نسبي من 20px إلى 200px
            height = 20 + (day_data['students_count'] / max_students_in_week) * 180
        else:
            height = 20
        
        day_data['bar_height'] = int(height)
        week_stats.append(day_data)
    
    # إحصائيات التسجيل بالساعات (إذا كان هناك تسجيل متكرر)
    hourly_stats = []
    if today_stats['new_students'] > 0:
        for hour in range(0, 24, 2):  # كل ساعتين
            hour_start = timezone.make_aware(
                datetime.combine(today, datetime.min.time().replace(hour=hour))
            )
            hour_end = hour_start + timedelta(hours=2)
            
            hour_count = Student.objects.filter(
                created_at__gte=hour_start,
                created_at__lt=hour_end,
                is_active=True
            ).count()
            
            if hour_count > 0:
                hourly_stats.append({
                    'hour_range': f"{hour:02d}:00 - {(hour+2):02d}:00",
                    'count': hour_count,
                    'percentage': round((hour_count * 100 / today_stats['new_students']), 1)
                })
    
    # التفاصيل المالية اليومية
    financial_summary = {}
    if user_role == 'SYSTEM_ADMIN' and current_year:
        try:
            # حساب المصروفات المتوقعة للطلاب الجدد اليوم
            expected_fees_today = 0
            for student in new_students_today:
                if student.grade_level:
                    student_fees = SchoolFeesSettings.objects.filter(
                        academic_year=current_year,
                        grade_level=student.grade_level,
                        is_active=True
                    ).aggregate(total=Sum('total_amount'))['total'] or 0
                    expected_fees_today += student_fees
            
            financial_summary = {
                'expected_fees_from_new_students': expected_fees_today,
                'average_fee_per_new_student': (expected_fees_today / today_stats['new_students']) if today_stats['new_students'] > 0 else 0,
            }
            
        except Exception as e:
            print(f"خطأ في حساب الملخص المالي: {e}")
            financial_summary = {
                'expected_fees_from_new_students': 0,
                'average_fee_per_new_student': 0,
            }
    
    context = {
        'report_date': today,
        'selected_date': today.strftime('%Y-%m-%d'),
        'today_stats': today_stats,
        'new_students_today': new_students_today,
        'daily_payments_stats': daily_payments_stats,
        'education_levels_today': education_levels_today,
        'week_stats': week_stats,
        'hourly_stats': hourly_stats,
        'financial_summary': financial_summary,
        'user_role': user_role,
        'system_settings': system_settings,
        'current_year': current_year,
        'title': f'التقرير اليومي - {today.strftime("%d/%m/%Y")}',
        'is_today': today == timezone.now().date(),
    }
    return render(request, 'students/daily_report.html', context)


def get_arabic_day_name(english_day):
    """تحويل اسم اليوم من الإنجليزية للعربية"""
    days_map = {
        'Monday': 'الإثنين',
        'Tuesday': 'الثلاثاء', 
        'Wednesday': 'الأربعاء',
        'Thursday': 'الخميس',
        'Friday': 'الجمعة',
        'Saturday': 'السبت',
        'Sunday': 'الأحد'
    }
    return days_map.get(english_day, english_day)

                  
@never_cache
@students_reports_access
def student_dashboard(request):
    """لوحة إحصائيات الطلاب - للمدير والإدارة"""
    user_role = get_user_role(request.user)
    
    # الإحصائيات الأساسية
    dashboard_stats = {
        'total': Student.objects.count(),
        'active': Student.objects.filter(is_active=True).count(),
        'new_today': Student.objects.filter(
            created_at__date=timezone.now().date()
        ).count(),
        'new_this_week': Student.objects.filter(
            created_at__date__gte=timezone.now().date() - timedelta(days=7)
        ).count(),
    }
    
    # إحصائيات الجنس
    male_students = Student.objects.filter(gender='M', is_active=True).count()
    female_students = Student.objects.filter(gender='F', is_active=True).count()
    
    # حساب النسب للجنس
    total_active = dashboard_stats['active']
    male_percentage = (male_students * 100 / total_active) if total_active > 0 else 0
    female_percentage = (female_students * 100 / total_active) if total_active > 0 else 0
    
    # إحصائيات المراحل التعليمية مع النسب
    education_levels_stats = []
    try:
        for level in EducationLevel.objects.filter(is_active=True).order_by('order'):
            student_count = Student.objects.filter(
                grade_level__education_level=level,
                is_active=True
            ).count()
            
            percentage = (student_count * 100 / total_active) if total_active > 0 else 0
            
            education_levels_stats.append({
                'name': level.name,
                'student_count': student_count,
                'percentage': round(percentage, 1)
            })
    except Exception:
        education_levels_stats = []
    
    context = {
        'stats': dashboard_stats,
        'male_students': male_students,
        'female_students': female_students,
        'male_percentage': round(male_percentage, 1),
        'female_percentage': round(female_percentage, 1),
        'education_levels_stats': education_levels_stats,
        'user_role': user_role,
        'title': 'لوحة إحصائيات الطلاب',
    }
    return render(request, 'students/student_dashboard.html', context)


# ===================================
# 🔧 الأدوات الإدارية (مدير عام فقط)
# ===================================

@never_cache
@students_sensitive_operation
def export_students(request):
    """تصدير بيانات الطلاب - للمدير العام فقط"""
    from django.http import HttpResponse
    import csv
    
    if request.method == 'POST':
        try:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="students_export.csv"'
            response.write('\ufeff'.encode('utf8'))  # BOM للعربية
            
            writer = csv.writer(response)
            writer.writerow([
                'الرقم الطلابي', 'الاسم', 'الرقم القومي', 'العمر', 'الجنس',
                'المرحلة التعليمية', 'الصف', 'رقم الهاتف', 'العنوان',
                'اسم ولي الأمر', 'هاتف ولي الأمر', 'إجمالي المدفوعات',
                'إجمالي المصروفات', 'المستحقات', 'تاريخ التسجيل'
            ])
            
            students = Student.objects.filter(is_active=True).select_related(
                'grade_level__education_level', 'academic_year'
            )
            
            for student in students:
                writer.writerow([
                    student.id,
                    student.name,
                    student.national_number,
                    student.age or 0,
                    'ذكر' if student.gender == 'M' else 'أنثى' if student.gender == 'F' else 'غير محدد',
                    student.education_level_name,
                    student.grade_name,
                    student.phone_number or '',
                    student.address or '',
                    student.parent_name or '',
                    student.parent_phone or '',
                    float(student.total_payments),
                    float(student.total_fees),
                    float(student.total_owed),
                    student.created_at.strftime('%Y-%m-%d') if student.created_at else '',
                ])
            
            messages.success(request, 'تم تصدير بيانات الطلاب بنجاح!')
            return response
            
        except Exception as e:
            messages.error(request, f'حدث خطأ في التصدير: {str(e)}')
    
    context = {
        'total_students': Student.objects.filter(is_active=True).count(),
        'title': 'تصدير بيانات الطلاب',
    }
    return render(request, 'students/export_students.html', context)

@never_cache
@students_sensitive_operation
def upgrade_students(request):
    """ترقية الطلاب للعام الجديد - للمدير العام فقط"""
    if request.method == 'POST':
        try:
            # منطق الترقية (سيتم تطويره لاحقاً)
            count = 0  # عدد الطلاب المرقين
            
            messages.success(request, f'تم ترقية {count} طالب بنجاح للعام الدراسي الجديد')
            return redirect('students:student_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ في الترقية: {str(e)}')
    
    context = {
        'warning_message': 'عملية الترقية تؤثر على جميع الطلاب المختارين ولا يمكن التراجع عنها',
        'total_students': Student.objects.filter(is_active=True).count(),
        'title': 'ترقية الطلاب للعام الجديد',
    }
    
    return render(request, 'students/upgrade_students.html', context)

# في students/views.py - إضافة هذه Views

@never_cache
@students_sensitive_operation
def export_students_advanced(request):
    """تصدير متقدم للطلاب"""
    if request.method == 'POST':
        export_format = request.POST.get('export_format', 'csv')
        include_inactive = request.POST.get('include_inactive', False)
        grade_levels = request.POST.getlist('grade_levels')
        
        # تحديد الطلاب للتصدير
        queryset = Student.objects.all()
        
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        
        if grade_levels:
            queryset = queryset.filter(grade_level_id__in=grade_levels)
        
        # إنشاء المُصدِّر
        exporter = StudentExporter(queryset)
        
        try:
            if export_format == 'csv':
                return exporter.export_csv(request)
            elif export_format == 'excel':
                return exporter.export_excel(request)
            elif export_format == 'json':
                return exporter.export_json(request)
            else:
                messages.error(request, 'صيغة التصدير غير مدعومة')
        
        except Exception as e:
            messages.error(request, f'خطأ في التصدير: {str(e)}')
    
    context = {
        'grade_levels': GradeLevel.objects.filter(is_active=True).select_related('education_level'),
        'total_students': Student.objects.filter(is_active=True).count(),
        'title': 'تصدير متقدم للطلاب'
    }
    return render(request, 'students/export_advanced.html', context)


@never_cache
@students_sensitive_operation
def import_students_advanced(request):
    """استيراد متقدم للطلاب"""
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, 'يرجى اختيار ملف للاستيراد')
            return redirect('students:import_students_advanced')
        
        file_obj = request.FILES['file']
        file_extension = file_obj.name.split('.')[-1].lower()
        
        # إنشاء المُستورِد
        importer = StudentImporter()
        
        try:
            if file_extension == 'csv':
                success = importer.process_csv_file(file_obj, request.user)
            elif file_extension in ['xlsx', 'xls']:
                success = importer.process_excel_file(file_obj, request.user)
            else:
                messages.error(request, 'صيغة الملف غير مدعومة. الصيغ المدعومة: CSV, Excel')
                return redirect('students:import_students_advanced')
            
            # عرض النتائج
            summary = importer.get_import_summary()
            
            if success and summary['success_count'] > 0:
                messages.success(request, 
                    f'تم استيراد {summary["success_count"]} طالب من أصل {summary["processed_count"]} بنجاح')
            
            if summary['errors']:
                for error in summary['errors'][:10]:  # عرض أول 10 أخطاء فقط
                    messages.error(request, error)
            
            if summary['warnings']:
                for warning in summary['warnings'][:5]:  # عرض أول 5 تحذيرات فقط
                    messages.warning(request, warning)
        
        except Exception as e:
            messages.error(request, f'خطأ في معالجة الملف: {str(e)}')
    
    context = {
        'title': 'استيراد متقدم للطلاب',
        'grade_levels': GradeLevel.objects.filter(is_active=True).select_related('education_level')
    }
    return render(request, 'students/import_advanced.html', context)


@never_cache
@students_sensitive_operation
def upgrade_students_wizard(request):
    """معالج ترقية الطلاب للعام الجديد"""
    
    # التحقق من توفر الأدوات
    if not UPGRADE_AVAILABLE or not StudentUpgradeManager:
        messages.error(request, 'أدوات ترقية الطلاب غير متوفرة حالياً')
        return redirect('students:student_list')
    
    try:
        upgrade_manager = StudentUpgradeManager()
    except Exception as e:
        messages.error(request, f'خطأ في تحميل أدوات الترقية: {str(e)}')
        return redirect('students:student_list')
    
    # التحقق من إمكانية الترقية
    try:
        can_upgrade, message = upgrade_manager.can_perform_upgrade()
    except Exception as e:
        can_upgrade = False
        message = f"خطأ في فحص إمكانية الترقية: {str(e)}"
    
    if request.method == 'POST':
        if not can_upgrade:
            messages.error(request, message)
            return redirect('students:upgrade_students_wizard')
        
        action = request.POST.get('action')
        
        if action == 'preview':
            # عرض المعاينة
            try:
                preview_data = upgrade_manager.get_upgrade_preview()
                context = {
                    'preview_data': preview_data,
                    'can_upgrade': can_upgrade,
                    'title': 'معاينة ترقية الطلاب'
                }
                return render(request, 'students/upgrade_preview.html', context)
            except Exception as e:
                messages.error(request, f'خطأ في معاينة الترقية: {str(e)}')
        
        elif action == 'confirm':
            # تنفيذ الترقية
            try:
                selected_grades = request.POST.getlist('selected_grades')
                upgrade_options = {
                    'reset_fees': request.POST.get('reset_fees') == 'on',
                    'archive_graduates': request.POST.get('archive_graduates') == 'on'
                }
                
                success = upgrade_manager.perform_upgrade(
                    [int(id) for id in selected_grades],
                    upgrade_options
                )
                
                summary = upgrade_manager.get_upgrade_summary()
                
                if success:
                    messages.success(request, 
                        f'تم ترقية {summary["upgraded_count"]} طالب، '
                        f'تخرج {summary["graduated_count"]} طالب، '
                        f'أُرشف {summary["archived_count"]} طالب')
                
                if summary['errors']:
                    for error in summary['errors']:
                        messages.error(request, error)
                
                return redirect('students:student_list')
            except Exception as e:
                messages.error(request, f'خطأ في تنفيذ الترقية: {str(e)}')
    
    # الحصول على العام الحالي
    try:
        current_year = SettingsAcademicYear.get_current_year()
    except:
        current_year = None
    
    context = {
        'can_upgrade': can_upgrade,
        'message': message,
        'current_year': current_year,
        'title': 'ترقية الطلاب للعام الجديد'
    }
    return render(request, 'students/upgrade_wizard.html', context)

@never_cache
@students_basic_access
def user_guide(request):
    """دليل استخدام النظام - متاح لجميع المستخدمين"""
    user_role = get_user_role(request.user)
    system_settings, current_year = get_system_data()
    
    # معلومات دور المستخدم للدليل
    role_info = {
        'SYSTEM_ADMIN': {
            'title': 'المدير العام',
            'permissions': ['جميع العمليات', 'العمليات الحساسة', 'التقارير المتقدمة', 'الأدوات الإدارية'],
            'color': 'danger'
        },
        'SCHOOL_MANAGER': {
            'title': 'مدير المدرسة',
            'permissions': ['إدارة الطلاب', 'التقارير العامة', 'البيانات المالية'],
            'color': 'primary'
        },
        'STUDENT_AFFAIRS': {
            'title': 'موظف شؤون الطلاب',
            'permissions': ['إضافة الطلاب', 'البحث والعرض'],
            'color': 'success'
        },
        'TEACHER': {
            'title': 'المعلم',
            'permissions': ['العرض فقط', 'البحث في الطلاب'],
            'color': 'info'
        }
    }
    
    current_role_info = role_info.get(user_role, {
        'title': 'مستخدم',
        'permissions': ['العرض الأساسي'],
        'color': 'secondary'
    })
    
    # إحصائيات سريعة للدليل
    stats = {
        'total_students': Student.objects.filter(is_active=True).count(),
        'education_levels': EducationLevel.objects.filter(is_active=True).count(),
        'grade_levels': GradeLevel.objects.filter(is_active=True).count(),
    }
    
    context = {
        'user_role': user_role,
        'current_role_info': current_role_info,
        'system_settings': system_settings,
        'current_year': current_year,
        'stats': stats,
        'title': 'دليل استخدام نظام إدارة الطلاب',
    }
    return render(request, 'students/user_guide.html', context)
