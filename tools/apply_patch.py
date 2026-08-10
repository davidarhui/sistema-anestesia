"""
CLI del USS Patch Engine.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Permite ejecutar la CLI tanto como módulo:
#
#   python3 -m tools.apply_patch
#
# como directamente:
#
#   python3 tools/apply_patch.py
#
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from tools.patch_engine import Patch, PatchEngine, PatchError
PATCHES_DIR = PROJECT_ROOT / "tools" / "patches"


def load_patch(patch_id: str) -> Patch:
    matches = sorted(PATCHES_DIR.glob(f"{patch_id}_*.py"))

    if not matches:
        raise PatchError(
            f"No encontré ningún parche con ID {patch_id!r}."
        )

    if len(matches) > 1:
        raise PatchError(
            f"Hay varios parches con ID {patch_id!r}: "
            + ", ".join(p.name for p in matches)
        )

    patch_file = matches[0]

    spec = importlib.util.spec_from_file_location(
        f"uss_patch_{patch_id}",
        patch_file,
    )

    if spec is None or spec.loader is None:
        raise PatchError(
            f"No pude cargar el parche: {patch_file}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    patch = getattr(module, "PATCH", None)

    if patch is None:
        raise PatchError(
            f"{patch_file.name} no define una variable PATCH."
        )

    if not isinstance(patch, Patch):
        raise PatchError(
            f"PATCH en {patch_file.name} no es una instancia de Patch."
        )

    return patch


def list_patches() -> int:
    print()
    print("USS Patch Engine v1.0")
    print("=" * 60)
    print()

    files = sorted(
        p for p in PATCHES_DIR.glob("*.py")
        if p.name != "__init__.py"
    )

    if not files:
        print("No hay parches disponibles.")
        return 0

    print("Parches disponibles:")
    print()

    for file in files:
        patch_id = file.name.split("_", 1)[0]

        try:
            patch = load_patch(patch_id)
            print(f"  {patch.id:<5} {patch.name}")
        except Exception as exc:
            print(f"  {file.name:<30} ERROR: {exc}")

    return 0


def apply_patch(patch_id: str) -> int:
    patch = load_patch(patch_id)

    print()
    print("USS Patch Engine v1.0")
    print("=" * 60)
    print()
    print(f"Patch:       {patch.id}")
    print(f"Nombre:      {patch.name}")
    print(f"Descripción: {patch.description}")
    print()

    engine = PatchEngine(PROJECT_ROOT)

    result = engine.apply(patch)

    if result.applied:
        print("✅ Parche aplicado correctamente.")
        print(f"   Archivo: {result.target}")

        if result.backup:
            print(f"   Backup:  {result.backup}")
    else:
        print(f"ℹ️  {result.message}")

    print()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="USS Patch Engine"
    )

    parser.add_argument(
        "command",
        nargs="?",
        help="ID del parche o 'list'",
    )

    args = parser.parse_args()

    if args.command is None or args.command == "list":
        return list_patches()

    try:
        return apply_patch(args.command)

    except PatchError as exc:
        print()
        print("❌ Patch Engine")
        print(f"   {exc}")
        print()
        return 1

    except Exception as exc:
        print()
        print("❌ Error inesperado")
        print(f"   {type(exc).__name__}: {exc}")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
