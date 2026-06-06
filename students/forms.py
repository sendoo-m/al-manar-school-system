from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator

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
# نموذج إضافة طالب
# ============================================================

class StudentForm(forms.ModelForm):
    grade_level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.none(),
        label='الصف الدراسي',
        required=False,
        empty_label='اختر الصف الدراسي',
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_grade_level',
        })
    )

    class Meta:
        model = Student
        fields = [
            'name',
            'national_number',
            'phone_number',
            'address',
            'parent_name',
            'parent_phone',
            'parent_email',
            'grade_level',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الطالب',
                'id': 'id_name',
            }),
            'national_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'أدخل الرقم القومي 14 رقم',
                'maxlength': '14',
                'id': 'id_national_number',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم هاتف الطالب',
                'id': 'id_phone_number',
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'العنوان',
                'id': 'id_address',
            }),
            'parent_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم ولي الأمر',
                'id': 'id_parent_name',
            }),
            'parent_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'هاتف ولي الأمر',
                'id': 'id_parent_phone',
            }),
            'parent_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'بريد ولي الأمر',
                'id': 'id_parent_email',
            }),
        }

        labels = {
            'name': 'اسم الطالب',
            'national_number': 'الرقم القومي',
            'phone_number': 'رقم الهاتف',
            'address': 'العنوان',
            'parent_name': 'اسم ولي الأمر',
            'parent_phone': 'هاتف ولي الأمر',
            'parent_email': 'بريد ولي الأمر',
            'grade_level': 'الصف الدراسي',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['grade_level'].queryset = GradeLevel.objects.filter(
            is_active=True
        ).select_related(
            'education_level'
        ).order_by(
            'education_level__order',
            'order',
            'name'
        )

    def clean_national_number(self):
        national_number = self.cleaned_data.get('national_number', '').strip()

        if national_number:
            is_valid, message = validate_egyptian_national_id(national_number)

            if not is_valid:
                raise forms.ValidationError(message)

            qs = Student.objects.filter(national_number=national_number)

            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError('يوجد طالب آخر بنفس الرقم القومي')

        return national_number

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number', '').strip()

        if phone_number and not phone_number.isdigit():
            raise forms.ValidationError('رقم الهاتف يجب أن يحتوي على أرقام فقط')

        return phone_number

    def clean_parent_phone(self):
        parent_phone = self.cleaned_data.get('parent_phone', '').strip()

        if parent_phone and not parent_phone.isdigit():
            raise forms.ValidationError('هاتف ولي الأمر يجب أن يحتوي على أرقام فقط')

        return parent_phone


# ============================================================
# نموذج تعديل طالب
# ============================================================

class Student_edit_Form(forms.ModelForm):
    national_number = forms.CharField(
        label='الرقم القومي',
        validators=[
            RegexValidator(
                regex=r'^\d{14}$',
                message='يجب أن يكون الرقم القومي 14 رقم',
            ),
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'maxlength': '14',
            'id': 'id_national_number',
        })
    )

    phone_number = forms.CharField(
        label='رقم الهاتف',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'maxlength': '20',
            'id': 'id_phone_number',
        })
    )

    age = forms.IntegerField(
        label='العمر',
        required=False,
        validators=[
            MinValueValidator(3),
            MaxValueValidator(25),
        ],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'id': 'id_age',
        })
    )

    grade_level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.none(),
        label='الصف الدراسي',
        required=False,
        empty_label='اختر الصف الدراسي',
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_grade_level',
        })
    )

    class Meta:
        model = Student
        fields = [
            'name',
            'national_number',
            'phone_number',
            'address',
            'parent_name',
            'parent_phone',
            'parent_email',
            'gender',
            'age',
            'date_of_birth',
            'grade_level',
            'is_active',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_name',
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'id': 'id_address',
            }),
            'parent_name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_parent_name',
            }),
            'parent_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_parent_phone',
            }),
            'parent_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'id': 'id_parent_email',
            }),
            'gender': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_gender',
            }),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'id': 'id_date_of_birth',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_is_active',
            }),
        }

        labels = {
            'name': 'اسم الطالب',
            'national_number': 'الرقم القومي',
            'phone_number': 'رقم الهاتف',
            'address': 'العنوان',
            'parent_name': 'اسم ولي الأمر',
            'parent_phone': 'هاتف ولي الأمر',
            'parent_email': 'بريد ولي الأمر',
            'gender': 'النوع',
            'age': 'العمر',
            'date_of_birth': 'تاريخ الميلاد',
            'grade_level': 'الصف الدراسي',
            'is_active': 'نشط',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['grade_level'].queryset = GradeLevel.objects.filter(
            is_active=True
        ).select_related(
            'education_level'
        ).order_by(
            'education_level__order',
            'order',
            'name'
        )

        self.fields['gender'].required = False
        self.fields['age'].required = False
        self.fields['date_of_birth'].required = False
        self.fields['is_active'].required = False

    def clean_national_number(self):
        national_number = self.cleaned_data.get('national_number', '').strip()

        if national_number:
            is_valid, message = validate_egyptian_national_id(national_number)

            if not is_valid:
                raise forms.ValidationError(message)

            qs = Student.objects.filter(national_number=national_number)

            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError('يوجد طالب آخر بنفس الرقم القومي')

        return national_number

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number', '').strip()

        if phone_number and not phone_number.isdigit():
            raise forms.ValidationError('رقم الهاتف يجب أن يحتوي على أرقام فقط')

        return phone_number

    def clean_parent_phone(self):
        parent_phone = self.cleaned_data.get('parent_phone', '').strip()

        if parent_phone and not parent_phone.isdigit():
            raise forms.ValidationError('هاتف ولي الأمر يجب أن يحتوي على أرقام فقط')

        return parent_phone


# ============================================================
# نموذج البحث عن الطلاب
# ============================================================

class StudentSearchForm(forms.Form):
    search_query = forms.CharField(
        label='البحث',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'البحث بالاسم أو الرقم القومي أو الهاتف',
            'class': 'form-control',
        })
    )

    education_level = forms.ModelChoiceField(
        queryset=EducationLevel.objects.none(),
        label='المرحلة التعليمية',
        required=False,
        empty_label='جميع المراحل',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    grade_level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.none(),
        label='الصف الدراسي',
        required=False,
        empty_label='جميع الصفوف',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    gender = forms.ChoiceField(
        choices=[('', 'جميع الأنواع')] + list(Student.GENDER_CHOICES),
        label='النوع',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    date_of_birth = forms.DateField(
        label='تاريخ الميلاد',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        })
    )

    has_balance = forms.ChoiceField(
        label='الحالة المالية',
        choices=[
            ('', 'الكل'),
            ('paid', 'مسدد بالكامل'),
            ('owing', 'عليه مستحقات'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['education_level'].queryset = EducationLevel.objects.filter(
            is_active=True
        ).order_by(
            'order',
            'name'
        )

        self.fields['grade_level'].queryset = GradeLevel.objects.filter(
            is_active=True
        ).select_related(
            'education_level'
        ).order_by(
            'education_level__order',
            'order',
            'name'
        )


# ============================================================
# نموذج متقدم لتصفية الطلاب
# ============================================================

class AdvancedStudentFilterForm(forms.Form):
    name_contains = forms.CharField(
        label='يحتوي الاسم على',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'جزء من اسم الطالب',
        })
    )

    age_min = forms.IntegerField(
        label='الحد الأدنى للعمر',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '3',
        })
    )

    age_max = forms.IntegerField(
        label='الحد الأقصى للعمر',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'max': '25',
        })
    )

    education_level = forms.ModelChoiceField(
        label='المرحلة التعليمية',
        queryset=EducationLevel.objects.none(),
        required=False,
        empty_label='جميع المراحل',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    grade_level = forms.ModelChoiceField(
        label='الصف الدراسي',
        queryset=GradeLevel.objects.none(),
        required=False,
        empty_label='جميع الصفوف',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    has_balance = forms.ChoiceField(
        label='الحالة المالية',
        choices=[
            ('', 'الكل'),
            ('paid', 'مسدد بالكامل'),
            ('owing', 'عليه مستحقات'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    registration_year = forms.ModelChoiceField(
        label='سنة التسجيل',
        queryset=AcademicYear.objects.none(),
        required=False,
        empty_label='جميع السنوات',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['education_level'].queryset = EducationLevel.objects.filter(
            is_active=True
        ).order_by(
            'order',
            'name'
        )

        self.fields['grade_level'].queryset = GradeLevel.objects.filter(
            is_active=True
        ).select_related(
            'education_level'
        ).order_by(
            'education_level__order',
            'order',
            'name'
        )

        self.fields['registration_year'].queryset = AcademicYear.objects.filter(
            is_active=True
        ).order_by(
            '-start_date',
            'name'
        )


# ============================================================
# نموذج إنشاء مستخدم
# ============================================================

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=False,
        label='الاسم الأول',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    last_name = forms.CharField(
        max_length=30,
        required=False,
        label='اسم العائلة',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    email = forms.EmailField(
        max_length=254,
        required=True,
        label='البريد الإلكتروني',
        help_text='مطلوب. أدخل عنوان بريد إلكتروني صحيح.',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
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

        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
        })

        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
        })

        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
        })