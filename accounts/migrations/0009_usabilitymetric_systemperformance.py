from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0008_order_delivery_area_order_delivery_city_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='UsabilityMetric',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('login', 'Login'), ('signup', 'Signup'), ('browse', 'Browse Products'), ('order', 'Place Order'), ('track', 'Track Delivery'), ('pay', 'Make Payment'), ('inventory', 'Manage Inventory'), ('analytics', 'View Analytics')], max_length=20)),
                ('duration_seconds', models.FloatField(default=0)),
                ('completed', models.BooleanField(default=True)),
                ('device_type', models.CharField(blank=True, default='desktop', max_length=50)),
                ('page_url', models.CharField(blank=True, max_length=500)),
                ('error_message', models.TextField(blank=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='usability_metrics', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='SystemPerformance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metric_name', models.CharField(max_length=100)),
                ('metric_value', models.FloatField()),
                ('period', models.CharField(choices=[('before', 'Before System'), ('after', 'After System')], max_length=10)),
                ('unit', models.CharField(blank=True, default='', max_length=50)),
                ('description', models.TextField(blank=True)),
                ('recorded_date', models.DateField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-recorded_date'],
            },
        ),
    ]
