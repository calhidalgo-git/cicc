"""T06: permisos separados (D10), roles sin datos demo (D11) y administrador de Django."""

from io import StringIO

from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings

from ..models import Assessment, Attempt, Audit, LearningPath, Resource
from ..permissions import GATES
from ..services.roles import ROLE_NAMES
from .demo import seed_demo

PASSWORD = 'DemoQA!2026'

# Código esperado de cada sección restringida y de cada descarga, por cuenta demo.
PAGES = {
    'questions': '/p/questions/',
    'reports': '/p/reports/',
    'users': '/p/users/',
    'roles': '/p/roles/',
    'settings': '/p/settings/',
    'audit': '/p/audit/',
    'backups': '/p/backups/',
}
ALLOWED = {
    'ana': set(),
    'diego': set(),
    'lucia': {'questions', 'reports', 'audit', 'report.xlsx'},
    'admin': {*PAGES, 'report.xlsx', 'backup'},
}


def permissions_of(name):
    group = Group.objects.get(name=name)
    return set(group.permissions.values_list('content_type__app_label', 'codename'))


class RolesBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_demo(stdout=StringIO())

    def login(self, name):
        self.assertTrue(self.client.login(username=name, password=PASSWORD))


class AccessMatrix(RolesBase):
    def test_every_role_and_restricted_section(self):
        self.assertEqual(set(GATES), set(PAGES))
        for name, allowed in ALLOWED.items():
            self.login(name)
            for slug, url in PAGES.items():
                wanted = 200 if slug in allowed else 403
                self.assertEqual(self.client.get(url).status_code, wanted, f'{name} {url}')
            wanted = 200 if 'report.xlsx' in allowed else 403
            self.assertEqual(self.client.get('/report.xlsx').status_code, wanted, name)
            wanted = 200 if 'backup' in allowed else 403
            self.assertEqual(self.client.post('/backup/').status_code, wanted, name)
            self.client.logout()

    def test_only_the_administrator_role_downloads_the_backup(self):
        # Una cuenta que no es superusuario y solo tiene el grupo Administrador.
        user = User.objects.create_user('jefa', password=PASSWORD, is_staff=True)
        user.groups.add(Group.objects.get(name='Administrador'))
        self.login('jefa')
        self.assertEqual(self.client.post('/backup/').status_code, 200)
        self.assertEqual(self.client.get('/p/backups/').status_code, 200)

    def test_reports_and_audit_are_separate_permissions(self):
        group = Group.objects.create(name='Solo auditoría')
        group.permissions.add(Permission.objects.get(codename='view_audit'))
        user = User.objects.create_user('auditora', password=PASSWORD)
        user.groups.add(group)
        self.login('auditora')
        self.assertEqual(self.client.get('/p/audit/').status_code, 200)
        self.assertEqual(self.client.get('/p/reports/').status_code, 403)
        self.assertEqual(self.client.get('/report.xlsx').status_code, 403)
        self.assertEqual(self.client.post('/backup/').status_code, 403)


class BootstrapRoles(TestCase):
    def test_creates_the_four_groups_with_the_matrix(self):
        out = StringIO()
        call_command('bootstrap_roles', stdout=out)
        self.assertIn(
            'Roles creados: Participante, Editor, Evaluador, Administrador', out.getvalue()
        )
        self.assertEqual(permissions_of('Participante'), set())
        self.assertEqual(
            {code for _, code in permissions_of('Editor')},
            {
                f'{action}_{model}'
                for model in ('resource', 'resourceversion', 'learningpath', 'lesson')
                for action in ('view', 'add', 'change')
            }
            | {'view_sectionpage', 'change_sectionpage'},
        )
        self.assertEqual(
            {code for _, code in permissions_of('Evaluador')},
            {
                f'{action}_{model}'
                for model in ('question', 'assessment')
                for action in ('view', 'add', 'change')
            }
            | {'view_audit', 'view_reports'},
        )
        self.assertEqual(
            permissions_of('Administrador'),
            set(
                Permission.objects.filter(content_type__app_label__in=['hub', 'auth']).values_list(
                    'content_type__app_label', 'codename'
                )
            ),
        )
        self.assertIn(('hub', 'export_backup'), permissions_of('Administrador'))
        self.assertNotIn('sessions', {app for app, _ in permissions_of('Administrador')})

    def test_running_twice_gives_the_same_permissions_and_no_users(self):
        call_command('bootstrap_roles', stdout=StringIO())
        first = {name: permissions_of(name) for name in ROLE_NAMES}
        out = StringIO()
        call_command('bootstrap_roles', stdout=out)
        self.assertIn('Roles creados: ninguno', out.getvalue())
        self.assertEqual({name: permissions_of(name) for name in ROLE_NAMES}, first)
        self.assertEqual(Group.objects.count(), 4)
        self.assertFalse(User.objects.exists())

    def test_restores_a_changed_role_and_keeps_other_groups(self):
        call_command('bootstrap_roles', stdout=StringIO())
        editor = Group.objects.get(name='Editor')
        editor.permissions.add(Permission.objects.get(codename='export_backup'))
        other = Group.objects.create(name='Consultores')
        other.permissions.add(Permission.objects.get(codename='view_resource'))
        call_command('bootstrap_roles', stdout=StringIO())
        self.assertNotIn(('hub', 'export_backup'), permissions_of('Editor'))
        self.assertEqual(permissions_of('Consultores'), {('hub', 'view_resource')})


