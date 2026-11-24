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


def link_legacy_resources(path, titles, summary):
    """Vincula con su curso los recursos que lo abrían antes de T05 (veto de Carlos a D4).

    Solo toca los recursos sin ruta asignada: no cambia una ruta elegida en el administrador.
    El recurso se reconoce por su título. Si hay más de un recurso con ese título, no se puede
    saber cuál es el histórico: no se toca ninguno y el título queda en ``summary['ambiguous']``
    para que se elija en el administrador (tercera revisión de Codex, 23-11-2026).

    Si algún recurso ya abre el curso, el vínculo histórico existe: no se vincula otro. Así un
    manual local con el título anterior de un recurso histórico renombrado no pasa a abrir el
    curso (cuarta revisión de Codex, 24-11-2026).
    """
    from hub.models import Resource

    linked = Resource.objects.filter(learning_path=path).exists()
    for title in titles:
        resources = list(Resource.objects.filter(title=title))
        if len(resources) > 1:
            summary['ambiguous'].append(title)
            continue
        if not linked and resources and resources[0].learning_path_id is None:
            resources[0].learning_path = path
            resources[0].save(update_fields=['learning_path'])
            summary['linked'] += 1
            linked = True


def official_key(course, item):
    """Marca de una lección oficial: «<slug del curso>:<posición oficial>»."""
    return f'{course["slug"]}:{item["position"]}'


def mark_intact_lessons(path, course):
    """Marca las lecciones sin marca que son idénticas a una oficial: misma posición, mismo título
    y mismo texto, y ninguna otra lección de la ruta con esa marca.

    Sirve para las instalaciones y los respaldos anteriores a la marca (24-11-2026). No adivina:
    reescribir una lección idéntica no cambia nada, y un ejercicio con texto propio nunca lo es.
    Devuelve cuántas marcó.
    """
    lessons = list(path.lessons.all())
    used = {lesson.official_key for lesson in lessons if lesson.official_key}
    marked = 0
    for item in course['lessons']:
        key = official_key(course, item)
        if key in used:
            continue
        text = html_to_text(sanitize_html((course['dir'] / item['file']).read_text('utf-8')))
        matches = [
            lesson
            for lesson in lessons
            if not lesson.official_key
            and (lesson.position, lesson.title, lesson.body)
            == (item['position'], item['title'], text)
        ]
        if len(matches) == 1:
            matches[0].official_key = key
            matches[0].save(update_fields=['official_key'])
            marked += 1
    return marked


def empty_summary():
    return {
        'paths': 0,
        'lessons': 0,
        'updated': 0,
        'linked': 0,
        'ambiguous': [],
        'occupied': [],
    }


@transaction.atomic
def relink_legacy_resources():
    """Solo vuelve a vincular los recursos históricos sin ruta con su curso oficial.

    Es para las instalaciones que ya aplicaron la T05 anterior (``beec6b6``), donde los cursos
    existen pero los tres recursos quedaron sin vínculo (revisión de Codex, 22-11-2026). No crea
    ni reescribe rutas ni lecciones, y no cambia un recurso que ya abre alguna ruta.
    """
    from hub.models import LearningPath

    summary = empty_summary()
    for course in read_courses():
        path = LearningPath.objects.filter(slug=course['slug']).first()
        if path is not None:
            link_legacy_resources(path, course.get('legacy_resource_titles', []), summary)
    return summary


@transaction.atomic
def load_courses(force=False):
    """Crea las rutas y lecciones que falten; con ``force`` también reescribe las existentes.

    Identifica las rutas por ``slug`` (reservado para los cursos oficiales: una ruta local con
    el mismo nombre tiene otro slug y no se toca).

    Las lecciones oficiales se identifican por su marca ``official_key``, nunca por su posición ni
    por su título o su texto (decisión de Carlos, 24-11-2026, tras la sexta revisión de Codex):
    - ``--force`` solo reescribe lecciones con marca, estén donde estén. Una lección propia (sin
      marca) nunca se reescribe.
    - Una lección oficial que falta se crea en su posición, con su marca, si esa posición está
      libre. Si la ocupa una lección propia, no se crea y queda en ``summary['occupied']``.

    Al crear un curso, o con ``force``, vincula los recursos históricos que lo abrían.
    """
    from hub.models import LearningPath, Lesson

    summary = empty_summary()
    for course in read_courses():
        path = LearningPath.objects.filter(slug=course['slug']).first()
        fields = {
            'title': course['title'],
            'area': course['area'],
            'description': course['description'],
            'position': course['position'],
            'intro_html': (course['dir'] / 'intro.html').read_text(encoding='utf-8'),
        }
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
            link_legacy_resources(path, course.get('legacy_resource_titles', []), summary)
        if not created:
            mark_intact_lessons(path, course)
        lessons = list(path.lessons.all())
        by_key = {lesson.official_key: lesson for lesson in lessons if lesson.official_key}
        taken = {lesson.position for lesson in lessons}
        for item in course['lessons']:
            key = official_key(course, item)
            body = (course['dir'] / item['file']).read_text(encoding='utf-8')
            lesson = by_key.get(key)
            if lesson is None:
                if item['position'] in taken:
                    summary['occupied'].append((course['title'], item['position'], item['title']))
                    continue
                Lesson.objects.create(
                    path=path,
                    position=item['position'],
                    title=item['title'],
                    body_html=body,
                    official_key=key,
                )
                taken.add(item['position'])
                summary['lessons'] += 1
            elif force:
                lesson.title = item['title']
                lesson.body_html = body
                lesson.save()
                summary['updated'] += 1
    return summary
