from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from properties.models import Property

class HomeView(ListView):
    model = Property
    context_object_name = "properties"
    paginate_by = 3
    template_name = "home/index.html"