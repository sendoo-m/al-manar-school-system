from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Group, Permission

from .models import User
from school_settings.models import SystemRole


class SystemRoleInline(admin.StackedInline):
    """إضافة الدور مباشرة في صفحة تعديل المستخدم"""
    model = SystemRole
    extra = 0
    max_num = 1
    can_delete = True

    fieldsets = (
        ('الدور والصلاحيات', {
            'fields': ('role', 'is_active'),
            'description': 'تحديد دور المستخدم في النظام',
        }),
    )


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    inlines = [SystemRoleInline]

    list_display = (
        'username',
        'get_full_name',
        'email',
        'get_role_display_name',
        'is_role_active',
        'is_staff',
        'is_active',
        'date_joined',
    )

    list_filter = (
        'is_staff',
        'is_superuser',
        'is_active',
        'date_of_enrollment',
        'system_role__role',
    )

    fieldsets = (
        ('معلومات الحساب', {'fields': ('username', 'password')}),
        ('المعلومات الشخصية', {
            'fields': ('first_name', 'last_name', 'email', 'date_of_enrollment', 'national_id')
        }),
        ('الصلاحيات الأساسية', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
            'description': 'الصلاحيات الأساسية - الدور يُحدد في القسم أدناه',
        }),
        ('صلاحيات متقدمة', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',),
            'description': 'تُحدد تلقائياً حسب الدور - لا تعدلها يدوياً إلا عند الحاجة',
        }),
        ('التواريخ المهمة', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
    )

    add_fieldsets = (
        ('معلومات الحساب الأساسية', {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
            'description': 'أدخل اسم المستخدم وكلمة المرور',
        }),
        ('المعلومات الشخصية', {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'email', 'date_of_enrollment', 'national_id'),
            'description': 'المعلومات الشخصية للمستخدم',
        }),
        ('الصلاحيات الأساسية', {
            'classes': ('wide',),
            'fields': ('is_staff', 'is_superuser', 'is_active'),
            'description': 'صلاحيات الوصول الأساسية',
        }),
    )

    search_fields = ('username', 'first_name', 'last_name', 'email', 'national_id')
    ordering = ('username',)

    def get_role_display_name(self, obj):
        return obj.get_role_display_name()
    get_role_display_name.short_description = 'الدور'

    def is_role_active(self, obj):
        return obj.is_role_active()
    is_role_active.boolean = True
    is_role_active.short_description = 'الدور نشط'

    def save_related(self, request, form, formsets, change):
        """حفظ الـ inline objects وتطبيق الصلاحيات"""
        super().save_related(request, form, formsets, change)

        user = form.instance
        if hasattr(user, 'system_role'):
            self.assign_user_permissions(user.system_role)

    def assign_user_permissions(self, system_role):
        """تطبيق صلاحيات المجموعة على المستخدم"""
        role_group_mapping = {
            'SYSTEM_ADMIN': 'مدير النظام',
            'SCHOOL_MANAGER': 'مدير المدرسة',
            'ACCOUNTANT': 'موظف الحسابات',
            'STUDENT_AFFAIRS': 'موظف شؤون الطلاب',
            'BOOKS_INVENTORY': 'موظف مخزن الكتب',
            'UNIFORMS_INVENTORY': 'موظف مخزن الملابس',

            # أدوار الخزينة
            'TREASURY_ADMIN': 'treasury_admin',
            'TREASURY_MANAGER': 'treasury_manager',
            'TREASURY_ACCOUNTANT': 'treasury_accountant',
            'TREASURY_CASHIER': 'treasury_cashier',
            'TREASURY_VIEWER': 'treasury_viewer',

            # أدوار المخازن
            'INVENTORY_MANAGER': 'inventory_manager',
        }

        user = system_role.user
        role = system_role.role

        if system_role.is_active and role in role_group_mapping:
            group_name = role_group_mapping[role]
            group, _ = Group.objects.get_or_create(name=group_name)

            if not user.is_superuser:
                user.groups.clear()

            user.groups.add(group)

            if not user.is_staff:
                user.is_staff = True
                user.save(update_fields=['is_staff'])

        elif not system_role.is_active:
            if not user.is_superuser:
                user.groups.clear()

            if not user.is_superuser and user.is_staff:
                user.is_staff = False
                user.save(update_fields=['is_staff'])

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        if not request.user.is_superuser:
            fieldsets = [fs for fs in fieldsets if fs[0] != 'صلاحيات متقدمة']

            modified_fieldsets = []
            for name, options in fieldsets:
                if name == 'الصلاحيات الأساسية':
                    options = options.copy()
                    options['fields'] = ('is_active',)
                modified_fieldsets.append((name, options))

            fieldsets = modified_fieldsets

        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))

        if not request.user.is_superuser:
            if hasattr(request.user, 'system_role'):
                user_role = request.user.system_role.role
                if user_role not in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
                    readonly_fields.extend(['is_staff', 'is_superuser'])
            else:
                readonly_fields.extend(['is_staff', 'is_superuser'])

        if obj and obj == request.user and not request.user.is_superuser:
            readonly_fields.extend(['is_staff', 'is_superuser'])

        return list(dict.fromkeys(readonly_fields))

    def has_delete_permission(self, request, obj=None):
        if obj and obj == request.user:
            return False

        if hasattr(request.user, 'system_role'):
            user_role = request.user.system_role.role
            if user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
                return True

        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if obj and obj == request.user:
            return True

        if hasattr(request.user, 'system_role'):
            user_role = request.user.system_role.role
            if user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
                return True

        return request.user.is_superuser

    def has_add_permission(self, request):
        if hasattr(request.user, 'system_role'):
            user_role = request.user.system_role.role
            if user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
                return True

        return request.user.is_superuser


