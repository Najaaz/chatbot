# Generated by Django 5.2 on 2025-05-01 20:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_alter_product_gender'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='seasonal_use',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
