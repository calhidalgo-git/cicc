"""Importación de documentación como cursos, con claves e imágenes cifradas. Datos ficticios."""

import json

from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings

from hub.models import Audit, LearningPath, Lesson, PrivateAsset, Secret
from hub.services.courses import sanitize_html
from hub.services.docs_import import ImportErrorDocs, import_docs

from .demo import seed_demo
from .temp import temp_folder

KEY = Fernet.generate_key().decode()
PNG = b'\x89PNG\r\n\x1a\nimagen-ficticia'


def write_docs(test):
    """Carpeta de documentos ficticia y su manifiesto, fuera del repositorio."""
    root = temp_folder(test, 'cicc-docs-')
    docs = root / 'docs'
    (docs / 'Guia' / 'img').mkdir(parents=True)
    (docs / 'Guia' / 'img' / 'pantalla.png').write_bytes(PNG)
    (docs / 'Guia' / '01_Ingreso.md').write_text(
        '---\ndocumento: "x"\n---\n'
        '# Ingreso al ambiente DEMO\n\n'
        '> Fuente original: `docs/x.docx`\n\n'
        'Entrar con usuario demo01 y Clave: Secreta.123\n\n'
        '![](img/pantalla.png)\n\n'
        '<img src="img/pantalla.png" style="width:1in" />\n\n'
        'Clave cert99$Demo para el segundo ambiente. Cambio de clave 35.\n\n'
        'Clave: Solicitar al líder.\n\n'
        '| NOMBRE | ENLACE | PASSWORD |\n|---|---|---|\n'
        '| App | https://demo.invalid | Tabla#2026 |\n\n'
        '> Contraseña\n>\n> SolaEnLinea99\n\n'
        'frase-unica-de-busqueda TOLDDEMO\n',
        encoding='utf-8',
    )
    (docs / 'Guia' / '02_Lista.md').write_text(
        '# Lista\n\n```text\nservidor-demo\nusuariodemo\nSinEtiqueta2026.\n```\n',
        encoding='utf-8',
    )
    manifest = root / 'manifest.json'
    manifest.write_text(
        json.dumps(
            {
                'source': str(docs),
                'protect': ['SinEtiqueta2026.'],
                'courses': [
                    {
                        'slug': 'demo-induccion',
                        'title': 'Inducción DEMO',
                        'area': 'Transversal',
                        'position': 10,
                        'items': ['Guia/02_Lista.md', 'Guia'],
                    }
                ],
            }
        ),
        encoding='utf-8',
    )
    return root, manifest


@override_settings(CICC_DATA_KEY=KEY)
class DocsImportTests(TestCase):
    def setUp(self):
        seed_demo()
        self.root, self.manifest = write_docs(self)
        self.media = temp_folder(self, 'cicc-media-')
        self.settings_media = override_settings(MEDIA_ROOT=self.media)
        self.settings_media.enable()
        self.addCleanup(self.settings_media.disable)
        import_docs(self.manifest)
        self.path = LearningPath.objects.get(slug='demo-induccion')

    def lesson(self, position):
        return self.path.lessons.get(position=position)

    def test_course_and_lessons_in_manifest_order_without_duplicates(self):
        self.assertEqual(
            list(self.path.lessons.values_list('title', flat=True)),
            ['Lista', 'Ingreso al ambiente DEMO'],
        )
        body = self.lesson(2).body_html
        self.assertNotIn('Fuente original', body)
        self.assertNotIn('documento:', body)

    def test_passwords_leave_the_text_and_are_encrypted(self):
        text = ' '.join(lesson.body_html + lesson.body for lesson in Lesson.objects.all())
        for value in [
            'Secreta.123',
            'cert99$Demo',
            'Tabla#2026',
            'SolaEnLinea99',
            'SinEtiqueta2026.',
        ]:
            self.assertNotIn(value, text)
        values = {secret.reveal() for secret in Secret.objects.all()}
        self.assertEqual(
            values,
            {'Secreta.123', 'cert99$Demo', 'Tabla#2026', 'SolaEnLinea99', 'SinEtiqueta2026.'},
        )
        for secret in Secret.objects.all():
            self.assertNotIn(secret.reveal().encode(), bytes(secret.ciphertext))
        # No son claves: se quedan como texto.
        self.assertIn('Cambio de clave 35', text)
        self.assertIn('Solicitar al líder', text)

    def test_images_are_stored_encrypted_once_and_served_only_when_logged_in(self):
        self.assertEqual(PrivateAsset.objects.count(), 1)
        asset = PrivateAsset.objects.get()
        raw = (self.media / asset.file.name).read_bytes()
        self.assertNotIn(b'PNG', raw)
        self.assertEqual(asset.read(), PNG)
        self.assertEqual(self.lesson(2).body_html.count(f'/privado/{asset.key}/'), 2)
        url = f'/privado/{asset.key}/'
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(User.objects.get(username='ana'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(response.content, PNG)

    def test_participant_sees_lock_editor_reveals_and_it_is_audited(self):
        secret = Secret.objects.filter(context__endswith='01_Ingreso').first()
        url = f'/secreto/{secret.pk}/'
        self.client.force_login(User.objects.get(username='ana'))
        page = self.client.get('/rutas/demo-induccion/2/').content.decode()
        self.assertIn('secret-chip locked', page)
        self.assertNotIn('data-secret-url', page)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(User.objects.get(username='diego'))
        page = self.client.get('/rutas/demo-induccion/2/').content.decode()
        self.assertIn('data-secret-url', page)
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['value'], secret.reveal())
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertTrue(
            Audit.objects.filter(action__startswith=f'Consulta dato protegido {secret.pk}').exists()
        )

    def test_reimport_is_idempotent_and_update_rewrites(self):
        lesson = self.lesson(1)
        lesson.body_html = '<p>editada a mano</p>'
        lesson.save()
        counts = (Lesson.objects.count(), Secret.objects.count(), PrivateAsset.objects.count())
        summary = import_docs(self.manifest)
        self.assertEqual(summary['skipped'], 2)
        self.assertEqual(self.lesson(1).body_html, '<p>editada a mano</p>')
        import_docs(self.manifest, update=True)
        self.assertNotIn('editada a mano', self.lesson(1).body_html)
        self.assertEqual(
            counts, (Lesson.objects.count(), Secret.objects.count(), PrivateAsset.objects.count())
        )

    def test_search_finds_imported_text(self):
        self.client.force_login(User.objects.get(username='ana'))
        page = self.client.get('/p/search/', {'q': 'TOLDDEMO'}).content.decode()
        self.assertIn('/rutas/demo-induccion/2/', page)

    def test_command_reports_summary(self):
        call_command(
            'import_docs', str(self.manifest), '--update', stdout=open(self.root / 'out.txt', 'w')
        )
        self.assertIn('Lecciones creadas: 0', (self.root / 'out.txt').read_text())


class DocsImportGuardsTests(TestCase):
    def test_without_key_it_refuses(self):
        _root, manifest = write_docs(self)
        with (
            override_settings(CICC_DATA_KEY=''),
            self.assertRaisesMessage(Exception, 'CICC_DATA_KEY'),
        ):
            import_docs(manifest)
        self.assertFalse(LearningPath.objects.filter(slug='demo-induccion').exists())

    @override_settings(CICC_DATA_KEY=KEY)
    def test_items_outside_the_source_and_official_slugs_are_rejected(self):
        root, manifest = write_docs(self)
        data = json.loads(manifest.read_text(encoding='utf-8'))
        data['courses'][0]['items'] = ['../manifest.json']
        manifest.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesMessage(ImportErrorDocs, 'fuera de la carpeta'):
            import_docs(manifest)
        data['courses'][0]['slug'] = 'fundamentos-qa'
        manifest.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesMessage(ImportErrorDocs, 'reservados'):
            import_docs(manifest)

    def test_sanitizer_keeps_only_private_images(self):
        key = 'a' * 64
        html = sanitize_html(
            f'<img src="/privado/{key}/" alt="x" onerror="y">'
            '<img src="https://externo.invalid/x.png"><img src="/privado/../x/">'
        )
        self.assertIn(f'src="/privado/{key}/"', html)
        self.assertNotIn('onerror', html)
        self.assertNotIn('externo', html)
        self.assertNotIn('../', html)
