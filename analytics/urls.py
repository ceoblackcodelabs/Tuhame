from django.urls import path

from . import views

app_name = 'analytics'

urlpatterns = [
    path('traffic/', views.TrafficDashboardView.as_view(), name='traffic'),
    path('site-visits/', views.SiteVisitsView.as_view(), name='site_visits'),
    path('blog/', views.BlogAnalyticsView.as_view(), name='blog_analytics'),
    path('leads/', views.LeadsView.as_view(), name='leads'),
    path('profile/<str:username>/', views.ProfileAnalyticsView.as_view(), name='profile_analytics'),
]
