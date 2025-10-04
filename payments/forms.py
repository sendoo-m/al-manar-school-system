from django import forms
from .models import Tuition, PaymentRecord, Discount, StudentDiscount, PaymentSettings
from students.models import Student
from django.core.validators import MinValueValidator
from decimal import Decimal


class TuitionForm(forms.ModelForm):
    installment_number = forms.IntegerField(
        label='رقم القسط',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1'
        })
    )
    
    amount_tuition = forms.DecimalField(
        label='مبلغ القسط',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01'
        })
    )
    
    amount_paid = forms.DecimalField(
        label='المبلغ المدفوع',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.00'
        })
    )
    
    due_date = forms.DateField(
        label='تاريخ الاستحقاق',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    payment_method = forms.ChoiceField(
        label='طريقة الدفع',
        choices=Tuition.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    notes = forms.CharField(
        label='ملاحظات',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'ملاحظات إضافية (اختيارية)'
        })
    )

    class Meta:
        model = Tuition
        fields = [
            'installment_number', 'amount_tuition', 'amount_paid', 
            'due_date', 'payment_method', 'notes'
        ]

    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        
        if self.student:
            # تحديد رقم القسط التالي تلقائياً
            last_installment = Tuition.objects.filter(student=self.student).order_by('-installment_number').first()
            if last_installment:
                self.fields['installment_number'].initial = last_installment.installment_number + 1
            else:
                self.fields['installment_number'].initial = 1

    def clean(self):
        cleaned_data = super().clean()
        amount_tuition = cleaned_data.get('amount_tuition')
        amount_paid = cleaned_data.get('amount_paid')
        
        if amount_tuition and amount_paid and amount_paid > amount_tuition:
            raise forms.ValidationError('المبلغ المدفوع لا يمكن أن يكون أكبر من مبلغ القسط')
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.student:
            instance.student = self.student
        if commit:
            instance.save()
        return instance


class PaymentForm(forms.ModelForm):
    """نموذج سريع لتسجيل دفع"""
    student = forms.ModelChoiceField(
        queryset=Student.objects.all(),
        label='الطالب',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    amount_paid = forms.DecimalField(
        label='المبلغ المدفوع',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01'
        })
    )
    
    payment_method = forms.ChoiceField(
        label='طريقة الدفع',
        choices=Tuition.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    notes = forms.CharField(
        label='ملاحظات',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2
        })
    )

    class Meta:
        model = PaymentRecord
        fields = ['amount_paid', 'payment_method', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ترتيب الطلاب حسب الاسم
        self.fields['student'].queryset = Student.objects.all().order_by('name')


class DiscountForm(forms.ModelForm):
    name = forms.CharField(
        label='اسم الخصم',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'مثال: خصم الأخوة، خصم المتفوقين'
        })
    )
    
    description = forms.CharField(
        label='وصف الخصم',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'وصف تفصيلي للخصم وشروطه'
        })
    )
    
    discount_value = forms.DecimalField(
        label='قيمة الخصم',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01'
        })
    )
    
    start_date = forms.DateField(
        label='تاريخ البداية',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    end_date = forms.DateField(
        label='تاريخ النهاية',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

    class Meta:
        model = Discount
        fields = [
            'name', 'description', 'discount_type', 'discount_value', 
            'start_date', 'end_date', 'is_active'
        ]
        widgets = {
            'discount_type': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'discount_type': 'نوع الخصم',
            'is_active': 'نشط',
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError('تاريخ النهاية يجب أن يكون بعد تاريخ البداية')
        
        return cleaned_data


class StudentDiscountForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=Student.objects.all(),
        label='الطالب',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    discount = forms.ModelChoiceField(
        queryset=Discount.objects.filter(is_active=True),
        label='الخصم',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = StudentDiscount
        fields = ['student', 'discount']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = Student.objects.all().order_by('name')
        self.fields['discount'].queryset = Discount.objects.filter(is_active=True).order_by('name')


class PaymentSettingsForm(forms.ModelForm):
    late_payment_penalty_rate = forms.DecimalField(
        label='معدل غرامة التأخير (%)',
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.00'
        })
    )
    
    grace_period_days = forms.IntegerField(
        label='فترة السماح (أيام)',
        validators=[MinValueValidator(0)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0'
        })
    )
    
    default_installments_count = forms.IntegerField(
        label='عدد الأقساط الافتراضي',
        validators=[MinValueValidator(1)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1'
        })
    )
    
    currency_symbol = forms.CharField(
        label='رمز العملة',
        max_length=5,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ج.م'
        })
    )

    class Meta:
        model = PaymentSettings
        fields = [
            'late_payment_penalty_rate', 'grace_period_days', 
            'default_installments_count', 'auto_generate_installments',
            'currency_symbol'
        ]
        widgets = {
            'auto_generate_installments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'auto_generate_installments': 'إنشاء أقساط تلقائي',
        }


class PaymentSearchForm(forms.Form):
    """نموذج البحث في المدفوعات"""
    student_name = forms.CharField(
        label='اسم الطالب',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'البحث بالاسم'
        })
    )
    
    payment_status = forms.ChoiceField(
        label='حالة الدفع',
        choices=[('', 'جميع الحالات')] + list(Tuition.PAYMENT_STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    payment_method = forms.ChoiceField(
        label='طريقة الدفع',
        choices=[('', 'جميع الطرق')] + list(Tuition.PAYMENT_METHOD_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        label='من تاريخ',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    date_to = forms.DateField(
        label='إلى تاريخ',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError('تاريخ البداية يجب أن يكون قبل تاريخ النهاية')
        
        return cleaned_data


class BulkPaymentForm(forms.Form):
    """نموذج الدفع الجماعي للفصل"""
    classroom = forms.ModelChoiceField(
        queryset=None,  # سيتم تحديدها في __init__
        label='الفصل الدراسي',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    amount_per_student = forms.DecimalField(
        label='المبلغ لكل طالب',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01'
        })
    )
    
    payment_method = forms.ChoiceField(
        label='طريقة الدفع',
        choices=Tuition.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    notes = forms.CharField(
        label='ملاحظات',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'ملاحظات للدفعة الجماعية'
        })
    )

    def __init__(self, *args, **kwargs):
        from students.models import Classroom
        super().__init__(*args, **kwargs)
        self.fields['classroom'].queryset = Classroom.objects.all().order_by('name')
