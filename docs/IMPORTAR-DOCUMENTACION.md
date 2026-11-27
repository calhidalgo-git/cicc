# Importar la documentación del área como cursos

Convierte una carpeta de documentos en Markdown en **rutas de aprendizaje** (cursos) con lecciones, progreso y búsqueda, para que una persona nueva tenga un camino ordenado. Así se cargó la documentación del área en la instalación local.

## Regla de oro: el contenido real no entra al repositorio

El repositorio es público. Los documentos, el manifiesto, la base de datos, `private_storage/` y `.env` quedan **fuera de git**. El código del repositorio solo sabe leerlos.

| Qué | Dónde | ¿En git? |
|---|---|---|
| Documentos `.md` e imágenes | Carpeta local, por ejemplo `Downloads/…-docs-md` | No |
| Manifiesto (cursos, orden, valores a proteger) | `../contenido-bn/manifest.json`, junto al repositorio | No |
| Clave de cifrado `CICC_DATA_KEY` | `.env` | No (`.gitignore`) |
| Lecciones, claves cifradas | Base de datos (`demo.sqlite3` o PostgreSQL) | No |
| Imágenes cifradas | `private_storage/assets/` | No |

## Qué se cifra

- **Contraseñas y claves** se detectan y se sacan del texto:
  - `Clave: valor`, `Password = valor`, `pass: a o b`;
  - `Clave valor` sin dos puntos, si el valor mezcla letras y números;
  - `Contraseña` sola en una línea, con el valor en la siguiente;
  - columnas PASSWORD, CLAVE o CONTRASEÑA en tablas `|` o separadas por tabuladores;
  - los valores exactos de la lista `protect` del manifiesto, para claves sin etiqueta.

  Se guardan cifradas (Fernet) en `Secret`. En la lección queda la marca `⟦secreto:N⟧`, que se ve como un botón 🔒. Solo quien tiene el permiso `hub.view_secret` puede revelarlo, y **cada consulta queda en la auditoría**. Por defecto tienen ese permiso Editor, Evaluador y Administrador. Al Participante se le da desde *Roles y permisos* si hace falta.
- **Imágenes**: todas se guardan cifradas en `private_storage/assets/` y solo se sirven a usuarios con sesión, por `/privado/<sha256>/`. Una captura de pantalla puede mostrar datos sensibles.
- Las direcciones, IP y enlaces internos quedan en claro, porque se necesitan para trabajar.

La detección es por patrones. Después de importar, revisa el resultado (ver «Verificar») y agrega a `protect` cualquier clave que se haya escapado.

**Si pierdes `CICC_DATA_KEY` no se pueden recuperar las claves ni las imágenes.** Guárdala en un lugar seguro, separado del respaldo de la base.

## Pasos

```powershell
cd cicc
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:CICC_DEMO='1'                 # instalación local
python manage.py generate_data_key # una sola vez: escribe CICC_DATA_KEY en .env
python manage.py migrate
python manage.py seed_demo         # solo en demo: usuarios y roles de ejemplo
python manage.py import_docs ..\contenido-bn\manifest.json
python manage.py runserver 127.0.0.1:8000
```

Los cursos aparecen en **Rutas de aprendizaje** (`/p/paths/`), en orden, y su texto se encuentra en la **Búsqueda global**.

Para actualizar el contenido después de cambiar los documentos o el manifiesto:

```powershell
python manage.py import_docs ..\contenido-bn\manifest.json            # solo agrega lo que falta
python manage.py import_docs ..\contenido-bn\manifest.json --update   # reescribe lecciones existentes
```

Sin `--update` no se toca una lección que ya existe, aunque se haya editado en el administrador. Las imágenes y claves repetidas no se duplican. El progreso de las personas se conserva, porque las lecciones se actualizan en su lugar.

## Formato del manifiesto

```json
{
  "source": "C:/ruta/a/los/documentos",
  "exclude": ["README.md"],
  "protect": ["ValorSinEtiqueta1", "OtroValor2"],
  "courses": [
    {
      "slug": "bn-01-induccion",
      "position": 10,
      "area": "Transversal",
      "title": "01 · Inducción",
      "description": "Texto para el listado de rutas.",
      "intro": "Introducción en **Markdown** que se ve al abrir el curso.",
      "items": ["Carpeta/primero.md", "Carpeta", "otro-archivo.md"]
    }
  ]
}
```

- `items`: archivos o carpetas relativos a `source`. Una carpeta aporta sus `.md` en orden natural (sin subcarpetas). Un archivo nombrado antes que su carpeta va primero y no se repite.
- `slug`: único. No puede usar los slugs de los cursos oficiales (`fundamentos-qa`, `qa-avanzado`, `certificacion-requerimiento`).
- `area`: `Mainframe`, `Distribuido` o `Transversal`.
- El título de cada lección es el primer `# Título` del archivo o, si no hay, el nombre del archivo.

## Verificar

```powershell
python manage.py shell -c "from hub.models import *; print(LearningPath.objects.count(), Lesson.objects.count(), Secret.objects.count(), PrivateAsset.objects.count())"
```

Revisa a mano las lecciones con credenciales. Si una clave aparece en claro, agrégala a `protect` y ejecuta `import_docs … --update`.
