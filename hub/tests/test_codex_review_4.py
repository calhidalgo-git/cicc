"""Correcciones de la cuarta revisión de Codex (24-11-2026).

1. Una base que aplicó la 0005 anterior y renumeró ejercicios propios delante de las lecciones
   oficiales no los pierde con load_courses --force.
2. Al revertir, un curso editado no cede su dirección a una copia del mismo título.
3. El respaldo hecho antes de revertir se restaura en la misma base en los dos órdenes de
   creación (copia antes o después del curso).
4. Una actualización en lote con una expresión no cambia ni toma una dirección oficial.
5. --relink no vincula un manual con el título antiguo de un recurso histórico renombrado.
6. bulk_update() con un iterador guarda los cambios.
"""

import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.test import TestCase

from ..models import LearningPath, Lesson, Progress, Resource
from ..views.management import backup_json
from .test_codex_review_3 import (
    BEFORE,
    PASSWORD,
    MigrationCase,
    SeededBase,
    fundamentos,
    load,
    official_html,
    official_text,
)


class AlreadyMigratedBaseKeepsTheExercises(TestCase):
    """Hallazgo 1: lo que dejó la 0005 anterior en una ruta con ejercicios en la posición 0."""

    def setUp(self):
        course = fundamentos()
        path = LearningPath(
            slug=course['slug'],
            title=course['title'],
            area=course['area'],
            description=course['description'],
        )
        path._official_course = True
        path.save()
        self.first = Lesson.objects.create(path=path, position=1, title='Ejercicio A', body='Mío A')
        Lesson.objects.create(path=path, position=2, title='Ejercicio B', body='Mío B')
        for item in course['lessons']:
            Lesson.objects.create(
                path=path,
                position=item['position'] + 2,
                title=item['title'],
                body_html=official_html(course, item),
            )
        self.user = User.objects.create_user('alumna', password=PASSWORD)
        Progress.objects.create(user=self.user, lesson=self.first)
        self.path = path

    def test_normal_and_forced_loads_keep_the_exercises_and_the_progress(self):
        for options in ({}, {'force': True}):
            output = load(**options)
            # Sin marcas (como deja la 0008 cuando hay dudas), nada se reescribe y se avisa.
            self.assertIn('la ocupa una lección propia', output, options)
            lessons = dict(self.path.lessons.values_list('position', 'title'))
            self.assertEqual((lessons[1], lessons[2]), ('Ejercicio A', 'Ejercicio B'), options)
            self.assertEqual(self.path.lessons.count(), 8, options)
            own = dict(self.path.lessons.values_list('title', 'body'))
            self.assertEqual((own['Ejercicio A'], own['Ejercicio B']), ('Mío A', 'Mío B'))
            done = Progress.objects.get(user=self.user).lesson
            self.assertEqual(
                (done.pk, done.title, done.body), (self.first.pk, 'Ejercicio A', 'Mío A')
            )

    def test_after_ordering_the_lessons_force_works_again(self):
        # Carlos ordena las lecciones en el administrador: las oficiales primero (1 a 6) y los
        # ejercicios después (7 y 8). Se pasa por posiciones libres para no repetir ninguna.
        lessons = self.path.lessons
        lessons.update(position=F('position') + 100)
        lessons.exclude(title__startswith='Ejercicio').update(position=F('position') - 102)
        lessons.filter(title='Ejercicio A').update(position=7)
        lessons.filter(title='Ejercicio B').update(position=8)
        self.assertEqual(
            sorted(self.path.lessons.values_list('position', flat=True)), list(range(1, 9))
        )
        output = load(force=True)
        self.assertNotIn('fuera de su posición', output)
        course = fundamentos()
        for item in course['lessons']:
            lesson = self.path.lessons.get(position=item['position'])
            self.assertEqual(
                (lesson.title, lesson.body), (item['title'], official_text(course, item))
            )
        self.assertEqual(self.path.lessons.get(position=7).body, 'Mío A')


