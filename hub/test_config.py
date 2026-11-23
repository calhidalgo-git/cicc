"""Pruebas de la configuración por entorno (config/env.py y config/settings.py)."""

import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings

from config.env import env_bool, env_list, env_required, load_env_file

# Variables que influyen en la configuración; los subprocesos arrancan sin ellas.
CONFIG_PREFIXES = ('CICC_', 'DJANGO_', 'PG', 'EMAIL_')
CONFIG_NAMES = {'DEBUG', 'QA_SQLITE', 'SHOW_DEMO_CREDENTIALS', 'DEFAULT_FROM_EMAIL', 'SITE_URL'}

# Claves ya publicadas en el repositorio (README de T01, pruebas de T02 y flujo de CI de T03).
# Producción debe rechazarlas todas.
HISTORICAL_README_SECRET = 'reemplazar-con-un-secreto-aleatorio'
PUBLISHED_TEST_SECRETS = (
    'clave-ficticia-de-prueba-' + 'x' * 40,
    'clave-ficticia-solo-para-la-integracion-continua-0123456789',
)

# La clave de producción de las pruebas se genera en cada ejecución: no queda escrita en ningún
# lugar, así que nadie puede copiarla para arrancar una instalación real.
PRODUCTION = {
    'DJANGO_SECRET_KEY': secrets.token_urlsafe(50),
    'CICC_ALLOWED_HOSTS': 'cicc.ejemplo.local',
    'PGDATABASE': 'cicc',
    'PGUSER': 'cicc_app',
    'PGPASSWORD': 'ficticia',
    'PGHOST': 'localhost',
}

SHOW_SETTINGS = (
    'import django; django.setup(); from django.conf import settings as s; '
    'print(s.DEBUG, s.CICC_DEMO, s.DATABASES["default"]["ENGINE"].rsplit(".", 1)[-1], '
    'getattr(s, "SESSION_COOKIE_SECURE", False), s.SECURE_HSTS_SECONDS, '
    '",".join(s.ALLOWED_HOSTS))'
)

RUN_CHECK = (
    'from django.core.management import execute_from_command_line; '
    'execute_from_command_line(["manage.py", "check"])'
)


