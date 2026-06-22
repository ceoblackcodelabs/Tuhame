# apps/clients/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, MinValueValidator

User = get_user_model()


class ClientType(models.TextChoices):
    TENANT = 'tenant', 'Tenant'
    BUYER = 'buyer', 'Buyer'
    OWNER = 'owner', 'Property Owner'
    AGENT = 'agent', 'Real Estate Agent'
    INVESTOR = 'investor', 'Investor'


class Client(models.Model):
    # Personal Info
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='client_profile')
    client_type = models.CharField(max_length=20, choices=ClientType.choices, default=ClientType.TENANT)

    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')])
    alternate_phone = models.CharField(max_length=20, blank=True)

    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)

    # Identification
    id_type = models.CharField(max_length=50, blank=True, help_text="Passport, Driver's License, etc.")
    id_number = models.CharField(max_length=100, blank=True)
    id_document = models.FileField(upload_to='clients/documents/', blank=True, null=True)

    # Professional Info
    occupation = models.CharField(max_length=100, blank=True)
    employer = models.CharField(max_length=200, blank=True)
    annual_income = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    # Preferences
    preferred_property_types = models.CharField(max_length=200, blank=True)
    budget_min = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    preferred_locations = models.TextField(blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    joined_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_clients')

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['client_type']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_client_type_display()})"


class ClientDocument(models.Model):
    DOCUMENT_TYPES = [
        ('id', 'Identification'),
        ('income', 'Income Proof'),
        ('employment', 'Employment Letter'),
        ('reference', 'Reference'),
        ('contract', 'Contract'),
        ('other', 'Other'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='clients/documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.client.name} - {self.title}"


class Watchlist(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='watchlist')
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='watched_by')
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['client', 'property']

    def __str__(self):
        return f"{self.client.name} watches {self.property.title}"