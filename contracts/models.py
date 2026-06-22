# apps/contracts/models.py
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid


class ContractType(models.TextChoices):
    LEASE = 'lease', 'Lease Agreement'
    SALE = 'sale', 'Sale Agreement'
    BOOKING = 'booking', 'Booking Agreement'
    MANAGEMENT = 'management', 'Property Management'


class ContractStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PENDING = 'pending', 'Pending Signature'
    ACTIVE = 'active', 'Active'
    COMPLETED = 'completed', 'Completed'
    TERMINATED = 'terminated', 'Terminated'
    EXPIRED = 'expired', 'Expired'


class Contract(models.Model):
    # Contract Info
    contract_number = models.CharField(max_length=50, unique=True)
    contract_type = models.CharField(max_length=20, choices=ContractType.choices)
    status = models.CharField(max_length=20, choices=ContractStatus.choices, default=ContractStatus.DRAFT)

    # Related Entities
    property = models.ForeignKey('properties.Property', on_delete=models.PROTECT, related_name='contracts')
    unit = models.ForeignKey('properties.Unit', on_delete=models.SET_NULL, null=True, blank=True, related_name='contracts')
    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='contracts')
    owner = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='owner_contracts', null=True)

    # Financial Terms
    monthly_rent = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    security_deposit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    payment_due_day = models.IntegerField(default=1, validators=[MinValueValidator(1)])

    # Dates
    start_date = models.DateField()
    end_date = models.DateField()
    termination_date = models.DateField(blank=True, null=True)
    signed_date = models.DateField(blank=True, null=True)

    # Terms
    notice_period_days = models.IntegerField(default=30)
    late_fee_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    late_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Documents
    contract_file = models.FileField(upload_to='contracts/', blank=True, null=True)

    # Additional Info
    special_terms = models.TextField(blank=True)
    utilities_included = models.BooleanField(default=False)
    parking_included = models.BooleanField(default=True)
    pets_allowed = models.BooleanField(default=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contract_number']),
            models.Index(fields=['status', 'start_date']),
            models.Index(fields=['client', 'property']),
        ]

    def __str__(self):
        return f"{self.contract_number} - {self.client.name} - {self.property.title}"

    def save(self, *args, **kwargs):
        if not self.contract_number:
            self.contract_number = f"CTR-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def is_active(self):
        """Check if contract is currently active"""
        today = timezone.now().date()
        return self.status == ContractStatus.ACTIVE and self.start_date <= today <= self.end_date

    def days_remaining(self):
        """Calculate days remaining in contract"""
        today = timezone.now().date()
        if self.end_date > today:
            return (self.end_date - today).days
        return 0


class ContractSignature(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='signatures')
    signer_name = models.CharField(max_length=200)
    signer_email = models.EmailField()
    signed_at = models.DateTimeField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    signature_file = models.ImageField(upload_to='contracts/signatures/', blank=True, null=True)
    is_owner = models.BooleanField(default=False)

    def __str__(self):
        status = "Signed" if self.signed_at else "Pending"
        return f"{self.signer_name} - {status}"


class ContractRenewal(models.Model):
    original_contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='renewals')
    new_contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='renewed_from', null=True)
    renewal_date = models.DateField(auto_now_add=True)
    new_end_date = models.DateField()
    terms_changed = models.TextField(blank=True)
    approved_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Renewal for {self.original_contract.contract_number}"