def clean_environ(**extra):
    """Entorno sin variables de configuración y sin leer el .env del desarrollador.

    CICC_ENV_FILE vacía hace que los subprocesos ignoren el .env de la raíz, así que las pruebas
    se ejecutan igual con o sin ese archivo. Una prueba puede indicar su propio archivo.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(CONFIG_PREFIXES) and key not in CONFIG_NAMES
    }
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    env['CICC_ENV_FILE'] = ''
    env.update(extra)
    return env


class EnvFile(SimpleTestCase):
    def write(self, text):
        folder = Path(tempfile.mkdtemp(prefix='cicc-env-'))
        path = folder / '.env'
        path.write_text(text, encoding='utf-8')
        return path

    def test_loads_values_and_skips_comments_blank_lines_and_quotes(self):
        path = self.write(
            '# comentario\n'
            '\n'
            'CICC_PRUEBA_A=uno\n'
            'CICC_PRUEBA_B="dos con espacios"\n'
            "CICC_PRUEBA_C='tres'\n"
            'linea sin igual\n'
            'CICC_PRUEBA_D = cuatro=4\n'
        )
        with mock.patch.dict(os.environ, {}):
            loaded = load_env_file(path)
            self.assertEqual(os.environ['CICC_PRUEBA_A'], 'uno')
            self.assertEqual(os.environ['CICC_PRUEBA_B'], 'dos con espacios')
            self.assertEqual(os.environ['CICC_PRUEBA_C'], 'tres')
            self.assertEqual(os.environ['CICC_PRUEBA_D'], 'cuatro=4')
        self.assertEqual(
            loaded,
            ['CICC_PRUEBA_A', 'CICC_PRUEBA_B', 'CICC_PRUEBA_C', 'CICC_PRUEBA_D'],
        )
        self.assertNotIn('CICC_PRUEBA_A', os.environ)

    def test_does_not_overwrite_existing_variables(self):
        path = self.write('CICC_PRUEBA_A=del-archivo\n')
        with mock.patch.dict(os.environ, {'CICC_PRUEBA_A': 'del-sistema'}):
            self.assertEqual(load_env_file(path), [])
            self.assertEqual(os.environ['CICC_PRUEBA_A'], 'del-sistema')

    def test_missing_file_is_ignored(self):
        self.assertEqual(load_env_file(Path(tempfile.mkdtemp()) / 'no-existe.env'), [])


class EnvHelpers(SimpleTestCase):
    def test_bool_only_one_is_true(self):
        with mock.patch.dict(os.environ, {'CICC_PRUEBA': '1'}):
            self.assertTrue(env_bool('CICC_PRUEBA', False))
        for value in ('0', 'no', 'true', 'cualquiera'):
            with mock.patch.dict(os.environ, {'CICC_PRUEBA': value}):
                self.assertFalse(env_bool('CICC_PRUEBA', True), value)

    def test_bool_uses_default_when_missing_or_empty(self):
        with mock.patch.dict(os.environ, {'CICC_PRUEBA': ''}):
            self.assertTrue(env_bool('CICC_PRUEBA', True))
        with mock.patch.dict(os.environ, {}):
            os.environ.pop('CICC_PRUEBA', None)
            self.assertFalse(env_bool('CICC_PRUEBA', False))

    def test_list_splits_by_comma_and_drops_empty_items(self):
        with mock.patch.dict(os.environ, {'CICC_PRUEBA': ' a.local, ,b.local,, '}):
            self.assertEqual(env_list('CICC_PRUEBA'), ['a.local', 'b.local'])
        with mock.patch.dict(os.environ, {}):
            os.environ.pop('CICC_PRUEBA', None)
            self.assertEqual(env_list('CICC_PRUEBA'), [])
            self.assertEqual(env_list('CICC_PRUEBA', ['x']), ['x'])

    def test_required_returns_the_value(self):
        with mock.patch.dict(os.environ, {'CICC_PRUEBA': 'valor'}):
            self.assertEqual(env_required('CICC_PRUEBA'), 'valor')

    def test_required_names_the_missing_variable(self):
        for value in ('', '   '):
            with mock.patch.dict(os.environ, {'CICC_PRUEBA': value}):
                with self.assertRaisesMessage(ImproperlyConfigured, 'CICC_PRUEBA'):
                    env_required('CICC_PRUEBA')
        with mock.patch.dict(os.environ, {}):
            os.environ.pop('CICC_PRUEBA', None)
            with self.assertRaisesMessage(ImproperlyConfigured, 'CICC_PRUEBA'):
                env_required('CICC_PRUEBA')


class SettingsByEnvironment(SimpleTestCase):
    """Arranca la configuración en un subproceso con un entorno limpio.

    Se ejecutan siempre, haya o no un .env en la raíz: los subprocesos no lo leen (CICC_ENV_FILE).
    """

    def run_python(self, code, **env):
        return subprocess.run(
            [sys.executable, '-c', code],
            cwd=settings.BASE_DIR,
            env=clean_environ(**env),
            capture_output=True,
            text=True,
        )

    def settings_with(self, **env):
        result = self.run_python(SHOW_SETTINGS, **env)
        self.assertEqual(result.returncode, 0, result.stderr)
        debug, demo, engine, secure, hsts, hosts = result.stdout.split()
        return {
            'DEBUG': debug == 'True',
            'CICC_DEMO': demo == 'True',
            'ENGINE': engine,
            'SESSION_COOKIE_SECURE': secure == 'True',
            'SECURE_HSTS_SECONDS': int(hsts),
            'ALLOWED_HOSTS': hosts.split(','),
        }

    def test_check_fails_without_variables_and_names_the_secret_key(self):
        result = self.run_python(RUN_CHECK)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DJANGO_SECRET_KEY', result.stderr)

    def test_production_requires_hosts(self):
        result = self.run_python(SHOW_SETTINGS, DJANGO_SECRET_KEY=PRODUCTION['DJANGO_SECRET_KEY'])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('CICC_ALLOWED_HOSTS', result.stderr)

    def test_production_requires_postgres_variables(self):
        env = dict(PRODUCTION)
        del env['PGPASSWORD']
        result = self.run_python(SHOW_SETTINGS, **env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PGPASSWORD', result.stderr)

    def test_check_passes_in_demo_mode(self):
        result = self.run_python(RUN_CHECK, CICC_DEMO='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        values = self.settings_with(CICC_DEMO='1')
        self.assertTrue(values['DEBUG'])
        self.assertTrue(values['CICC_DEMO'])
        self.assertEqual(values['ENGINE'], 'sqlite3')
        self.assertEqual(values['ALLOWED_HOSTS'], ['localhost', '127.0.0.1', 'testserver'])

    def test_demo_mode_can_disable_debug(self):
        self.assertFalse(self.settings_with(CICC_DEMO='1', DEBUG='0')['DEBUG'])

    def test_check_passes_with_full_production_variables_and_sqlite(self):
        result = self.run_python(RUN_CHECK, QA_SQLITE='1', **PRODUCTION)
        self.assertEqual(result.returncode, 0, result.stderr)
        values = self.settings_with(QA_SQLITE='1', **PRODUCTION)
        self.assertFalse(values['DEBUG'])
        self.assertFalse(values['CICC_DEMO'])
        self.assertEqual(values['ENGINE'], 'sqlite3')
        self.assertEqual(values['ALLOWED_HOSTS'], ['cicc.ejemplo.local'])
        self.assertFalse(values['SESSION_COOKIE_SECURE'])

    def test_production_uses_postgres_without_qa_sqlite(self):
        values = self.settings_with(**PRODUCTION)
        self.assertEqual(values['ENGINE'], 'postgresql')
        self.assertFalse(values['DEBUG'])

    def test_qa_sqlite_does_not_relax_the_secret_key(self):
        result = self.run_python(SHOW_SETTINGS, QA_SQLITE='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DJANGO_SECRET_KEY', result.stderr)

    def test_debug_only_with_explicit_one(self):
        self.assertTrue(self.settings_with(DEBUG='1', **PRODUCTION)['DEBUG'])
        self.assertFalse(self.settings_with(DEBUG='true', **PRODUCTION)['DEBUG'])

    def test_https_enables_secure_cookies_and_hsts(self):
        values = self.settings_with(CICC_HTTPS='1', **PRODUCTION)
        self.assertTrue(values['SESSION_COOKIE_SECURE'])
        self.assertEqual(values['SECURE_HSTS_SECONDS'], 31536000)

    def test_trusted_origins_come_from_the_environment(self):
        result = self.run_python(
            'import django; django.setup(); from django.conf import settings as s; '
            'print(",".join(s.CSRF_TRUSTED_ORIGINS))',
            CICC_CSRF_TRUSTED_ORIGINS='https://a.ejemplo.local, https://b.ejemplo.local',
            **PRODUCTION,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'https://a.ejemplo.local,https://b.ejemplo.local')

    def test_production_rejects_the_development_secret_key(self):
        env = dict(PRODUCTION, DJANGO_SECRET_KEY='local-demo-only-not-for-production')
        result = self.run_python(RUN_CHECK, **env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DJANGO_SECRET_KEY', result.stderr)
        self.assertIn('clave de desarrollo', result.stderr)

    def test_production_rejects_the_t01_development_secret_key(self):
        # Quien actualiza desde T01 pudo dejar definida la clave de desarrollo de entonces.
        env = dict(PRODUCTION, DJANGO_SECRET_KEY='local-prototype-only-change-before-deployment')
        for extra in ({}, {'QA_SQLITE': '1'}):
            result = self.run_python(RUN_CHECK, **env, **extra)
            self.assertNotEqual(result.returncode, 0, extra)
            self.assertIn('DJANGO_SECRET_KEY', result.stderr, extra)
            self.assertIn('clave de desarrollo o de ejemplo', result.stderr, extra)

    def test_production_rejects_the_readme_example_secret_key(self):
        env = dict(PRODUCTION, DJANGO_SECRET_KEY='genera-una-clave-aleatoria')
        for extra in ({}, {'QA_SQLITE': '1'}):
            result = self.run_python(RUN_CHECK, **env, **extra)
            self.assertNotEqual(result.returncode, 0, extra)
            self.assertIn('DJANGO_SECRET_KEY', result.stderr, extra)
            self.assertIn('clave de desarrollo o de ejemplo', result.stderr, extra)

    def test_production_rejects_the_exact_example_of_the_old_readme(self):
        # Valor literal que publicaba el README hasta T01 (README.md, línea 25).
        env = dict(PRODUCTION, DJANGO_SECRET_KEY=HISTORICAL_README_SECRET)
        for extra in ({}, {'QA_SQLITE': '1'}):
            result = self.run_python(RUN_CHECK, **env, **extra)
            self.assertNotEqual(result.returncode, 0, extra)
            self.assertIn('DJANGO_SECRET_KEY', result.stderr, extra)
            self.assertIn('clave de desarrollo o de ejemplo', result.stderr, extra)

    def test_production_rejects_the_fixed_keys_of_tests_and_ci(self):
        for key in PUBLISHED_TEST_SECRETS:
            env = dict(PRODUCTION, DJANGO_SECRET_KEY=key)
            for extra in ({}, {'QA_SQLITE': '1'}):
                result = self.run_python(RUN_CHECK, **env, **extra)
                self.assertNotEqual(result.returncode, 0, (key, extra))
                self.assertIn('clave de desarrollo o de ejemplo', result.stderr, (key, extra))

    def test_production_rejects_published_keys_with_surrounding_spaces(self):
        env = dict(PRODUCTION, DJANGO_SECRET_KEY=f'  {HISTORICAL_README_SECRET}  ')
        result = self.run_python(RUN_CHECK, **env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('clave de desarrollo o de ejemplo', result.stderr)

    def test_the_test_secret_key_is_generated_on_each_run(self):
        from config import settings as config_settings

        key = PRODUCTION['DJANGO_SECRET_KEY']
        self.assertNotIn(key, config_settings._PUBLIC_SECRETS)
        self.assertNotIn(key, PUBLISHED_TEST_SECRETS)
        self.assertGreaterEqual(len(key), 50)

    def test_readme_does_not_publish_a_fixed_secret_key(self):
        readme = (Path(settings.BASE_DIR) / 'README.md').read_text(encoding='utf-8')
        self.assertNotIn("DJANGO_SECRET_KEY='", readme)
        self.assertIn('secrets.token_urlsafe', readme)

    def test_demo_mode_still_accepts_the_development_secret_key(self):
        result = self.run_python(RUN_CHECK, CICC_DEMO='1')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_production_rejects_hosts_made_only_of_separators(self):
        for value in (' , , ', ',', '  '):
            env = dict(PRODUCTION, CICC_ALLOWED_HOSTS=value)
            result = self.run_python(RUN_CHECK, **env)
            self.assertNotEqual(result.returncode, 0, repr(value))
            self.assertIn('CICC_ALLOWED_HOSTS', result.stderr, repr(value))

    def test_production_accepts_hosts_with_extra_separators(self):
        env = dict(PRODUCTION, CICC_ALLOWED_HOSTS=' a.ejemplo.local, ,b.ejemplo.local,, ')
        values = self.settings_with(**env)
        self.assertEqual(values['ALLOWED_HOSTS'], ['a.ejemplo.local', 'b.ejemplo.local'])

    def test_qa_sqlite_still_requires_postgres_variables_in_production(self):
        for missing in ('PGDATABASE', 'PGUSER', 'PGPASSWORD', 'PGHOST'):
            env = dict(PRODUCTION, QA_SQLITE='1')
            del env[missing]
            result = self.run_python(RUN_CHECK, **env)
            self.assertNotEqual(result.returncode, 0, missing)
            self.assertIn(missing, result.stderr, missing)
        blank = dict(PRODUCTION, QA_SQLITE='1', CICC_DEMO='0', PGPASSWORD='')
        result = self.run_python(RUN_CHECK, **blank)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PGPASSWORD', result.stderr)

    def test_pgport_is_optional(self):
        self.assertNotIn('PGPORT', PRODUCTION)
        result = self.run_python(
            'import django; django.setup(); from django.conf import settings as s; '
            'print(s.DATABASES["default"]["PORT"])',
            **PRODUCTION,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '5432')

    def test_settings_load_a_real_env_file(self):
        folder = Path(tempfile.mkdtemp(prefix='cicc-envfile-'))
        env_file = folder / '.env'
        env_file.write_text(
            '\n'.join(f'{key}={value}' for key, value in PRODUCTION.items()), encoding='utf-8'
        )
        values = self.settings_with(CICC_ENV_FILE=str(env_file))
        self.assertEqual(values['ENGINE'], 'postgresql')
        self.assertEqual(values['ALLOWED_HOSTS'], ['cicc.ejemplo.local'])

    def test_system_variables_win_over_the_env_file(self):
        folder = Path(tempfile.mkdtemp(prefix='cicc-envfile-'))
        env_file = folder / '.env'
        env_file.write_text(
            '\n'.join(f'{key}={value}' for key, value in PRODUCTION.items()), encoding='utf-8'
        )
        values = self.settings_with(
            CICC_ENV_FILE=str(env_file), CICC_ALLOWED_HOSTS='del-sistema.ejemplo.local'
        )
        self.assertEqual(values['ALLOWED_HOSTS'], ['del-sistema.ejemplo.local'])

    def test_copying_env_example_does_not_start_production(self):
        example = Path(settings.BASE_DIR) / '.env.example'
        result = self.run_python(RUN_CHECK, CICC_ENV_FILE=str(example))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DJANGO_SECRET_KEY', result.stderr)


class PasswordValidators(SimpleTestCase):
    def test_four_standard_validators_with_minimum_length_ten(self):
        names = [item['NAME'].rsplit('.', 1)[-1] for item in settings.AUTH_PASSWORD_VALIDATORS]
        self.assertEqual(
            names,
            [
                'UserAttributeSimilarityValidator',
                'MinimumLengthValidator',
                'CommonPasswordValidator',
                'NumericPasswordValidator',
            ],
        )
        self.assertEqual(settings.AUTH_PASSWORD_VALIDATORS[1]['OPTIONS'], {'min_length': 10})


class DemoLabels(TestCase):
    def setUp(self):
        user = User.objects.create_user('etiquetas', password='clave-ficticia-123')
        self.client.force_login(user)

    @override_settings(CICC_DEMO=True)
    def test_demo_mode_shows_the_labels(self):
        response = self.client.get('/p/dashboard/')
        self.assertContains(response, 'ENTORNO DEMO')
        self.assertContains(response, 'Datos ficticios de demostración')

    @override_settings(CICC_DEMO=False)
    def test_production_hides_the_labels(self):
        response = self.client.get('/p/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'ENTORNO DEMO')
        self.assertNotContains(response, 'Datos ficticios')


class LoginScreen(TestCase):
    """Pantalla de acceso sin sesión: la ayuda de la demo solo aparece con CICC_DEMO."""

    DEMO_HELP = (
        'Demostración:',
        'DemoQA!2026',
        'ana, diego o lucia',
        'Solo datos ficticios',
        'Credenciales exclusivas para uso local',
    )

    @override_settings(CICC_DEMO=False)
    def test_production_login_hides_demo_accounts_and_password(self):
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ingresar a CICC')
        for text in self.DEMO_HELP:
            self.assertNotContains(response, text)

    @override_settings(CICC_DEMO=False)
    def test_production_login_with_error_still_hides_demo_help(self):
        response = self.client.post('/login/', {'username': 'nadie', 'password': 'incorrecta'})
        self.assertContains(response, 'Usuario o contraseña incorrectos.')
        for text in self.DEMO_HELP:
            self.assertNotContains(response, text)

    @override_settings(CICC_DEMO=True)
    def test_demo_login_shows_demo_accounts(self):
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        for text in self.DEMO_HELP:
            self.assertContains(response, text)
