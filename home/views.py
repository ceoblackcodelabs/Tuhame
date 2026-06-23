from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from properties.models import Property, PropertyStatus, PropertyImage, PropertyType, Amenity
from django.db import models
from .forms import ViewingScheduleForm
from django.contrib import messages
from django.db.models import Q, Avg, Count

class HomeView(ListView):
    model = Property
    context_object_name = "properties"
    paginate_by = 3
    template_name = "home/index.html"


class PropertiesListView(ListView):
    model = Property
    context_object_name = "properties"
    paginate_by = 9
    template_name = "home/properties/properties.html"

    def get_queryset(self):
        queryset = Property.objects.filter(is_active=True)

        # Get filter parameters
        location = self.request.GET.get('location', '').strip()
        property_type = self.request.GET.get('property_type', '')
        min_price = self.request.GET.get('min_price', '')
        max_price = self.request.GET.get('max_price', '')
        bedrooms = self.request.GET.get('bedrooms', '')
        bathrooms = self.request.GET.get('bathrooms', '')
        availability = self.request.GET.get('availability', '')
        amenities = self.request.GET.getlist('amenities', [])

        # Location filter
        if location:
            queryset = queryset.filter(
                Q(city__icontains=location) |
                Q(state__icontains=location) |
                Q(address__icontains=location) |
                Q(country__icontains=location)
            )

        # Property type filter
        if property_type and property_type != 'All':
            queryset = queryset.filter(property_type=property_type)

        # Price range filter
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except (ValueError, TypeError):
                pass
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except (ValueError, TypeError):
                pass

        # Bedrooms filter
        if bedrooms and bedrooms != 'Any':
            if bedrooms == 'Studio':
                queryset = queryset.filter(bedrooms=0)
            elif bedrooms == '4+':
                queryset = queryset.filter(bedrooms__gte=4)
            else:
                try:
                    queryset = queryset.filter(bedrooms=int(bedrooms))
                except (ValueError, TypeError):
                    pass

        # Bathrooms filter
        if bathrooms and bathrooms != 'Any':
            if bathrooms == '3+':
                queryset = queryset.filter(bathrooms__gte=3)
            else:
                try:
                    queryset = queryset.filter(bathrooms=float(bathrooms))
                except (ValueError, TypeError):
                    pass

        # Availability filter
        if availability and availability != 'All':
            if availability == 'available':
                queryset = queryset.filter(status=PropertyStatus.AVAILABLE)
            elif availability == 'coming_soon':
                queryset = queryset.filter(status=PropertyStatus.MAINTENANCE)

        # Amenities filter
        if amenities:
            for amenity in amenities:
                queryset = queryset.filter(amenities__name__icontains=amenity)

        # Sorting
        sort_by = self.request.GET.get('sort', 'newest')
        if sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'lowest_price':
            queryset = queryset.order_by('price')
        elif sort_by == 'highest_price':
            queryset = queryset.order_by('-price')
        elif sort_by == 'most_popular':
            queryset = queryset.annotate(
                booking_count=Count('bookings')
            ).order_by('-booking_count')

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get filter parameters for template
        context['current_location'] = self.request.GET.get('location', '')
        context['current_property_type'] = self.request.GET.get('property_type', 'All')
        context['current_min_price'] = self.request.GET.get('min_price', '')
        context['current_max_price'] = self.request.GET.get('max_price', '')
        context['current_bedrooms'] = self.request.GET.get('bedrooms', 'Any')
        context['current_bathrooms'] = self.request.GET.get('bathrooms', 'Any')
        context['current_availability'] = self.request.GET.get('availability', 'available')
        context['current_sort'] = self.request.GET.get('sort', 'newest')
        context['selected_amenities'] = self.request.GET.getlist('amenities', [])

        # Get all amenities for filter display
        context['all_amenities'] = Amenity.objects.all()

        # Get property types with display names
        property_types = Property.objects.filter(
            is_active=True
        ).values('property_type').annotate(
            count=Count('id')
        )

        # Add display names
        for pt in property_types:
            pt['display_name'] = dict(PropertyType.choices).get(pt['property_type'], pt['property_type'].capitalize())

        context['property_types'] = property_types

        # Price range stats
        price_stats = Property.objects.filter(is_active=True).aggregate(
            min_price=models.Min('price'),
            max_price=models.Max('price'),
            avg_price=models.Avg('price')
        )
        context['price_stats'] = price_stats

        return context

class PropertiesDetailView(DetailView):
    model = Property
    context_object_name = "property"
    template_name = "home/properties/about_property.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        property = self.get_object()

        # Get similar properties
        similar_properties = Property.objects.filter(
            is_active=True,
            status=PropertyStatus.AVAILABLE
        ).exclude(
            id=property.id
        ).filter(
            models.Q(city=property.city) |
            models.Q(property_type=property.property_type)
        )[:3]

        context['similar_properties'] = similar_properties

        # Initialize form with user data if authenticated
        initial_data = {}
        if self.request.user.is_authenticated:
            initial_data = {
                'full_name': self.request.user.get_full_name() or self.request.user.username,
                'email': self.request.user.email,
            }
        context['form'] = ViewingScheduleForm(initial=initial_data)

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = ViewingScheduleForm(request.POST)

        if form.is_valid():
            viewing = form.save(commit=False)
            viewing.property = self.object

            # Set user if authenticated
            if request.user.is_authenticated:
                viewing.user = request.user

            viewing.save()
            messages.success(request, f"Viewing request sent successfully for {viewing.preferred_date}!")
            return redirect('home:about_property', slug=self.object.slug)
        else:
            messages.error(request, "Please correct the errors below.")
            context = self.get_context_data()
            context['form'] = form
            return self.render_to_response(context)


class PropertyMapSearchListView(ListView):
    model = Property
    context_object_name = "properties"
    paginate_by = 3
    template_name = "home/properties/map.html"

