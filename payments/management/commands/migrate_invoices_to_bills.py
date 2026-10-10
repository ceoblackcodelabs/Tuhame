"""
One-off: move the legacy Invoice system onto Bills, so landlords have a
single way to bill tenants.

    python manage.py migrate_invoices_to_bills --dry-run   # preview
    python manage.py migrate_invoices_to_bills             # do it

For every invoice not yet migrated:
  * a Bill is created (billed to the client's account, or - for off-platform
    clients with no account - held under the property owner so it is never
    shown to other residents; the client's name is kept in the description)
  * each of its payments becomes a Payment on that bill
  * unpaid invoices are cancelled (superseded by the bill) so they stop
    counting as pending/overdue; paid ones keep their status as history
  * Invoice.migrated_bill is set, which also stops the money ledger counting
    the old payments a second time

Safe to re-run: already-migrated invoices are skipped. Each invoice is
migrated in its own transaction.
"""
from datetime import datetime, time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from clients.models import Bill, Payment as BillPayment
from payments.models import Invoice

BILL_TYPE = {'rent': 'rent', 'maintenance': 'maintenance'}
BILL_STATUS = {'paid': 'paid', 'overdue': 'overdue', 'pending': 'pending', 'partial': 'pending',
               'cancelled': 'cancelled', 'refunded': 'cancelled'}
METHOD = {'cash': 'cash', 'bank_transfer': 'bank_transfer', 'credit_card': 'card',
          'debit_card': 'card', 'check': 'cheque', 'online': 'other', 'mpesa': 'mpesa'}
PAY_STATUS = {'paid': 'completed', 'pending': 'pending', 'refunded': 'refunded'}


def migrate_invoice(invoice):
    client = invoice.client
    owner = invoice.property.owner
    tenant = client.user or owner

    paid = invoice.get_total_paid()
    amount = invoice.total_amount
    notes = [f'Migrated from invoice {invoice.invoice_number}.']
    if invoice.status == 'partial' and paid:
        amount = invoice.total_amount - paid
        notes.append(f'Originally {invoice.total_amount}, {paid} already paid.')

    description = invoice.description or f'Invoice {invoice.invoice_number}'
    if not client.user_id:
        description = f'{description} – {client.name}'

    bill = Bill.objects.create(
        property=invoice.property, user=tenant,
        bill_type=BILL_TYPE.get(invoice.category, 'other'),
        description=description[:200], amount=amount, due_date=invoice.due_date,
        paid_date=invoice.paid_date, status=BILL_STATUS.get(invoice.status, 'pending'),
        reference_number=invoice.invoice_number, notes=' '.join(notes),
    )

    for payment in invoice.payments.all():
        BillPayment.objects.create(
            user=tenant, bill=bill, amount=payment.amount,
            payment_method=METHOD.get(payment.payment_method, 'other'),
            payment_status=PAY_STATUS.get(payment.status, 'cancelled'),
            transaction_id=payment.reference_number[:100],
            paid_at=timezone.make_aware(datetime.combine(payment.payment_date, time(12, 0))),
            notes=f'Migrated from payment {payment.payment_id}.',
        )

    if invoice.status in ('pending', 'partial', 'overdue'):
        invoice.status = 'cancelled'
    invoice.migrated_bill = bill
    invoice.save()
    return bill


class Command(BaseCommand):
    help = 'Migrate legacy invoices and their payments onto Bills.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated, change nothing.')

    def handle(self, *args, **options):
        todo = Invoice.objects.filter(migrated_bill__isnull=True).select_related('client', 'property__owner')
        total = todo.count()
        if options['dry_run']:
            for inv in todo:
                self.stdout.write(f'would migrate {inv.invoice_number} ({inv.status}, {inv.total_amount}, '
                                  f'{inv.payments.count()} payment(s))')
            self.stdout.write(f'{total} invoice(s) would be migrated.')
            return

        done = 0
        for invoice in todo:
            try:
                with transaction.atomic():
                    migrate_invoice(invoice)
                done += 1
            except Exception as exc:  # keep going; report at the end
                self.stderr.write(f'FAILED {invoice.invoice_number}: {exc}')
        self.stdout.write(self.style.SUCCESS(f'Migrated {done} of {total} invoice(s).'))
