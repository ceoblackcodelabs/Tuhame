# apps/dashboard/views.py
from django.views.generic import FormView, TemplateView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import RedirectView


class LoginView(FormView):
    """
    Custom Login View using Class-Based View
    """
    template_name = 'auth/login.html'
    form_class = AuthenticationForm
    success_url = reverse_lazy('dashboard')

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