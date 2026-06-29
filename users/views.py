# apps/dashboard/views.py
from django.views.generic import FormView, TemplateView, DetailView, UpdateView, View, CreateView
from .models import Profile
from django.http import JsonResponse, Http404
import base64
from django.core.files.base import ContentFile
import uuid

from django.urls import reverse
from home.models import ViewingSchedule, SavedProperty
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import RedirectView
from .forms import ProfileForm, UserRegistrationForm
from django.db import models
import qrcode
from io import BytesIO
import base64
from .utils import generate_qr_code_for_user

from django.contrib.auth import get_user_model
User = get_user_model()

class LoginView(FormView):
    """
    Custom Login View using Class-Based View
    """
    template_name = 'auth/login.html'
    form_class = AuthenticationForm
    success_url = reverse_lazy('home:home')

    def dispatch(self, request, *args, **kwargs):
        """Redirect authenticated users to dashboard"""
        if request.user.is_authenticated:
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Process valid form and log in user"""
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(self.request, username=username, password=password)

        if user is not None:
            login(self.request, user)
            messages.success(self.request, f'Welcome back, {user.get_full_name() or user.username}!')
            return super().form_valid(form)
        else:
            messages.error(self.request, 'Invalid username or password.')
            return self.form_invalid(form)

    def form_invalid(self, form):
        """Handle invalid form submission"""
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """Add extra context to template"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Login - Real Estate Management System'
        return context

class RegisterView(CreateView):
    """
    User Registration View
    """
    template_name = 'auth/register.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        """Redirect authenticated users to dashboard"""
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Save user and log them in"""
        response = super().form_valid(form)

        # Log the user in after registration
        user = self.object
        login(self.request, user)

        messages.success(
            self.request,
            f'Welcome to 2Hame, {user.get_full_name() or user.username}! 🎉 Your account has been created successfully.'
        )

        return response

    def form_invalid(self, form):
        """Handle invalid form submission"""
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """Add extra context to template"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Account - 2Hame'
        return context

class LogoutView(RedirectView):
    """
    Custom Logout View using Class-Based View
    """
    url = reverse_lazy('login')

    def get(self, request, *args, **kwargs):
        """Log out the user and redirect to login page"""
        logout(request)
        messages.success(request, 'You have been successfully logged out.')
        return super().get(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard View - Only accessible after login
    """
    template_name = 'dashboard.html'
    login_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add dashboard statistics here
        return context

# public profile view by username
class PublicProfileView(DetailView):
    """Public profile view by username - NO LOGIN REQUIRED"""
    model = Profile
    template_name = 'auth/public_profile.html'
    context_object_name = 'profile'
    slug_field = 'user__username'
    slug_url_kwarg = 'username'

    def get_queryset(self):
        return Profile.objects.filter(is_active=True, user__is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_object()
        user = profile.user

        # Only show public information
        context['full_name'] = profile.get_full_name()
        context['user'] = user
        context['phone'] = profile.phone_number
        context['email'] = user.email
        context['current_property'] = profile.current_property
        context['city'] = profile.city
        context['country'] = profile.country
        context['profile_picture'] = profile.profile_picture
        context['is_public'] = True
        return context

#token qr
class PublicProfileByTokenView(DetailView):
    """Public profile view - NO LOGIN REQUIRED"""
    model = Profile
    template_name = 'auth/public_profile.html'
    context_object_name = 'profile'
    slug_field = 'qr_code_token'
    slug_url_kwarg = 'token'

    # IMPORTANT: No LoginRequiredMixin here!

    def get_queryset(self):
        return Profile.objects.filter(is_active=True)

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except (ValueError, TypeError, Profile.DoesNotExist):
            raise Http404("Profile not found")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_object()
        user = profile.user

        context['full_name'] = profile.get_full_name()
        context['user'] = user
        context['phone'] = profile.phone_number
        context['email'] = user.email
        context['current_property'] = profile.current_property
        context['city'] = profile.city
        context['country'] = profile.country
        context['profile_picture'] = profile.profile_picture
        context['is_public'] = True
        return context

# LOGGED IN USER PROFILE VIEW
class MyProfileView(LoginRequiredMixin, DetailView):
    """View for users to see their own profile"""

    model = Profile
    template_name = "auth/my_profile.html"
    context_object_name = "profile"

    def get_object(self, queryset=None):
        """Get the profile of the currently logged-in user"""
        return self.request.user.profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user

        # Get move history for this user
        context['move_history'] = self.request.user.move_history.all()[:5]

        # Get upcoming viewings
        context['upcoming_viewings'] = ViewingSchedule.objects.filter(
            user=self.request.user,
            status__in=['pending', 'confirmed']
        ).order_by('preferred_date')[:5]

        # Get bills for user's current property
        profile = self.request.user.profile
        if profile.current_property:
            # Get all bills for the current property
            context['bills'] = profile.current_property.bills.filter(
                is_active=True
            ).order_by('-due_date', '-created_at')

            # Get bill statistics
            bills = context['bills']
            context['total_bills'] = bills.count()
            context['paid_bills'] = bills.filter(status='paid').count()
            context['pending_bills'] = bills.filter(status='pending').count()
            context['overdue_bills'] = bills.filter(status='overdue').count()
            context['total_amount_due'] = bills.filter(
                status__in=['pending', 'overdue']
            ).aggregate(total=models.Sum('amount'))['total'] or 0

            # Get utility usage for current property
            context['utility_usage'] = profile.current_property.utility_usage.all().order_by('-reading_date')[:3]
        else:
            context['bills'] = []
            context['total_bills'] = 0
            context['paid_bills'] = 0
            context['pending_bills'] = 0
            context['overdue_bills'] = 0
            context['total_amount_due'] = 0
            context['utility_usage'] = []

        # Get saved properties
        saved_properties = SavedProperty.objects.filter(
            user=self.request.user
        ).select_related('property').order_by('-saved_at')

        context['saved_properties'] = saved_properties
        context['saved_properties_count'] = saved_properties.count()

        # Generate QR Code
        context['qr_code_data'] = generate_qr_code_for_user(profile)
        print(context['qr_code_data'])

        return context

class MyProfileUpdateView(LoginRequiredMixin, UpdateView):
    """View for users to update their own profile"""

    model = Profile
    form_class = ProfileForm
    template_name = "auth/edit_profile.html"

    def get_object(self, queryset=None):
        """Get the profile of the currently logged-in user"""
        return self.request.user.profile

    def get_success_url(self):
        return reverse_lazy('my_profile')

    def form_valid(self, form):
        """Handle successful form submission"""
        messages.success(self.request, "Your profile has been updated successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        """Handle invalid form submission"""
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


class ProfileDetailView(LoginRequiredMixin, DetailView):
    """View for admins/landlords to see another user's profile"""

    model = Profile
    template_name = "auth/profile_detail.html"
    context_object_name = "profile"
    slug_field = 'user__username'
    slug_url_kwarg = 'username'

    def get_queryset(self):
        """Only allow viewing profiles if user is admin or landlord"""
        queryset = super().get_queryset()

        # If user is staff or superuser, allow viewing all
        if self.request.user.is_staff or self.request.user.is_superuser:
            return queryset

        # If user is a property owner, allow viewing profiles of tenants in their properties
        # Get all properties owned by this user
        owned_properties = self.request.user.owned_properties.values_list('id', flat=True)

        # Only show profiles of residents in those properties
        return queryset.filter(current_property__in=owned_properties)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check if the current user can edit this profile
        context['can_edit'] = (
            self.request.user.is_staff or
            self.request.user.is_superuser or
            self.request.user == self.object.user
        )

        return context

class RegenerateQRView(LoginRequiredMixin, View):
    """View to regenerate QR code for the current user"""

    def get(self, request):
        profile = request.user.profile

        # Regenerate QR code
        success = profile.regenerate_qr_code()

        if success:
            messages.success(request, 'QR Code regenerated successfully!')
        else:
            messages.error(request, 'Failed to regenerate QR code. Please try again.')

        return redirect('my_profile')