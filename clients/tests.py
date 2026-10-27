"""
End-to-end test of the landlord -> tenant rent collection flow:

  landlord adds tenant -> rent bill generated -> tenant sees it in their
  portal (and only their own) -> tenant reports payment -> landlord
  confirms -> landlord dashboard shows the money.
"""
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.cache import cache as _cache
from django.test import TestCase as _DjangoTestCase, override_settings


class TestCase(_DjangoTestCase):
    """Rate-limit counters live in the shared cache, so start every test clean."""

    def _pre_setup(self):
        super()._pre_setup()
        _cache.clear()

from django.urls import reverse
from django.utils import timezone

from clients.models import Bill, Payment
from home.models import ServiceRequest, ServiceReview
from properties.models import Property
from users.models import Profile

User = get_user_model()

# The real storage needs `collectstatic` to have run; tests shouldn't.
TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def make_property(owner, title):
    return Property.objects.create(
        title=title, property_type='residential', address='1 Test Rd', city='Nairobi',
        state='Nairobi', zip_code='00100', description='x', area_sqft=500, price=Decimal('25000'),
        owner=owner,
    )


def make_user(username, role='hunter', verified_owner=False):
    user = User.objects.create_user(username, f'{username}@example.com', 'pass12345')
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.role = role
    profile.is_verified_owner = verified_owner
    profile.save()
    # users.signals re-saves the *cached* user.profile on every User.save()
    # (incl. login), so hand back a fresh instance without a stale cache.
    return User.objects.get(pk=user.pk)


@override_settings(STORAGES=TEST_STORAGES, ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False, FORMGUARD_ENABLED=False, RATELIMIT_ENABLED=False)
class RentCollectionFlowTests(TestCase):
    def setUp(self):
        self.landlord = make_user('landlord', 'owner', verified_owner=True)
        self.other_landlord = make_user('landlord2', 'owner', verified_owner=True)
        self.tenant1 = make_user('tenant1')
        self.tenant2 = make_user('tenant2')
        self.prop = make_property(self.landlord, 'Block A')
        self.other_prop = make_property(self.other_landlord, 'Block Z')

    def assign(self, tenant, rent='25000'):
        self.client.force_login(self.landlord)
        return self.client.post(reverse('tenant_add'), {
            'property': self.prop.pk,
            'tenant_email': tenant.email,
            'monthly_rent': rent,
            'moved_in_date': timezone.now().date().isoformat(),
            'generate_first_bill': 'on',
        })

    def test_full_flow(self):
        # 1. landlord assigns two tenants to the same building
        self.assertRedirects(self.assign(self.tenant1), reverse('tenant_list'))
        self.assign(self.tenant2)
        bill1 = Bill.objects.get(user=self.tenant1)
        bill2 = Bill.objects.get(user=self.tenant2)
        self.assertEqual(bill1.amount, Decimal('25000.00'))

        # 2. landlord roster + bill list render
        for name in ('tenant_list', 'bill_list', 'dashboard', 'client_list', 'invoice_list',
                     'payment_list', 'contract_list', 'property_list'):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 200, name)
        self.assertContains(self.client.get(reverse('tenant_list')), 'tenant1')

        # 3. tenant portal shows the tenant's own bill but not their neighbour's
        self.client.force_login(self.tenant1)
        r = self.client.get(reverse('my_profile'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual([b.pk for b in r.context['bills']], [bill1.pk])
        self.assertEqual(r.context['total_amount_due'], Decimal('25000.00'))

        # 4. tenants can't pay (or even open) someone else's bill
        self.assertEqual(self.client.get(reverse('tenant_bill_pay', args=[bill2.pk])).status_code, 403)
        self.assertEqual(self.client.post(
            reverse('tenant_bill_pay', args=[bill2.pk]), {'payment_method': 'mpesa'}).status_code, 403)
        bill2.refresh_from_db()
        self.assertEqual(bill2.status, 'pending')

        # 5. tenant reports payment -> NOT yet paid; landlord must confirm
        r = self.client.post(reverse('tenant_bill_pay', args=[bill1.pk]),
                             {'payment_method': 'mpesa', 'transaction_id': 'QK7X8Y9Z1A'})
        self.assertRedirects(r, reverse('my_profile'))
        bill1.refresh_from_db()
        self.assertEqual(bill1.status, 'processing')
        payment = Payment.objects.get(bill=bill1)
        self.assertEqual(payment.payment_status, 'pending')

        # a second submit must not create a duplicate payment
        self.client.post(reverse('tenant_bill_pay', args=[bill1.pk]),
                         {'payment_method': 'mpesa', 'transaction_id': 'QK7X8Y9Z1A'})
        self.assertEqual(Payment.objects.filter(bill=bill1).count(), 1)

        # tenants can't confirm payments themselves
        self.assertEqual(self.client.post(reverse('bill_mark_paid', args=[bill1.pk])).status_code, 403)

        # 6. a different landlord can't confirm it either
        self.client.force_login(self.other_landlord)
        self.assertEqual(self.client.post(reverse('bill_mark_paid', args=[bill1.pk])).status_code, 403)

        # 7. the real landlord confirms -> bill paid, payment completed
        self.client.force_login(self.landlord)
        self.client.post(reverse('bill_mark_paid', args=[bill1.pk]))
        bill1.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(bill1.status, 'paid')
        self.assertEqual(payment.payment_status, 'completed')

        # 8. landlord dashboard now counts the rent collected
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['revenue_current_value'], 'KSh 25,000.00')

        # 9. other landlord's dashboard and bill list stay empty
        self.client.force_login(self.other_landlord)
        self.assertEqual(self.client.get(reverse('dashboard')).context['revenue_current_value'], 'KSh 0.00')
        self.assertEqual(self.client.get(reverse('bill_list')).context['total_bills'], 0)

    def test_dashboard_denied_to_tenants(self):
        self.client.force_login(self.tenant1)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)

    def test_landlord_cannot_assign_tenant_to_other_landlords_property(self):
        self.client.force_login(self.landlord)
        r = self.client.post(reverse('tenant_add'), {
            'property': self.other_prop.pk, 'tenant_email': self.tenant1.email,
            'monthly_rent': '100', 'moved_in_date': timezone.now().date().isoformat(),
        })
        self.assertEqual(r.status_code, 200)  # form re-rendered with an error
        self.assertFalse(Profile.objects.filter(current_property=self.other_prop).exists())

    def test_remove_tenant(self):
        self.assign(self.tenant1)
        profile = Profile.objects.get(user=self.tenant1)
        self.client.force_login(self.other_landlord)
        self.assertEqual(self.client.post(reverse('tenant_remove', args=[profile.pk])).status_code, 403)
        self.client.force_login(self.landlord)
        self.client.post(reverse('tenant_remove', args=[profile.pk]))
        profile.refresh_from_db()
        self.assertIsNone(profile.current_property)

    def test_process_bills_marks_overdue_and_generates_recurring(self):
        today = timezone.now().date()
        self.assign(self.tenant1)
        bill = Bill.objects.get(user=self.tenant1)
        bill.due_date = today - timedelta(days=40)
        bill.save()

        call_command('process_bills', stdout=StringIO())
        bill.refresh_from_db()
        self.assertEqual(bill.status, 'overdue')

        # recurring monthly: next month's bill exists exactly once, even after a re-run
        call_command('process_bills', stdout=StringIO())
        nxt = Bill.objects.filter(user=self.tenant1, bill_type='rent').exclude(pk=bill.pk)
        self.assertTrue(nxt.exists())
        self.assertEqual(nxt.filter(due_date__gt=bill.due_date).count(), nxt.count())
        count = Bill.objects.count()
        call_command('process_bills', stdout=StringIO())
        self.assertEqual(Bill.objects.count(), count)


