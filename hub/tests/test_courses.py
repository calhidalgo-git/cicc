"""T05: cursos como rutas de aprendizaje (paso 10 de la ficha)."""

import json
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from ..models import LearningPath, Lesson, Progress, Resource
from ..services.courses import COURSES_DIR, html_to_text, read_courses, sanitize_html

PASSWORD = 'DemoQA!2026'
EXPECTED = {'fundamentos-qa': 6, 'qa-avanzado': 11, 'certificacion-requerimiento': 6}


def load(**options):
    call_command('load_courses', stdout=StringIO(), **options)


class CoursesBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', stdout=StringIO())

    def login(self, name='ana'):
        self.assertTrue(self.client.login(username=name, password=PASSWORD))


class ContentFiles(CoursesBase):
    def test_counts_per_course(self):
        counts = {slug: Lesson.objects.filter(path__slug=slug).count() for slug in EXPECTED}
        self.assertEqual(counts, EXPECTED)

    def test_each_lesson_text_matches_its_original_file(self):
        for course in read_courses():
            path = LearningPath.objects.get(slug=course['slug'])
            self.assertEqual(path.title, course['title'])
            self.assertEqual(path.area, 'Transversal')
            intro = (course['dir'] / 'intro.html').read_text(encoding='utf-8')
            self.assertEqual(html_to_text(path.intro_html), html_to_text(intro))
            for item in course['lessons']:
                lesson = path.lessons.get(position=item['position'])
                original = (course['dir'] / item['file']).read_text(encoding='utf-8')
                self.assertEqual(lesson.title, item['title'])
                self.assertEqual(lesson.body, html_to_text(original), item['file'])
                self.assertTrue(lesson.body)

    def test_content_files_lose_nothing_when_sanitized(self):
        for file in COURSES_DIR.rglob('*.html'):
            original = file.read_text(encoding='utf-8')
            self.assertEqual(html_to_text(sanitize_html(original)), html_to_text(original), file)

    def test_course_definitions_use_the_agreed_slugs(self):
        slugs = [
            json.loads(f.read_text(encoding='utf-8'))['slug']
            for f in sorted(COURSES_DIR.glob('*/course.json'))
        ]
        self.assertEqual(sorted(slugs), sorted(EXPECTED))


class LoadCourses(CoursesBase):
    def test_loading_twice_does_not_duplicate(self):
        before = (LearningPath.objects.count(), Lesson.objects.count())
        load()
        load()
        self.assertEqual((LearningPath.objects.count(), Lesson.objects.count()), before)

    def test_manual_edit_survives_and_force_overwrites_it(self):
        lesson = Lesson.objects.get(path__slug='qa-avanzado', position=3)
        original_title, original_body = lesson.title, lesson.body
        lesson.title = 'Editada a mano'
        lesson.body_html = '<p>Texto editado</p>'
        lesson.save()
        path = lesson.path
        path.description = 'Descripción editada'
        path.save()
        load()
        lesson.refresh_from_db()
        path.refresh_from_db()
        self.assertEqual(lesson.title, 'Editada a mano')
        self.assertEqual(lesson.body, 'Texto editado')
        self.assertEqual(path.description, 'Descripción editada')
        load(force=True)
        lesson.refresh_from_db()
        path.refresh_from_db()
        self.assertEqual(lesson.title, original_title)
        self.assertEqual(lesson.body, original_body)
        self.assertNotEqual(path.description, 'Descripción editada')

    def test_missing_lessons_are_created_without_touching_the_rest(self):
        path = LearningPath.objects.get(slug='fundamentos-qa')
        path.lessons.filter(position=4).delete()
        keep = path.lessons.get(position=1)
        keep.title = 'Conservada'
        keep.save()
        load()
        self.assertEqual(path.lessons.count(), 6)
        self.assertEqual(path.lessons.get(position=1).title, 'Conservada')


class Sanitizing(CoursesBase):
    def test_script_and_event_attributes_are_removed(self):
        dirty = '<script>alert(1)</script><p onclick="x">hola</p>'
        self.assertEqual(sanitize_html(dirty), '<p>hola</p>')
        path = LearningPath.objects.get(slug='fundamentos-qa')
        lesson = Lesson.objects.create(path=path, position=99, title='Prueba', body_html=dirty)
        lesson.refresh_from_db()
        self.assertEqual(lesson.body_html, '<p>hola</p>')
        self.assertEqual(lesson.body, 'hola')
        path.intro_html = dirty
        path.save()
        path.refresh_from_db()
        self.assertEqual(path.intro_html, '<p>hola</p>')

    def test_links_keep_only_allowed_schemes(self):
        cleaned = sanitize_html(
            '<a href="javascript:alert(1)" title="t">a</a><a href="https://ejemplo.local/">b</a>'
        )
        self.assertNotIn('javascript', cleaned)
        self.assertIn('href="https://ejemplo.local/"', cleaned)
        self.assertNotIn('<img', sanitize_html('<img src="x" onerror="alert(1)">'))

    def test_new_paths_get_a_unique_slug(self):
        first = LearningPath.objects.create(title='Ruta nueva', area='Transversal', description='d')
        second = LearningPath.objects.create(
            title='Ruta nueva', area='Transversal', description='d'
        )
        self.assertEqual(first.slug, 'ruta-nueva')
        self.assertEqual(second.slug, 'ruta-nueva-2')


