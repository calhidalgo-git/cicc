"""Permisos separados de T06 (D10) en las instalaciones que ya tienen grupos.

- Todo grupo que tiene ``hub.view_audit`` recibe ``hub.view_reports``: conserva el acceso a los
  reportes, que antes dependía de ``view_audit``.
- El grupo ``Administrador``, si existe, recibe ``hub.export_backup``.

Los permisos nuevos se crean aquí porque Django solo los crea al terminar ``migrate``. Al revertir,
se borran del catálogo, y con ellos de todos los grupos y cuentas: antes de T06 no existían.
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


NEW_PERMISSIONS = ['view_reports', 'export_backup']


def delete_new_permissions(apps, schema_editor):
    """Borra los dos permisos del catálogo. Con ellos desaparecen sus asignaciones a grupos y a
    cuentas (cuarta revisión de Codex, 24-11-2026). Si se vuelve solo a 0010, Django los crea otra
    vez al terminar ``migrate``, sin asignar; la 0010 los borra al revertirse.
    """
    Permission = apps.get_model('auth', 'Permission')
    Permission.objects.filter(content_type__app_label='hub', codename__in=NEW_PERMISSIONS).delete()


def backward(apps, schema_editor):
    delete_new_permissions(apps, schema_editor)


class Migration(migrations.Migration):
    dependencies = [
        ('hub', '0010_roles_permissions'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [migrations.RunPython(forward, backward)]
