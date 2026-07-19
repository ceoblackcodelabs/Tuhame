# apps/properties/management/commands/seed_nairobi_properties.py
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from properties.models import Property, PropertyType, PropertyStatus, Amenity

User = get_user_model()

# Real Nairobi neighbourhoods with approximate center coordinates
NEIGHBOURHOODS = [
    ("Kilimani", -1.2833, 36.7833),
    ("Westlands", -1.2676, 36.8062),
    ("Karen", -1.3197, 36.7076),
    ("Lavington", -1.2762, 36.7692),
    ("Kileleshwa", -1.2833, 36.7667),
    ("Runda", -1.2167, 36.8167),
    ("South B", -1.3167, 36.8333),
    ("South C", -1.3333, 36.8167),
    ("Langata", -1.3667, 36.7333),
    ("Upper Hill", -1.2989, 36.8172),
    ("Parklands", -1.2611, 36.8125),
    ("Ngong Road", -1.3000, 36.7800),
    ("Kasarani", -1.2231, 36.8969),
    ("Embakasi", -1.3236, 36.8945),
    ("Nairobi CBD", -1.2864, 36.8172),
    ("Muthaiga", -1.2500, 36.8167),
    ("Gigiri", -1.2333, 36.8000),
    ("Kitisuru", -1.2333, 36.7833),
    ("Ridgeways", -1.2000, 36.8500),
    ("Donholm", -1.2939, 36.8794),
    ("Buruburu", -1.2833, 36.8667),
    ("Kileleshwa", -1.2800, 36.7700),
]

# (type, title template, price range KES, bedrooms range, bathrooms range, area range sqft)
LISTING_TEMPLATES = [
    (PropertyType.RESIDENTIAL, "Modern Apartment in {n}", (35000, 120000), (1, 3), (1, 2), (600, 1400)),
    (PropertyType.RESIDENTIAL, "Spacious Family House in {n}", (80000, 250000), (3, 5), (2, 4), (1800, 3500)),
    (PropertyType.RESIDENTIAL, "Cozy Studio in {n}", (18000, 35000), (0, 1), (1, 1), (350, 550)),
    (PropertyType.BNB, "Furnished BnB Suite in {n}", (3500, 9000), (1, 2), (1, 2), (500, 900)),
    (PropertyType.HOTEL, "Boutique Hotel Rooms in {n}", (6000, 15000), (1, 1), (1, 1), (300, 500)),
    (PropertyType.COMMERCIAL, "Prime Office Space in {n}", (150000, 500000), (0, 0), (2, 4), (2000, 6000)),
    (PropertyType.COMMERCIAL, "Retail Shopfront in {n}", (60000, 180000), (0, 0), (1, 2), (400, 1200)),
    (PropertyType.LAND, "Residential Plot in {n}", (3500000, 15000000), (0, 0), (0, 0), (4000, 12000)),
    (PropertyType.INDUSTRIAL, "Warehouse Space in {n}", (200000, 600000), (0, 0), (1, 2), (5000, 15000)),
    (PropertyType.SCHOOL, "School Premises in {n}", (250000, 700000), (0, 0), (4, 10), (8000, 20000)),
]

DESCRIPTIONS = [
    "A beautifully maintained property offering comfort, security, and easy access to major roads, "
    "shopping centres and schools. Perfect for professionals and families alike.",
    "Located in one of Nairobi's most sought-after neighbourhoods, this property combines modern "
    "finishes with a peaceful, secure environment.",
    "Bright, well-ventilated spaces with quality fittings throughout. Close to matatu routes, "
    "supermarkets and recreational facilities.",
    "An excellent investment opportunity in a rapidly growing area, with reliable water and power supply.",
    "Gated community living with round-the-clock security, backup water, and dedicated parking.",
]


class Command(BaseCommand):
    help = "Seed the database with realistic property listings across Nairobi, owned by the admin account"

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', type=int, default=24,
            help='Number of properties to create (default: 24)'
        )
        parser.add_argument(
            '--owner', type=str, default='admin',
            help='Username of the account that should own the seeded properties (default: admin)'
        )

    def handle(self, *args, **options):
        count = options['count']
        owner_username = options['owner']

        try:
            owner = User.objects.get(username=owner_username)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                f"No user found with username '{owner_username}'. "
                f"Create it first or pass --owner=<existing_username>."
            ))
            return

        amenities = list(Amenity.objects.all())
        if not amenities:
            self.stdout.write(self.style.WARNING("No Amenity records found - properties will be created without amenities."))

        created = 0
        for i in range(count):
            neighbourhood, base_lat, base_lng = random.choice(NEIGHBOURHOODS)
            prop_type, title_tpl, price_range, bed_range, bath_range, area_range = random.choice(LISTING_TEMPLATES)

            # Jitter the coordinates slightly so properties in the same
            # neighbourhood don't all stack on the exact same map pin
            lat = base_lat + random.uniform(-0.008, 0.008)
            lng = base_lng + random.uniform(-0.008, 0.008)

            title = title_tpl.format(n=neighbourhood)
            price = Decimal(random.randrange(price_range[0], price_range[1], 500))
            bedrooms = random.randint(*bed_range)
            bathrooms = Decimal(random.randint(bath_range[0] * 2, bath_range[1] * 2)) / 2 if bath_range[1] else Decimal('0')
            area_sqft = Decimal(random.randint(*area_range))

            slug_base = slugify(f"{title}-{neighbourhood}-{i}-{random.randint(1000,9999)}")

            prop = Property.objects.create(
                title=title,
                slug=slug_base,
                property_type=prop_type,
                status=PropertyStatus.AVAILABLE,
                address=f"{random.randint(1, 400)} {neighbourhood} Road",
                city="Nairobi",
                state="Nairobi County",
                zip_code="00100",
                country="Kenya",
                latitude=round(lat, 6),
                longitude=round(lng, 6),
                description=random.choice(DESCRIPTIONS),
                area_sqft=area_sqft,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                floor_number=random.randint(0, 8) if prop_type == PropertyType.RESIDENTIAL else 0,
                total_floors=random.randint(1, 12),
                year_built=random.randint(2005, 2024),
                price=price,
                security_deposit=price if prop_type != PropertyType.LAND else Decimal('0'),
                maintenance_fee=Decimal(random.randint(0, 5000)) if prop_type == PropertyType.RESIDENTIAL else Decimal('0'),
                owner=owner,
                is_active=True,
            )

            if amenities:
                prop.amenities.set(random.sample(amenities, k=min(len(amenities), random.randint(3, 7))))

            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Created {created} Nairobi properties owned by '{owner.username}'."
        ))
