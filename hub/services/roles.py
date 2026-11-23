"""Los cuatro roles de CICC y sus permisos (T06, D11).

``bootstrap_roles`` crea o actualiza los grupos con esta matriz. No crea usuarios ni toca otros
grupos, así que puede ejecutarse en producción las veces que haga falta.
"""

from django.contrib.auth.models import Group, Permission
from django.db import transaction


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


def role_permissions(name):
    """Permisos que corresponden al rol ``name``."""
    if name == ADMINISTRATOR:
        return Permission.objects.filter(content_type__app_label__in=ADMINISTRATOR_APPS)
    codes = ROLES[name]
    permissions = Permission.objects.filter(content_type__app_label='hub', codename__in=codes)
    missing = set(codes) - set(permissions.values_list('codename', flat=True))
    if missing:
        raise LookupError(
            'Faltan permisos en la base: ' + ', '.join(sorted(missing)) + '. Ejecuta migrate.'
        )
    return permissions


ROLE_NAMES = [*ROLES, ADMINISTRATOR]


@transaction.atomic
def bootstrap_roles():
    """Crea o actualiza los cuatro grupos. Devuelve los nombres de los grupos creados."""
    created_names = []
    for name in ROLE_NAMES:
        group, created = Group.objects.get_or_create(name=name)
        group.permissions.set(role_permissions(name))
        if created:
            created_names.append(name)
    return created_names
