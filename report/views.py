from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Sum
from datetime import date, datetime, timedelta
from decimal import Decimal

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
def reports_home(request):
    """الصفحة الرئيسية للتقارير"""
    
    # إحصائيات سريعة
    quick_stats = generate_student_statistics()
    
    context = {
        'quick_stats': quick_stats,
        'today': date.today(),
    }
    
    return render(request, 'report/reports_home.html', context)


@never_cache
@login_required
def daily_report(request):
    """التقرير اليومي"""
    
    report_data = generate_daily_report()
    
    context = {
        'report_data': report_data,
        'title': 'التقرير اليومي',
    }
    
    return render(request, 'report/daily_report.html', context)


@never_cache
@login_required
def monthly_report(request):
    """التقرير الشهري"""
    
    # الحصول على السنة والشهر من الطلب
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            year = None
            month = None
    
    report_data = generate_monthly_report(year, month)
    
    # قائمة السنوات والشهور للفلتر
    current_year = date.today().year
    years = list(range(current_year - 5, current_year + 1))
    months = [
        (1, 'يناير'), (2, 'فبراير'), (3, 'مارس'), (4, 'أبريل'),
        (5, 'مايو'), (6, 'يونيو'), (7, 'يوليو'), (8, 'أغسطس'),
        (9, 'سبتمبر'), (10, 'أكتوبر'), (11, 'نوفمبر'), (12, 'ديسمبر')
    ]
    
    context = {
        'report_data': report_data,
        'years': years,
        'months': months,
        'selected_year': report_data['year'],
        'selected_month': report_data['month'],
        'title': f'التقرير الشهري - {report_data["month"]}/{report_data["year"]}',
    }
    
    return render(request, 'report/monthly_report.html', context)


@never_cache
@login_required
def financial_report(request):
    """التقرير المالي"""
    
    report_data = generate_financial_report()
    
    context = {
        'report_data': report_data,
        'title': 'التقرير المالي',
    }
    
    return render(request, 'report/financial_report.html', context)


@never_cache
@login_required
def student_list_report(request):
    """تقرير قائمة الطلاب"""
    
    # جمع الفلاتر من الطلب
    filters = {}
    
    if request.GET.get('gender'):
        filters['gender'] = request.GET.get('gender')
    
    if request.GET.get('education_level'):
        filters['education_level'] = int(request.GET.get('education_level'))
    
    if request.GET.get('grade_level'):
        filters['grade_level'] = int(request.GET.get('grade_level'))
    
    if request.GET.get('academic_year'):
        filters['academic_year'] = int(request.GET.get('academic_year'))
    
    if request.GET.get('financial_status'):
        filters['financial_status'] = request.GET.get('financial_status')
    
    if request.GET.get('age_min'):
        try:
            filters['age_min'] = int(request.GET.get('age_min'))
        except ValueError:
            pass
    
    if request.GET.get('age_max'):
        try:
            filters['age_max'] = int(request.GET.get('age_max'))
        except ValueError:
            pass
    
    # تصدير CSV إذا طُلب
    if request.GET.get('export') == 'csv':
        report_data = generate_student_list_report(filters)
        return export_students_to_csv(report_data['students'])
    
    # إنشاء التقرير
    report_data = generate_student_list_report(filters)
    
    # البيانات للفلاتر
    education_levels = EducationLevel.objects.filter(is_active=True).order_by('order')
    grade_levels = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order')
    academic_years = SettingsAcademicYear.objects.all().order_by('-year')
    
    context = {
        'report_data': report_data,
        'education_levels': education_levels,
        'grade_levels': grade_levels,
        'academic_years': academic_years,
        'filters': filters,
        'title': 'تقرير قائمة الطلاب',
    }
    
    return render(request, 'report/student_list_report.html', context)


@never_cache
@login_required
def statistics_report(request):
    """تقرير الإحصائيات"""
    
    statistics_data = generate_student_statistics()
    
    context = {
        'statistics_data': statistics_data,
        'title': 'تقرير الإحصائيات',
    }
    
    return render(request, 'report/statistics_report.html', context)


@never_cache
@login_required
def archived_students_report(request):
    """تقرير الطلاب المؤرشفين"""
    
    # الحصول على التواريخ من الطلب
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            start_date = None
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            end_date = None
    
    report_data = generate_archived_students_report(start_date, end_date)
    
    context = {
        'report_data': report_data,
        'start_date': start_date,
        'end_date': end_date,
        'title': 'تقرير الطلاب المؤرشفين',
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
