from django.contrib import admin
from .models import *
from import_export.admin import ImportExportModelAdmin
from import_export.resources import ModelResource
from .models import Student
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.admin import ImportExportMixin
from django.contrib import admin
from .models import Student

admin.site.site_header = "Al-Manar School App"  # Set the admin site header
admin.site.site_title = "Al-Manar School App"  # Set the admin site title
admin.site.index_title = _('Dashboard')  # Set the admin site title


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('year',)
    search_fields = ('year',)

@admin.register(EducationalStage)
class EducationalStageAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'get_educational_stage')

    def get_name(self, obj):
        return obj.name

    get_name.short_description = 'Name'

    def get_educational_stage(self, obj):
        return obj.educational_stage.name

    get_educational_stage.short_description = 'Educational Stage'


# class StudentResource(ModelResource):
#     class Meta:
#         model = Student
#         fields = ('name', 'gender', 'date_of_birth', 'academic_year', 'classroom', 'national_number')
#         list_display = ('name', 'national_number', 'age', 'gender', 'date_of_birth')
#         list_filter = ('gender', 'classroom__educational_stage')
#         search_fields = ('name', 'national_number')


class StudentResource(resources.ModelResource):
    class Meta:
        model = Student
        fields = ('name', 'gender', 'date_of_birth', 'academic_year', 'classroom', 'national_number', 'total_payments', 'total_owed', 'phone_number')


@admin.register(Student)
class StudentAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = StudentResource
    list_display = ('name', 'national_number', 'age', 'total_payments', 'total_owed', 'phone_number')
    list_filter = ('gender', 'classroom__educational_stage' , 'total_owed')
    search_fields = ('name', 'national_number', 'classroom')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'expense_type', 'amount', 'date')
    list_filter = ('classroom__educational_stage', 'expense_type')
    search_fields = ('student__name',)

    def get_name(self, obj):
        return obj.classroom.name

    get_name.short_description = 'Classroom Name'


@admin.register(Tuition)
class TuitionAdmin(admin.ModelAdmin):
    list_display = ('student', 'installment_number', 'amount_tuition', 'receipt_date')
    list_filter = ('student__classroom__educational_stage', )
    search_fields = ('student__name',)

admin.site.register(ArchiveStudent)