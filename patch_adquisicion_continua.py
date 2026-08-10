from pathlib import Path

ARCHIVO = Path("registro_anestesia.py")

texto = ARCHIVO.read_text(encoding="utf-8")

viejo = """if (
    fc_real is not None
    and not self.grafica.datos_sv
):"""

nuevo = """if fc_real is not None:"""

if viejo not in texto:
    raise SystemExit(
        "❌ No encontré el bloque esperado. "
        "Probablemente el archivo cambió desde la última revisión."
    )

texto = texto.replace(viejo, nuevo, 1)

ARCHIVO.write_text(texto, encoding="utf-8")

print("✅ Primera parte aplicada correctamente.")