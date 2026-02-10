from django.db import migrations


def create_roles(apps, schema_editor):
    Role = apps.get_model('account', 'Role')
    roles = [
        {'name': 'user', 'description': 'Regular user'},
        {'name': 'vendor', 'description': 'Event vendor'},
        {'name': 'admin', 'description': 'Administrator'},
    ]

    for r in roles:
        Role.objects.update_or_create(name=r['name'], defaults={'description': r['description']})


def remove_roles(apps, schema_editor):
    Role = apps.get_model('account', 'Role')
    Role.objects.filter(name__in=['user', 'vendor', 'admin']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_roles, reverse_code=remove_roles),
    ]