@override_settings(STORAGES=TEST_STORAGES, ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False, FORMGUARD_ENABLED=False, RATELIMIT_ENABLED=False)
class UnifiedLedgerTests(TestCase):
    """Invoice payments and confirmed tenant bill payments must both count
    everywhere money-in is reported."""

    def setUp(self):
        from clients.models import Client
        from contracts.models import Contract
        from payments.models import Invoice, Payment as InvoicePayment

        self.landlord = make_user('landlord', 'owner', verified_owner=True)
        self.other = make_user('other', 'owner', verified_owner=True)
        self.tenant = make_user('tenant')
        self.prop = make_property(self.landlord, 'Block A')
        today = timezone.now().date()

        # System 1: landlord-recorded invoice payment, KES 10,000 cash
        client = Client.objects.create(name='Walk In', email='w@x.com', phone='254700000001')
        contract = Contract.objects.create(
            contract_number='C1', contract_type='rental', property=self.prop, client=client,
            start_date=today, end_date=today + timedelta(days=365))
        invoice = Invoice.objects.create(
            contract=contract, client=client, property=self.prop, amount=Decimal('10000'), due_date=today,
            period_start=today, period_end=today)
        InvoicePayment.objects.create(
            invoice=invoice, client=client, amount=10000, payment_method='cash', payment_date=today)

        # System 2: tenant bill payment confirmed by the landlord, KES 25,000 M-Pesa
        bill = Bill.objects.create(property=self.prop, user=self.tenant, bill_type='rent',
                                   description='Rent', amount=25000, due_date=today)
        pay = Payment.objects.create(user=self.tenant, bill=bill, amount=25000,
                                     payment_method='mpesa', payment_status='pending')
        pay.mark_completed('QK1')

    def test_ledger_totals_methods_and_scoping(self):
        from payments import ledger
        self.assertEqual(ledger.collected(self.landlord), Decimal('35000'))
        self.assertEqual(ledger.collected(self.other), Decimal('0'))
        self.assertEqual({m['payment_method']: m['total'] for m in ledger.by_method(self.landlord)},
                         {'cash': Decimal('10000'), 'mpesa': Decimal('25000')})
        today = timezone.now().date()
        self.assertEqual(ledger.collected(self.landlord, payment_date=today), Decimal('35000'))
        self.assertEqual(ledger.count(self.landlord, payment_date=today), 2)
        self.assertEqual(len(ledger.recent(self.landlord, 5)), 2)
        self.assertEqual(ledger.by_property(self.landlord)[0]['total'], Decimal('35000'))

    def test_pages_show_combined_revenue(self):
        self.client.force_login(self.landlord)
        self.assertEqual(self.client.get(reverse('dashboard')).context['revenue_current_value'], 'KSh 35,000.00')
        self.assertEqual(self.client.get(reverse('property_list')).context['total_revenue'], Decimal('35000'))
        self.assertEqual(self.client.get(reverse('payment_list')).context['total_amount'], Decimal('35000'))
        self.assertEqual(self.client.get(reverse('report_list')).status_code, 200)

    def test_reports_include_both(self):
        from Report.models import Report
        today = timezone.now().date().isoformat()
        self.client.force_login(self.landlord)

        self.client.post(reverse('daily_report'), {'report_date': today})
        daily = Report.objects.get(report_type='daily')
        self.assertEqual(daily.status, 'completed', daily.report_data)
        self.assertEqual(daily.total_revenue, Decimal('35000'))
        self.assertEqual(daily.report_data['summary']['daily_transactions'], 2)
        self.assertEqual(daily.report_data['top_properties'][0]['revenue'], 35000.0)

        self.client.post(reverse('report_generate'), {
            'report_type': 'custom', 'title': 'Custom', 'description': '',
            'start_date': today, 'end_date': today,
        })
        custom = Report.objects.get(report_type='custom')
        self.assertEqual(custom.status, 'completed')
        self.assertEqual(custom.total_revenue, Decimal('35000'))

        self.client.force_login(self.other)
        self.client.post(reverse('daily_report'), {'report_date': today})
        self.assertEqual(Report.objects.get(generated_by=self.other).total_revenue, Decimal('0'))


