from django.db import models
from django.utils.timezone import now
from django.conf import settings
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum


# Create your models here.

class EducationalStage(models.Model):
    STAGE_CHOICES = (
        ('', 'اختار المرحلة الدراسية'),
        ('BC', 'babyclass'),
        ('Kindergarten', 'Kindergarten'),
        ('Primary Stage', 'Primary Stage'),
        ('Prep Stage', 'Prep Stage'),
        ('Secondary Stage', 'Secondary Stage'),
    )

    name = models.CharField(max_length=50, choices=STAGE_CHOICES, verbose_name="Educational Stage", default='default_value', null=True)

    def __str__(self):
        return self.name


class Classroom(models.Model):
    CLASS_CHOICES = (
        ('', 'اختار المرحلة التعليمية'),
        ('BC', 'مرحلة تمهيدي'),
        ('KG1', 'رياض أطفال 1'),
        ('KG2', 'رياض أطفال 2'),
        ('Prim1', 'الصف الأول الابتدائي'),
        ('Prim2', 'الصف الثاني الابتدائي'),
        ('Prim3', 'الصف الثالث الابتدائي'),
        ('Prim4', 'الصف الرابع الابتدائي'),
        ('Prim5', 'الصف الخامس الابتدائي'),
        ('Prim6', 'الصف السادس الابتدائي'),
        ('Prep7', 'الصف الأول الإعدادي'),
        ('Prep8', 'الصف الثاني الإعدادي'),
        ('Prep9', 'الصف الثالث الإعدادي'),
        ('Sec1', 'الصف الأول الثانوي'),
        ('Sec2', 'الصف الثاني الثانوي'),
        ('Sec3', 'الصف الثالث الثانوي'),
        
    )

    name = models.CharField(max_length=100, default='Default Classroom Name', null=True)
    stage = models.CharField(max_length=50, choices=CLASS_CHOICES, default='default_value', null=True)
    educational_stage = models.ForeignKey(EducationalStage, on_delete=models.CASCADE)
    fee_per_student = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return self.name

    
class AcademicYear(models.Model):
    year = models.CharField(max_length=4, unique=True, default='2023')

    def __str__(self):
        return self.year


class Expense(models.Model):
    classroom = models.ForeignKey(Classroom, related_name='classroom_expenses', on_delete=models.CASCADE, null=True)
    expense_type = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    date = models.DateField()
    total_owed = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # def __str__(self):
    #     return str(self.expense_type)

    # def update_total_owed(self):
    #     total_installments = self.classroom.student_set.aggregate(total_installments=Sum('installments__amount'))['total_installments'] or 0
    #     remaining_amount = self.amount - total_installments
    #     self.total_owed = remaining_amount - self.classroom.fee_per_student + self.get_discounted_amount()
    #     self.save()
    def __str__(self):
        return str(self.expense_type)

    def update_total_owed(self):
        total_installments = self.classroom.student_set.aggregate(total_installments=Sum('installments__amount'))['total_installments'] or 0
        remaining_amount = self.amount - total_installments
        self.total_owed = remaining_amount - self.classroom.fee_per_student + self.get_discounted_amount()
        self.save()

    
    # def __str__(self):
    #     return str(self.expense_type)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.classroom.fee_per_student -= self.amount
        self.classroom.save()
        self.update_total_owed()

    def update_total_owed(self):
        total_installments = self.classroom.student_set.aggregate(total_installments=Sum('installments__amount'))['total_installments'] or 0
        total_owed = self.amount - total_installments
        self.classroom.student_set.update(total_owed=total_owed)
    
    # def __str__(self):
    #     return str(self.expense_type)

    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     self.classroom.fee_per_student -= self.amount
    #     self.classroom.save()
    #     self.update_total_owed()

    # def update_total_owed(self):
    #     total_installments = self.classroom.student_set.aggregate(total_installments=Sum('installments__amount'))['total_installments'] or 0
    #     total_owed = self.amount - total_installments
    #     self.classroom.student_set.update(total_owed=total_owed)

