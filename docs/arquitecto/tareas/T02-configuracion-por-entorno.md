# T02 — Configuración por entorno

**Depende de:** T01. **Tamaño:** M. **Decisiones:** D2, D3.

## Objetivo

Que la aplicación sea segura por defecto: sin variables de entorno arranca en modo producción y se niega a funcionar con valores inseguros. El modo local se activa con una sola variable, `CICC_DEMO=1`.

## Contexto

Hoy `config/settings.py` tiene `DEBUG` en 1 por defecto, una clave secreta fija de respaldo, `ALLOWED_HOSTS` fijo con `.vercel.app`, ningún validador de contraseña y un bloque final para Vercel que copia la base a `/tmp` y usa sesiones en cookies. El destino es un servidor interno; Vercel se abandona.

## Pasos

1. Crea `config/env.py` con funciones puras y probadas:
   - `load_env_file(path)`: lee líneas `CLAVE=valor` de `.env` (ignora vacías y las que empiezan con `#`, quita comillas envolventes) y las coloca en `os.environ` **sin sobrescribir** variables ya definidas.
   - `env_bool(name, default)`, `env_list(name)` (separa por comas, descarta vacíos) y `env_required(name)` que lanza `ImproperlyConfigured` con un mensaje en español que nombra la variable.
2. Reescribe `config/settings.py` según la tabla de la sección 9 de la arquitectura objetivo:
   - `CICC_DEMO = env_bool('CICC_DEMO', False)`, expuesto como ajuste.
   - Modo demo: SQLite en `demo.sqlite3`, `DEBUG` 1 salvo que se indique `DEBUG=0`, clave de desarrollo permitida, hosts locales.
   - Modo producción: `DJANGO_SECRET_KEY`, `CICC_ALLOWED_HOSTS` y las variables `PG*` obligatorias (`PGPORT` por defecto 5432); `DEBUG` solo con `DEBUG=1` explícito.
   - `QA_SQLITE=1` sigue forzando SQLite en cualquier modo, sin relajar las demás reglas.
   - `CICC_CSRF_TRUSTED_ORIGINS` → `CSRF_TRUSTED_ORIGINS`.
   - `CICC_HTTPS=1` → `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS = 31536000`, `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`.
   - `AUTH_PASSWORD_VALIDATORS`: los cuatro validadores estándar de Django con longitud mínima 10.
   - Elimina por completo el bloque de Vercel y `.vercel.app`.
3. Agrega un procesador de contexto `hub.context_processors.cicc` que entregue `cicc_demo` a las plantillas. En `templates/base.html`, la etiqueta "ENTORNO DEMO" y el texto "Datos ficticios de demostración" del pie se muestran solo si `cicc_demo` es verdadero. No cambies nada más de esa plantilla.
4. Crea `.env.example` con todas las variables, comentadas en español y con valores ficticios.
5. Actualiza `START-DEMO.ps1` para usar `CICC_DEMO=1` en lugar de `QA_SQLITE` y `DEBUG`.
6. Si existe un `vercel.json`, una carpeta `api/` u otro archivo exclusivo de Vercel, elimínalo y anótalo en la bitácora.
7. Pruebas nuevas en `hub/test_config.py`:
   - Unitarias de `config/env.py` (archivo `.env` temporal, no sobrescribe, listas, obligatorias).
   - Con subproceso y entorno limpio: `python manage.py check` **falla** nombrando `DJANGO_SECRET_KEY` cuando no hay variables; **pasa** con `CICC_DEMO=1`; **pasa** con las variables de producción completas y `QA_SQLITE=1`, y en ese caso `DEBUG` es falso.

## Criterios de aceptación

- [ ] En una terminal sin variables, `python manage.py check` termina con error y un mensaje que nombra la variable que falta.
- [ ] `$env:CICC_DEMO='1'; python manage.py test hub` pasa completo.
- [ ] `grep -ri vercel .` (excluyendo `.venv`, `.git` y `docs/arquitecto`) no devuelve nada.
- [ ] Con `CICC_DEMO` sin definir, la interfaz no muestra "ENTORNO DEMO" ni "Datos ficticios".
- [ ] `START-DEMO.ps1` sigue levantando la demo desde cero.
- [ ] `.env` está ignorado por git y `.env.example` está versionado.

## Fuera de alcance

WhiteNoise, Waitress y logs (T09); bloqueo de login y límites de carga (T08); cambios en `seed_demo` (T06).
