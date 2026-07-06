# apps/properties/forms.py
from django import forms
from django.utils import timezone
from .models import ViewingSchedule
from properties.models import PropertyReview


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


class ReviewForm(forms.ModelForm):
    """Form for submitting property reviews"""

    class Meta:
        model = PropertyReview
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Tell others what you loved (or didn\'t love) about this property…',
                'style': 'width:100%;padding:0.75rem 1rem;border:1.5px solid var(--gray-200);border-radius:var(--radius);font-size:0.9rem;color:var(--gray-800);background:var(--gray-50);outline:none;resize:vertical;font-family:inherit;transition:border-color 0.2s;'
            }),
            'rating': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].required = True
        self.fields['comment'].required = False