def create_user_groups():
    """
    إنشاء مجموعات المستخدمين مع الصلاحيات المناسبة.

    مهم:
    لا تستدعي هذه الدالة في أسفل admin.py.
    شغلها يدوياً من shell أو من management command بعد تشغيل migrations.
    """
    groups_permissions = {
        'مدير النظام': None,  # كل الصلاحيات
        'مدير المدرسة': [
            'view_user', 'change_user', 'add_user',
            'add_student', 'change_student', 'view_student', 'delete_student',
            'add_classroom', 'change_classroom', 'view_classroom',
            'view_tuition', 'change_tuition',
            'add_expense', 'change_expense', 'view_expense',
            'view_systemsettings', 'change_systemsettings',
            'view_systemrole', 'change_systemrole', 'add_systemrole',
        ],
        'موظف الحسابات': [
            'view_student',
            'add_tuition', 'change_tuition', 'view_tuition',
            'add_expense', 'change_expense', 'view_expense',
            'view_systemsettings',
        ],
        'موظف شؤون الطلاب': [
            'add_student', 'change_student', 'view_student',
            'view_classroom',
            'add_archivestudent', 'change_archivestudent', 'view_archivestudent',
            'view_tuition',
        ],
        'موظف مخزن الكتب': [
            'view_student',
            'view_classroom',
        ],
        'موظف مخزن الملابس': [
            'view_student',
            'view_classroom',
        ],
        'treasury_admin': None,
        'treasury_manager': [
            'view_student',
            'view_tuition',
            'change_tuition',
            'view_systemsettings',
        ],
        'treasury_accountant': [
            'view_student',
            'add_tuition',
            'change_tuition',
            'view_tuition',
        ],
        'treasury_cashier': [
            'view_student',
            'add_tuition',
            'view_tuition',
        ],
        'treasury_viewer': [
            'view_student',
            'view_tuition',
        ],
        'inventory_manager': [
            'view_student',
            'view_classroom',
        ],
    }

    created_groups = []

    for group_name, permission_codenames in groups_permissions.items():
        group, created = Group.objects.get_or_create(name=group_name)

        if permission_codenames is None:
            permissions = Permission.objects.all()
        else:
            permissions = Permission.objects.filter(codename__in=permission_codenames)

        group.permissions.set(permissions)

        if created:
            created_groups.append(group_name)

    return created_groups


