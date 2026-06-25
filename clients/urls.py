# apps/clients/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.ClientListView.as_view(), name='client_list'),
    path('add/', views.ClientCreateView.as_view(), name='client_add'),
    path('<int:pk>/', views.ClientDetailView.as_view(), name='client_detail'),
    path('<int:pk>/edit/', views.ClientUpdateView.as_view(), name='client_edit'),
    path('<int:pk>/delete/', views.ClientDeleteView.as_view(), name='client_delete'),

    path('<int:client_pk>/document/add/', views.ClientDocumentUploadView.as_view(), name='document_add'),
    path('document/<int:pk>/edit/', views.ClientDocumentUpdateView.as_view(), name='document_edit'),
    path('document/<int:pk>/delete/', views.ClientDocumentDeleteView.as_view(), name='document_delete'),
    path('document/<int:pk>/download/', views.ClientDocumentDownloadView.as_view(), name='document_download'),

    # Watchlist
    path('<int:client_pk>/watchlist/add/', views.WatchlistCreateView.as_view(), name='watchlist_add'),
    path('watchlist/<int:pk>/delete/', views.WatchlistDeleteView.as_view(), name='watchlist_delete'),

    # Bill CRUD
    path('admin/bills/', views.BillListView.as_view(), name='bill_list'),
    path('admin/bills/create/', views.BillCreateView.as_view(), name='bill_create'),
    path('admin/bills/<int:pk>/update/', views.BillUpdateView.as_view(), name='bill_update'),
    path('admin/bills/<int:pk>/delete/', views.BillDeleteView.as_view(), name='bill_delete'),
    path('admin/bills/<int:pk>/mark-paid/', views.BillMarkPaidView.as_view(), name='bill_mark_paid'),
]