# apps/payments/models.py
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PAID = 'paid', 'Paid'
    OVERDUE = 'overdue', 'Overdue'
    PARTIAL = 'partial', 'Partially Paid'
    REFUNDED = 'refunded', 'Refunded'
    CANCELLED = 'cancelled', 'Cancelled'


class PaymentMethod(models.TextChoices):
    CASH = 'cash', 'Cash'
    BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
    CREDIT_CARD = 'credit_card', 'Credit Card'
    DEBIT_CARD = 'debit_card', 'Debit Card'
    CHECK = 'check', 'Check'
    ONLINE = 'online', 'Online Payment'


class PaymentCategory(models.TextChoices):
    RENT = 'rent', 'Rent'
    DEPOSIT = 'deposit', 'Security Deposit'
    MAINTENANCE = 'maintenance', 'Maintenance Fee'
    UTILITIES = 'utilities', 'Utilities'
    LATE_FEE = 'late_fee', 'Late Fee'
    OTHER = 'other', 'Other'


class Invoice(models.Model):
    invoice_number = models.CharField(max_length=50, unique=True)
    contract = models.ForeignKey('contracts.Contract', on_delete=models.CASCADE, related_name='invoices')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='invoices')
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='invoices')

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    paid_date = models.DateField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    category = models.CharField(max_length=20, choices=PaymentCategory.choices, default=PaymentCategory.RENT)

    description = models.TextField(blank=True)
    period_start = models.DateField()
    period_end = models.DateField()

    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['client', 'status']),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.client.name} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"

        # Calculate total amount with proper decimal precision
        self.total_amount = (
            self.amount +
            self.tax_amount -
            self.discount_amount
        ).quantize(Decimal('0.01'))

        super().save(*args, **kwargs)

    def is_overdue(self):
        from django.utils import timezone
        return self.status != PaymentStatus.PAID and self.due_date < timezone.now().date()

    def get_remaining_balance(self):
        """Calculate remaining balance safely"""
        from decimal import Decimal
        total_paid = self.payments.filter(status='paid').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        remaining = self.total_amount - total_paid
        return remaining.quantize(Decimal('0.01'))

    def get_total_paid(self):
        """Calculate total paid amount safely"""
        from decimal import Decimal
        total_paid = self.payments.filter(status='paid').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        return total_paid.quantize(Decimal('0.01'))

    def is_fully_paid(self):
        """Check if invoice is fully paid"""
        return self.get_remaining_balance() <= Decimal('0.01')


class Payment(models.Model):
    payment_id = models.CharField(max_length=50, unique=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='payments')

    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    payment_date = models.DateField()
    reference_number = models.CharField(max_length=100, blank=True)

    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PAID)

    receipt_file = models.FileField(upload_to='payments/receipts/', blank=True, null=True)
    notes = models.TextField(blank=True)

    processed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='processed_payments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['payment_id']),
            models.Index(fields=['payment_date']),
        ]

    def __str__(self):
        return f"Payment {self.payment_id} - {self.amount} - {self.payment_date}"

    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class LateFee(models.Model):
    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name='late_fee')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    days_late = models.IntegerField()
    calculated_at = models.DateTimeField(auto_now_add=True)
    waived = models.BooleanField(default=False)
    waiver_reason = models.TextField(blank=True)

    def __str__(self):
        return f"Late Fee for {self.invoice.invoice_number}: ${self.amount}"