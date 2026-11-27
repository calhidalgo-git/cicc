"""Cifrado de los datos protegidos: credenciales y adjuntos del contenido importado.

La clave vive fuera del repositorio, en la variable ``CICC_DATA_KEY`` (o en ``.env``). Se genera
con ``python manage.py generate_data_key``. Sin esa clave no se puede leer nada de lo cifrado:
respáldala por un canal distinto al de la base de datos.
"""

import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class DataKeyError(ImproperlyConfigured):
    pass


def _key():
    key = getattr(settings, 'CICC_DATA_KEY', '') or ''
    if not key:
        raise DataKeyError(
            'Falta CICC_DATA_KEY. Genérala con «python manage.py generate_data_key» y guárdala '
            'en .env (no se versiona).'
        )
    return key.encode('ascii')


def fernet():
    try:
        return Fernet(_key())
    except ValueError as error:
        raise DataKeyError('CICC_DATA_KEY no es una clave Fernet válida.') from error


def encrypt(data: bytes) -> bytes:
    return fernet().encrypt(data)


def decrypt(token: bytes) -> bytes:
    try:
        return fernet().decrypt(token)
    except InvalidToken as error:
        raise DataKeyError(
            'No se pudo descifrar: la CICC_DATA_KEY actual no es la que cifró estos datos.'
        ) from error


def fingerprint(value: str) -> str:
    """Huella HMAC del valor: identifica un secreto repetido sin guardarlo en claro."""
    return hmac.new(_key(), value.encode('utf-8'), hashlib.sha256).hexdigest()


def new_key() -> str:
    return Fernet.generate_key().decode('ascii')
