"""T06: correcciones de la cuarta revisión de Codex (24-11-2026).

1. Nadie borra un avance desde el administrador, tampoco un superusuario (decisión de Carlos).
2. Volver de 0011 a 0009 borra los dos permisos del catálogo y sus asignaciones directas.
3. bootstrap_roles se detiene con un mensaje claro si la base no está migrada o si falta uno de
   los dos permisos indispensables del Administrador.
"""

from io import StringIO

from django.contrib import admin
from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import RequestFactory, TestCase, TransactionTestCase

from ..models import Attempt, Audit, Lesson, Progress
from .demo import seed_demo

PASSWORD = 'DemoQA!2026'
NEW = ['view_reports', 'export_backup']


class ProgressCannotBeDeleted(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_demo(stdout=StringIO())
        cls.progress = Progress.objects.create(
            user=User.objects.get(username='ana'), lesson=Lesson.objects.first()
        )
        cls.root = User.objects.create_superuser('raiz', password=PASSWORD)

    def test_superuser_gets_403_and_the_progress_stays(self):
        self.client.force_login(self.root)
        url = f'/admin/hub/progress/{self.progress.pk}/delete/'
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, {'post': 'yes'}).status_code, 403)
        self.assertTrue(Progress.objects.filter(pk=self.progress.pk).exists())

    def test_the_bulk_delete_action_is_not_offered(self):
        self.client.force_login(self.root)
        response = self.client.get('/admin/hub/progress/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'delete_selected')
        response = self.client.post(
            '/admin/hub/progress/',
            {'action': 'delete_selected', '_selected_action': [self.progress.pk], 'post': 'yes'},
        )
        self.assertTrue(Progress.objects.filter(pk=self.progress.pk).exists())

    def test_attempts_and_audit_keep_the_superuser_exception(self):
        request = RequestFactory().get('/admin/')
        request.user = self.root
        for model in (Attempt, Audit):
            self.assertTrue(admin.site._registry[model].has_delete_permission(request), model)
        self.assertFalse(admin.site._registry[Progress].has_delete_permission(request))


class MigrationCase(TransactionTestCase):
    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)

    def latest(self):
        return MigrationExecutor(connection).loader.graph.leaf_nodes()

    def tearDown(self):
        self.migrate(self.latest())


class RevertRemovesTheNewPermissions(MigrationCase):
    def test_catalogue_groups_and_direct_assignments(self):
        seed_demo(stdout=StringIO())
        reports = Permission.objects.get(content_type__app_label='hub', codename='view_reports')
        user = User.objects.create_user('directa', password=PASSWORD)
        user.user_permissions.add(reports)

        for target in ('0010_roles_permissions', '0009_section_pages_data'):
            self.migrate([('hub', '0011_roles_permissions_data')])
            self.migrate([('hub', target)])
            if target.startswith('0009'):
                self.assertFalse(Permission.objects.filter(codename__in=NEW).exists())
            # Ninguna cuenta ni grupo conserva los permisos nuevos.
            self.assertFalse(
                User.user_permissions.through.objects.filter(permission__codename__in=NEW).exists(),
                target,
            )
            self.assertFalse(
                Group.permissions.through.objects.filter(permission__codename__in=NEW).exists(),
                target,
            )

        # Al volver a aplicar, el Administrador recupera la descarga; la cuenta directa no.
        self.migrate(self.latest())
        self.assertTrue(
            Group.objects.get(name='Administrador').permissions.filter(codename='export_backup')
        )
        self.assertFalse(User.objects.get(username='directa').user_permissions.exists())


class BootstrapRolesChecksTheBase(MigrationCase):
    def run_command(self):
        call_command('bootstrap_roles', stdout=StringIO())

    def test_pending_migrations_ask_for_migrate(self):
        self.migrate([('hub', '0010_roles_permissions')])
        with self.assertRaisesMessage(CommandError, 'Ejecuta migrate'):
            self.run_command()

    def test_database_without_tables_asks_for_migrate(self):
        self.migrate([('hub', None), ('auth', None), ('admin', None), ('sessions', None)])
        with self.assertRaisesMessage(CommandError, 'Ejecuta migrate'):
            self.run_command()

    def test_missing_export_backup_is_reported(self):
        Permission.objects.filter(codename='export_backup').delete()
        with self.assertRaisesMessage(CommandError, 'export_backup'):
            self.run_command()
        self.assertFalse(Group.objects.filter(name='Administrador').exists())
