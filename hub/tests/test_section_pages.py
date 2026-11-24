"""T12: una página con teoría para cada opción del menú."""

import importlib
import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.core import serializers
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from ..models import LearningPath, Lesson, SectionBlock, SectionPage
from ..permissions import NAV, allowed
from ..services import pages as pages_service
from .demo import seed_demo
from .temp import temp_folder

PASSWORD = 'DemoQA!2026'
DANGEROUS = '<script>alert(1)</script><p onclick="x">hola</p>'
PENDING = 'Contenido pendiente'
EDIT = 'Editar contenido'


def result(slug):
    return f'<p class="theory-result"><a href="/p/{slug}/">'


class SectionPagesBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_demo(stdout=StringIO())

    def login(self, name):
        self.assertTrue(self.client.login(username=name, password=PASSWORD))

    def write_files(self, files):
        """Carpeta temporal con los archivos dados; devuelve su ruta."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        for name, text in files.items():
            Path(directory.name, name).write_text(text, encoding='utf-8')
        return directory.name

    def load(self, files, *args):
        directory = self.write_files(files)
        out = StringIO()
        with mock.patch.object(pages_service, 'PAGES_DIR', Path(directory)):
            call_command('load_pages', *args, stdout=out)
        return out.getvalue()


class EveryMenuEntryHasAPage(SectionPagesBase):
    def test_one_page_per_menu_entry(self):
        slugs = [slug for slug, _, _ in NAV]
        self.assertEqual(sorted(SectionPage.objects.values_list('slug', flat=True)), sorted(slugs))
        self.assertEqual(
            dict(SectionPage.objects.values_list('slug', 'title')),
            {slug: label for slug, label, _ in NAV},
        )

    def test_migration_list_matches_the_menu(self):
        migration = importlib.import_module('hub.migrations.0009_section_pages_data')
        self.assertEqual(migration.MENU, [(slug, label) for slug, label, _ in NAV])

    def test_every_menu_entry_opens_for_a_role_with_access(self):
        for name in ('admin', 'ana', 'diego', 'lucia'):
            self.login(name)
            user = User.objects.get(username=name)
            opened = 0
            for slug, _, _ in NAV:
                if not allowed(user, slug):
                    continue
                response = self.client.get(f'/p/{slug}/')
                self.assertEqual(response.status_code, 200, f'{name} /p/{slug}/')
                self.assertContains(response, PENDING)
                opened += 1
            self.assertGreater(opened, 0)
            self.client.logout()

    def test_admin_opens_all_entries(self):
        self.login('admin')
        for slug, _, _ in NAV:
            self.assertEqual(self.client.get(f'/p/{slug}/').status_code, 200, slug)

    def test_missing_row_still_shows_pending(self):
        SectionPage.objects.filter(slug='glossary').delete()
        self.login('ana')
        self.assertContains(self.client.get('/p/glossary/'), PENDING)

    def test_load_pages_recreates_a_missing_row_without_duplicates(self):
        SectionPage.objects.filter(slug='glossary').delete()
        self.load({})
        self.load({})
        self.assertEqual(SectionPage.objects.filter(slug='glossary').count(), 1)
        self.assertEqual(SectionPage.objects.count(), len(NAV))


class TheoryIsShown(SectionPagesBase):
    def setUp(self):
        self.page = SectionPage.objects.get(slug='library')
        self.page.title = 'Cómo usar la biblioteca'
        self.page.intro_html = '<p>Introducción ficticia de la biblioteca.</p>'
        self.page.save()
        SectionBlock.objects.create(
            page=self.page, position=2, title='Segundo', body_html='<p>B</p>'
        )
        SectionBlock.objects.create(
            page=self.page, position=1, title='Primero', body_html='<p>A</p>'
        )

    def test_page_with_theory_shows_it_above_the_section(self):
        self.login('ana')
        response = self.client.get('/p/library/')
        html = response.content.decode()
        self.assertNotContains(response, PENDING)
        self.assertContains(response, 'Cómo usar la biblioteca')
        self.assertContains(response, '<p>Introducción ficticia de la biblioteca.</p>', html=True)
        # Los bloques van en orden de posición y todo va arriba del contenido de la sección.
        self.assertLess(html.index('Primero'), html.index('Segundo'))
        self.assertLess(html.index('Segundo'), html.index('recursos para seguir creciendo'))
        # Lo que la sección ya mostraba sigue ahí.
        self.assertContains(response, 'Explora, comparte y encuentra la respuesta')

    def test_other_sections_stay_pending(self):
        self.login('ana')
        self.assertContains(self.client.get('/p/videos/'), PENDING)

    def test_edit_link_only_for_editors(self):
        self.login('ana')
        self.assertNotContains(self.client.get('/p/library/'), EDIT)
        self.assertNotContains(self.client.get('/p/videos/'), EDIT)
        self.client.logout()
        for name in ('diego', 'admin'):
            self.login(name)
            response = self.client.get('/p/library/')
            self.assertContains(response, EDIT)
            self.assertContains(response, f'/admin/hub/sectionpage/{self.page.pk}/change/')
            self.assertContains(self.client.get('/p/videos/'), EDIT)
            self.client.logout()
        self.login('lucia')
        self.assertNotContains(self.client.get('/p/library/'), EDIT)


class Sanitizing(SectionPagesBase):
    def test_saving_removes_dangerous_html(self):
        page = SectionPage.objects.get(slug='videos')
        page.intro_html = DANGEROUS
        page.save()
        block = SectionBlock.objects.create(page=page, title='T', body_html=DANGEROUS)
        page.refresh_from_db()
        block.refresh_from_db()
        self.assertEqual(page.intro_html, '<p>hola</p>')
        self.assertEqual(page.intro, 'hola')
        self.assertEqual(block.body_html, '<p>hola</p>')
        self.assertEqual(block.body, 'hola')

    def test_loading_a_file_removes_dangerous_html(self):
        self.load({'links.html': f'{DANGEROUS}<h2>Bloque</h2>{DANGEROUS}<img src=x onerror=y>'})
        page = SectionPage.objects.get(slug='links')
        self.assertEqual(page.intro_html, '<p>hola</p>')
        self.assertEqual(page.blocks.get().body_html, '<p>hola</p>')

    def test_markdown_shows_html_as_text(self):
        self.load({'links.md': '## Bloque\n\n<script>alert(1)</script> texto'})
        body = SectionPage.objects.get(slug='links').blocks.get().body_html
        self.assertNotIn('<script>', body)
        self.assertIn('&lt;script&gt;', body)

    def test_restoring_a_backup_sanitizes_again(self):
        page = SectionPage.objects.get(slug='audit')
        block = SectionBlock.objects.create(page=page, title='T', body_html='<p>x</p>')
        lesson = Lesson.objects.order_by('pk').first()
        path = LearningPath.objects.order_by('pk').first()
        data = json.loads(serializers.serialize('json', [page, block, lesson, path]))
        for item in data:
            for field in ('intro_html', 'body_html'):
                if field in item['fields']:
                    item['fields'][field] = DANGEROUS
        directory = self.write_files({'respaldo.json': json.dumps(data)})
        call_command('loaddata', str(Path(directory, 'respaldo.json')), stdout=StringIO())
        page.refresh_from_db()
        block.refresh_from_db()
        lesson.refresh_from_db()
        path.refresh_from_db()
        self.assertEqual(page.intro_html, '<p>hola</p>')
        self.assertEqual(block.body_html, '<p>hola</p>')
        self.assertEqual(block.body, 'hola')
        self.assertEqual(lesson.body_html, '<p>hola</p>')
        self.assertEqual(lesson.body, 'hola')
        self.assertEqual(path.intro_html, '<p>hola</p>')

    def test_backup_includes_the_new_tables(self):
        SectionBlock.objects.create(
            page=SectionPage.objects.get(slug='audit'), title='Respaldada', body_html='<p>r</p>'
        )
        self.login('admin')
        data = json.loads(self.client.post('/backup/').content)
        models = {item['model'] for item in data}
        self.assertIn('hub.sectionpage', models)
        self.assertIn('hub.sectionblock', models)


class LoadPages(SectionPagesBase):
    FILES = {
        'glossary.md': (
            '# Glosario de calidad\n\nIntroducción ficticia.\n\n'
            '## Defecto\n\nUn **defecto** es una diferencia.\n\n'
            '## Evidencia\n\n- Captura\n- Registro\n'
        ),
        'README.md': '# No se carga',
        '_borrador.md': '## No se carga',
        'desconocida.md': '## No es del menú',
    }

    def test_loads_title_intro_and_ordered_blocks(self):
        out = self.load(self.FILES)
        page = SectionPage.objects.get(slug='glossary')
        self.assertEqual(page.title, 'Glosario de calidad')
        self.assertEqual(page.intro_html, '<p>Introducción ficticia.</p>')
        self.assertEqual(page.origin, 'file')
        self.assertEqual(
            list(page.blocks.values_list('position', 'title')), [(1, 'Defecto'), (2, 'Evidencia')]
        )
        self.assertIn('<strong>defecto</strong>', page.blocks.get(position=1).body_html)
        self.assertIn('<li>Captura</li>', page.blocks.get(position=2).body_html)
        self.assertIn('desconocida.md', out)
        self.assertEqual(SectionPage.objects.filter(origin='file').count(), 1)

    def test_is_idempotent(self):
        self.load(self.FILES)
        first = SectionPage.objects.get(slug='glossary')
        block_ids = list(first.blocks.values_list('pk', flat=True))
        out = self.load(self.FILES)
        again = SectionPage.objects.get(slug='glossary')
        self.assertIn('cargadas desde archivo: 0', out)
        self.assertEqual(again.updated, first.updated)
        self.assertEqual(list(again.blocks.values_list('pk', flat=True)), block_ids)
        self.assertEqual(SectionBlock.objects.filter(page=again).count(), 2)

    def test_a_changed_file_updates_a_page_loaded_from_file(self):
        self.load(self.FILES)
        self.load({'glossary.md': '## Solo uno\n\nTexto nuevo.'})
        page = SectionPage.objects.get(slug='glossary')
        self.assertEqual(page.title, 'Glosario')
        self.assertEqual(list(page.blocks.values_list('title', flat=True)), ['Solo uno'])

    def test_keeps_admin_edits_unless_forced(self):
        page = SectionPage.objects.get(slug='glossary')
        page.intro_html = '<p>Escrito a mano.</p>'
        page.origin = 'admin'
        page.save()
        out = self.load(self.FILES)
        page.refresh_from_db()
        self.assertEqual(page.intro_html, '<p>Escrito a mano.</p>')
        self.assertIn('se conserva', out)
        self.load(self.FILES, '--force')
        page.refresh_from_db()
        self.assertEqual(page.intro_html, '<p>Introducción ficticia.</p>')
        self.assertEqual(page.origin, 'file')
        self.assertEqual(page.blocks.count(), 2)

    def test_two_files_for_one_section_is_an_error(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            self.load({'glossary.md': '## A', 'glossary.html': '<h2>B</h2>'})

    def test_example_file_in_the_project_parses(self):
        content = pages_service.parse_page_file(pages_service.PAGES_DIR / '_ejemplo.md')
        self.assertTrue(content['title'])
        self.assertEqual(len(content['blocks']), 2)

    def test_seed_demo_runs_load_pages(self):
        SectionPage.objects.all().delete()
        seed_demo(stdout=StringIO())
        self.assertEqual(SectionPage.objects.count(), len(NAV))


class SearchFindsTheory(SectionPagesBase):
    def setUp(self):
        for slug in ('procedures', 'backups'):
            SectionBlock.objects.create(
                page=SectionPage.objects.get(slug=slug),
                title='Bloque',
                body_html=f'<p>Frase solo en teoría zafiro-{slug}.</p>',
            )

    def test_search_finds_a_phrase_from_a_theory_block(self):
        self.login('ana')
        response = self.client.get('/p/search/', {'q': 'zafiro-procedures'})
        self.assertContains(response, result('procedures'))
        self.assertContains(response, 'Procedimientos de certificación')

    def test_search_finds_the_introduction(self):
        page = SectionPage.objects.get(slug='videos')
        page.intro_html = '<p>Introducción con la palabra turmalina.</p>'
        page.save()
        self.login('ana')
        self.assertContains(self.client.get('/p/search/', {'q': 'turmalina'}), result('videos'))

    def test_search_hides_sections_the_person_cannot_open(self):
        self.login('ana')
        response = self.client.get('/p/search/', {'q': 'zafiro-backups'})
        self.assertNotContains(response, result('backups'))
        self.client.logout()
        self.login('admin')
        response = self.client.get('/p/search/', {'q': 'zafiro-backups'})
        self.assertContains(response, result('backups'))

    def test_empty_pages_do_not_match_by_title(self):
        self.login('ana')
        response = self.client.get('/p/search/', {'q': 'Videoteca'})
        self.assertNotContains(response, result('videos'))
        self.assertContains(response, 'Sin teoría coincidente.')


class AdminEditing(SectionPagesBase):
    def change_url(self, page):
        return f'/admin/hub/sectionpage/{page.pk}/change/'

    def form_data(self, page, blocks):
        data = {
            'title': 'Título editado',
            'intro_html': '<p>Intro editada</p><script>x</script>',
            'blocks-TOTAL_FORMS': str(len(blocks)),
            'blocks-INITIAL_FORMS': '0',
            'blocks-MIN_NUM_FORMS': '0',
            'blocks-MAX_NUM_FORMS': '1000',
        }
        for index, (position, title) in enumerate(blocks):
            data[f'blocks-{index}-position'] = str(position)
            data[f'blocks-{index}-title'] = title
            data[f'blocks-{index}-body_html'] = f'<p>{title}</p>'
            data[f'blocks-{index}-page'] = str(page.pk)
        return data

    def test_editor_saves_page_and_inline_blocks(self):
        page = SectionPage.objects.get(slug='lessons')
        self.login('diego')
        self.assertEqual(self.client.get(self.change_url(page)).status_code, 200)
        response = self.client.post(
            self.change_url(page), self.form_data(page, [(2, 'Después'), (1, 'Antes')])
        )
        self.assertEqual(response.status_code, 302, response.content[:2000])
        page.refresh_from_db()
        self.assertEqual(page.title, 'Título editado')
        self.assertEqual(page.intro_html, '<p>Intro editada</p>')
        self.assertEqual(page.origin, 'admin')
        self.assertEqual(page.updated_by.username, 'diego')
        self.assertEqual(list(page.blocks.values_list('title', flat=True)), ['Antes', 'Después'])
        self.client.logout()
        self.login('ana')
        response = self.client.get('/p/lessons/')
        html = response.content.decode()
        self.assertLess(html.index('<h3>Antes</h3>'), html.index('<h3>Después</h3>'))

    def test_staff_without_permission_cannot_edit(self):
        page = SectionPage.objects.get(slug='lessons')
        self.login('lucia')
        self.assertEqual(self.client.get(self.change_url(page)).status_code, 403)
        response = self.client.post(self.change_url(page), self.form_data(page, [(1, 'X')]))
        self.assertEqual(response.status_code, 403)
        page.refresh_from_db()
        self.assertEqual(page.title, 'Mis lecciones')
        self.assertFalse(page.blocks.exists())

    def test_participant_cannot_open_the_admin(self):
        page = SectionPage.objects.get(slug='lessons')
        self.login('ana')
        response = self.client.get(self.change_url(page))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_pages_are_not_added_or_deleted_from_the_admin(self):
        page = SectionPage.objects.get(slug='lessons')
        self.login('admin')
        self.assertEqual(self.client.get('/admin/hub/sectionpage/add/').status_code, 403)
        self.assertEqual(
            self.client.get(f'/admin/hub/sectionpage/{page.pk}/delete/').status_code, 403
        )
        self.assertEqual(self.client.get('/admin/hub/sectionpage/').status_code, 200)


class SectionPageMigrations(TransactionTestCase):
    BEFORE = [('hub', '0007_resource_opens_learning_path')]
    AFTER = [('hub', '0009_section_pages_data')]

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        self.migrate(executor.loader.graph.leaf_nodes())

    def test_forward_backward_and_forward_again(self):
        self.migrate(self.BEFORE)
        self.assertNotIn('hub_sectionpage', connection.introspection.table_names())
        apps = self.migrate(self.AFTER)
        SectionPage = apps.get_model('hub', 'SectionPage')
        self.assertEqual(SectionPage.objects.count(), len(NAV))
        self.migrate(self.BEFORE)
        self.assertNotIn('hub_sectionpage', connection.introspection.table_names())
        apps = self.migrate(self.AFTER)
        self.assertEqual(apps.get_model('hub', 'SectionPage').objects.count(), len(NAV))


class BackupRestoresBySectionSlug(TransactionTestCase):
    """Un respaldo se restaura aunque cambien los números internos de las secciones.

    Revisión de Codex (22-11-2026): tras revertir 0009 y volver a aplicarla, las secciones vacías
    se crean con otros números. El JSON con esos números chocaba, en una instalación recién
    migrada, con la misma sección guardada con otro número.
    """

    PAGES = [('hub', '0009_section_pages_data')]
    NO_PAGES = [('hub', '0008_section_pages')]

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)

    def tearDown(self):
        self.migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def page_numbers(self):
        return dict(SectionPage.objects.values_list('slug', 'pk'))

    def counts(self):
        from ..models import Attempt, Audit, Progress, Resource

        return {
            model.__name__: model.objects.count()
            for model in (Resource, LearningPath, Lesson, Progress, Attempt, Audit)
        }

    def write_theory(self):
        admin = User.objects.get(username='admin')
        environment = SectionPage.objects.get(slug='environment')
        environment.intro_html = '<p>Introducción con la palabra ágata.</p>'
        environment.origin = 'admin'
        environment.updated_by = admin
        environment.save()
        SectionBlock.objects.create(
            page=environment, position=1, title='Primero', body_html='<p>Bloque ónice.</p>'
        )
        SectionBlock.objects.create(
            page=environment, position=2, title='Segundo', body_html='<p>Bloque jaspe.</p>'
        )
        SectionBlock.objects.create(
            page=SectionPage.objects.get(slug='glossary'),
            position=1,
            title='Defecto',
            body_html='<p>Un defecto es una diferencia.</p>',
        )

    def theory(self):
        return {
            page.slug: (
                page.title,
                page.intro_html,
                page.origin,
                page.updated_by.username if page.updated_by else None,
                [(b.position, b.title, b.body_html, b.body) for b in page.blocks.all()],
            )
            for page in SectionPage.objects.select_related('updated_by').prefetch_related('blocks')
        }

    def empty_installation(self):
        """Base recién migrada con las cuentas: sin contenido y con las 26 secciones nuevas."""
        from ..models import (
            Assessment,
            Attempt,
            Audit,
            Progress,
            Question,
            Resource,
            ResourceVersion,
        )

        for model in (
            Audit,
            Attempt,
            Progress,
            Question,
            Assessment,
            SectionBlock,
            SectionPage,
            Lesson,
            LearningPath,
            ResourceVersion,
            Resource,
        ):
            model.objects.all().delete()
        self.migrate(self.NO_PAGES)
        self.migrate(self.PAGES)

    def test_backup_after_reapplying_0009_restores_on_a_fresh_installation(self):
        self.migrate(self.NO_PAGES)
        # T06: la demo usa los permisos de 0010 y 0011, así que se carga con la base al día.
        self.migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
        seed_demo(stdout=StringIO())
        self.write_theory()
        first = self.page_numbers()

        # Revertir y volver a aplicar 0009: las secciones vacías reciben otros números.
        self.migrate(self.NO_PAGES)
        self.migrate(self.PAGES)
        self.migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
        renumbered = self.page_numbers()
        self.assertEqual(set(renumbered), {item[0] for item in NAV})
        self.assertEqual(renumbered['environment'], first['environment'])
        self.assertNotEqual(renumbered['dashboard'], first['dashboard'])

        self.assertTrue(self.client.login(username='admin', password=PASSWORD))
        response = self.client.post('/backup/')
        self.assertEqual(response.status_code, 200)
        backup = json.loads(response.content)
        theory, counts = self.theory(), self.counts()
        pages = [item for item in backup if item['model'] == 'hub.sectionpage']
        self.assertEqual(len(pages), len(NAV))
        self.assertTrue(all('pk' not in item for item in pages))
        blocks = [item for item in backup if item['model'] == 'hub.sectionblock']
        self.assertEqual(
            sorted(item['fields']['page'] for item in blocks),
            [['environment'], ['environment'], ['glossary']],
        )
        self.client.logout()

        self.empty_installation()
        fresh = self.page_numbers()
        self.assertEqual(set(fresh), set(renumbered))
        self.assertTrue(any(fresh[slug] != renumbered[slug] for slug in fresh))
        target = temp_folder(self, prefix='cicc-respaldo-') / 'respaldo.json'
        target.write_text(json.dumps(backup, ensure_ascii=False), encoding='utf-8')
        call_command('loaddata', str(target), stdout=StringIO())

        # Las secciones conservan el número de la instalación nueva y reciben su teoría.
        self.assertEqual(self.page_numbers(), fresh)
        self.assertEqual(self.theory(), theory)
        self.assertEqual(self.counts(), counts)
        self.assertEqual(SectionBlock.objects.count(), 3)
        self.assertTrue(self.client.login(username='admin', password=PASSWORD))
        response = self.client.get('/p/environment/')
        self.assertContains(response, 'Bloque jaspe.')
        response = self.client.get('/p/search/', {'q': 'ónice'})
        self.assertContains(response, result('environment'))

        # Restaurar el mismo respaldo otra vez no duplica nada.
        call_command('loaddata', str(target), stdout=StringIO())
        self.assertEqual(self.page_numbers(), fresh)
        self.assertEqual(self.theory(), theory)
