# home/forms.py - الملف الكامل المُحدث
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from school_settings.models import SystemRole
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import Group

# الحصول على نموذج المستخدم الصحيح
User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """نموذج إنشاء مستخدم متوافق مع SystemRole الموجود"""
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='الاسم الأول',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'أدخل الاسم الأول'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label='اسم العائلة',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'أدخل اسم العائلة'
        })
    )
    
    email = forms.EmailField(
        required=True,
        label='البريد الإلكتروني',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@email.com'
        })
    )
    
    username = forms.CharField(
        label='اسم المستخدم',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم المستخدم (إنجليزي فقط)'
        })
    )
    
    password1 = forms.CharField(
        label='كلمة المرور',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'كلمة مرور قوية'
        })
    )
    
    password2 = forms.CharField(
        label='تأكيد كلمة المرور',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'أعد كتابة كلمة المرور'
        })
    )
    
    # الحقول الإضافية من User المخصص
    national_id = forms.CharField(
        max_length=14,
        required=False,
        label='الرقم القومي',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '14 رقم (اختياري)',
            'pattern': '[0-9]{14}',
            'title': 'يجب أن يكون 14 رقم'
        })
    )
    
    date_of_enrollment = forms.DateField(
        required=False,
        label='تاريخ التعيين',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    # اختيار الدور من SystemRole
    role = forms.ChoiceField(
        choices=SystemRole.ROLE_CHOICES,
        required=True,
        label='الدور الوظيفي',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label='حساب نشط',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    is_staff = forms.BooleanField(
        required=False,
        initial=False,
        label='صلاحية الوصول للوحة الإدارة',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 
                 'password1', 'password2', 'national_id', 
                 'date_of_enrollment', 'role', 'is_active', 'is_staff')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 🔒 إزالة خيار مدير النظام من القائمة لأمان إضافي
        role_choices = [choice for choice in SystemRole.ROLE_CHOICES if choice[0] != 'SYSTEM_ADMIN']
        self.fields['role'].choices = role_choices
    
    def clean_national_id(self):
        national_id = self.cleaned_data.get('national_id')
        if national_id:
            if len(national_id) != 14:
                raise ValidationError('الرقم القومي يجب أن يكون 14 رقم')
            if not national_id.isdigit():
                raise ValidationError('الرقم القومي يجب أن يحتوي على أرقام فقط')
            # فحص إذا كان مستخدم بنفس الرقم القومي
            if User.objects.filter(national_id=national_id).exists():
                raise ValidationError('يوجد مستخدم آخر بنفس الرقم القومي')
        return national_id
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('يوجد مستخدم آخر بنفس البريد الإلكتروني')
        return email
    
    def clean_role(self):
        """التأكد من عدم محاولة تعيين دور مدير النظام"""
        role = self.cleaned_data.get('role')
        
        if role == 'SYSTEM_ADMIN':
            raise ValidationError('🔒 لا يمكن تعيين دور مدير النظام من هنا. استخدم لوحة الإدارة Django.')
        
        return role
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_active = self.cleaned_data['is_active']
        user.is_staff = self.cleaned_data['is_staff']
        
        # الحقول الإضافية
        user.national_id = self.cleaned_data.get('national_id')
        user.date_of_enrollment = self.cleaned_data.get('date_of_enrollment')
        
        if commit:
            user.save()
            
            # إنشاء SystemRole للمستخدم
            SystemRole.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                is_active=self.cleaned_data['is_active']
            )
            
            # تعيين صلاحيات إضافية حسب الدور
            self.assign_role_permissions(user, self.cleaned_data['role'])
        
        return user
    
    def assign_role_permissions(self, user, role):
        """تعيين الصلاحيات والمجموعات حسب الدور"""
        
        # إذا كان مدير نظام، اعطه جميع الصلاحيات
        if role == 'SYSTEM_ADMIN':
            user.is_staff = True
            user.is_superuser = True
            user.save()
            return
        
        # إذا كان مدير مدرسة، اعطه صلاحية الوصول للإدارة
        elif role == 'SCHOOL_MANAGER':
            user.is_staff = True
            user.save()
        
        # تطبيق المجموعات للأدوار الجديدة
        role_groups_mapping = {
            # أدوار الخزينة
            'TREASURY_ADMIN': ['treasury_admin'],
            'TREASURY_MANAGER': ['treasury_manager'],
            'TREASURY_ACCOUNTANT': ['treasury_accountant'],
            'TREASURY_CASHIER': ['treasury_cashier'],
            'TREASURY_VIEWER': ['treasury_viewer'],
            
            # أدوار المخازن
            'BOOKS_INVENTORY': ['books_inventory_staff'],
            'UNIFORMS_INVENTORY': ['uniforms_inventory_staff'],
            'INVENTORY_MANAGER': ['books_inventory_staff', 'uniforms_inventory_staff', 'treasury_manager'],
            
            # الأدوار الأخرى
            'ACCOUNTANT': ['treasury_accountant'],  # ربط محاسب عام بالخزينة
        }
        
        groups_for_role = role_groups_mapping.get(role, [])
        
        for group_name in groups_for_role:
            try:
                group, created = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)
            except Exception as e:
                print(f"خطأ في إضافة المجموعة {group_name}: {e}")


