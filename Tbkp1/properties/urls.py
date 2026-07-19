# apps/properties/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('properties/', views.PropertyListView.as_view(), name='property_list'),
    path('add/', views.PropertyCreateView.as_view(), name='add_property'),
    path('<int:pk>/', views.PropertyDetailView.as_view(), name='property_detail'),
    path('<int:pk>/edit/', views.PropertyUpdateView.as_view(), name='property_edit'),
    path('<int:pk>/delete/', views.PropertyDeleteView.as_view(), name='property_delete'),

    path('<int:property_pk>/unit/add/', views.UnitCreateView.as_view(), name='unit_add'),

    path('bookings/', views.BookingListView.as_view(), name='booking_list'),
    path('bookings/add/', views.BookingCreateView.as_view(), name='booking_add'),

    # Geocoding endpoints
    path('geocode/', views.geocode_address, name='geocode_address'),
    path('reverse-geocode/', views.reverse_geocode, name='reverse_geocode'),

    # scheduling
    path('viewings/', views.ReviewListView.as_view(), name='schedule_view'),
    path('viewings/<int:pk>/', views.ViewingDetailView.as_view(), name='viewing_detail'),
    path('viewings/<int:pk>/edit/', views.ViewingUpdateView.as_view(), name='viewing_edit'),
    path('viewings/<int:pk>/confirm/', views.ConfirmViewingView.as_view(), name='confirm_viewing'),
    path('viewings/<int:pk>/cancel/', views.CancelViewingView.as_view(), name='cancel_viewing'),
    path('viewings/<int:pk>/complete/', views.CompleteViewingView.as_view(), name='complete_viewing'),
]