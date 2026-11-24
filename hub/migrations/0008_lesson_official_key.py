"""T05: marca de lección oficial (decisión de Carlos, 24-11-2026, tras la sexta revisión de Codex).

load_courses escribe ``official_key`` al crear cada lección oficial, y load_courses --force solo
reescribe lecciones con marca. Así una lección propia nunca se reescribe, esté donde esté.

En una instalación que ya tenía los cursos (T05 anterior), se marcan solo las lecciones idénticas a
la oficial: misma posición, mismo título y mismo texto. Marcarlas no puede borrar nada, porque
reescribirlas deja lo mismo. Las editadas quedan sin marca: --force no las toca y load_courses
avisa si ocupan la posición de una lección oficial.
"""

import json
from pathlib import Path

from django.db import migrations, models

COURSES_DIR = Path(__file__).resolve().parent.parent / 'content' / 'courses'


def mark_existing_official_lessons(apps, schema_editor):
    from hub.services.courses import html_to_text, sanitize_html

    LearningPath = apps.get_model('hub', 'LearningPath')
    Lesson = apps.get_model('hub', 'Lesson')
    for definition in COURSES_DIR.glob('*/course.json'):
        course = json.loads(definition.read_text(encoding='utf-8'))
        path = LearningPath.objects.filter(slug=course['slug']).first()
        if path is None:
            continue
        lessons = list(Lesson.objects.filter(path=path))
        for item in course['lessons']:
            html = (definition.parent / item['file']).read_text(encoding='utf-8')
            expected = (item['position'], item['title'], html_to_text(sanitize_html(html)))
            matches = [l for l in lessons if (l.position, l.title, l.body) == expected]
            if len(matches) == 1:
                matches[0].official_key = f'{course["slug"]}:{item["position"]}'
                matches[0].save(update_fields=['official_key'])


class Migration(migrations.Migration):
    dependencies = [
        ('hub', '0007_resource_opens_learning_path'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='official_key',
            field=models.CharField(blank=True, default='', editable=False, max_length=220),
        ),
        migrations.AddConstraint(
            model_name='lesson',
            constraint=models.UniqueConstraint(
                condition=models.Q(('official_key', ''), _negated=True),
                fields=('path', 'official_key'),
                name='unique_lesson_official_key',
            ),
        ),
        migrations.RunPython(mark_existing_official_lessons, migrations.RunPython.noop),
    ]