admin.site.register(User, CustomUserAdmin)

# مهم جداً:
# تم حذف create_user_groups() من هنا لأنه كان يعمل Query أثناء تحميل admin.py
# وهذا كان سبب تحذير:
# Accessing the database during app initialization is discouraged

admin.site.site_header = "School Management System"
admin.site.site_title = "School Admin"
admin.site.index_title = "Main Dashboard"

# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
# from .models import User
# from django.contrib.auth.forms import UserCreationForm, UserChangeForm
# from django.contrib.auth.models import Group, Permission
# from school_settings.models import SystemRole


# class SystemRoleInline(admin.StackedInline):
#     """إضافة الدور مباشرة في صفحة تعديل المستخدم"""
#     model = SystemRole
#     extra = 0
#     max_num = 1
#     can_delete = True
    
#     fieldsets = (
#         ('الدور والصلاحيات', {
#             'fields': ('role', 'is_active'),
#             'description': 'تحديد دور المستخدم في النظام'
#         }),
#     )


# class CustomUserCreationForm(UserCreationForm):
#     class Meta(UserCreationForm.Meta):
#         model = User
#         fields = ('username', 'first_name', 'last_name', 'email')


# class CustomUserChangeForm(UserChangeForm):
#     class Meta(UserChangeForm.Meta):
#         model = User


# class CustomUserAdmin(UserAdmin):
#     add_form = CustomUserCreationForm
#     form = CustomUserChangeForm
#     model = User
#     inlines = [SystemRoleInline]  # إضافة الـ inline للأدوار
    
#     list_display = ('username', 'get_full_name', 'email', 'get_role_display_name', 'is_role_active', 'is_staff', 'is_active', 'date_joined')
#     list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_of_enrollment', 'system_role__role')
    
#     fieldsets = (
#         ('معلومات الحساب', {'fields': ('username', 'password')}),
#         ('المعلومات الشخصية', {
#             'fields': ('first_name', 'last_name', 'email', 'date_of_enrollment', 'national_id')
#         }),
#         ('الصلاحيات الأساسية', {
#             'fields': ('is_active', 'is_staff', 'is_superuser'),
#             'description': 'الصلاحيات الأساسية - الدور يُحدد في القسم أدناه'
#         }),
#         ('صلاحيات متقدمة', {
#             'fields': ('groups', 'user_permissions'),
#             'classes': ('collapse',),
#             'description': 'تُحدد تلقائياً حسب الدور - لا تعدلها يدوياً'
#         }),
#         ('التواريخ المهمة', {
#             'fields': ('last_login', 'date_joined'),
#             'classes': ('collapse',)
#         }),
#     )
    
#     add_fieldsets = (
#         ('معلومات الحساب الأساسية', {
#             'classes': ('wide',),
#             'fields': ('username', 'password1', 'password2'),
#             'description': 'أدخل اسم المستخدم وكلمة المرور'
#         }),
#         ('المعلومات الشخصية', {
#             'classes': ('wide',),
#             'fields': ('first_name', 'last_name', 'email', 'date_of_enrollment', 'national_id'),
#             'description': 'المعلومات الشخصية للمستخدم'
#         }),
#         ('الصلاحيات الأساسية', {
#             'classes': ('wide',),
#             'fields': ('is_staff', 'is_superuser', 'is_active'),
#             'description': 'صلاحيات الوصول الأساسية'
#         }),
#     )
    
#     search_fields = ('username', 'first_name', 'last_name', 'email', 'national_id')
#     ordering = ('username',)
    
#     # دالة لعرض الدور في قائمة المستخدمين
#     def get_role_display_name(self, obj):
#         return obj.get_role_display_name()
#     get_role_display_name.short_description = 'الدور'
    
