from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from properties.models import Property, PropertyStatus, PropertyType, Amenity, PropertyReview
from django.db import models
from .forms import ViewingScheduleForm, ReviewForm, ContactForm
from django.contrib import messages
import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg, Count
from users.models import Profile

class HomeView(ListView):
    model = Property
    context_object_name = "properties"
    paginate_by = 3
    template_name = "home/index.html"

    def get_queryset(self):
        queryset = Property.objects.filter(
            is_active=True,
            status=PropertyStatus.AVAILABLE
        )

        # Get search parameters
        search_query = self.request.GET.get('search', '').strip()
        property_type = self.request.GET.get('property_type', '')

        # Apply search filter
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(address__icontains=search_query) |
                Q(city__icontains=search_query) |
                Q(state__icontains=search_query) |
                Q(country__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        # Apply property type filter
        if property_type and property_type != 'All Types':
            queryset = queryset.filter(property_type=property_type.lower())

        # Slice LAST, after all filters - filtering a sliced queryset raises
        # an AssertionError in Django, which was crashing the homepage
        # whenever a property_type filter was combined with the featured list.
        return queryset.order_by('-created_at')[:6]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get search parameters
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_type'] = self.request.GET.get('property_type', 'All Types')

        # Get property types for dropdown
        context['property_types'] = [
            {'value': 'All Types', 'label': 'All Types'},
            {'value': 'apartment', 'label': 'Apartment'},
            {'value': 'villa', 'label': 'Villa'},
            {'value': 'bnb', 'label': 'BnB'},
            {'value': 'rental', 'label': 'Rental'},
            {'value': 'commercial', 'label': 'Commercial'},
            {'value': 'residential', 'label': 'Residential'},
            {'value': 'land', 'label': 'Land'},
            {'value': 'industrial', 'label': 'Industrial'},
        ]

        # Get category counts
        categories = []
        for property_type in PropertyType.choices:
            count = Property.objects.filter(
                is_active=True,
                property_type=property_type[0]
            ).count()
            categories.append({
                'type': property_type[0],
                'label': property_type[1],
                'count': count,
                'icon': self.get_category_icon(property_type[0])
            })
        context['categories'] = categories
        context['total_active_properties'] = Property.objects.filter(is_active=True).count()

        # Testimonials - pulled from real, positive property reviews
        context['testimonials'] = PropertyReview.objects.filter(
            rating__gte=4
        ).exclude(comment='').select_related('user', 'property').order_by('-rating', '-created_at')[:6]

        return context

    def get_category_icon(self, property_type):
        """Get icon for property type"""
        icons = {
            'apartment': '🏠',
            'rental': '🏡',
            'villa': '🏘',
            'bnb': '🛏',
            'commercial': '🏢',
            'residential': '🏠',
            'land': '🌳',
            'industrial': '🏭',
        }
        return icons.get(property_type, '🏠')


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
        property_obj = self.get_object()

        # Get similar properties
        similar_properties = Property.objects.filter(
            is_active=True,
            status=PropertyStatus.AVAILABLE
        ).exclude(
            id=property_obj.id
        ).filter(
            Q(city=property_obj.city) |
            Q(property_type=property_obj.property_type)
        )[:3]

        context['similar_properties'] = similar_properties

        # Initialize viewing form with user data if authenticated
        initial_data = {}
        if self.request.user.is_authenticated:
            initial_data = {
                'full_name': self.request.user.get_full_name() or self.request.user.username,
                'email': self.request.user.email,
            }
        context['form'] = ViewingScheduleForm(initial=initial_data)

        # Initialize review form
        context['review_form'] = ReviewForm()

        # Check if user has already reviewed
        if self.request.user.is_authenticated:
            user_review = PropertyReview.objects.filter(
                property=property_obj,
                user=self.request.user
            ).first()
            context['user_review'] = user_review

            # Check if user can review this property (they must live there)
            context['can_review'] = self.can_user_review_property(self.request.user, property_obj)
        else:
            context['user_review'] = None
            context['can_review'] = False

        # Calculate review statistics
        reviews = property_obj.reviews.all()
        review_count = reviews.count()

        if review_count > 0:
            # Average rating
            avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

            # Rating percentages for the bar chart
            rating_counts = {}
            for i in range(1, 6):
                rating_counts[i] = reviews.filter(rating=i).count()

            total = review_count
            context['avg_rating'] = avg_rating
            context['rating_5_pct'] = (rating_counts.get(5, 0) / total * 100) if total > 0 else 0
            context['rating_4_pct'] = (rating_counts.get(4, 0) / total * 100) if total > 0 else 0
            context['rating_3_pct'] = (rating_counts.get(3, 0) / total * 100) if total > 0 else 0
            context['rating_2_pct'] = (rating_counts.get(2, 0) / total * 100) if total > 0 else 0
            context['rating_1_pct'] = (rating_counts.get(1, 0) / total * 100) if total > 0 else 0
        else:
            context['avg_rating'] = 0
            context['rating_5_pct'] = 0
            context['rating_4_pct'] = 0
            context['rating_3_pct'] = 0
            context['rating_2_pct'] = 0
            context['rating_1_pct'] = 0

        return context

    def can_user_review_property(self, user, property_obj):
        """Check if a user can review a property (they must live there)"""
        try:
            profile = user.profile
            # Check if the user's current property matches this property
            return profile.current_property == property_obj
        except Profile.DoesNotExist:
            return False

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


class SubmitReviewView(LoginRequiredMixin, View):
    """View for submitting a property review - only for current residents"""

    def post(self, request, *args, **kwargs):
        property_obj = get_object_or_404(Property, slug=kwargs.get('slug'))

        # Check if user can review this property
        if not self.can_user_review_property(request.user, property_obj):
            messages.error(request, "You can only review properties you are currently living in.")
            return redirect('home:about_property', slug=property_obj.slug)

        # Check if user already reviewed
        existing_review = PropertyReview.objects.filter(
            property=property_obj,
            user=request.user
        ).first()

        if existing_review:
            messages.warning(request, "You have already reviewed this property.")
            return redirect('home:about_property', slug=property_obj.slug)

        form = ReviewForm(request.POST)

        if form.is_valid():
            review = form.save(commit=False)
            review.property = property_obj
            review.user = request.user
            review.save()
            messages.success(request, f"Your {review.rating}-star review was submitted successfully!")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return redirect('home:about_property', slug=property_obj.slug)

    def can_user_review_property(self, user, property_obj):
        """Check if a user can review a property (they must live there)"""
        try:
            profile = user.profile
            return profile.current_property == property_obj
        except Profile.DoesNotExist:
            return False


class EditReviewView(LoginRequiredMixin, View):
    """View for editing a property review - only for current residents"""

    def get(self, request, *args, **kwargs):
        property_obj = get_object_or_404(Property, slug=kwargs.get('slug'))

        # Check if user can review this property
        if not self.can_user_review_property(request.user, property_obj):
            messages.error(request, "You can only review properties you are currently living in.")
            return redirect('home:about_property', slug=property_obj.slug)

        review = get_object_or_404(PropertyReview, property=property_obj, user=request.user)
        return redirect('home:about_property', slug=property_obj.slug)

    def post(self, request, *args, **kwargs):
        property_obj = get_object_or_404(Property, slug=kwargs.get('slug'))

        # Check if user can review this property
        if not self.can_user_review_property(request.user, property_obj):
            messages.error(request, "You can only review properties you are currently living in.")
            return redirect('home:about_property', slug=property_obj.slug)

        review = get_object_or_404(PropertyReview, property=property_obj, user=request.user)
        form = ReviewForm(request.POST, instance=review)

        if form.is_valid():
            form.save()
            messages.success(request, f"Your review was updated successfully!")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return redirect('home:about_property', slug=property_obj.slug)

    def can_user_review_property(self, user, property_obj):
        """Check if a user can review a property (they must live there)"""
        try:
            profile = user.profile
            return profile.current_property == property_obj
        except Profile.DoesNotExist:
            return False


class DeleteReviewView(LoginRequiredMixin, View):
    """View for deleting a property review"""

    def post(self, request, *args, **kwargs):
        property_obj = get_object_or_404(Property, slug=kwargs.get('slug'))
        review = get_object_or_404(PropertyReview, property=property_obj, user=request.user)

        review.delete()
        messages.success(request, "Your review was deleted successfully.")

        return redirect('home:about_property', slug=property_obj.slug)

class PropertyMapSearchListView(View):
    """
    View for the map search page with dynamic properties
    """
    template_name = 'map/map_search.html'

    def get(self, request, *args, **kwargs):
        # Get filter parameters
        property_type = request.GET.get('type', '')
        search_query = request.GET.get('search', '')
        min_price = request.GET.get('min_price', '')
        max_price = request.GET.get('max_price', '')

        # Get all active properties
        properties = Property.objects.filter(
            is_active=True,
            status=PropertyStatus.AVAILABLE
        )

        # Apply filters
        if property_type and property_type != 'all':
            properties = properties.filter(property_type=property_type)

        if search_query:
            properties = properties.filter(
                Q(title__icontains=search_query) |
                Q(city__icontains=search_query) |
                Q(state__icontains=search_query) |
                Q(address__icontains=search_query)
            )

        if min_price:
            try:
                properties = properties.filter(price__gte=float(min_price))
            except (ValueError, TypeError):
                pass

        if max_price:
            try:
                properties = properties.filter(price__lte=float(max_price))
            except (ValueError, TypeError):
                pass

        # Prepare data for the map
        properties_data = []
        for prop in properties:
            # Get the first image or use a placeholder
            main_image = prop.main_image.url if prop.main_image else None

            properties_data.append({
                'id': prop.id,
                'name': prop.title,
                'type': prop.property_type,
                'location': f"{prop.city}, {prop.state}",
                'lat': float(prop.latitude) if prop.latitude else None,
                'lng': float(prop.longitude) if prop.longitude else None,
                'price': float(prop.price),
                'beds': prop.bedrooms,
                'baths': float(prop.bathrooms),
                'rating': 4.5,  # You can add a rating field or calculate from reviews
                'dist': '0.5 km',  # You can calculate distance from user location
                'img': main_image or 'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=400&auto=format&fit=crop&q=80',
                'slug': prop.slug,
                'address': prop.address,
            })

        # Filter out properties without coordinates
        properties_data = [p for p in properties_data if p['lat'] and p['lng']]

        context = {
            'properties': json.dumps(properties_data),
            'properties_count': len(properties_data),
        }

        return render(request, self.template_name, context)


class PropertyMapDataView(View):
    """
    AJAX endpoint for getting property data for the map
    """
    def get(self, request, *args, **kwargs):
        # Get filter parameters
        property_type = request.GET.get('type', '')
        search_query = request.GET.get('search', '')
        min_price = request.GET.get('min_price', '')
        max_price = request.GET.get('max_price', '')

        # Get all active properties
        properties = Property.objects.filter(
            is_active=True,
            status=PropertyStatus.AVAILABLE
        )

        # Apply filters
        if property_type and property_type != 'all':
            properties = properties.filter(property_type=property_type)

        if search_query:
            properties = properties.filter(
                Q(title__icontains=search_query) |
                Q(city__icontains=search_query) |
                Q(state__icontains=search_query) |
                Q(address__icontains=search_query)
            )

        if min_price:
            try:
                properties = properties.filter(price__gte=float(min_price))
            except (ValueError, TypeError):
                pass

        if max_price:
            try:
                properties = properties.filter(price__lte=float(max_price))
            except (ValueError, TypeError):
                pass

        # Prepare data for the map
        properties_data = []
        for prop in properties:
            # Get the first image or use a placeholder
            main_image = prop.main_image.url if prop.main_image else None

            properties_data.append({
                'id': prop.id,
                'name': prop.title,
                'type': prop.property_type,
                'location': f"{prop.city}, {prop.state}",
                'lat': float(prop.latitude) if prop.latitude else None,
                'lng': float(prop.longitude) if prop.longitude else None,
                'price': float(prop.price),
                'beds': prop.bedrooms,
                'baths': float(prop.bathrooms),
                'rating': 4.5,
                'dist': '0.5 km',
                'img': main_image or 'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=400&auto=format&fit=crop&q=80',
                'slug': prop.slug,
                'address': prop.address,
            })

        # Filter out properties without coordinates
        properties_data = [p for p in properties_data if p['lat'] and p['lng']]

        return JsonResponse({
            'properties': properties_data,
            'count': len(properties_data)
        })


# move
from .models import MoveRequest, MoveChecklistItem, MoveOffer, MoveOfferStatus
from .utils import haversine_km, estimate_eta_minutes
from django.contrib.auth.mixins import UserPassesTestMixin
from decimal import Decimal, InvalidOperation
class SubmitMoveRequestView(LoginRequiredMixin, View):
    """View for submitting a move request"""

    def post(self, request):
        user = request.user

        # Get form data
        moving_from = request.POST.get('moving_from')
        moving_from_lat = request.POST.get('moving_from_lat')
        moving_from_lng = request.POST.get('moving_from_lng')

        moving_to_property_id = request.POST.get('moving_to_property')
        moving_to_manual = request.POST.get('moving_to_manual')
        moving_to_lat = request.POST.get('moving_to_lat')
        moving_to_lng = request.POST.get('moving_to_lng')

        move_date = request.POST.get('move_date')
        move_time = request.POST.get('move_time')
        items = request.POST.getlist('items')
        special_instructions = request.POST.get('special_instructions', '')
        request_mover = request.POST.get('request_mover') == 'on'
        movers_count = request.POST.get('movers_count', 2)
        estimated_hours = request.POST.get('estimated_hours', 4)
        mover_notes = request.POST.get('mover_notes', '')

        # Validate
        if not moving_from or not move_date:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('my_profile')

        # Get property if selected
        moving_to_property = None
        if moving_to_property_id and moving_to_property_id != 'other':
            try:
                moving_to_property = Property.objects.get(id=moving_to_property_id)
            except Property.DoesNotExist:
                pass

        # Create move request
        try:
            movers_count = int(movers_count) if request_mover else 0
        except (TypeError, ValueError):
            movers_count = 2
        try:
            estimated_hours = int(estimated_hours) if request_mover else 0
        except (TypeError, ValueError):
            estimated_hours = 4

        move_request = MoveRequest.objects.create(
            user=user,
            moving_from=moving_from,
            moving_from_lat=moving_from_lat or None,
            moving_from_lng=moving_from_lng or None,
            moving_to_property=moving_to_property,
            moving_to_manual=moving_to_manual if moving_to_property_id == 'other' else '',
            moving_to_lat=moving_to_lat or None,
            moving_to_lng=moving_to_lng or None,
            move_date=move_date,
            move_time=move_time,
            items=items,
            items_list=', '.join(items) if items else 'No items specified',
            special_instructions=special_instructions,
            request_mover=request_mover,
            movers_count=movers_count,
            estimated_hours=estimated_hours,
            mover_notes=mover_notes if request_mover else '',
        )

        messages.success(request, 'Move request submitted successfully!')
        return redirect('my_profile')


class CancelMoveRequestView(LoginRequiredMixin, View):
    """View for cancelling a move request"""

    def post(self, request, pk):
        move_request = get_object_or_404(MoveRequest, pk=pk, user=request.user)
        if move_request.status == 'pending':
            move_request.status = 'cancelled'
            move_request.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'Cannot cancel this request'})


