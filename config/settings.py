import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from config.env import env_bool, env_list, env_required, load_env_file

BASE_DIR = Path(__file__).resolve().parent.parent

# Un archivo .env en la raíz, si existe, completa las variables que no estén ya definidas.
# CICC_ENV_FILE indica otra ruta; vacía, no se lee ningún archivo (lo usan las pruebas).
_ENV_FILE = os.environ.get('CICC_ENV_FILE')
if _ENV_FILE is None:
    load_env_file(BASE_DIR / '.env')
elif _ENV_FILE.strip():
    load_env_file(_ENV_FILE.strip())

# Modo local de demostración: SQLite, DEBUG activo por defecto y clave de desarrollo permitida.
# Sin esta variable la aplicación arranca en modo producción y exige su configuración.
CICC_DEMO = env_bool('CICC_DEMO', False)

# DEBUG solo se activa con DEBUG=1. En modo demo vale 1 salvo que se indique DEBUG=0.
DEBUG = env_bool('DEBUG', CICC_DEMO)

_DEV_SECRET = 'local-demo-only-not-for-production'
# Claves que ya se distribuyeron con el repositorio. Nadie debe poder arrancar producción con ellas.
# Las pruebas y la integración continua generan una clave aleatoria en cada ejecución.
_PUBLIC_SECRETS = {
    # Clave de la demo.
    _DEV_SECRET,
    # La que tenía esta configuración antes de T02.
    'local-prototype-only-change-before-deployment',
    # Ejemplo del README anterior a T02 (T01, README.md, línea 25).
    'reemplazar-con-un-secreto-aleatorio',
    # Texto de ejemplo habitual.
    'genera-una-clave-aleatoria',
    # Clave fija que usaban las pruebas de configuración de T02.
    'clave-ficticia-de-prueba-' + 'x' * 40,
    # Clave fija que usaba el flujo de integración continua de T03.
    'clave-ficticia-solo-para-la-integracion-continua-0123456789',
}
if CICC_DEMO:
    SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '').strip() or _DEV_SECRET
    ALLOWED_HOSTS = env_list('CICC_ALLOWED_HOSTS', ['localhost', '127.0.0.1', 'testserver'])
else:
    SECRET_KEY = env_required('DJANGO_SECRET_KEY')
    if SECRET_KEY.strip() in _PUBLIC_SECRETS:
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY tiene una clave de desarrollo o de ejemplo publicada en el '
            'repositorio. En producción define una clave aleatoria propia.'
        )
    # Se valida la lista ya separada: un valor como " , , " no deja ningún host.
    ALLOWED_HOSTS = env_list('CICC_ALLOWED_HOSTS')
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            'Falta la variable de entorno obligatoria CICC_ALLOWED_HOSTS (o no contiene ningún '
            'host). Indica los hosts separados por comas, por ejemplo cicc.ejemplo.local.'
        )

CSRF_TRUSTED_ORIGINS = env_list('CICC_CSRF_TRUSTED_ORIGINS')

# Se sirve por HTTPS (normalmente detrás de un proxy inverso que termina el certificado).
CICC_HTTPS = env_bool('CICC_HTTPS', False)

# Clave Fernet que cifra credenciales y adjuntos del contenido importado (hub/services/crypto.py).
# Va en .env, nunca en el repositorio. Sin ella el contenido cifrado no se puede leer.
CICC_DATA_KEY = os.environ.get('CICC_DATA_KEY', '').strip()

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'hub',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'hub.context_processors.cicc',
            ]
        },
    }
]

_SQLITE = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'demo.sqlite3'}
if CICC_DEMO:
    DATABASES = {'default': _SQLITE}
else:
    # En producción las variables PG* son obligatorias. QA_SQLITE=1 es un alias histórico que solo
    # cambia el motor a SQLite: no relaja ninguna de las reglas anteriores.
    _POSTGRES = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env_required('PGDATABASE'),
        'USER': env_required('PGUSER'),
        'PASSWORD': env_required('PGPASSWORD'),
        'HOST': env_required('PGHOST'),
        'PORT': os.environ.get('PGPORT', '').strip() or '5432',
    }
    DATABASES = {'default': _SQLITE if env_bool('QA_SQLITE', False) else _POSTGRES}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 10},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'private_storage'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Lima'
USE_TZ = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
X_FRAME_OPTIONS = 'DENY'

if CICC_HTTPS:
    # Cookies solo por HTTPS, redirección y HSTS. El proxy inverso debe enviar X-Forwarded-Proto.
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
