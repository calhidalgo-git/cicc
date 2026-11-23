"""Lectura de variables de entorno para la configuración de CICC."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def load_env_file(path):
    """Carga líneas CLAVE=valor de un archivo .env sin sobrescribir variables ya definidas.

    Ignora líneas vacías, comentarios (#) y líneas sin '='. Quita comillas envolventes.
    Devuelve la lista de claves que se cargaron.
    """
    path = Path(path)
    if not path.is_file():
        return []
    loaded = []
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        if key.startswith('export '):
            key = key[len('export ') :].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if not key or key in os.environ:
            continue
        os.environ[key] = value
        loaded.append(key)
    return loaded


def env_bool(name, default):
    """Devuelve True solo si la variable vale exactamente 1.

    Sin definir o vacía, devuelve el valor por defecto. Cualquier otro valor cuenta como falso.
    """
    value = os.environ.get(name, '').strip()
    if not value:
        return default
    return value == '1'


def env_list(name, default=None):
    """Separa una variable por comas y descarta los elementos vacíos."""
    value = os.environ.get(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(',') if item.strip()]


def env_required(name):
    """Devuelve el valor de una variable obligatoria o lanza ImproperlyConfigured."""
    value = os.environ.get(name, '').strip()
    if not value:
        raise ImproperlyConfigured(
            f'Falta la variable de entorno obligatoria {name}. '
            'Defínela en el entorno o en el archivo .env (consulta .env.example), '
            'o usa CICC_DEMO=1 para el modo de demostración local.'
        )
    return value
