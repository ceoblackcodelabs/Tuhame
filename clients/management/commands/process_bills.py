"""
Daily housekeeping for rent collection. Run once a day from cron, e.g.

    0 6 * * * cd /path/to/Tuhame && python manage.py process_bills

  1. Every period of a recurring bill that has come due since it was last
     processed gets its bill created - including all the months missed if
     this wasn't run for a while (re-running is safe: nothing is duplicated).
  2. Pending bills past their due date become "overdue".

Recurrence is handed forward: only the newest bill in a chain stays
recurring, so each period is generated exactly once. A recurring bill
whose tenant has moved out of the property stops recurring.
"""
import calendar
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from clients.models import Bill

MONTHS = {'monthly': 1, 'quarterly': 3, 'yearly': 12}


def add_periods(start, interval, k):
    """`start` moved forward by k periods. Always counted from the original
    date so a bill due on the 31st returns to the 31st after a short month
    instead of drifting to the 28th."""
    if interval == 'weekly':
        return start + timedelta(weeks=k)
    month_index = start.month - 1 + MONTHS[interval] * k
    year, month = start.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


class Command(BaseCommand):
    help = 'Generate due recurring bills (including missed periods) and mark late bills overdue.'

    def handle(self, *args, **options):
        today = timezone.now().date()
        created = 0

        recurring = Bill.objects.filter(is_recurring=True, is_active=True, recurrence_interval__in=list(MONTHS) + ['weekly'])
        for bill in recurring.select_related('property', 'user__profile'):
            tenant = bill.user
            if tenant is not None and getattr(tenant, 'profile', None) and tenant.profile.current_property_id != bill.property_id:
                Bill.objects.filter(pk=bill.pk).update(is_recurring=False)  # moved out
                continue

            with transaction.atomic():
                newest, k = bill, 1
                while (due := add_periods(bill.due_date, bill.recurrence_interval, k)) <= today:
                    newest, was_created = Bill.objects.get_or_create(
                        property=bill.property, user=bill.user, bill_type=bill.bill_type, due_date=due,
                        defaults={
                            'category': bill.category,
                            'description': bill.description,
                            'amount': bill.amount,
                            'status': 'pending',
                            'is_recurring': False,
                            'recurrence_interval': bill.recurrence_interval,
                        },
                    )
                    created += was_created
                    k += 1
                if newest is not bill:
                    Bill.objects.filter(pk=newest.pk).update(is_recurring=True)
                    Bill.objects.filter(pk=bill.pk).update(is_recurring=False)

        overdue = Bill.objects.filter(status='pending', due_date__lt=today).update(status='overdue')

        self.stdout.write(self.style.SUCCESS(
            f'{created} recurring bill(s) created, {overdue} bill(s) marked overdue.'
        ))
