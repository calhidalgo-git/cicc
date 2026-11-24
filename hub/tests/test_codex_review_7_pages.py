"""T12: séptima revisión de Codex (24-11-2026). Un .md con la firma UTF-8 de Windows."""

from django.test import TestCase

from ..services.pages import parse_page_file
from .temp import temp_folder


class MarkdownWithUtf8Signature(TestCase):
    def test_the_title_is_read_with_and_without_the_signature(self):
        text = '# Mi glosario\n\nIntroducción.\n\n## Bloque\n\nTexto.\n'
        folder = temp_folder(self)
        for name, data in (
            ('con.md', b'\xef\xbb\xbf' + text.encode('utf-8')),
            ('sin.md', text.encode('utf-8')),
        ):
            path = folder / name
            path.write_bytes(data)
            content = parse_page_file(path)
            self.assertEqual(content['title'], 'Mi glosario', name)
            self.assertNotIn('# Mi glosario', content['intro_html'], name)
            self.assertEqual([block['title'] for block in content['blocks']], ['Bloque'], name)
