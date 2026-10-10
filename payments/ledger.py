"""
Single source of truth for "money collected".

Rent is collected through two models that grew up separately:

  * payments.Payment   - recorded by a landlord against an Invoice
  * clients.Payment    - submitted by a tenant against a Bill and counted
                         only once the landlord has confirmed it
                         (payment_status='completed')

Every dashboard / overview / report figure for money in must go through
these helpers so the two can never drift apart again. Lookups use the
invoice-payment field names (payment_date, created_at); they are
translated for bill payments (paid_at).
"""
from decimal import Decimal

from django.db.models import Count, Sum

from clients.models import Payment as BillPayment
from payments.models import Payment as InvoicePayment

_LOOKUP_MAP = {'payment_date': 'paid_at__date', 'created_at': 'paid_at'}


def _translate(lookups):
    out = {}
    for key, value in lookups.items():
        head, sep, tail = key.partition('__')
        out[_LOOKUP_MAP.get(head, head) + sep + tail] = value
    return out


def _querysets(user, **lookups):
    if user is None:
        return InvoicePayment.objects.none(), BillPayment.objects.none()
    if user.is_superuser:
        invoice_qs = InvoicePayment.objects.all()
        bill_qs = BillPayment.objects.all()
    else:
        invoice_qs = InvoicePayment.objects.filter(invoice__property__owner=user)
        bill_qs = BillPayment.objects.filter(bill__property__owner=user)
    # payments of invoices already moved onto a bill are counted via that bill
    invoice_qs = invoice_qs.filter(status='paid', invoice__migrated_bill__isnull=True, **lookups)
    bill_qs = bill_qs.filter(payment_status='completed', **_translate(lookups))
    return invoice_qs, bill_qs


def collected(user, **lookups):
    """Total money in for `user`'s properties (all properties for a superuser)."""
    invoice_qs, bill_qs = _querysets(user, **lookups)
    return (
        (invoice_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0'))
        + (bill_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0'))
    )


def count(user, **lookups):
    invoice_qs, bill_qs = _querysets(user, **lookups)
    return invoice_qs.count() + bill_qs.count()


def by_method(user, **lookups):
    """[{'payment_method', 'count', 'total'}] merged across both systems."""
    invoice_qs, bill_qs = _querysets(user, **lookups)
    merged = {}
    for qs in (invoice_qs, bill_qs):
        for row in qs.values('payment_method').annotate(count=Count('id'), total=Sum('amount')):
            entry = merged.setdefault(row['payment_method'], {'payment_method': row['payment_method'], 'count': 0, 'total': Decimal('0')})
            entry['count'] += row['count']
            entry['total'] += row['total'] or Decimal('0')
    return sorted(merged.values(), key=lambda r: -r['total'])


def recent(user, limit=5):
    """Newest money-in events across both systems: [{'who', 'payment_date', 'amount', 'payment_method'}]."""
    invoice_qs, bill_qs = _querysets(user)
    rows = [
        {'who': p.client.name, 'payment_date': p.payment_date, 'amount': p.amount, 'payment_method': p.payment_method}
        for p in invoice_qs.select_related('client').order_by('-payment_date', '-created_at')[:limit]
    ] + [
        {'who': p.user.get_full_name() or p.user.username, 'payment_date': (p.paid_at or p.created_at).date(),
         'amount': p.amount, 'payment_method': p.payment_method}
        for p in bill_qs.select_related('user').order_by('-paid_at')[:limit]
    ]
    return sorted(rows, key=lambda r: r['payment_date'], reverse=True)[:limit]


def by_property(user, limit=5, **lookups):
    """Top properties by money collected: [{'title', 'city', 'total'}]."""
    invoice_qs, bill_qs = _querysets(user, **lookups)
    merged = {}
    for qs, prefix in ((invoice_qs, 'invoice__property'), (bill_qs, 'bill__property')):
        for row in qs.values(f'{prefix}__title', f'{prefix}__city').annotate(total=Sum('amount')):
            key = (row[f'{prefix}__title'], row[f'{prefix}__city'])
            merged[key] = merged.get(key, Decimal('0')) + (row['total'] or Decimal('0'))
    ranked = sorted(merged.items(), key=lambda kv: -kv[1])[:limit]
    return [{'title': t, 'city': c, 'total': total} for (t, c), total in ranked]
