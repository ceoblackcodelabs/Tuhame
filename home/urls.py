from django.urls import path
from .views import *

app_name = "home"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("properties/listing/", PropertiesListView.as_view(), name="properties"),
    path("property/listing/<slug:slug>/", PropertiesDetailView.as_view(), name="about_property"),
    path("property/map-list/", PropertyMapSearchListView.as_view(), name="property_map"),
    path('property/map-data/', PropertyMapDataView.as_view(), name='property_map_data'),
]
