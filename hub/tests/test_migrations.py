"""Migraciones de T05 sobre una base con datos (rutas, lecciones con posición repetida y avance)."""

from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from ..services.courses import html_to_text, read_courses, sanitize_html

BEFORE = [('hub', '0003_alter_resource_area')]
AFTER = [('hub', '0006_unique_slug_and_lesson_position')]


def official_text(course, item):
    """Texto plano que Lesson.save() guarda en «body» para una lección oficial."""
    return html_to_text(sanitize_html((course['dir'] / item['file']).read_text(encoding='utf-8')))


class LearningPathMigrations(TransactionTestCase):
    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        self.migrate(executor.loader.graph.leaf_nodes())

    def test_existing_paths_lessons_and_progress_survive(self):
        apps = self.migrate(BEFORE)
        User = apps.get_model('auth', 'User')
        LearningPath = apps.get_model('hub', 'LearningPath')
        Lesson = apps.get_model('hub', 'Lesson')
        Progress = apps.get_model('hub', 'Progress')
        user = User.objects.create(username='migracion')
        first = LearningPath.objects.create(title='Ruta Única', area='Transversal', description='d')
        twin = LearningPath.objects.create(title='Ruta única', area='Transversal', description='d')
        # Una ruta con el nombre de un curso oficial pero sin sus lecciones es local: no recibe
        # el slug reservado (revisión de Codex, 22-11-2026).
        course = LearningPath.objects.create(
            title='QA Avanzado y Especialización', area='Transversal', description='d'
        )
        a = Lesson.objects.create(path=first, title='A', body='a', position=1)
        b = Lesson.objects.create(path=first, title='B', body='b', position=1)
        c = Lesson.objects.create(path=first, title='C', body='c', position=2)
        Lesson.objects.create(path=twin, title='D', body='d', position=1)
        Progress.objects.create(user=user, lesson=b)

        apps = self.migrate(AFTER)
        LearningPath = apps.get_model('hub', 'LearningPath')
        Lesson = apps.get_model('hub', 'Lesson')
        Progress = apps.get_model('hub', 'Progress')
        self.assertEqual(
            dict(LearningPath.objects.values_list('pk', 'slug')),
            {
                first.pk: 'ruta-unica',
                twin.pk: 'ruta-unica-2',
                course.pk: 'qa-avanzado-y-especializacion',
            },
        )
        ordered = Lesson.objects.filter(path_id=first.pk).order_by('position')
        self.assertEqual(list(ordered.values_list('pk', flat=True)), [a.pk, b.pk, c.pk])
        self.assertEqual(list(ordered.values_list('position', flat=True)), [1, 2, 3])
        self.assertEqual(Lesson.objects.count(), 4)
        self.assertTrue(Progress.objects.filter(user_id=user.pk, lesson_id=b.pk).exists())


