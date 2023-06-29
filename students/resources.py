from import_export import resources
from .models import Student
from .models import *
from import_export.admin import ImportExportModelAdmin
from import_export.resources import ModelResource
from import_export import resources
from import_export.admin import ImportExportMixin


class StudentResource(resources.ModelResource):
    class Meta:
        model = Student
        fields = ('name', 'gender', 'classroom', 'national_number', 'total_payments', 'total_owed', 'phone_number')
