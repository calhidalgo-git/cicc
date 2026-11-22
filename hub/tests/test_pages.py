"""Red de seguridad de T04: rutas de cursos, texto distintivo de cada sección y códigos por rol.

Se escribió antes de dividir vistas y plantillas, y pasaba con el código anterior.
"""

from django.core.management import call_command
from django.test import TestCase

from ..catalog import MODULES
from ..models import Resource
from ..views import NAV

PASSWORD = 'DemoQA!2026'

# Portada, número de lecciones y prefijo de cada curso con plantillas propias.
COURSES = [
    ('/qa/fundamentos/', 'semana', 6),
    ('/qa/avanzado/', 'semana', 11),
    ('/qa/certificacion/', 'tema', 6),
]

# Texto que hoy solo aparece en cada sección. Videoteca, enlaces y módulos se comprueban aparte.
SECTION_TEXT = {
    'dashboard': 'Recién llegados a la biblioteca',
    'library': 'Explora, comparte y encuentra la respuesta para tu siguiente desafío.',
    'search': 'Rutas y academia',
    'components': 'Mapa conceptual del ambiente de certificación',
    'paths': 'Abrir ruta',
    'lessons': '/ LECCIÓN 1',
    'assessments': 'Haz visible tu conocimiento.',
    'results': 'Historial de evaluaciones',
    'questions': 'Importar preguntas desde Excel',
    'reports': 'Del conocimiento a la decisión.',
    'users': 'Equipo de calidad',
    'roles': 'Acceso según responsabilidad',
    'settings': 'Configuración de la plataforma',
    'audit': 'Actividad reciente',
    'backups': 'Respaldo del contenido',
}

RESTRICTED = {'questions', 'reports', 'users', 'roles', 'settings', 'audit', 'backups'}

# Secciones restringidas que cada cuenta demo puede abrir (medido antes de T04).
ALLOWED_BY_ROLE = {
    'ana': set(),
    'diego': set(),
    'lucia': {'questions', 'reports', 'audit', 'backups'},
    'admin': RESTRICTED,
}


def course_urls():
    urls, missing = [], []
    for base, segment, total in COURSES:
        urls.append(base)
        urls += [f'{base}{segment}/{n}/' for n in range(1, total + 1)]
        missing += [f'{base}{segment}/{total + 1}/', f'{base}{segment}/0/']
    return urls, missing


class PagesBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo')

    def login(self, name='ana'):
        self.assertTrue(self.client.login(username=name, password=PASSWORD))


class CourseRoutes(PagesBase):
    def test_every_course_page_answers_200_when_logged_in(self):
        self.login()
        urls, _ = course_urls()
        self.assertEqual(len(urls), 3 + 6 + 11 + 6)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_course_pages_redirect_to_login_without_session(self):
        urls, _ = course_urls()
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn('/login/', response['Location'], url)

    def test_number_out_of_range_is_404(self):
        self.login()
        _, missing = course_urls()
        for url in missing:
            self.assertEqual(self.client.get(url).status_code, 404, url)


class SectionContent(PagesBase):
    def test_each_section_shows_its_distinctive_text(self):
        self.login('admin')
        checked = set()
        for slug, text in SECTION_TEXT.items():
            self.assertContains(self.client.get(f'/p/{slug}/'), text, msg_prefix=slug)
            checked.add(slug)
        for slug, kind in (('videos', 'Video'), ('links', 'Enlace')):
            title = Resource.objects.filter(published=True, kind=kind).first().title
            self.assertContains(self.client.get(f'/p/{slug}/'), title, msg_prefix=slug)
            checked.add(slug)
        for slug in MODULES:
            title = Resource.objects.filter(published=True, kind=slug).first().title
            self.assertContains(self.client.get(f'/p/{slug}/'), title, msg_prefix=slug)
            checked.add(slug)
        self.assertEqual(checked, {slug for slug, _, _ in NAV})

    def test_status_codes_by_role(self):
        for name, allowed in ALLOWED_BY_ROLE.items():
            self.login(name)
            for slug, _, _ in NAV:
                wanted = 403 if slug in RESTRICTED - allowed else 200
                self.assertEqual(
                    self.client.get(f'/p/{slug}/').status_code, wanted, f'{name} {slug}'
                )
            self.assertEqual(self.client.get('/p/no-existe/').status_code, 404, name)
            self.client.logout()
        for slug, _, _ in NAV:
            response = self.client.get(f'/p/{slug}/')
            self.assertEqual(response.status_code, 302, f'sin sesión {slug}')
