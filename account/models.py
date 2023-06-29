from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


# Create your models here.

# account/models.py

class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Email field must be set')
        # email = self.normalize_email(email)
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)

class User(AbstractUser):
    username = models.CharField(max_length=150, unique=True)  # Add the username field
    # email = models.EmailField(unique=True)
    date_of_enrollment = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=20, null=True, blank=True)
    department = models.CharField(max_length=20, choices=[
        ('accounts', 'Accounts'),
        ('student_affairs', 'Student Affairs'),
        ('administration', 'Administration')
    ])
    
    USERNAME_FIELD = 'username'
    # REQUIRED_FIELDS = ['email']
    
    objects = CustomUserManager()
    
    class Meta:
        permissions = [
            ('can_view_reports', 'Can view all reports'),
            ('can_edit_employee', 'Can edit employee profile'),
            ('can_add_student', 'Can add new student'),
            ('can_edit_student', 'Can edit student profile'),
            ('can_add_expense', 'Can add new expense'),
            ('can_pay_installment', 'Can pay student installment')
        ]