class UpdateKeepsLocalCoursesApart(TransactionTestCase):
    """Actualización real desde 0003 (T04) hasta la última migración, más load_courses."""

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def latest(self):
        executor = MigrationExecutor(connection)
        return executor.loader.graph.leaf_nodes()

    def tearDown(self):
        self.migrate(self.latest())

    def load(self, **options):
        out = StringIO()
        call_command('load_courses', stdout=out, **options)
        return out.getvalue()

    def test_local_course_named_like_an_official_one_keeps_its_content_and_progress(self):
        apps = self.migrate(BEFORE)
        User = apps.get_model('auth', 'User')
        LearningPath = apps.get_model('hub', 'LearningPath')
        Lesson = apps.get_model('hub', 'Lesson')
        Progress = apps.get_model('hub', 'Progress')
        user = User.objects.create(username='local')
        local = LearningPath.objects.create(
            title='Fundamentos QA', area='Transversal', description='Curso local'
        )
        own = Lesson.objects.create(path=local, title='Mi lección', body='Propia', position=1)
        Progress.objects.create(user=user, lesson=own)

        self.migrate(self.latest())
        from ..models import LearningPath, Lesson, Progress

        self.assertEqual(LearningPath.objects.get(pk=local.pk).slug, 'fundamentos-qa-2')
        for options in ({}, {'force': True}):
            self.load(**options)
            path = LearningPath.objects.get(pk=local.pk)
            self.assertEqual(path.slug, 'fundamentos-qa-2', options)
            self.assertEqual(path.description, 'Curso local', options)
            self.assertEqual(
                list(path.lessons.values_list('pk', 'title', 'body')),
                [(own.pk, 'Mi lección', 'Propia')],
                options,
            )
            self.assertTrue(Progress.objects.filter(user_id=user.pk, lesson_id=own.pk).exists())
            official = LearningPath.objects.get(slug='fundamentos-qa')
            self.assertNotEqual(official.pk, local.pk)
            self.assertEqual(Lesson.objects.filter(path=official).count(), 6, options)
        self.assertEqual(Progress.objects.count(), 1)

    def test_reapplying_after_a_revert_leaves_every_path_local(self):
        """Desde la sexta revisión de Codex (decisión de Carlos, 24-11-2026), la 0005 no intenta
        reconocer el curso tras revertir: ni siquiera el curso intacto recupera su dirección. La
        recupera el respaldo hecho antes de revertir."""
        course = next(c for c in read_courses() if c['slug'] == 'qa-avanzado')
        apps = self.migrate(BEFORE)
        LearningPath = apps.get_model('hub', 'LearningPath')
        Lesson = apps.get_model('hub', 'Lesson')
        # Así queda el curso oficial al revertir a 0003: su título, área y descripción y sus once
        # lecciones con el texto plano de su HTML, más una lección local que se le agregó.
        official = LearningPath.objects.create(
            title=course['title'], area=course['area'], description=course['description']
        )
        for item in course['lessons']:
            Lesson.objects.create(
                path=official,
                title=item['title'],
                body=official_text(course, item),
                position=item['position'],
            )
        Lesson.objects.create(path=official, title='Agregada', body='b', position=12)
        # Otra ruta con el mismo título, pero sin las lecciones del curso, es local.
        twin = LearningPath.objects.create(
            title=course['title'], area=course['area'], description=course['description']
        )
        Lesson.objects.create(path=twin, title='Semana 1 – Otra cosa', body='b', position=1)

        apps = self.migrate(AFTER)
        LearningPath = apps.get_model('hub', 'LearningPath')
        self.assertEqual(
            LearningPath.objects.get(pk=official.pk).slug, 'qa-avanzado-y-especializacion'
        )
        self.assertEqual(
            LearningPath.objects.get(pk=twin.pk).slug, 'qa-avanzado-y-especializacion-2'
        )

    def test_update_links_the_historical_resources_without_touching_local_ones(self):
        apps = self.migrate(BEFORE)
        Resource = apps.get_model('hub', 'Resource')
        historical = Resource.objects.create(
            title='Introducción a DB2 para QA', area='Mainframe', kind='Documento', description='d'
        )
        local = Resource.objects.create(
            title='Recurso local', area='Distribuido', kind='Documento', description='d'
        )

        self.migrate(self.latest())
        from ..models import Resource

        output = self.load()
        self.assertIn('recursos vinculados: 1', output)
        self.assertEqual(
            Resource.objects.get(pk=historical.pk).learning_path.slug,
            'certificacion-requerimiento',
        )
        self.assertIsNone(Resource.objects.get(pk=local.pk).learning_path)


