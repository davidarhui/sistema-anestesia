"""
===============================================================================
USS Patch Engine
===============================================================================

Motor seguro y reutilizable para aplicar modificaciones al proyecto.

Principios:
    1. Nunca modificar un archivo sin respaldo.
    2. Validar el parche antes de escribir.
    3. Verificar sintaxis antes de sustituir el archivo original.
    4. Escribir de forma atómica siempre que sea posible.
    5. No aplicar dos veces el mismo parche.
    6. Preferir localización estructural para código Python complejo.

===============================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os
import shutil
import tempfile

from tools.backup import BackupManager
from tools.verify import SyntaxVerifier


class PatchError(RuntimeError):
    """Error controlado durante la aplicación de un parche."""


class PatchAlreadyApplied(PatchError):
    """El parche ya se encuentra aplicado."""


class PatchValidationError(PatchError):
    """El archivo objetivo no coincide con lo esperado por el parche."""


@dataclass
class PatchResult:
    """Resultado de una operación de parcheo."""

    patch_id: str
    patch_name: str
    target: Path
    applied: bool
    backup: Optional[Path] = None
    message: str = ""


class Patch(ABC):
    """
    Clase base para todos los parches.

    Cada parche debe definir:

        id
        name
        description
        target_file

    El método transform() puede realizar una transformación textual
    tradicional o utilizar AST Tools + Matcher + Rewriter.
    """

    id: str = ""
    name: str = ""
    description: str = ""
    target_file: str = ""

    def already_applied(self, text: str) -> bool:
        """
        Devuelve True si el parche ya se encuentra aplicado.

        Los parches pueden sobrescribir este método.
        """
        return False

    def validate(self, text: str) -> None:
        """
        Verifica que el archivo sea compatible con el parche.

        Debe lanzar PatchValidationError si no lo es.
        """
        return None

    @abstractmethod
    def transform(self, text: str) -> str:
        """
        Devuelve el contenido completo del archivo después del parche.

        Aunque el parche utilice AST internamente, debe preservar
        el resto del archivo y devolver finalmente un str.
        """
        raise NotImplementedError


class StructuralPatch(Patch):
    """
    Clase base semántica para parches estructurales.

    No cambia el contrato de Patch; simplemente identifica aquellos
    parches que utilizan AST/Matcher/Rewriter para localizar y modificar
    código de forma estructural.
    """

    structural = True


class PatchEngine:
    """Aplica parches de manera segura sobre un proyecto."""

    def __init__(
        self,
        project_root: Path,
        backup_dir: Optional[Path] = None,
    ):
        self.project_root = Path(project_root).resolve()

        if backup_dir is None:
            backup_dir = self.project_root / "backups"

        self.backup_manager = BackupManager(
            Path(backup_dir)
        )

    def _resolve_target(self, patch: Patch) -> Path:
        """Obtiene y valida la ruta del archivo objetivo."""

        if not patch.target_file:
            raise PatchError(
                f"El parche {patch.id!r} no define target_file."
            )

        target = (
            self.project_root / patch.target_file
        ).resolve()

        try:
            target.relative_to(self.project_root)
        except ValueError:
            raise PatchError(
                "El parche intenta modificar un archivo "
                f"fuera del proyecto: {target}"
            )

        if not target.exists():
            raise PatchError(
                f"No existe el archivo objetivo: {target}"
            )

        if not target.is_file():
            raise PatchError(
                f"El objetivo no es un archivo: {target}"
            )

        return target

    def apply(self, patch: Patch) -> PatchResult:
        """
        Aplica un parche siguiendo este flujo:

            leer
              ↓
            detectar si ya está aplicado
              ↓
            validar
              ↓
            transformar EN MEMORIA
              ↓
            verificar que cambió
              ↓
            crear backup
              ↓
            escribir archivo temporal
              ↓
            verificar sintaxis
              ↓
            reemplazo atómico
        """

        target = self._resolve_target(patch)

        original_text = target.read_text(
            encoding="utf-8"
        )

        if patch.already_applied(original_text):
            return PatchResult(
                patch_id=patch.id,
                patch_name=patch.name,
                target=target,
                applied=False,
                message="El parche ya estaba aplicado.",
            )

        # Toda la validación y transformación ocurre
        # ANTES de tocar el archivo real.
        patch.validate(original_text)

        new_text = patch.transform(
            original_text
        )

        if not isinstance(new_text, str):
            raise PatchError(
                f"El parche {patch.id} "
                "no devolvió texto válido."
            )

        if new_text == original_text:
            raise PatchError(
                f"El parche {patch.id} "
                "no produjo ningún cambio."
            )

        backup = self.backup_manager.create_backup(
            target
        )

        temp_path: Optional[Path] = None

        try:
            # El temporal vive en la misma carpeta para que
            # os.replace() pueda realizar un reemplazo atómico.
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".patchtmp",
                delete=False,
            ) as temp_file:

                temp_file.write(new_text)
                temp_file.flush()
                os.fsync(temp_file.fileno())

                temp_path = Path(
                    temp_file.name
                )

            shutil.copystat(
                target,
                temp_path,
            )

            ok, error = (
                SyntaxVerifier.verify_python(
                    temp_path
                )
            )

            if not ok:
                raise PatchError(
                    "La versión modificada no pasó "
                    "la verificación de sintaxis:\n\n"
                    f"{error}"
                )

            os.replace(
                temp_path,
                target,
            )

            temp_path = None

            return PatchResult(
                patch_id=patch.id,
                patch_name=patch.name,
                target=target,
                applied=True,
                backup=backup,
                message=(
                    "Parche aplicado correctamente."
                ),
            )

        except Exception:

            # Normalmente el archivo original permanece intacto
            # hasta os.replace(). Si excepcionalmente el reemplazo
            # ocurrió antes de una falla posterior, restauramos.
            if target.exists():
                try:
                    current_text = target.read_text(
                        encoding="utf-8"
                    )
                except Exception:
                    current_text = None

                if current_text == new_text:
                    self.backup_manager.restore_backup(
                        backup,
                        target,
                    )

            raise

        finally:
            if (
                temp_path is not None
                and temp_path.exists()
            ):
                temp_path.unlink()
