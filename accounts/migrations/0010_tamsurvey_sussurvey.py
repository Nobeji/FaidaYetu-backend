from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0009_usabilitymetric_systemperformance'),
    ]

    operations = [
        migrations.CreateModel(
            name='TAMSurvey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('perceived_usefulness', models.IntegerField(default=0)),
                ('perceived_ease_of_use', models.IntegerField(default=0)),
                ('behavioral_intention', models.IntegerField(default=0)),
                ('actual_usage', models.IntegerField(default=0)),
                ('comments', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tam_surveys', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SUSSurvey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('q1', models.IntegerField(default=3)),
                ('q2', models.IntegerField(default=3)),
                ('q3', models.IntegerField(default=3)),
                ('q4', models.IntegerField(default=3)),
                ('q5', models.IntegerField(default=3)),
                ('q6', models.IntegerField(default=3)),
                ('q7', models.IntegerField(default=3)),
                ('q8', models.IntegerField(default=3)),
                ('q9', models.IntegerField(default=3)),
                ('q10', models.IntegerField(default=3)),
                ('user_role', models.CharField(blank=True, default='customer', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sus_surveys', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
