"""T05 (2 de 3): slugs de las rutas existentes y posiciones sin repetir.

Va sola porque PostgreSQL no permite cambiar el esquema de una tabla con datos recién modificados
en la misma transacción. Revertirla no deshace nada: la 0004 elimina los slugs al revertirse.

Todas las rutas que existen al aplicarla reciben un slug propio, nunca el de un curso oficial.
Antes de T05 los cursos no estaban en la base: los crea después load_courses.

Si la migración se repite tras revertir a 0003, la dirección de cada curso ya se perdió y los datos
no permiten saber con certeza cuál de las rutas era el curso. Seis revisiones de Codex (22 a
24-11-2026) mostraron que cada regla para reconocerlo (título, textos, posiciones, copias) dejaba
algún caso en que una copia heredaba la dirección o se reescribía un ejercicio. Por decisión de
Carlos (24-11-2026) la migración ya no lo intenta: todas las rutas quedan locales, con su texto y su
avance, y la dirección oficial se recupera restaurando el respaldo hecho antes de revertir.
"""

import json
from pathlib import Path

from django.db import migrations
from django.utils.text import slugify

COURSES_DIR = Path(__file__).resolve().parent.parent / 'content' / 'courses'


def official_slugs():
    return {
        json.loads(definition.read_text(encoding='utf-8'))['slug']
        for definition in COURSES_DIR.glob('*/course.json')
    }


def assign_slugs(apps, schema_editor):
    LearningPath = apps.get_model('hub', 'LearningPath')
    # Ninguna ruta local puede recibir un slug oficial, ni siquiera con sufijo de otra.
    used = official_slugs()
    for path in LearningPath.objects.order_by('pk'):
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
