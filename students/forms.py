from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import *
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from datetime import date

from django import forms
from .models import Student, extract_birth_date_from_national_id, calculate_age_from_birth_date, extract_gender_from_national_id, validate_egyptian_national_id

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'national_number', 'phone_number', 'classroom', 'address', 'parent_name', 'parent_phone', 'parent_email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الطالب'}),
            'national_number': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'أدخل الرقم القومي (14 رقم)',
                'maxlength': '14',
                'id': 'national_number'
            }),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الهاتف'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'العنوان'}),
            'parent_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم ولي الأمر'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'هاتف ولي الأمر'}),
            'parent_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'بريد ولي الأمر'}),
            'classroom': forms.SelectMultiple(attrs={'class': 'form-control'})
        }

    def clean_national_number(self):
        national_number = self.cleaned_data.get('national_number')
        if national_number:
            is_valid, message = validate_egyptian_national_id(national_number)
            if not is_valid:
                raise forms.ValidationError(message)
        return national_number


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
        })
    )

    phone_number = forms.CharField(
        label='رقم الهاتف',
        max_length=11,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'maxlength': '11',
        })
    )

    age = forms.IntegerField(
        label='العمر',
        validators=[
            MinValueValidator(3),
            MaxValueValidator(17),
        ],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
        })
    )

    classroom = forms.ModelMultipleChoiceField(
        queryset=Classroom.objects.all(), 
        label='الفصل الدراسي', 
        required=True,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
            'size': '5'
        })
    )

    class Meta:
        model = Student
        fields = ['name', 'national_number', 'phone_number', 'gender', 'age', 'date_of_birth', 'classroom']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }),
        }
        labels = {
            'name': 'اسم الطالب',
            'national_number': 'الرقم القومي',
            'phone_number': 'رقم الهاتف',
            'gender': 'النوع',
            'age': 'العمر',
            'date_of_birth': 'تاريخ الميلاد',
            'classroom': 'الفصل الدراسي',
        }


class StudentSearchForm(forms.Form):
    search_query = forms.CharField(
        label='البحث', 
        required=False, 
        max_length=100, 
        widget=forms.TextInput(attrs={
            'placeholder': 'البحث بالاسم أو الرقم القومي',
            'class': 'form-control',
        })
    )
    
    educational_stage = forms.ModelChoiceField(
        queryset=EducationalStage.objects.all(), 
        label='المرحلة التعليمية', 
        required=False,
        empty_label="جميع المراحل",
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )
    
    gender = forms.ChoiceField(
        choices=[('', 'جميع الأنواع')] + list(Student.GENDER_CHOICES), 
        label='النوع', 
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )
    
    date_of_birth = forms.DateField(
        label='تاريخ الميلاد', 
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
        })
    )
    
    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(), 
        label='الفصل الدراسي', 
        required=False,
        empty_label="جميع الفصول",
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ترتيب الفصول والمراحل
        self.fields['classroom'].queryset = Classroom.objects.all().order_by('educational_stage', 'name')
        self.fields['educational_stage'].queryset = EducationalStage.objects.all().order_by('name')


class ExpenseForm(forms.ModelForm):
    date = forms.DateField(
        label='التاريخ',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

    expense_type = forms.CharField(
        label='نوع المصروف',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'مثال: رسوم دراسية، كتب، أنشطة'
        })
    )

    amount = forms.DecimalField(
        label='المبلغ',
        max_digits=8,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0'
        })
    )

    class Meta:
        model = Expense
        fields = ['expense_type', 'amount', 'date']


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
        label='البريد الإلكتروني',
        help_text='مطلوب. أدخل عنوان بريد إلكتروني صحيح.',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        labels = {
            'username': 'اسم المستخدم',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = 'form-control'
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'


class CommentForm(forms.ModelForm):
    content = forms.CharField(
        label='المحتوى',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'اكتب تعليقك هنا...'
        })
    )

    class Meta:
        model = Comment
        fields = ['user', 'content']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'user': 'المستخدم',
            'content': 'المحتوى',
        }


# نموذج متقدم لتصفية الطلاب
class AdvancedStudentFilterForm(forms.Form):
    name_contains = forms.CharField(
        label='يحتوي الاسم على',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    age_min = forms.IntegerField(
        label='الحد الأدنى للعمر',
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '3'})
    )
    
    age_max = forms.IntegerField(
        label='الحد الأقصى للعمر',
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'max': '17'})
    )
    
    has_payments = forms.ChoiceField(
        label='حالة المدفوعات',
        choices=[
            ('', 'الكل'),
            ('yes', 'لديه مدفوعات'),
            ('no', 'لا يوجد مدفوعات'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    registration_year = forms.ModelChoiceField(
        label='سنة التسجيل',
        queryset=AcademicYear.objects.all(),
        required=False,
        empty_label="جميع السنوات",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
