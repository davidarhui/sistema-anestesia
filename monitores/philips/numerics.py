"""Decodificación de FC, SpO2, PNI, temperatura y FR: pendiente."""


class NumericsDecoder:
    def decode(self, payload: bytes) -> dict[str, float | int | str]:
        raise NotImplementedError("Pendiente de capturar una sesión IntelliVue real.")
