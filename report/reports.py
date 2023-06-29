from datetime import date, timedelta
from django.db.models import Sum
from datetime import date
from django.db.models import Count
from students.models import EducationalStage, Classroom, Expense, Tuition

def generate_daily_report():
    today = date.today()
    expenses = Expense.objects.filter(date=today)
    installments_paid = Tuition.objects.filter(receipt_date=today, paid=True)

    # Generate the report
    print("Daily Report:\n")
    print("Expenses:")
    for expense in expenses:
        print(expense.amount, expense.date)
    print("\nInstallments Paid:")
    for installment in installments_paid:
        print(installment.amount, installment.receipt_date)

def generate_monthly_report():
    today = date.today()
    first_day_of_month = today.replace(day=1)
    last_day_of_month = first_day_of_month.replace(day=28) + timedelta(days=4)

    expenses = Expense.objects.filter(date__range=(first_day_of_month, last_day_of_month))
    installments_paid = Tuition.objects.filter(receipt_date__range=(first_day_of_month, last_day_of_month), paid=True)

    # Generate the report
    print("Monthly Report:\n")
    print("Expenses:")
    for expense in expenses:
        print(expense.amount, expense.date)
    print("\nInstallments Paid:")
    for installment in installments_paid:
        print(installment.amount, installment.receipt_date)


def generate_educational_stage_report():
    educational_stages = EducationalStage.objects.all()

    # Generate the report
    print("Educational Stage Report:\n")
    for stage in educational_stages:
        classrooms = Classroom.objects.filter(educational_stage=stage)
        total_students = classrooms.aggregate(total_students=Count('student'))['total_students']
        total_fees_due = classrooms.aggregate(total_fees_due=Sum('total_owed'))['total_fees_due'] or 0

        print(f"Educational Stage: {stage.name}")
        print(f"Total Students: {total_students}")
        print(f"Total Fees Due: {total_fees_due}")
        print("")

def generate_classroom_report():
    classrooms = Classroom.objects.all()

    # Generate the report
    print("Classroom Report:\n")
    for classroom in classrooms:
        total_students = classroom.total_students()
        total_fees_due = classroom.total_fees_due()
        total_paid_students = classroom.total_paid_students()
        total_unpaid_students = classroom.total_unpaid_students()
        remaining_tuitions = classroom.remaining_tuitions()

        print(f"Classroom: {classroom.name}")
        print(f"Total Students: {total_students}")
        print(f"Total Fees Due: {total_fees_due}")
        print(f"Total Paid Students: {total_paid_students}")
        print(f"Total Unpaid Students: {total_unpaid_students}")
        print(f"Remaining Tuitions: {remaining_tuitions}")
        print("")

def generate_expenses_report():
    expenses = Expense.objects.all()

    # Generate the report
    print("Expenses Report:\n")
    for expense in expenses:
        print(f"Expense Type: {expense.expense_type}")
        print(f"Amount: {expense.amount}")
        print(f"Date: {expense.date}")
        print("")

def generate_installments_paid_report():
    installments_paid = Tuition.objects.filter(paid=True)

    # Generate the report
    print("Installments Paid Report:\n")
    for installment in installments_paid:
        print(f"Amount: {installment.amount}")
        print(f"Receipt Date: {installment.receipt_date}")
        print("")

def generate_installments_unpaid_report():
    installments_unpaid = Tuition.objects.filter(paid=False)

    # Generate the report
    print("Installments Unpaid Report:\n")
    for installment in installments_unpaid:
        print(f"Amount: {installment.amount}")
        print(f"Receipt Date: {installment.receipt_date}")
        print("")
