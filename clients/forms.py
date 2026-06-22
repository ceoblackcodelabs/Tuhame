# apps/clients/forms.py
from django import forms
from .models import Client, ClientDocument, Watchlist


class ClientForm(forms.ModelForm):
    confirm_email = forms.EmailField(
        label='Confirm Email',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm email address'
        })
    )

    class Meta:
        model = Client
        fields = [
            'client_type', 'name', 'email', 'phone', 'alternate_phone',
            'address', 'city', 'state', 'zip_code', 'occupation',
            'employer', 'annual_income', 'preferred_property_types',
            'budget_min', 'budget_max', 'preferred_locations', 'notes',
            'id_type', 'id_number', 'id_document', 'is_active'
        ]
        widgets = {
            'client_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1234567890'
            }),
            'alternate_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Alternate contact number'
            }),
            'address': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Street address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State'
            }),
            'zip_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ZIP Code'
            }),
            'occupation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Current occupation'
            }),
            'employer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Employer name'
            }),
            'annual_income': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Annual income'
            }),
            'preferred_property_types': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., BNB, Hotel, Residential'
            }),
            'budget_min': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Minimum budget'
            }),
            'budget_max': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Maximum budget'
            }),
            'preferred_locations': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Preferred cities or neighborhoods'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Additional notes about the client'
            }),
            'id_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Passport, Driver\'s License, etc.'
            }),
            'id_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID Number'
            }),
            'id_document': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mark required fields
        required_fields = ['client_type', 'name', 'email', 'phone']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['required'] = 'required'

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        confirm_email = cleaned_data.get('confirm_email')

        if email and confirm_email and email != confirm_email:
            raise forms.ValidationError("Email addresses do not match")

        # Budget validation
        min_budget = cleaned_data.get('budget_min')
        max_budget = cleaned_data.get('budget_max')

        if min_budget and max_budget and min_budget > max_budget:
            raise forms.ValidationError("Minimum budget cannot exceed maximum budget")

        return cleaned_data


class ClientDocumentForm(forms.ModelForm):
    class Meta:
        model = ClientDocument
        fields = ['document_type', 'title', 'file', 'expires_at']
        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Document title'
            }),
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'expires_at': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }


class WatchlistForm(forms.ModelForm):
    class Meta:
        model = Watchlist
        fields = ['property', 'notes']
        widgets = {
            'property': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Add notes about why this property is in watchlist'
            }),
        }