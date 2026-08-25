from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_profile_owner_about_heading_profile_owner_brand_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='owner_tiktok_url',
            field=models.URLField(blank=True),
        ),
    ]
