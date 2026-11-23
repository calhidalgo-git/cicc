"""T05 (2 de 3): slugs de las rutas existentes y posiciones sin repetir.

Va sola porque PostgreSQL no permite cambiar el esquema de una tabla con datos recién modificados
en la misma transacción. Revertirla no deshace nada: la 0004 elimina los slugs al revertirse.

Los slugs de los tres cursos oficiales están reservados. Antes de T05 los cursos no estaban en la
base, así que una ruta solo puede ser oficial si es ese curso, cargado antes por load_courses (la
migración se repite tras revertirla). Como al revertir se pierde el slug, la ruta se reconoce solo
si conserva todo lo que load_courses --force reescribiría: el título, el área y la descripción del
curso, y cada una de sus lecciones con la misma posición, el mismo título y el mismo texto.

Una ruta local que copie el nombre, los títulos o el orden del curso, pero no su contenido, no se
puede distinguir por esos datos: recibe otro slug y queda separada, con su texto y su avance
(revisión de Codex, 22-11-2026). Si una ruta sí coincide en todo, tomarla por oficial no cambia
nada de lo que contiene.
"""

import json
from pathlib import Path

from django.db import migrations
from django.utils.text import slugify

COURSES_DIR = Path(__file__).resolve().parent.parent / 'content' / 'courses'


def official_courses():
    """Título del curso → datos que lo identifican tras una reversión."""
    from hub.services.courses import html_to_text, sanitize_html

    courses = {}
    for definition in sorted(COURSES_DIR.glob('*/course.json')):
        data = json.loads(definition.read_text(encoding='utf-8'))
        lessons = {}
        for item in data['lessons']:
            body_html = (definition.parent / item['file']).read_text(encoding='utf-8')
            # Lesson.save() guarda en «body» el texto plano del HTML saneado.
            lessons[item['position']] = (item['title'], html_to_text(sanitize_html(body_html)))
        courses[data['title']] = {
            'slug': data['slug'],
            'area': data['area'],
            'description': data['description'],
            'lessons': lessons,
        }
    return courses


def is_official_course(path, course, Lesson):
    """True solo si la ruta conserva exactamente el contenido oficial del curso."""
    if path.area != course['area'] or path.description != course['description']:
        return False
    # Antes de T05 la posición podía repetirse: se comparan todas las lecciones de esas posiciones.
    own = sorted(
        Lesson.objects.filter(path=path, position__in=course['lessons']).values_list(
            'position', 'title', 'body'
        )
    )
    expected = sorted((position, *data) for position, data in course['lessons'].items())
    return own == expected


def assign_slugs(apps, schema_editor):
    LearningPath = apps.get_model('hub', 'LearningPath')
    Lesson = apps.get_model('hub', 'Lesson')
    official = official_courses()
    # Ninguna ruta local puede recibir un slug oficial, ni siquiera con sufijo de otra.
    used = {course['slug'] for course in official.values()}
    claimed = set()
    for path in LearningPath.objects.order_by('pk'):
        course = official.get(path.title)
        if (
            course
            and course['slug'] not in claimed
            and is_official_course(path, course, Lesson)
        ):
            claimed.add(course['slug'])
            path.slug = course['slug']
            path.save(update_fields=['slug'])
            continue
        base = slugify(path.title)[:190] or 'ruta'
        candidate, number = base, 2
        while candidate in used:
            candidate = f'{base}-{number}'
            number += 1
        used.add(candidate)
        path.slug = candidate
        path.save(update_fields=['slug'])


def renumber_repeated_positions(apps, schema_editor):
    """Si una ruta tiene posiciones repetidas, las renumera 1, 2, 3… conservando el orden."""
    LearningPath = apps.get_model('hub', 'LearningPath')
    Lesson = apps.get_model('hub', 'Lesson')
    for path in LearningPath.objects.all():
        lessons = list(Lesson.objects.filter(path=path).order_by('position', 'pk'))
        positions = [lesson.position for lesson in lessons]
        if len(positions) == len(set(positions)):
            continue
        for number, lesson in enumerate(lessons, 1):
            lesson.position = number
            lesson.save(update_fields=['position'])


class Migration(migrations.Migration):
    dependencies = [
        ('hub', '0004_learning_path_fields'),
    ]

    operations = [
        migrations.RunPython(assign_slugs, migrations.RunPython.noop),
        migrations.RunPython(renumber_repeated_positions, migrations.RunPython.noop),
    ]
