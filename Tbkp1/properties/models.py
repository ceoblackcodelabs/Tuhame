# apps/properties/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import slugify

User = get_user_model()


class PropertyType(models.TextChoices):
    BNB = 'bnb', 'Bed & Breakfast'
    HOTEL = 'hotel', 'Hotel'
    SCHOOL = 'school', 'School'
    RESIDENTIAL = 'residential', 'Residential'
    COMMERCIAL = 'commercial', 'Commercial'
    LAND = 'land', 'Land'
    INDUSTRIAL = 'industrial', 'Industrial'


class PropertyStatus(models.TextChoices):
    AVAILABLE = 'available', 'Available'
    RENTED = 'rented', 'Rented'
    SOLD = 'sold', 'Sold'
    MAINTENANCE = 'maintenance', 'Under Maintenance'
    RESERVED = 'reserved', 'Reserved'


class Amenity(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Amenities"

    def __str__(self):
        return self.name


class Property(models.Model):
    # Basic Info
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    status = models.CharField(max_length=20, choices=PropertyStatus.choices, default=PropertyStatus.AVAILABLE)

    # Location
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='USA')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    # Property Details
    description = models.TextField()
    area_sqft = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    bedrooms = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    floor_number = models.IntegerField(default=0)
    total_floors = models.IntegerField(default=1)
    year_built = models.IntegerField(blank=True, null=True)

    # Financial
    price = models.DecimalField(max_digits=12, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    maintenance_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Ownership
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='owned_properties')
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_properties')

    # Amenities
    amenities = models.ManyToManyField(Amenity, blank=True)

    # Media
    main_image = models.ImageField(upload_to='properties/main/', blank=True, null=True)

    # Availability
    available_from = models.DateField(default=timezone.now)
    minimum_lease_days = models.IntegerField(default=30)
    maximum_lease_days = models.IntegerField(blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['property_type', 'status']),
            models.Index(fields=['city', 'state']),
            models.Index(fields=['price']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_property_type_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='properties/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

class PropertyReview(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='property_reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['property', 'user']

    def __str__(self):
        return f"Review by {self.user.username} for {self.property.title}"


class Unit(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='units')
    unit_number = models.CharField(max_length=50)
    floor = models.IntegerField(default=1)
    bedrooms = models.IntegerField(default=0)
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    area_sqft = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    price_modifier = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=PropertyStatus.choices, default=PropertyStatus.AVAILABLE)

    class Meta:
        unique_together = ['property', 'unit_number']

    def __str__(self):
        return f"{self.property.title} - Unit {self.unit_number}"


class Booking(models.Model):
    BOOKING_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookings')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='bookings', null=True, blank=True)
    client = models.ForeignKey(
        'clients.Client', on_delete=models.CASCADE, related_name='bookings',
        null=True, blank=True
    )
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    guests_count = models.IntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='pending')
    special_requests = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['check_in_date']

    def __str__(self):
        client_name = self.client.name if self.client else 'Unknown client'
        return f"Booking for {client_name} - {self.property.title}"


