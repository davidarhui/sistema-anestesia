"""
verify.py
=========

Verificación de archivos modificados por el Patch Engine.
"""

from __future__ import annotations

from pathlib import Path
import subprocess


class SyntaxVerifier:
    """Verifica que un archivo Python tenga sintaxis válida."""

    @staticmethod
    def verify_python(file: Path) -> tuple[bool, str]:
        file = Path(file)

        result = subprocess.run(
            [
                "python3",
                "-m",
                "py_compile",
                str(file),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return True, ""

        return False, result.stderr.strip()