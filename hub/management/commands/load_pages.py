from django.core.management.base import BaseCommand, CommandError

from hub.services.pages import PageFileError, load_pages


class Command(BaseCommand):
    help = (
        'Crea una página de teoría por cada opción del menú y carga el contenido de '
        'hub/content/pages/<sección>.md o .html. No toca las páginas editadas en el '
        'administrador, salvo con --force.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Reemplaza también las páginas editadas en el administrador.',
        )

    def handle(self, *args, **options):
        try:
            summary = load_pages(force=options['force'])
        except PageFileError as error:
            raise CommandError(str(error)) from error
        for name in summary['unknown']:
            self.stdout.write(
                self.style.WARNING(f'{name}: no corresponde a ninguna opción del menú; se omite.')
            )
        for slug in summary['kept']:
            self.stdout.write(
                self.style.WARNING(
                    f'{slug}: se conserva la edición hecha en el administrador (usa --force).'
                )
            )
        self.stdout.write(
            self.style.SUCCESS(
                f'Páginas creadas: {summary["created"]}; cargadas desde archivo: '
                f'{summary["loaded"]}; conservadas: {len(summary["kept"])}'
            )
        )
