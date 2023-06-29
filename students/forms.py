from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import *
from django.core.validators import RegexValidator
from django import forms
from .models import Student, EducationalStage, Classroom
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date
from django.core.validators import MinValueValidator, MaxValueValidator

# class StudentForm(forms.ModelForm):
#     class Meta:
#         model = Student
#         fields = ['name', 'national_number', 'gender', 'age', 'date_of_birth', 'classroom']
#         widgets = {
#             'date_of_birth': forms.DateInput(attrs={'type': 'date'})
#         }


# class StudentForm(forms.ModelForm):
#     national_number = forms.CharField(
#         label='National number',
#         validators=[
#             RegexValidator(
#                 regex=r'^\d{14}$',
#                 message='National number must be a 14-digit number',
#             ),
#         ],
#     )
    
#     class Meta:
#         model = Student
#         fields = '__all__' # ['name', 'national_number', 'gender', 'age', 'date_of_birth', 'classroom']
#         widgets = {
#             'date_of_birth': forms.DateInput(attrs={'type': 'date'})
#         }
class StudentForm(forms.ModelForm):
    national_number = forms.CharField(
        label='National number',
        validators=[
            RegexValidator(
                regex=r'^\d{14}$',
                message='National number must be a 14-digit number',
            ),
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'maxlength': '14',
        })
    )

    age = forms.IntegerField(
        validators=[
            MinValueValidator(3, message='Age must be between 3 and 17 years.'),
            MaxValueValidator(17, message='Age must be between 3 and 17 years.'),
        ],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'maxlength': '2',
        })
    )
    

    phone_number = forms.CharField(
        label='Phone number',
        max_length=11,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'maxlength': '11',
        })
    )

    classroom = forms.ModelMultipleChoiceField(
        queryset=Classroom.objects.all(), 
        label='Classroom', 
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control',
        })
    )


    class Meta:
        model = Student
        fields = '__all__'
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Perform any necessary modifications to the instance object here
        if commit:
            instance.save()
            self.save_m2m()
        return instance
    
class Student_edit_Form(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'national_number', 'phone_number', 'gender', 'age', 'date_of_birth', 'classroom']


class StudentSearchForm(forms.Form):
    search_query = forms.CharField(
        label='Search', 
        required=False, 
        max_length=100, 
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by Name, National Number',
            'class': 'form-control',
        })
    )
    educational_stage = forms.ModelChoiceField(
        queryset=EducationalStage.objects.all(), 
        label='Educational Stage', 
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )
    gender = forms.ChoiceField(
        choices=Student.GENDER_CHOICES, 
        label='Gender', 
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )
    date_of_birth = forms.DateField(
        label='Date of Birth', 
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
        })
    )
    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(), 
        label='Classroom', 
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )


class ExpenseForm(forms.ModelForm):
    date = forms.DateField(
        label='Date',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Expense
        fields = ['expense_type', 'amount', 'date']

class TuitionForm(forms.ModelForm):
    class Meta:
        model = Tuition
        fields = ['installment_number', 'amount_tuition', 'payment_user']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['receipt_date'].disabled = True
        self.fields['installment_number'].label = 'رقم الايصال'
        self.fields['amount_tuition'].label = 'مبلغ القسط'
        self.fields['payment_user'].label = 'مسؤل الحسابات'


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    email = forms.EmailField(max_length=254, help_text='Required. Enter a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')



class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['user', 'content']
