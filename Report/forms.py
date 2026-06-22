# apps/report/forms.py
from django import forms
from .models import Report, ReportType
from django.utils import timezone

class GenerateReportForm(forms.Form):
    """Form for generating new reports"""
    report_type = forms.ChoiceField(
        choices=ReportType.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter report title'
        })
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter report description (optional)'
        })
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    include_charts = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    include_details = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date cannot be after end date")

        return cleaned_data


class DailyReportForm(forms.Form):
    """Form for generating daily report for a specific date"""
    report_date = forms.DateField(
        label="Select Date",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

    def clean_report_date(self):
        report_date = self.cleaned_data.get('report_date')
        if report_date and report_date > timezone.now().date():
            raise forms.ValidationError("Cannot generate report for future date")
        return report_date