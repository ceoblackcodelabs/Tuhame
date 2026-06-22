# apps/contracts/forms.py
from django import forms
from .models import Contract


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = [
            'contract_type', 'property', 'unit', 'client', 'owner',
            'monthly_rent', 'security_deposit', 'total_amount',
            'start_date', 'end_date', 'payment_due_day', 'notice_period_days',
            'late_fee_amount', 'late_fee_percentage', 'special_terms',
            'utilities_included', 'parking_included', 'pets_allowed'
        ]
        widgets = {
            'contract_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'property': forms.Select(attrs={
                'class': 'form-select'
            }),
            'unit': forms.Select(attrs={
                'class': 'form-select'
            }),
            'client': forms.Select(attrs={
                'class': 'form-select'
            }),
            'owner': forms.Select(attrs={
                'class': 'form-select'
            }),
            'monthly_rent': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Monthly rent amount'
            }),
            'security_deposit': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Security deposit amount'
            }),
            'total_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Total contract amount'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'payment_due_day': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 31,
                'placeholder': 'Day of month (1-31)'
            }),
            'notice_period_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'Notice period in days'
            }),
            'late_fee_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Fixed late fee amount'
            }),
            'late_fee_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Late fee percentage'
            }),
            'special_terms': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Any special terms or conditions'
            }),
            'utilities_included': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'parking_included': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'pets_allowed': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError("End date must be after start date")

        return cleaned_data