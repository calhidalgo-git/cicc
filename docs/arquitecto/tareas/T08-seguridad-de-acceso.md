# T08 — Seguridad de acceso

**Depende de:** T02, T06. **Tamaño:** M. **Decisiones:** D13, D14.

## Objetivo

Proteger el inicio de sesión, permitir que cada persona cambie su contraseña y limitar lo que se puede subir.

## Contexto

No hay límite de intentos de login. No existe pantalla para cambiar la contraseña: hoy solo puede hacerlo quien tenga acceso al administrador. Los adjuntos de `ResourceVersion` se suben desde el administrador sin límite de tamaño ni de tipo. No hay correo (decisión D13).

## Pasos

1. **Bloqueo de login** con `django-axes`: 5 fallos para la combinación usuario + IP bloquean 15 minutos; un inicio correcto reinicia el contador. Consulta la documentación de la versión que instales para los nombres exactos de los ajustes y anótalos en la bitácora. Página de bloqueo en español con el diseño de `login.html`. Aplica también al login del administrador. Si la aplicación va detrás de un proxy, la IP del cliente se toma de la cabecera del proxy solo cuando `CICC_HTTPS=1` o un ajuste explícito lo indique; documenta el ajuste en `.env.example`.
2. **Cambio de contraseña:** `/cuenta/clave/` con las vistas estándar de Django (`PasswordChangeView` y su confirmación), plantillas propias con el diseño existente y un enlace en la parte inferior de la barra lateral. Aplica los validadores de T02.
3. **Sesión:** `SESSION_COOKIE_AGE` de 12 horas. `CSRF_COOKIE_SAMESITE = 'Lax'`. Verifica que el autoguardado del examen sigue funcionando.
4. **Auditoría de acceso:** registra en `Audit`, mediante las señales de autenticación de Django, inicio de sesión correcto, cierre de sesión, intento fallido (solo el nombre de usuario intentado, truncado; nunca la contraseña) y cambio de contraseña.
5. **Cargas:**
   - `DATA_UPLOAD_MAX_MEMORY_SIZE` y `FILE_UPLOAD_MAX_MEMORY_SIZE` de 5 MB.
   - Validador en `ResourceVersion.file`: máximo 25 MB y extensiones `pdf docx xlsx pptx txt md csv png jpg zip`. Mensajes en español. No valida archivos ya almacenados.
6. **Descargas:** confirma que `download` responde con `Content-Disposition: attachment` y `X-Content-Type-Options: nosniff`; agrega la prueba.
7. **Pruebas:** bloqueo tras 5 fallos y acceso denegado aun con contraseña correcta durante el bloqueo; desbloqueo al vencer el plazo (manipulando el tiempo o el registro, sin `sleep`); cambio de contraseña correcto, con contraseña actual errónea y con contraseña débil; eventos de auditoría creados; rechazo de archivo por tamaño y por extensión; cabeceras de descarga.

## Criterios de aceptación

- [ ] Tras 5 intentos fallidos, el sexto con la contraseña correcta es rechazado y se muestra la página de bloqueo en español.
- [ ] Un participante sin acceso al administrador puede cambiar su contraseña.
- [ ] La auditoría muestra los eventos de acceso y ningún registro contiene contraseñas.
- [ ] Con las variables de producción y `CICC_HTTPS=1`, `python manage.py check --deploy` no muestra advertencias; si queda alguna, está justificada en la bitácora.
- [ ] El examen completo (iniciar, autoguardar, recargar, finalizar) funciona tras los cambios.

## Fuera de alcance

Recuperación de contraseña por correo, SSO, segundo factor, política de caducidad de contraseñas, cabecera Content-Security-Policy (el examen usa un script en línea; queda como observación para una fase posterior), antivirus de adjuntos.
