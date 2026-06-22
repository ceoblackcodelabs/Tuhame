# apps/payments/forms.py
from django import forms
from django.db import models
from .models import Invoice, Payment, PaymentMethod, PaymentStatus, PaymentCategory
from decimal import Decimal


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'contract', 'client', 'property', 'amount', 'tax_amount',
            'discount_amount', 'due_date', 'category', 'description',
            'period_start', 'period_end'
        ]
        widgets = {
            'contract': forms.Select(attrs={
                'class': 'form-select'
            }),
            'client': forms.Select(attrs={
                'class': 'form-select'
            }),
            'property': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Base amount'
            }),
            'tax_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Tax amount'
            }),
            'discount_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Discount amount'
            }),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Invoice description'
            }),
            'period_start': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'period_end': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter contracts to only active ones
        from contracts.models import Contract
        self.fields['contract'].queryset = Contract.objects.filter(status='active')

        # Filter clients to only active ones
        from clients.models import Client
        self.fields['client'].queryset = Client.objects.filter(is_active=True)

        # Filter properties to only active ones
        from properties.models import Property
        self.fields['property'].queryset = Property.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount', 0)
        tax = cleaned_data.get('tax_amount', 0)
        discount = cleaned_data.get('discount_amount', 0)

        total = amount + tax - discount
        cleaned_data['total_amount'] = total

        # Validate period dates
        period_start = cleaned_data.get('period_start')
        period_end = cleaned_data.get('period_end')

        if period_start and period_end and period_start > period_end:
            raise forms.ValidationError("Period end date must be after period start date")

        return cleaned_data


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['invoice', 'amount', 'payment_method', 'payment_date', 'reference_number', 'notes', 'receipt_file']
        widgets = {
            'invoice': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Payment amount',
                'min': '0.01'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select'
            }),
            'payment_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Transaction reference number'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Payment notes'
            }),
            'receipt_file': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show all invoices but provide better error messages
        from payments.models import Invoice
        self.fields['invoice'].queryset = Invoice.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        invoice = cleaned_data.get('invoice')
        amount = cleaned_data.get('amount')

        if not invoice or not amount:
            return cleaned_data

        # Calculate total paid so far
        total_paid = invoice.payments.filter(status='paid').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        # Calculate remaining balance
        remaining = invoice.total_amount - total_paid

        # Round to 2 decimal places
        remaining = remaining.quantize(Decimal('0.01'))
        amount = amount.quantize(Decimal('0.01'))

        # Check if invoice is already fully paid
        if remaining <= Decimal('0.01'):
            raise forms.ValidationError(
                f'This invoice is already fully paid. Total: ${invoice.total_amount}, Paid: ${total_paid}'
            )

        # Check if payment amount exceeds remaining balance
        if amount > remaining:
            raise forms.ValidationError(
                f'Payment amount (${amount}) exceeds remaining balance (${remaining}). '
                f'Please enter an amount up to ${remaining}.'
            )

        return cleaned_data


class InvoiceFilterForm(forms.Form):
    """Form for filtering invoices"""
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All')] + list(PaymentStatus.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ChoiceField(
        required=False,
        choices=[('', 'All')] + list(PaymentCategory.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )


class PaymentFilterForm(forms.Form):
    """Form for filtering payments"""
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All')] + list(PaymentStatus.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    payment_method = forms.ChoiceField(
        required=False,
        choices=[('', 'All')] + list(PaymentMethod.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )