from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    path('my-profile/', views.MyProfileView.as_view(), name='my_profile'),
    path('my-profile/edit/', views.MyProfileUpdateView.as_view(), name='edit_profile'),

    # View other profiles (admin/landlord only)
    path('profile/<str:username>/', views.ProfileDetailView.as_view(), name='profile_detail'),
    path('profile/<str:username>/', views.PublicProfileView.as_view(), name='public_profile'),
    path('api/generate-qr/', views.generate_user_qr, name='generate_qr'),
]