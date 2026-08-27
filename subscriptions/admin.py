from django.contrib import admin
from .models import SubscriptionPlan, Offer, OfferClaim, OwnerSubscription, SubscriptionPayment


@admin.register(SubscriptionPlan)
class AdminSubscriptionPlan(admin.ModelAdmin):
    list_display = ('name', 'billing_period', 'price', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')


@admin.register(Offer)
class AdminOffer(admin.ModelAdmin):
    list_display = ('title', 'amount', 'max_claims', 'duration_months', 'is_active', 'created_at')
    list_editable = ('is_active',)


@admin.register(OfferClaim)
class AdminOfferClaim(admin.ModelAdmin):
    list_display = ('offer', 'user', 'claimed_at')


@admin.register(OwnerSubscription)
class AdminOwnerSubscription(admin.ModelAdmin):
    list_display = ('user', 'plan', 'source_offer', 'started_at', 'expires_at', 'is_active')


@admin.register(SubscriptionPayment)
class AdminSubscriptionPayment(admin.ModelAdmin):
    list_display = ('user', 'plan', 'amount', 'phone_number', 'status', 'mpesa_receipt_number', 'created_at')
    list_filter = ('status', 'plan')
    search_fields = ('user__username', 'user__email', 'phone_number', 'checkout_request_id', 'mpesa_receipt_number')
    readonly_fields = (
        'user', 'plan', 'checkout_request_id', 'merchant_request_id', 'mpesa_receipt_number',
        'amount', 'phone_number', 'result_code', 'result_desc', 'created_at', 'completed_at', 'callback_payload',
    )
