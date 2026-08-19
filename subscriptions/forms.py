# apps/subscriptions/forms.py
from django import forms
from .models import Offer, SubscriptionPlan


class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = ['title', 'description', 'amount', 'max_claims', 'duration_months', 'available_until', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Early Bird Launch Offer',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': "What's included, shown to owners on the Settings page...",
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g., 5000',
            }),
            'max_claims': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 1, 'placeholder': 'e.g., 10',
            }),
            'duration_months': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 1, 'placeholder': 'e.g., 24',
            }),
            'available_until': forms.DateTimeInput(attrs={
                'class': 'form-control', 'type': 'datetime-local',
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SubscriptionPlanForm(forms.ModelForm):
    class Meta:
        model = SubscriptionPlan
        fields = ['name', 'price', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
