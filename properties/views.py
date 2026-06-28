# apps/properties/views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count
from .models import Property, PropertyType, PropertyStatus, Unit, Booking
from .forms import PropertyForm, UnitForm, BookingForm
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from clients.models import Client
from django.http import JsonResponse
from payments.models import Payment


class PropertyListView(ListView):
    model = Property
    template_name = 'properties/property_list.html'
    context_object_name = 'properties'
    paginate_by = 10  # Add pagination

    def get_queryset(self):
        queryset = Property.objects.filter(is_active=True)

        # Filters
        property_type = self.request.GET.get('type')
        if property_type:
            queryset = queryset.filter(property_type=property_type)

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        city = self.request.GET.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)

        min_price = self.request.GET.get('min_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)

        max_price = self.request.GET.get('max_price')
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        bedrooms = self.request.GET.get('bedrooms')
        if bedrooms:
            queryset = queryset.filter(bedrooms__gte=bedrooms)

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(address__icontains=search)
            )

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Financial Statistics
        today = timezone.now().date()
        first_day_of_month = today.replace(day=1)
        last_month = today - timedelta(days=30)

        # Total revenue (from paid payments)
        total_revenue = Payment.objects.filter(
            status='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Monthly revenue
        monthly_revenue = Payment.objects.filter(
            status='paid',
            payment_date__year=today.year,
            payment_date__month=today.month
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Previous month revenue for growth calculation
        prev_month_revenue = Payment.objects.filter(
            status='paid',
            payment_date__year=last_month.year,
            payment_date__month=last_month.month
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Calculate growth percentages
        if prev_month_revenue > 0:
            revenue_growth = ((monthly_revenue - prev_month_revenue) / prev_month_revenue) * 100
            monthly_growth = revenue_growth
        else:
            revenue_growth = 0
            monthly_growth = 0

        # Property statistics
        total_properties = Property.objects.filter(is_active=True).count()
        active_properties_count = Property.objects.filter(is_active=True, status='available').count()

        if total_properties > 0:
            active_percentage = (active_properties_count / total_properties) * 100
        else:
            active_percentage = 0

        # Property growth (comparing to last month)
        last_month_properties = Property.objects.filter(
            created_at__date__gte=last_month,
            created_at__date__lte=today
        ).count()
        property_growth = (last_month_properties / total_properties * 100) if total_properties > 0 else 0

        # Client statistics
        total_clients = Client.objects.filter(is_active=True).count() if 'Client' in globals() else 0
        new_clients_month = Client.objects.filter(
            created_at__date__gte=first_day_of_month
        ).count() if 'Client' in globals() else 0

        client_growth = (new_clients_month / total_clients * 100) if total_clients > 0 else 0

        # Recent transactions
        recent_transactions = Payment.objects.filter(
            status='paid'
        ).order_by('-payment_date')[:5]

        total_transactions = Payment.objects.filter(
            status='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Recent properties
        recent_properties = Property.objects.filter(is_active=True).order_by('-created_at')[:5]

        # Revenue percentage change
        if prev_month_revenue > 0:
            revenue_percentage = ((monthly_revenue - prev_month_revenue) / prev_month_revenue) * 100
        else:
            revenue_percentage = 0

        context.update({
            'total_revenue': total_revenue,
            'monthly_revenue': monthly_revenue,
            'revenue_growth': round(revenue_growth, 1),
            'monthly_growth': round(monthly_growth, 1),
            'total_properties': total_properties,
            'active_properties_count': active_properties_count,
            'active_percentage': round(active_percentage, 1),
            'property_growth': round(property_growth, 1),
            'total_clients': total_clients,
            'active_clients': total_clients,
            'new_clients_month': new_clients_month,
            'client_growth': round(client_growth, 1),
            'recent_transactions': recent_transactions,
            'total_transactions': total_transactions,
            'recent_properties': recent_properties,
            'revenue_percentage': round(revenue_percentage, 1),
        })

        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['property_types'] = PropertyType.choices
        context['statuses'] = PropertyStatus.choices
        return context


class PropertyDetailView(DetailView):
    model = Property
    template_name = 'properties/property_detail.html'
    context_object_name = 'property'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['units'] = self.object.units.filter(is_available=True)
        context['images'] = self.object.images.all()
        context['amenities'] = self.object.amenities.all()
        return context


class PropertyCreateView(CreateView):
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_form.html'
    success_url = reverse_lazy('property_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Property added successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Property'
        context['submit_text'] = 'Add Property'
        return context


class PropertyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_form.html'
    success_url = reverse_lazy('properties:list')

    def test_func(self):
        property = self.get_object()
        return self.request.user == property.owner or self.request.user.is_staff

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Property updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Property'
        context['submit_text'] = 'Update Property'
        return context

def geocode_address(request):
    """Geocode address to get latitude and longitude"""
    address = request.GET.get('address', '')
    if not address:
        return JsonResponse({'error': 'Address is required'}, status=400)

    # Use Nominatim (OpenStreetMap) geocoding API
    import requests
    from urllib.parse import quote

    url = f"https://nominatim.openstreetmap.org/search?q={quote(address)}&format=json&limit=1"
    headers = {
        'User-Agent': 'TuHame Property App'
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()

        if data:
            return JsonResponse({
                'lat': data[0]['lat'],
                'lon': data[0]['lon'],
                'display_name': data[0]['display_name']
            })
        else:
            return JsonResponse({'error': 'Location not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def reverse_geocode(request):
    """Reverse geocode to get address from latitude/longitude"""
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')

    if not lat or not lon:
        return JsonResponse({'error': 'Latitude and longitude are required'}, status=400)

    import requests

    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
    headers = {
        'User-Agent': 'TuHame Property App'
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()

        if data and 'display_name' in data:
            return JsonResponse({
                'display_name': data['display_name'],
                'address': data.get('display_name', '')
            })
        else:
            return JsonResponse({'error': 'Address not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


class PropertyDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Property
    template_name = 'properties/property_confirm_delete.html'
    success_url = reverse_lazy('property_list')

    def test_func(self):
        property = self.get_object()
        return self.request.user == property.owner or self.request.user.is_staff


class UnitCreateView(LoginRequiredMixin, CreateView):
    model = Unit
    form_class = UnitForm
    template_name = 'properties/unit_form.html'

    def form_valid(self, form):
        property_pk = self.kwargs.get('property_pk')
        form.instance.property_id = property_pk
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('properties:detail', kwargs={'pk': self.kwargs['property_pk']})


class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'properties/booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 20

    def get_queryset(self):
        return Booking.objects.filter(client__user=self.request.user)


class BookingCreateView(LoginRequiredMixin, CreateView):
    model = Booking
    form_class = BookingForm
    template_name = 'properties/booking_form.html'

    def form_valid(self, form):
        form.instance.client = self.request.user.client_profile
        form.instance.total_price = self.calculate_total_price(form.cleaned_data)
        return super().form_valid(form)

    def calculate_total_price(self, cleaned_data):
        # Logic to calculate total based on dates and property rates
        property = cleaned_data['property']
        nights = (cleaned_data['check_out_date'] - cleaned_data['check_in_date']).days
        return property.price * nights

    def get_success_url(self):
        return reverse_lazy('properties:booking_list')