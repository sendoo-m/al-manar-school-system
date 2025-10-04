import csv
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db.models import Count, Sum, Q, F
from django.http import HttpResponse
from io import StringIO

# استيراد النماذج الجديدة
from students.models import Student, ArchiveStudent
from school_settings.models import (
    AcademicYear as SettingsAcademicYear, 
    EducationLevel, 
    GradeLevel,
    SystemSettings
)


def generate_daily_report():
    """إنشاء تقرير يومي"""
    today = date.today()
    
    # إحصائيات عامة
    total_students = Student.objects.filter(is_active=True).count()
    male_students = Student.objects.filter(gender='M', is_active=True).count()
    female_students = Student.objects.filter(gender='F', is_active=True).count()
    
    # الطلاب الجدد اليوم
    new_students_today = Student.objects.filter(
        created_at__date=today,
        is_active=True
    ).count()
    
    # الطلاب حسب المراحل التعليمية
    try:
        education_level_stats = EducationLevel.objects.filter(is_active=True).annotate(
            student_count=Count('gradelevel__student', filter=Q(gradelevel__student__is_active=True))
        ).order_by('order')
    except:
        education_level_stats = []
    
    # إحصائيات مالية
    total_owed = Student.objects.filter(is_active=True).aggregate(
        total=Sum('total_owed')
    )['total'] or Decimal('0')
    
    total_payments = Student.objects.filter(is_active=True).aggregate(
        total=Sum('total_payments')
    )['total'] or Decimal('0')
    
    students_owing = Student.objects.filter(total_owed__gt=0, is_active=True).count()
    students_paid = Student.objects.filter(total_owed__lte=0, is_active=True).count()
    
    report_data = {
        'date': today,
        'total_students': total_students,
        'male_students': male_students,
        'female_students': female_students,
        'new_students_today': new_students_today,
        'education_level_stats': education_level_stats,
        'total_owed': total_owed,
        'total_payments': total_payments,
        'students_owing': students_owing,
        'students_paid': students_paid,
    }
    
    return report_data


