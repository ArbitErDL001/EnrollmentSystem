from django.db import migrations


ROLE_NAMES = (
    'Admin',
    'Registrar',
    'Cashier',
    'Instructor',
    'Student',
)


def create_roles(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for role in ROLE_NAMES:
        Group.objects.get_or_create(name=role)


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_roles, migrations.RunPython.noop),
    ]
