# apps/profiles/forms.py
from django import forms
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()


class ProfileForm(forms.ModelForm):
    """Form for updating user profile"""

    class Meta:
        model = Profile
        fields = [
            'full_name',
            'bio',
            'profile_picture',
            'date_of_birth',
            'phone_number',
            'alternative_phone',
            'address',
            'city',
            'state',
            'country',
            'zip_code',
            'occupation',
            'employer',
            'emergency_contact_name',
            'emergency_contact_phone',
            'emergency_contact_relationship',
            'preferred_contact_method',
            'preferred_language',
            'email_notifications',
            'sms_notifications',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date'
            }),
            'address': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Your full address'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add placeholder text to all fields
        placeholders = {
            'full_name': 'Your full name',
            'phone_number': '+254 712 000 001',
            'alternative_phone': '+254 712 000 002',
            'city': 'Nairobi',
            'state': 'Nairobi County',
            'country': 'Kenya',
            'zip_code': '00100',
            'occupation': 'Your occupation',
            'employer': 'Your employer',
            'emergency_contact_name': 'Emergency contact name',
            'emergency_contact_phone': '+254 712 000 003',
            'emergency_contact_relationship': 'e.g. Spouse, Parent, Sibling',
        }

        for field_name, placeholder in placeholders.items():
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'placeholder': placeholder,
                    'class': 'form-control'
                })

        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            if field_name not in ['bio', 'address', 'profile_picture']:
                field.widget.attrs.setdefault('class', 'form-control')
            elif field_name in ['bio', 'address']:
                field.widget.attrs.setdefault('class', 'form-control')

    def clean_phone_number(self):
        """Validate phone number format"""
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Basic validation - you can add more specific validation
            if not phone.startswith('+') and not phone[0].isdigit():
                raise forms.ValidationError("Please enter a valid phone number.")
        return phone