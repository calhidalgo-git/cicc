"""Cursos como rutas de aprendizaje: saneado del HTML y carga desde hub/content/courses/."""

import html
import json
import re
from pathlib import Path

import nh3
from django.db import transaction

COURSES_DIR = Path(__file__).resolve().parent.parent / 'content' / 'courses'

ALLOWED_TAGS = {
    'h2',
    'h3',
    'h4',
    'p',
    'ul',
    'ol',
    'li',
    'strong',
    'em',
    'b',
    'i',
    'a',
    'table',
    'thead',
    'tbody',
    'tr',
    'th',
    'td',
    'blockquote',
    'code',
    'pre',
    'br',
    'hr',
    'span',
    'div',
}
ALLOWED_ATTRIBUTES = {
    '*': {'class'},
    'a': {'href', 'title'},
}
URL_SCHEMES = {'http', 'https', 'mailto'}

_TAG_RE = re.compile(r'<[^>]+>')
_SPACE_RE = re.compile(r'\s+')


def sanitize_html(value):
    """HTML limitado a la lista permitida (D5). Elimina scripts, estilos y atributos de eventos."""
    if not value:
        return ''
    return nh3.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=URL_SCHEMES,
    )


def html_to_text(value):
    """Texto plano del HTML, con espacios normalizados. Es lo que usa la búsqueda."""
    text = _TAG_RE.sub(' ', value or '')
    return _SPACE_RE.sub(' ', html.unescape(text)).strip()


def read_courses():
    """Definiciones de los cursos incluidos en el proyecto, ordenadas por posición."""
    courses = []
    for definition in sorted(COURSES_DIR.glob('*/course.json')):
        data = json.loads(definition.read_text(encoding='utf-8'))
        data['dir'] = definition.parent
        courses.append(data)
    return sorted(courses, key=lambda course: course['position'])


def official_slugs():
    """Slugs de los cursos oficiales. Ninguna ruta local puede usarlos."""
    return frozenset(course['slug'] for course in read_courses())


def link_legacy_resources(path, titles):
    """Vincula con su curso los recursos que lo abrían antes de T05 (veto de Carlos a D4).

    Solo toca los recursos sin ruta asignada: no cambia una ruta elegida en el administrador.
    """
    from hub.models import Resource

    return Resource.objects.filter(title__in=titles, learning_path__isnull=True).update(
        learning_path=path
    )


@transaction.atomic
def load_courses(force=False):
    """Crea las rutas y lecciones que falten; con ``force`` también reescribe las existentes.

    Identifica las rutas por ``slug`` (reservado para los cursos oficiales: una ruta local con
    el mismo nombre tiene otro slug y no se toca) y las lecciones por ``position``.

    Al crear un curso, o con ``force``, vincula los recursos históricos que lo abrían.
    """
    from hub.models import LearningPath, Lesson

    summary = {'paths': 0, 'lessons': 0, 'updated': 0, 'linked': 0}
    for course in read_courses():
        fields = {
            'title': course['title'],
            'area': course['area'],
            'description': course['description'],
            'position': course['position'],
            'intro_html': (course['dir'] / 'intro.html').read_text(encoding='utf-8'),
        }
        path = LearningPath.objects.filter(slug=course['slug']).first()
        created = path is None
        if created:
            path = LearningPath(slug=course['slug'], **fields)
            path._official_course = True
            path.save()
            summary['paths'] += 1
        elif force:
            for name, value in fields.items():
                setattr(path, name, value)
            path.save()
            summary['updated'] += 1
        if created or force:
            summary['linked'] += link_legacy_resources(
                path, course.get('legacy_resource_titles', [])
            )
        existing = {lesson.position: lesson for lesson in path.lessons.all()}
        for item in course['lessons']:
            body = (course['dir'] / item['file']).read_text(encoding='utf-8')
            lesson = existing.get(item['position'])
            if lesson is None:
                Lesson.objects.create(
                    path=path, position=item['position'], title=item['title'], body_html=body
                )
                summary['lessons'] += 1
            elif force:
                lesson.title = item['title']
                lesson.body_html = body
                lesson.save()
                summary['updated'] += 1
    return summary
