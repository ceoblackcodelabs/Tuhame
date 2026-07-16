from django.db import models
from properties.models import Property
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class ViewingSchedule(models.Model):
    """Model for scheduling property viewings"""

    TIME_SLOTS = [
        ('morning', 'Morning (8am – 12pm)'),
        ('afternoon', 'Afternoon (12pm – 5pm)'),
        ('evening', 'Evening (5pm – 7pm)'),
    ]

    VIEWING_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='viewings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='viewings')

    # Contact details
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)

    # Viewing details
    preferred_date = models.DateField()
    preferred_time = models.CharField(max_length=20, choices=TIME_SLOTS, default='afternoon')
    special_requests = models.TextField(blank=True)

    # Status and metadata
    status = models.CharField(max_length=20, choices=VIEWING_STATUS, default='pending')
    notes = models.TextField(blank=True, help_text="Internal notes for the property owner/agent")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Scheduling
    scheduled_datetime = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['property', 'status']),
            models.Index(fields=['preferred_date']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"Viewing for {self.property.title} - {self.full_name} ({self.preferred_date})"

    def confirm_viewing(self, scheduled_datetime=None):
        """Confirm the viewing and set scheduled time"""
        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        if scheduled_datetime:
            self.scheduled_datetime = scheduled_datetime
        self.save()

    def complete_viewing(self):
        """Mark viewing as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()

    def cancel_viewing(self, reason=""):
        """Cancel the viewing"""
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        self.save()

    def is_pending(self):
        return self.status == 'pending'

    def is_confirmed(self):
        return self.status == 'confirmed'

    def is_upcoming(self):
        """Check if the viewing is upcoming (confirmed and in the future)"""
        if self.status == 'confirmed' and self.scheduled_datetime:
            return self.scheduled_datetime > timezone.now()
        return False


class SavedProperty(models.Model):
    """Model to track saved/favourite properties for users"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_properties'
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='saved_by'
    )
    saved_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Optional notes about why this property was saved")

    class Meta:
        ordering = ['-saved_at']
        unique_together = ['user', 'property']  # Prevent duplicate saves

    def __str__(self):
        return f"{self.user.username} saved {self.property.title}"



# move
class MoveRequest(models.Model):
    """Model for move requests"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    TIME_CHOICES = [
        ('morning', 'Morning (8am-12pm)'),
        ('afternoon', 'Afternoon (12pm-5pm)'),
        ('evening', 'Evening (5pm-8pm)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='move_requests')

    # Move details
    moving_from = models.TextField()
    moving_from_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    moving_from_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    moving_to_property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='move_in_requests'
    )
    moving_to_manual = models.TextField(blank=True, help_text="If not selecting a property")
    moving_to_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    moving_to_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    move_date = models.DateField()
    move_time = models.CharField(max_length=20, choices=TIME_CHOICES, default='afternoon')

    # Items
    items = models.JSONField(default=list, help_text="List of items to move")
    items_list = models.CharField(max_length=500, blank=True, help_text="Comma-separated list for display")

    # Special instructions
    special_instructions = models.TextField(blank=True)

    # Mover request
    request_mover = models.BooleanField(default=False)
    movers_count = models.IntegerField(default=2)
    estimated_hours = models.IntegerField(default=4)
    mover_notes = models.TextField(blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, help_text="Admin notes")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Move request by {self.user.username} - {self.move_date}"

    def get_items_display(self):
        """Get readable items list"""
        if self.items:
            return ', '.join(self.items)
        return self.items_list


DEFAULT_CHECKLIST_ITEMS = [
    'Notify current landlord',
    'Book moving company',
    'Transfer utilities to new address',
    'Update address with bank',
    'Pack bedroom',
    'Pack kitchen',
    'Pack living room',
    'Arrange cleaning service',
    'Return keys to old property',
    'Set up internet at new place',
    'Update address with KRA',
    'Update address with NHIF/NSSF',
]


class MoveChecklistItem(models.Model):
    """A single to-do item on a user's moving checklist"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='checklist_items')
    text = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.text} ({'done' if self.done else 'pending'}) - {self.user.username}"

    @classmethod
    def seed_defaults_for(cls, user):
        """Create the default checklist for a user who has none yet"""
        items = [
            cls(user=user, text=text, done=False, order=i)
            for i, text in enumerate(DEFAULT_CHECKLIST_ITEMS)
        ]
        cls.objects.bulk_create(items)
        return cls.objects.filter(user=user).order_by('order', 'created_at')


class ContactMessage(models.Model):
    """A message submitted through the public Contact Us page"""

    SUBJECT_CHOICES = [
        ('general', 'General Inquiry'),
        ('support', 'Support / Technical Issue'),
        ('listing', 'Listing a Property'),
        ('partnership', 'Partnership / Business'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES, default='general')
    message = models.TextField()

    # Optionally linked if the sender was logged in
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='contact_messages'
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_subject_display()} ({self.created_at:%Y-%m-%d})"