@override_settings(STORAGES=TEST_STORAGES, ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False, FORMGUARD_ENABLED=False, RATELIMIT_ENABLED=False)
class RecurringBacklogTests(TestCase):
    def setUp(self):
        self.landlord = make_user('landlord', 'owner', verified_owner=True)
        self.tenant = make_user('tenant')
        self.prop = make_property(self.landlord, 'Block A')
        Profile.objects.filter(user=self.tenant).update(current_property=self.prop)

    def make_bill(self, days_ago, interval='monthly'):
        return Bill.objects.create(
            property=self.prop, user=self.tenant, bill_type='rent', description='Rent', amount=1000,
            due_date=timezone.now().date() - timedelta(days=days_ago), is_recurring=True,
            recurrence_interval=interval)

    def run_cmd(self):
        call_command('process_bills', stdout=StringIO())

    def test_every_missed_month_is_backfilled_once(self):
        from clients.management.commands.process_bills import add_periods
        first = self.make_bill(days_ago=100)
        self.run_cmd()
        bills = list(Bill.objects.filter(user=self.tenant).order_by('due_date'))
        expected = [add_periods(first.due_date, 'monthly', k) for k in range(0, 4)]
        expected = [d for d in expected if d <= timezone.now().date()]
        self.assertEqual([b.due_date for b in bills], expected)
        self.assertGreaterEqual(len(bills), 4)  # 100 days is always at least 3 missed months
        # all past-due ones are overdue, and only the newest keeps recurring
        self.assertTrue(all(b.status == 'overdue' for b in bills))
        self.assertEqual([b.is_recurring for b in bills], [False] * (len(bills) - 1) + [True])
        self.run_cmd()  # idempotent
        self.assertEqual(Bill.objects.filter(user=self.tenant).count(), len(bills))

    def test_no_drift_on_month_end(self):
        from datetime import date
        from clients.management.commands.process_bills import add_periods
        self.assertEqual(add_periods(date(2026, 1, 31), 'monthly', 1), date(2026, 2, 28))
        self.assertEqual(add_periods(date(2026, 1, 31), 'monthly', 2), date(2026, 3, 31))
        self.assertEqual(add_periods(date(2026, 1, 15), 'quarterly', 1), date(2026, 4, 15))
        self.assertEqual(add_periods(date(2026, 1, 15), 'weekly', 2), date(2026, 1, 29))

    def test_moved_out_tenant_stops_being_billed(self):
        bill = self.make_bill(days_ago=100)
        Profile.objects.filter(user=self.tenant).update(current_property=None)
        self.run_cmd()
        self.assertEqual(Bill.objects.filter(user=self.tenant).count(), 1)
        bill.refresh_from_db()
        self.assertFalse(bill.is_recurring)


@override_settings(STORAGES=TEST_STORAGES, ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False, FORMGUARD_ENABLED=False, RATELIMIT_ENABLED=False)
class InvoiceRetirementTests(TestCase):
    """Bills are the one billing system: invoices are read-only history, and
    `migrate_invoices_to_bills` moves them over without double counting."""

    def setUp(self):
        from clients.models import Client
        from contracts.models import Contract
        from payments.models import Invoice, Payment as InvoicePayment

        self.landlord = make_user('landlord', 'owner', verified_owner=True)
        self.tenant = make_user('tenant')
        self.prop = make_property(self.landlord, 'Block A')
        today = timezone.now().date()
        account_client = Client.objects.create(user=self.tenant, name='Tenant', email='tenant@example.com',
                                               phone='254700000002')
        walk_in = Client.objects.create(name='Walk In', email='w@x.com', phone='254700000001')

        def invoice(client, number, total, status, paid):
            contract = Contract.objects.create(
                contract_number='C-' + number, contract_type='rental', property=self.prop, client=client,
                start_date=today, end_date=today + timedelta(days=365))
            inv = Invoice.objects.create(
                invoice_number=number, contract=contract, client=client, property=self.prop,
                amount=Decimal(total), due_date=today, period_start=today, period_end=today, status=status)
            if paid:
                InvoicePayment.objects.create(invoice=inv, client=client, amount=Decimal(paid),
                                              payment_method='cash', payment_date=today)
            return inv

        self.paid = invoice(account_client, 'INV-PAID', '10000', 'paid', '10000')
        self.partial = invoice(walk_in, 'INV-PART', '8000', 'partial', '3000')
        self.open = invoice(account_client, 'INV-OPEN', '5000', 'pending', None)

    def test_legacy_mutations_redirect_to_bills(self):
        self.client.force_login(self.landlord)
        for name, args, target in [('invoice_add', [], 'bill_create'), ('invoice_edit', [self.open.pk], 'bill_list'),
                                   ('invoice_delete', [self.open.pk], 'bill_list'),
                                   ('payment_add_for_invoice', [self.open.pk], 'bill_list')]:
            for method in (self.client.get, self.client.post):
                self.assertRedirects(method(reverse(name, args=args)), reverse(target))
        self.assertEqual(self.open.__class__.objects.filter(pk=self.open.pk).count(), 1)
        # history stays readable
        for name, args in [('invoice_list', []), ('invoice_detail', [self.paid.pk]), ('payment_list', [])]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('invoice_add')).status_code, 302)
        self.assertIn('login', self.client.get(reverse('invoice_add'))['Location'])

    def test_migration_moves_everything_without_double_counting(self):
        from payments import ledger
        before = ledger.collected(self.landlord)
        self.assertEqual(before, Decimal('13000'))

        call_command('migrate_invoices_to_bills', '--dry-run', stdout=StringIO())
        self.assertEqual(Bill.objects.count(), 0)

        call_command('migrate_invoices_to_bills', stdout=StringIO())
        self.assertEqual(Bill.objects.count(), 3)
        self.assertEqual(ledger.collected(self.landlord), before)  # same money, counted once

        paid = Bill.objects.get(reference_number='INV-PAID')
        self.assertEqual((paid.status, paid.user), ('paid', self.tenant))
        part = Bill.objects.get(reference_number='INV-PART')
        self.assertEqual((part.status, part.amount), ('pending', Decimal('5000.00')))
        self.assertEqual(part.user, self.landlord)             # off-platform client held by the owner,
        self.assertIn('Walk In', part.description)             # never shown to other residents
        self.assertEqual(part.payments.get().payment_status, 'completed')

        self.open.refresh_from_db()
        self.assertEqual(self.open.status, 'cancelled')        # superseded by its bill
        self.assertEqual(self.open.migrated_bill.amount, Decimal('5000.00'))

        # tenant sees their migrated bills, not the walk-in's
        self.client.force_login(self.tenant)
        Profile.objects.filter(user=self.tenant).update(current_property=self.prop)
        refs = {b.reference_number for b in self.client.get(reverse('my_profile')).context['bills']}
        self.assertEqual(refs, {'INV-PAID', 'INV-OPEN'})

        # landlord's tenant portal page for the old invoice links to the bill
        self.client.force_login(self.landlord)
        self.assertContains(self.client.get(reverse('invoice_detail', args=[self.open.pk])), 'Open Bill')

        call_command('migrate_invoices_to_bills', stdout=StringIO())  # idempotent
        self.assertEqual(Bill.objects.count(), 3)
        self.assertEqual(ledger.collected(self.landlord), before)