class UserEditForm(forms.ModelForm):
    """نموذج تعديل المستخدم مع إمكانية تغيير كلمة المرور"""
    
    # إضافة حقل الدور
    role = forms.ChoiceField(
        choices=SystemRole.ROLE_CHOICES,
        required=True,
        label='الدور الوظيفي',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # الحقول الإضافية
    national_id = forms.CharField(
        max_length=14,
        required=False,
        label='الرقم القومي',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'pattern': '[0-9]{14}',
            'placeholder': '14 رقم (اختياري)'
        })
    )
    
    date_of_enrollment = forms.DateField(
        required=False,
        label='تاريخ التعيين',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    # ✅ إضافة حقول كلمة المرور
    change_password = forms.BooleanField(
        required=False,
        initial=False,
        label='تغيير كلمة المرور',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'changePasswordToggle'
        })
    )
    
    new_password1 = forms.CharField(
        required=False,
        label='كلمة المرور الجديدة',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'كلمة مرور قوية',
            'disabled': True
        })
    )
    
    new_password2 = forms.CharField(
        required=False,
        label='تأكيد كلمة المرور الجديدة',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'أعد كتابة كلمة المرور',
            'disabled': True
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 
                 'national_id', 'date_of_enrollment', 'is_active', 'is_staff', 
                 'role', 'change_password', 'new_password1', 'new_password2']
        
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        labels = {
            'username': 'اسم المستخدم',
            'first_name': 'الاسم الأول',
            'last_name': 'اسم العائلة',
            'email': 'البريد الإلكتروني',
            'is_active': 'حساب نشط',
            'is_staff': 'صلاحية الإدارة',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # إذا كان يحرر مستخدم موجود، اجلب دوره الحالي
        if self.instance and hasattr(self.instance, 'system_role'):
            self.fields['role'].initial = self.instance.system_role.role
        
        # 🔒 إزالة خيار مدير النظام من القائمة لأمان إضافي
        role_choices = [choice for choice in SystemRole.ROLE_CHOICES if choice[0] != 'SYSTEM_ADMIN']
        self.fields['role'].choices = role_choices
    
    def clean_national_id(self):
        national_id = self.cleaned_data.get('national_id')
        if national_id:
            if len(national_id) != 14:
                raise ValidationError('الرقم القومي يجب أن يكون 14 رقم')
            if not national_id.isdigit():
                raise ValidationError('الرقم القومي يجب أن يحتوي على أرقام فقط')
            
            # فحص إذا كان مستخدم آخر بنفس الرقم القومي (عدا المستخدم الحالي)
            existing_users = User.objects.filter(national_id=national_id)
            if self.instance:
                existing_users = existing_users.exclude(pk=self.instance.pk)
            
            if existing_users.exists():
                raise ValidationError('يوجد مستخدم آخر بنفس الرقم القومي')
        return national_id
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # فحص إذا كان مستخدم آخر بنفس البريد الإلكتروني (عدا المستخدم الحالي)
        existing_users = User.objects.filter(email=email)
        if self.instance:
            existing_users = existing_users.exclude(pk=self.instance.pk)
        
        if existing_users.exists():
            raise ValidationError('يوجد مستخدم آخر بنفس البريد الإلكتروني')
        return email
    
    def clean_role(self):
        """التأكد من عدم محاولة تعيين دور مدير النظام"""
        role = self.cleaned_data.get('role')
        
        if role == 'SYSTEM_ADMIN':
            raise ValidationError('🔒 لا يمكن تعيين دور مدير النظام من هنا. استخدم لوحة الإدارة Django.')
        
        return role
    
    def clean_new_password1(self):
        """التحقق من كلمة المرور الجديدة"""
        change_password = self.cleaned_data.get('change_password')
        new_password1 = self.cleaned_data.get('new_password1')
        
        if change_password:
            if not new_password1:
                raise ValidationError('كلمة المرور الجديدة مطلوبة')
            
            # التحقق من قوة كلمة المرور
            try:
                validate_password(new_password1)
            except ValidationError as e:
                raise ValidationError(e.messages)
        
        return new_password1
    
    def clean_new_password2(self):
        """التحقق من تطابق كلمتي المرور"""
        change_password = self.cleaned_data.get('change_password')
        new_password1 = self.cleaned_data.get('new_password1')
        new_password2 = self.cleaned_data.get('new_password2')
        
        if change_password:
            if not new_password2:
                raise ValidationError('تأكيد كلمة المرور مطلوب')
            
            if new_password1 != new_password2:
                raise ValidationError('كلمتا المرور غير متطابقتان')
        
        return new_password2
    
    def save(self, commit=True):
        user = super().save(commit)
        
        if commit:
            # تحديث كلمة المرور إذا تم طلب ذلك
            if self.cleaned_data.get('change_password') and self.cleaned_data.get('new_password1'):
                user.set_password(self.cleaned_data['new_password1'])
                user.save()
            
            # تحديث أو إنشاء SystemRole
            role, created = SystemRole.objects.get_or_create(
                user=user,
                defaults={'role': self.cleaned_data['role']}
            )
            
            if not created:
                role.role = self.cleaned_data['role']
                role.is_active = self.cleaned_data['is_active']
                role.save()
            
            # تحديث صلاحيات خاصة حسب الدور
            self.update_role_permissions(user, self.cleaned_data['role'])
        
        return user
    
    def update_role_permissions(self, user, role):
        """تحديث الصلاحيات والمجموعات حسب الدور"""
        
        # إزالة صلاحيات السوبر يوزر أولاً
        user.is_superuser = False
        user.is_staff = False
        
        # تعيين صلاحيات جديدة حسب الدور
        if role == 'SYSTEM_ADMIN':
            user.is_staff = True
            user.is_superuser = True
        elif role == 'SCHOOL_MANAGER':
            user.is_staff = True
        
        # الحفاظ على is_staff إذا كان محدد في الفورم
        if self.cleaned_data.get('is_staff'):
            user.is_staff = True
            
        user.save()
        
        # إزالة المجموعات السابقة وتطبيق الجديدة
        if not user.is_superuser:
            # إزالة مجموعات النظام فقط، الاحتفاظ بالمجموعات الأخرى
            system_groups = ['treasury_admin', 'treasury_manager', 'treasury_accountant', 
                           'treasury_cashier', 'treasury_viewer', 'books_inventory_staff', 
                           'uniforms_inventory_staff']
            
            for group_name in system_groups:
                try:
                    group = Group.objects.get(name=group_name)
                    user.groups.remove(group)
                except Group.DoesNotExist:
                    pass
            
            # تطبيق المجموعات الجديدة
            role_groups_mapping = {
                # أدوار الخزينة
                'TREASURY_ADMIN': ['treasury_admin'],
                'TREASURY_MANAGER': ['treasury_manager'],
                'TREASURY_ACCOUNTANT': ['treasury_accountant'],
                'TREASURY_CASHIER': ['treasury_cashier'],
                'TREASURY_VIEWER': ['treasury_viewer'],
                
                # أدوار المخازن
                'BOOKS_INVENTORY': ['books_inventory_staff'],
                'UNIFORMS_INVENTORY': ['uniforms_inventory_staff'],
                'INVENTORY_MANAGER': ['books_inventory_staff', 'uniforms_inventory_staff', 'treasury_manager'],
                
                # الأدوار الأخرى
                'ACCOUNTANT': ['treasury_accountant'],  # ربط محاسب عام بالخزينة
            }
            
            groups_for_role = role_groups_mapping.get(role, [])
            
            for group_name in groups_for_role:
                try:
                    group, created = Group.objects.get_or_create(name=group_name)
                    user.groups.add(group)
                except Exception as e:
                    print(f"خطأ في إضافة المجموعة {group_name}: {e}")


def get_role_descriptions():
    """أوصاف الأدوار الوظيفية - شاملة"""
    return {
        # الأدوار الأساسية
        'SYSTEM_ADMIN': {
            'name': '🔧 مدير النظام',
            'description': 'جميع الصلاحيات - إدارة كاملة للنظام',
            'permissions': ['إدارة المستخدمين', 'إعدادات النظام', 'جميع التقارير', 'لوحة الإدارة']
        },
        'SCHOOL_MANAGER': {
            'name': '👨‍💼 مدير المدرسة', 
            'description': 'إدارة عامة للمدرسة والإشراف على الأقسام',
            'permissions': ['إدارة الطلاب', 'التقارير العامة', 'الإشراف على الأقسام']
        },
        'ACCOUNTANT': {
            'name': '💰 محاسب عام',
            'description': 'إدارة الشؤون المالية والمحاسبية العامة',
            'permissions': ['نظام المدفوعات', 'التقارير المالية', 'إدارة الأقساط', 'صلاحيات الخزينة']
        },
        'STUDENT_AFFAIRS': {
            'name': '🎓 شؤون الطلاب',
            'description': 'إدارة بيانات الطلاب والسجلات الأكاديمية',
            'permissions': ['إضافة الطلاب', 'تعديل البيانات', 'التقارير الأكاديمية']
        },
        'TEACHER': {
            'name': '👩‍🏫 معلم',
            'description': 'صلاحيات التدريس وعرض بيانات الطلاب',
            'permissions': ['عرض الطلاب', 'الدرجات', 'التقارير الأكاديمية']
        },
        
        # ✅ أدوار الخزينة الجديدة
        'TREASURY_ADMIN': {
            'name': '💼 مدير الخزينة العام',
            'description': 'جميع صلاحيات الخزينة والإشراف الكامل',
            'permissions': ['إدارة الخزائن', 'إدارة الحسابات', 'التقارير المالية', 'إدارة مستخدمي الخزينة']
        },
        'TREASURY_MANAGER': {
            'name': '👨‍💼 مدير الخزينة',
            'description': 'إدارة العمليات المالية والإشراف',
            'permissions': ['إدارة العمليات', 'اعتماد المعاملات', 'التقارير الإدارية']
        },
        'TREASURY_ACCOUNTANT': {
            'name': '🧾 محاسب الخزينة',
            'description': 'العمليات المحاسبية والمالية المتخصصة',
            'permissions': ['تسجيل المعاملات', 'التقارير المحاسبية', 'مراجعة الحسابات']
        },
        'TREASURY_CASHIER': {
            'name': '💰 أمين الخزينة',
            'description': 'العمليات النقدية اليومية',
            'permissions': ['المعاملات النقدية', 'إدارة النقدية', 'تسجيل الإيرادات']
        },
        'TREASURY_VIEWER': {
            'name': '👁️ مراجع الخزينة',
            'description': 'مراجعة وعرض العمليات فقط',
            'permissions': ['عرض المعاملات', 'التقارير الأساسية', 'المراجعة']
        },
        
        # ✅ أدوار المخازن الجديدة
        'BOOKS_INVENTORY': {
            'name': '📚 موظف مخزن الكتب',
            'description': 'إدارة مخزون الكتب والمواد التعليمية',
            'permissions': ['إدارة مخزون الكتب', 'طلبات الكتب', 'توزيع المواد', 'تقارير المخزون']
        },
        'UNIFORMS_INVENTORY': {
            'name': '👕 موظف مخزن الملابس',
            'description': 'إدارة الزي المدرسي والملابس',
            'permissions': ['إدارة الزي المدرسي', 'طلبات الملابس', 'تقارير مخزن الملابس']
        },
        'INVENTORY_MANAGER': {
            'name': '📦 مدير المخازن',
            'description': 'الإشراف على جميع المخازن والمواد',
            'permissions': ['إدارة جميع المخازن', 'الإشراف على الموظفين', 'تقارير شاملة', 'صلاحيات الخزينة']
        }
    }


def get_inventory_group_descriptions():
    """أوصاف مجموعات المخازن والخزينة"""
    return {
        'treasury_admin': {
            'name': '💼 مدير الخزينة العام',
            'description': 'جميع صلاحيات الخزينة والإشراف الكامل',
            'permissions': ['إدارة الخزائن', 'إدارة الحسابات', 'التقارير المالية', 'إدارة المستخدمين']
        },
        'treasury_manager': {
            'name': '👨‍💼 مدير الخزينة',
            'description': 'إدارة العمليات المالية والإشراف',
            'permissions': ['إدارة العمليات', 'اعتماد المعاملات', 'التقارير الإدارية']
        },
        'treasury_accountant': {
            'name': '🧾 محاسب الخزينة',
            'description': 'العمليات المحاسبية والمالية',
            'permissions': ['تسجيل المعاملات', 'التقارير المحاسبية', 'مراجعة الحسابات']
        },
        'treasury_cashier': {
            'name': '💰 أمين الخزينة',
            'description': 'العمليات النقدية اليومية',
            'permissions': ['المعاملات النقدية', 'إدارة النقدية', 'تسجيل الإيرادات']
        },
        'treasury_viewer': {
            'name': '👁️ مراجع الخزينة',
            'description': 'مراجعة وعرض العمليات فقط',
            'permissions': ['عرض المعاملات', 'التقارير الأساسية', 'المراجعة']
        },
        'books_inventory_staff': {
            'name': '📚 موظف مخزن الكتب',
            'description': 'إدارة مخزون الكتب والمواد التعليمية',
            'permissions': ['إدارة مخزون الكتب', 'طلبات الكتب', 'توزيع المواد', 'تقارير المخزون']
        },
        'uniforms_inventory_staff': {
            'name': '👕 موظف مخزن الملابس',
            'description': 'إدارة الزي المدرسي والملابس',
            'permissions': ['إدارة الزي المدرسي', 'طلبات الملابس', 'تقارير مخزن الملابس']
        }
    }


def get_group_display_name(group_name):
    """الحصول على الاسم المعروض للمجموعة"""
    group_names = {
        'treasury_admin': 'مدير الخزينة العام',
        'treasury_manager': 'مدير الخزينة',
        'treasury_accountant': 'محاسب الخزينة',
        'treasury_cashier': 'أمين الخزينة',
        'treasury_viewer': 'مراجع الخزينة',
        'books_inventory_staff': 'موظف مخزن الكتب',
        'uniforms_inventory_staff': 'موظف مخزن الملابس',
    }
    return group_names.get(group_name, group_name)