class RevertWithAnEditedCourse(MigrationCase):
    """Hallazgos 2 y 3: la copia y el curso editado; los dos órdenes de creación."""

    def copy(self):
        course = fundamentos()
        local = LearningPath.objects.create(
            title=course['title'], area=course['area'], description=course['description']
        )
        for item in course['lessons']:
            Lesson.objects.create(
                path=local,
                position=item['position'],
                title=item['title'],
                body_html=official_html(course, item),
            )
        Lesson.objects.create(path=local, position=7, title='Séptima propia', body='Mía')
        return local

    def progress_on(self, user, slug):
        self.client.force_login(user)
        response = self.client.get(f'/rutas/{slug}/')
        self.assertEqual(response.status_code, 200)
        path = response.context['path']
        done = Progress.objects.filter(user=user, lesson__path=path).count()
        return path.pk, path.lessons.count(), done

    def revert_and_restore(self, copy_first, edit):
        local = self.copy() if copy_first else None
        load()
        local = local or self.copy()
        official = LearningPath.objects.get(slug='fundamentos-qa')
        if edit:
            lesson = official.lessons.get(position=3)
            lesson.body_html = '<p>Texto editado por Carlos</p>'
            lesson.save()
        user = User.objects.create_user('alumna', password=PASSWORD)
        Progress.objects.create(user=user, lesson=official.lessons.get(position=1))
        self.assertEqual(self.progress_on(user, 'fundamentos-qa'), (official.pk, 6, 1))
        backup = Path(tempfile.mkdtemp()) / 'respaldo.json'
        backup.write_text(backup_json(), encoding='utf-8')

        self.migrate(BEFORE)
        self.migrate(self.latest())
        # Dos rutas con el título del curso: ninguna toma la dirección oficial.
        self.assertFalse(LearningPath.objects.filter(slug='fundamentos-qa').exists())
        self.assertEqual(Progress.objects.get(user=user).lesson.path_id, official.pk)

        # Como indica el README: restaurar en la misma base antes de load_courses.
        call_command('loaddata', str(backup), verbosity=0)
        self.assertEqual(self.progress_on(user, 'fundamentos-qa'), (official.pk, 6, 1))
        self.assertEqual(LearningPath.objects.get(pk=local.pk).slug, 'fundamentos-qa-2')
        self.assertEqual(LearningPath.objects.get(pk=local.pk).lessons.count(), 7)
        self.assertIn('Rutas creadas: 0', load())
        if edit:
            self.assertEqual(
                official.lessons.get(position=3).body_html, '<p>Texto editado por Carlos</p>'
            )

    def test_copy_first_and_an_edited_course(self):
        self.revert_and_restore(copy_first=True, edit=True)

    def test_course_first_and_an_identical_copy(self):
        self.revert_and_restore(copy_first=False, edit=False)

    def test_course_first_and_an_edited_course(self):
        self.revert_and_restore(copy_first=False, edit=True)


class UpdateWithExpressions(TestCase):
    """Hallazgo 4: el valor final de una expresión también se comprueba."""

    def test_an_expression_cannot_give_a_local_path_an_official_slug(self):
        local = LearningPath.objects.create(title='Ruta local', area='Transversal', description='d')
        with self.assertRaises(ValidationError):
            LearningPath.objects.filter(pk=local.pk).update(
                slug=Concat(Value('fundamentos-'), Value('qa'))
            )
        self.assertEqual(LearningPath.objects.get(pk=local.pk).slug, 'ruta-local')
        load()
        self.assertEqual(LearningPath.objects.get(pk=local.pk).slug, 'ruta-local')
        self.assertEqual(LearningPath.objects.get(slug='fundamentos-qa').lessons.count(), 6)

    def test_an_expression_cannot_change_an_official_slug(self):
        load()
        local = LearningPath.objects.create(title='Ruta local', area='Transversal', description='d')
        with self.assertRaises(ValidationError):
            LearningPath.objects.all().update(slug=Concat(F('slug'), Value('-x')))
        self.assertTrue(LearningPath.objects.filter(slug='fundamentos-qa').exists())
        # Nada cambió: tampoco la ruta local, porque el cambio se deshace entero.
        self.assertEqual(LearningPath.objects.get(pk=local.pk).slug, 'ruta-local')

    def test_an_expression_still_works_on_local_paths(self):
        load()
        local = LearningPath.objects.create(title='Ruta local', area='Transversal', description='d')
        updated = LearningPath.objects.filter(pk=local.pk).update(
            slug=Concat(F('slug'), Value('-2'))
        )
        self.assertEqual(updated, 1)
        self.assertEqual(LearningPath.objects.get(pk=local.pk).slug, 'ruta-local-2')


class BulkUpdateWithAnIterator(TestCase):
    """Hallazgo 6: la comprobación previa no consume el iterador."""

    def test_the_change_is_saved(self):
        local = LearningPath.objects.create(title='Ruta local', area='Transversal', description='d')
        local.slug = 'nueva'
        self.assertEqual(LearningPath.objects.bulk_update(iter([local]), ['slug']), 1)
        self.assertEqual(LearningPath.objects.get(pk=local.pk).slug, 'nueva')


class RenamedHistoricalResource(SeededBase):
    """Hallazgo 5: un manual con el título antiguo de un recurso histórico renombrado."""

    TITLE = 'Guía de pruebas batch y JCL'

    def test_relink_keeps_the_manual_and_the_historical_link(self):
        historical = Resource.objects.get(title=self.TITLE)
        historical.title = 'Guía batch y JCL (edición 2026)'
        historical.save()
        manual = Resource.objects.create(
            title=self.TITLE, area='Mainframe', kind='Documento', description='Mi manual'
        )
        for options in ({'relink': True}, {'force': True}):
            self.assertIn('recursos vinculados: 0', load(**options), options)
            manual.refresh_from_db()
            historical.refresh_from_db()
            self.assertIsNone(manual.learning_path, options)
            self.assertEqual(historical.learning_path.slug, 'fundamentos-qa')
        self.client.login(username='ana', password=PASSWORD)
        response = self.client.get(f'/resource/{manual.pk}/')
        self.assertContains(response, 'Mi manual')
        self.assertTemplateNotUsed(response, 'learning/path.html')
