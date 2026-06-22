from django.shortcuts import render
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from properties.models import Property

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


class PropertyMapSearchListView(ListView):
    model = Property
    context_object_name = "properties"
    paginate_by = 3
    template_name = "home/properties/map.html"