@override_settings(STORAGES=TEST_STORAGES, ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False, FORMGUARD_ENABLED=False, RATELIMIT_ENABLED=False)
class ServicesDirectoryTests(TestCase):
    def register(self, **extra):
        data = {
            'username': 'fundi1', 'email': 'fundi1@example.com', 'first_name': 'Juma', 'last_name': 'Otieno',
            'password': 'Str0ng!pass99', 'confirm_password': 'Str0ng!pass99', 'phone_number': '0712345678',
            'city': 'Nairobi', 'role': 'provider', 'service_category': 'plumber', 'agree_terms': 'on',
        }
        data.update(extra)
        return self.client.post(reverse('register'), data)

    def test_provider_signup_and_public_directory(self):
        self.assertEqual(self.client.get(reverse('register')).status_code, 200)
        # a provider must say what they do
        r = self.register(service_category='')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username='fundi1').exists())

        self.register()
        profile = Profile.objects.get(user__username='fundi1')
        self.assertEqual((profile.role, profile.service_category), ('provider', 'plumber'))
        profile.provider_bio = 'Fixing leaks since 2015'
        profile.is_active = True
        profile.save()
        self.client.logout()

        # public - no login needed
        r = self.client.get(reverse('home:services'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Juma')
        self.assertContains(self.client.get(reverse('home:services') + '?category=plumber'), 'Juma')
        self.assertNotContains(self.client.get(reverse('home:services') + '?category=electrician'), 'Fixing leaks')
        self.assertContains(self.client.get(reverse('home:services') + '?q=leaks'), 'Juma')
        self.assertEqual(self.client.get(reverse('home:services') + '?category=bogus').status_code, 200)

        # non-providers and category-less accounts never appear
        other = make_user('hunter1')
        self.assertNotContains(self.client.get(reverse('home:services')), 'hunter1')

        # landing page links to it
        self.assertContains(self.client.get(reverse('home:home')), reverse('home:services'))


@override_settings(STORAGES=TEST_STORAGES, ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False, FORMGUARD_ENABLED=False, RATELIMIT_ENABLED=False)
class ServiceBookingFlowTests(TestCase):
    def setUp(self):
        self.provider = make_user('fundi', 'provider')
        Profile.objects.filter(user=self.provider).update(
            service_category='plumber', full_name='Juma Fundi', phone_number='0712345678',
            provider_lat=Decimal('-1.292100'), provider_lng=Decimal('36.821900'),
            provider_location_label='Kilimani',
        )
        self.customer = make_user('mama')
        self.stranger = make_user('stranger')
        self.valid = {'description': 'Kitchen sink is leaking badly', 'address': 'Kilimani, Apt 4B',
                      'phone': '0722000111', 'preferred_time': 'morning'}

    def book(self, user=None, **over):
        self.client.force_login(user or self.customer)
        return self.client.post(reverse('home:service_request_create', args=['fundi']), {**self.valid, **over})

    def test_map_data_and_pages(self):
        r = self.client.get(reverse('home:services_map_data'))
        data = r.json()['providers']
        self.assertEqual([(p['username'], p['lat'], p['rating']) for p in data], [('fundi', -1.2921, None)])
        self.assertEqual(self.client.get(reverse('home:services_map_data') + '?category=cleaner').json()['providers'], [])
        for name in ('home:services_map', 'home:services'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        r = self.client.get(reverse('home:provider_detail', args=['fundi']))
        self.assertContains(r, 'Juma Fundi')
        self.assertContains(r, 'Log in to send a request')
        self.assertEqual(self.client.get(reverse('home:provider_detail', args=['mama'])).status_code, 404)

    def test_booking_validation_and_access(self):
        self.client.logout()
        r = self.client.post(reverse('home:service_request_create', args=['fundi']), self.valid)
        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r['Location'])

        self.book(description='short')
        self.assertEqual(ServiceRequest.objects.count(), 0)
        self.book(user=self.provider)  # can't book yourself
        self.assertEqual(ServiceRequest.objects.count(), 0)
        self.book()
        self.book()  # duplicate pending is ignored
        self.assertEqual(ServiceRequest.objects.count(), 1)

    def test_full_lifecycle_with_review(self):
        self.book()
        job = ServiceRequest.objects.get()
        act = lambda user, name: (self.client.force_login(user), self.client.post(
            reverse('home:service_request_action', args=[job.pk, name]), {'note': 'KES 1,500, 10am'}))[1]

        # only the provider can accept; a stranger and the customer cannot
        self.assertEqual(act(self.stranger, 'accept').status_code, 403)
        self.assertEqual(act(self.customer, 'accept').status_code, 403)
        self.assertEqual(act(self.provider, 'complete').status_code, 403)  # not accepted yet
        act(self.provider, 'accept')
        job.refresh_from_db()
        self.assertEqual((job.status, job.provider_note), ('accepted', 'KES 1,500, 10am'))

        # no review before the job is done, nor by anyone but the customer
        review_url = reverse('home:service_review', args=[job.pk])
        self.client.force_login(self.customer)
        self.client.post(review_url, {'rating': 5})
        self.assertEqual(ServiceReview.objects.count(), 0)

        act(self.provider, 'complete')
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.post(review_url, {'rating': 5}).status_code, 404)
        self.client.force_login(self.customer)
        self.client.post(review_url, {'rating': 9})            # invalid
        self.assertEqual(ServiceReview.objects.count(), 0)
        self.client.post(review_url, {'rating': 4, 'comment': 'Fixed it fast'})
        self.client.post(review_url, {'rating': 1})             # second review ignored
        self.assertEqual(ServiceReview.objects.get().rating, 4)

        # rating now shows on the map feed, directory and provider page
        p = self.client.get(reverse('home:services_map_data')).json()['providers'][0]
        self.assertEqual((p['rating'], p['reviews']), (4.0, 1))
        self.assertContains(self.client.get(reverse('home:provider_detail', args=['fundi'])), 'Fixed it fast')
        self.assertContains(self.client.get(reverse('home:services')), '4.0')

        # both sides see it on their requests page; a customer can cancel only their own pending job
        self.assertEqual(self.client.get(reverse('home:my_service_requests')).status_code, 200)
        self.client.force_login(self.provider)
        self.assertContains(self.client.get(reverse('home:my_service_requests')), 'Kitchen sink')

    def test_cancel_and_decline(self):
        self.book()
        job = ServiceRequest.objects.get()
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.post(reverse('home:service_request_action', args=[job.pk, 'cancel'])).status_code, 403)
        self.client.force_login(self.customer)
        self.client.post(reverse('home:service_request_action', args=[job.pk, 'cancel']))
        job.refresh_from_db()
        self.assertEqual(job.status, 'cancelled')
        self.assertEqual(self.client.post(reverse('home:service_request_action', args=[job.pk, 'bogus'])).status_code, 404)

    def test_provider_can_set_location_in_profile_form(self):
        from users.forms import ProfileForm
        form = ProfileForm(instance=self.provider.profile)
        for f in ('provider_lat', 'provider_lng', 'provider_location_label', 'service_category'):
            self.assertIn(f, form.fields)

    def test_header_is_transparent_over_hero_on_landing(self):
        html = self.client.get(reverse('home:home')).content.decode()
        self.assertIn('class="navbar transparent over-hero"', html)
        self.assertNotIn('over-hero', self.client.get(reverse('home:properties')).content.decode().split('<nav class="navbar')[1][:60])


