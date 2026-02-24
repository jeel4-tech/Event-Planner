from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('account', '0006_user_business_logo'),
    ]

    operations = [
        migrations.CreateModel(
            name='Token',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(default=0, max_digits=10, decimal_places=2)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='token', to='account.user')),
            ],
        ),
    ]
