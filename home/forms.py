# apps/properties/forms.py
from django import forms
from django.utils import timezone
from .models import ViewingSchedule, ContactMessage
from properties.models import PropertyReview


class ViewingScheduleForm(forms.ModelForm):
    class Meta:
        model = ViewingSchedule
        fields = ['full_name', 'email', 'phone_number', 'preferred_date', 'preferred_time', 'special_requests']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'placeholder': 'Enter your full name',
                'class': 'form-control'
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'your.email@example.com',
                'class': 'form-control'
            }),
            'phone_number': forms.TextInput(attrs={
                'placeholder': '+254 712 000 001',
                'class': 'form-control'
            }),
            'preferred_date': forms.DateInput(attrs={
                'type': 'date',
                'min': timezone.now().date().isoformat(),
                'class': 'form-control'
            }),
            'preferred_time': forms.Select(attrs={
                'class': 'form-control'
            }),
            'special_requests': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Any special requests or questions? (Optional)',
                'class': 'form-control'
            }),
        }
        labels = {
            'full_name': 'Full Name',
            'email': 'Email Address',
            'phone_number': 'Phone Number',
            'preferred_date': 'Preferred Date',
            'preferred_time': 'Preferred Time',
            'special_requests': 'Special Requests (Optional)',
        }


class ReviewForm(forms.ModelForm):
    """Form for submitting property reviews"""

    class Meta:
        model = PropertyReview
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Tell others what you loved (or didn\'t love) about this property…',
                'style': 'width:100%;padding:0.75rem 1rem;border:1.5px solid var(--gray-200);border-radius:var(--radius);font-size:0.9rem;color:var(--gray-800);background:var(--gray-50);outline:none;resize:vertical;font-family:inherit;transition:border-color 0.2s;'
            }),
            'rating': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].required = True
        self.fields['comment'].required = False

class ContactForm(forms.ModelForm):
    """Form for the public Contact Us page"""

    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your full name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@example.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '+254 712 000 000 (optional)'}),
            'message': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': "Tell us how we can help…"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-input')
        self.fields['phone'].required = False


class OwnerContactForm(forms.ModelForm):
    """Form on a property owner's public TuHame portfolio page
    (templates/public_profile/owner_portfolio.html) - a visitor reaching
    out directly to that owner. No `subject` field (that's specific to
    the platform's own general Contact Us page, ContactForm above) - the
    `owner` FK on the saved instance is what routes it to that owner's
    "Direct Contact" list instead, set by the view, not this form."""

    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your full name', 'class': 'field'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@example.com', 'class': 'field'}),
            'phone': forms.TextInput(attrs={'placeholder': '+254 712 000 000 (optional)', 'class': 'field'}),
            'message': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': "What are you looking for?",
                'class': 'field',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone'].required = False



import re as _re
from django.core.validators import validate_email as _validate_email
from .models import Lead

_URL_RE = _re.compile(r'(https?://|www\.)', _re.I)
_CONTROL_RE = _re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def _clean_text(value, max_len):
    """Collapse control characters and surrounding whitespace. Output escaping
    is left to the template engine/admin - we never mark anything safe."""
    return _CONTROL_RE.sub('', (value or '')).strip()[:max_len]


def normalize_ke_phone(raw):
    """'0712 345 678' / '+254712345678' / '254712345678' -> '254712345678'.
    Other international numbers (+ then 9-15 digits) are kept as digits."""
    digits = _re.sub(r'[\s\-().]', '', raw or '')
    if not _re.fullmatch(r'\+?\d{9,15}', digits):
        return None
    if digits.startswith('+'):
        return digits[1:]
    if digits.startswith('0') and len(digits) == 10:
        return '254' + digits[1:]
    if len(digits) == 9 and digits[0] in '17':
        return '254' + digits
    return digits


class LeadForm(forms.Form):
    """Strict server-side validation for the landing popup. The browser form
    is a convenience only - nothing here trusts it."""

    name = forms.CharField(max_length=100, min_length=2)
    phone = forms.CharField(max_length=25)
    email = forms.CharField(max_length=254, required=False)
    interest = forms.ChoiceField(choices=Lead.INTEREST_CHOICES)
    location = forms.CharField(max_length=100, required=False)
    budget = forms.CharField(max_length=15, required=False)
    message = forms.CharField(max_length=500, required=False)
    consent = forms.BooleanField(
        error_messages={'required': 'Please tick the box so we can contact you about this request.'}
    )

    def clean_name(self):
        name = _clean_text(self.cleaned_data['name'], 100)
        if len(name) < 2 or _URL_RE.search(name) or not _re.search(r'[A-Za-z\u00C0-\u024F]', name):
            raise forms.ValidationError('Please enter your real name.')
        return name

    def clean_phone(self):
        phone = normalize_ke_phone(self.cleaned_data['phone'])
        if not phone:
            raise forms.ValidationError('Enter a valid phone number, e.g. 0712 345 678.')
        return phone

    def clean_email(self):
        email = _clean_text(self.cleaned_data.get('email'), 254)
        if not email:
            return ''
        try:
            _validate_email(email)
        except forms.ValidationError:
            raise forms.ValidationError('That email address does not look right.')
        return email.lower()

    def clean_location(self):
        return _clean_text(self.cleaned_data.get('location'), 100)

    def clean_budget(self):
        raw = _re.sub(r'[,\sKESkes]', '', self.cleaned_data.get('budget') or '')
        if not raw:
            return None
        if not raw.isdigit() or int(raw) > 1_000_000_000:
            raise forms.ValidationError('Enter your budget as a number, e.g. 45000.')
        return int(raw)

    def clean_message(self):
        message = _clean_text(self.cleaned_data.get('message'), 500)
        if len(_URL_RE.findall(message)) > 1:
            raise forms.ValidationError('Please leave links out of your message.')
        return message
