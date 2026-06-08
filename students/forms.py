from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

from .models import (
    Student,
    validate_egyptian_national_id,
)

from school_settings.models import (
    AcademicYear,
    EducationLevel,
    GradeLevel,
)


# ============================================================
# أدوات مساعدة للنماذج
# ============================================================

BASE_INPUT_CLASS = 'form-control'
BASE_SELECT_CLASS = 'form-control'
BASE_CHECKBOX_CLASS = 'form-check-input'


def clean_optional_digits(value, field_label):
    """التحقق من رقم اختياري يحتوي على أرقام فقط عند إدخاله"""
    value = (value or '').strip()

    if value and not value.isdigit():
        raise forms.ValidationError(f'{field_label} يجب أن يحتوي على أرقام فقط')

    return value


def validate_unique_optional_field(model, field_name, value, instance=None, message='هذه القيمة مستخدمة من قبل'):
    """التحقق من عدم تكرار حقل اختياري"""
    value = (value or '').strip()

    if not value:
        return value

    qs = model.objects.filter(**{field_name: value})

    if instance and instance.pk:
        qs = qs.exclude(pk=instance.pk)

    if qs.exists():
        raise forms.ValidationError(message)

    return value


class StudentBaseFormMixin:
    """Mixin مشترك بين نموذج الإضافة والتعديل"""

    def setup_grade_queryset(self):
        self.fields['grade_level'].queryset = GradeLevel.objects.filter(
            is_active=True
        ).select_related(
            'education_level'
        ).order_by(
            'education_level__order',
            'order',
            'name'
        )

    def setup_academic_year_queryset(self):
        if 'academic_year' in self.fields:
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(
                is_active=True
            ).order_by(
                '-start_date',
                'name'
            )

    def setup_optional_fields(self):
        """جعل كل الحقول اختيارية ما عدا الاسم"""
        for field_name, field in self.fields.items():
            field.required = field_name == 'name'

    def clean_national_number(self):
        national_number = (self.cleaned_data.get('national_number') or '').strip()

        if national_number:
            is_valid, message = validate_egyptian_national_id(national_number)

            if not is_valid:
                raise forms.ValidationError(message)

            return validate_unique_optional_field(
                Student,
                'national_number',
                national_number,
                instance=self.instance,
                message='يوجد طالب آخر بنفس الرقم القومي'
            )

        return ''

    def clean_passport_number(self):
        passport_number = (self.cleaned_data.get('passport_number') or '').strip()

        if passport_number:
            return validate_unique_optional_field(
                Student,
                'passport_number',
                passport_number,
                instance=self.instance,
                message='يوجد طالب آخر بنفس رقم جواز السفر'
            )

        return ''

    def clean_phone_number(self):
        return clean_optional_digits(
            self.cleaned_data.get('phone_number'),
            'رقم الهاتف'
        )

    def clean_parent_phone(self):
        return clean_optional_digits(
            self.cleaned_data.get('parent_phone'),
            'هاتف ولي الأمر'
        )

    def clean_educational_guardian_phone(self):
        return clean_optional_digits(
            self.cleaned_data.get('educational_guardian_phone'),
            'هاتف صاحب الولاية التعليمية'
        )

    def clean(self):
        cleaned_data = super().clean()

        is_integration_student = cleaned_data.get('is_integration_student')
        disability_type = cleaned_data.get('disability_type')

        if not is_integration_student and disability_type:
            cleaned_data['is_integration_student'] = True

        is_staff_child = cleaned_data.get('is_staff_child')
        staff_parent_name = cleaned_data.get('staff_parent_name')
        staff_parent_job = cleaned_data.get('staff_parent_job')

        if not is_staff_child and (staff_parent_name or staff_parent_job):
            cleaned_data['is_staff_child'] = True

        return cleaned_data


# ============================================================
# نموذج إضافة طالب
# ============================================================

