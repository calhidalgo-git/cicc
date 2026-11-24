"""Correcciones de la quinta revisión de Codex (24-11-2026), opción 2 de Carlos.

1. Un ejercicio completado en una posición del curso conserva su contenido y su avance con --force.
2. Al revertir, la copia no hereda la dirección aunque el curso haya cambiado de nombre o de
   todos sus textos.
3. Las lecciones de una ruta se reordenan en un solo guardado del administrador.
4. Una práctica al final con el título de una semana no impide reponer una semana ausente.
"""

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from ..models import LearningPath, Lesson, Progress
from ..views.management import backup_json
from .temp import temp_folder
from .test_codex_review_3 import (
    BEFORE,
    PASSWORD,
    MigrationCase,
    fundamentos,
    load,
    official_html,
    official_text,
)


def official_path(course):
    path = LearningPath(
        slug=course['slug'],
        title=course['title'],
        area=course['area'],
        description=course['description'],
    )
    path._official_course = True
    path.save()
    return path


class ForceKeepsAnUnrecognisedLesson(TestCase):
    """Hallazgo 1: semanas 1 a 5 en su lugar, un ejercicio en la 6 y la semana 6 renombrada en 7.

    Desde la sexta revisión, las lecciones oficiales llevan marca (``official_key``): el ejercicio
    no la tiene y --force no lo toca; la semana 6 sí, y se repone aunque esté en la posición 7.
    """

    def setUp(self):
        self.course = fundamentos()
        self.path = official_path(self.course)
        for item in self.course['lessons'][:5]:
            Lesson.objects.create(
                path=self.path,
                position=item['position'],
                title=item['title'],
                body_html=official_html(self.course, item),
                official_key=f'fundamentos-qa:{item["position"]}',
            )
        self.exercise = Lesson.objects.create(
            path=self.path, position=6, title='Ejercicio A', body='Mío A'
        )
        self.sixth = Lesson.objects.create(
            path=self.path,
            position=7,
            title='Semana 6 renombrada',
            body_html='<p>Editada</p>',
            official_key='fundamentos-qa:6',
        )
        self.user = User.objects.create_user('alumna', password=PASSWORD)
        Progress.objects.create(user=self.user, lesson=self.exercise)

    def test_the_exercise_and_its_progress_survive(self):
        for options in ({}, {'force': True}):
            load(**options)
            self.exercise.refresh_from_db()
            self.assertEqual((self.exercise.title, self.exercise.body), ('Ejercicio A', 'Mío A'))
            self.assertEqual(Progress.objects.get(user=self.user).lesson_id, self.exercise.pk)
            self.assertEqual(self.path.lessons.count(), 7)

    def test_force_restores_the_sixth_week_where_it_is(self):
        load(force=True)
        sixth = self.course['lessons'][5]
        self.sixth.refresh_from_db()
        self.assertEqual(
            (self.sixth.position, self.sixth.title, self.sixth.body),
            (7, sixth['title'], official_text(self.course, sixth)),
        )


class PracticeWithARepeatedTitle(TestCase):
    """Hallazgo 9: falta la semana 2 y hay una práctica al final con el título de la semana 1."""

    def test_the_missing_week_is_created_and_the_practice_kept(self):
        course = fundamentos()
        path = official_path(course)
        for item in course['lessons']:
            if item['position'] != 2:
                Lesson.objects.create(
                    path=path,
                    position=item['position'],
                    title=item['title'],
                    body_html=official_html(course, item),
                )
        practice = Lesson.objects.create(
            path=path, position=7, title=course['lessons'][0]['title'], body='Mi práctica'
        )
        output = load()
        self.assertNotIn('la ocupa una lección propia', output)
        self.assertIn('lecciones creadas: 1', output)
        self.assertEqual(path.lessons.get(position=2).title, course['lessons'][1]['title'])
        practice.refresh_from_db()
        self.assertEqual((practice.position, practice.body), (7, 'Mi práctica'))


class RevertWithARenamedOrRewrittenCourse(MigrationCase):
    """Hallazgo 2: el curso original cambió de nombre o de todos sus textos."""

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

    def revert_and_restore(self, change):
        local = self.copy()
        load()
        official = LearningPath.objects.get(slug='fundamentos-qa')
        change(official)
        user = User.objects.create_user('alumna', password=PASSWORD)
        Progress.objects.create(user=user, lesson=official.lessons.get(position=1))
        self.assertEqual(self.progress_on(user, 'fundamentos-qa'), (official.pk, 6, 1))
        backup = temp_folder(self) / 'respaldo.json'
        backup.write_text(backup_json(), encoding='utf-8')

        self.migrate(BEFORE)
        self.migrate(self.latest())
        self.assertFalse(LearningPath.objects.filter(slug='fundamentos-qa').exists())
        self.assertEqual(Progress.objects.get(user=user).lesson.path_id, official.pk)

        call_command('loaddata', str(backup), verbosity=0)
        self.assertEqual(self.progress_on(user, 'fundamentos-qa'), (official.pk, 6, 1))
        self.assertEqual(LearningPath.objects.get(pk=local.pk).lessons.count(), 7)

    def test_the_course_changed_its_title(self):
        def rename(path):
            path.title = 'Fundamentos QA (edición 2026)'
            path.save()

        self.revert_and_restore(rename)

    def test_the_course_rewrote_all_its_texts(self):
        def rewrite(path):
            for lesson in path.lessons.all():
                lesson.body_html = f'<p>Texto propio {lesson.position}</p>'
                lesson.save()

        self.revert_and_restore(rewrite)


class ReorderLessonsInOneSave(TestCase):
    """Hallazgo 6: intercambiar posiciones desde el formulario de la ruta."""

    def form_data(self, path, positions):
        data = {
            'title': path.title,
            'slug': path.slug,
            'area': path.area,
            'description': path.description,
            'intro_html': path.intro_html,
            'position': path.position,
            'lessons-TOTAL_FORMS': str(len(positions)),
            'lessons-INITIAL_FORMS': str(len(positions)),
            'lessons-MIN_NUM_FORMS': '0',
            'lessons-MAX_NUM_FORMS': '1000',
        }
        for index, (lesson, position) in enumerate(positions):
            data.update(
                {
                    f'lessons-{index}-id': lesson.pk,
                    f'lessons-{index}-path': path.pk,
                    f'lessons-{index}-position': position,
                    f'lessons-{index}-title': lesson.title,
                    f'lessons-{index}-body_html': lesson.body_html,
                    f'lessons-{index}-body': lesson.body,
                }
            )
        return data

    def test_swapping_positions_saves(self):
        path = LearningPath.objects.create(title='Ruta local', area='Transversal', description='d')
        a = Lesson.objects.create(path=path, position=1, title='A', body='a')
        b = Lesson.objects.create(path=path, position=2, title='B', body='b')
        c = Lesson.objects.create(path=path, position=3, title='C', body='c')
        User.objects.create_superuser('raiz', password=PASSWORD)
        self.client.login(username='raiz', password=PASSWORD)
        response = self.client.post(
            f'/admin/hub/learningpath/{path.pk}/change/',
            self.form_data(path, [(a, 3), (b, 1), (c, 2)]),
        )
        self.assertEqual(response.status_code, 302, getattr(response, 'context', None))
        self.assertEqual(
            list(path.lessons.order_by('position').values_list('title', flat=True)),
            ['B', 'C', 'A'],
        )
