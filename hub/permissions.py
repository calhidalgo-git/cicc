"""Menú de secciones y permiso que exige cada una."""

from .catalog import MODULES

NAV = [
    ('dashboard', 'Vista general', '◈'),
    ('library', 'Biblioteca', '▤'),
    ('videos', 'Videoteca', '▷'),
    ('links', 'Enlaces útiles', '↗'),
    ('paths', 'Rutas de aprendizaje', '⌘'),
    ('lessons', 'Mis lecciones', '▧'),
    ('assessments', 'Evaluaciones', '◇'),
    ('results', 'Mis resultados', '✓'),
    ('questions', 'Banco de preguntas', '⊞'),
    ('reports', 'Reportes', '▥'),
    ('users', 'Usuarios', '♧'),
    ('roles', 'Roles y permisos', '⚿'),
    ('settings', 'Configuración', '⚙'),
    ('audit', 'Auditoría', '≡'),
    ('backups', 'Respaldos', '↺'),
]
NAV[1:1] = [(s, t, '▤') for s, t in MODULES.items()] + [
    ('components', 'Mapa de componentes', '⌘'),
    ('search', 'Búsqueda global', '⌕'),
]
GATES = {
    'questions': 'hub.change_question',
    'reports': 'hub.view_audit',
    'users': 'auth.view_user',
    'roles': 'auth.view_group',
    'settings': 'auth.change_group',
    'audit': 'hub.view_audit',
    'backups': 'hub.view_audit',
}
TITLES = {slug: title for slug, title, _ in NAV}


def allowed(user, slug):
    """True si el usuario puede abrir la sección (las que no están en GATES son libres)."""
    return slug not in GATES or user.has_perm(GATES[slug])


def visible_nav(user):
    """Entradas de NAV (slug, etiqueta, icono) que el usuario puede abrir."""
    return [item for item in NAV if allowed(user, item[0])]