class ChecklistToggleView(LoginRequiredMixin, View):
    """Toggle a moving checklist item's done state"""

    def post(self, request, pk):
        item = get_object_or_404(MoveChecklistItem, pk=pk, user=request.user)
        item.done = not item.done
        item.save()

        total = MoveChecklistItem.objects.filter(user=request.user).count()
        done = MoveChecklistItem.objects.filter(user=request.user, done=True).count()
        percentage = round((done / total) * 100) if total else 0

        return JsonResponse({
            'success': True,
            'done': item.done,
            'progress': done,
            'total': total,
            'percentage': percentage,
        })


class ChecklistAddView(LoginRequiredMixin, View):
    """Add a new moving checklist item"""

    def post(self, request):
        text = request.POST.get('text', '').strip()
        if not text:
            return JsonResponse({'success': False, 'error': 'Task text is required'}, status=400)

        last_order = MoveChecklistItem.objects.filter(user=request.user).count()
        item = MoveChecklistItem.objects.create(user=request.user, text=text[:255], order=last_order)

        total = MoveChecklistItem.objects.filter(user=request.user).count()
        done = MoveChecklistItem.objects.filter(user=request.user, done=True).count()
        percentage = round((done / total) * 100) if total else 0

        return JsonResponse({
            'success': True,
            'id': item.pk,
            'text': item.text,
            'progress': done,
            'total': total,
            'percentage': percentage,
        })


