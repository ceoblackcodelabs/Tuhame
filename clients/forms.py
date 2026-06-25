# apps/clients/forms.py
from django import forms
from .models import Client, ClientDocument, Watchlist, Bill, BillCategory
from django.utils import timezone
from users.models import Profile
from home.models import Property
from django.contrib.auth import get_user_model
User = get_user_model()


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

# bill form
class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = [
            'property',
            'user',
            'category',
            'bill_type',
            'description',
            'amount',
            'due_date',
            'status',
            'reference_number',
            'notes',
            'receipt',
            'is_recurring',
            'recurrence_interval',
        ]
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter bill description'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Invoice or reference number'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes...'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'property': forms.Select(attrs={'class': 'form-select'}),
            'user': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'bill_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
            'is_recurring': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'recurrence_interval': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'bill_type': 'Bill Type',
            'reference_number': 'Reference/Invoice Number',
            'is_recurring': 'Recurring Bill',
            'recurrence_interval': 'Recurrence Interval',
        }
        help_texts = {
            'reference_number': 'Enter the invoice or reference number from the bill',
            'notes': 'Add any additional information about this bill',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # For staff users - show all properties and users
        if self.user and self.user.is_staff:
            # Staff can see all properties and users
            self.fields['property'].queryset = Property.objects.filter(is_active=True)
            self.fields['user'].queryset = User.objects.filter(is_active=True)
        else:
            # Regular users - only see their own properties
            # Get properties owned by this user
            user_properties = Property.objects.filter(owner=self.user, is_active=True)
            self.fields['property'].queryset = user_properties

            # Get users (clients) who have bookings or profiles linked to these properties
            # Option 1: Users who have booked these properties
            user_ids_from_bookings = self.user.owned_properties.values_list(
                'bookings__user__id', flat=True
            ).distinct()

            # Option 2: Users who have profiles with current_property in these properties
            user_ids_from_profiles = Profile.objects.filter(
                current_property__in=user_properties
            ).values_list('user__id', flat=True).distinct()

            # Combine and get unique user IDs
            user_ids = set(list(user_ids_from_bookings) + list(user_ids_from_profiles))

            # Also include the property owner (self.user)
            user_ids.add(self.user.id)

            # Filter users
            self.fields['user'].queryset = User.objects.filter(
                id__in=user_ids,
                is_active=True
            )

        # If editing an existing bill, include the current user even if they don't match filters
        if self.instance and self.instance.pk:
            if self.instance.user and self.instance.user not in self.fields['user'].queryset:
                self.fields['user'].queryset = self.fields['user'].queryset | User.objects.filter(id=self.instance.user.id)

            if self.instance.property and self.instance.property not in self.fields['property'].queryset:
                self.fields['property'].queryset = self.fields['property'].queryset | Property.objects.filter(id=self.instance.property.id)

        # Set initial user if creating bill
        if self.user and not self.instance.pk:
            self.fields['user'].initial = self.user

        # Add CSS classes
        for field in self.fields.values():
            if hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()

        # Validate recurring bill
        is_recurring = cleaned_data.get('is_recurring')
        recurrence_interval = cleaned_data.get('recurrence_interval')

        if is_recurring and not recurrence_interval:
            raise forms.ValidationError(
                'Please select a recurrence interval for recurring bills.'
            )

        # Validate due date is not in the past (unless editing)
        due_date = cleaned_data.get('due_date')
        if due_date and not self.instance.pk:
            if due_date < timezone.now().date():
                self.add_error('due_date', 'Due date cannot be in the past.')

        # Validate that the user belongs to the selected property
        property = cleaned_data.get('property')
        user = cleaned_data.get('user')

        if property and user:
            # Check if user is the owner
            if property.owner == user:
                pass  # Owner is valid
            else:
                # Check if user has a booking for this property
                has_booking = property.bookings.filter(user=user).exists()
                # Check if user has a profile with this property
                has_profile = Profile.objects.filter(user=user, current_property=property).exists()

                if not has_booking and not has_profile:
                    if not self.user.is_staff:
                        self.add_error('user', f'This user is not associated with the selected property.')

        return cleaned_data