from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_tamsurvey_sussurvey'),
    ]

    operations = [
        migrations.AddField(
            model_name='tamsurvey',
            name='user_role',
            field=models.CharField(blank=True, default='customer', max_length=20),
        ),
    ]