@override_settings(STORAGES=TEST_STORAGES, ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False, FORMGUARD_ENABLED=False, RATELIMIT_ENABLED=False,
                   SITE_URL='https://example.test', SITE_NAME='BrandX')
class SeoTests(TestCase):
    def setUp(self):
        self.provider = make_user('fundi', 'provider')
        Profile.objects.filter(user=self.provider).update(
            service_category='plumber', full_name='Juma Fundi', city='Nairobi', provider_bio='Fixing leaks',
            provider_lat=Decimal('-1.292100'), provider_lng=Decimal('36.821900'))
        self.customer = make_user('mama')

    def html(self, url):
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200, url)
        return r.content.decode()

    def test_canonical_is_the_pages_own_url_not_the_homepage(self):
        # a page that overrides nothing must self-canonicalise (was: always the homepage)
        self.assertIn('rel="canonical" href="https://example.test/contact/"', self.html('/contact/'))
        self.assertIn('og:url" content="https://example.test/contact/"', self.html('/contact/'))
        self.assertIn('og:site_name" content="BrandX"', self.html('/'))

    def test_homepage_matches_the_product(self):
        h = self.html('/')
        self.assertIn('<title>BrandX – Find Homes, Collect Rent', h)
        self.assertIn('plumbers', h.split('name="description"')[1][:400])
        self.assertIn('"@type": "FAQPage"', h)
        self.assertEqual(h.count('<h1'), 1)
        self.assertNotIn('https://2hame.com', h)  # no hardcoded domain left

    def test_service_pages(self):
        h = self.html('/services/?category=plumber')
        self.assertIn('Plumbers in Kenya', h.split('<title>')[1].split('</title>')[0])
        self.assertIn('href="https://example.test/services/?category=plumber"', h)
        self.assertIn('BreadcrumbList', h)
        self.assertIn('noindex', self.html('/services/?q=leak'))     # internal search results aren't indexed
        self.assertNotIn('noindex', self.html('/services/?category=plumber').split('name="robots"')[1][:80])

    def test_provider_page_schema_uses_only_real_ratings(self):
        import json, re
        url = reverse('home:provider_detail', args=['fundi'])
        def schema(h):
            blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)
            return [json.loads(b) for b in blocks if '"ProfessionalService"' in b][0]

        before = schema(self.html(url))
        self.assertEqual(before['name'], 'Juma Fundi')
        self.assertEqual(before['geo']['latitude'], -1.2921)
        self.assertNotIn('aggregateRating', before)                   # no fake rating before any review

        job = ServiceRequest.objects.create(provider=self.provider, requester=self.customer, description='Fix sink now',
                                            address='x', phone='0700000000', status='completed')
        ServiceReview.objects.create(request=job, provider=self.provider, reviewer=self.customer, rating=5, comment='Great')
        after = schema(self.html(url))
        self.assertEqual(after['aggregateRating']['ratingValue'], '5.0')
        self.assertEqual(after['aggregateRating']['reviewCount'], '1')
        self.assertEqual(after['review'][0]['reviewBody'], 'Great')
        self.assertIn('rel="canonical" href="https://example.test/services/provider/fundi/"', self.html(url))

    def test_sitemap_and_robots(self):
        sm = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('https://example.test/services/provider/fundi/', sm)
        self.assertIn('category=plumber', sm)
        self.assertIn('/services/map/', sm)
        self.assertNotIn('category=electrician', sm)                  # no empty category pages
        robots = self.client.get('/robots.txt').content.decode()
        self.assertIn('Sitemap: https://example.test/sitemap.xml', robots)
        self.assertIn('Disallow: /services/requests/', robots)
        self.assertIn('noindex', self.html('/users/login/'))


