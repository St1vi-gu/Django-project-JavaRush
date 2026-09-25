from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from .models import Profile

from users.signals import User


class RegisterForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'Input'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'Input'}))

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует")
        return email

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password)
        return password

    def save(self):
        email = self.cleaned_data['email']
        user= User.objects.create_user(username=email, password=self.cleaned_data['password'])
        user.email = email
        user.save(update_fields=['email'])
        return user



class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('full_name', 'phone', 'city', 'address')
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'Input'}),
            'phone': forms.TextInput(attrs={'class': 'Input'}),
            'city': forms.TextInput(attrs={'class': 'Input'}),
            'address': forms.TextInput(attrs={'class': 'Input'}),

        }