class ChecklistDeleteView(LoginRequiredMixin, View):
    """Delete a moving checklist item"""

    def post(self, request, pk):
        item = get_object_or_404(MoveChecklistItem, pk=pk, user=request.user)
        item.delete()

        total = MoveChecklistItem.objects.filter(user=request.user).count()
        done = MoveChecklistItem.objects.filter(user=request.user, done=True).count()
        percentage = round((done / total) * 100) if total else 0

        return JsonResponse({
            'success': True,
            'progress': done,
            'total': total,
            'percentage': percentage,
        })

class ContactView(View):
    """Public Contact Us page - anyone can submit, no login required"""
    template_name = 'home/contact.html'

    def get(self, request):
        initial = {}
        if request.user.is_authenticated:
            initial['name'] = request.user.get_full_name() or request.user.username
            initial['email'] = request.user.email
            if hasattr(request.user, 'profile'):
                initial['phone'] = request.user.profile.phone_number
        form = ContactForm(initial=initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_message = form.save(commit=False)
            if request.user.is_authenticated:
                contact_message.user = request.user
            contact_message.save()

            # Best-effort notification email - never blocks the user-facing
            # success response if email sending fails (e.g. no SMTP configured yet)
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                send_mail(
                    subject=f"[2Hame Contact] {contact_message.get_subject_display()} from {contact_message.name}",
                    message=(
                        f"From: {contact_message.name} <{contact_message.email}>\n"
                        f"Phone: {contact_message.phone or 'Not provided'}\n\n"
                        f"{contact_message.message}"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    fail_silently=True,
                )
            except Exception:
                pass

            messages.success(
                request,
                "Thanks for reaching out! We've received your message and will get back to you shortly."
            )
            return redirect('home:contact')

        messages.error(request, "Please correct the errors below.")
        return render(request, self.template_name, {'form': form})


class MoverDetailView(LoginRequiredMixin, DetailView):
    """Public mover portfolio page - trust score, bio, service areas"""
    model = Profile
    template_name = 'home/mover_detail.html'
    context_object_name = 'mover_profile'
    slug_field = 'user__username'
    slug_url_kwarg = 'username'

    def get_queryset(self):
        return Profile.objects.filter(role='mover', is_active=True, user__is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.object
        context['trust_score'] = profile.get_trust_score()
        context['completed_moves'] = profile.completed_moves_count()
        context['service_areas'] = profile.get_mover_service_areas_list()
        return context


class MoversNearbyDataView(LoginRequiredMixin, View):
    """JSON feed of movers with a set base location, for the property map search"""

    def get(self, request):
        movers = Profile.objects.filter(
            role='mover', is_active=True, user__is_active=True,
            mover_base_lat__isnull=False, mover_base_lng__isnull=False,
        ).select_related('user')

        data = []
        for m in movers:
            data.append({
                'username': m.user.username,
                'name': m.get_full_name(),
                'lat': float(m.mover_base_lat),
                'lng': float(m.mover_base_lng),
                'label': m.mover_base_label or m.city,
                'vehicle': m.get_mover_vehicle_type_display() if m.mover_vehicle_type else 'Mover',
                'trust_score': m.get_trust_score(),
                'completed_moves': m.completed_moves_count(),
            })
        return JsonResponse({'movers': data})


class MoverMapView(LoginRequiredMixin, TemplateView):
    """
    Uber-style map for movers: shows open move requests (house hunters who
    need help moving) as pins so a mover can browse and commit to one.
    """
    template_name = 'map/mover_map.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_mover'] = hasattr(self.request.user, 'profile') and self.request.user.profile.is_mover()
        return context


class MoverMapDataView(LoginRequiredMixin, View):
    """JSON feed of open move requests (pending, wants a mover, not yet matched)"""

    def get(self, request):
        requests = MoveRequest.objects.filter(
            request_mover=True,
            status='pending',
            moving_from_lat__isnull=False,
            moving_from_lng__isnull=False,
        ).exclude(user=request.user).select_related('user', 'moving_to_property')

        data = []
        for mr in requests:
            already_committed = mr.offers.filter(mover=request.user).exclude(status=MoveOfferStatus.WITHDRAWN).exists()
            data.append({
                'id': mr.id,
                'from_lat': float(mr.moving_from_lat),
                'from_lng': float(mr.moving_from_lng),
                'to_lat': float(mr.moving_to_lat) if mr.moving_to_lat else None,
                'to_lng': float(mr.moving_to_lng) if mr.moving_to_lng else None,
                'moving_from': mr.moving_from,
                'moving_to': mr.moving_to_property.title if mr.moving_to_property else mr.moving_to_manual,
                'move_date': mr.move_date.strftime('%b %d, %Y'),
                'move_time': mr.get_move_time_display(),
                'movers_count': mr.movers_count,
                'estimated_hours': mr.estimated_hours,
                'items': mr.get_items_display(),
                'mover_notes': mr.mover_notes,
                'offers_count': mr.open_offers_count(),
                'already_committed': already_committed,
            })
        return JsonResponse({'requests': data})


class CommitMoveOfferView(LoginRequiredMixin, View):
    """A mover commits (bids) on a move request with their price and live location"""

    def post(self, request, pk):
        profile = getattr(request.user, 'profile', None)
        if not profile or not profile.is_mover():
            return JsonResponse({'success': False, 'error': 'Only users with the Mover role can commit to a move.'}, status=403)

        move_request = get_object_or_404(MoveRequest, pk=pk, request_mover=True)
        if move_request.status != 'pending':
            return JsonResponse({'success': False, 'error': 'This move request is no longer open.'}, status=400)
        if move_request.user_id == request.user.id:
            return JsonResponse({'success': False, 'error': "You can't commit to your own move request."}, status=400)

        price_raw = request.POST.get('price')
        lat = request.POST.get('lat')
        lng = request.POST.get('lng')

        try:
            price = Decimal(price_raw)
            if price <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError):
            return JsonResponse({'success': False, 'error': 'Enter a valid price.'}, status=400)

        distance_km = None
        eta_minutes = None
        if lat and lng and move_request.moving_from_lat and move_request.moving_from_lng:
            try:
                distance_km = round(haversine_km(lat, lng, move_request.moving_from_lat, move_request.moving_from_lng), 2)
                eta_minutes = estimate_eta_minutes(distance_km)
            except (ValueError, TypeError):
                pass

        offer, created = MoveOffer.objects.update_or_create(
            move_request=move_request,
            mover=request.user,
            defaults={
                'price': price,
                'status': MoveOfferStatus.PENDING,
                'mover_lat': lat or None,
                'mover_lng': lng or None,
                'distance_km': distance_km,
                'eta_minutes': eta_minutes,
            }
        )

        return JsonResponse({
            'success': True,
            'offer_id': offer.pk,
            'distance_km': float(distance_km) if distance_km is not None else None,
            'eta_minutes': eta_minutes,
        })


class WithdrawMoveOfferView(LoginRequiredMixin, View):
    """A mover withdraws their own pending offer"""

    def post(self, request, pk):
        offer = get_object_or_404(MoveOffer, pk=pk, mover=request.user)
        if offer.status == MoveOfferStatus.PENDING:
            offer.status = MoveOfferStatus.WITHDRAWN
            offer.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'This offer can no longer be withdrawn.'}, status=400)


