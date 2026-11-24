"""Correcciones de T05 tras la revisión de Codex (22-11-2026).

- Los tres cursos oficiales tienen la identidad reservada: una ruta local con el mismo nombre
  queda separada, con su contenido y su avance, en la carga normal y con --force.
- La carga vincula los recursos históricos con su curso (veto de Carlos a D4).
- Las direcciones antiguas /qa/... conservan sus rangos de 6, 11 y 6.
- Un respaldo JSON de T04 se restaura directamente en T05.
"""

import json
from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from ..models import LearningPath, Lesson, Progress, Resource
from ..services.courses import official_slugs, read_courses
from .temp import temp_folder

PASSWORD = 'DemoQA!2026'
OFFICIAL = {'fundamentos-qa': 6, 'qa-avanzado': 11, 'certificacion-requerimiento': 6}


def load(**options):
    out = StringIO()
    call_command('load_courses', stdout=out, **options)
    return out.getvalue()


class SeededBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', stdout=StringIO())

    def ana(self):
        return User.objects.get(username='ana')

    def remove_official_courses(self):
        """Simula una base anterior a la carga de los cursos oficiales."""
        LearningPath.objects.filter(slug__in=official_slugs()).delete()

    def official_lesson_counts(self):
        return {slug: Lesson.objects.filter(path__slug=slug).count() for slug in sorted(OFFICIAL)}


