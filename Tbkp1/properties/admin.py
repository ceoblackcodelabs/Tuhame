from django.contrib import admin
from .models import Property, PropertyImage, Amenity

@admin.register(Property)
class AdminProperty(admin.ModelAdmin):
    list_display = ("title", 'property_type', "address", "city", "country", "bedrooms", "price")


@admin.register(PropertyImage)
class AdminPropertyImage(admin.ModelAdmin):
    list_display = ("property", "caption", "is_primary", "order")

@admin.register(Amenity)
class AdminAmenities(admin.ModelAdmin):
    list_display = ("name", "icon", "description")