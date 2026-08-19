# apps/subscriptions/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
import calendar


def add_months(dt, months):
    """Add N calendar months to a datetime without needing python-dateutil
    (not in requirements.txt - this project deploys to shared hosting where
    extra deps are best avoided). Clamps the day to the target month's
    length, e.g. Jan 31 + 1 month -> Feb 28/29."""
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


class BillingPeriod(models.TextChoices):
    FREE = 'free', 'Free'
    MONTHLY = 'monthly', 'Monthly'
    ANNUAL = 'annual', 'Annual'


class SubscriptionPlan(models.Model):
    """A purchasable tier (Free / Monthly / Annual). Prices are editable by
    the platform admin from the Settings > Plans screen, so they aren't
    hardcoded anywhere beyond the seed migration's starting values."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    billing_period = models.CharField(max_length=10, choices=BillingPeriod.choices)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.CharField(
        max_length=255, blank=True,
        help_text="Short line shown under the plan name, e.g. 'Unlimited listings, priority support'.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'price']

    def __str__(self):
        return f"{self.name} (KES {self.price})" if self.price else self.name

    def duration_months_value(self):
        """How many months one purchase of this plan covers, or None for
        Free (never expires)."""
        if self.billing_period == BillingPeriod.MONTHLY:
            return 1
        if self.billing_period == BillingPeriod.ANNUAL:
            return 12
        return None


class Offer(models.Model):
    """An admin-created promo, e.g. 'KES 5,000 for the first 10 users,
    unlimited use for 24 months'. Claiming one grants the claimant a
    subscription that runs for `duration_months`, capped at `max_claims`
    total claimants."""
    title = models.CharField(max_length=150)
    description = models.TextField(
        blank=True, help_text="Shown to owners on the Settings page, e.g. what's included.",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in KES for this offer.")
    max_claims = models.PositiveIntegerField(help_text="How many users can grab this offer, e.g. 10.")
    duration_months = models.PositiveIntegerField(help_text="How many months of access one claim covers, e.g. 24.")
    is_active = models.BooleanField(default=True)
    available_until = models.DateTimeField(
        blank=True, null=True,
        help_text="Optional cutoff date after which the offer can no longer be claimed, even if slots remain.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='offers_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def claims_count(self):
        return self.claims.count()

    def claims_remaining(self):
        return max(self.max_claims - self.claims_count(), 0)

    def is_claimable(self):
        if not self.is_active:
            return False
        if self.available_until and timezone.now() > self.available_until:
            return False
        return self.claims_remaining() > 0

    def has_been_claimed_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.claims.filter(user=user).exists()


class OfferClaim(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='claims')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='offer_claims')
    claimed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['offer', 'user']
        ordering = ['-claimed_at']

    def __str__(self):
        return f"{self.user} claimed {self.offer}"


class OwnerSubscription(models.Model):
    """Which plan an owner is currently on. Every owner effectively has one
    of these - created lazily (defaulting to the Free plan) the first time
    they visit Settings, rather than via a signal, to keep this simple."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, related_name='subscribers')
    source_offer = models.ForeignKey(
        Offer, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions',
        help_text="Set if this subscription came from claiming an offer rather than a standard plan.",
    )
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(blank=True, null=True, help_text="Blank/null means it never expires (Free plan).")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.plan}"

    def is_expired(self):
        return bool(self.expires_at and timezone.now() > self.expires_at)

    def status_label(self):
        if self.source_offer:
            return 'Expired' if self.is_expired() else 'Active'
        if not self.plan or self.plan.billing_period == BillingPeriod.FREE:
            return 'Free'
        if self.is_expired():
            return 'Expired'
        return 'Active'
