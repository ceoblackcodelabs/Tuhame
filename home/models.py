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


