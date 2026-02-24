from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0012_alter_advancepayment_id'),
        ('account', '0006_user_business_logo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='advancepayment',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.user'),
        ),
    ]
