from django.contrib import admin
from .models import SubscriptionPlan, Offer, OfferClaim, OwnerSubscription


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
