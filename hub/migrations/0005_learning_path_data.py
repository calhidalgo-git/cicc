"""T05 (2 de 3): slugs de las rutas existentes y posiciones sin repetir.

Va sola porque PostgreSQL no permite cambiar el esquema de una tabla con datos recién modificados
en la misma transacción. Revertirla no deshace nada: la 0004 elimina los slugs al revertirse.
"""

from django.db import migrations
from django.utils.text import slugify


# Los cursos cargados por load_courses conservan sus slugs acordados si la migración se repite.
COURSE_SLUGS = {
    'Fundamentos QA': 'fundamentos-qa',
    'QA Avanzado y Especialización': 'qa-avanzado',
    'Certificación de un Requerimiento de Software': 'certificacion-requerimiento',
}


def assign_slugs(apps, schema_editor):
    LearningPath = apps.get_model('hub', 'LearningPath')
    used = set()
    for path in LearningPath.objects.order_by('pk'):
        base = COURSE_SLUGS.get(path.title) or slugify(path.title)[:190] or 'ruta'
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
