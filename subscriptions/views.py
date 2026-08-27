# apps/subscriptions/views.py
import json
import logging

from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import SubscriptionPlan, Offer, OfferClaim, OwnerSubscription, SubscriptionPayment, BillingPeriod, add_months
from .forms import OfferForm, SubscriptionPlanForm
from .mpesa import initiate_subscription_stk_push

logger = logging.getLogger('mpesa')


def get_or_create_subscription(user):
    """Every owner effectively has a subscription - created lazily on first
    visit to Settings, defaulting to the Free plan, rather than via a signal
    (keeps this self-contained and easy to reason about)."""
    sub = getattr(user, 'subscription', None)
    if sub:
        return sub
    free_plan = SubscriptionPlan.objects.filter(billing_period=BillingPeriod.FREE).first()
    sub, _ = OwnerSubscription.objects.get_or_create(
        user=user, defaults={'plan': free_plan, 'started_at': timezone.now()}
    )
    return sub


class SettingsView(LoginRequiredMixin, View):
    template_name = 'subscriptions/settings.html'

    def get(self, request):
        from django.shortcuts import render
        subscription = get_or_create_subscription(request.user)
        plans = SubscriptionPlan.objects.filter(is_active=True)
        offers = []
        for offer in Offer.objects.filter(is_active=True):
            offer.claimed_by_user = offer.has_been_claimed_by(request.user)
            if offer.is_claimable() or offer.claimed_by_user:
                offers.append(offer)
        context = {
            'subscription': subscription,
            'plans': plans,
            'offers': offers,
        }
        return render(request, self.template_name, context)


class ClaimOfferView(LoginRequiredMixin, View):
    def post(self, request, pk):
        offer = get_object_or_404(Offer, pk=pk)

        if offer.has_been_claimed_by(request.user):
            messages.info(request, "You've already claimed this offer.")
            return redirect('subscriptions:settings')

        if not offer.is_claimable():
            messages.error(request, 'Sorry, this offer is no longer available.')
            return redirect('subscriptions:settings')

        OfferClaim.objects.create(offer=offer, user=request.user)

        subscription = get_or_create_subscription(request.user)
        now = timezone.now()
        subscription.plan = None
        subscription.source_offer = offer
        subscription.started_at = now
        subscription.expires_at = add_months(now, offer.duration_months)
        subscription.is_active = True
        subscription.save()

        messages.success(request, f'Offer claimed! Your access now runs until {subscription.expires_at.strftime("%d %b %Y")}.')
        return redirect('subscriptions:settings')


# ── Admin-only: manage Offers and edit Plan prices ──

class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class OfferListView(LoginRequiredMixin, SuperuserRequiredMixin, ListView):
    model = Offer
    template_name = 'subscriptions/offer_list.html'
    context_object_name = 'offers'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plans'] = SubscriptionPlan.objects.all()
        return context


class OfferCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = Offer
    form_class = OfferForm
    template_name = 'subscriptions/offer_form.html'
    success_url = reverse_lazy('subscriptions:offer_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Offer created.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Offer'
        context['submit_text'] = 'Create Offer'
        return context


class OfferUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = Offer
    form_class = OfferForm
    template_name = 'subscriptions/offer_form.html'
    success_url = reverse_lazy('subscriptions:offer_list')

    def form_valid(self, form):
        messages.success(self.request, 'Offer updated.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Offer'
        context['submit_text'] = 'Update Offer'
        return context


class OfferDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Offer
    success_url = reverse_lazy('subscriptions:offer_list')

    def post(self, request, *args, **kwargs):
        messages.success(request, 'Offer deleted.')
        return super().post(request, *args, **kwargs)


class PlanUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = SubscriptionPlan
    form_class = SubscriptionPlanForm
    template_name = 'subscriptions/plan_form.html'
    success_url = reverse_lazy('subscriptions:offer_list')

    def form_valid(self, form):
        messages.success(self.request, 'Plan updated.')
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# M-Pesa Daraja STK Push - subscription payments only
# ---------------------------------------------------------------------------

def normalize_phone(raw):
    """Safaricom wants 2547XXXXXXXX / 2541XXXXXXXX - no '+', no leading 0."""
    phone = str(raw or '').strip().replace(' ', '')
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    elif phone.startswith('+254'):
        phone = phone[1:]
    return phone


class SubscribeInitiateView(LoginRequiredMixin, View):
    """User-triggered: start an STK push for a plan. Rate-limited by being
    login-required (one push per authenticated user's own click) - the
    callback below is server-to-server from Safaricom and is NOT
    rate-limited the same way."""

    def post(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk, is_active=True)
        if plan.billing_period == BillingPeriod.FREE or not plan.price:
            messages.info(request, "That plan doesn't require payment.")
            return redirect('subscriptions:settings')

        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            payload = request.POST

        phone = normalize_phone(payload.get('phone_number'))
        if not phone.startswith(('2547', '2541', '2540', '2546')):
            return JsonResponse({'success': False, 'error': 'Enter a valid Safaricom number.'}, status=400)

        payment = SubscriptionPayment.objects.create(
            user=request.user, plan=plan, amount=plan.price, phone_number=phone,
        )

        if initiate_subscription_stk_push(payment):
            return JsonResponse({
                'success': True,
                'message': 'STK push sent — check your phone.',
                'payment_id': payment.id,
            })

        payment.refresh_from_db()
        return JsonResponse(
            {'success': False, 'error': payment.result_desc or 'Failed to initiate payment'}, status=500,
        )


@method_decorator(csrf_exempt, name='dispatch')
class SubscriptionCallbackView(View):
    """Server-to-server from Safaricom - always returns HTTP 200 with a
    ResultCode, even on error, since Safaricom's retry logic reacts badly
    to a raw 500 or a non-JSON response."""

    def post(self, request, *args, **kwargs):
        try:
            callback_data = json.loads(request.body or '{}')
            stk = callback_data.get('Body', {}).get('stkCallback', {})
            checkout_request_id = stk.get('CheckoutRequestID')
            result_code = stk.get('ResultCode')
            result_desc = stk.get('ResultDesc', '')

            if not checkout_request_id:
                return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Missing CheckoutRequestID'})

            try:
                payment = SubscriptionPayment.objects.get(checkout_request_id=checkout_request_id)
            except SubscriptionPayment.DoesNotExist:
                logger.error("SubscriptionPayment not found for %s", checkout_request_id)
                return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Transaction Not Found'})

            # Idempotency guard -- Safaricom retries callbacks that don't
            # get a fast, valid 200. Without this a retry double-processes
            # the same payment (e.g. double-extends the subscription).
            if payment.status != SubscriptionPayment.STATUS_PENDING:
                return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Already processed'})

            if result_code == 0:
                items = stk.get('CallbackMetadata', {}).get('Item', [])
                receipt = next((i.get('Value') for i in items if i.get('Name') == 'MpesaReceiptNumber'), None)
                if receipt:
                    payment.mark_completed(receipt_number=receipt, callback_data=callback_data)
                    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})
                payment.mark_failed(999, "Missing receipt", callback_data)
                return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Missing Receipt'})

            if result_code in (1032, 1037):
                payment.mark_cancelled(result_desc, callback_data)
            elif result_code == 2001:
                payment.mark_failed(2001, "Insufficient funds", callback_data)
            else:
                payment.mark_failed(result_code, result_desc, callback_data)

            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Failure'})

        except Exception as e:
            logger.error("Subscription M-Pesa callback error: %s", str(e))
            return JsonResponse({'ResultCode': 1, 'ResultDesc': f'Error: {str(e)}'})


class SubscriptionPaymentStatusView(LoginRequiredMixin, View):
    """Polled by the frontend every 2-3s while the STK prompt is pending on
    the user's phone. Reads local state only - never talks to Safaricom."""

    def get(self, request, pk):
        payment = get_object_or_404(SubscriptionPayment, pk=pk, user=request.user)
        return JsonResponse({
            'status': payment.status,
            'result_desc': payment.result_desc,
            'mpesa_receipt': payment.mpesa_receipt_number,
        })
