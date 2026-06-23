# apps/properties/forms.py
from django import forms
from django.utils import timezone
from .models import ViewingSchedule


class ViewingScheduleForm(forms.ModelForm):
    class Meta:
        model = ViewingSchedule
        fields = ['full_name', 'email', 'phone_number', 'preferred_date', 'preferred_time', 'special_requests']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'placeholder': 'Enter your full name',
                'class': 'form-control'
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'your.email@example.com',
                'class': 'form-control'
            }),
            'phone_number': forms.TextInput(attrs={
                'placeholder': '+254 712 000 001',
                'class': 'form-control'
            }),
            'preferred_date': forms.DateInput(attrs={
                'type': 'date',
                'min': timezone.now().date().isoformat(),
                'class': 'form-control'
            }),
            'preferred_time': forms.Select(attrs={
                'class': 'form-control'
            }),
            'special_requests': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Any special requests or questions? (Optional)',
                'class': 'form-control'
            }),
        }
        labels = {
            'full_name': 'Full Name',
            'email': 'Email Address',
            'phone_number': 'Phone Number',
            'preferred_date': 'Preferred Date',
            'preferred_time': 'Preferred Time',
            'special_requests': 'Special Requests (Optional)',
        }