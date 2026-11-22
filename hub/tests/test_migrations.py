"""Migraciones de T05 sobre una base con datos (rutas, lecciones con posición repetida y avance)."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [('hub', '0003_alter_resource_area')]
AFTER = [('hub', '0006_unique_slug_and_lesson_position')]


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
            {first.pk: 'ruta-unica', twin.pk: 'ruta-unica-2', course.pk: 'qa-avanzado'},
        )
        ordered = Lesson.objects.filter(path_id=first.pk).order_by('position')
        self.assertEqual(list(ordered.values_list('pk', flat=True)), [a.pk, b.pk, c.pk])
        self.assertEqual(list(ordered.values_list('position', flat=True)), [1, 2, 3])
        self.assertEqual(Lesson.objects.count(), 4)
        self.assertTrue(Progress.objects.filter(user_id=user.pk, lesson_id=b.pk).exists())
