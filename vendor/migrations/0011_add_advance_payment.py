from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0010_chatmessage_image'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='advance_percentage',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='booking',
            name='advance_required',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='booking',
            name='advance_paid',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.CreateModel(
            name='AdvancePayment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(max_digits=10, decimal_places=2)),
                ('currency', models.CharField(default='INR', max_length=10)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('succeeded', 'Succeeded'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('gateway', models.CharField(max_length=100, null=True, blank=True)),
                ('gateway_id', models.CharField(max_length=255, null=True, blank=True)),
                ('gateway_response', models.JSONField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='advance_payments', to='vendor.booking')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
