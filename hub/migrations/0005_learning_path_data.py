"""T05 (2 de 3): slugs de las rutas existentes y posiciones sin repetir.

Va sola porque PostgreSQL no permite cambiar el esquema de una tabla con datos recién modificados
en la misma transacción. Revertirla no deshace nada: la 0004 elimina los slugs al revertirse.

Los slugs de los tres cursos oficiales están reservados. Una ruta solo recibe uno de ellos si es
ese curso, cargado antes por load_courses (la migración se repite tras revertirla): mismo título y
todas sus lecciones, con la misma posición y el mismo título. Una ruta local con el mismo nombre
recibe otro slug y queda separada, con su contenido y su avance.
"""

import json
from pathlib import Path

from django.db import migrations
from django.utils.text import slugify

COURSES_DIR = Path(__file__).resolve().parent.parent / 'content' / 'courses'


def official_courses():
    """Título del curso → (slug, conjunto de (posición, título) de sus lecciones)."""
    courses = {}
    for definition in sorted(COURSES_DIR.glob('*/course.json')):
        data = json.loads(definition.read_text(encoding='utf-8'))
        lessons = {(item['position'], item['title']) for item in data['lessons']}
        courses[data['title']] = (data['slug'], lessons)
    return courses


def assign_slugs(apps, schema_editor):
    LearningPath = apps.get_model('hub', 'LearningPath')
    Lesson = apps.get_model('hub', 'Lesson')
    official = official_courses()
    # Ninguna ruta local puede recibir un slug oficial, ni siquiera con sufijo de otra.
    used = {slug for slug, _lessons in official.values()}
    claimed = set()
    for path in LearningPath.objects.order_by('pk'):
        slug, lessons = official.get(path.title, (None, None))
        if slug and slug not in claimed:
            own = set(Lesson.objects.filter(path=path).values_list('position', 'title'))
            if lessons <= own:
                claimed.add(slug)
                path.slug = slug
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
