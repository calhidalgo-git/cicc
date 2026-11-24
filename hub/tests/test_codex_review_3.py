"""Correcciones de la tercera revisión de Codex (23-11-2026).

1. Una ruta con las lecciones oficiales y ejercicios propios (por ejemplo en la posición 0) no
   recibe la dirección oficial, y load_courses --force no borra esos ejercicios.
2. El respaldo guarda a las personas por su nombre de usuario: el avance, los intentos y la
   auditoría vuelven a su dueño aunque las cuentas tengan otros números.
3. Al revertir, la dirección oficial no pasa a una copia; con dos copias exactas, ninguna la toma
   y el respaldo hecho antes de revertir se restaura.
4. --relink no vincula un recurso propio que repite el título de uno histórico.
5. Un cambio en lote tampoco cambia ni toma la dirección de un curso oficial.
"""

import json
from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.serializers.base import DeserializationError
from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from ..models import (
    Assessment,
    Attempt,
    Audit,
    LearningPath,
    Lesson,
    Progress,
    Question,
    Resource,
    ResourceVersion,
)
from ..services.courses import html_to_text, read_courses, sanitize_html
from ..views.management import BACKUP_MODELS, backup_json
from .temp import temp_folder

PASSWORD = 'DemoQA!2026'
BEFORE = [('hub', '0003_alter_resource_area')]


def fundamentos():
    return next(c for c in read_courses() if c['slug'] == 'fundamentos-qa')


def official_html(course, item):
    return (course['dir'] / item['file']).read_text(encoding='utf-8')


def official_text(course, item):
    return html_to_text(sanitize_html(official_html(course, item)))


def load(**options):
    out = StringIO()
    call_command('load_courses', stdout=out, **options)
    return out.getvalue()


class MigrationCase(TransactionTestCase):
    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def latest(self):
        return MigrationExecutor(connection).loader.graph.leaf_nodes()

    def tearDown(self):
        self.migrate(self.latest())

    def official_lessons(self):
        course = fundamentos()
        path = LearningPath.objects.get(slug='fundamentos-qa')
        self.assertEqual(
            list(path.lessons.order_by('position').values_list('position', 'title', 'body')),
            [(i['position'], i['title'], official_text(course, i)) for i in course['lessons']],
        )
        return path


class ExercisesNextToTheOfficialLessons(MigrationCase):
    """Hallazgo 1: seis lecciones oficiales idénticas y dos ejercicios propios en la posición 0."""

    def test_update_from_t04_keeps_the_exercises_and_their_progress(self):
        apps = self.migrate(BEFORE)
        OldPath = apps.get_model('hub', 'LearningPath')
        OldLesson = apps.get_model('hub', 'Lesson')
        OldProgress = apps.get_model('hub', 'Progress')
        user = apps.get_model('auth', 'User').objects.create(username='alumna')
        course = fundamentos()
        path = OldPath.objects.create(
            title=course['title'], area=course['area'], description=course['description']
        )
        for item in course['lessons']:
            OldLesson.objects.create(
                path=path,
                position=item['position'],
                title=item['title'],
                body=official_text(course, item),
            )
        first = OldLesson.objects.create(path=path, position=0, title='Ejercicio A', body='Mío A')
        OldLesson.objects.create(path=path, position=0, title='Ejercicio B', body='Mío B')
        OldProgress.objects.create(user=user, lesson=first)

        self.migrate(self.latest())
        for options in ({}, {'force': True}):
            load(**options)
            local = LearningPath.objects.get(pk=path.pk)
            self.assertEqual(local.slug, 'fundamentos-qa-2', options)
            own = dict(local.lessons.values_list('title', 'body'))
            self.assertEqual((own['Ejercicio A'], own['Ejercicio B']), ('Mío A', 'Mío B'), options)
            self.assertEqual(local.lessons.count(), 8, options)
            done = Progress.objects.get(user__username='alumna').lesson
            self.assertEqual((done.pk, done.title, done.body), (first.pk, 'Ejercicio A', 'Mío A'))
            self.assertNotEqual(self.official_lessons().pk, path.pk)