def generate_monthly_report(year=None, month=None):
    """إنشاء تقرير شهري"""
    if not year or not month:
        today = date.today()
        year = today.year
        month = today.month
    
    # تاريخ بداية ونهاية الشهر
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    # الطلاب الجدد في الشهر
    new_students = Student.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        is_active=True
    )
    
    # إحصائيات عامة
    total_students = Student.objects.filter(is_active=True).count()
    new_students_count = new_students.count()
    
    # توزيع حسب الجنس
    new_male_students = new_students.filter(gender='M').count()
    new_female_students = new_students.filter(gender='F').count()
    
    # توزيع حسب المراحل التعليمية
    try:
        education_level_distribution = new_students.values(
            'grade_level__education_level__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
    except:
        education_level_distribution = []
    
    # الطلاب المؤرشفين في الشهر
    archived_students = ArchiveStudent.objects.filter(
        archived_date__date__gte=start_date,
        archived_date__date__lte=end_date
    ).count()
    
    report_data = {
        'year': year,
        'month': month,
        'start_date': start_date,
        'end_date': end_date,
        'total_students': total_students,
        'new_students_count': new_students_count,
        'new_male_students': new_male_students,
        'new_female_students': new_female_students,
        'education_level_distribution': education_level_distribution,
        'archived_students': archived_students,
        'new_students_list': new_students.select_related('grade_level__education_level'),
    }
    
    return report_data


def generate_financial_report():
    """إنشاء تقرير مالي"""
    
    # إحصائيات مالية عامة
    active_students = Student.objects.filter(is_active=True)
    
    total_fees = active_students.aggregate(total=Sum('total_fees'))['total'] or Decimal('0')
    total_payments = active_students.aggregate(total=Sum('total_payments'))['total'] or Decimal('0')
    total_owed = active_students.aggregate(total=Sum('total_owed'))['total'] or Decimal('0')
    
    # تصنيف الطلاب حسب الحالة المالية
    students_paid = active_students.filter(total_owed__lte=0).count()
    students_partial = active_students.filter(
        total_owed__gt=0, 
        total_owed__lt=F('total_fees')
    ).count()
    students_owing = active_students.filter(total_owed__gte=F('total_fees')).count()
    
    # التوزيع المالي حسب المراحل التعليمية
    try:
        financial_by_level = EducationLevel.objects.filter(is_active=True).annotate(
            total_students=Count('gradelevel__student', filter=Q(gradelevel__student__is_active=True)),
            total_fees=Sum('gradelevel__student__total_fees', filter=Q(gradelevel__student__is_active=True)),
            total_payments=Sum('gradelevel__student__total_payments', filter=Q(gradelevel__student__is_active=True)),
            total_owed=Sum('gradelevel__student__total_owed', filter=Q(gradelevel__student__is_active=True))
        ).order_by('order')
    except:
        financial_by_level = []
    
    # أعلى 10 طلاب في المستحقات
    top_owing_students = active_students.filter(total_owed__gt=0).order_by('-total_owed')[:10]
    
    report_data = {
        'total_students': active_students.count(),
        'total_fees': total_fees,
        'total_payments': total_payments,
        'total_owed': total_owed,
        'collection_rate': (total_payments / total_fees * 100) if total_fees > 0 else 0,
        'students_paid': students_paid,
        'students_partial': students_partial,
        'students_owing': students_owing,
        'financial_by_level': financial_by_level,
        'top_owing_students': top_owing_students,
        'report_date': datetime.now(),
    }
    
    return report_data


def generate_student_list_report(filters=None):
    """إنشاء تقرير قائمة الطلاب"""
    
    queryset = Student.objects.filter(is_active=True).select_related(
        'grade_level__education_level',
        'academic_year'
    )
    
    # تطبيق الفلاتر إن وجدت
    if filters:
        if filters.get('gender'):
            queryset = queryset.filter(gender=filters['gender'])
        
        if filters.get('education_level'):
            queryset = queryset.filter(grade_level__education_level_id=filters['education_level'])
        
        if filters.get('grade_level'):
            queryset = queryset.filter(grade_level_id=filters['grade_level'])
        
        if filters.get('academic_year'):
            queryset = queryset.filter(academic_year_id=filters['academic_year'])
        
        if filters.get('financial_status'):
            if filters['financial_status'] == 'paid':
                queryset = queryset.filter(total_owed__lte=0)
            elif filters['financial_status'] == 'partial':
                queryset = queryset.filter(total_owed__gt=0, total_owed__lt=F('total_fees'))
            elif filters['financial_status'] == 'owing':
                queryset = queryset.filter(total_owed__gte=F('total_fees'))
        
        if filters.get('age_min'):
            queryset = queryset.filter(age__gte=filters['age_min'])
        
        if filters.get('age_max'):
            queryset = queryset.filter(age__lte=filters['age_max'])
    
    students = queryset.order_by('name')
    
    # إحصائيات
    total_count = students.count()
    male_count = students.filter(gender='M').count()
    female_count = students.filter(gender='F').count()
    
    total_fees = students.aggregate(total=Sum('total_fees'))['total'] or Decimal('0')
    total_payments = students.aggregate(total=Sum('total_payments'))['total'] or Decimal('0')
    total_owed = students.aggregate(total=Sum('total_owed'))['total'] or Decimal('0')
    
    report_data = {
        'students': students,
        'total_count': total_count,
        'male_count': male_count,
        'female_count': female_count,
        'total_fees': total_fees,
        'total_payments': total_payments,
        'total_owed': total_owed,
        'filters': filters or {},
        'report_date': datetime.now(),
    }
    
    return report_data


def export_students_to_csv(students_queryset=None):
    """تصدير الطلاب إلى CSV"""
    if students_queryset is None:
        students_queryset = Student.objects.filter(is_active=True).select_related(
            'grade_level__education_level',
            'academic_year'
        )
    
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="students_report_{datetime.now().strftime("%Y%m%d_%H%M")}.csv"'
    
    writer = csv.writer(response)
    
    # كتابة الرؤوس
    writer.writerow([
        'اسم الطالب',
        'الرقم القومي', 
        'العمر',
        'الجنس',
        'تاريخ الميلاد',
        'رقم الهاتف',
        'العنوان',
        'الصف الدراسي',
        'المرحلة التعليمية',
        'العام الدراسي',
        'إجمالي المصروفات',
        'إجمالي المدفوعات',
        'المستحقات',
        'الحالة المالية',
        'اسم ولي الأمر',
        'هاتف ولي الأمر',
        'بريد ولي الأمر',
        'تاريخ التسجيل'
    ])
    
    # كتابة البيانات
    for student in students_queryset:
        writer.writerow([
            student.name,
            student.national_number,
            student.age or '',
            'ذكر' if student.gender == 'M' else 'أنثى' if student.gender == 'F' else '',
            student.date_of_birth.strftime('%Y-%m-%d') if student.date_of_birth else '',
            student.phone_number,
            student.address,
            student.grade_name,
            student.education_level_name,
            str(student.academic_year) if student.academic_year else '',
            float(student.total_fees) if student.total_fees else 0,
            float(student.total_payments) if student.total_payments else 0,
            float(student.total_owed) if student.total_owed else 0,
            student.get_financial_status(),
            student.parent_name,
            student.parent_phone,
            student.parent_email,
            student.created_at.strftime('%Y-%m-%d %H:%M') if student.created_at else ''
        ])
    
    return response


def generate_student_statistics():
    """إنشاء إحصائيات الطلاب"""
    
    active_students = Student.objects.filter(is_active=True)
    
    # إحصائيات عامة
    total_students = active_students.count()
    male_students = active_students.filter(gender='M').count()
    female_students = active_students.filter(gender='F').count()
    
    # التوزيع العمري
    age_distribution = {
        '3-6': active_students.filter(age__gte=3, age__lte=6).count(),
        '7-12': active_students.filter(age__gte=7, age__lte=12).count(),
        '13-15': active_students.filter(age__gte=13, age__lte=15).count(),
        '16-18': active_students.filter(age__gte=16, age__lte=18).count(),
        '19+': active_students.filter(age__gte=19).count(),
    }
    
    # التوزيع حسب المراحل التعليمية
    try:
        education_level_stats = EducationLevel.objects.filter(is_active=True).annotate(
            student_count=Count('gradelevel__student', filter=Q(gradelevel__student__is_active=True)),
            male_count=Count('gradelevel__student', filter=Q(
                gradelevel__student__is_active=True,
                gradelevel__student__gender='M'
            )),
            female_count=Count('gradelevel__student', filter=Q(
                gradelevel__student__is_active=True,
                gradelevel__student__gender='F'
            ))
        ).order_by('order')
    except:
        education_level_stats = []
    
    # التوزيع حسب الصفوف
    try:
        grade_level_stats = GradeLevel.objects.filter(is_active=True).annotate(
            student_count=Count('student', filter=Q(student__is_active=True))
        ).select_related('education_level').order_by('education_level__order', 'order')
    except:
        grade_level_stats = []
    
    # الإحصائيات المالية
    financial_stats = {
        'total_fees': active_students.aggregate(total=Sum('total_fees'))['total'] or Decimal('0'),
        'total_payments': active_students.aggregate(total=Sum('total_payments'))['total'] or Decimal('0'),
        'total_owed': active_students.aggregate(total=Sum('total_owed'))['total'] or Decimal('0'),
        'students_paid': active_students.filter(total_owed__lte=0).count(),
        'students_owing': active_students.filter(total_owed__gt=0).count(),
    }
    
    # إحصائيات التسجيل الأخيرة
    today = date.today()
    registration_stats = {
        'today': active_students.filter(created_at__date=today).count(),
        'this_week': active_students.filter(created_at__date__gte=today - timedelta(days=7)).count(),
        'this_month': active_students.filter(created_at__date__gte=today.replace(day=1)).count(),
    }
    
    return {
        'total_students': total_students,
        'male_students': male_students,
        'female_students': female_students,
        'age_distribution': age_distribution,
        'education_level_stats': education_level_stats,
        'grade_level_stats': grade_level_stats,
        'financial_stats': financial_stats,
        'registration_stats': registration_stats,
        'generated_at': datetime.now(),
    }


def generate_archived_students_report(start_date=None, end_date=None):
    """تقرير الطلاب المؤرشفين"""
    
    queryset = ArchiveStudent.objects.all()
    
    if start_date:
        queryset = queryset.filter(archived_date__date__gte=start_date)
    
    if end_date:
        queryset = queryset.filter(archived_date__date__lte=end_date)
    
    archived_students = queryset.order_by('-archived_date')
    
    # إحصائيات
    total_archived = archived_students.count()
    male_archived = archived_students.filter(archive_gender='M').count()
    female_archived = archived_students.filter(archive_gender='F').count()
    
    total_lost_fees = archived_students.aggregate(
        total=Sum('archive_total_owed')
    )['total'] or Decimal('0')
    
    # أسباب الأرشفة
    archive_reasons = archived_students.values('archived_reason').annotate(
        count=Count('id')
    ).order_by('-count')
    
    return {
        'archived_students': archived_students,
        'total_archived': total_archived,
        'male_archived': male_archived,
        'female_archived': female_archived,
        'total_lost_fees': total_lost_fees,
        'archive_reasons': archive_reasons,
        'start_date': start_date,
        'end_date': end_date,
        'generated_at': datetime.now(),
    }


def export_daily_report_csv():
    """تصدير التقرير اليومي إلى CSV"""
    report_data = generate_daily_report()
    
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="daily_report_{date.today().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    # كتابة البيانات
    writer.writerow(['التقرير اليومي', report_data['date'].strftime('%Y-%m-%d')])
    writer.writerow([])
    writer.writerow(['الإحصائيات العامة'])
    writer.writerow(['إجمالي الطلاب', report_data['total_students']])
    writer.writerow(['الطلاب الذكور', report_data['male_students']])
    writer.writerow(['الطالبات الإناث', report_data['female_students']])
    writer.writerow(['الطلاب الجدد اليوم', report_data['new_students_today']])
    writer.writerow([])
    writer.writerow(['الإحصائيات المالية'])
    writer.writerow(['إجمالي المستحقات', float(report_data['total_owed'])])
    writer.writerow(['إجمالي المدفوعات', float(report_data['total_payments'])])
    writer.writerow(['الطلاب المسددين', report_data['students_paid']])
    writer.writerow(['الطلاب المدينين', report_data['students_owing']])
    
    if report_data['education_level_stats']:
        writer.writerow([])
        writer.writerow(['التوزيع حسب المراحل التعليمية'])
        writer.writerow(['المرحلة التعليمية', 'عدد الطلاب'])
        for level in report_data['education_level_stats']:
            writer.writerow([level.name, level.student_count])
    
    return response


def export_financial_summary_csv():
    """تصدير ملخص مالي إلى CSV"""
    report_data = generate_financial_report()
    
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="financial_summary_{date.today().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    # كتابة الملخص المالي
    writer.writerow(['الملخص المالي', datetime.now().strftime('%Y-%m-%d %H:%M')])
    writer.writerow([])
    writer.writerow(['إجمالي الطلاب', report_data['total_students']])
    writer.writerow(['إجمالي المصروفات', float(report_data['total_fees'])])
    writer.writerow(['إجمالي المدفوعات', float(report_data['total_payments'])])
    writer.writerow(['إجمالي المستحقات', float(report_data['total_owed'])])
    writer.writerow(['معدل التحصيل %', f"{report_data['collection_rate']:.2f}"])
    writer.writerow([])
    writer.writerow(['تصنيف الطلاب'])
    writer.writerow(['طلاب مسددين بالكامل', report_data['students_paid']])
    writer.writerow(['طلاب مسددين جزئياً', report_data['students_partial']])
    writer.writerow(['طلاب مدينين', report_data['students_owing']])
    
    # أعلى المدينين
    if report_data['top_owing_students']:
        writer.writerow([])
        writer.writerow(['أعلى 10 طلاب في المستحقات'])
        writer.writerow(['اسم الطالب', 'الرقم القومي', 'المستحق عليه'])
        for student in report_data['top_owing_students']:
            writer.writerow([student.name, student.national_number, float(student.total_owed)])
    
    return response
