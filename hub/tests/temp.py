"""Carpetas temporales de las pruebas, que se borran al terminar cada prueba (séptima revisión de
Codex, 24-11-2026: los respaldos de prueba quedaban en la carpeta temporal del sistema)."""

import shutil
import tempfile
from pathlib import Path


def temp_folder(test, prefix='cicc-'):
    folder = Path(tempfile.mkdtemp(prefix=prefix))
    test.addCleanup(shutil.rmtree, folder, ignore_errors=True)
    return folder
