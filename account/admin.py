from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from .forms import CustomUserCreationForm
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

# Register your models here.



class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username',)

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    list_display = ('username', 'department', 'is_staff', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser', 'date_of_enrollment')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('date_of_enrollment', 'national_id', 'department')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'date_of_enrollment', 'national_id', 'department', 'is_staff', 'is_superuser', 'is_active')}
        ),
    )
    search_fields = ('username',)
    ordering = ('username',)
admin.site.register(User, CustomUserAdmin)