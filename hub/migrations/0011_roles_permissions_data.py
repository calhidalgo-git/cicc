"""Permisos separados de T06 (D10) en las instalaciones que ya tienen grupos.

- Todo grupo que tiene ``hub.view_audit`` recibe ``hub.view_reports``: conserva el acceso a los
  reportes, que antes dependía de ``view_audit``.
- El grupo ``Administrador``, si existe, recibe ``hub.export_backup``.

Los permisos nuevos se crean aquí porque Django solo los crea al terminar ``migrate``. Al revertir,
se quitan de todos los grupos: antes de T06 no existían.
"""

from django.contrib.auth.management import create_permissions
from django.db import migrations


def permission(apps, codename):
    Permission = apps.get_model('auth', 'Permission')
    return Permission.objects.get(content_type__app_label='hub', codename=codename)


def forward(apps, schema_editor):
    hub = apps.get_app_config('hub')
    hub.models_module = True
    create_permissions(hub, apps=apps, verbosity=0)
    hub.models_module = None
    Group = apps.get_model('auth', 'Group')
    view_reports = permission(apps, 'view_reports')
    for group in Group.objects.filter(
        permissions__content_type__app_label='hub', permissions__codename='view_audit'
    ):
        group.permissions.add(view_reports)
    administrator = Group.objects.filter(name='Administrador').first()
    if administrator is not None:
        administrator.permissions.add(permission(apps, 'export_backup'))


def backward(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    new = Permission.objects.filter(
        content_type__app_label='hub', codename__in=['view_reports', 'export_backup']
    )
    for group in Group.objects.filter(permissions__in=new).distinct():
        group.permissions.remove(*new)


class Migration(migrations.Migration):
    dependencies = [
        ('hub', '0010_roles_permissions'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [migrations.RunPython(forward, backward)]
