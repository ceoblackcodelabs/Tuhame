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
]
