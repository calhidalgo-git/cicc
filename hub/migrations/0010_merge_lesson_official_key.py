"""Une la marca de lección oficial de T05 (0008_lesson_official_key) con las páginas de T12.

Las dos salen de 0007 y no tocan las mismas tablas. Es una migración de unión sin operaciones:
una base con T12 ya aplicada solo añade la 0008 de T05 (24-11-2026).
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('hub', '0008_lesson_official_key'),
        ('hub', '0009_section_pages_data'),
    ]

    operations = []