@override_settings(STORAGES=TEST_STORAGES, ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False, FORMGUARD_ENABLED=False, RATELIMIT_ENABLED=False,
                   SITE_URL='https://example.test', SITE_NAME='BrandX')
class OwnerPublicProfileTests(TestCase):
    def setUp(self):
        self.owner = make_user('landlord', 'owner', verified_owner=True)
        Profile.objects.filter(user=self.owner).update(
            owner_brand_name='Acme Homes', owner_tagline='Homes chosen with care', bio='We list verified homes.',
            owner_whatsapp_number='254712345678', phone_number='0712345678', city='Nairobi')
        self.p1 = make_property(self.owner, 'Garden Villa')
        self.p2 = make_property(self.owner, 'City Studio')
        Property.objects.filter(pk=self.p2.pk).update(city='Mombasa', price=Decimal('9000'))
        self.url = reverse('home:owner_portfolio', args=['landlord'])

    def test_new_design_renders_with_real_data(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn('cdn.tailwindcss.com', html)           # the new Tailwind design, not the old stylesheet
        self.assertNotIn('public-profile.css', html)
        for needle in ('Acme Homes', 'Homes chosen with care', 'Garden Villa', 'City Studio', 'Our Story',
                       'Got questions?', 'Testimonials', 'wa.me/254712345678'):
            self.assertIn(needle, html)
        self.assertIn('rel="canonical" href="https://example.test/owners/landlord/"', html)
        self.assertIn('Example', html)                       # clearly-labelled sample reviews while none exist
        self.assertEqual(html.count('<h1'), 1)

    def test_filters_search_and_pagination_still_work(self):
        titles = lambda q: {p.title for p in self.client.get(self.url + q).context['properties']}
        self.assertEqual(titles('?search=villa'), {'Garden Villa'})
        self.assertEqual(titles('?city=Mombasa'), {'City Studio'})
        self.assertEqual(titles('?price_max=10000'), {'City Studio'})
        self.assertEqual(titles(''), {'Garden Villa', 'City Studio'})
        self.assertContains(self.client.get(self.url + '?search=nomatch'), 'No properties match')

    def test_contact_form_posts_to_the_owner(self):
        from home.models import ContactMessage
        r = self.client.post(reverse('home:owner_portfolio_contact', args=['landlord']), {
            'name': 'Visitor', 'email': 'v@example.com', 'message': 'Is the villa available?'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(ContactMessage.objects.get().owner, self.owner)
        self.assertIn('class="field"', self.client.get(self.url).content.decode())

    def test_reviews_show_real_ratings_and_owner_links(self):
        from properties.models import PropertyReview
        PropertyReview.objects.create(property=self.p1, user=self.owner_visitor(), rating=5, comment='Wonderful stay')
        html = self.client.get(self.url).content.decode()
        self.assertIn('Wonderful stay', html)
        self.assertIn('"aggregateRating"', html)
        self.assertNotIn('>Example<', html)
        self.assertNotIn(reverse('dashboard'), html)         # dashboard link is owner-only
        self.client.force_login(self.owner)
        self.assertIn(reverse('dashboard'), self.client.get(self.url).content.decode())

    def owner_visitor(self):
        return make_user('visitor')



# ─────────────────────────────────────────────────────────────────────────────
# Security: lead popup, rate limiting, bot guard, login lockout
# ─────────────────────────────────────────────────────────────────────────────
import time as _time
from unittest import mock

from django.test import Client as DjangoClient

from home.models import Lead
from Tuhame import formguard


def fresh_token(age=10):
    """A valid guard token that looks `age` seconds old."""
    with mock.patch('Tuhame.formguard.time.time', return_value=_time.time() - age):
        return formguard.issue_token()


LEAD = {'name': 'Jane Wanjiru', 'phone': '0712 345 678', 'email': 'Jane@Example.com', 'interest': 'rent',
        'location': 'Kilimani', 'budget': 'KES 45,000', 'message': 'Two bedrooms please', 'consent': 'on'}


@override_settings(STORAGES=TEST_STORAGES, ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False,
                   SITE_URL='https://example.test', SITE_NAME='BrandX')
class LeadPopupTests(TestCase):
    url = '/lead/submit/'

    def post(self, data=None, client=None, token=True, **extra):
        c = client or self.client
        payload = {**LEAD, **(data or {})}
        if token:
            payload['_fg'] = fresh_token()
        return c.post(self.url, payload, HTTP_X_REQUESTED_WITH='XMLHttpRequest', **extra)

    def test_popup_is_on_every_load_of_the_landing_page_only(self):
        for _ in range(3):  # "every refresh"
            html = self.client.get('/').content.decode()
            self.assertIn('id="lead-dialog"', html)
            self.assertIn('showModal', html)
            self.assertIn('name="_fg"', html)
            self.assertIn('name="website_url"', html)
        self.assertNotIn('lead-dialog', self.client.get('/contact/').content.decode())
        self.assertNotIn('lead-dialog', self.client.get('/properties/listing/').content.decode()
                         if False else self.client.get('/services/').content.decode())

    def test_valid_submission_saves_a_clean_lead_and_returns_success(self):
        r = self.post()
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body['ok'])
        self.assertIn('Thank you, Jane', body['message'])
        lead = Lead.objects.get()
        self.assertEqual((lead.name, lead.phone, lead.email, lead.interest, lead.budget),
                         ('Jane Wanjiru', '254712345678', 'jane@example.com', 'rent', 45000))
        self.assertTrue(lead.consent)
        self.assertEqual(len(lead.ip_hash), 64)               # hashed, not a raw IP address
        self.assertNotIn('127.0.0.1', lead.ip_hash)

    def test_phone_accepts_the_formats_people_actually_type(self):
        from home.forms import normalize_ke_phone
        for raw in ('712 345 678', '0712 345 678', '+254 712 345 678', '254712345678', '0712-345-678', '112345678'):
            self.assertTrue(normalize_ke_phone(raw).startswith('254'), raw)
        self.assertEqual(normalize_ke_phone('712 345 678'), '254712345678')
        for bad in ('abc', '123', '', '07123'):
            self.assertIsNone(normalize_ke_phone(bad), bad)

    def test_popup_is_two_short_steps_with_only_name_and_phone_required(self):
        html = self.client.get('/').content.decode()
        dialog = html.split('id="lead-dialog"')[1].split('</dialog>')[0]
        self.assertIn('data-step="1"', dialog)
        self.assertIn('data-step="2"', dialog)
        self.assertEqual(dialog.count('name="interest"'), 6)
        self.assertIn('name="consent"', dialog)
        # the extras live behind the optional toggle, not in the main flow
        before_toggle = dialog.split('id="lead-more"')[0]
        for optional in ('name="email"', 'name="location"', 'name="budget"', 'name="message"'):
            self.assertNotIn(optional, before_toggle)
            self.assertIn(optional, dialog)

    def test_resubmitting_the_same_request_does_not_duplicate(self):
        self.post(); self.post()
        self.assertEqual(Lead.objects.count(), 1)

    @override_settings(RATELIMIT_ENABLED=False)   # this test fires many bad submissions on purpose
    def test_validation_rejects_bad_input_with_field_errors(self):
        cases = {
            'name': {'name': 'x'}, 'phone': {'phone': 'abc'}, 'email': {'email': 'not-an-email'},
            'budget': {'budget': 'lots'}, 'interest': {'interest': 'hack'},
            'message': {'message': 'see http://a.com and http://b.com'},
        }
        for field, bad in cases.items():
            r = self.post(bad)
            self.assertEqual(r.status_code, 400, field)
            self.assertIn(field, r.json()['fields'])
        payload = {k: v for k, v in LEAD.items() if k != 'consent'}
        r = self.client.post(self.url, {**payload, '_fg': fresh_token()}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertIn('consent', r.json()['fields'])
        self.assertEqual(Lead.objects.count(), 0)

    def test_output_is_escaped_and_html_never_trusted(self):
        self.post({'name': '<script>alert(1)</script> Eve', 'message': '<img src=x onerror=alert(1)>'})
        lead = Lead.objects.get()
        from django.template import Template, Context
        rendered = Template('{{ l.name }}|{{ l.message }}').render(Context({'l': lead}))
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('<img', rendered)

    def test_csrf_is_enforced(self):
        strict = DjangoClient(enforce_csrf_checks=True)
        r = self.post(client=strict)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Lead.objects.count(), 0)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    @override_settings(RATELIMIT_ENABLED=False)   # isolate the bot guard from the limiter
    def test_bots_are_rejected(self):
        # honeypot filled
        self.assertEqual(self.post({'website_url': 'http://spam.example'}).status_code, 400)
        # no token at all
        self.assertEqual(self.post(token=False).status_code, 400)
        # forged token
        self.assertEqual(self.client.post(self.url, {**LEAD, '_fg': 'forged:token'}).status_code, 400)
        # submitted instantly (script speed)
        quick = self.client.post(self.url, {**LEAD, '_fg': fresh_token(age=0)}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(quick.status_code, 400)
        # a token from long ago (page left open for a day)
        old = self.client.post(self.url, {**LEAD, '_fg': fresh_token(age=7 * 3600)})
        self.assertEqual(old.status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)

    def test_rate_limit_blocks_the_fourth_attempt_in_ten_minutes(self):
        for i in range(3):
            r = self.post({'phone': f'07123456{i}0', 'interest': 'rent'})
            self.assertEqual(r.status_code, 200, i)
        r = self.post({'phone': '0799999999'})
        self.assertEqual(r.status_code, 429)
        self.assertFalse(r.json()['ok'])
        self.assertIn('try again in', r.json()['error'])
        self.assertTrue(int(r['Retry-After']) > 0)
        self.assertEqual(Lead.objects.count(), 3)

    def test_rate_limit_is_per_ip_and_forwarded_header_cannot_dodge_it(self):
        for i in range(3):
            self.post({'phone': f'07123456{i}0'})
        # a forged X-Forwarded-For must not give a fresh allowance (proxy hops = 0)
        r = self.post({'phone': '0788888888'}, HTTP_X_FORWARDED_FOR='9.9.9.9')
        self.assertEqual(r.status_code, 429)
        # a genuinely different client address is counted separately
        other = DjangoClient(REMOTE_ADDR='10.1.2.3')
        self.assertEqual(self.post({'phone': '0722222222'}, client=other).status_code, 200)

    @override_settings(RATELIMIT_PROXY_HOPS=1)
    def test_trusted_proxy_uses_the_right_most_forwarded_ip(self):
        from Tuhame.ratelimit import client_ip
        from django.test import RequestFactory
        req = RequestFactory().get('/', HTTP_X_FORWARDED_FOR='6.6.6.6, 203.0.113.7', REMOTE_ADDR='10.0.0.1')
        self.assertEqual(client_ip(req), '203.0.113.7')      # the hop our proxy added, not the forgeable left-most one

    def test_html_form_posts_get_a_readable_429_page(self):
        for i in range(3):
            self.post({'phone': f'07123456{i}0'})
        r = self.client.post(self.url, {**LEAD, '_fg': fresh_token(), 'phone': '0700000001'})
        self.assertEqual(r.status_code, 429)
        self.assertContains(r, 'Too many attempts', status_code=429)


@override_settings(STORAGES=TEST_STORAGES, ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False,
                   SITE_URL='https://example.test', SITE_NAME='BrandX')
class FormSecurityEverywhereTests(TestCase):
    """Rate limits and the bot guard apply to the OTHER forms too, centrally."""

    def setUp(self):
        self.owner = make_user('landlord', 'owner', verified_owner=True)
        self.user = make_user('tenant')

    def test_every_public_form_page_carries_the_guard(self):
        for url in ('/contact/', '/users/login/', '/users/register/', '/users/password-reset/',
                    reverse('home:owner_portfolio', args=['landlord'])):
            html = self.client.get(url).content.decode()
            self.assertIn('name="_fg"', html, url)
            self.assertIn('name="website_url"', html, url)

    def test_contact_form_rejects_bots_and_accepts_humans(self):
        data = {'name': 'Sam', 'email': 's@example.com', 'subject': 'general', 'message': 'Hello there team'}
        self.assertEqual(self.client.post('/contact/', data).status_code, 400)                     # no token
        self.assertEqual(self.client.post('/contact/', {**data, '_fg': fresh_token(), 'website_url': 'x'}).status_code, 400)
        ok = self.client.post('/contact/', {**data, '_fg': fresh_token()})
        self.assertEqual(ok.status_code, 302)

    def test_owner_contact_is_guarded(self):
        url = reverse('home:owner_portfolio_contact', args=['landlord'])
        data = {'name': 'V', 'email': 'v@example.com', 'message': 'Is it free?'}
        self.assertEqual(self.client.post(url, data).status_code, 400)
        self.assertEqual(self.client.post(url, {**data, '_fg': fresh_token()}).status_code, 302)

    def test_registration_and_password_reset_are_rate_limited(self):
        for i in range(5):
            self.client.post('/users/register/', {'_fg': fresh_token(), 'username': 'x'})
        r = self.client.post('/users/register/', {'_fg': fresh_token(), 'username': 'x'})
        self.assertEqual(r.status_code, 429)
        for i in range(5):
            self.client.post('/users/password-reset/', {'_fg': fresh_token(), 'email': 'a@b.com'})
        self.assertEqual(self.client.post('/users/password-reset/', {'_fg': fresh_token(), 'email': 'a@b.com'}).status_code, 429)

    def test_any_other_post_hits_the_generic_cap(self):
        self.client.force_login(self.user)
        codes = [self.client.post('/clients/tenants/999/remove/').status_code for _ in range(65)]
        self.assertEqual(codes[:60].count(429), 0)
        self.assertEqual(codes[60:], [429] * 5)

    def test_per_user_limits_follow_the_account(self):
        self.client.force_login(self.user)
        url = '/clients/bills/1/pay/'
        codes = [self.client.post(url, {'payment_method': 'mpesa'}).status_code for _ in range(12)]
        self.assertEqual(codes[10:], [429, 429])

    def test_payment_gateway_callback_is_never_throttled(self):
        codes = {self.client.post('/settings/mpesa/subscription-callback/', data='{}', content_type='application/json').status_code
                 for _ in range(80)}
        self.assertNotIn(429, codes)

    def test_login_locks_out_password_guessing_even_for_the_right_password(self):
        user = make_user('victim')
        for i in range(5):
            r = self.client.post('/users/login/', {'username': 'victim', 'password': f'wrong{i}', '_fg': fresh_token()})
            self.assertEqual(r.status_code, 200)
        locked = self.client.post('/users/login/', {'username': 'victim', 'password': 'pass12345', '_fg': fresh_token()})
        self.assertEqual(locked.status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)
        # a different username from the same IP is unaffected
        make_user('bystander')
        ok = self.client.post('/users/login/', {'username': 'bystander', 'password': 'pass12345', '_fg': fresh_token()})
        self.assertEqual(ok.status_code, 302)

    def test_login_success_clears_the_failure_count(self):
        make_user('forgetful')
        for i in range(3):
            self.client.post('/users/login/', {'username': 'forgetful', 'password': 'bad', '_fg': fresh_token()})
        good = self.client.post('/users/login/', {'username': 'forgetful', 'password': 'pass12345', '_fg': fresh_token()})
        self.assertEqual(good.status_code, 302)
        self.client.logout()
        for i in range(4):  # would be locked if the earlier 3 still counted (3+4 > 5)
            r = self.client.post('/users/login/', {'username': 'forgetful', 'password': 'bad', '_fg': fresh_token()})
            self.assertEqual(r.status_code, 200)

    def test_security_can_be_switched_off_only_by_settings(self):
        with override_settings(RATELIMIT_ENABLED=False, FORMGUARD_ENABLED=False):
            r = self.client.post('/contact/', {'name': 'Sam', 'email': 's@example.com', 'subject': 'general', 'message': 'Hello there team'})
            self.assertEqual(r.status_code, 302)
