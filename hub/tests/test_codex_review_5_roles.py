"""T06: correcciones de la quinta revisión de Codex (24-11-2026).

1. Quitar una lección con avances desde el formulario de su ruta, borrar la lección o borrar la
   ruta no borra ningún avance: el administrador lo impide (decisión de Carlos).
2. Una base con la 0010 original aplicada, sin la última migración de auth, se puede actualizar.
"""

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase

from ..models import LearningPath, Lesson, Progress
from .test_codex_review_4_roles import MigrationCase

PASSWORD = 'DemoQA!2026'


class LessonsWithProgressAreProtected(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.path = LearningPath.objects.create(
            title='Ruta local', area='Transversal', description='d'
        )
        cls.first = Lesson.objects.create(path=cls.path, position=1, title='A', body='a')
        cls.second = Lesson.objects.create(path=cls.path, position=2, title='B', body='b')
        cls.progress = Progress.objects.create(
            user=User.objects.create_user('alumna', password=PASSWORD), lesson=cls.first
        )
        cls.root = User.objects.create_superuser('raiz', password=PASSWORD)

    def setUp(self):
        self.client.force_login(self.root)

    def form_data(self, delete):
        data = {
            'title': self.path.title,
            'slug': self.path.slug,
            'area': self.path.area,
            'description': self.path.description,
            'intro_html': '',
            'position': self.path.position,
            'lessons-TOTAL_FORMS': '2',
            'lessons-INITIAL_FORMS': '2',
            'lessons-MIN_NUM_FORMS': '0',
            'lessons-MAX_NUM_FORMS': '1000',
        }
        for index, lesson in enumerate((self.first, self.second)):
            data.update(
                {
                    f'lessons-{index}-id': lesson.pk,
                    f'lessons-{index}-path': self.path.pk,
                    f'lessons-{index}-position': lesson.position,
                    f'lessons-{index}-title': lesson.title,
                    f'lessons-{index}-body_html': '',
                    f'lessons-{index}-body': lesson.body,
                }
            )
            if lesson in delete:
                data[f'lessons-{index}-DELETE'] = 'on'
        return data

    def test_removing_the_lesson_from_its_path_form_is_refused(self):
        response = self.client.post(
            f'/admin/hub/learningpath/{self.path.pk}/change/', self.form_data({self.first})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Lesson.objects.filter(pk=self.first.pk).exists())
        self.assertTrue(Progress.objects.filter(pk=self.progress.pk).exists())

    def test_a_lesson_without_progress_can_still_be_removed(self):
        response = self.client.post(
            f'/admin/hub/learningpath/{self.path.pk}/change/', self.form_data({self.second})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Lesson.objects.filter(pk=self.second.pk).exists())

    def test_deleting_the_lesson_or_the_path_is_refused(self):
        for url in (
            f'/admin/hub/lesson/{self.first.pk}/delete/',
            f'/admin/hub/learningpath/{self.path.pk}/delete/',
        ):
            self.client.post(url, {'post': 'yes'})
            self.assertTrue(Progress.objects.filter(pk=self.progress.pk).exists(), url)
        self.assertTrue(LearningPath.objects.filter(pk=self.path.pk).exists())


class UpdateFromTheOriginal0010(MigrationCase):
    def test_a_base_without_the_last_auth_migration_updates(self):
        # Como dejaba la 0010 original desde una base vacía: auth sin su migración 0012.
        self.migrate([('auth', '0011_update_proxy_permissions')])
        loader = MigrationLoader(connection)
        self.assertIn(('hub', '0010_roles_permissions'), loader.applied_migrations)
        self.assertNotIn(
            ('auth', '0012_alter_user_first_name_max_length'), loader.applied_migrations
        )
        loader.check_consistent_history(connection)
        call_command('migrate', verbosity=0, stdout=StringIO())
        self.assertIn(
            ('hub', '0012_progress_protects_lesson'), MigrationLoader(connection).applied_migrations
        )
