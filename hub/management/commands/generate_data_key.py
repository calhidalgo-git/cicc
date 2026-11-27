from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from hub.services.crypto import new_key


class Command(BaseCommand):
    help = (
        'Genera la clave CICC_DATA_KEY que cifra credenciales e imágenes y la agrega a .env. '
        'No reemplaza una clave existente: perderla deja ilegible el contenido cifrado.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--print', action='store_true', help='Solo muestra una clave nueva.')

    def handle(self, *args, **options):
        key = new_key()
        if options['print']:
            self.stdout.write(key)
            return
        if settings.CICC_DATA_KEY:
            self.stdout.write(self.style.WARNING('CICC_DATA_KEY ya está definida; no se cambió.'))
            return
        env = Path(settings.BASE_DIR) / '.env'
        existing = env.read_text(encoding='utf-8-sig') if env.exists() else ''
        if 'CICC_DATA_KEY=' in existing:
            self.stdout.write(self.style.WARNING('.env ya tiene CICC_DATA_KEY; no se cambió.'))
            return
        separator = '' if not existing or existing.endswith('\n') else '\n'
        env.write_text(existing + separator + f'CICC_DATA_KEY={key}\n', encoding='utf-8')
        self.stdout.write(
            self.style.SUCCESS(
                f'Clave guardada en {env}. Haz una copia en un lugar seguro y distinto del '
                'respaldo de la base: sin ella no se pueden leer las claves ni las imágenes.'
            )
        )
