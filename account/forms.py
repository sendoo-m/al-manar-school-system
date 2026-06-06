from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

User = get_user_model()


class SignupForm(UserCreationForm):
    """فورم إنشاء حساب جديد"""

    class Meta:
        model = User
        fields = (
            'username',
            'password1',
            'password2',
            'date_of_enrollment',
            'national_id',
        )


class LoginForm(AuthenticationForm):
    """فورم تسجيل الدخول"""

    username = forms.CharField(
        label='اسم المستخدم',
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'class': 'form-control',
            'placeholder': 'اسم المستخدم',
        })
    )

    password = forms.CharField(
        label='كلمة المرور',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'كلمة المرور',
            'autocomplete': 'current-password',
        })
    )


class CustomUserCreationForm(UserCreationForm):
    """فورم إنشاء مستخدم من داخل النظام"""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'date_of_enrollment',
            'national_id',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        labels = {
            'username': 'اسم المستخدم',
            'first_name': 'الاسم الأول',
            'last_name': 'اسم العائلة',
            'email': 'البريد الإلكتروني',
            'date_of_enrollment': 'تاريخ الالتحاق',
            'national_id': 'الرقم القومي',
        }

        for field_name, label in labels.items():
            if field_name in self.fields:
                self.fields[field_name].label = label
                self.fields[field_name].widget.attrs.setdefault('class', 'form-control')

        if 'date_of_enrollment' in self.fields:
            self.fields['date_of_enrollment'].widget = forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }
            )

# from django import forms
# from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
# from .models import User
# from django.contrib.auth import get_user_model

# class SignupForm(UserCreationForm):
#     class Meta:
#         model = User
#         fields = ('username', 'password1', 'password2', 'date_of_enrollment', 'national_id', 'department')

# class LoginForm(AuthenticationForm):
#     username = forms.EmailField(widget=forms.TextInput(attrs={'autofocus': True}))

# class CustomUserCreationForm(UserCreationForm):
#     class Meta(UserCreationForm.Meta):
#         model = get_user_model()

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['username'].label = 'Username'