class RevertKeepsTheOfficialAddress(MigrationCase):
    """Hallazgo 3: una copia creada antes que el curso no se queda con su dirección."""

    def copy(self, extra):
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
        if extra:
            Lesson.objects.create(path=local, position=7, title='Séptima propia', body='Mía')
        return local

    def complete_official_lesson(self):
        user = User.objects.create_user('alumna', password=PASSWORD)
        official = LearningPath.objects.get(slug='fundamentos-qa')
        Progress.objects.create(user=user, lesson=official.lessons.get(position=1))
        return user, official

    def progress_on(self, user, slug):
        self.client.force_login(user)
        response = self.client.get(f'/rutas/{slug}/')
        self.assertEqual(response.status_code, 200)
        path = response.context['path']
        return (
            path.pk,
            path.lessons.count(),
            Progress.objects.filter(user=user, lesson__path=path).count(),
        )

    def revert_with_a_copy(self, extra):
        local = self.copy(extra=extra)
        load()
        user, official = self.complete_official_lesson()
        self.assertEqual(self.progress_on(user, 'fundamentos-qa'), (official.pk, 6, 1))
        backup = temp_folder(self) / 'respaldo.json'
        backup.write_text(backup_json(), encoding='utf-8')

        self.migrate(BEFORE)
        self.migrate(self.latest())
        # Las dos rutas cumplen la regla: no se puede saber cuál es el curso y ninguna toma la
        # dirección (antes la tomaba la de número interno menor, la copia).
        slugs = dict(
            LearningPath.objects.filter(title=fundamentos()['title']).values_list('pk', 'slug')
        )
        self.assertEqual(set(slugs), {local.pk, official.pk})
        self.assertNotIn('fundamentos-qa', slugs.values())
        # El avance sigue en su ruta.
        self.assertEqual(Progress.objects.get(user=user).lesson.path_id, official.pk)

        # Como indica el README: restaurar el respaldo justo después de migrar.
        call_command('loaddata', str(backup), verbosity=0)
        self.assertEqual(self.progress_on(user, 'fundamentos-qa'), (official.pk, 6, 1))
        self.assertEqual(LearningPath.objects.get(pk=local.pk).slug, 'fundamentos-qa-2')
        self.assertIn('Rutas creadas: 0', load())
        self.official_lessons()
        self.assertEqual(LearningPath.objects.get(pk=local.pk).lessons.count(), 7 if extra else 6)

    def test_a_copy_with_an_extra_lesson_does_not_take_the_address(self):
        self.revert_with_a_copy(extra=True)

    def test_an_exact_copy_does_not_take_the_address(self):
        self.revert_with_a_copy(extra=False)


class SeededBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', stdout=StringIO())


class DuplicatedHistoricalTitle(SeededBase):
    """Hallazgo 4: un manual propio con el título de un recurso histórico."""

    TITLE = 'Guía de pruebas batch y JCL'

    def test_relink_leaves_both_resources_alone_and_warns(self):
        historical = Resource.objects.get(title=self.TITLE)
        self.assertEqual(historical.learning_path.slug, 'fundamentos-qa')
        manual = Resource.objects.create(
            title=self.TITLE, area='Mainframe', kind='Documento', description='Mi manual'
        )
        output = load(relink=True)
        self.assertIn('recursos vinculados: 0', output)
        self.assertIn(f'Hay más de un recurso titulado «{self.TITLE}»', output)
        manual.refresh_from_db()
        historical.refresh_from_db()
        self.assertIsNone(manual.learning_path)
        self.assertEqual(historical.learning_path.slug, 'fundamentos-qa')
        self.client.login(username='ana', password=PASSWORD)
        response = self.client.get(f'/resource/{manual.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mi manual')
        self.assertTemplateNotUsed(response, 'learning/path.html')

    def test_force_and_first_load_skip_an_ambiguous_title(self):
        Resource.objects.filter(title=self.TITLE).update(learning_path=None)
        Resource.objects.create(
            title=self.TITLE, area='Mainframe', kind='Documento', description='Mi manual'
        )
        output = load(force=True)
        self.assertIn('Hay más de un recurso titulado', output)
        self.assertFalse(Resource.objects.filter(title=self.TITLE, learning_path__isnull=False))
        # Los otros dos recursos históricos siguen abriendo su curso.
        self.assertEqual(
            Resource.objects.get(title='Introducción a DB2 para QA').learning_path.slug,
            'certificacion-requerimiento',
        )


