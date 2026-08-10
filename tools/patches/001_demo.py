from tools.patch_engine import Patch, PatchValidationError


class DemoPatch(Patch):
    id = "001"
    name = "Demo Patch Engine"
    description = "Prueba controlada del motor de parches."
    target_file = "demo_patch_target.py"

    ORIGINAL = 'mensaje = "antes"'
    MODIFICADO = 'mensaje = "después"'

    def already_applied(self, text: str) -> bool:
        return self.MODIFICADO in text

    def validate(self, text: str) -> None:
        if self.ORIGINAL not in text:
            raise PatchValidationError(
                "No encontré el contenido esperado en demo_patch_target.py."
            )

    def transform(self, text: str) -> str:
        return text.replace(
            self.ORIGINAL,
            self.MODIFICADO,
            1,
        )


PATCH = DemoPatch()
