# core/forms.py
from django import forms
from .models import CustomUser, ContactMessage
import secrets


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'id': 'contact_text',
                'class': 'contact_text',
                'placeholder': 'Texte...',
                'required': True,
            })
        }


class SimpleRegistrationForm(forms.ModelForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email *',
            'required': True
        })
    )

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Nom d'utilisateur *",
            'required': True
        })
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est déjà utilisé.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        random_password = secrets.token_urlsafe(16)
        user.set_password(random_password)
        user.category = 'subscribed_unverified'
        user.email_verified = False

        if commit:
            user.save()
        return user