# apps/properties/management/commands/seed_data.py
import random
import os
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from django.core.files.base import ContentFile
from faker import Faker

from properties.models import (
    Property, PropertyType, PropertyStatus, Amenity,
    PropertyImage, Unit, Booking
)
from clients.models import Client, ClientType
from contracts.models import Contract, ContractType, ContractStatus
from payments.models import Invoice, Payment, PaymentMethod, PaymentStatus, PaymentCategory

fake = Faker()


class Command(BaseCommand):
    help = 'Seed the database with realistic test data for Real Estate Management System'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=5,
            help='Number of users to create (default: 5)'
        )
        parser.add_argument(
            '--properties',
            type=int,
            default=20,
            help='Number of properties to create (default: 20)'
        )
        parser.add_argument(
            '--clients',
            type=int,
            default=30,
            help='Number of clients to create (default: 30)'
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Clean existing data before seeding'
        )

    def handle(self, *args, **options):
        if options['clean']:
            self.clean_data()

        self.stdout.write(self.style.SUCCESS('Starting data seeding...'))

        # Create users
        users = self.create_users(options['users'])

        # Create amenities
        amenities = self.create_amenities()

        # Create clients
        clients = self.create_clients(options['clients'])

        # Create properties
        properties = self.create_properties(options['properties'], users, amenities)

        # Create property images
        self.create_property_images(properties)

        # Create units for properties (especially for hotels and schools)
        self.create_units(properties)

        # Create bookings
        self.create_bookings(properties, clients)

        # Create contracts
        contracts = self.create_contracts(properties, clients, users)

        # Create invoices and payments
        self.create_invoices_and_payments(contracts, clients, users)

        self.stdout.write(self.style.SUCCESS(f'''
        ========================================
        Data Seeding Complete!
        ========================================
        Users created: {options['users']}
        Properties created: {options['properties']}
        Clients created: {options['clients']}
        Amenities created: {len(amenities)}
        ========================================
        '''))

    def clean_data(self):
        """Delete existing data from all tables"""
        self.stdout.write('Cleaning existing data...')

        # Order matters due to foreign key constraints
        Booking.objects.all().delete()
        PropertyImage.objects.all().delete()
        Unit.objects.all().delete()
        Property.objects.all().delete()
        Amenity.objects.all().delete()

        # Delete non-superuser users
        User.objects.filter(is_superuser=False).delete()

        self.stdout.write(self.style.SUCCESS('Data cleaned successfully'))

    def create_users(self, count):
        """Create regular users"""
        self.stdout.write('Creating users...')
        users = []

        # Create superuser if not exists
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write('Superuser created: admin/admin123')

        # Create regular users
        for i in range(count):
            first_name = fake.first_name()
            last_name = fake.last_name()
            username = f"{first_name.lower()}.{last_name.lower()}{i}"
            email = fake.email()

            user = User.objects.create_user(
                username=username,
                email=email,
                password='password123',
                first_name=first_name,
                last_name=last_name
            )
            users.append(user)

        self.stdout.write(f'Created {count} users')
        return users

    def create_amenities(self):
        """Create common amenities"""
        self.stdout.write('Creating amenities...')

        amenities_data = [
            ('WiFi', 'fa-wifi', 'High-speed internet access'),
            ('Parking', 'fa-parking', 'Free parking available'),
            ('Pool', 'fa-swimming-pool', 'Swimming pool'),
            ('Gym', 'fa-dumbbell', 'Fitness center'),
            ('Air Conditioning', 'fa-snowflake', 'Central AC'),
            ('Heating', 'fa-fire', 'Central heating'),
            ('Kitchen', 'fa-utensils', 'Full kitchen'),
            ('Washer/Dryer', 'fa-tshirt', 'In-unit laundry'),
            ('Pet Friendly', 'fa-paw', 'Pets allowed'),
            ('TV', 'fa-tv', 'Smart TV with streaming'),
            ('Breakfast', 'fa-coffee', 'Free breakfast included'),
            ('Room Service', 'fa-concierge-bell', '24/7 room service'),
            ('Spa', 'fa-spa', 'Spa and wellness center'),
            ('Conference Room', 'fa-chalkboard', 'Meeting facilities'),
            ('Playground', 'fa-child', 'Children playground'),
        ]

        amenities = []
        for name, icon, desc in amenities_data:
            amenity, created = Amenity.objects.get_or_create(
                name=name,
                defaults={'icon': icon, 'description': desc}
            )
            amenities.append(amenity)

        self.stdout.write(f'Created/Found {len(amenities)} amenities')
        return amenities

    def generate_property_image(self, property_type, width=800, height=600):
        """Generate a realistic property image using Pillow"""
        # Create image with gradient background
        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)

        # Color schemes based on property type
        color_schemes = {
            PropertyType.BNB: [(139, 69, 19), (255, 215, 0)],  # Brown/Gold
            PropertyType.HOTEL: [(25, 25, 112), (100, 149, 237)],  # Midnight Blue/Cornflower
            PropertyType.SCHOOL: [(139, 0, 0), (255, 99, 71)],  # Firebrick/Tomato
            PropertyType.RESIDENTIAL: [(34, 139, 34), (144, 238, 144)],  # Forest Green/Light Green
            PropertyType.COMMERCIAL: [(70, 130, 180), (176, 224, 230)],  # Steel Blue/Powder Blue
            PropertyType.LAND: [(101, 67, 33), (222, 184, 135)],  # Brown/Burlywood
            PropertyType.INDUSTRIAL: [(105, 105, 105), (192, 192, 192)],  # Dim Gray/Silver
        }

        colors = color_schemes.get(property_type, color_schemes[PropertyType.RESIDENTIAL])

        # Draw gradient background
        for i in range(height):
            r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * (i / height))
            g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * (i / height))
            b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * (i / height))
            draw.line([(0, i), (width, i)], fill=(r, g, b))

        # Draw building/windows pattern
        building_width = width // 3
        building_height = height // 2
        building_x = (width - building_width) // 2
        building_y = (height - building_height) // 2

        # Building outline
        draw.rectangle(
            [building_x, building_y, building_x + building_width, building_y + building_height],
            outline=(255, 255, 255),
            width=3
        )

        # Draw windows
        window_size = 40
        for row in range(2):
            for col in range(3):
                window_x = building_x + 20 + col * 60
                window_y = building_y + 30 + row * 60
                draw.rectangle(
                    [window_x, window_y, window_x + window_size, window_y + window_size],
                    fill=(255, 255, 200),
                    outline=(255, 255, 255),
                    width=2
                )

        # Draw roof
        roof_points = [
            (building_x - 10, building_y),
            (building_x + building_width // 2, building_y - 40),
            (building_x + building_width + 10, building_y)
        ]
        draw.polygon(roof_points, fill=(200, 100, 100), outline=(255, 255, 255))

        # Add text label
        try:
            # Try to use a default font
            font = ImageFont.load_default()
        except:
            font = None

        label = property_type.replace('_', ' ').title()
        text_bbox = draw.textbbox((0, 0), label, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (width - text_width) // 2
        draw.text((text_x, height - 50), label, fill=(255, 255, 255), font=font)

        # Convert to bytes
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)

        return ContentFile(buffer.read(), f'property_{hash(buffer.getvalue())}.jpg')

    def create_properties(self, count, users, amenities):
        """Create property listings"""
        self.stdout.write('Creating properties...')
        properties = []

        cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix',
                 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'Austin',
                 'Miami', 'Seattle', 'Denver', 'Boston', 'Nashville']

        property_titles = {
            PropertyType.BNB: ['Cozy Retreat', 'Luxury Suite', 'Garden View', 'Beach House', 'Mountain Lodge'],
            PropertyType.HOTEL: ['Grand Plaza', 'Seaside Resort', 'City Central', 'Luxury Towers', 'Executive Stay'],
            PropertyType.SCHOOL: ['Sunrise Academy', 'Riverside School', 'Innovation Center', 'Learning Hub', 'Smart Campus'],
            PropertyType.RESIDENTIAL: ['Modern Apartment', 'Family Home', 'Luxury Condo', 'Townhouse', 'Villa Estate'],
            PropertyType.COMMERCIAL: ['Business Center', 'Retail Space', 'Office Complex', 'Corporate Hub', 'Shopping Plaza'],
            PropertyType.LAND: ['Development Land', 'Agricultural Land', 'Hillside Property', 'Lakefront Land', 'Urban Plot'],
            PropertyType.INDUSTRIAL: ['Warehouse District', 'Industrial Park', 'Manufacturing Hub', 'Logistics Center', 'Factory Complex'],
        }

        for i in range(count):
            property_type = random.choice(list(PropertyType))
            titles = property_titles.get(property_type, ['Property'])
            title = f"{random.choice(titles)} {i+1}"

            city = random.choice(cities)
            state = fake.state()

            # Create property
            property = Property.objects.create(
                title=title,
                property_type=property_type,
                status=random.choice([PropertyStatus.AVAILABLE, PropertyStatus.RENTED]),
                address=fake.street_address(),
                city=city,
                state=state,
                zip_code=fake.zipcode(),
                country='USA',
                latitude=float(fake.latitude()),
                longitude=float(fake.longitude()),
                description=fake.paragraph(nb_sentences=5),
                area_sqft=Decimal(random.randint(500, 5000)),
                bedrooms=random.randint(1, 6),
                bathrooms=Decimal(random.randint(1, 4)),
                floor_number=random.randint(0, 10),
                total_floors=random.randint(1, 15),
                year_built=random.randint(1950, 2023),
                price=Decimal(random.randint(500, 10000)),
                security_deposit=Decimal(random.randint(500, 5000)),
                maintenance_fee=Decimal(random.randint(0, 500)),
                owner=random.choice(users),
                agent=random.choice(users) if random.choice([True, False]) else None,
                available_from=timezone.now(),
                minimum_lease_days=random.choice([30, 90, 180, 365]),
            )

            # Add random amenities
            property.amenities.add(*random.sample(amenities, k=random.randint(3, 8)))

            # Generate and save main image
            image_content = self.generate_property_image(property_type)
            property.main_image.save(f'main_{property.slug}.jpg', image_content, save=True)

            properties.append(property)

            if (i + 1) % 5 == 0:
                self.stdout.write(f'  Created {i + 1}/{count} properties')

        return properties

    def create_property_images(self, properties):
        """Create gallery images for properties"""
        self.stdout.write('Creating property gallery images...')

        for property in properties:
            # Create 2-5 gallery images per property
            num_images = random.randint(2, 5)
            for i in range(num_images):
                image_content = self.generate_property_image(property.property_type)

                PropertyImage.objects.create(
                    property=property,
                    caption=fake.sentence(),
                    is_primary=(i == 0),
                    order=i
                ).image.save(f'gallery_{property.slug}_{i}.jpg', image_content, save=True)

        self.stdout.write(f'Created gallery images for {len(properties)} properties')

    def create_units(self, properties):
        """Create units for properties (especially hotels and schools)"""
        self.stdout.write('Creating property units...')
        units_created = 0

        for property in properties:
            if property.property_type in [PropertyType.HOTEL, PropertyType.SCHOOL, PropertyType.BNB]:
                # Create 5-20 units for hotels/schools
                num_units = random.randint(5, 20)

                for i in range(num_units):
                    Unit.objects.create(
                        property=property,
                        unit_number=f"{random.choice(['A', 'B', 'C', 'D', 'E'])}{i+1:03d}",
                        floor=random.randint(1, property.total_floors),
                        bedrooms=random.randint(0, 3),
                        bathrooms=Decimal(random.randint(1, 3)),
                        area_sqft=Decimal(random.randint(200, 2000)),
                        price_modifier=Decimal(random.randint(-200, 500)),
                        is_available=random.choice([True, False]),
                    )
                    units_created += 1

        self.stdout.write(f'Created {units_created} units')

    def create_clients(self, count):
        """Create client records"""
        self.stdout.write('Creating clients...')
        clients = []

        client_types = [ClientType.TENANT, ClientType.BUYER, ClientType.OWNER, ClientType.INVESTOR]

        for i in range(count):
            user = User.objects.create_user(
                username=f"client_{i+1}",
                email=fake.email(),
                password='client123',
                first_name=fake.first_name(),
                last_name=fake.last_name()
            )

            client = Client.objects.create(
                user=user,
                client_type=random.choice(client_types),
                name=f"{user.first_name} {user.last_name}",
                email=user.email,
                phone=fake.phone_number(),
                address=fake.street_address(),
                city=fake.city(),
                state=fake.state(),
                zip_code=fake.zipcode(),
                occupation=fake.job(),
                employer=fake.company(),
                annual_income=Decimal(random.randint(30000, 200000)),
                preferred_property_types=random.choice(['bnb,hotel', 'residential', 'commercial', 'all']),
                budget_min=Decimal(random.randint(500, 2000)),
                budget_max=Decimal(random.randint(2000, 10000)),
                notes=fake.paragraph(),
                created_by=User.objects.first()
            )
            clients.append(client)

        self.stdout.write(f'Created {count} clients')
        return clients

    def create_bookings(self, properties, clients):
        """Create bookings"""
        self.stdout.write('Creating bookings...')
        bookings_created = 0

        for property in properties:
            if property.property_type in [PropertyType.BNB, PropertyType.HOTEL]:
                num_bookings = random.randint(0, 10)

                for _ in range(num_bookings):
                    client = random.choice(clients)
                    check_in = timezone.now().date() + timedelta(days=random.randint(1, 60))
                    check_out = check_in + timedelta(days=random.randint(1, 14))
                    nights = (check_out - check_in).days

                    unit = property.units.first() if property.units.exists() else None

                    Booking.objects.create(
                        property=property,
                        unit=unit,
                        check_in_date=check_in,
                        check_out_date=check_out,
                        guests_count=random.randint(1, 6),
                        total_price=property.price * nights,
                        status=random.choice(['pending', 'confirmed', 'checked_in', 'checked_out']),
                        special_requests=fake.sentence() if random.choice([True, False]) else ''
                    )
                    bookings_created += 1

        self.stdout.write(f'Created {bookings_created} bookings')

    def create_contracts(self, properties, clients, users):
        """Create contracts"""
        self.stdout.write('Creating contracts...')
        contracts = []

        # Create a mapping of users to clients (for owner assignment)
        user_to_client = {}
        for client in clients:
            if client.user:
                user_to_client[client.user.id] = client

        for property in properties[:50]:  # Create contracts for first 50 properties
            if random.choice([True, False]):
                client = random.choice(clients)
                start_date = timezone.now().date()
                end_date = start_date + timedelta(days=random.randint(90, 730))

                # Find the client that matches the property owner
                owner_client = None
                if property.owner and property.owner.id in user_to_client:
                    owner_client = user_to_client[property.owner.id]

                # If no matching client found, create one or use a random client
                if not owner_client:
                    # Option 1: Use a random client as owner
                    owner_client = random.choice(clients)

                contract = Contract.objects.create(
                    contract_type=random.choice([ContractType.LEASE, ContractType.BOOKING]),
                    status=random.choice([ContractStatus.ACTIVE, ContractStatus.DRAFT, ContractStatus.PENDING]),
                    property=property,
                    client=client,
                    owner=owner_client,  # Now this is a Client object, not a User
                    monthly_rent=property.price,
                    security_deposit=property.security_deposit,
                    start_date=start_date,
                    end_date=end_date,
                    payment_due_day=random.randint(1, 28),
                    notice_period_days=30,
                    late_fee_amount=Decimal(random.randint(25, 100)),
                    special_terms=fake.paragraph() if random.choice([True, False]) else '',
                    utilities_included=random.choice([True, False]),
                    parking_included=random.choice([True, False]),
                    pets_allowed=random.choice([True, False]),
                    created_by=random.choice(users)
                )
                contracts.append(contract)

                if len(contracts) % 10 == 0:
                    self.stdout.write(f'  Created {len(contracts)} contracts')

        self.stdout.write(f'Created {len(contracts)} contracts')
        return contracts

    def create_invoices_and_payments(self, contracts, clients, users):
        """Create invoices and payments"""
        self.stdout.write('Creating invoices and payments...')
        invoices_created = 0
        payments_created = 0

        for contract in contracts[:30]:  # Create for first 30 contracts
            if contract.status == ContractStatus.ACTIVE:
                # Create 1-6 months of invoices
                months = random.randint(1, 6)
                current_date = contract.start_date

                for month in range(months):
                    period_start = current_date.replace(day=1)
                    if month == months - 1:
                        period_end = min(contract.end_date, current_date + timedelta(days=30))
                    else:
                        period_end = period_start + timedelta(days=30)

                    invoice = Invoice.objects.create(
                        contract=contract,
                        client=contract.client,
                        property=contract.property,
                        amount=contract.monthly_rent,
                        tax_amount=contract.monthly_rent * Decimal('0.08'),
                        discount_amount=Decimal(random.randint(0, 100)) if random.choice([True, False]) else 0,
                        due_date=period_start + timedelta(days=contract.payment_due_day),
                        category=PaymentCategory.RENT,
                        period_start=period_start,
                        period_end=period_end,
                        description=f"Rent for {period_start.strftime('%B %Y')}",
                        created_by=random.choice(users)
                    )
                    invoices_created += 1

                    # Create payment for 70% of invoices
                    if random.random() < 0.7:
                        Payment.objects.create(
                            invoice=invoice,
                            client=contract.client,
                            amount=invoice.total_amount,
                            payment_method=random.choice(list(PaymentMethod)),
                            payment_date=invoice.due_date - timedelta(days=random.randint(-5, 5)),
                            reference_number=f"REF-{random.randint(10000, 99999)}",
                            status=PaymentStatus.PAID,
                            processed_by=random.choice(users)
                        )
                        payments_created += 1

                    current_date = period_end + timedelta(days=1)

        self.stdout.write(f'Created {invoices_created} invoices and {payments_created} payments')