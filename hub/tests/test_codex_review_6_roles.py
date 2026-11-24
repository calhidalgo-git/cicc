"""T06: sexta revisión de Codex (24-11-2026) y revisión completa.

1. El aviso al proteger una lección está en español.
2. La tabla de Usuarios no muestra «Administrador» a quien no tiene grupo.
"""

from django.contrib.auth.models import Group, User
from django.test import TestCase

from ..models import LearningPath, Lesson, Progress

PASSWORD = 'DemoQA!2026'


class ProtectedLessonMessage(TestCase):
    def test_the_message_names_the_person_and_the_lesson(self):
        path = LearningPath.objects.create(title='Ruta local', area='Transversal', description='d')
        lesson = Lesson.objects.create(path=path, position=1, title='A', body='a')
        Progress.objects.create(user=User.objects.create_user('alumna'), lesson=lesson)
        self.client.force_login(User.objects.create_superuser('raiz', password=PASSWORD))
        data = {
            'title': path.title,
            'slug': path.slug,
            'area': path.area,
            'description': path.description,
            'intro_html': '',
            'position': path.position,
            'lessons-TOTAL_FORMS': '1',
            'lessons-INITIAL_FORMS': '1',
            'lessons-MIN_NUM_FORMS': '0',
            'lessons-MAX_NUM_FORMS': '1000',
            'lessons-0-id': lesson.pk,
            'lessons-0-path': path.pk,
            'lessons-0-position': 1,
            'lessons-0-title': 'A',
            'lessons-0-body_html': '',
            'lessons-0-body': 'a',
            'lessons-0-DELETE': 'on',
        }
        response = self.client.post(f'/admin/hub/learningpath/{path.pk}/change/', data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'avance')
        self.assertContains(response, 'alumna completó «A»')
        self.assertNotContains(response, 'Progress object')
        self.assertTrue(Lesson.objects.filter(pk=lesson.pk).exists())


class UsersTableRole(TestCase):
    def test_role_column(self):
        root = User.objects.create_superuser('raiz', password=PASSWORD)
        User.objects.create_user('sinrol', password=PASSWORD)
        editor = User.objects.create_user('editora', password=PASSWORD)
        editor.groups.add(Group.objects.create(name='Editor'))
        self.client.force_login(root)
        response = self.client.get('/p/users/')
        self.assertEqual(response.status_code, 200)
        text = response.content.decode()
        self.assertIn('Superusuario', text)
        self.assertIn('Sin rol', text)
        self.assertIn('Editor', text)
        self.assertNotIn('>Administrador<', text)
