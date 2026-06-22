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
]