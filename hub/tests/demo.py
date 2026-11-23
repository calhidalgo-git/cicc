"""Datos demo para las pruebas.

Desde T06, ``seed_demo`` solo corre con ``CICC_DEMO=1``. Las pruebas también se ejecutan en modo
producción (PostgreSQL), así que activan el modo demo solo mientras cargan los datos ficticios.
"""

from django.core.management import call_command
from django.test import override_settings


def seed_demo(**options):
    with override_settings(CICC_DEMO=True):
        call_command('seed_demo', **options)
