# apps/clients/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, MinValueValidator
from django.utils import timezone
from home.models import Property

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


class BillCategory(models.Model):
    """Category for bills (e.g., Rent, Water, Electricity)"""

    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji or icon for the bill")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Bill Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Bill(models.Model):
    """Model for bills and utilities"""

    BILL_STATUS = [
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
        ('processing', 'Processing'),
    ]

    BILL_TYPES = [
        ('rent', 'Rent'),
        ('water', 'Water'),
        ('electricity', 'Electricity'),
        ('internet', 'Internet'),
        ('service_charge', 'Service Charge'),
        ('maintenance', 'Maintenance'),
        ('security', 'Security'),
        ('garbage', 'Garbage Collection'),
        ('other', 'Other'),
    ]

    # Relationships
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='bills'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bills'
    )
    category = models.ForeignKey(
        BillCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bills'
    )

    # Bill Details
    bill_type = models.CharField(max_length=20, choices=BILL_TYPES, default='other')
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=BILL_STATUS, default='pending')

    # Additional Info
    reference_number = models.CharField(max_length=100, blank=True, help_text="Bill reference or invoice number")
    notes = models.TextField(blank=True)
    receipt = models.FileField(upload_to='bills/receipts/', blank=True, null=True)

    # Recurring
    is_recurring = models.BooleanField(default=False)
    recurrence_interval = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
            ('weekly', 'Weekly'),
        ],
        help_text="How often this bill recurs"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-due_date', '-created_at']
        indexes = [
            models.Index(fields=['property', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['bill_type']),
        ]

    def __str__(self):
        return f"{self.get_bill_type_display()} - {self.property.title} - {self.amount}"

    def is_paid(self):
        """Check if bill is paid"""
        return self.status == 'paid'

    def is_overdue(self):
        """Check if bill is overdue"""
        if self.status == 'paid':
            return False
        return self.due_date < timezone.now().date()

    def get_status_display_with_icon(self):
        """Get status with icon for display"""
        icons = {
            'paid': '✅ Paid',
            'pending': '⏳ Pending',
            'overdue': '❗ Overdue',
            'cancelled': '❌ Cancelled',
            'processing': '🔄 Processing',
        }
        return icons.get(self.status, self.get_status_display())

    def mark_as_paid(self, paid_date=None, reference_number=''):
        """Mark bill as paid"""
        self.status = 'paid'
        self.paid_date = paid_date or timezone.now().date()
        if reference_number:
            self.reference_number = reference_number
        self.save()

    def get_amount_display(self):
        """Get formatted amount"""
        return f"KES {self.amount:,.2f}"

    def get_days_until_due(self):
        """Get days until bill is due"""
        if self.status == 'paid':
            return None
        days = (self.due_date - timezone.now().date()).days
        return days


class UtilityUsage(models.Model):
    """Track utility usage over time (water, electricity, etc.)"""

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='utility_usage'
    )
    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name='utility_usage',
        null=True,
        blank=True
    )

    UTILITY_TYPES = [
        ('water', 'Water'),
        ('electricity', 'Electricity'),
        ('gas', 'Gas'),
        ('internet', 'Internet Data'),
        ('other', 'Other'),
    ]

    utility_type = models.CharField(max_length=20, choices=UTILITY_TYPES)
    usage_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Units used (e.g., kWh, liters)")
    unit = models.CharField(max_length=20, default='units', help_text="Unit of measurement")
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    reading_date = models.DateField(default=timezone.now)
    previous_reading = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    current_reading = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-reading_date']

    def __str__(self):
        return f"{self.get_utility_type_display()} - {self.property.title} - {self.reading_date}"

    def calculate_total_cost(self):
        """Calculate total cost based on usage and cost per unit"""
        if self.usage_amount and self.cost_per_unit:
            self.total_cost = self.usage_amount * self.cost_per_unit
            return self.total_cost
        return 0


class Payment(models.Model):
    """Track payments made by users"""

    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payments')

    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')

    transaction_id = models.CharField(max_length=100, blank=True, help_text="Transaction reference from payment provider")
    mpesa_code = models.CharField(max_length=50, blank=True, help_text="M-Pesa confirmation code")

    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    receipt_url = models.URLField(blank=True, help_text="Link to receipt")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.bill} - {self.amount}"

    def mark_completed(self, transaction_id=''):
        """Mark payment as completed"""
        self.payment_status = 'completed'
        self.paid_at = timezone.now()
        if transaction_id:
            self.transaction_id = transaction_id
        self.save()

        # Update bill status
        if self.bill:
            self.bill.mark_as_paid(reference_number=self.transaction_id)