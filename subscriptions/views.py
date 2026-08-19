# apps/subscriptions/views.py
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from .models import SubscriptionPlan, Offer, OfferClaim, OwnerSubscription, BillingPeriod, add_months
from .forms import OfferForm, SubscriptionPlanForm


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
