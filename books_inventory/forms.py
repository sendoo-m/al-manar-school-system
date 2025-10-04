from django import forms

class BookForm(forms.Form):
    title = forms.CharField(max_length=255, label='Title')
    author = forms.CharField(max_length=255, label='Author')
    isbn = forms.CharField(max_length=20, required=False, label='ISBN')
    published_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
