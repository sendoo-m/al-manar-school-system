from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from .models import Student, Classroom, Expense, Tuition

from datetime import date
from django.db.models import Sum

def generate_daily_report(date):
    students = Student.objects.filter(date_of_birth=date)
    classrooms = Classroom.objects.filter(created_at=date)
    expenses = Expense.objects.filter(date=date)
    installments_paid = Tuition.objects.filter(receipt_date=date, paid=True)
    installments_unpaid = Tuition.objects.filter(receipt_date=date, paid=False)

    # Generate the report
    print(f"Daily Report for {date}:\n")
    print("Students:")
    for student in students:
        print(student.name)

    print("\nClassrooms:")
    for classroom in classrooms:
        print(classroom.name)

    print("\nExpenses:")
    for expense in expenses:
        print(expense.expense_type)

    print("\nInstallments Paid:")
    for installment in installments_paid:
        print(installment.amount)

    print("\nInstallments Unpaid:")
    for installment in installments_unpaid:
        print(installment.amount)

def generate_monthly_report(year, month):
    students = Student.objects.filter(date_of_birth__year=year, date_of_birth__month=month)
    classrooms = Classroom.objects.filter(created_at__year=year, created_at__month=month)
    expenses = Expense.objects.filter(date__year=year, date__month=month)
    installments_paid = Tuition.objects.filter(receipt_date__year=year, receipt_date__month=month, paid=True)
    installments_unpaid = Tuition.objects.filter(receipt_date__year=year, receipt_date__month=month, paid=False)

    # Generate the report
    print(f"Monthly Report for {month}/{year}:\n")
    print("Students:")
    for student in students:
        print(student.name)

    print("\nClassrooms:")
    for classroom in classrooms:
        print(classroom.name)

    print("\nExpenses:")
    for expense in expenses:
        print(expense.expense_type)

    print("\nInstallments Paid:")
    for installment in installments_paid:
        print(installment.amount)

    print("\nInstallments Unpaid:")
    for installment in installments_unpaid:
        print(installment.amount)

def generate_educational_stage_report(stage):
    classrooms = Classroom.objects.filter(educational_stage__name=stage)
    students = Student.objects.filter(classroom__in=classrooms)
    expenses = Expense.objects.filter(classroom__in=classrooms)
    installments_paid = Tuition.objects.filter(student__in=students, paid=True)
    installments_unpaid = Tuition.objects.filter(student__in=students, paid=False)

    # Generate the report
    print(f"Educational Stage Report for {stage}:\n")
    print("Classrooms:")
    for classroom in classrooms:
        print(classroom.name)

    print("\nStudents:")
    for student in students:
        print(student.name)

    print("\nExpenses:")
    for expense in expenses:
        print(expense.expense_type)

    print("\nInstallments Paid:")
    for installment in installments_paid:
        print(installment.amount)

    print("\nInstallments Unpaid:")
    for installment in installments_unpaid:
        print(installment.amount)

def generate_classroom_report(classroom):
    students = Student.objects.filter(classroom=classroom)
    expenses = Expense.objects.filter(classroom=classroom)
    installments_paid = Tuition.objects.filter(student__in=students, paid=True)
    installments_unpaid = Tuition.objects.filter(student__in=students, paid=False)

    # Generate the report
    print(f"Classroom Report for {classroom.name}:\n")
    print("Students:")
    for student in students:
        print(student.name)

    print("\nExpenses:")
    for expense in expenses:
        print(expense.expense_type)

    print("\nInstallments Paid:")
    for installment in installments_paid:
        print(installment.amount)

    print("\nInstallments Unpaid:")
    for installment in installments_unpaid:
        print(installment.amount)

def generate_expenses_report():
    expenses = Expense.objects.all()

    # Generate the report
    print("Expenses Report:\n")
    for expense in expenses:
        print(expense.expense_type, expense.amount, expense.date)

def generate_installments_paid_report():
    installments_paid = Tuition.objects.filter(paid=True)

    # Generate the report
    print("Installments Paid Report:\n")
    for installment in installments_paid:
        print(installment.amount, installment.receipt_date)

def generate_installments_unpaid_report():
    installments_unpaid = Tuition.objects.filter(paid=False)

    # Generate the report
    print("Installments Unpaid Report:\n")
    for installment in installments_unpaid:
        print(installment.amount, installment.receipt_date)
