"""Tercera revisión de Codex (23-11-2026), T12.

- El respaldo no hace una consulta por fila al escribir las claves de páginas, bloques y personas.
- Con las cuentas numeradas de otra forma, la teoría, el avance y los intentos vuelven a su dueño.
"""

import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from ..models import Assessment, Attempt, Lesson, Progress, SectionBlock, SectionPage
from ..views.management import BACKUP_MODELS, backup_json

PASSWORD = 'DemoQA!2026'


class BackupBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', stdout=StringIO())

    def queries(self):
        with CaptureQueriesContext(connection) as captured:
            backup_json()
        return len(captured.captured_queries)


class QueriesDoNotGrowWithRows(BackupBase):
    def test_blocks_and_people_do_not_add_queries(self):
        page = SectionPage.objects.get(slug='glossary')
        page.updated_by = User.objects.get(username='diego')
        page.save()
        before = self.queries()
        for number in range(50):
            SectionBlock.objects.create(page=page, title=f'Bloque {number}', body_html='<p>x</p>')
        ana = User.objects.get(username='ana')
        assessment = Assessment.objects.first()
        for lesson in Lesson.objects.order_by('pk')[:20]:
            Progress.objects.create(user=ana, lesson=lesson)
            Attempt.objects.create(
                user=ana,
                assessment=assessment,
                deadline=timezone.now() + timedelta(minutes=5),
                finished=True,
                score=60,
            )
        self.assertEqual(self.queries(), before)


class RestoreWithAccountsNumberedDifferently(BackupBase):
    def test_theory_progress_and_attempts_keep_their_owner(self):
        ana = User.objects.get(username='ana')
        diego = User.objects.get(username='diego')
        page = SectionPage.objects.get(slug='glossary')
        page.updated_by = diego
        page.save()
        SectionBlock.objects.create(page=page, title='Definición', body_html='<p>QA</p>')
        Progress.objects.create(user=ana, lesson=Lesson.objects.order_by('pk').first())
        Attempt.objects.create(
            user=ana,
            assessment=Assessment.objects.first(),
            deadline=timezone.now() + timedelta(minutes=5),
            finished=True,
            score=75,
        )
        self.client.login(username='admin', password=PASSWORD)
        response = self.client.post('/backup/')
        self.assertEqual(response.status_code, 200)
        backup = Path(tempfile.mkdtemp()) / 'respaldo.json'
        backup.write_bytes(response.content)

        for model in reversed(BACKUP_MODELS):
            model.objects.all().delete()
        old = dict(User.objects.values_list('username', 'pk'))
        User.objects.all().delete()
        names = list(old)
        for username, pk in zip(names, reversed([old[n] for n in names]), strict=True):
            User.objects.create_user(username, password=PASSWORD, pk=pk)
        self.assertNotEqual(User.objects.get(username='ana').pk, old['ana'])

        call_command('loaddata', str(backup), verbosity=0)
        self.assertEqual(Progress.objects.get().user.username, 'ana')
        self.assertEqual(Attempt.objects.get(score=75).user.username, 'ana')
        page = SectionPage.objects.get(slug='glossary')
        self.assertEqual(page.updated_by.username, 'diego')
        self.assertEqual(list(page.blocks.values_list('title', flat=True)), ['Definición'])
        self.client.login(username='ana', password=PASSWORD)
        self.assertContains(self.client.get('/p/glossary/'), 'Definición')
