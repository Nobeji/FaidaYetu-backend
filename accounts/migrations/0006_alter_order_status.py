from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_alter_product_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('new', 'New'), ('paid', 'Paid'), ('processing', 'Processing'), ('ready', 'Ready'), ('in_transit', 'In Transit'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')], default='new', max_length=20),
        ),
    ]