#     # دالة لعرض حالة الدور
#     def is_role_active(self, obj):
#         return obj.is_role_active()
#     is_role_active.boolean = True
#     is_role_active.short_description = 'الدور نشط'
    
#     def save_related(self, request, form, formsets, change):
#         """حفظ الـ inline objects وتطبيق الصلاحيات"""
#         super().save_related(request, form, formsets, change)
        
#         # تطبيق الصلاحيات بعد حفظ الدور
#         user = form.instance
#         if hasattr(user, 'system_role'):
#             self.assign_user_permissions(user.system_role)
    
#     def assign_user_permissions(self, system_role):
#         """تطبيق صلاحيات المجموعة على المستخدم"""
#         role_group_mapping = {
#             'SYSTEM_ADMIN': 'مدير النظام',
#             'SCHOOL_MANAGER': 'مدير المدرسة',
#             'ACCOUNTANT': 'موظف الحسابات',
#             'STUDENT_AFFAIRS': 'موظف شؤون الطلاب',
#             'BOOKS_INVENTORY': 'موظف مخزن الكتب',
#             'UNIFORMS_INVENTORY': 'موظف مخزن الملابس',
#         }
        
#         user = system_role.user
#         role = system_role.role
        
#         if system_role.is_active and role in role_group_mapping:
#             group_name = role_group_mapping[role]
#             try:
#                 group = Group.objects.get(name=group_name)
#                 user.groups.clear()
#                 user.groups.add(group)
#                 user.is_staff = True
#                 user.save()
#             except Group.DoesNotExist:
#                 pass
#         elif not system_role.is_active:
#             user.groups.clear()
#             if not user.is_superuser:
#                 user.is_staff = False
#             user.save()
    
#     # تخصيص الصلاحيات حسب المستخدم الحالي
#     def get_fieldsets(self, request, obj=None):
#         fieldsets = super().get_fieldsets(request, obj)
        
#         # إذا لم يكن المستخدم superuser، قم بإخفاء بعض الحقول
#         if not request.user.is_superuser:
#             # إزالة قسم الصلاحيات المتقدمة للمستخدمين غير المدراء
#             fieldsets = [fs for fs in fieldsets if fs[0] != 'صلاحيات متقدمة']
            
#             # تعديل قسم الصلاحيات الأساسية
#             modified_fieldsets = []
#             for name, options in fieldsets:
#                 if name == 'الصلاحيات الأساسية':
#                     options = options.copy()
#                     options['fields'] = ('is_active',)  # السماح بتفعيل/إلغاء تفعيل فقط
#                 modified_fieldsets.append((name, options))
#             fieldsets = modified_fieldsets
                
#         return fieldsets
    
#     def get_readonly_fields(self, request, obj=None):
#         readonly_fields = list(super().get_readonly_fields(request, obj))
        
#         # إذا لم يكن المستخدم superuser
#         if not request.user.is_superuser:
#             # السماح فقط لمدراء النظام والمدرسة بتعديل is_staff و is_superuser
#             if hasattr(request.user, 'system_role'):
#                 user_role = request.user.system_role.role
#                 if user_role not in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
#                     readonly_fields.extend(['is_staff', 'is_superuser'])
#             else:
#                 readonly_fields.extend(['is_staff', 'is_superuser'])
            
#         # منع المستخدمين من تعديل صلاحياتهم الخاصة
#         if obj and obj == request.user and not request.user.is_superuser:
#             readonly_fields.extend(['is_staff', 'is_superuser'])
            
#         return readonly_fields
    
#     def has_delete_permission(self, request, obj=None):
#         # منع حذف المستخدم لنفسه
#         if obj and obj == request.user:
#             return False
#         # السماح للمدراء بحذف المستخدمين
#         if hasattr(request.user, 'system_role'):
#             user_role = request.user.system_role.role
#             if user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
#                 return True
#         return request.user.is_superuser
    
