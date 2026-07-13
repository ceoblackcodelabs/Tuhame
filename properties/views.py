# apps/properties/views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q, Sum, Count
from .models import Property, PropertyType, PropertyStatus, Unit, Booking
from .forms import PropertyForm, UnitForm, BookingForm, ViewingScheduleForm
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
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except (ValueError, TypeError):
                pass

        max_price = self.request.GET.get('max_price')
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except (ValueError, TypeError):
                pass

        bedrooms = self.request.GET.get('bedrooms')
        if bedrooms:
            try:
                queryset = queryset.filter(bedrooms__gte=int(bedrooms))
            except (ValueError, TypeError):
                pass

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
        total_clients = Client.objects.filter(is_active=True).count()
        new_clients_month = Client.objects.filter(
            created_at__date__gte=first_day_of_month
        ).count()

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

        # ============ CHART DATA ============

        # Line chart: revenue trend, last 7 days
        line_chart_labels = []
        line_chart_data = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            daily_total = Payment.objects.filter(
                status='paid',
                payment_date=date
            ).aggregate(total=Sum('amount'))['total'] or 0
            line_chart_labels.append(date.strftime('%m/%d'))
            line_chart_data.append(float(daily_total))

        # Bar chart: properties by type
        type_display = dict(PropertyType.choices)
        property_type_counts = Property.objects.filter(is_active=True).values('property_type').annotate(
            count=Count('id')
        ).order_by('-count')
        bar_chart_labels = [type_display.get(p['property_type'], p['property_type']) for p in property_type_counts]
        bar_chart_data = [p['count'] for p in property_type_counts]

        # Doughnut chart: paid transactions by payment method
        method_display = {
            'cash': 'Cash', 'bank_transfer': 'Bank Transfer', 'credit_card': 'Credit Card',
            'debit_card': 'Debit Card', 'check': 'Check', 'online': 'Online', 'mpesa': 'M-Pesa',
        }
        payment_methods = Payment.objects.filter(status='paid').values('payment_method').annotate(
            total=Sum('amount')
        )
        doughnut_labels = [method_display.get(m['payment_method'], (m['payment_method'] or 'Other').title()) for m in payment_methods]
        doughnut_data = [float(m['total']) for m in payment_methods]

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
            'property_types': PropertyType.choices,
            'statuses': PropertyStatus.choices,
            'line_chart_labels': line_chart_labels,
            'line_chart_data': line_chart_data,
            'bar_chart_labels': bar_chart_labels,
            'bar_chart_data': bar_chart_data,
            'doughnut_labels': doughnut_labels,
            'doughnut_data': doughnut_data,
        })

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


class PropertyCreateView(LoginRequiredMixin, CreateView):
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
    success_url = reverse_lazy('property_list')

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
        'User-Agent': '2Hame Property App'
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
        'User-Agent': '2Hame Property App'
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
        return reverse_lazy('property_detail', kwargs={'pk': self.kwargs['property_pk']})


class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'properties/booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 20

    def get_queryset(self):
        queryset = Booking.objects.select_related('property', 'client', 'unit').order_by('-created_at')
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(client__user=self.request.user)


class BookingCreateView(LoginRequiredMixin, CreateView):
    model = Booking
    form_class = BookingForm
    template_name = 'properties/booking_form.html'

    def form_valid(self, form):
        client_profile = getattr(self.request.user, 'client_profile', None)
        if client_profile is None:
            messages.error(
                self.request,
                'Your account needs a client profile before you can make a booking. '
                'Please contact support.'
            )
            return redirect('booking_list')
        form.instance.client = client_profile
        form.instance.total_price = self.calculate_total_price(form.cleaned_data)
        return super().form_valid(form)

    def calculate_total_price(self, cleaned_data):
        # Logic to calculate total based on dates and property rates
        property = cleaned_data['property']
        nights = (cleaned_data['check_out_date'] - cleaned_data['check_in_date']).days
        return property.price * nights

    def get_success_url(self):
        return reverse_lazy('booking_list')

