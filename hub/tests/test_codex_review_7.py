"""Correcciones de la séptima revisión de Codex (24-11-2026).

2. Una lección oficial que pasa a otra ruta pierde su marca: se puede devolver sin error 500.
3. El aviso de posición ocupada distingue otra lección oficial de una propia.
5. Un respaldo con una posición repetida y otra en el máximo del campo se restaura.
"""

import json

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from django.test import TestCase

from ..models import LearningPath, Lesson, Progress
from .temp import temp_folder
from .test_codex_review_3 import PASSWORD, load


class MovingAnOfficialLessonAndBack(TestCase):
    def setUp(self):
        load()
        self.course = LearningPath.objects.get(slug='fundamentos-qa')
        self.other = LearningPath.objects.create(title='Otra', area='Transversal', description='d')
        self.lesson = self.course.lessons.get(position=4)
        self.user = User.objects.create_user('alumna', password=PASSWORD)
        Progress.objects.create(user=self.user, lesson=self.lesson)

    def test_the_lesson_loses_its_mark_and_can_come_back(self):
        self.lesson.path = self.other
        self.lesson.save()
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.official_key, '')
        self.assertIn('lecciones creadas: 1', load())
        replacement = self.course.lessons.get(position=4)
        self.assertEqual(replacement.official_key, 'fundamentos-qa:4')

        # De vuelta al curso, en una posición libre, desde el formulario individual.
        root = User.objects.create_superuser('raiz', password=PASSWORD)
        self.client.force_login(root)
        response = self.client.post(
            f'/admin/hub/lesson/{self.lesson.pk}/change/',
            {
                'path': self.course.pk,
                'title': self.lesson.title,
                'body': self.lesson.body,
                'body_html': self.lesson.body_html,
                'position': 40,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.lesson.refresh_from_db()
        self.assertEqual((self.lesson.path_id, self.lesson.position), (self.course.pk, 40))
        self.assertEqual(Progress.objects.get(user=self.user).lesson_id, self.lesson.pk)


class OccupiedPositionMessage(TestCase):
    def test_another_official_lesson_is_not_called_own(self):
        load()
        course = LearningPath.objects.get(slug='fundamentos-qa')
        course.lessons.get(position=2).delete()
        third = course.lessons.get(position=3)
        third.position = 2
        third.save()
        output = load()
        self.assertIn('la ocupa otra lección oficial', output)
        self.assertNotIn('la ocupa una lección propia', output)
        # La semana 3 ya existe (en la posición 2, con su marca): no se crea una copia.
        third.refresh_from_db()
        self.assertEqual((third.position, third.official_key), (2, 'fundamentos-qa:3'))
        self.assertFalse(course.lessons.filter(position=3).exists())

    def test_an_own_lesson_is_named(self):
        load()
        course = LearningPath.objects.get(slug='fundamentos-qa')
        course.lessons.get(position=2).delete()
        Lesson.objects.create(path=course, position=2, title='Mi práctica', body='Mía')
        self.assertIn('la ocupa una lección propia, «Mi práctica»', load())


class RestoreWithTheMaximumPosition(TestCase):
    def test_a_repeated_position_uses_a_free_number(self):
        top = connection.ops.integer_field_range('PositiveIntegerField')[1]
        path = LearningPath.objects.create(title='Ruta', area='Transversal', description='d')
        data = [
            {
                'model': 'hub.lesson',
                'pk': 9000 + number,
                'fields': {'path': path.pk, 'title': title, 'body': title, 'position': position},
            }
            for number, (title, position) in enumerate((('A', 1), ('B', top), ('C', 1)))
        ]
        fixture = temp_folder(self) / 'respaldo.json'
        fixture.write_text(json.dumps(data), encoding='utf-8')
        call_command('loaddata', str(fixture), verbosity=0)
        self.assertEqual(
            dict(path.lessons.values_list('title', 'position')), {'A': 1, 'B': top, 'C': 2}
        )