class CoursePages(CoursesBase):
    def test_path_page_shows_intro_lessons_and_progress(self):
        self.login()
        response = self.client.get('/rutas/fundamentos-qa/')
        self.assertContains(response, 'Objetivos generales')
        self.assertContains(response, 'Semana 6 – Tendencias y futuro del QA')
        self.assertContains(response, '0 de 6 lecciones completadas · 0%')

    def test_completing_a_course_lesson_creates_progress_and_raises_the_percentage(self):
        self.login()
        ana = User.objects.get(username='ana')
        lesson = Lesson.objects.get(path__slug='fundamentos-qa', position=1)
        page = self.client.get('/rutas/fundamentos-qa/1/')
        self.assertContains(page, 'QA asegura la calidad')
        self.assertContains(page, 'Marcar como completada')
        response = self.client.post(f'/lesson/{lesson.pk}/complete/')
        self.assertEqual(response['Location'], '/rutas/fundamentos-qa/1/')
        self.assertTrue(Progress.objects.filter(user=ana, lesson=lesson).exists())
        self.assertContains(self.client.get('/rutas/fundamentos-qa/1/'), 'Lección completada')
        self.assertContains(
            self.client.get('/rutas/fundamentos-qa/'), '1 de 6 lecciones completadas · 17%'
        )

    def test_external_next_is_ignored(self):
        self.login()
        lesson = Lesson.objects.get(path__slug='qa-avanzado', position=2)
        for target in ('https://evil.example/', '//evil.example/x', 'javascript:alert(1)'):
            response = self.client.post(f'/lesson/{lesson.pk}/complete/', {'next': target})
            self.assertEqual(response['Location'], '/rutas/qa-avanzado/2/', target)
        response = self.client.post(f'/lesson/{lesson.pk}/complete/', {'next': '/p/paths/'})
        self.assertEqual(response['Location'], '/p/paths/')

    def test_lesson_navigation(self):
        self.login()
        middle = self.client.get('/rutas/fundamentos-qa/2/')
        self.assertContains(middle, 'rel="prev"')
        self.assertContains(middle, 'rel="next"')
        self.assertNotContains(self.client.get('/rutas/fundamentos-qa/1/'), 'rel="prev"')
        self.assertNotContains(self.client.get('/rutas/fundamentos-qa/6/'), 'rel="next"')
        self.assertEqual(self.client.get('/rutas/fundamentos-qa/7/').status_code, 404)
        self.assertEqual(self.client.get('/rutas/no-existe/').status_code, 404)

    def test_global_search_finds_a_phrase_only_in_a_course_lesson(self):
        self.login()
        phrase = 'Identificación clara del requerimiento funcional'
        self.assertFalse(Resource.objects.filter(description__icontains=phrase).exists())
        response = self.client.get('/p/search/', {'q': phrase})
        self.assertContains(response, '/rutas/certificacion-requerimiento/1/')

    def test_course_resources_open_their_course(self):
        # Decisión de Carlos (21-11-2026): como antes de T05, estos recursos abren su curso.
        # Ya no se decide por el título sino por el campo learning_path.
        self.login()
        for title, slug in (
            ('Guía de pruebas batch y JCL', 'fundamentos-qa'),
            ('Checklist de pruebas de API REST', 'qa-avanzado'),
            ('Introducción a DB2 para QA', 'certificacion-requerimiento'),
        ):
            resource = Resource.objects.get(title=title)
            self.assertEqual(resource.learning_path.slug, slug)
            response = self.client.get(f'/resource/{resource.pk}/')
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'learning/path.html')
            self.assertEqual(response.context['path'].slug, slug)
            self.assertEqual(resource.display_title, resource.learning_path.title)

    def test_renaming_a_resource_does_not_change_where_it_opens(self):
        self.login()
        resource = Resource.objects.get(title='Guía de pruebas batch y JCL')
        resource.title = 'Otro título'
        resource.save()
        response = self.client.get(f'/resource/{resource.pk}/')
        self.assertEqual(response.context['path'].slug, 'fundamentos-qa')
        other = Resource.objects.filter(learning_path__isnull=True).first()
        response = self.client.get(f'/resource/{other.pk}/')
        self.assertTemplateUsed(response, 'resource.html')

    def test_dashboard_shows_the_course_names_and_the_courses_in_order(self):
        self.login()
        response = self.client.get('/p/dashboard/')
        self.assertContains(response, '<h2>Cursos</h2>', html=True)
        html = response.content.decode()
        positions = [
            html.index(f'href="/rutas/{slug}/"')
            for slug in ('fundamentos-qa', 'qa-avanzado', 'certificacion-requerimiento')
        ]
        self.assertEqual(positions, sorted(positions))
        # «Recién llegados» muestra el nombre del curso en los recursos que lo abren.
        for name in (
            'Fundamentos QA',
            'QA Avanzado y Especialización',
            'Certificación de un Requerimiento de Software',
        ):
            self.assertContains(response, f'<h3>{name}</h3>', html=True)
        self.assertNotContains(response, '<h3>Guía de pruebas batch y JCL</h3>', html=True)

    def test_paths_and_lessons_sections_link_to_the_new_pages(self):
        self.login()
        self.assertContains(self.client.get('/p/paths/'), 'href="/rutas/qa-avanzado/1/"')
        self.assertContains(self.client.get('/p/lessons/'), 'href="/rutas/qa-avanzado/1/"')