from home.models import ViewingSchedule
class ReviewListView(LoginRequiredMixin, ListView):
    """View for listing viewing schedules"""
    model = ViewingSchedule
    template_name = 'properties/schedule_view.html'
    context_object_name = 'viewings'
    paginate_by = 20

    def get_queryset(self):
        queryset = ViewingSchedule.objects.all().select_related('property', 'user').order_by('-created_at')

        # Filter by search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(property__title__icontains=search)
            )

        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by time
        time = self.request.GET.get('time', '')
        if time:
            queryset = queryset.filter(preferred_time=time)

        # Filter by date range
        date_from = self.request.GET.get('date_from', '')
        if date_from:
            queryset = queryset.filter(preferred_date__gte=date_from)

        date_to = self.request.GET.get('date_to', '')
        if date_to:
            queryset = queryset.filter(preferred_date__lte=date_to)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()

        # Statistics
        context['total_viewings'] = queryset.count()
        context['pending_count'] = queryset.filter(status='pending').count()
        context['confirmed_count'] = queryset.filter(status='confirmed').count()
        context['completed_count'] = queryset.filter(status='completed').count()
        context['cancelled_count'] = queryset.filter(status='cancelled').count()
        context['no_show_count'] = queryset.filter(status='no_show').count()

        # Recent viewings
        context['recent_viewings'] = queryset[:10]

        # Growth calculations (simple example)
        total = context['total_viewings']
        context['viewings_growth'] = 12  # You can calculate this based on previous month

        return context

class ViewingDetailView(LoginRequiredMixin, DetailView):
    """View for displaying a single viewing schedule"""
    model = ViewingSchedule
    template_name = 'properties/viewing_detail.html'
    context_object_name = 'viewing'
    pk_url_kwarg = 'pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        viewing = self.get_object()

        # Get the property details
        context['property'] = viewing.property

        # Get the user who requested the viewing
        context['user'] = viewing.user

        # Add current time for comparison
        context['now'] = timezone.now()

        # Calculate time status
        if viewing.status == 'confirmed' and viewing.scheduled_datetime:
            if viewing.scheduled_datetime > timezone.now():
                context['time_status'] = 'upcoming'
                context['time_status_label'] = 'Upcoming'
                context['time_status_class'] = 'success'
            elif viewing.scheduled_datetime < timezone.now():
                context['time_status'] = 'past'
                context['time_status_label'] = 'Past'
                context['time_status_class'] = 'secondary'
        else:
            context['time_status'] = 'not_scheduled'
            context['time_status_label'] = 'Not Scheduled'
            context['time_status_class'] = 'warning'

        # Get activity log
        context['activity_log'] = [
            {
                'action': 'Created',
                'date': viewing.created_at,
                'icon': 'mdi mdi-plus-circle',
                'color': 'primary'
            },
        ]

        if viewing.confirmed_at:
            context['activity_log'].append({
                'action': 'Confirmed',
                'date': viewing.confirmed_at,
                'icon': 'mdi mdi-check-circle',
                'color': 'success'
            })

        if viewing.completed_at:
            context['activity_log'].append({
                'action': 'Completed',
                'date': viewing.completed_at,
                'icon': 'mdi mdi-check-all',
                'color': 'info'
            })

        if viewing.cancelled_at:
            context['activity_log'].append({
                'action': 'Cancelled',
                'date': viewing.cancelled_at,
                'icon': 'mdi mdi-close-circle',
                'color': 'danger'
            })

        return context

class ViewingUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View for updating a viewing schedule"""
    model = ViewingSchedule
    form_class = ViewingScheduleForm
    template_name = 'properties/viewing_form.html'
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('schedule_view')

    def test_func(self):
        viewing = self.get_object()
        return self.request.user.is_staff or self.request.user == viewing.user

    def form_valid(self, form):
        messages.success(self.request, 'Viewing schedule updated successfully!')
        return super().form_valid(form)


class ConfirmViewingView(LoginRequiredMixin, View):
    """View to confirm a viewing"""

    def get(self, request, pk):
        viewing = get_object_or_404(ViewingSchedule, pk=pk)
        if viewing.status == 'pending':
            viewing.confirm_viewing()
            messages.success(request, f'Viewing for {viewing.full_name} has been confirmed!')
        else:
            messages.warning(request, 'This viewing cannot be confirmed.')
        return redirect('schedule_view')


class CancelViewingView(LoginRequiredMixin, View):
    """View to cancel a viewing"""

    def get(self, request, pk):
        viewing = get_object_or_404(ViewingSchedule, pk=pk)
        if viewing.status in ['pending', 'confirmed']:
            viewing.cancel_viewing()
            messages.success(request, f'Viewing for {viewing.full_name} has been cancelled.')
        else:
            messages.warning(request, 'This viewing cannot be cancelled.')
        return redirect('schedule_view')


class CompleteViewingView(LoginRequiredMixin, View):
    """View to mark a viewing as completed"""

    def get(self, request, pk):
        viewing = get_object_or_404(ViewingSchedule, pk=pk)
        if viewing.status == 'confirmed':
            viewing.complete_viewing()
            messages.success(request, f'Viewing for {viewing.full_name} has been marked as completed!')
        else:
            messages.warning(request, 'This viewing cannot be marked as completed.')
        return redirect('schedule_view')
