from collections import defaultdict

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPen

# ============================================================
# PATCH 007B — TRIÁNGULO RECTÁNGULO RELLENO, HIPOTENUSA A MITAD INFERIOR
# Cambia SOLO esta constante para probar los cuatro estilos:
#   "letter"  -> sólo inicial
#   "box"     -> inicial dentro de cuadro discreto
#   "circle"  -> inicial dentro de círculo discreto
#   "dot"     -> pequeño punto + inicial
# ============================================================
MEDICATION_MARKER_STYLE = "triangle"

# Escala tipográfica relativa al tamaño del marcador.
# 0.34 deja la letra claramente menor que en 006A/006A.2.
MEDICATION_FONT_SCALE = 0.42
MEDICATION_FONT_MIN_PX = 3
MEDICATION_FONT_MAX_PX = 8


def medication_name_for_letter(graf, letra):
    """Devuelve el nombre visible asociado a la fila A-M."""
    try:
        idx = graf.filas_meds.index(letra)
    except (ValueError, AttributeError):
        return ""

    try:
        return graf.inputs_medicamentos[idx].text().strip()
    except (IndexError, AttributeError):
        return ""


def medication_initial(graf, letra):
    """Inicial clínica del fármaco; cae a la letra A-M si no hay nombre."""
    nombre = medication_name_for_letter(graf, letra)
    for ch in nombre:
        if ch.isalnum():
            return ch.upper()
    return str(letra or "?")[:1].upper()


def _offset_for_duplicate(index, marker_size):
    """Escalona repeticiones en la misma celda sin salir demasiado de ella."""
    if index <= 0:
        return 0.0, 0.0

    step = marker_size * 0.34
    pattern = [
        (step, 0.0),
        (-step, 0.0),
        (0.0, step * 0.52),
        (0.0, -step * 0.52),
        (step, step * 0.52),
        (-step, step * 0.52),
    ]
    return pattern[(index - 1) % len(pattern)]


def _font_px(marker_size, requested_font_size=None):
    """Fuente deliberadamente pequeña; ignora tamaños grandes heredados del 006A."""
    px = marker_size * MEDICATION_FONT_SCALE
    # Si estamos imprimiendo (marcadores grandes), no dejar que la
    # fuente siga creciendo.
    px = min(px, 5.5)
    if requested_font_size is not None:
        try:
            px = min(px, float(requested_font_size))
        except (TypeError, ValueError):
            pass
    return int(max(MEDICATION_FONT_MIN_PX, min(MEDICATION_FONT_MAX_PX, round(px))))


def _draw_marker(painter, rect, initial, marker_size, style):
    """Dibuja una sola marca usando el estilo seleccionado."""
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if style == "letter":
        painter.setPen(QPen(QColor("black"), 0.8))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, initial)
        return

    if style == "triangle":
        # Triángulo rectángulo RELLENO que ocupa la mitad derecha de la celda:
        #   • vértice 1: esquina superior derecha
        #   • vértice 2: esquina inferior derecha
        #   • vértice 3: punto medio de la línea inferior
        # La hipotenusa va de la esquina superior derecha al punto medio
        # de la línea inferior, tal como se definió para el registro.
        from PyQt6.QtGui import QPolygonF
        x_right = rect.right()
        x_mid = rect.left() + rect.width() / 2.0
        y_top = rect.top()
        y_bottom = rect.bottom()
        puntos = QPolygonF([
            QPointF(x_right, y_top),
            QPointF(x_right, y_bottom),
            QPointF(x_mid, y_bottom),
        ])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("black"))
        painter.drawPolygon(puntos)
        return

    if style == "box":
        # Cuadro
        inner = rect.adjusted(
            marker_size * 0.18,
            marker_size * 0.18,
            -marker_size * 0.18,
            -marker_size * 0.18
        )

        painter.setPen(QPen(QColor("black"), max(0.55, marker_size * 0.045)))
        painter.setBrush(QColor("white"))
        painter.drawRect(inner)

        # Letra: tamaño independiente del cuadro
        font = painter.font()
        font.setPixelSize(max(2, int(marker_size * 0.28)))
        painter.setFont(font)

        painter.setPen(QPen(QColor("black"), 0.8))
        painter.drawText(
            inner,
            Qt.AlignmentFlag.AlignCenter,
            initial
        )
        return

    if style == "circle":
        inner = rect.adjusted(marker_size * 0.10, marker_size * 0.10,
                              -marker_size * 0.10, -marker_size * 0.10)
        painter.setPen(QPen(QColor("black"), max(0.55, marker_size * 0.045)))
        painter.setBrush(QColor("white"))
        painter.drawEllipse(inner)
        painter.setPen(QPen(QColor("black"), 0.8))
        painter.drawText(inner, Qt.AlignmentFlag.AlignCenter, initial)
        return

    if style == "dot":
        # Punto pequeño a la izquierda + inicial. Sigue siendo monocromático.
        dot_r = max(1.0, marker_size * 0.075)
        cx = rect.left() + marker_size * 0.20
        cy = rect.center().y()
        painter.setPen(QPen(QColor("black"), 0.6))
        painter.setBrush(QColor("black"))
        painter.drawEllipse(QPointF(cx, cy), dot_r, dot_r)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        text_rect = QRectF(
            rect.left() + marker_size * 0.26,
            rect.top(),
            marker_size * 0.70,
            marker_size,
        )
        painter.setPen(QPen(QColor("black"), 0.8))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, initial)
        return

    # Fallback seguro.
    painter.setPen(QPen(QColor("black"), 0.8))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, initial)