class StudentForm(StudentBaseFormMixin, forms.ModelForm):
    grade_level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.none(),
        label='الصف الدراسي',
        required=False,
        empty_label='اختر الصف الدراسي',
        widget=forms.Select(attrs={
            'class': BASE_SELECT_CLASS,
            'id': 'id_grade_level',
        })
    )

    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.none(),
        label='العام الدراسي',
        required=False,
        empty_label='اختر العام الدراسي',
        widget=forms.Select(attrs={
            'class': BASE_SELECT_CLASS,
            'id': 'id_academic_year',
        })
    )

    class Meta:
        model = Student
        fields = [
            'name',
            'student_type',
            'national_number',
            'passport_number',
            'nationality',
            'religion',
            'phone_number',
            'address',
            'academic_year',
            'grade_level',
            'enrollment_status',
            'transferred_from_school',
            'transferred_to_school',
            'is_integration_student',
            'disability_type',
            'exempt_from_arabic',
            'exempt_from_english',
            'exempt_from_french',
            'other_subject_exemptions',
            'parent_name',
            'parent_phone',
            'parent_email',
            'father_job',
            'educational_guardian',
            'educational_guardian_name',
            'educational_guardian_phone',
            'is_staff_child',
            'staff_parent_name',
            'staff_parent_job',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'اسم الطالب',
                'id': 'id_name',
            }),
            'student_type': forms.Select(attrs={
                'class': BASE_SELECT_CLASS,
                'id': 'id_student_type',
            }),
            'national_number': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'أدخل الرقم القومي 14 رقم للطلاب المصريين',
                'maxlength': '14',
                'id': 'id_national_number',
            }),
            'passport_number': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'رقم جواز السفر للوافدين',
                'id': 'id_passport_number',
            }),
            'nationality': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'الجنسية',
                'id': 'id_nationality',
            }),
            'religion': forms.Select(attrs={
                'class': BASE_SELECT_CLASS,
                'id': 'id_religion',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'رقم هاتف الطالب',
                'id': 'id_phone_number',
            }),
            'address': forms.Textarea(attrs={
                'class': BASE_INPUT_CLASS,
                'rows': 3,
                'placeholder': 'العنوان',
                'id': 'id_address',
            }),
            'enrollment_status': forms.Select(attrs={
                'class': BASE_SELECT_CLASS,
                'id': 'id_enrollment_status',
            }),
            'transferred_from_school': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'اسم المدرسة القادم منها',
                'id': 'id_transferred_from_school',
            }),
            'transferred_to_school': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'اسم المدرسة المحول إليها',
                'id': 'id_transferred_to_school',
            }),
            'is_integration_student': forms.CheckboxInput(attrs={
                'class': BASE_CHECKBOX_CLASS,
                'id': 'id_is_integration_student',
            }),
            'disability_type': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'نوع الإعاقة',
                'id': 'id_disability_type',
            }),
            'exempt_from_arabic': forms.CheckboxInput(attrs={
                'class': BASE_CHECKBOX_CLASS,
                'id': 'id_exempt_from_arabic',
            }),
            'exempt_from_english': forms.CheckboxInput(attrs={
                'class': BASE_CHECKBOX_CLASS,
                'id': 'id_exempt_from_english',
            }),
            'exempt_from_french': forms.CheckboxInput(attrs={
                'class': BASE_CHECKBOX_CLASS,
                'id': 'id_exempt_from_french',
            }),
            'other_subject_exemptions': forms.Textarea(attrs={
                'class': BASE_INPUT_CLASS,
                'rows': 2,
                'placeholder': 'إعفاءات أخرى من مواد',
                'id': 'id_other_subject_exemptions',
            }),
            'parent_name': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'اسم ولي الأمر',
                'id': 'id_parent_name',
            }),
            'parent_phone': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'هاتف ولي الأمر',
                'id': 'id_parent_phone',
            }),
            'parent_email': forms.EmailInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'بريد ولي الأمر',
                'id': 'id_parent_email',
            }),
            'father_job': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'وظيفة الأب',
                'id': 'id_father_job',
            }),
            'educational_guardian': forms.Select(attrs={
                'class': BASE_SELECT_CLASS,
                'id': 'id_educational_guardian',
            }),
            'educational_guardian_name': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'اسم صاحب الولاية التعليمية',
                'id': 'id_educational_guardian_name',
            }),
            'educational_guardian_phone': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'هاتف صاحب الولاية التعليمية',
                'id': 'id_educational_guardian_phone',
            }),
            'is_staff_child': forms.CheckboxInput(attrs={
                'class': BASE_CHECKBOX_CLASS,
                'id': 'id_is_staff_child',
            }),
            'staff_parent_name': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'اسم الموظف من العاملين',
                'id': 'id_staff_parent_name',
            }),
            'staff_parent_job': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'وظيفة الموظف داخل المدرسة',
                'id': 'id_staff_parent_job',
            }),
        }

        labels = {
            'name': 'اسم الطالب',
            'student_type': 'نوع الطالب',
            'national_number': 'الرقم القومي',
            'passport_number': 'رقم جواز السفر',
            'nationality': 'الجنسية',
            'religion': 'الديانة',
            'phone_number': 'رقم الهاتف',
            'address': 'العنوان',
            'academic_year': 'العام الدراسي',
            'grade_level': 'الصف الدراسي',
            'enrollment_status': 'حالة القيد',
            'transferred_from_school': 'محول من مدرسة',
            'transferred_to_school': 'محول إلى مدرسة',
            'is_integration_student': 'طالب دمج / من ذوي الهمم',
            'disability_type': 'نوع الإعاقة',
            'exempt_from_arabic': 'إعفاء من اللغة العربية',
            'exempt_from_english': 'إعفاء من اللغة الإنجليزية',
            'exempt_from_french': 'إعفاء من اللغة الفرنسية',
            'other_subject_exemptions': 'إعفاءات أخرى',
            'parent_name': 'اسم ولي الأمر',
            'parent_phone': 'هاتف ولي الأمر',
            'parent_email': 'بريد ولي الأمر',
            'father_job': 'وظيفة الأب',
            'educational_guardian': 'صاحب الولاية التعليمية',
            'educational_guardian_name': 'اسم صاحب الولاية التعليمية',
            'educational_guardian_phone': 'هاتف صاحب الولاية التعليمية',
            'is_staff_child': 'من أبناء العاملين',
            'staff_parent_name': 'اسم الموظف',
            'staff_parent_job': 'وظيفة الموظف داخل المدرسة',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setup_grade_queryset()
        self.setup_academic_year_queryset()
        self.setup_optional_fields()


# ============================================================
# نموذج تعديل طالب
# ============================================================

class Student_edit_Form(StudentBaseFormMixin, forms.ModelForm):
    grade_level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.none(),
        label='الصف الدراسي',
        required=False,
        empty_label='اختر الصف الدراسي',
        widget=forms.Select(attrs={
            'class': BASE_SELECT_CLASS,
            'id': 'id_grade_level',
        })
    )

    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.none(),
        label='العام الدراسي',
        required=False,
        empty_label='اختر العام الدراسي',
        widget=forms.Select(attrs={
            'class': BASE_SELECT_CLASS,
            'id': 'id_academic_year',
        })
    )

    age = forms.IntegerField(
        label='العمر',
        required=False,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(30),
        ],
        widget=forms.NumberInput(attrs={
            'class': BASE_INPUT_CLASS,
            'readonly': 'readonly',
            'id': 'id_age',
        })
    )

    class Meta:
        model = Student
        fields = [
            'name',
            'student_type',
            'national_number',
            'passport_number',
            'nationality',
            'religion',
            'gender',
            'age',
            'date_of_birth',
            'phone_number',
            'address',
            'academic_year',
            'grade_level',
            'enrollment_status',
            'transferred_from_school',
            'transferred_to_school',
            'is_integration_student',
            'disability_type',
            'exempt_from_arabic',
            'exempt_from_english',
            'exempt_from_french',
            'other_subject_exemptions',
            'parent_name',
            'parent_phone',
            'parent_email',
            'father_job',
            'educational_guardian',
            'educational_guardian_name',
            'educational_guardian_phone',
            'is_staff_child',
            'staff_parent_name',
            'staff_parent_job',
            'is_active',
        ]

        widgets = {
            'name': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'id': 'id_name', 'placeholder': 'اسم الطالب'}),
            'student_type': forms.Select(attrs={'class': BASE_SELECT_CLASS, 'id': 'id_student_type'}),
            'national_number': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'maxlength': '14', 'id': 'id_national_number', 'placeholder': 'الرقم القومي اختياري'}),
            'passport_number': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'id': 'id_passport_number', 'placeholder': 'رقم جواز السفر'}),
            'nationality': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'id': 'id_nationality', 'placeholder': 'الجنسية'}),
            'religion': forms.Select(attrs={'class': BASE_SELECT_CLASS, 'id': 'id_religion'}),
            'gender': forms.Select(attrs={'class': BASE_SELECT_CLASS, 'id': 'id_gender'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': BASE_INPUT_CLASS, 'id': 'id_date_of_birth'}),
            'phone_number': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'maxlength': '20', 'id': 'id_phone_number'}),
            'address': forms.Textarea(attrs={'class': BASE_INPUT_CLASS, 'rows': 3, 'id': 'id_address'}),
            'enrollment_status': forms.Select(attrs={'class': BASE_SELECT_CLASS, 'id': 'id_enrollment_status'}),
            'transferred_from_school': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'id': 'id_transferred_from_school'}),
            'transferred_to_school': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'id': 'id_transferred_to_school'}),
            'is_integration_student': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX_CLASS, 'id': 'id_is_integration_student'}),
            'disability_type': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'id': 'id_disability_type'}),
            'exempt_from_arabic': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX_CLASS, 'id': 'id_exempt_from_arabic'}),
            'exempt_from_english': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX_CLASS, 'id': 'id_exempt_from_english'}),
            'exempt_from_french': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX_CLASS, 'id': 'id_exempt_from_french'}),
            'other_subject_exemptions': forms.Textarea(attrs={'class': BASE_INPUT_CLASS, 'rows': 2, 'id': 'id_other_subject_exemptions'}),
            'parent_name': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'id': 'id_parent_name'}),
            'parent_phone': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'id': 'id_parent_phone'}),
            'parent_email': forms.EmailInput(attrs={'class': BASE_INPUT_CLASS, 'id': 'id_parent_email'}),
            'father_job': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'id': 'id_father_job'}),
            'educational_guardian': forms.Select(attrs={'class': BASE_SELECT_CLASS, 'id': 'id_educational_guardian'}),
            'educational_guardian_name': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'id': 'id_educational_guardian_name'}),
            'educational_guardian_phone': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'id': 'id_educational_guardian_phone'}),
            'is_staff_child': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX_CLASS, 'id': 'id_is_staff_child'}),
            'staff_parent_name': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'id': 'id_staff_parent_name'}),
            'staff_parent_job': forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'id': 'id_staff_parent_job'}),
            'is_active': forms.CheckboxInput(attrs={'class': BASE_CHECKBOX_CLASS, 'id': 'id_is_active'}),
        }

        labels = StudentForm.Meta.labels.copy()
        labels.update({
            'gender': 'النوع',
            'age': 'العمر',
            'date_of_birth': 'تاريخ الميلاد',
            'is_active': 'نشط',
        })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setup_grade_queryset()
        self.setup_academic_year_queryset()
        self.setup_optional_fields()

        self.fields['gender'].required = False
        self.fields['age'].required = False
        self.fields['date_of_birth'].required = False
        self.fields['is_active'].required = False


