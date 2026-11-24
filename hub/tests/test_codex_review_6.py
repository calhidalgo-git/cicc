"""Sexta revisión de Codex (24-11-2026): no adivinar (decisión de Carlos, opción 1).

1. load_courses marca cada lección oficial; --force solo reescribe lecciones con marca. Un
   ejercicio propio, aunque repita el título de una semana o esté en su posición, nunca se
   reescribe.
2. La 0008 marca las lecciones de los cursos ya cargados solo cuando no hay duda.
3. Tras revertir, ninguna ruta recupera la dirección oficial, ni siquiera el curso reordenado; el
   respaldo hecho antes de revertir la devuelve.
4. El formulario de la ruta admite quitar una lección y dar su puesto a otra en un solo guardado, y
   reordenar con una lección en la posición máxima.
"""

import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from django.test import TestCase

from ..models import LearningPath, Lesson, Progress
from ..views.management import backup_json
from .test_codex_review_3 import BEFORE, PASSWORD, MigrationCase, fundamentos, load, official_text


class OfficialLessonsAreMarked(TestCase):
    def setUp(self):
        load()
        self.course = fundamentos()
        self.path = LearningPath.objects.get(slug='fundamentos-qa')

    def test_every_official_lesson_has_its_mark(self):
        self.assertEqual(
            sorted(self.path.lessons.values_list('position', 'official_key')),
            [(i['position'], f'fundamentos-qa:{i["position"]}') for i in self.course['lessons']],
        )

    def test_force_restores_an_edited_and_moved_official_lesson(self):
        lesson = self.path.lessons.get(position=3)
        lesson.title, lesson.body_html, lesson.position = 'Mía', '<p>Mía</p>', 30
        lesson.save()
        load(force=True)
        lesson.refresh_from_db()
        third = self.course['lessons'][2]
        self.assertEqual(
            (lesson.title, lesson.body), (third['title'], official_text(self.course, third))
        )
        # Se queda donde la puso la persona; la posición 3 no se rellena con otra copia.
        self.assertEqual(lesson.position, 30)
        self.assertEqual(self.path.lessons.count(), 6)

    def test_an_exercise_with_a_week_title_in_its_position_is_never_rewritten(self):
        sixth = self.path.lessons.get(position=6)
        sixth.position = 7
        sixth.save()
        exercise = Lesson.objects.create(
            path=self.path, position=6, title=self.course['lessons'][5]['title'], body='Mío'
        )
        user = User.objects.create_user('alumna', password=PASSWORD)
        Progress.objects.create(user=user, lesson=exercise)
        for options in ({}, {'force': True}):
            load(**options)
            exercise.refresh_from_db()
            self.assertEqual(exercise.body, 'Mío', options)
            self.assertEqual(Progress.objects.get(user=user).lesson_id, exercise.pk)

    def test_a_missing_lesson_in_a_taken_position_is_reported(self):
        lesson = self.path.lessons.get(position=2)
        Progress.objects.filter(lesson=lesson).delete()
        lesson.delete()
        Lesson.objects.create(path=self.path, position=2, title='Práctica', body='Mía')
        output = load()
        self.assertIn('la posición 2', output)
        self.assertIn('la ocupa una lección propia', output)
        self.assertEqual(self.path.lessons.get(position=2).body, 'Mía')


class MarkingExistingCourses(MigrationCase):
    """La 0008 en una instalación con la T05 anterior (cursos ya cargados, sin marcas)."""

    def test_only_intact_lessons_are_marked(self):
        apps = self.migrate([('hub', '0007_resource_opens_learning_path')])
        OldPath = apps.get_model('hub', 'LearningPath')
        OldLesson = apps.get_model('hub', 'Lesson')
        course = fundamentos()
        items = course['lessons']
        path = OldPath.objects.create(
            slug='fundamentos-qa', title=course['title'], area='Transversal', description='d'
        )
        # Intacta, editada, con el título oficial y texto propio, y una práctica con ese título.
        OldLesson.objects.create(
            path=path, position=1, title=items[0]['title'], body=official_text(course, items[0])
        )
        OldLesson.objects.create(
            path=path, position=2, title='Editada', body=official_text(course, items[1])
        )
        OldLesson.objects.create(path=path, position=3, title=items[2]['title'], body='mío')
        OldLesson.objects.create(path=path, position=9, title=items[2]['title'], body='mío')

        self.migrate(self.latest())
        marks = dict(Lesson.objects.filter(path_id=path.pk).values_list('position', 'official_key'))
        self.assertEqual(marks, {1: 'fundamentos-qa:1', 2: '', 3: '', 9: ''})
        # Ninguna lección propia se reescribe ni se pierde con --force.
        load(force=True)
        self.assertEqual(Lesson.objects.get(path_id=path.pk, position=3).body, 'mío')
        self.assertEqual(Lesson.objects.get(path_id=path.pk, position=2).title, 'Editada')