def draw_medication_marks(
    painter,
    graf,
    *,
    x_grid,
    y_sv_top,
    column_width,
    row_height,
    col_inicio=0,
    col_fin=None,
    marker_size=None,
    font_size=None,
    style=None,
):
    """Dibuja administraciones de medicamentos en pantalla o PDF.

    Pantalla y PDF comparten este renderer. Cada marca se conserva en su fila
    A-M y muestra la inicial real del fármaco. Repeticiones en la misma celda
    se escalonan para no ocultarse.
    """
    marcas = getattr(graf, "marcas_medicamentos", []) or []
    if not marcas:
        return

    filas = getattr(graf, "filas_meds", []) or []
    if not filas:
        return

    if col_fin is None:
        col_fin = col_inicio + int(getattr(graf.cuadricula_sv, "num_columnas", 72))

    if marker_size is None:
        marker_size = max(8.0, min(float(row_height) * 0.70, float(column_width) * 0.52))

    style = (style or MEDICATION_MARKER_STYLE).strip().lower()
    font_px = _font_px(marker_size, font_size)

    usados = defaultdict(int)

    painter.save()
    try:
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)
        # Normal, no Bold: reduce el peso visual en la cuadrícula.
        painter.setFont(QFont("Arial", font_px, QFont.Weight.Normal))

        for marca in marcas:
            letra = str(marca.get("letra", ""))
            try:
                fila = filas.index(letra)
            except ValueError:
                continue

            try:
                col_global = int(marca.get("col", 0))
            except (TypeError, ValueError):
                continue

            if col_global < col_inicio or col_global >= col_fin:
                continue

            col_local = col_global - col_inicio
            key = (fila, col_global)
            dup_index = usados[key]
            usados[key] += 1

            dx, dy = _offset_for_duplicate(dup_index, marker_size)

            cx = x_grid + col_local * column_width + column_width / 2.0 + dx
            cy = y_sv_top + fila * row_height + row_height / 2.0 + dy

            half = marker_size / 2.0
            cell_left = x_grid + col_local * column_width
            cell_right = cell_left + column_width
            row_top = y_sv_top + fila * row_height
            row_bottom = row_top + row_height

            if style == "triangle":
                # La geometría del triángulo se define contra los bordes reales
                # de la celda de medicamento, no contra un marcador centrado.
                # Así la hipotenusa parte de la esquina superior derecha y llega
                # exactamente a la mitad de la línea inferior de esa celda.
                # Si hubiera más de una administración en la misma celda, se
                # reduce progresivamente hacia la izquierda para distinguirlas.
                duplicate_shift = dup_index * min(column_width * 0.18, marker_size * 0.30)
                rect_right = cell_right - duplicate_shift
                rect_left = cell_left
                rect = QRectF(rect_left, row_top, rect_right - rect_left, row_height)
            else:
                cx = max(cell_left + half, min(cx, cell_right - half))
                cy = max(row_top + half, min(cy, row_bottom - half))
                rect = QRectF(cx - half, cy - half, marker_size, marker_size)
            _draw_marker(
                painter,
                rect,
                medication_initial(graf, letra),
                marker_size,
                style,
            )
    finally:
        painter.restore()