@override_settings(CICC_DEMO=False)
class SeedDemoOutsideDemo(TestCase):
    def test_fails_and_writes_nothing(self):
        with self.assertRaisesMessage(CommandError, 'CICC_DEMO=1'):
            call_command('seed_demo', stdout=StringIO())
        self.assertFalse(User.objects.exists())
        self.assertFalse(Group.objects.exists())
        self.assertFalse(Resource.objects.exists())
        self.assertFalse(LearningPath.objects.exists())
        self.assertFalse(Assessment.objects.exists())

    def test_production_setup_without_demo_accounts(self):
        call_command('bootstrap_roles', stdout=StringIO())
        call_command(
            'createsuperuser',
            username='responsable',
            email='responsable@example.com',
            interactive=False,
            stdout=StringIO(),
        )
        self.assertEqual(list(User.objects.values_list('username', flat=True)), ['responsable'])
        self.assertEqual(Group.objects.count(), 4)


class AdminScreens(RolesBase):
    def setUp(self):
        lucia = User.objects.get(username='lucia')
        self.attempt = Attempt.objects.create(
            user=lucia,
            assessment=Assessment.objects.first(),
            deadline='2030-01-01T00:00Z',
            score=50,
        )
        self.audit = Audit.objects.create(user=lucia, action='Acción original')

    def test_evaluator_cannot_change_attempts_or_audit(self):
        self.login('lucia')
        attempt_url = f'/admin/hub/attempt/{self.attempt.pk}/change/'
        self.assertEqual(self.client.get(attempt_url).status_code, 403)
        response = self.client.post(attempt_url, {'score': 100, 'finished': 'on'})
        self.assertEqual(response.status_code, 403)
        audit_url = f'/admin/hub/audit/{self.audit.pk}/change/'
        # Con view_audit la ve, pero solo para leer.
        response = self.client.get(audit_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="_save"')
        response = self.client.post(audit_url, {'action': 'Cambiada'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get('/admin/hub/audit/add/').status_code, 403)
        self.assertEqual(
            self.client.post(
                f'/admin/hub/audit/{self.audit.pk}/delete/', {'post': 'yes'}
            ).status_code,
            403,
        )
        self.attempt.refresh_from_db()
        self.audit.refresh_from_db()
        self.assertEqual(self.attempt.score, 50)
        self.assertEqual(self.audit.action, 'Acción original')

    def test_no_add_or_save_buttons_for_attempts_audit_and_progress(self):
        self.login('admin')
        for model, pk in (('attempt', self.attempt.pk), ('audit', self.audit.pk)):
            changelist = self.client.get(f'/admin/hub/{model}/')
            self.assertEqual(changelist.status_code, 200)
            self.assertNotContains(changelist, f'/admin/hub/{model}/add/')
            change = self.client.get(f'/admin/hub/{model}/{pk}/change/')
            self.assertEqual(change.status_code, 200)
            self.assertNotContains(change, 'name="_save"')
            self.assertNotContains(change, 'name="_continue"')
            self.assertEqual(self.client.get(f'/admin/hub/{model}/add/').status_code, 403)
        self.assertNotContains(self.client.get('/admin/hub/progress/'), '/admin/hub/progress/add/')
        # El superusuario sí puede borrar.
        response = self.client.post(f'/admin/hub/audit/{self.audit.pk}/delete/', {'post': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Audit.objects.filter(pk=self.audit.pk).exists())

    def test_attempt_and_audit_lists_filter_and_search(self):
        self.login('admin')
        response = self.client.get('/admin/hub/audit/', {'q': 'lucia'})
        self.assertContains(response, 'Acción original')
        response = self.client.get('/admin/hub/audit/', {'q': 'nadie-con-este-nombre'})
        self.assertNotContains(response, 'Acción original')
        response = self.client.get('/admin/hub/attempt/', {'q': 'lucia'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['cl'].has_filters)
        self.assertEqual(response.context['cl'].result_count, 1)

    def test_resource_list_has_columns_filters_search_and_versions(self):
        self.login('admin')
        resource = Resource.objects.get(title='Guía de pruebas batch y JCL')
        response = self.client.get('/admin/hub/resource/', {'q': 'JCL'})
        self.assertContains(response, 'Guía de pruebas batch y JCL')
        self.assertEqual(
            list(response.context['cl'].list_display),
            ['action_checkbox', 'title', 'area', 'kind', 'published'],
        )
        response = self.client.get('/admin/hub/resource/', {'area__exact': 'Mainframe'})
        self.assertNotContains(response, 'Checklist de pruebas de API REST')
        response = self.client.get(f'/admin/hub/resource/{resource.pk}/change/')
        self.assertContains(response, 'versions-TOTAL_FORMS')

    def test_question_validation_runs_in_the_assessment_form(self):
        self.login('admin')
        assessment = Assessment.objects.first()
        url = f'/admin/hub/assessment/{assessment.pk}/change/'
        page = self.client.get(url)
        self.assertContains(page, 'questions-TOTAL_FORMS')
        data = {
            'title': assessment.title,
            'area': assessment.area,
            'minutes': assessment.minutes,
            'pass_score': assessment.pass_score,
            'questions-TOTAL_FORMS': '1',
            'questions-INITIAL_FORMS': '0',
            'questions-MIN_NUM_FORMS': '0',
            'questions-MAX_NUM_FORMS': '1000',
            'questions-0-text': 'Pregunta rota',
            'questions-0-options': '["Solo una"]',
            'questions-0-correct': '3',
            'questions-0-explanation': 'x',
        }
        before = assessment.questions.count()
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'al menos dos opciones')
        self.assertEqual(assessment.questions.count(), before)


class DataMigration(TransactionTestCase):
    BEFORE = [('hub', '0009_section_pages_data')]
    AFTER = [('hub', '0011_roles_permissions_data')]

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        self.migrate(executor.loader.graph.leaf_nodes())

    def test_groups_with_view_audit_keep_reports_and_admin_gets_backup(self):
        apps = self.migrate(self.BEFORE)
        OldGroup = apps.get_model('auth', 'Group')
        OldPermission = apps.get_model('auth', 'Permission')
        # Como en una base de T05: los permisos nuevos aún no existen.
        OldPermission.objects.filter(codename__in=['view_reports', 'export_backup']).delete()
        view_audit = OldPermission.objects.get(content_type__app_label='hub', codename='view_audit')
        auditors = OldGroup.objects.create(name='Auditores internos')
        auditors.permissions.add(view_audit)
        evaluators = OldGroup.objects.create(name='Evaluador')
        evaluators.permissions.add(view_audit)
        administrators = OldGroup.objects.create(name='Administrador')
        OldGroup.objects.create(name='Participante')

        self.migrate(self.AFTER)
        self.assertIn(('hub', 'view_reports'), permissions_of('Auditores internos'))
        self.assertIn(('hub', 'view_reports'), permissions_of('Evaluador'))
        self.assertEqual(permissions_of('Administrador'), {('hub', 'export_backup')})
        self.assertEqual(permissions_of('Participante'), set())
        self.assertNotIn(('hub', 'export_backup'), permissions_of('Auditores internos'))
        user = User.objects.create_user('auditor', password=PASSWORD)
        user.groups.add(Group.objects.get(pk=auditors.pk))
        self.assertTrue(self.client.login(username='auditor', password=PASSWORD))
        self.assertEqual(self.client.get('/p/reports/').status_code, 200)
        self.assertEqual(self.client.get('/p/audit/').status_code, 200)
        self.assertEqual(self.client.post('/backup/').status_code, 403)

        # Revertir quita los permisos nuevos y deja los anteriores.
        self.migrate(self.BEFORE)
        self.assertEqual(permissions_of('Auditores internos'), {('hub', 'view_audit')})
        self.assertEqual(permissions_of('Administrador'), set())
        self.assertEqual(administrators.pk, Group.objects.get(name='Administrador').pk)

    def test_fresh_database_without_groups(self):
        self.migrate(self.BEFORE)
        self.migrate(self.AFTER)
        self.assertFalse(Group.objects.exists())
        self.assertTrue(Permission.objects.filter(codename='export_backup').exists())
