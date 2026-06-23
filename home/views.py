from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from properties.models import Property, PropertyStatus, PropertyImage, PropertyType
from django.db import models
from .forms import ViewingScheduleForm
from django.contrib import messages

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

