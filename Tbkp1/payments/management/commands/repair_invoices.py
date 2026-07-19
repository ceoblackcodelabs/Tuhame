# apps/payments/management/commands/repair_invoices.py
from django.core.management.base import BaseCommand
from django.db import models
from decimal import Decimal
from django.utils import timezone
from payments.models import Invoice, Payment, PaymentStatus


class Command(BaseCommand):
    help = 'Repair and clean up invoice data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--repay',
            action='store_true',
            help='Recalculate total paid amounts for all invoices'
        )
        parser.add_argument(
            '--fix-overdue',
            action='store_true',
            help='Update overdue status for invoices'
        )
        parser.add_argument(
            '--clean-payments',
            action='store_true',
            help='Clean up orphaned payments'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all repair operations'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting invoice repair...'))

        if options['repay'] or options['all']:
            self.recalculate_payments()

        if options['fix_overdue'] or options['all']:
            self.update_overdue_status()

        if options['clean_payments'] or options['all']:
            self.clean_orphaned_payments()

        self.stdout.write(self.style.SUCCESS('\nInvoice repair complete!'))

    def recalculate_payments(self):
        """Recalculate total paid amounts for all invoices"""
        self.stdout.write('\n--- Recalculating invoice payment totals ---')

        invoices = Invoice.objects.all()
        updated = 0

        for invoice in invoices:
            # Calculate total paid
            total_paid = invoice.payments.filter(status='paid').aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')

            total_paid = total_paid.quantize(Decimal('0.01'))

            # Determine status
            if total_paid >= invoice.total_amount:
                correct_status = 'paid'
            elif total_paid > 0:
                correct_status = 'partial'
            else:
                correct_status = 'pending'

            # Update if needed
            if invoice.status != correct_status:
                invoice.status = correct_status
                if correct_status == 'paid':
                    invoice.paid_date = timezone.now().date()
                else:
                    invoice.paid_date = None
                invoice.save()
                updated += 1
                self.stdout.write(f'  Updated invoice {invoice.invoice_number}: {correct_status}')

        self.stdout.write(self.style.SUCCESS(f'Updated {updated} invoices'))

    def update_overdue_status(self):
        """Update overdue status for invoices"""
        self.stdout.write('\n--- Updating overdue status ---')

        today = timezone.now().date()

        # Invoices that are overdue
        overdue_invoices = Invoice.objects.filter(
            status__in=['pending', 'partial'],
            due_date__lt=today
        )

        count = overdue_invoices.count()
        overdue_invoices.update(status='overdue')

        self.stdout.write(self.style.SUCCESS(f'Marked {count} invoices as overdue'))

    def clean_orphaned_payments(self):
        """Clean up orphaned or invalid payments"""
        self.stdout.write('\n--- Cleaning orphaned payments ---')

        # Check for payments with amount > invoice total
        invalid_payments = []
        payments = Payment.objects.filter(status='paid')

        for payment in
            invoice = payment.invoice
            total_paid = invoice.payments.filter(status='paid').aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')

            if total_paid > invoice.total_amount + Decimal('0.01'):
                invalid_payments.append(payment)
                self.stdout.write(
                    f'  Found payment {payment.payment_id} exceeding invoice total: '
                    f'${total_paid} > ${invoice.total_amount}'
                )

        if invalid_
            self.stdout.write(f'\nFound {len(invalid_payments)} problematic payments')
            # Optionally mark them as refunded
            for payment in invalid_
                payment.status = 'refunded'
                payment.save()
                self.stdout.write(f'  Marked payment {payment.payment_id} as refunded')