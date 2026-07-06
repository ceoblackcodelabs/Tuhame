from django.urls import path
from .views import *
from .utils import toggle_save_property, get_saved_properties, check_saved_status

app_name = "home"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("properties/listing/", PropertiesListView.as_view(), name="properties"),
    path("property/listing/<slug:slug>/", PropertiesDetailView.as_view(), name="about_property"),
    path("property/map-list/", PropertyMapSearchListView.as_view(), name="property_map"),
    path('property/map-data/', PropertyMapDataView.as_view(), name='property_map_data'),

    # Review URLs
    path('property/listing/<slug:slug>/review/submit/', SubmitReviewView.as_view(), name='submit_review'),
    path('property/listing/<slug:slug>/review/edit/', EditReviewView.as_view(), name='edit_review'),
    path('property/listing/<slug:slug>/review/delete/', DeleteReviewView.as_view(), name='delete_review'),

    # Favourites/Saved Properties URLs
    path('api/save-property/', toggle_save_property, name='toggle_save_property'),
    path('api/saved-properties/', get_saved_properties, name='get_saved_properties'),
    path('api/check-saved/', check_saved_status, name='check_saved_status'),
]