#     def has_change_permission(self, request, obj=None):
#         # السماح للجميع بتعديل ملفاتهم الشخصية
#         if obj and obj == request.user:
#             return True
#         # تحديد الصلاحيات حسب الدور
#         if hasattr(request.user, 'system_role'):
#             user_role = request.user.system_role.role
#             if user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
#                 return True
#         return request.user.is_superuser
    
#     def has_add_permission(self, request):
#         # السماح بإضافة مستخدمين للمدراء فقط
#         if hasattr(request.user, 'system_role'):
#             user_role = request.user.system_role.role
#             if user_role in ['SYSTEM_ADMIN', 'SCHOOL_MANAGER']:
#                 return True
#         return request.user.is_superuser


# # إنشاء مجموعات الصلاحيات تلقائياً
# def create_user_groups():
#     """إنشاء مجموعات المستخدمين مع الصلاحيات المناسبة"""
    
#     # صلاحيات مدير النظام
#     system_admin_group, created = Group.objects.get_or_create(name='مدير النظام')
#     if created:
#         all_permissions = Permission.objects.all()
#         system_admin_group.permissions.set(all_permissions)
    
#     # صلاحيات مدير المدرسة
#     school_manager_group, created = Group.objects.get_or_create(name='مدير المدرسة')
#     if created:
#         manager_permissions = Permission.objects.filter(
#             codename__in=[
#                 'view_user', 'change_user', 'add_user',
#                 'add_student', 'change_student', 'view_student', 'delete_student',
#                 'add_classroom', 'change_classroom', 'view_classroom',
#                 'view_tuition', 'change_tuition',
#                 'add_expense', 'change_expense', 'view_expense',
#                 'view_systemsettings', 'change_systemsettings',
#                 'view_systemrole', 'change_systemrole', 'add_systemrole',
#             ]
#         )
#         school_manager_group.permissions.set(manager_permissions)
    
#     # صلاحيات موظف الحسابات
#     accountant_group, created = Group.objects.get_or_create(name='موظف الحسابات')
#     if created:
#         accountant_permissions = Permission.objects.filter(
#             codename__in=[
#                 'view_student',
#                 'add_tuition', 'change_tuition', 'view_tuition',
#                 'add_expense', 'change_expense', 'view_expense',
#                 'view_systemsettings',
#             ]
#         )
#         accountant_group.permissions.set(accountant_permissions)
    
#     # صلاحيات موظف شؤون الطلاب
#     student_affairs_group, created = Group.objects.get_or_create(name='موظف شؤون الطلاب')
#     if created:
#         student_affairs_permissions = Permission.objects.filter(
#             codename__in=[
#                 'add_student', 'change_student', 'view_student',
#                 'view_classroom',
#                 'add_archivestudent', 'change_archivestudent', 'view_archivestudent',
#                 'view_tuition',
#             ]
#         )
#         student_affairs_group.permissions.set(student_affairs_permissions)
    
#     # صلاحيات موظف مخزن الكتب
#     books_inventory_group, created = Group.objects.get_or_create(name='موظف مخزن الكتب')
#     if created:
#         books_permissions = Permission.objects.filter(
#             codename__in=[
#                 'view_student',
#                 'view_classroom',
#             ]
#         )
#         books_inventory_group.permissions.set(books_permissions)
    
#     # صلاحيات موظف مخزن الملابس
#     uniforms_inventory_group, created = Group.objects.get_or_create(name='موظف مخزن الملابس')
#     if created:
#         uniforms_permissions = Permission.objects.filter(
#             codename__in=[
#                 'view_student',
#                 'view_classroom',
#             ]
#         )
#         uniforms_inventory_group.permissions.set(uniforms_permissions)


# # تسجيل النموذج المخصص
# admin.site.register(User, CustomUserAdmin)

# # إنشاء المجموعات عند استيراد الملف
# create_user_groups()

# # تخصيص عناوين لوحة الإدارة
# admin.site.site_header = "نظام إدارة مدرسة المنار"
# admin.site.site_title = "إدارة المدرسة"
# admin.site.index_title = "لوحة التحكم الرئيسية"
