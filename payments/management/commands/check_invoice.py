# Create a temporary debug command
# apps/payments/management/commands/check_invoice.py

from django.core.management.base import BaseCommand
from payments.models import Invoice
from django.db import models
from decimal import Decimal

class Command(BaseCommand):
    help = 'Check invoice payment status'

    def add_arguments(self, parser):
        parser.add_argument('invoice_id', type=int, help='Invoice ID to check')

    def handle(self, *args, **options):
        invoice_id = options['invoice_id']

        try:
            invoice = Invoice.objects.get(id=invoice_id)

            self.stdout.write(f"\nInvoice Details:")
            self.stdout.write(f"ID: {invoice.id}")
            self.stdout.write(f"Number: {invoice.invoice_number}")
            self.stdout.write(f"Total Amount: ${invoice.total_amount}")
            self.stdout.write(f"Status: {invoice.status}")

            # Calculate total paid
            total_paid = invoice.payments.filter(status='paid').aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')

            self.stdout.write(f"Total Paid: ${total_paid}")
            self.stdout.write(f"Remaining: ${invoice.total_amount - total_paid}")

            # List all payments
            payments = invoice.payments.all()
            if
                self.stdout.write(f"\nPayment History:")
                for payment in
                    self.stdout.write(f"  - {payment.payment_id}: ${payment.amount} ({payment.status}) on {payment.payment_date}")
            else:
                self.stdout.write("\nNo payments recorded.")

        except Invoice.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Invoice with ID {invoice_id} not found"))