class Tuition(models.Model):
    student = models.ForeignKey('Student', related_name='tuitions', on_delete=models.CASCADE)
    installment_number = models.IntegerField()
    amount_tuition = models.DecimalField(max_digits=8, decimal_places=2)
    paid = models.BooleanField(default=False)
    receipt_date = models.DateTimeField(default=timezone.now, editable=False)
    payment_user = models.CharField(max_length=50, default="account user")
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save the installment first

        if self.paid:
            self.student.update_total_payments()  # Update total_payments and total_owed for the student
        else:
            self.student.update_total_payments()  # Update total_payments and total_owed for the student when the installment is not paid

    def delete(self, *args, **kwargs):
        student = self.Student  # Store a reference to the associated student before deleting the tuition
        super().delete(*args, **kwargs)  # Delete the tuition
        student.update_total_payments()  # Update total_payments and total_owed for the student
        student.update_total_owed()  # Update total_owed and total_owed for the student

class Student(models.Model):
    GENDER_CHOICES = (
        ('', '---------'),
        ('M', 'Male'),
        ('F', 'Female'),
    )

    DISCOUNT_CHOICES = (
        ('NONE', 'No Discount'),
        ('CHAIRMAN', 'Chairman of the Board Discount'),
        ('VICE_CHAIRMAN', 'Vice Chairman of the Board Discount'),
        ('EMPLOYEE_CHILD', 'Employee Child Discount'),
        ('ARMED_FORCES', 'Armed Forces Discount'),
    )

    name = models.CharField(max_length=50)
    national_number = models.IntegerField(unique=True)
    age = models.IntegerField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, default=timezone.now, null=True, blank=True)
    classroom = models.ManyToManyField(Classroom)
    total_payments = models.DecimalField(max_digits=8, decimal_places=2, default=0, null=True, blank=True)
    total_owed = models.DecimalField(max_digits=8, decimal_places=2, default=0, null=True, blank=True)
    phone_number = models.CharField(max_length=20, default='')
    discount = models.CharField(max_length=20, choices=DISCOUNT_CHOICES, default='NONE')

    def __str__(self):
        return self.name

    def total_tuition(self):
        return self.tuitions.aggregate(total_tuition=Sum('amount_tuition'))['total_tuition'] or 0

    def update_total_payments(self):
        self.total_payments = self.tuitions.filter(paid=True).aggregate(total_payments=Sum('amount_tuition'))['total_payments'] or 0
        self.total_owed = self.total_tuition() - self.total_payments
        self.save()

    def save(self, *args, **kwargs):
        is_new_student = not self.pk
        super().save(*args, **kwargs)

        if is_new_student:
            self.total_owed = self.total_tuition()
            self.save()

    def update_total_payments(self):
        self.total_payments = self.tuitions.filter(paid=True).aggregate(total_payments=Sum('amount_tuition'))['total_payments'] or 0
        self.total_owed = self.calculate_total_owed()
        self.save()

    def calculate_total_owed(self):
        total_expenses = Expense.objects.filter(classroom__student=self).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
        total_payments = self.total_payments
        discount = self.get_discounted_amount()
        return total_expenses - total_payments - discount

    def total_students(self):
        return self.student_set.count()

    def total_fees_due(self):
        return self.student_set.filter(tuitions__paid=False).aggregate(total_fees_due=Sum('tuitions__amount'))['total_fees_due']

    def total_paid_students(self):
        return self.student_set.filter(tuitions__paid=True).count()

    def total_unpaid_students(self):
        return self.student_set.filter(tuitions__paid=False).count()

    def remaining_tuitions(self):
        return self.student_set.filter(tuitions__paid=False).aggregate(total_remaining_tuitions=Sum('tuitions__amount'))['total_remaining_tuitions']

    def get_discounted_amount(self):
        if self.discount == 'CHAIRMAN':
            return 5000  # Deduct L.E 5000 for Chairman discount
        elif self.discount == 'VICE_CHAIRMAN':
            return 3000  # Deduct L.E 3000 for Vice Chairman discount
        elif self.discount == 'EMPLOYEE_CHILD':
            return 4000  # Deduct L.E 4000 for Employee Child discount
        elif self.discount == 'ARMED_FORCES':
            return 2000  # Deduct L.E 2000 for Armed Forces discount
        else:
            return 0

    # def __str__(self):
    #     return self.name

    # def total_tuition(self):
    #     return self.tuitions.aggregate(total_tuition=Sum('amount_tuition'))['total_tuition'] or 0

    # def update_total_payments(self):
    #     self.total_payments = self.tuitions.filter(paid=True).aggregate(total_payments=Sum('amount_tuition'))['total_payments'] or 0
    #     self.total_owed = self.total_tuition() - self.total_payments
    #     self.save()

    # def save(self, *args, **kwargs):
    #     is_new_student = not self.pk
    #     super().save(*args, **kwargs)

    #     if is_new_student:
    #         self.total_owed = self.total_tuition()
    #         self.save()

    # # def update_total_payments(self):
    # #     self.total_payments = self.tuitions.filter(paid=True).aggregate(total_payments=Sum('amount_tuition'))['total_payments'] or 0
    # #     self.total_owed = self.calculate_total_owed()
    # #     self.save()

    # def calculate_total_owed(self):
    #     total_expenses = Expense.objects.filter(classroom__student=self).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
    #     total_payments = self.total_payments
    #     discount = self.get_discounted_amount()
    #     return total_expenses - total_payments - discount

    # # from my laptop dont it work
    # def calculate_total_owed(self):
    #     total_expenses = Expense.objects.filter(classroom__student=self).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
    #     total_payments = self.total_payments
    #     discount = self.get_discounted_amount()
    #     return total_expenses - total_payments - discount


    # def total_students(self):
    #     return self.student_set.count()

    # def total_fees_due(self):
    #     return self.student_set.filter(tuitions__paid=False).aggregate(total_fees_due=Sum('tuitions__amount'))['total_fees_due']

    # def total_paid_students(self):
    #     return self.student_set.filter(tuitions__paid=True).count()

    # def total_unpaid_students(self):
    #     return self.student_set.filter(tuitions__paid=False).count()

    # def remaining_tuitions(self):
    #     return self.student_set.filter(tuitions__paid=False).aggregate(total_remaining_tuitions=Sum('tuitions__amount'))['total_remaining_tuitions']

    # def get_discounted_amount(self):
    #     if self.discount == 'CHAIRMAN':
    #         return 5000  # Deduct $5000 for Chairman discount
    #     elif self.discount == 'VICE_CHAIRMAN':
    #         return 3000  # Deduct $3000 for Vice Chairman discount
    #     elif self.discount == 'EMPLOYEE_CHILD':
    #         return 4000  # Deduct $4000 for Employee Child discount
    #     elif self.discount == 'ARMED_FORCES':
    #         return 2000  # Deduct $2000 for Armed Forces discount
    #     else:
    #         return 0
    # def __str__(self):
    #     return self.name

    # def total_tuition(self):
    #     return self.tuitions.aggregate(total_tuition=Sum('amount_tuition'))['total_tuition'] or 0

    # def update_total_payments(self):
    #     self.total_payments = self.tuitions.filter(paid=True).aggregate(total_payments=Sum('amount_tuition'))['total_payments'] or 0
    #     self.total_owed = self.total_tuition() - self.total_payments
    #     self.save()

    # def total_students(self):
    #     return self.student_set.count()

    # def total_fees_due(self):
    #     return self.student_set.filter(tuitions__paid=False).aggregate(total_fees_due=Sum('tuitions__amount'))['total_fees_due']

    # def total_paid_students(self):
    #     return self.student_set.filter(tuitions__paid=True).count()

    # def total_unpaid_students(self):
    #     return self.student_set.filter(tuitions__paid=False).count()

    # def remaining_tuitions(self):
    #     return self.student_set.filter(tuitions__paid=False).aggregate(total_remaining_tuitions=Sum('tuitions__amount'))['total_remaining_tuitions']
     
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)

    def __str__(self):
        return self.user.username


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.timestamp}"

class ArchiveStudent(models.Model):
    GENDER_CHOICES = (
        ('', '---------'),
        ('M', 'Male'),
        ('F', 'Female'),
    )

    archive_name = models.CharField(max_length=50)
    archive_national_number = models.IntegerField(unique=True)
    archive_age = models.IntegerField()
    archive_gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    archive_date_of_birth = models.DateField()
    archive_academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, default=timezone.now)
    archive_classroom = models.ManyToManyField(Classroom)
    archive_total_payments = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    archive_total_owed = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return self.archive_name
