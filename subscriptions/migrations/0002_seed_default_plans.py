from django.db import migrations


# Seeds the three default plans referenced when this feature was requested:
# Free (current default for every owner), Monthly, and Annual at KES 15,000
# (the figure given). The monthly price wasn't specified, so it's set here
# as an editable placeholder (KES 1,500) - change it any time from
# Settings > Plans (admin only) without needing another migration.
def seed_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model('subscriptions', 'SubscriptionPlan')
    plans = [
        {
            'name': 'Free', 'slug': 'free', 'billing_period': 'free',
            'price': 0, 'description': 'Get started at no cost.', 'sort_order': 0,
        },
        {
            'name': 'Monthly', 'slug': 'monthly', 'billing_period': 'monthly',
            'price': 1500, 'description': 'Billed every month.', 'sort_order': 1,
        },
        {
            'name': 'Annual', 'slug': 'annual', 'billing_period': 'annual',
            'price': 15000, 'description': 'Billed once a year - best value.', 'sort_order': 2,
        },
    ]
    for data in plans:
        SubscriptionPlan.objects.get_or_create(slug=data['slug'], defaults=data)


def unseed_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model('subscriptions', 'SubscriptionPlan')
    SubscriptionPlan.objects.filter(slug__in=['free', 'monthly', 'annual']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_plans, unseed_plans),
    ]