class BulkUpdateKeepsTheOfficialAddress(SeededBase):
    """Hallazgo 5: QuerySet.update() y bulk_update() no pasan por save()."""

    def test_update_cannot_change_or_take_an_official_slug(self):
        with self.assertRaises(ValidationError):
            LearningPath.objects.filter(slug='fundamentos-qa').update(slug='otra-direccion')
        with self.assertRaises(ValidationError):
            LearningPath.objects.all().update(slug='fundamentos-qa')
        local = LearningPath.objects.create(title='Ruta local', area='Transversal', description='d')
        with self.assertRaises(ValidationError):
            LearningPath.objects.filter(pk=local.pk).update(slug='qa-avanzado')
        self.assertTrue(LearningPath.objects.filter(slug='fundamentos-qa').exists())
        self.assertIn('Rutas creadas: 0; lecciones creadas: 0', load())

    def test_bulk_update_cannot_change_an_official_slug(self):
        course = LearningPath.objects.get(slug='fundamentos-qa')
        course.slug = 'otra-direccion'
        with self.assertRaises(ValidationError):
            LearningPath.objects.bulk_update([course], ['slug'])
        self.assertTrue(LearningPath.objects.filter(slug='fundamentos-qa').exists())

    def test_local_paths_and_other_fields_still_update_in_bulk(self):
        local = LearningPath.objects.create(title='Ruta local', area='Transversal', description='d')
        self.assertEqual(LearningPath.objects.filter(pk=local.pk).update(slug='nueva'), 1)
        self.assertEqual(
            LearningPath.objects.filter(slug='fundamentos-qa').update(description='Nueva'), 1
        )
        # Volver a guardar la misma dirección oficial no es un cambio.
        self.assertEqual(
            LearningPath.objects.filter(slug='qa-avanzado').update(slug='qa-avanzado'), 1
        )
        local.slug = 'otra'
        LearningPath.objects.bulk_update([local], ['slug'])
        self.assertEqual(LearningPath.objects.get(pk=local.pk).slug, 'otra')


class BackupKeepsPeopleByUsername(SeededBase):
    """Hallazgo 2: las cuentas del destino tienen otros números internos."""

    def make_history(self):
        ana = User.objects.get(username='ana')
        lesson = Lesson.objects.filter(path__slug='fundamentos-qa').get(position=1)
        Progress.objects.create(user=ana, lesson=lesson)
        Attempt.objects.create(
            user=ana,
            assessment=Assessment.objects.first(),
            deadline=timezone.now() + timedelta(minutes=5),
            finished=True,
            score=75,
        )
        self.client.login(username='admin', password=PASSWORD)
        response = self.client.post('/backup/')
        self.assertEqual(response.status_code, 200)
        backup = temp_folder(self) / 'respaldo.json'
        backup.write_bytes(response.content)
        return backup

    def empty_content(self):
        for model in reversed(BACKUP_MODELS):
            model.objects.all().delete()

    def test_people_are_stored_by_username(self):
        data = json.loads(self.make_history().read_text(encoding='utf-8'))
        for item in data:
            if item['model'] in ('hub.progress', 'hub.attempt', 'hub.audit'):
                self.assertIsInstance(item['fields']['user'], list, item['model'])
        self.assertIn(['ana'], [i['fields']['user'] for i in data if i['model'] == 'hub.progress'])

    def test_restore_with_accounts_numbered_differently(self):
        backup = self.make_history()
        self.empty_content()
        # Otra instalación: las mismas cuentas, creadas en otro orden.
        old = dict(User.objects.values_list('username', 'pk'))
        User.objects.all().delete()
        names = list(old)
        for username, pk in zip(names, reversed([old[n] for n in names]), strict=True):
            User.objects.create_user(username, password=PASSWORD, pk=pk)
        self.assertNotEqual(User.objects.get(username='ana').pk, old['ana'])

        call_command('loaddata', str(backup), verbosity=0)
        progress = Progress.objects.get()
        self.assertEqual(progress.user.username, 'ana')
        attempt = Attempt.objects.get(score=75)
        self.assertEqual(attempt.user.username, 'ana')
        audit = Audit.objects.get(action='Exportación respaldo de contenido')
        self.assertEqual(audit.user.username, 'admin')

    def test_missing_account_stops_the_restore_without_changes(self):
        backup = self.make_history()
        self.empty_content()
        User.objects.filter(username='ana').delete()
        with self.assertRaises((IntegrityError, DeserializationError)):
            call_command('loaddata', str(backup), verbosity=0)
        for model in (Resource, ResourceVersion, LearningPath, Lesson, Question, Progress, Attempt):
            self.assertFalse(model.objects.exists(), model.__name__)

    def test_an_older_backup_with_numbers_still_loads(self):
        backup = self.make_history()
        data = json.loads(backup.read_text(encoding='utf-8'))
        users = dict(User.objects.values_list('username', 'pk'))
        for item in data:
            if isinstance(item['fields'].get('user'), list):
                item['fields']['user'] = users[item['fields']['user'][0]]
        backup.write_text(json.dumps(data), encoding='utf-8')
        self.empty_content()
        call_command('loaddata', str(backup), verbosity=0)
        self.assertEqual(Progress.objects.get().user.username, 'ana')