# ============================================================
# نموذج البحث عن الطلاب
# ============================================================

class StudentSearchForm(forms.Form):
    search_query = forms.CharField(
        label='البحث',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'البحث بالاسم أو الرقم القومي أو جواز السفر أو الهاتف',
            'class': BASE_INPUT_CLASS,
        })
    )

    education_level = forms.ModelChoiceField(
        queryset=EducationLevel.objects.none(),
        label='المرحلة التعليمية',
        required=False,
        empty_label='جميع المراحل',
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    grade_level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.none(),
        label='الصف الدراسي',
        required=False,
        empty_label='جميع الصفوف',
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    gender = forms.ChoiceField(
        choices=[('', 'جميع الأنواع')] + list(Student.GENDER_CHOICES),
        label='النوع',
        required=False,
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    student_type = forms.ChoiceField(
        choices=[('', 'كل أنواع الطلاب')] + list(Student.STUDENT_TYPE_CHOICES),
        label='نوع الطالب',
        required=False,
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    enrollment_status = forms.ChoiceField(
        choices=[('', 'كل حالات القيد')] + list(Student.ENROLLMENT_STATUS_CHOICES),
        label='حالة القيد',
        required=False,
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    religion = forms.ChoiceField(
        choices=[('', 'كل الديانات')] + list(Student.RELIGION_CHOICES),
        label='الديانة',
        required=False,
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    is_integration_student = forms.ChoiceField(
        label='طلاب الدمج',
        choices=[('', 'الكل'), ('yes', 'طلاب دمج / ذوي الهمم'), ('no', 'ليسوا طلاب دمج')],
        required=False,
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    is_staff_child = forms.ChoiceField(
        label='أبناء العاملين',
        choices=[('', 'الكل'), ('yes', 'من أبناء العاملين'), ('no', 'ليس من أبناء العاملين')],
        required=False,
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    date_of_birth = forms.DateField(
        label='تاريخ الميلاد',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': BASE_INPUT_CLASS})
    )

    has_balance = forms.ChoiceField(
        label='الحالة المالية',
        choices=[('', 'الكل'), ('paid', 'مسدد بالكامل'), ('owing', 'عليه مستحقات')],
        required=False,
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['education_level'].queryset = EducationLevel.objects.filter(is_active=True).order_by('order', 'name')
        self.fields['grade_level'].queryset = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order', 'name')


# ============================================================
# نموذج متقدم لتصفية الطلاب
# ============================================================

class AdvancedStudentFilterForm(forms.Form):
    name_contains = forms.CharField(
        label='يحتوي الاسم على',
        required=False,
        widget=forms.TextInput(attrs={'class': BASE_INPUT_CLASS, 'placeholder': 'جزء من اسم الطالب'})
    )

    age_min = forms.IntegerField(
        label='الحد الأدنى للعمر',
        required=False,
        widget=forms.NumberInput(attrs={'class': BASE_INPUT_CLASS, 'min': '0'})
    )

    age_max = forms.IntegerField(
        label='الحد الأقصى للعمر',
        required=False,
        widget=forms.NumberInput(attrs={'class': BASE_INPUT_CLASS, 'max': '30'})
    )

    education_level = forms.ModelChoiceField(
        label='المرحلة التعليمية',
        queryset=EducationLevel.objects.none(),
        required=False,
        empty_label='جميع المراحل',
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    grade_level = forms.ModelChoiceField(
        label='الصف الدراسي',
        queryset=GradeLevel.objects.none(),
        required=False,
        empty_label='جميع الصفوف',
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    student_type = forms.ChoiceField(
        choices=[('', 'كل أنواع الطلاب')] + list(Student.STUDENT_TYPE_CHOICES),
        label='نوع الطالب',
        required=False,
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    enrollment_status = forms.ChoiceField(
        choices=[('', 'كل حالات القيد')] + list(Student.ENROLLMENT_STATUS_CHOICES),
        label='حالة القيد',
        required=False,
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    is_integration_student = forms.ChoiceField(
        label='طلاب الدمج',
        choices=[('', 'الكل'), ('yes', 'طلاب دمج / ذوي الهمم'), ('no', 'ليسوا طلاب دمج')],
        required=False,
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    is_staff_child = forms.ChoiceField(
        label='أبناء العاملين',
        choices=[('', 'الكل'), ('yes', 'من أبناء العاملين'), ('no', 'ليس من أبناء العاملين')],
        required=False,
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    has_balance = forms.ChoiceField(
        label='الحالة المالية',
        choices=[('', 'الكل'), ('paid', 'مسدد بالكامل'), ('owing', 'عليه مستحقات')],
        required=False,
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    registration_year = forms.ModelChoiceField(
        label='سنة التسجيل',
        queryset=AcademicYear.objects.none(),
        required=False,
        empty_label='جميع السنوات',
        widget=forms.Select(attrs={'class': BASE_SELECT_CLASS})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['education_level'].queryset = EducationLevel.objects.filter(is_active=True).order_by('order', 'name')
        self.fields['grade_level'].queryset = GradeLevel.objects.filter(is_active=True).select_related('education_level').order_by('education_level__order', 'order', 'name')
        self.fields['registration_year'].queryset = AcademicYear.objects.filter(is_active=True).order_by('-start_date', 'name')


# ============================================================
# نموذج إنشاء مستخدم
# ============================================================

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=False,
        label='الاسم الأول',
        widget=forms.TextInput(attrs={'class': BASE_INPUT_CLASS})
    )

    last_name = forms.CharField(
        max_length=30,
        required=False,
        label='اسم العائلة',
        widget=forms.TextInput(attrs={'class': BASE_INPUT_CLASS})
    )

    email = forms.EmailField(
        max_length=254,
        required=True,
        label='البريد الإلكتروني',
        help_text='مطلوب. أدخل عنوان بريد إلكتروني صحيح.',
        widget=forms.EmailInput(attrs={'class': BASE_INPUT_CLASS})
    )

    class Meta:
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'password1',
            'password2',
        )

        labels = {
            'username': 'اسم المستخدم',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].widget.attrs.update({'class': BASE_INPUT_CLASS})
        self.fields['password1'].widget.attrs.update({'class': BASE_INPUT_CLASS})
        self.fields['password2'].widget.attrs.update({'class': BASE_INPUT_CLASS})

# from django import forms
# from django.contrib.auth.forms import UserCreationForm
# from django.contrib.auth.models import User
# from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator

# from .models import (
#     Student,
#     validate_egyptian_national_id,
# )

# from school_settings.models import (
#     AcademicYear,
#     EducationLevel,
#     GradeLevel,
# )


# # ============================================================
# # نموذج إضافة طالب
# # ============================================================

# class StudentForm(forms.ModelForm):
#     grade_level = forms.ModelChoiceField(
#         queryset=GradeLevel.objects.none(),
#         label='الصف الدراسي',
#         required=False,
#         empty_label='اختر الصف الدراسي',
#         widget=forms.Select(attrs={
#             'class': 'form-control',
#             'id': 'id_grade_level',
#         })
#     )

#     class Meta:
#         model = Student
#         fields = [
#             'name',
#             'national_number',
#             'phone_number',
#             'address',
#             'parent_name',
#             'parent_phone',
#             'parent_email',
#             'grade_level',
#         ]

#         widgets = {
#             'name': forms.TextInput(attrs={
#                 'class': 'form-control',
#                 'placeholder': 'اسم الطالب',
#                 'id': 'id_name',
#             }),
#             'national_number': forms.TextInput(attrs={
#                 'class': 'form-control',
#                 'placeholder': 'أدخل الرقم القومي 14 رقم',
#                 'maxlength': '14',
#                 'id': 'id_national_number',
#             }),
#             'phone_number': forms.TextInput(attrs={
#                 'class': 'form-control',
#                 'placeholder': 'رقم هاتف الطالب',
#                 'id': 'id_phone_number',
#             }),
#             'address': forms.Textarea(attrs={
#                 'class': 'form-control',
#                 'rows': 3,
#                 'placeholder': 'العنوان',
#                 'id': 'id_address',
#             }),
#             'parent_name': forms.TextInput(attrs={
#                 'class': 'form-control',
#                 'placeholder': 'اسم ولي الأمر',
#                 'id': 'id_parent_name',
#             }),
#             'parent_phone': forms.TextInput(attrs={
#                 'class': 'form-control',
#                 'placeholder': 'هاتف ولي الأمر',
#                 'id': 'id_parent_phone',
#             }),
#             'parent_email': forms.EmailInput(attrs={
#                 'class': 'form-control',
#                 'placeholder': 'بريد ولي الأمر',
#                 'id': 'id_parent_email',
#             }),
#         }

#         labels = {
#             'name': 'اسم الطالب',
#             'national_number': 'الرقم القومي',
#             'phone_number': 'رقم الهاتف',
#             'address': 'العنوان',
#             'parent_name': 'اسم ولي الأمر',
#             'parent_phone': 'هاتف ولي الأمر',
#             'parent_email': 'بريد ولي الأمر',
#             'grade_level': 'الصف الدراسي',
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         self.fields['grade_level'].queryset = GradeLevel.objects.filter(
#             is_active=True
#         ).select_related(
#             'education_level'
#         ).order_by(
#             'education_level__order',
#             'order',
#             'name'
#         )

#     def clean_national_number(self):
#         national_number = self.cleaned_data.get('national_number', '').strip()

#         if national_number:
#             is_valid, message = validate_egyptian_national_id(national_number)

#             if not is_valid:
#                 raise forms.ValidationError(message)

#             qs = Student.objects.filter(national_number=national_number)

#             if self.instance and self.instance.pk:
#                 qs = qs.exclude(pk=self.instance.pk)

#             if qs.exists():
#                 raise forms.ValidationError('يوجد طالب آخر بنفس الرقم القومي')

#         return national_number

#     def clean_phone_number(self):
#         phone_number = self.cleaned_data.get('phone_number', '').strip()

#         if phone_number and not phone_number.isdigit():
#             raise forms.ValidationError('رقم الهاتف يجب أن يحتوي على أرقام فقط')

#         return phone_number

#     def clean_parent_phone(self):
#         parent_phone = self.cleaned_data.get('parent_phone', '').strip()

#         if parent_phone and not parent_phone.isdigit():
#             raise forms.ValidationError('هاتف ولي الأمر يجب أن يحتوي على أرقام فقط')

#         return parent_phone


# # ============================================================
# # نموذج تعديل طالب
# # ============================================================

# class Student_edit_Form(forms.ModelForm):
#     national_number = forms.CharField(
#         label='الرقم القومي',
#         validators=[
#             RegexValidator(
#                 regex=r'^\d{14}$',
#                 message='يجب أن يكون الرقم القومي 14 رقم',
#             ),
#         ],
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'maxlength': '14',
#             'id': 'id_national_number',
#         })
#     )

#     phone_number = forms.CharField(
#         label='رقم الهاتف',
#         max_length=20,
#         required=False,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'maxlength': '20',
#             'id': 'id_phone_number',
#         })
#     )

#     age = forms.IntegerField(
#         label='العمر',
#         required=False,
#         validators=[
#             MinValueValidator(3),
#             MaxValueValidator(25),
#         ],
#         widget=forms.NumberInput(attrs={
#             'class': 'form-control',
#             'readonly': 'readonly',
#             'id': 'id_age',
#         })
#     )

#     grade_level = forms.ModelChoiceField(
#         queryset=GradeLevel.objects.none(),
#         label='الصف الدراسي',
#         required=False,
#         empty_label='اختر الصف الدراسي',
#         widget=forms.Select(attrs={
#             'class': 'form-control',
#             'id': 'id_grade_level',
#         })
#     )

#     class Meta:
#         model = Student
#         fields = [
#             'name',
#             'national_number',
#             'phone_number',
#             'address',
#             'parent_name',
#             'parent_phone',
#             'parent_email',
#             'gender',
#             'age',
#             'date_of_birth',
#             'grade_level',
#             'is_active',
#         ]

#         widgets = {
#             'name': forms.TextInput(attrs={
#                 'class': 'form-control',
#                 'id': 'id_name',
#             }),
#             'address': forms.Textarea(attrs={
#                 'class': 'form-control',
#                 'rows': 3,
#                 'id': 'id_address',
#             }),
#             'parent_name': forms.TextInput(attrs={
#                 'class': 'form-control',
#                 'id': 'id_parent_name',
#             }),
#             'parent_phone': forms.TextInput(attrs={
#                 'class': 'form-control',
#                 'id': 'id_parent_phone',
#             }),
#             'parent_email': forms.EmailInput(attrs={
#                 'class': 'form-control',
#                 'id': 'id_parent_email',
#             }),
#             'gender': forms.Select(attrs={
#                 'class': 'form-control',
#                 'id': 'id_gender',
#             }),
#             'date_of_birth': forms.DateInput(attrs={
#                 'type': 'date',
#                 'class': 'form-control',
#                 'id': 'id_date_of_birth',
#             }),
#             'is_active': forms.CheckboxInput(attrs={
#                 'class': 'form-check-input',
#                 'id': 'id_is_active',
#             }),
#         }

#         labels = {
#             'name': 'اسم الطالب',
#             'national_number': 'الرقم القومي',
#             'phone_number': 'رقم الهاتف',
#             'address': 'العنوان',
#             'parent_name': 'اسم ولي الأمر',
#             'parent_phone': 'هاتف ولي الأمر',
#             'parent_email': 'بريد ولي الأمر',
#             'gender': 'النوع',
#             'age': 'العمر',
#             'date_of_birth': 'تاريخ الميلاد',
#             'grade_level': 'الصف الدراسي',
#             'is_active': 'نشط',
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         self.fields['grade_level'].queryset = GradeLevel.objects.filter(
#             is_active=True
#         ).select_related(
#             'education_level'
#         ).order_by(
#             'education_level__order',
#             'order',
#             'name'
#         )

#         self.fields['gender'].required = False
#         self.fields['age'].required = False
#         self.fields['date_of_birth'].required = False
#         self.fields['is_active'].required = False

#     def clean_national_number(self):
#         national_number = self.cleaned_data.get('national_number', '').strip()

#         if national_number:
#             is_valid, message = validate_egyptian_national_id(national_number)

#             if not is_valid:
#                 raise forms.ValidationError(message)

#             qs = Student.objects.filter(national_number=national_number)

#             if self.instance and self.instance.pk:
#                 qs = qs.exclude(pk=self.instance.pk)

#             if qs.exists():
#                 raise forms.ValidationError('يوجد طالب آخر بنفس الرقم القومي')

#         return national_number

#     def clean_phone_number(self):
#         phone_number = self.cleaned_data.get('phone_number', '').strip()

#         if phone_number and not phone_number.isdigit():
#             raise forms.ValidationError('رقم الهاتف يجب أن يحتوي على أرقام فقط')

#         return phone_number

#     def clean_parent_phone(self):
#         parent_phone = self.cleaned_data.get('parent_phone', '').strip()

#         if parent_phone and not parent_phone.isdigit():
#             raise forms.ValidationError('هاتف ولي الأمر يجب أن يحتوي على أرقام فقط')

#         return parent_phone


# # ============================================================
# # نموذج البحث عن الطلاب
# # ============================================================

# class StudentSearchForm(forms.Form):
#     search_query = forms.CharField(
#         label='البحث',
#         required=False,
#         max_length=100,
#         widget=forms.TextInput(attrs={
#             'placeholder': 'البحث بالاسم أو الرقم القومي أو الهاتف',
#             'class': 'form-control',
#         })
#     )

#     education_level = forms.ModelChoiceField(
#         queryset=EducationLevel.objects.none(),
#         label='المرحلة التعليمية',
#         required=False,
#         empty_label='جميع المراحل',
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

#     grade_level = forms.ModelChoiceField(
#         queryset=GradeLevel.objects.none(),
#         label='الصف الدراسي',
#         required=False,
#         empty_label='جميع الصفوف',
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

#     gender = forms.ChoiceField(
#         choices=[('', 'جميع الأنواع')] + list(Student.GENDER_CHOICES),
#         label='النوع',
#         required=False,
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

#     date_of_birth = forms.DateField(
#         label='تاريخ الميلاد',
#         required=False,
#         widget=forms.DateInput(attrs={
#             'type': 'date',
#             'class': 'form-control',
#         })
#     )

#     has_balance = forms.ChoiceField(
#         label='الحالة المالية',
#         choices=[
#             ('', 'الكل'),
#             ('paid', 'مسدد بالكامل'),
#             ('owing', 'عليه مستحقات'),
#         ],
#         required=False,
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         self.fields['education_level'].queryset = EducationLevel.objects.filter(
#             is_active=True
#         ).order_by(
#             'order',
#             'name'
#         )

#         self.fields['grade_level'].queryset = GradeLevel.objects.filter(
#             is_active=True
#         ).select_related(
#             'education_level'
#         ).order_by(
#             'education_level__order',
#             'order',
#             'name'
#         )


# # ============================================================
# # نموذج متقدم لتصفية الطلاب
# # ============================================================

# class AdvancedStudentFilterForm(forms.Form):
#     name_contains = forms.CharField(
#         label='يحتوي الاسم على',
#         required=False,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'جزء من اسم الطالب',
#         })
#     )

#     age_min = forms.IntegerField(
#         label='الحد الأدنى للعمر',
#         required=False,
#         widget=forms.NumberInput(attrs={
#             'class': 'form-control',
#             'min': '3',
#         })
#     )

#     age_max = forms.IntegerField(
#         label='الحد الأقصى للعمر',
#         required=False,
#         widget=forms.NumberInput(attrs={
#             'class': 'form-control',
#             'max': '25',
#         })
#     )

#     education_level = forms.ModelChoiceField(
#         label='المرحلة التعليمية',
#         queryset=EducationLevel.objects.none(),
#         required=False,
#         empty_label='جميع المراحل',
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

#     grade_level = forms.ModelChoiceField(
#         label='الصف الدراسي',
#         queryset=GradeLevel.objects.none(),
#         required=False,
#         empty_label='جميع الصفوف',
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

#     has_balance = forms.ChoiceField(
#         label='الحالة المالية',
#         choices=[
#             ('', 'الكل'),
#             ('paid', 'مسدد بالكامل'),
#             ('owing', 'عليه مستحقات'),
#         ],
#         required=False,
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

#     registration_year = forms.ModelChoiceField(
#         label='سنة التسجيل',
#         queryset=AcademicYear.objects.none(),
#         required=False,
#         empty_label='جميع السنوات',
#         widget=forms.Select(attrs={'class': 'form-control'})
#     )

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         self.fields['education_level'].queryset = EducationLevel.objects.filter(
#             is_active=True
#         ).order_by(
#             'order',
#             'name'
#         )

#         self.fields['grade_level'].queryset = GradeLevel.objects.filter(
#             is_active=True
#         ).select_related(
#             'education_level'
#         ).order_by(
#             'education_level__order',
#             'order',
#             'name'
#         )

#         self.fields['registration_year'].queryset = AcademicYear.objects.filter(
#             is_active=True
#         ).order_by(
#             '-start_date',
#             'name'
#         )


# # ============================================================
# # نموذج إنشاء مستخدم
# # ============================================================

# class SignUpForm(UserCreationForm):
#     first_name = forms.CharField(
#         max_length=30,
#         required=False,
#         label='الاسم الأول',
#         widget=forms.TextInput(attrs={'class': 'form-control'})
#     )

#     last_name = forms.CharField(
#         max_length=30,
#         required=False,
#         label='اسم العائلة',
#         widget=forms.TextInput(attrs={'class': 'form-control'})
#     )

#     email = forms.EmailField(
#         max_length=254,
#         required=True,
#         label='البريد الإلكتروني',
#         help_text='مطلوب. أدخل عنوان بريد إلكتروني صحيح.',
#         widget=forms.EmailInput(attrs={'class': 'form-control'})
#     )

#     class Meta:
#         model = User
#         fields = (
#             'username',
#             'first_name',
#             'last_name',
#             'email',
#             'password1',
#             'password2',
#         )

#         labels = {
#             'username': 'اسم المستخدم',
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         self.fields['username'].widget.attrs.update({
#             'class': 'form-control',
#         })

#         self.fields['password1'].widget.attrs.update({
#             'class': 'form-control',
#         })

#         self.fields['password2'].widget.attrs.update({
#             'class': 'form-control',
#         })