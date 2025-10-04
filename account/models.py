from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)

class User(AbstractUser):
    username = models.CharField(max_length=150, unique=True)
    date_of_enrollment = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=20, null=True, blank=True)
    
    # تم حذف حقل department - سنعتمد على SystemRole فقط
    
    USERNAME_FIELD = 'username'
    objects = CustomUserManager()
    
    # دالة للحصول على الدور من SystemRole
    def get_system_role(self):
        if hasattr(self, 'system_role'):
            return self.system_role.role
        return None
    
    # دالة للحصول على اسم الدور المعروض
    def get_role_display_name(self):
        if hasattr(self, 'system_role'):
            return self.system_role.get_role_display()
        return "غير محدد"
    
    # التحقق من صلاحية الوصول حسب الدور
    def has_role(self, role):
        return self.get_system_role() == role
    
    # التحقق من النشاط
    def is_role_active(self):
        if hasattr(self, 'system_role'):
            return self.system_role.is_active
        return False
    
    class Meta:
        permissions = [
            ('can_view_reports', 'Can view all reports'),
            ('can_edit_employee', 'Can edit employee profile'),
            ('can_add_student', 'Can add new student'),
            ('can_edit_student', 'Can edit student profile'),
            ('can_add_expense', 'Can add new expense'),
            ('can_pay_installment', 'Can pay student installment')
        ]
