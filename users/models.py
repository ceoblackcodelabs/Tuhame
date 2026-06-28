# apps/profiles/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from properties.models import Property
import uuid
from django.utils import timezone

User = get_user_model()


class Profile(models.Model):
    """User profile model - one to one with User"""

    # Relationship with User
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    # Personal Information
    full_name = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(
        upload_to='profiles/pictures/',
        blank=True,
        null=True
    )
    date_of_birth = models.DateField(blank=True, null=True)

    # Contact Information
    phone_number = models.CharField(max_length=20, blank=True)
    alternative_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Kenya')
    zip_code = models.CharField(max_length=20, blank=True)

    # Professional Information
    occupation = models.CharField(max_length=100, blank=True)
    employer = models.CharField(max_length=200, blank=True)

    # Current Residence
    current_property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='residents',
        help_text="The property where this user currently lives"
    )
    moved_in_date = models.DateField(blank=True, null=True)

    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)

    # Preferences
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=[
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('whatsapp', 'WhatsApp'),
            ('sms', 'SMS'),
        ],
        default='email'
    )
    preferred_language = models.CharField(
        max_length=20,
        choices=[
            ('en', 'English'),
            ('sw', 'Swahili'),
        ],
        default='en'
    )

    # Notifications
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=True)

    # QR Code
    qr_code_image = models.ImageField(
        upload_to='profiles/qr_codes/',
        blank=True,
        null=True,
        help_text="QR code for the user's profile"
    )
    qr_code_token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="Unique token for QR code"
    )
    qr_code_generated_at = models.DateTimeField(blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['city', 'country']),
            models.Index(fields=['qr_code_token']),
        ]

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_full_name(self):
        """Get full name or fallback to username"""
        if self.full_name:
            return self.full_name
        return self.user.get_full_name() or self.user.username

    def get_phone(self):
        """Get primary phone number"""
        return self.phone_number

    def has_current_property(self):
        """Check if user has a current property"""
        return self.current_property is not None

    def move_to_property(self, property, moved_in_date=None):
        """Move user to a new property"""
        from django.utils import timezone

        if self.current_property:
            pass

        self.current_property = property
        self.moved_in_date = moved_in_date or timezone.now().date()
        self.save()

        # Generate QR code when moved to a property
        self.generate_qr_code()

    def leave_current_property(self):
        """Remove user from current property"""
        self.current_property = None
        self.moved_in_date = None
        self.save()

    def generate_qr_code(self):
        """Generate QR code for the user's profile"""
        try:
            import qrcode
            from io import BytesIO
            from django.core.files.base import ContentFile
            from django.urls import reverse

            # Create QR code data
            qr_data = {
                'user_id': self.user.id,
                'username': self.user.username,
                'token': str(self.qr_code_token),
                'profile_id': self.id,
            }

            # Build the URL for the profile
            # Using the QR token URL
            qr_url = f"/profile/qr/{self.qr_code_token}/"

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)

            # Create image
            img = qr.make_image(fill_color="black", back_color="white")

            # Save to BytesIO
            buffer = BytesIO()
            img.save(buffer, format='PNG')

            # Save to model
            filename = f"qr_{self.user.username}_{self.id}.png"
            self.qr_code_image.save(filename, ContentFile(buffer.getvalue()), save=False)
            self.qr_code_generated_at = timezone.now()
            self.save()

            return True
        except Exception as e:
            print(f"Error generating QR code: {e}")
            return False

    def regenerate_qr_code(self):
        """Regenerate QR code"""
        # Generate a new token
        self.qr_code_token = uuid.uuid4()
        return self.generate_qr_code()

class MoveHistory(models.Model):
    """Track user moves between properties"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='move_history')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='move_history')

    from_property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moves_out'
    )
    to_property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moves_in'
    )

    moved_in_date = models.DateField()
    moved_out_date = models.DateField(null=True, blank=True)

    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-moved_in_date']

    def __str__(self):
        return f"{self.profile.get_full_name()} moved to {self.to_property.title if self.to_property else 'Unknown'}"