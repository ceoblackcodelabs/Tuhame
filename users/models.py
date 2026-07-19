# apps/profiles/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from properties.models import Property
import uuid
from django.utils import timezone

User = get_user_model()


class UserRole(models.TextChoices):
    HUNTER = 'hunter', 'House Hunter'
    OWNER = 'owner', 'Property Owner'
    MOVER = 'mover', 'Mover'


class VerificationStatus(models.TextChoices):
    NONE = 'none', 'Not Requested'
    PENDING = 'pending', 'Pending Review'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


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

    # Role - hunter (looking for a place) or owner (listing properties)
    role = models.CharField(max_length=10, choices=UserRole.choices, default=UserRole.HUNTER)

    # Owner verification - a user switching to 'owner' needs to be approved
    # by the main admin before they're treated as a verified property owner
    verification_status = models.CharField(
        max_length=10, choices=VerificationStatus.choices, default=VerificationStatus.NONE
    )
    is_verified_owner = models.BooleanField(default=False)
    verification_requested_at = models.DateTimeField(blank=True, null=True)
    verification_reviewed_at = models.DateTimeField(blank=True, null=True)
    verification_reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, blank=True, null=True, related_name='verified_owner_profiles'
    )
    verification_notes = models.TextField(
        blank=True, help_text="Internal admin notes, e.g. reason for rejection"
    )

    # Mover portfolio - public profile a mover can edit once they hold the role
    MOVER_VEHICLE_CHOICES = [
        ('motorbike', 'Motorbike'),
        ('pickup', 'Pickup Truck'),
        ('van', 'Van'),
        ('truck_small', 'Small Truck'),
        ('truck_large', 'Large Truck'),
    ]
    mover_bio = models.TextField(blank=True, help_text="Public bio shown on your mover profile")
    mover_vehicle_type = models.CharField(max_length=20, choices=MOVER_VEHICLE_CHOICES, blank=True)
    mover_years_experience = models.PositiveIntegerField(default=0)
    mover_service_areas = models.CharField(
        max_length=255, blank=True, help_text="Comma-separated areas you serve, e.g. Kilimani, Westlands, Karen"
    )
    mover_base_lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    mover_base_lng = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    mover_base_label = models.CharField(max_length=255, blank=True, help_text="Human-readable base location")

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

    def is_hunter(self):
        return self.role == UserRole.HUNTER

    def is_owner_role(self):
        return self.role == UserRole.OWNER

    def is_mover(self):
        return self.role == UserRole.MOVER

    def completed_moves_count(self):
        return self.user.move_offers.filter(status='accepted', move_request__status='completed').count()

    def active_moves_count(self):
        return self.user.move_offers.filter(status='accepted', move_request__status='matched').count()

    def get_trust_score(self):
        """
        Simple, transparent trust score for a mover's public portfolio.
        Starts at a neutral 50 for a brand-new mover and grows with a track
        record of completed moves and account tenure, capped at 100.
        This is not a fake rating - it's derived entirely from real completed
        moves in our own database.
        """
        completed = self.completed_moves_count()
        if completed == 0:
            return None  # "New Mover" - no score yet, shown distinctly in templates
        tenure_days = (timezone.now() - self.created_at).days if self.created_at else 0
        score = 50 + min(completed * 6, 42) + min(tenure_days // 30, 8)
        return min(score, 100)

    def get_mover_service_areas_list(self):
        return [a.strip() for a in self.mover_service_areas.split(',') if a.strip()]

    def request_owner_verification(self):
        """
        Switch this profile to the owner role and (re)submit it for admin
        review, unless it's already verified.
        """
        self.role = UserRole.OWNER
        if not self.is_verified_owner:
            self.verification_status = VerificationStatus.PENDING
            self.verification_requested_at = timezone.now()
        self.save()

    def approve_owner_verification(self, reviewer):
        self.is_verified_owner = True
        self.verification_status = VerificationStatus.APPROVED
        self.verification_reviewed_at = timezone.now()
        self.verification_reviewed_by = reviewer
        self.save()

    def reject_owner_verification(self, reviewer, notes=''):
        self.is_verified_owner = False
        self.verification_status = VerificationStatus.REJECTED
        self.verification_reviewed_at = timezone.now()
        self.verification_reviewed_by = reviewer
        self.verification_notes = notes
        self.save()

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

    # apps/profiles/models.py - Update the generate_qr_code method
    def generate_qr_code(self):
        """Generate QR code for the user's profile"""
        try:
            import qrcode
            import logging
            from io import BytesIO
            from django.core.files.base import ContentFile
            from django.conf import settings

            logger = logging.getLogger(__name__)

            # Build the URL from SITE_URL (always set - see settings.py)
            base_url = settings.SITE_URL.rstrip('/')

            # Use the shorter QR URL pattern
            qr_url = f"{base_url}/users/qr/{self.qr_code_token}/"

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
            logging.getLogger(__name__).warning("Error generating QR code for profile %s: %s", self.pk, e)
            return False

    def regenerate_qr_code(self):
        """Regenerate QR code"""
        # Generate a new token
        self.qr_code_token = uuid.uuid4()
        return self.generate_qr_code()

    @property
    def total_moves(self):
        """Get total number of moves for this user"""
        return self.move_history.count()

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