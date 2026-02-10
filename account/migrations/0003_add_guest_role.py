from django.db import migrations


def create_guest_role(apps, schema_editor):
    Role = apps.get_model('account', 'Role')
    Role.objects.update_or_create(name='guest', defaults={'description': 'Guest user'})


def remove_guest_role(apps, schema_editor):
    Role = apps.get_model('account', 'Role')
    Role.objects.filter(name='guest').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0002_create_roles'),
    ]

    operations = [
        migrations.RunPython(create_guest_role, reverse_code=remove_guest_role),
    ]
