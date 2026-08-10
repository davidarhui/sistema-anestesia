from __future__ import annotations

from tools.patch_engine import (
    StructuralPatch,
    PatchValidationError,
)

from tools.ast_tools import (
    parse_python,
    find_function,
    find_class,
    find_method,
    NodeNotFoundError,
)

from tools.matcher import (
    find_unique_if,
    MatchNotFoundError,
)

from tools.rewriter import replace_node_code


class ContinuousAcquisitionPatch(StructuralPatch):
    id = "002"
    name = "Continuous Pulse"
    description = (
        "Convierte la primera lectura real del monitor en adquisición "
        "continua por columnas de 5 minutos."
    )

    target_file = "registro_anestesia.py"

    MARKER = "[MX500] Columna"

    OLD_CONDITION = (
        "fc_real is not None "
        "and not self.grafica.datos_sv"
    )

    def already_applied(self, text: str) -> bool:
        return self.MARKER in text

    def _parse(self, text: str):
        return parse_python(
            text,
            self.target_file,
        )

    def _find_target(self, text: str):
        tree = self._parse(text)

        fn = find_function(
            tree,
            "recibir_muestra_monitor",
        )

        try:
            return find_unique_if(
                fn,
                self.OLD_CONDITION,
            )

        except MatchNotFoundError as exc:
            raise PatchValidationError(
                "No encontré la lógica de primera lectura esperada "
                "dentro de recibir_muestra_monitor()."
            ) from exc

    def validate(self, text: str) -> None:
        tree = self._parse(text)

        # ---------------------------------------------------------
        # 1. Debe existir recibir_muestra_monitor()
        #    y el IF antiguo que vamos a sustituir.
        # ---------------------------------------------------------
        self._find_target(text)

        # ---------------------------------------------------------
        # 2. Debe existir GraficaAnestesia.
        # ---------------------------------------------------------
        try:
            find_class(
                tree,
                "GraficaAnestesia",
            )
        except NodeNotFoundError as exc:
            raise PatchValidationError(
                "No encontré la clase GraficaAnestesia."
            ) from exc

        # ---------------------------------------------------------
        # 3. La gráfica debe saber convertir tiempo → minutos.
        # ---------------------------------------------------------
        try:
            find_method(
                tree,
                "GraficaAnestesia",
                "minutos_desde_inicio",
            )
        except NodeNotFoundError as exc:
            raise PatchValidationError(
                "GraficaAnestesia no contiene "
                "minutos_desde_inicio()."
            ) from exc

        # ---------------------------------------------------------
        # 4. Validamos atributos fundamentales existentes.
        #
        # Estos sí deben existir ANTES del parche.
        # ---------------------------------------------------------
        required_fragments = (
            "self.datos_sv",
            "self.columna_actual",
            "self.max_columnas",
            "self.cuadricula_sv",
            "self.hora_base_rejilla",
        )

        missing = [
            item
            for item in required_fragments
            if item not in text
        ]

        if missing:
            raise PatchValidationError(
                "GraficaAnestesia no contiene toda la "
                "infraestructura esperada: "
                + ", ".join(missing)
            )

    def transform(self, text: str) -> str:
        target_if = self._find_target(text)

        replacement = r'''
if fc_real is not None:
    # ---------------------------------------------------------
    # Adquisición continua desde Philips IntelliVue.
    #
    # Mientras permanecemos dentro del mismo intervalo de
    # 5 minutos, actualizamos el mismo registro. Al cambiar
    # de intervalo se crea una nueva columna.
    # ---------------------------------------------------------

    ahora = datetime.now()

    minutos = self.grafica.minutos_desde_inicio(ahora)
    col = max(0, minutos // 5)

    if col >= self.grafica.max_columnas:
        col = self.grafica.max_columnas - 1

    # Buscamos un registro ya existente para esta columna.
    dato_columna = None

    for dato in self.grafica.datos_sv:
        if dato.get("col") == col:
            dato_columna = dato
            break

    accion = "actualizada"

    if dato_columna is None:
        dato_columna = {
            "col": col,
            "fc": None,
            "spo2": None,
            "source": "philips_intellivue",
            "value_source": fuente_fc,
            "captured_at": muestra.get("captured_at"),
        }

        self.grafica.datos_sv.append(
            dato_columna
        )

        accion = "creada"

    # FC real o pulso, según disponibilidad.
    dato_columna["fc"] = float(fc_real)

    # No sustituimos un valor válido por None.
    spo2_real = muestra.get("spo2")

    if spo2_real is not None:
        dato_columna["spo2"] = spo2_real

    dato_columna["source"] = "philips_intellivue"
    dato_columna["value_source"] = fuente_fc
    dato_columna["captured_at"] = muestra.get(
        "captured_at"
    )

    # columna_actual conserva la semántica existente:
    # apunta a la siguiente columna disponible.
    self.grafica.columna_actual = min(
        col + 1,
        self.grafica.max_columnas,
    )

    self.grafica.cuadricula_sv.update()
    self.grafica.update()

    print(
        f"[MX500] Columna {col} {accion}: "
        f"{fuente_fc}={fc_real} lpm | "
        f"SpO2="
        f"{spo2_real if spo2_real is not None else '—'}"
    )
'''

        return replace_node_code(
            text,
            target_if,
            replacement,
        )


PATCH = ContinuousAcquisitionPatch()
