"""Una página de sección vacía por cada opción del menú (T12).

La lista se copia aquí, y no se importa de hub.permissions, para que la migración no cambie si
el menú cambia después. Las opciones nuevas las crea el comando load_pages.
"""

from django.db import migrations

MENU = [
    ('dashboard', 'Vista general'),
    ('knowledge', 'Conocimiento del área'),
    ('environment', 'Ambiente de certificación'),
    ('mainframe', 'Mainframe'),
    ('distributed', 'Distribuido'),
    ('lifecycle', 'Ciclo de vida y pruebas'),
    ('tools', 'Herramientas QA / ClearQuest'),
    ('procedures', 'Procedimientos de certificación'),
    ('incidents', 'Incidentes y soluciones'),
    ('glossary', 'Glosario'),
    ('components', 'Mapa de componentes'),
    ('search', 'Búsqueda global'),
    ('library', 'Biblioteca'),
    ('videos', 'Videoteca'),
    ('links', 'Enlaces útiles'),
    ('paths', 'Rutas de aprendizaje'),
    ('lessons', 'Mis lecciones'),
    ('assessments', 'Evaluaciones'),
    ('results', 'Mis resultados'),
    ('questions', 'Banco de preguntas'),
    ('reports', 'Reportes'),
    ('users', 'Usuarios'),
    ('roles', 'Roles y permisos'),
    ('settings', 'Configuración'),
    ('audit', 'Auditoría'),
    ('backups', 'Respaldos'),
]


def create_pages(apps, schema_editor):
    SectionPage = apps.get_model('hub', 'SectionPage')
    existing = set(SectionPage.objects.values_list('slug', flat=True))
    SectionPage.objects.bulk_create(
        SectionPage(slug=slug, title=title) for slug, title in MENU if slug not in existing
    )


def remove_empty_pages(apps, schema_editor):
    # Solo se quitan las páginas que siguen vacías; la teoría escrita no se borra aquí.
    SectionPage = apps.get_model('hub', 'SectionPage')
    SectionPage.objects.filter(
        slug__in=[slug for slug, _ in MENU], intro_html='', blocks__isnull=True
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('hub', '0008_section_pages'),
    ]

    operations = [
        migrations.RunPython(create_pages, remove_empty_pages),
    ]