class OlderBackupWithoutMarks(TestCase):
    """Un respaldo anterior a la marca: load_courses marca las lecciones idénticas."""

    def test_intact_lessons_get_their_mark_and_edited_ones_are_kept(self):
        load()
        path = LearningPath.objects.get(slug='fundamentos-qa')
        path.lessons.update(official_key='')
        edited = path.lessons.get(position=4)
        edited.body_html = '<p>Editada</p>'
        edited.save()
        output = load(force=True)
        self.assertEqual(
            path.lessons.exclude(official_key='').count(), 5, 'las cinco idénticas, marcadas'
        )
        edited.refresh_from_db()
        self.assertEqual((edited.official_key, edited.body), ('', 'Editada'))
        self.assertIn('la posición 4', output)


class RevertWithAReorderedCourse(MigrationCase):
    """Hallazgo 2: el curso original reordenado y una copia creada antes."""

    def test_no_path_takes_the_address_and_the_backup_restores_it(self):
        course = fundamentos()
        copy = LearningPath.objects.create(
            title=course['title'], area=course['area'], description=course['description']
        )
        for item in course['lessons']:
            Lesson.objects.create(
                path=copy, position=item['position'], title=item['title'], body='copia'
            )
        Lesson.objects.create(path=copy, position=7, title='Séptima', body='Mía')
        load()
        official = LearningPath.objects.get(slug='fundamentos-qa')
        lessons = list(official.lessons.order_by('position'))
        official.lessons.update(position=models_offset(100))
        for number, lesson in enumerate([lessons[-1], *lessons[:-1]], 1):
            Lesson.objects.filter(pk=lesson.pk).update(position=number)
        user = User.objects.create_user('alumna', password=PASSWORD)
        Progress.objects.create(user=user, lesson=lessons[0])
        backup = Path(tempfile.mkdtemp()) / 'respaldo.json'
        backup.write_text(backup_json(), encoding='utf-8')

        self.migrate(BEFORE)
        self.migrate(self.latest())
        self.assertFalse(LearningPath.objects.filter(slug='fundamentos-qa').exists())

        call_command('loaddata', str(backup), verbosity=0)
        restored = LearningPath.objects.get(slug='fundamentos-qa')
        self.assertEqual(restored.pk, official.pk)
        self.assertEqual(Progress.objects.get(user=user).lesson.path_id, official.pk)
        self.assertEqual(restored.lessons.get(position=1).pk, lessons[-1].pk)
        self.assertEqual(LearningPath.objects.get(pk=copy.pk).lessons.count(), 7)
        self.assertIn('Rutas creadas: 0', load())


def models_offset(amount):
    from django.db.models import F

    return F('position') + amount


class RouteFormPositions(TestCase):
    def setUp(self):
        User.objects.create_superuser('raiz', password=PASSWORD)
        self.client.login(username='raiz', password=PASSWORD)
        self.path = LearningPath.objects.create(
            title='Ruta local', area='Transversal', description='d'
        )

    def post(self, rows):
        data = {
            'title': self.path.title,
            'slug': self.path.slug,
            'area': self.path.area,
            'description': self.path.description,
            'intro_html': '',
            'position': self.path.position,
            'lessons-TOTAL_FORMS': str(len(rows)),
            'lessons-INITIAL_FORMS': str(len(rows)),
            'lessons-MIN_NUM_FORMS': '0',
            'lessons-MAX_NUM_FORMS': '1000',
        }
        for index, (lesson, position, delete) in enumerate(rows):
            data.update(
                {
                    f'lessons-{index}-id': lesson.pk,
                    f'lessons-{index}-path': self.path.pk,
                    f'lessons-{index}-position': position,
                    f'lessons-{index}-title': lesson.title,
                    f'lessons-{index}-body_html': '',
                    f'lessons-{index}-body': lesson.body,
                }
            )
            if delete:
                data[f'lessons-{index}-DELETE'] = 'on'
        return self.client.post(f'/admin/hub/learningpath/{self.path.pk}/change/', data)

    def test_remove_a_lesson_and_reuse_its_position(self):
        a = Lesson.objects.create(path=self.path, position=1, title='A', body='a')
        b = Lesson.objects.create(path=self.path, position=2, title='B', body='b')
        response = self.post([(a, 2, False), (b, 2, True)])
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Lesson.objects.filter(pk=b.pk).exists())
        self.assertEqual(Lesson.objects.get(pk=a.pk).position, 2)

    def test_reorder_with_a_lesson_at_the_maximum_position(self):
        top = 2147483647 if connection.vendor == 'postgresql' else 9223372036854775807
        a = Lesson.objects.create(path=self.path, position=1, title='A', body='a')
        b = Lesson.objects.create(path=self.path, position=2, title='B', body='b')
        c = Lesson.objects.create(path=self.path, position=top, title='C', body='c')
        response = self.post([(a, 2, False), (b, 1, False), (c, top, False)])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(self.path.lessons.order_by('position').values_list('title', flat=True)),
            ['B', 'A', 'C'],
        )