class MoveRequestOffersView(LoginRequiredMixin, View):
    """
    Polling endpoint: the house hunter's page calls this periodically to get
    a live-ish view of who has committed to their move request.
    """

    def get(self, request, pk):
        move_request = get_object_or_404(MoveRequest, pk=pk, user=request.user)
        offers = move_request.offers.exclude(status=MoveOfferStatus.WITHDRAWN).select_related('mover', 'mover__profile')

        data = []
        for offer in offers:
            mover_profile = getattr(offer.mover, 'profile', None)
            data.append({
                'id': offer.pk,
                'mover_name': mover_profile.get_full_name() if mover_profile else offer.mover.username,
                'price': float(offer.price),
                'distance_km': float(offer.distance_km) if offer.distance_km is not None else None,
                'eta_minutes': offer.eta_minutes,
                'status': offer.status,
                'created_at': offer.created_at.strftime('%H:%M'),
            })

        return JsonResponse({
            'move_request_status': move_request.status,
            'offers': data,
        })


class AcceptMoveOfferView(LoginRequiredMixin, View):
    """The house hunter accepts one mover's offer, dropping all the others"""

    def post(self, request, pk):
        offer = get_object_or_404(MoveOffer, pk=pk, move_request__user=request.user)
        if offer.status != MoveOfferStatus.PENDING:
            return JsonResponse({'success': False, 'error': 'This offer is no longer available.'}, status=400)

        offer.accept()
        messages.success(request, f"You've matched with {offer.mover.get_full_name() or offer.mover.username} for your move!")
        return JsonResponse({'success': True})
