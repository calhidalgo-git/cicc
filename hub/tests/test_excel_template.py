from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import load_workbook

from ..models import Assessment, Question
from .demo import seed_demo


class ExcelTemplate(TestCase):
    """La fila de ejemplo de la plantilla apunta a una evaluación que existe (T03)."""

    @classmethod
    def setUpTestData(cls):
        seed_demo()

    def setUp(self):
        self.client.login(username='lucia', password='DemoQA!2026')

    def template_id(self):
        sheet = load_workbook(BytesIO(self.client.get('/template/').content)).active
        return sheet['A2'].value

    def test_example_row_uses_the_first_existing_assessment(self):
        # Se borra la primera evaluación para que ninguna tenga el ID más bajo esperado.
        first = Assessment.objects.order_by('pk').first()
        Assessment.objects.filter(pk=first.pk).delete()
        expected = Assessment.objects.order_by('pk').first().pk
        self.assertNotEqual(expected, first.pk)
        self.assertEqual(self.template_id(), expected)

    def test_downloaded_template_imports_without_editing(self):
        Assessment.objects.filter(pk=Assessment.objects.order_by('pk').first().pk).delete()
        content = self.client.get('/template/').content
        before = Question.objects.count()
        response = self.client.post('/import/', {'file': SimpleUploadedFile('q.xlsx', content)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Question.objects.count(), before + 1)