class ReservedIdentity(SeededBase):
    def test_official_slugs_come_from_the_course_files(self):
        self.assertEqual(official_slugs(), frozenset(OFFICIAL))

    def test_local_path_with_an_official_name_gets_another_slug(self):
        local = LearningPath.objects.create(
            title='Fundamentos QA', area='Transversal', description='Ruta local'
        )
        self.assertEqual(local.slug, 'fundamentos-qa-2')

    def test_local_path_created_before_the_courses_stays_separate_with_its_progress(self):
        self.remove_official_courses()
        local = LearningPath.objects.create(
            title='Fundamentos QA', area='Transversal', description='Ruta local'
        )
        self.assertNotIn(local.slug, official_slugs())
        own = Lesson.objects.create(path=local, position=1, title='Mi lección', body='Propia')
        Progress.objects.create(user=self.ana(), lesson=own)

        for options in ({}, {'force': True}):
            load(**options)
            local.refresh_from_db()
            own.refresh_from_db()
            self.assertEqual(local.title, 'Fundamentos QA', options)
            self.assertEqual(local.description, 'Ruta local', options)
            self.assertEqual(list(local.lessons.values_list('title', flat=True)), ['Mi lección'])
            self.assertEqual(own.body, 'Propia', options)
            self.assertTrue(Progress.objects.filter(user=self.ana(), lesson=own).exists())
            self.assertEqual(self.official_lesson_counts(), OFFICIAL, options)
            self.assertNotEqual(LearningPath.objects.get(slug='fundamentos-qa').pk, local.pk)

    def test_a_reserved_slug_cannot_be_taken_by_another_path(self):
        for slug in sorted(OFFICIAL):
            path = LearningPath(title='Otra ruta', area='Transversal', description='d', slug=slug)
            with self.assertRaises(ValidationError) as caught:
                path.full_clean()
            self.assertIn('slug', caught.exception.message_dict)
            with self.assertRaises(ValidationError):
                path.save()
        local = LearningPath.objects.create(title='Ruta local', area='Transversal', description='d')
        local.slug = 'qa-avanzado'
        with self.assertRaises(ValidationError):
            local.save()
        self.assertEqual(LearningPath.objects.get(pk=local.pk).slug, 'ruta-local')

    def test_the_official_course_can_still_be_edited(self):
        course = LearningPath.objects.get(slug='qa-avanzado')
        course.description = 'Editada en el administrador'
        course.full_clean()
        course.save()
        course.refresh_from_db()
        self.assertEqual(course.description, 'Editada en el administrador')

    def test_admin_rejects_a_reserved_slug(self):
        self.assertTrue(self.client.login(username='admin', password=PASSWORD))
        response = self.client.post(
            '/admin/hub/learningpath/add/',
            {
                'title': 'Fundamentos QA',
                'slug': 'fundamentos-qa',
                'area': 'Transversal',
                'description': 'Ruta local',
                'intro_html': '',
                'position': 0,
                'lessons-TOTAL_FORMS': 0,
                'lessons-INITIAL_FORMS': 0,
                'lessons-MIN_NUM_FORMS': 0,
                'lessons-MAX_NUM_FORMS': 1000,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'reservada para un curso oficial')
        self.assertEqual(LearningPath.objects.filter(title='Fundamentos QA').count(), 1)


class OfficialAddressIsFixed(SeededBase):
    """La dirección de un curso oficial no cambia (revisión de Codex, 22-11-2026)."""

    def edit_form(self, path, **changes):
        data = {
            'title': path.title,
            'slug': path.slug,
            'area': path.area,
            'description': path.description,
            'intro_html': path.intro_html,
            'position': path.position,
            'lessons-TOTAL_FORMS': 0,
            'lessons-INITIAL_FORMS': 0,
            'lessons-MIN_NUM_FORMS': 0,
            'lessons-MAX_NUM_FORMS': 1000,
        }
        data.update(changes)
        return data

    def test_the_model_rejects_a_new_slug_for_an_official_course(self):
        course = LearningPath.objects.get(slug='fundamentos-qa')
        course.slug = 'otra-direccion'
        with self.assertRaises(ValidationError) as caught:
            course.full_clean()
        self.assertIn('slug', caught.exception.message_dict)
        with self.assertRaises(ValidationError):
            course.save()
        self.assertEqual(LearningPath.objects.get(pk=course.pk).slug, 'fundamentos-qa')

    def test_admin_edit_form_keeps_the_official_address(self):
        course = LearningPath.objects.get(slug='fundamentos-qa')
        lessons = course.lessons.count()
        Progress.objects.create(user=self.ana(), lesson=course.lessons.first())
        self.assertTrue(self.client.login(username='admin', password=PASSWORD))
        url = f'/admin/hub/learningpath/{course.pk}/change/'

        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'name="slug"')
        self.assertContains(page, 'fundamentos-qa')

        response = self.client.post(
            url, self.edit_form(course, slug='otra-direccion', description='Editada')
        )
        self.assertEqual(response.status_code, 302)
        course.refresh_from_db()
        self.assertEqual(course.slug, 'fundamentos-qa')
        self.assertEqual(course.description, 'Editada')

        self.assertIn('Rutas creadas: 0', load())
        self.assertEqual(LearningPath.objects.filter(title='Fundamentos QA').count(), 1)
        self.assertEqual(course.lessons.count(), lessons)
        self.client.login(username='ana', password=PASSWORD)
        response = self.client.get('/rutas/fundamentos-qa/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['done_count'], 1)

    def test_a_local_path_can_still_change_its_address(self):
        local = LearningPath.objects.create(title='Ruta local', area='Transversal', description='d')
        self.assertTrue(self.client.login(username='admin', password=PASSWORD))
        url = f'/admin/hub/learningpath/{local.pk}/change/'
        self.assertContains(self.client.get(url), 'name="slug"')
        response = self.client.post(url, self.edit_form(local, slug='mi-ruta'))
        self.assertEqual(response.status_code, 302)
        local.refresh_from_db()
        self.assertEqual(local.slug, 'mi-ruta')


class HistoricalResources(SeededBase):
    HISTORICAL = {
        'Guía de pruebas batch y JCL': 'fundamentos-qa',
        'Checklist de pruebas de API REST': 'qa-avanzado',
        'Introducción a DB2 para QA': 'certificacion-requerimiento',
    }

    def linked(self):
        return dict(
            Resource.objects.filter(title__in=self.HISTORICAL).values_list(
                'title', 'learning_path__slug'
            )
        )

    def test_update_links_the_three_historical_resources_again(self):
        # Al actualizar, los cursos se crean después de migrar y los recursos no tienen ruta.
        self.remove_official_courses()
        self.assertEqual(set(self.linked().values()), {None})
        output = load()
        self.assertEqual(self.linked(), self.HISTORICAL)
        self.assertIn('recursos vinculados: 3', output)
        self.client.login(username='ana', password=PASSWORD)
        for title, slug in self.HISTORICAL.items():
            response = self.client.get(f'/resource/{Resource.objects.get(title=title).pk}/')
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'learning/path.html')
            self.assertEqual(response.context['path'].slug, slug)

    def test_linking_respects_local_resources_and_local_paths(self):
        self.remove_official_courses()
        local_path = LearningPath.objects.create(
            title='Fundamentos QA', area='Transversal', description='Ruta local'
        )
        chosen = Resource.objects.get(title='Checklist de pruebas de API REST')
        chosen.learning_path = local_path
        chosen.save()
        other = Resource.objects.create(
            title='Mi recurso local', area='Mainframe', kind='Documento', description='d'
        )
        load()
        chosen.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(chosen.learning_path, local_path)
        self.assertIsNone(other.learning_path)
        self.assertEqual(
            Resource.objects.get(title='Guía de pruebas batch y JCL').learning_path.slug,
            'fundamentos-qa',
        )
        self.assertFalse(Resource.objects.filter(learning_path=local_path).exclude(pk=chosen.pk))

    def test_normal_load_keeps_a_manual_unlink_and_force_restores_it(self):
        resource = Resource.objects.get(title='Introducción a DB2 para QA')
        resource.learning_path = None
        resource.save()
        load()
        resource.refresh_from_db()
        self.assertIsNone(resource.learning_path)
        load(force=True)
        resource.refresh_from_db()
        self.assertEqual(resource.learning_path.slug, 'certificacion-requerimiento')

    def test_relink_repairs_only_the_empty_links_of_an_earlier_t05(self):
        """Instalación con la T05 anterior (beec6b6): cursos cargados, recursos sin vínculo."""
        Resource.objects.filter(title__in=self.HISTORICAL).update(learning_path=None)
        local_path = LearningPath.objects.create(
            title='Ruta local', area='Transversal', description='d'
        )
        chosen = Resource.objects.get(title='Checklist de pruebas de API REST')
        chosen.learning_path = local_path
        chosen.save()
        course = LearningPath.objects.get(slug='fundamentos-qa')
        course.description = 'Editada a mano'
        course.save()
        lesson = course.lessons.get(position=2)
        lesson.title = 'Mi título'
        lesson.body_html = '<p>Mi texto</p>'
        lesson.save()
        # La carga normal no repara esos vínculos (el curso ya existía).
        self.assertIn('recursos vinculados: 0', load())
        # Una lección oficial borrada a propósito: --relink no la vuelve a crear.
        Lesson.objects.filter(path=course, position=6).delete()
        counts = (LearningPath.objects.count(), Lesson.objects.count())

        output = load(relink=True)
        self.assertIn('Rutas creadas: 0; lecciones creadas: 0; reescritas: 0', output)
        self.assertIn('recursos vinculados: 2', output)
        expected = dict(self.HISTORICAL)
        expected[chosen.title] = 'ruta-local'
        self.assertEqual(self.linked(), expected)
        self.assertEqual((LearningPath.objects.count(), Lesson.objects.count()), counts)
        course.refresh_from_db()
        lesson.refresh_from_db()
        self.assertEqual(course.description, 'Editada a mano')
        self.assertEqual((lesson.title, lesson.body_html), ('Mi título', '<p>Mi texto</p>'))
        self.assertFalse(course.lessons.filter(position=6).exists())
        # Repetirla no cambia nada.
        self.assertIn('recursos vinculados: 0', load(relink=True))

    def test_relink_and_force_cannot_be_combined(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command('load_courses', '--relink', '--force', stdout=StringIO())

    def test_every_course_lists_its_historical_titles(self):
        for course in read_courses():
            self.assertTrue(course['legacy_resource_titles'], course['slug'])


class LegacyRanges(SeededBase):
    def setUp(self):
        self.client.login(username='ana', password=PASSWORD)

    def test_old_addresses_keep_6_11_and_6(self):
        for prefix, slug, length in (
            ('/qa/fundamentos/semana', 'fundamentos-qa', 6),
            ('/qa/avanzado/semana', 'qa-avanzado', 11),
            ('/qa/certificacion/tema', 'certificacion-requerimiento', 6),
        ):
            path = LearningPath.objects.get(slug=slug)
            Lesson.objects.create(path=path, position=length + 1, title='Ampliación', body='Nueva')
            last = self.client.get(f'{prefix}/{length}/')
            self.assertEqual(last.status_code, 301, prefix)
            self.assertEqual(last['Location'], f'/rutas/{slug}/{length}/')
            self.assertEqual(self.client.get(f'{prefix}/{length + 1}/').status_code, 404, prefix)
            self.assertEqual(self.client.get(f'{prefix}/0/').status_code, 404, prefix)
            # La ampliación se abre en la dirección nueva.
            self.assertEqual(self.client.get(f'/rutas/{slug}/{length + 1}/').status_code, 200)


def t04_backup(users):
    """Respaldo JSON con el formato de /backup/ en T04: sin slug, posición de ruta ni HTML."""
    ana, lucia = users
    return [
        {
            'model': 'hub.resource',
            'pk': 501,
            'fields': {
                'title': 'Guía de pruebas batch y JCL',
                'area': 'Mainframe',
                'kind': 'Documento',
                'description': 'Recurso histórico',
                'url': '',
                'published': True,
            },
        },
        {
            'model': 'hub.resource',
            'pk': 502,
            'fields': {
                'title': 'Recurso local',
                'area': 'Distribuido',
                'kind': 'Documento',
                'description': 'Sin curso',
                'url': '',
                'published': True,
            },
        },
        {
            'model': 'hub.learningpath',
            'pk': 701,
            'fields': {'title': 'Ruta Mainframe', 'area': 'Mainframe', 'description': 'Uno'},
        },
        {
            'model': 'hub.learningpath',
            'pk': 702,
            'fields': {'title': 'Ruta Mainframe', 'area': 'Mainframe', 'description': 'Dos'},
        },
        {
            'model': 'hub.learningpath',
            'pk': 703,
            'fields': {'title': 'Fundamentos QA', 'area': 'Transversal', 'description': 'Local'},
        },
        {
            'model': 'hub.lesson',
            'pk': 801,
            'fields': {'path': 701, 'title': 'A', 'body': 'Texto A', 'position': 1},
        },
        {
            'model': 'hub.lesson',
            'pk': 802,
            'fields': {'path': 701, 'title': 'B', 'body': 'Texto B', 'position': 1},
        },
        {
            'model': 'hub.lesson',
            'pk': 803,
            'fields': {'path': 702, 'title': 'C', 'body': 'Texto C', 'position': 1},
        },
        {
            'model': 'hub.lesson',
            'pk': 804,
            'fields': {'path': 703, 'title': 'Mi lección', 'body': 'Propia', 'position': 1},
        },
        {'model': 'hub.progress', 'pk': 901, 'fields': {'user': ana.pk, 'lesson': 802}},
        {'model': 'hub.progress', 'pk': 902, 'fields': {'user': ana.pk, 'lesson': 804}},
        {'model': 'hub.progress', 'pk': 903, 'fields': {'user': lucia.pk, 'lesson': 803}},
    ]


class RestoreT04Backup(SeededBase):
    def write(self, objects):
        folder = temp_folder(self, prefix='cicc-respaldo-')
        target = folder / 'respaldo-t04.json'
        target.write_text(json.dumps(objects, ensure_ascii=False), encoding='utf-8')
        return target

    def empty_content(self):
        """Base vacía de contenido (solo migrate y las cuentas), como pide la restauración."""
        for model in (Progress, Lesson, LearningPath, Resource):
            model.objects.all().delete()

    def test_t04_backup_with_several_paths_and_progress_restores_directly(self):
        users = (self.ana(), User.objects.get(username='lucia'))
        self.empty_content()
        backup = self.write(t04_backup(users))
        call_command('loaddata', str(backup), verbosity=0)

        slugs = dict(LearningPath.objects.values_list('pk', 'slug'))
        self.assertEqual(
            slugs, {701: 'ruta-mainframe', 702: 'ruta-mainframe-2', 703: 'fundamentos-qa-2'}
        )
        # La lección con posición repetida pasa al final de su ruta, en el orden del respaldo.
        self.assertEqual(
            list(
                Lesson.objects.filter(path_id=701)
                .order_by('position')
                .values_list('pk', 'position')
            ),
            [(801, 1), (802, 2)],
        )
        self.assertEqual(
            set(Progress.objects.values_list('user_id', 'lesson_id')),
            {(users[0].pk, 802), (users[0].pk, 804), (users[1].pk, 803)},
        )

        load()
        self.assertEqual(self.official_lesson_counts(), OFFICIAL)
        self.assertEqual(LearningPath.objects.get(pk=703).lessons.count(), 1)
        self.assertEqual(Resource.objects.get(pk=501).learning_path.slug, 'fundamentos-qa')
        self.assertIsNone(Resource.objects.get(pk=502).learning_path)
        self.assertEqual(Progress.objects.count(), 3)

        self.client.login(username='ana', password=PASSWORD)
        response = self.client.get('/rutas/ruta-mainframe/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['done_count'], 1)
        response = self.client.get('/rutas/fundamentos-qa-2/')
        self.assertEqual(response.context['done_count'], 1)

    def test_backup_over_an_official_course_is_rejected_without_changes(self):
        users = (self.ana(), User.objects.get(username='lucia'))
        official = LearningPath.objects.get(slug='fundamentos-qa')
        objects = t04_backup(users)
        for item in objects:
            if item['model'] == 'hub.learningpath' and item['pk'] == 701:
                item['pk'] = official.pk
            if item['model'] == 'hub.lesson' and item['fields']['path'] == 701:
                item['fields']['path'] = official.pk
        before = (LearningPath.objects.count(), Lesson.objects.count(), Progress.objects.count())
        with self.assertRaisesMessage(Exception, 'Restaura el respaldo en una base vacía'):
            call_command('loaddata', str(self.write(objects)), verbosity=0)
        official.refresh_from_db()
        self.assertEqual(official.slug, 'fundamentos-qa')
        self.assertEqual(official.title, 'Fundamentos QA')
        self.assertEqual(
            (LearningPath.objects.count(), Lesson.objects.count(), Progress.objects.count()),
            before,
        )
