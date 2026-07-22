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
    path("contact/", ContactView.as_view(), name="contact"),

    # Review URLs
    path('property/listing/<slug:slug>/review/submit/', SubmitReviewView.as_view(), name='submit_review'),
    path('property/listing/<slug:slug>/review/edit/', EditReviewView.as_view(), name='edit_review'),
    path('property/listing/<slug:slug>/review/delete/', DeleteReviewView.as_view(), name='delete_review'),

    # Favourites/Saved Properties URLs
    path('api/save-property/', toggle_save_property, name='toggle_save_property'),
    path('api/saved-properties/', get_saved_properties, name='get_saved_properties'),
    path('api/check-saved/', check_saved_status, name='check_saved_status'),

    # move request
    path('submit-move-request/', SubmitMoveRequestView.as_view(), name='submit_move_request'),
    path('api/cancel-move-request/<int:pk>/', CancelMoveRequestView.as_view(), name='cancel_move_request'),

    # moving checklist
    path('api/checklist/add/', ChecklistAddView.as_view(), name='checklist_add'),
    path('api/checklist/<int:pk>/toggle/', ChecklistToggleView.as_view(), name='checklist_toggle'),
    path('api/checklist/<int:pk>/delete/', ChecklistDeleteView.as_view(), name='checklist_delete'),

    # movers marketplace
    path('movers/map/', MoverMapView.as_view(), name='mover_map'),
    path('movers/<str:username>/', MoverDetailView.as_view(), name='mover_detail'),
    path('owners/<str:username>/', OwnerPortfolioView.as_view(), name='owner_portfolio'),
    path('api/movers/map-data/', MoverMapDataView.as_view(), name='mover_map_data'),
    path('api/movers/nearby/', MoversNearbyDataView.as_view(), name='movers_nearby_data'),
    path('api/move-requests/<int:pk>/commit/', CommitMoveOfferView.as_view(), name='commit_move_offer'),
    path('api/move-requests/<int:pk>/offers/', MoveRequestOffersView.as_view(), name='move_request_offers'),
    path('api/move-offers/<int:pk>/withdraw/', WithdrawMoveOfferView.as_view(), name='withdraw_move_offer'),
    path('api/move-offers/<int:pk>/accept/', AcceptMoveOfferView.as_view(), name='accept_move_offer'),
]
