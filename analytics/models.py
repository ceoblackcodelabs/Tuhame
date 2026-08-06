from django.conf import settings
from django.db import models
from django.utils import timezone


class PageVisit(models.Model):
    """
    One row per real pageview, logged by analytics.middleware.PageVisitMiddleware.
    This is what the Traffic and Blog Analytics dashboards are built on -
    there's no other visit tracking anywhere in the project, so this is the
    actual source of truth rather than an estimate.
    """

    DEVICE_DESKTOP = 'desktop'
    DEVICE_MOBILE = 'mobile'
    DEVICE_TABLET = 'tablet'
    DEVICE_BOT = 'bot'
    DEVICE_OTHER = 'other'
    DEVICE_CHOICES = [
        (DEVICE_DESKTOP, 'Desktop'),
        (DEVICE_MOBILE, 'Mobile'),
        (DEVICE_TABLET, 'Tablet'),
        (DEVICE_BOT, 'Bot'),
        (DEVICE_OTHER, 'Other'),
    ]

    path = models.CharField(max_length=500, db_index=True)
    visited_at = models.DateTimeField(default=timezone.now, db_index=True)

    # Best-effort "who" - a session key covers anonymous visitors too,
    # since most site traffic isn't logged in.
    session_key = models.CharField(max_length=40, blank=True, default='', db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='page_visits',
    )

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_type = models.CharField(max_length=10, choices=DEVICE_CHOICES, default=DEVICE_OTHER, db_index=True)

    # Populated lazily by analytics.geolocation, not at request time - see
    # that module for why (keeps page-load latency unaffected by an
    # external geolocation lookup).
    country = models.CharField(max_length=100, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    location_resolved = models.BooleanField(default=False, db_index=True)

    referrer = models.CharField(max_length=500, blank=True, default='')

    class Meta:
        indexes = [
            models.Index(fields=['visited_at']),
            models.Index(fields=['path', 'visited_at']),
            models.Index(fields=['location_resolved']),
        ]
        ordering = ['-visited_at']

    def __str__(self):
        return f'{self.path} @ {self.visited_at:%Y-%m-%d %H:%M}'
