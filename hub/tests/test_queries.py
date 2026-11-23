"""T04, paso 8: límite de consultas por sección y datos que lee el dashboard de un participante."""

import re
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from ..models import Assessment, Attempt, Lesson, Progress
from ..views import NAV

MAX_QUERIES = 12
PASSWORD = 'DemoQA!2026'
RESTRICTED = {'questions', 'reports', 'users', 'roles', 'settings', 'audit', 'backups'}
ALLOWED_BY_ROLE = {
    'ana': set(),
    'lucia': {'questions', 'reports', 'audit', 'backups'},
    'admin': RESTRICTED,
}


class QueryBudget(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo')
        # Intentos y avance para que las listas también tengan filas.
        now = timezone.now()
        for name in ALLOWED_BY_ROLE:
            user = User.objects.get(username=name)
            for assessment in Assessment.objects.order_by('pk'):
                Attempt.objects.create(
                    user=user,
                    assessment=assessment,
                    deadline=now + timedelta(minutes=5),
                    finished=True,
                    score=80,
                )
            Progress.objects.create(user=user, lesson=Lesson.objects.order_by('pk').first())

    def queries_for(self, url):
        self.client.get(url)  # la primera visita puede guardar la sesión
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        return [query['sql'] for query in captured.captured_queries]

    def test_no_section_exceeds_the_budget(self):
        for name, allowed in ALLOWED_BY_ROLE.items():
            self.client.login(username=name, password=PASSWORD)
            for slug, _, _ in NAV:
                if slug in RESTRICTED - allowed:
                    continue
                for url in (f'/p/{slug}/', f'/p/{slug}/?q=prueba'):
                    count = len(self.queries_for(url))
                    self.assertLessEqual(count, MAX_QUERIES, f'{name} {url}: {count} consultas')
            self.client.logout()

    def test_participant_dashboard_reads_only_its_own_data(self):
        self.client.login(username='ana', password=PASSWORD)
        ana = User.objects.get(username='ana')
        for sql in self.queries_for('/p/dashboard/'):
            tables = {
                name for pair in re.findall(r'FROM "(\w+)"|JOIN "(\w+)"', sql) for name in pair
            }
            self.assertNotIn('hub_audit', tables, sql)
            # Las preguntas solo se cuentan (número real del próximo desafío); nunca se leen.
            self.assertNotIn('FROM "hub_question"', sql)
            if 'hub_question' in tables:
                self.assertIn('COUNT("hub_question"."id")', sql)
            if 'auth_user' in tables or 'auth_group' in tables:
                # Solo el usuario de la sesión, sus grupos y sus permisos; nunca listados.
                self.assertRegex(sql, rf'"(auth_user"\."id|user_id)" = {ana.pk}\b', sql)
