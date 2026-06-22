from django.contrib import admin
from .models import Property

@admin.register(Property)
class AdminProperty(admin.ModelAdmin):
    list_display = ("title", 'property_type', "address", "city", "country", "bedrooms", "price")

    