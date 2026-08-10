"""
backup.py
==========

Manejo de respaldos para el Patch Engine.

Responsabilidad:
- Crear un respaldo de un archivo.
- Restaurar un respaldo.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shutil


class BackupManager:
    """Administra respaldos de archivos."""

    def __init__(self, backup_dir: Path):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, target: Path) -> Path:
        """Crea un respaldo del archivo indicado."""

        target = Path(target)

        if not target.exists():
            raise FileNotFoundError(target)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        backup = (
            self.backup_dir
            / f"{target.stem}_{timestamp}{target.suffix}"
        )

        shutil.copy2(target, backup)

        return backup

    def restore_backup(self, backup: Path, target: Path):
        """Restaura un respaldo."""

        shutil.copy2(backup, target)