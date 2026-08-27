# apps/subscriptions/urls.py
from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('', views.SettingsView.as_view(), name='settings'),
    path('offers/<int:pk>/claim/', views.ClaimOfferView.as_view(), name='claim_offer'),

    # Admin-only management
    path('offers/', views.OfferListView.as_view(), name='offer_list'),
    path('offers/add/', views.OfferCreateView.as_view(), name='offer_add'),
    path('offers/<int:pk>/edit/', views.OfferUpdateView.as_view(), name='offer_edit'),
    path('offers/<int:pk>/delete/', views.OfferDeleteView.as_view(), name='offer_delete'),
    path('plans/<int:pk>/edit/', views.PlanUpdateView.as_view(), name='plan_edit'),

    # M-Pesa STK Push - subscription payments
    path('plans/<int:pk>/pay/', views.SubscribeInitiateView.as_view(), name='subscribe_initiate'),
    path('mpesa/subscription-callback/', views.SubscriptionCallbackView.as_view(), name='subscription_callback'),
    path('payments/<int:pk>/status/', views.SubscriptionPaymentStatusView.as_view(), name='subscription_payment_status'),
]
