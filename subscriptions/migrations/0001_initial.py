from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SubscriptionPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(unique=True)),
                ('billing_period', models.CharField(choices=[('free', 'Free'), ('monthly', 'Monthly'), ('annual', 'Annual')], max_length=10)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('description', models.CharField(blank=True, help_text="Short line shown under the plan name, e.g. 'Unlimited listings, priority support'.", max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['sort_order', 'price'],
            },
        ),
        migrations.CreateModel(
            name='Offer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=150)),
                ('description', models.TextField(blank=True, help_text="Shown to owners on the Settings page, e.g. what's included.")),
                ('amount', models.DecimalField(decimal_places=2, help_text='Price in KES for this offer.', max_digits=10)),
                ('max_claims', models.PositiveIntegerField(help_text='How many users can grab this offer, e.g. 10.')),
                ('duration_months', models.PositiveIntegerField(help_text='How many months of access one claim covers, e.g. 24.')),
                ('is_active', models.BooleanField(default=True)),
                ('available_until', models.DateTimeField(blank=True, help_text='Optional cutoff date after which the offer can no longer be claimed, even if slots remain.', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='offers_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OfferClaim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('claimed_at', models.DateTimeField(auto_now_add=True)),
                ('offer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='claims', to='subscriptions.offer')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='offer_claims', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-claimed_at'],
                'unique_together': {('offer', 'user')},
            },
        ),
        migrations.CreateModel(
            name='OwnerSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_at', models.DateTimeField(blank=True, help_text='Blank/null means it never expires (Free plan).', null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('plan', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subscribers', to='subscriptions.subscriptionplan')),
                ('source_offer', models.ForeignKey(blank=True, help_text='Set if this subscription came from claiming an offer rather than a standard plan.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subscriptions', to='subscriptions.offer')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='subscription', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
