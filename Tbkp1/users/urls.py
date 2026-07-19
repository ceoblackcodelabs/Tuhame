# apps/users/urls.py
from django.urls import path, re_path
from . import views, tests


urlpatterns = [
    # Authentication URLs
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    path('my-profile/', views.MyProfileView.as_view(), name='my_profile'),
    path('my-profile/edit/', views.MyProfileUpdateView.as_view(), name='edit_profile'),

    # Admin/Landlord view other profiles
    path('profile/<str:username>/', views.ProfileDetailView.as_view(), name='profile_detail'),

    # PUBLIC profile - NO LOGIN REQUIRED - For QR codes
    # This uses the UUID token from the profile
    path('qr/<uuid:token>/', views.PublicProfileByTokenView.as_view(), name='public_profile_by_token'),

    # Also support username-based public profiles
    path('public/<str:username>/', views.PublicProfileView.as_view(), name='public_profile'),

    # Regenerate QR
    path('regenerate-qr/', views.RegenerateQRView.as_view(), name='regenerate_qr'),

    # Owner verification workflow
    path('request-owner-verification/', views.RequestOwnerVerificationView.as_view(), name='request_owner_verification'),
    path('owner-verification/', views.OwnerVerificationQueueView.as_view(), name='owner_verification_queue'),
    path('owner-verification/<int:pk>/approve/', views.ApproveOwnerVerificationView.as_view(), name='approve_owner_verification'),
    path('owner-verification/<int:pk>/reject/', views.RejectOwnerVerificationView.as_view(), name='reject_owner_verification'),

    # test
    path('test-qr/', tests.test_qr_url, name='test_qr'),
]