"""Los cuatro roles de CICC y sus permisos (T06, D11).

``bootstrap_roles`` crea o actualiza los grupos con esta matriz. No crea usuarios ni toca otros
grupos, así que puede ejecutarse en producción las veces que haga falta.
"""

from django.contrib.auth.models import Group, Permission
from django.db import DEFAULT_DB_ALIAS, connections, transaction
from django.db.migrations.executor import MigrationExecutor


def crud(*models):
    """Permisos de ver, agregar y cambiar de cada modelo de ``hub``."""
    return [f'{action}_{model}' for model in models for action in ('view', 'add', 'change')]


ROLES = {
    'Participante': [],
    'Editor': [
        *crud('resource', 'resourceversion', 'learningpath', 'lesson'),
        # T12: la teoría de las páginas del menú (los bloques se editan con la página).
        'view_sectionpage',
        'change_sectionpage',
    ],
    'Evaluador': [
        *crud('question', 'assessment'),
        'view_audit',
        'view_reports',
    ],
}
ADMINISTRATOR = 'Administrador'
ADMINISTRATOR_APPS = ('hub', 'auth')
# El Administrador recibe todos los permisos de hub y auth; sin estos dos perdería reportes y la
# descarga del respaldo sin que nadie lo note (cuarta revisión de Codex, 24-11-2026).
ADMINISTRATOR_REQUIRED = ['view_reports', 'export_backup']


def missing_codes(codes):
    found = Permission.objects.filter(content_type__app_label='hub', codename__in=codes)
    return set(codes) - set(found.values_list('codename', flat=True))


def role_permissions(name):
    """Permisos que corresponden al rol ``name``."""
    if name == ADMINISTRATOR:
        codes = ADMINISTRATOR_REQUIRED
        permissions = Permission.objects.filter(content_type__app_label__in=ADMINISTRATOR_APPS)
    else:
        codes = ROLES[name]
        permissions = Permission.objects.filter(content_type__app_label='hub', codename__in=codes)
    missing = missing_codes(codes)
    if missing:
        raise LookupError(
            'Faltan permisos en la base: ' + ', '.join(sorted(missing)) + '. Ejecuta migrate.'
        )
    return permissions


def check_migrated(using=DEFAULT_DB_ALIAS):
    """Detiene el comando si la base no tiene todas las migraciones, o ni siquiera sus tablas."""
    executor = MigrationExecutor(connections[using])
    pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
    if pending:
        raise LookupError(
            f'La base no está al día: faltan {len(pending)} migraciones. Ejecuta migrate.'
        )


ROLE_NAMES = [*ROLES, ADMINISTRATOR]


@transaction.atomic
def bootstrap_roles():
    """Crea o actualiza los cuatro grupos. Devuelve los nombres de los grupos creados.

    El comando ``bootstrap_roles`` llama antes a ``check_migrated()``.
    """
    created_names = []
    for name in ROLE_NAMES:
        group, created = Group.objects.get_or_create(name=name)
        group.permissions.set(role_permissions(name))
        if created:
            created_names.append(name)
    return created_names
