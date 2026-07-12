# apps/properties/forms.py
from django import forms
from .models import Property, Unit, Booking
from django.contrib.auth import get_user_model
from django.utils import timezone
from home.models import ViewingSchedule

User = get_user_model()

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            'title', 'property_type', 'status', 'address', 'city', 'state',
            'zip_code', 'country', 'latitude', 'longitude', 'description',
            'area_sqft', 'bedrooms', 'bathrooms', 'floor_number', 'total_floors',
            'year_built', 'price', 'security_deposit', 'maintenance_fee',
            'agent', 'amenities', 'available_from', 'minimum_lease_days',
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
                'placeholder': 'Full street address',
                'id': 'address-input'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'latitude-input',
                'step': '0.000001',
                'readonly': True,
                'placeholder': 'Auto-filled from map'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'longitude-input',
                'step': '0.000001',
                'readonly': True,
                'placeholder': 'Auto-filled from map'
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
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Add required class to required fields
        for field_name, field in self.fields.items():
            if field.required:
                field.widget.attrs['required'] = 'required'

        # Set initial user
        if self.user and not self.instance.pk:
            self.fields['agent'].queryset = User.objects.filter(
                is_active=True,
                groups__name='agents'
            )


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


class ViewingScheduleForm(forms.ModelForm):
    """Form for creating and updating viewing schedules"""

    class Meta:
        model = ViewingSchedule
        fields = [
            'property',
            'full_name',
            'email',
            'phone_number',
            'preferred_date',
            'preferred_time',
            'special_requests',
            'status',
            'notes',
            'scheduled_datetime',
        ]
        widgets = {
            'property': forms.Select(attrs={
                'class': 'form-select'
            }),
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+254 712 345 678'
            }),
            'preferred_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'preferred_time': forms.Select(attrs={
                'class': 'form-select'
            }),
            'special_requests': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Any special requests or questions?'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Internal notes for the property owner/agent...'
            }),
            'scheduled_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
        }
        labels = {
            'property': 'Property',
            'full_name': 'Full Name',
            'email': 'Email Address',
            'phone_number': 'Phone Number',
            'preferred_date': 'Preferred Date',
            'preferred_time': 'Preferred Time',
            'special_requests': 'Special Requests',
            'status': 'Status',
            'notes': 'Internal Notes',
            'scheduled_datetime': 'Scheduled Date & Time',
        }
        help_texts = {
            'notes': 'These notes are only visible to property owners and agents.',
            'scheduled_datetime': 'Set the actual date and time for the viewing.',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filter properties for non-staff users
        if self.user and not self.user.is_staff:
            self.fields['property'].queryset = Property.objects.filter(
                owner=self.user,
                is_active=True
            )

        # Set initial values for new viewing
        if not self.instance.pk:
            if self.user:
                self.fields['full_name'].initial = self.user.get_full_name() or self.user.username
                self.fields['email'].initial = self.user.email

            # Set default date to tomorrow
            tomorrow = timezone.now().date() + timezone.timedelta(days=1)
            self.fields['preferred_date'].initial = tomorrow

            # Only show pending status for new entries
            self.fields['status'].initial = 'pending'

        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'

    def clean_preferred_date(self):
        """Validate that preferred date is not in the past"""
        preferred_date = self.cleaned_data.get('preferred_date')
        if preferred_date and not self.instance.pk:
            if preferred_date < timezone.now().date():
                raise forms.ValidationError("Preferred date cannot be in the past.")
        return preferred_date

    def clean_scheduled_datetime(self):
        """Validate scheduled datetime"""
        scheduled_datetime = self.cleaned_data.get('scheduled_datetime')
        status = self.cleaned_data.get('status')

        if scheduled_datetime and status == 'confirmed':
            if scheduled_datetime < timezone.now():
                raise forms.ValidationError("Scheduled datetime cannot be in the past for confirmed viewings.")

        return scheduled_datetime

    def clean(self):
        """Clean and validate all fields"""
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        scheduled_datetime = cleaned_data.get('scheduled_datetime')

        # If status is confirmed, scheduled_datetime is required
        if status == 'confirmed' and not scheduled_datetime:
            self.add_error('scheduled_datetime', 'Scheduled date and time is required for confirmed viewings.')

        # If status is completed, scheduled_datetime should be in the past
        if status == 'completed' and scheduled_datetime:
            if scheduled_datetime > timezone.now():
                self.add_error('scheduled_datetime', 'Completed viewings must have a past scheduled datetime.')

        return cleaned_data

    def save(self, commit=True):
        """Save the form and handle status changes"""
        instance = super().save(commit=False)

        # If status is being changed to confirmed, set confirmed_at
        if instance.status == 'confirmed' and not instance.confirmed_at:
            instance.confirmed_at = timezone.now()

        # If status is being changed to completed, set completed_at
        if instance.status == 'completed' and not instance.completed_at:
            instance.completed_at = timezone.now()

        # If status is being changed to cancelled, set cancelled_at
        if instance.status == 'cancelled' and not instance.cancelled_at:
            instance.cancelled_at = timezone.now()

        if commit:
            instance.save()

        return instance


class ViewingFilterForm(forms.Form):
    """Form for filtering viewing schedules"""

    STATUS_CHOICES = [
        ('', 'All Status'),
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]

    TIME_CHOICES = [
        ('', 'All Times'),
        ('morning', 'Morning (8am-12pm)'),
        ('afternoon', 'Afternoon (12pm-5pm)'),
        ('evening', 'Evening (5pm-7pm)'),
    ]

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, email, property...'
        })
    )
    status = forms.ChoiceField(
        required=False,
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    time = forms.ChoiceField(
        required=False,
        choices=TIME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

    def clean(self):
        """Validate date range"""
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')

        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("Date from cannot be later than date to.")

        return cleaned_data