class LocalCopyOfAnOfficialCourse(TransactionTestCase):
    """Una ruta local con el nombre, los títulos y el orden de un curso oficial, pero con sus
    propios textos (revisión de Codex, 22-11-2026). Los datos no permiten saber que es oficial:
    queda como ruta local, con su texto y su avance, en la migración, en la carga normal y con
    --force.
    """

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def latest(self):
        return MigrationExecutor(connection).loader.graph.leaf_nodes()

    def tearDown(self):
        self.migrate(self.latest())

    def course(self):
        return next(c for c in read_courses() if c['slug'] == 'fundamentos-qa')

    def own_text(self, position):
        return f'Ejercicio propio {position}'

    def copy_course(self, LearningPath, Lesson, Progress, user):
        """Crea la copia local y marca como completada su tercera lección."""
        course = self.course()
        local = LearningPath.objects.create(
            title=course['title'], area=course['area'], description='Curso local copiado'
        )
        lessons = {}
        for item in course['lessons']:
            lessons[item['position']] = Lesson.objects.create(
                path=local,
                title=item['title'],
                body=self.own_text(item['position']),
                position=item['position'],
            )
        Progress.objects.create(user=user, lesson=lessons[3])
        return local.pk, lessons[3].pk

    def assert_local_copy_is_intact(self, local_pk, done_pk, user_pk, paths=2):
        from ..models import LearningPath, Lesson, Progress

        course = self.course()
        for options in ({}, {'force': True}):
            call_command('load_courses', stdout=StringIO(), **options)
            local = LearningPath.objects.get(pk=local_pk)
            self.assertEqual(local.slug, 'fundamentos-qa-2', options)
            self.assertEqual(local.description, 'Curso local copiado', options)
            self.assertEqual(
                list(local.lessons.order_by('position').values_list('position', 'title', 'body')),
                [
                    (item['position'], item['title'], self.own_text(item['position']))
                    for item in course['lessons']
                ],
                options,
            )
            done = Lesson.objects.get(pk=done_pk)
            self.assertEqual((done.path_id, done.position), (local_pk, 3), options)
            self.assertEqual(done.body, 'Ejercicio propio 3', options)
            self.assertEqual(
                list(Progress.objects.values_list('user_id', 'lesson_id')), [(user_pk, done_pk)]
            )
            official = LearningPath.objects.get(slug='fundamentos-qa')
            self.assertNotEqual(official.pk, local_pk)
            self.assertEqual(
                list(official.lessons.order_by('position').values_list('title', 'body')),
                [(item['title'], official_text(course, item)) for item in course['lessons']],
                options,
            )
            self.assertEqual(LearningPath.objects.filter(title=course['title']).count(), paths)

    def test_first_update_from_t04_keeps_the_local_copy_apart(self):
        apps = self.migrate(BEFORE)
        user = apps.get_model('auth', 'User').objects.create(username='copia')
        local_pk, done_pk = self.copy_course(
            apps.get_model('hub', 'LearningPath'),
            apps.get_model('hub', 'Lesson'),
            apps.get_model('hub', 'Progress'),
            user,
        )

        self.migrate(self.latest())
        self.assert_local_copy_is_intact(local_pk, done_pk, user.pk)

    def test_reapplying_after_a_revert_keeps_the_local_copy_apart(self):
        from django.contrib.auth.models import User

        from ..models import LearningPath, Lesson, Progress

        user = User.objects.create(username='copia')
        # La copia local se creó antes que el curso oficial: tiene el número interno menor.
        local_pk, done_pk = self.copy_course(LearningPath, Lesson, Progress, user)
        call_command('load_courses', stdout=StringIO())
        official_pk = LearningPath.objects.get(slug='fundamentos-qa').pk
        self.assertGreater(official_pk, local_pk)

        self.migrate(BEFORE)
        apps = self.migrate(AFTER)
        LearningPath = apps.get_model('hub', 'LearningPath')
        # Quinta revisión de Codex: la copia conserva los títulos oficiales, así que no se puede
        # saber cuál es el curso y ninguna toma la dirección. load_courses crea el curso aparte.
        self.assertNotEqual(LearningPath.objects.get(pk=official_pk).slug, 'fundamentos-qa')
        self.assertEqual(LearningPath.objects.get(pk=local_pk).slug, 'fundamentos-qa-2')

        self.migrate(self.latest())
        # La copia, el curso anterior (ahora local) y el curso que crea load_courses.
        self.assert_local_copy_is_intact(local_pk, done_pk, user.pk, paths=3)
