# apps/profiles/forms.py
from django import forms
from django.contrib.auth import get_user_model
from .models import Profile
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

User = get_user_model()


class ProfileForm(forms.ModelForm):
    """Form for updating user profile"""

    class Meta:
        model = Profile
        fields = [
            'role',
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

class UserRegistrationForm(forms.ModelForm):
    """Form for user registration"""

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a strong password',
            'id': 'reg-password',
            'required': True,
            'style': 'padding-right:3rem;'
        }),
        validators=[validate_password],
        help_text='Password must be at least 8 characters long and contain letters and numbers.'
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Repeat your password',
            'id': 'reg-confirm-password',
            'required': True,
            'style': 'padding-right:3rem;'
        }),
        label='Confirm Password'
    )

    phone_number = forms.CharField(
        max_length=20,
        required=False,  # Make optional since Profile has blank=True
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+254 700 000 000',
            'id': 'id_phone'
        }),
        validators=[
            RegexValidator(
                regex=r'^\+?[0-9\s\-()]{8,20}$',
                message='Enter a valid phone number (e.g., +254 712 345 678)'
            )
        ]
    )

    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Nairobi',
            'id': 'id_city'
        })
    )

    looking_for = forms.ChoiceField(
        choices=[
            ('', 'Select property type…'),
            ('apartment', 'Apartment'),
            ('villa', 'Villa / House'),
            ('studio', 'Studio / Bedsitter'),
            ('bnb', 'BnB / Short Stay'),
            ('commercial', 'Commercial Space'),
            ('land', 'Land / Plot'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-input',
            'style': 'padding-left:1rem;'
        })
    )

    agree_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'style': 'accent-color:var(--primary);width:15px;height:15px;'
        }),
        label='I agree to the Terms of Service and Privacy Policy',
        error_messages={
            'required': 'You must agree to the Terms of Service and Privacy Policy.'
        }
    )

    receive_alerts = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'style': 'accent-color:var(--primary);width:15px;height:15px;'
        }),
        label='Send me new listing alerts and housing tips (optional)'
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'James',
                'required': True
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Kariuki',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'you@email.com',
                'required': True
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'jameskariuki',
                'id': 'id_username',
                'required': True
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make username optional since we'll generate it if not provided
        self.fields['username'].required = False
        self.fields['username'].help_text = 'Optional. If left blank, will be auto-generated.'

    def clean_username(self):
        """Validate username or generate one if empty"""
        username = self.cleaned_data.get('username', '').strip()

        if not username:
            # Generate username from email
            email = self.cleaned_data.get('email', '')
            if email:
                username = email.split('@')[0]
                # Make sure it's unique
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
            else:
                raise forms.ValidationError('Username or email is required to generate a username.')

        elif User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')

        return username

    def clean_email(self):
        """Validate email is unique"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean(self):
        """Validate password match"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError('Passwords do not match.')

        return cleaned_data

    def save(self, commit=True):
        """Create user - profile will be created by signals"""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])

        # Ensure username is set
        if not user.username:
            user.username = self.cleaned_data.get('username') or user.email.split('@')[0]

        if commit:
            user.save()
            # Profile is automatically created by the signal
            # We just need to update the profile with the additional data
            try:
                profile = user.profile
                profile.full_name = f"{user.first_name} {user.last_name}".strip()
                profile.phone_number = self.cleaned_data.get('phone_number', '')
                profile.city = self.cleaned_data.get('city', '')
                profile.save()
            except Profile.DoesNotExist:
                # If signal didn't create it (shouldn't happen), create it now
                Profile.objects.create(
                    user=user,
                    full_name=f"{user.first_name} {user.last_name}".strip(),
                    phone_number=self.cleaned_data.get('phone_number', ''),
                    city=self.cleaned_data.get('city', '')
                )

        return user

