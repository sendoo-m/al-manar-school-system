from django.shortcuts import render
from report.reports import generate_daily_report, generate_monthly_report
from students.models import Tuition, Expense, Classroom
# from .reports import *

from .reports import generate_educational_stage_report, generate_classroom_report, generate_expenses_report, generate_installments_paid_report, generate_installments_unpaid_report


# Create your views here.


def installments_unpaid_report(request):
    installments_unpaid = Tuition.objects.filter(paid=False)
    context = {'installments_unpaid': installments_unpaid}
    return render(request, 'report/installments_unpaid_report.html', context)

def expenses_report(request):
    expenses = Expense.objects.all()
    context = {'expenses': expenses}
    return render(request, 'report/expenses_report.html', context)


def daily_report_view(request):
    # Generate the daily report and retrieve the required data
    total_students_added, total_students_paid, total_expenses = generate_daily_report()

    # Pass the data to the template
    context = {
        'total_students_added': total_students_added,
        'total_students_paid': total_students_paid,
        'total_expenses': total_expenses
    }

    return render(request, 'report/daily_report.html', context)


def monthly_report_view(request):
    generate_monthly_report()
    return render(request, 'report/monthly_report.html')

def expenses_report(request):
    expenses = Expense.objects.all()
    context = {'expenses': expenses}
    return render(request, 'report/expenses_report.html', context)

def installments_unpaid_report(request):
    generate_installments_unpaid_report()
    return render(request, 'report/installments_unpaid_report.html')

def educational_stage_report(request):
    generate_educational_stage_report()
    return render(request, 'report/educational_stage_report.html')

def classroom_report(request):
    generate_classroom_report()
    return render(request, 'report/classroom_report.html')

def installments_paid_report(request):
    generate_installments_paid_report()
    return render(request, 'report/installments_paid_report.html')

def generate_reports(request):
    generate_educational_stage_report()
    generate_classroom_report()
    generate_expenses_report()
    generate_installments_paid_report()
    generate_installments_unpaid_report()
    return render(request, 'report/generate_reports.html')
