# apps/properties/forms.py
from django import forms
from .models import Property, Unit, Booking


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            'title', 'property_type', 'status', 'address', 'city', 'state',
            'zip_code', 'country', 'description', 'area_sqft', 'bedrooms',
            'bathrooms', 'floor_number', 'total_floors', 'year_built',
            'price', 'security_deposit', 'maintenance_fee', 'agent',
            'amenities', 'available_from', 'minimum_lease_days',
            'maximum_lease_days', 'main_image'
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 5,
                'class': 'form-control',
                'placeholder': 'Enter property description...'
            }),
            'address': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Full street address'
            }),
            'amenities': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
            'available_from': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Luxury Beachfront Villa'
            }),
            'property_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
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
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country'
            }),
            'area_sqft': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Square feet',
                'step': '0.01'
            }),
            'bedrooms': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'bathrooms': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': 0
            }),
            'floor_number': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'total_floors': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'year_built': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1800,
                'max': 2026
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Price per month/night',
                'step': '0.01'
            }),
            'security_deposit': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'maintenance_fee': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'agent': forms.Select(attrs={
                'class': 'form-select'
            }),
            'minimum_lease_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'maximum_lease_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'main_image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add required class to required fields
        for field_name, field in self.fields.items():
            if field.required:
                field.widget.attrs['required'] = 'required'


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ['unit_number', 'floor', 'bedrooms', 'bathrooms', 'area_sqft', 'price_modifier', 'is_available']
        widgets = {
            'unit_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 101, A-12, Room 1'
            }),
            'floor': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'bedrooms': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'bathrooms': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': 0
            }),
            'area_sqft': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Square feet'
            }),
            'price_modifier': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '+/- amount from base price'
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['property', 'unit', 'check_in_date', 'check_out_date', 'guests_count', 'special_requests']
        widgets = {
            'property': forms.Select(attrs={
                'class': 'form-select'
            }),
            'unit': forms.Select(attrs={
                'class': 'form-select'
            }),
            'check_in_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'check_out_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'guests_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Number of guests'
            }),
            'special_requests': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Any special requests or requirements...'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in_date')
        check_out = cleaned_data.get('check_out_date')

        if check_in and check_out and check_in >= check_out:
            raise forms.ValidationError("Check-out date must be after check-in date")

        return cleaned_data