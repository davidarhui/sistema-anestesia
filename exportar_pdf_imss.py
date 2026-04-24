from PyQt6.QtGui import (
    QPainter, QPageSize, QPageLayout, QPen, QFont, QColor, QPolygonF
)
from PyQt6.QtCore import Qt, QRect, QPointF
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import QFileDialog, QMessageBox


def exportar_a_pdf_imss(ventana, ruta_pdf=None, nombre_sugerido="registro_anestesia_imss.pdf"):
    """
    Exporta un PDF estilo IMSS dibujado con QPainter.
    Versión 2: proporciones más cercanas a la hoja clínica.
    """

    if not ruta_pdf:
        ruta_pdf, _ = QFileDialog.getSaveFileName(
            ventana,
            "Guardar PDF",
            nombre_sugerido,
            "PDF Files (*.pdf)"
        )

        if not ruta_pdf:
            return

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(ruta_pdf)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
    printer.setPageOrientation(QPageLayout.Orientation.Portrait)
    printer.setFullPage(False)
    printer.setResolution(300)

    painter = QPainter()
    if not painter.begin(printer):
        QMessageBox.critical(ventana, "Error", "No se pudo iniciar la exportación a PDF.")
        return

    try:
        page_rect = printer.pageLayout().paintRectPixels(printer.resolution())
        dpi = printer.resolution()

        def mm(valor_mm):
            return int(valor_mm * dpi / 25.4)
        
        def clamp(valor, minimo, maximo):
            return max(minimo, min(maximo, valor))

        def pen_scaled(base_mm, ref_mm):
            """
            base_mm: grosor base deseado en mm
            ref_mm: tamaño de referencia del cuadrito o celda en mm/pixels del PDF
            """
            # Ajuste relativo suave
            factor = ref_mm / mm(3.0)   # 3 mm como referencia clínica
            grosor = base_mm * factor
            return clamp(grosor, 0.6, 3.5)

        def valor_a_y(valor, y_top, y_bottom):
            vmin = 40
            vmax = 240
            valor = max(vmin, min(vmax, valor))
            proporcion = (valor - vmin) / (vmax - vmin)
            return y_bottom - proporcion * (y_bottom - y_top)

        def temperatura_a_y(valor, y_top, y_bottom):
            vmin = 34.0
            vmax = 40.0
            valor = max(vmin, min(vmax, valor))
            proporcion = (valor - vmin) / (vmax - vmin)
            return y_bottom - proporcion * (y_bottom - y_top)

        def draw_line_field(x, y, label, valor, label_w, line_w):
            painter.setFont(font_label)
            painter.drawText(x, y, label)

            painter.setFont(font_text)
            painter.drawText(x + label_w, y, str(valor))

            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawLine(x + label_w, y + mm(1.0), x + label_w + line_w, y + mm(1.0))

        def draw_unidad_field(x, y, valor, total_w):
            painter.setFont(font_label)
            painter.drawText(x, y, "Unidad:")

            label_w = mm(14)
            text_x = x + label_w
            text_w = total_w - label_w

            painter.setFont(font_text)

            texto = str(valor)

            # Detectar si ocupa más de una línea (aprox)
            if len(texto) > 35:
                alto_rect = mm(9)
                offset_y = mm(4.0)   # centrado para 2 líneas
            else:
                alto_rect = mm(6)
                offset_y = mm(4.0)   # subir texto de 1 línea

            rect = QRect(text_x, y - offset_y, text_w, alto_rect)

            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                texto
            )

            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawLine(text_x, y + mm(1.0), x + total_w, y + mm(1.0))

        def draw_wrapped_field(x, y, label, valor, x_texto_fijo, total_w):
            painter.setFont(font_label)
            painter.drawText(x, y, label)

            text_x = x_texto_fijo
            text_w = (x + total_w) - text_x

            painter.setFont(font_text)

            texto = str(valor)

            # Detectar texto largo
            if len(texto) > 45:
                alto_rect = mm(9)
                offset_y = mm(4.0)
                linea_y = y + mm(4.5)   # línea baja para 2 líneas
            else:
                alto_rect = mm(6)
                offset_y = mm(4.0)
                linea_y = y + mm(1.0)   # línea normal para 1 línea

            rect = QRect(text_x, y - offset_y, text_w, alto_rect)

            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                texto
            )

            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawLine(text_x, linea_y, x + total_w, linea_y)

            return linea_y

        def draw_ta_marker(x, y, valor=None, up=True):
            # Grosor base según severidad
            if valor is None:
                base = 2.0
            elif valor < 70 or valor > 180:
                base = 2.4
            elif valor < 80 or valor > 160:
                base = 2.2
            else:
                base = 2.0

            painter.setPen(QPen(Qt.GlobalColor.black, pen_scaled(base, ref_escala)))
            painter.setBrush(Qt.BrushStyle.NoBrush)

            dx = clamp(ref_escala * 0.20, mm(0.8), mm(1.5))
            dy = clamp(ref_escala * 0.30, mm(1.1), mm(2.2))

            if up:
                painter.drawLine(int(x), int(y), int(x - dx), int(y + dy))
                painter.drawLine(int(x), int(y), int(x + dx), int(y + dy))
            else:
                painter.drawLine(int(x), int(y), int(x - dx), int(y - dy))
                painter.drawLine(int(x), int(y), int(x + dx), int(y - dy))

        def draw_fc_point(x, y):
            painter.setPen(QPen(Qt.GlobalColor.black, pen_scaled(0.35, ref_escala)))
            painter.setBrush(QColor("black"))
            r = clamp(ref_escala * 0.10, mm(0.35), mm(0.8))
            painter.drawEllipse(QPointF(x, y), r, r)

        def draw_temp_triangle(x, y):
            painter.setPen(QPen(Qt.GlobalColor.black, pen_scaled(0.7, ref_escala)))
            painter.setBrush(Qt.BrushStyle.NoBrush)

            dx = clamp(ref_escala * 0.14, mm(0.5), mm(1.0))
            dy_up = clamp(ref_escala * 0.18, mm(0.7), mm(1.3))
            dy_down = clamp(ref_escala * 0.12, mm(0.5), mm(0.9))

            pts = QPolygonF([
                QPointF(x, y - dy_up),
                QPointF(x - dx, y + dy_down),
                QPointF(x + dx, y + dy_down),
            ])
            painter.drawPolygon(pts)

        def draw_resp_circle(x, y, modo="E"):
            painter.save()

            if modo == "E":  # relleno, más grande
                r = clamp(ref_escala * 0.22, mm(0.9), mm(1.8))
                painter.setPen(QPen(Qt.GlobalColor.black, pen_scaled(1.6, ref_escala)))
                painter.setBrush(QColor("black"))

            elif modo == "A":  # borde grueso, mediano
                r = clamp(ref_escala * 0.18, mm(0.75), mm(1.5))
                painter.setPen(QPen(Qt.GlobalColor.black, pen_scaled(2.2, ref_escala)))
                painter.setBrush(Qt.BrushStyle.NoBrush)

            else:  # C vacío, más pequeño
                r = clamp(ref_escala * 0.14, mm(0.6), mm(1.2))
                painter.setPen(QPen(Qt.GlobalColor.black, pen_scaled(1.2, ref_escala)))
                painter.setBrush(Qt.BrushStyle.NoBrush)

            painter.drawEllipse(QPointF(x, y), r, r)
            painter.restore()

        font_title = QFont("Arial", 14, QFont.Weight.Bold)
        font_label = QFont("Arial", 9, QFont.Weight.Bold)
        font_text = QFont("Arial", 9)
        font_small = QFont("Arial", 6)
        font_small_bold = QFont("Arial", 6, QFont.Weight.Bold)
        font_micro = QFont("Arial", 5)

        datos = ventana.obtener_registro_completo()
        paciente = datos["paciente"]
        cirugia = datos["cirugia"]
        graf = ventana.grafica

        margen_izq = mm(10)
        margen_der = mm(10)
        margen_sup = mm(10)
        margen_inf = mm(10)

        area_x = margen_izq
        area_y = margen_sup
        area_w = page_rect.width() - margen_izq - margen_der
        area_h = page_rect.height() - margen_sup - margen_inf

        y = area_y

        # =========================
        # TÍTULO
        # =========================
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setFont(font_title)
        painter.drawText(
            QRect(area_x, y, area_w, mm(8)),
            Qt.AlignmentFlag.AlignCenter,
            "REGISTRO DE ANESTESIA Y RECUPERACIÓN"
        )
        y += mm(11)

        # =========================
        # ENCABEZADO
        # =========================
        col1_x = area_x
        col2_x = area_x + int(area_w * 0.34)

        draw_line_field(col1_x, y, "Nombre:", paciente["nombre"], mm(16), mm(72))

        x_nss = area_x + int(area_w * 0.62)  # 👈 ajusta este valor
        draw_line_field(x_nss, y, "NSS:", paciente["nss"], mm(10), mm(50))
        y += mm(7)

        draw_line_field(col1_x, y, "Edad:", paciente["edad"], mm(10), mm(22))
        draw_line_field(col2_x, y, "Sexo:", paciente["sexo"], mm(10), mm(16))

        x_unidad = col2_x + mm(28)
        w_unidad_total = area_x + area_w - x_unidad

        draw_unidad_field(x_unidad, y, paciente["unidad"], w_unidad_total)

        y += mm(7)

        x_texto_dx_cx = area_x + mm(43)

        linea_y = draw_wrapped_field(area_x, y, "Diagnóstico preoperatorio:", cirugia["dx_pre"], x_texto_dx_cx, area_w)
        y = linea_y + mm(6)

        linea_y = draw_wrapped_field(area_x, y, "Cirugía programada:", cirugia["cirugia_programada"], x_texto_dx_cx, area_w)
        y = linea_y + mm(6)

        linea_y = draw_wrapped_field(area_x, y, "Diagnóstico operatorio:", cirugia["dx_post"], x_texto_dx_cx, area_w)
        y = linea_y + mm(6)

        linea_y = draw_wrapped_field(area_x, y, "Cirugía realizada:", cirugia["cirugia_realizada"], x_texto_dx_cx, area_w)
        y = linea_y + mm(8)

        y_inicio_grafica = y

        # =========================
        # GEOMETRÍA PRINCIPAL
        # =========================
        w_eventos = mm(14)
        w_escala = mm(10)

        x_eventos = area_x
        x_escala = x_eventos + w_eventos
        x_grid = x_escala + w_escala

        w_grid = area_w - w_eventos - w_escala

        import math

        cols_sv = [d.get("col", 0) for d in graf.datos_sv]
        cols_temp = [d.get("col", 0) for d in graf.datos_temp]
        cols_resp = [d.get("col", 0) for d in graf.datos_resp]

        max_col_datos = max(cols_sv + cols_temp + cols_resp + [35])
        columnas_totales = max_col_datos + 1

        ancho_col_min = mm(3)
        columnas_maximas_en_pagina = int(w_grid / ancho_col_min)

        columnas_por_pagina = min(columnas_totales, columnas_maximas_en_pagina)
        columnas_por_pagina = max(36, columnas_por_pagina)

        total_paginas = math.ceil(columnas_totales / columnas_por_pagina)

        for pagina_actual in range(total_paginas):
            if pagina_actual > 0:
                printer.newPage()

            col_inicio = pagina_actual * columnas_por_pagina
            col_fin = col_inicio + columnas_por_pagina

            num_columnas = columnas_por_pagina
            ancho_col = w_grid / num_columnas

            y = y_inicio_grafica

            alto_fila_ag = mm(5)
            alto_banda_min = mm(4)
            alto_sv = mm(68)

            num_filas = 20
            alto_fila = alto_sv / num_filas
            ref_escala = min(ancho_col, alto_fila)

            y_ag_top = y
            y_ag_bottom = y_ag_top + alto_fila_ag * 4
            y_min_top = y_ag_bottom
            y_min_bottom = y_min_top + alto_banda_min
            y_sv_top = y_min_bottom
            y_sv_bottom = y_sv_top + alto_sv

            # =========================
            # AGENTES
            # =========================
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.setFont(font_small_bold)

            y_agentes_label = y_ag_top + alto_fila_ag * 2 - mm(1.2)

            painter.drawText(
                QRect(int(x_eventos), int(y_agentes_label - mm(1.0)), int(w_eventos + w_escala), mm(3)),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "AGENTES"
            )

            painter.setPen(QPen(Qt.GlobalColor.black, pen_scaled(1.2, ref_escala)))
            painter.drawRect(int(x_grid), int(y_ag_top), int(w_grid), int(alto_fila_ag * 4))

            painter.setPen(QPen(QColor(190, 190, 190), 0.6))
            for j in range(1, 4):
                yy = y_ag_top + j * alto_fila_ag
                painter.drawLine(int(x_grid), int(yy), int(x_grid + w_grid), int(yy))

            for i in range(1, num_columnas):
                if i % 3 != 0:
                    xx = x_grid + i * ancho_col
                    painter.drawLine(int(xx), int(y_ag_top), int(xx), int(y_ag_bottom))

            for i in range(0, num_columnas + 1):
                xx = x_grid + i * ancho_col

                if i % 12 == 0:  # cada 60 min
                    painter.setPen(QPen(Qt.GlobalColor.black, pen_scaled(1.2, ref_escala)))
                elif i % 3 == 0:  # cada 15 min
                    painter.setPen(QPen(QColor(125, 125, 125), 1))
                else:
                    continue

                painter.drawLine(int(xx), int(y_ag_top), int(xx), int(y_ag_bottom))

            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.setFont(font_small)

            y_sevo = y_ag_top + alto_fila_ag * 0.70
            y_flujo = y_ag_top + alto_fila_ag * 1.70
            y_fio2 = y_ag_top + alto_fila_ag * 2.70
            y_spo2 = y_ag_top + alto_fila_ag * 3.70

            label_w = w_eventos + w_escala - mm(1)

            painter.drawText(QRect(int(x_eventos), int(y_sevo - mm(1.7)), int(label_w), mm(3.5)),
                            Qt.AlignmentFlag.AlignRight, "Sevo")
            painter.drawText(QRect(int(x_eventos), int(y_flujo - mm(1.7)), int(label_w), mm(3.5)),
                            Qt.AlignmentFlag.AlignRight, "Flujo")
            painter.drawText(QRect(int(x_eventos), int(y_fio2 - mm(1.7)), int(label_w), mm(3.5)),
                            Qt.AlignmentFlag.AlignRight, "FiO₂")
            painter.drawText(QRect(int(x_eventos), int(y_spo2 - mm(1.7)), int(label_w), mm(3.5)),
                            Qt.AlignmentFlag.AlignRight, "SpO₂")

            painter.setFont(font_micro)
            for d in graf.datos_sv:
                col_global = d.get("col", 0)

                if col_global < col_inicio or col_global >= col_fin:
                    continue

                col = col_global - col_inicio
                x_centro = x_grid + col * ancho_col + (ancho_col / 2)

                painter.drawText(QRect(int(x_centro - mm(2.5)), int(y_sevo - mm(1.5)), mm(5), mm(3)),
                                Qt.AlignmentFlag.AlignCenter, f'{d["sevo"]:.1f}')
                painter.drawText(QRect(int(x_centro - mm(2.5)), int(y_flujo - mm(1.5)), mm(5), mm(3)),
                                Qt.AlignmentFlag.AlignCenter, f'{d["flujo"]:.1f}')
                painter.drawText(QRect(int(x_centro - mm(2.5)), int(y_fio2 - mm(1.5)), mm(5), mm(3)),
                                Qt.AlignmentFlag.AlignCenter, str(d["fio2"]))
                painter.drawText(QRect(int(x_centro - mm(2.5)), int(y_spo2 - mm(1.5)), mm(5), mm(3)),
                                Qt.AlignmentFlag.AlignCenter, str(d["spo2"]))

            # =========================
            # FRANJA DE MINUTOS
            # =========================
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawLine(int(x_grid), int(y_min_top), int(x_grid + w_grid), int(y_min_top))
            painter.drawLine(int(x_grid), int(y_min_bottom), int(x_grid + w_grid), int(y_min_bottom))

            painter.setFont(font_micro)
            for i in range(num_columnas):
                minuto_real = (i + 1) * 5
                if minuto_real % 15 == 0:
                    minuto_etiqueta = minuto_real % 60
                    if minuto_etiqueta == 0:
                        minuto_etiqueta = 60

                    x_txt = x_grid + (i + 1) * ancho_col
                    rect = QRect(int(x_txt - mm(2.5)), int(y_min_top + mm(0.8)), mm(5), mm(3))
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(minuto_etiqueta))

            # =========================
            # GRÁFICA SV
            # =========================
            painter.setPen(QPen(Qt.GlobalColor.black, pen_scaled(1.2, ref_escala)))
            painter.drawRect(int(x_grid), int(y_sv_top), int(w_grid), int(alto_sv))

            painter.setPen(QPen(QColor(190, 190, 190), 0.6))
            for j in range(1, num_filas):
                yy = y_sv_top + j * alto_fila

                if j % 2 == 0:
                    # cada 20 mmHg → línea más marcada
                    painter.setPen(QPen(QColor(125, 125, 125), pen_scaled(0.55, ref_escala)))
                else:
                    # cada 10 mmHg → línea tenue
                    painter.setPen(QPen(QColor(200, 200, 200), pen_scaled(0.35, ref_escala)))

                painter.drawLine(int(x_grid), int(yy), int(x_grid + w_grid), int(yy))

            for i in range(1, num_columnas):
                if i % 3 != 0:
                    xx = x_grid + i * ancho_col
                    painter.drawLine(int(xx), int(y_sv_top), int(xx), int(y_sv_bottom))

            for i in range(0, num_columnas + 1):
                xx = x_grid + i * ancho_col

                if i % 12 == 0:  # cada 60 min
                    painter.setPen(QPen(Qt.GlobalColor.black, pen_scaled(1.0, ref_escala)))
                elif i % 3 == 0:  # cada 15 min
                    painter.setPen(QPen(QColor(125, 125, 125), 1))
                else:
                    continue

                painter.drawLine(int(xx), int(y_sv_top), int(xx), int(y_sv_bottom))

            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.setFont(font_micro)

            for valor in [40, 60, 80, 100, 120, 140, 160, 180, 200, 220, 240]:
                yy = valor_a_y(valor, y_sv_top, y_sv_bottom)
                rect = QRect(int(x_escala), int(yy - mm(1.5)), int(w_escala - mm(1)), mm(3))
                painter.drawText(rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(valor))

            y_sv_datos_bottom = y_sv_bottom - (alto_fila * 3)   

            # Línea separadora arriba del bloque respiración
            y_sep_resp = y_sv_bottom - (alto_fila * 3)
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawLine(int(x_grid), int(y_sep_resp), int(x_grid + w_grid), int(y_sep_resp))

            # Datos SV
            for d in graf.datos_sv:
                col_global = d.get("col", 0)

                if col_global < col_inicio or col_global >= col_fin:
                    continue

                col = col_global - col_inicio

                x_linea = x_grid + col * ancho_col
                x_centro = x_linea + ancho_col / 2

                # pequeño desplazamiento horizontal

                x_fc = x_centro + mm(0.6)

                y_tas = valor_a_y(d["tas"], y_sv_top, y_sv_datos_bottom)
                y_tad = valor_a_y(d["tad"], y_sv_top, y_sv_datos_bottom)
                y_fc = valor_a_y(d["fc"], y_sv_top, y_sv_datos_bottom)

                draw_ta_marker(x_linea, y_tas, valor=d["tas"], up=False)
                draw_ta_marker(x_linea, y_tad, valor=d["tad"], up=True)
                draw_fc_point(x_centro, y_fc)

            for d in graf.datos_temp:
                col_global = d.get("col", 0)

                if col_global < col_inicio or col_global >= col_fin:
                    continue

                col = col_global - col_inicio
                x_centro = x_grid + col * ancho_col + (ancho_col / 2)
                y_temp = temperatura_a_y(d["temp"], y_sv_top, y_sv_datos_bottom)
                draw_temp_triangle(x_centro, y_temp)

            # =========================
            # RESPIRACIÓN (CAE) como círculos
            # =========================
            for d in graf.datos_resp:
                col_global = d.get("col", 0)
                modo = d.get("modo", "")

                if col_global < col_inicio or col_global >= col_fin:
                    continue

                col = col_global - col_inicio
                x_centro = x_grid + col * ancho_col + (ancho_col / 2)

                if modo == "C":
                    y_resp = y_sv_bottom - alto_fila * 0.5
                elif modo == "A":
                    y_resp = y_sv_bottom - alto_fila * 1.5
                elif modo == "E":
                    y_resp = y_sv_bottom - alto_fila * 2.5
                else:
                    continue

                draw_resp_circle(x_centro, y_resp, modo)

            

            # =========================
            # EVENTOS ABAJO
            # =========================
            y_eventos_abajo = y_sv_bottom + mm(3)

            painter.setFont(font_small_bold)
            painter.drawText(
                QRect(int(x_eventos), int(y_eventos_abajo - mm(1.8)), int(w_eventos + w_escala), mm(3.5)),
                Qt.AlignmentFlag.AlignLeft,
                "TIEMPO"
            )

            painter.setFont(font_micro)
            eventos_por_columna = {}

            for ev in graf.eventos_registrados:
                minutos = int((ev["hora"] - graf.hora_inicio).total_seconds() // 60)
                col_global = minutos // 5

                if col_global < col_inicio or col_global >= col_fin:
                    continue

                col = col_global - col_inicio
                eventos_por_columna.setdefault(col, []).append(str(ev["numero"]))

            for col, nums in eventos_por_columna.items():
                x_centro = x_grid + col * ancho_col + (ancho_col / 2)
                texto = ",".join(sorted(nums, key=int))
                rect = QRect(int(x_centro - mm(3.5)), int(y_eventos_abajo - mm(1.5)), mm(7), mm(3))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, texto)

            # =========================
            # COLUMNA IZQUIERDA: SIMBOLOGÍA + EVENTOS
            # =========================
            painter.setPen(QPen(Qt.GlobalColor.black, 1))

            eventos_labels = [
                "1. LLEG. QUIR.",
                "2. I. ANEST.",
                "3. I. OPER.",
                "4. T. OPER.",
                "5. T. ANEST.",
                "6. P. REC."
            ]

            # --- etiquetas respiración (izquierda, pero pegadas a la escala TA) ---
            painter.setFont(font_small_bold)

            x_eac = x_escala + mm(1)   # más a la derecha, casi pegado a la escala TA

            y_c_label = y_sv_bottom - alto_fila * 0.5
            y_a_label = y_sv_bottom - alto_fila * 1.5
            y_e_label = y_sv_bottom - alto_fila * 2.5

            painter.drawText(
                QRect(int(x_eac), int(y_e_label - mm(2)), int(mm(4)), mm(4)),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "E"
            )
            painter.drawText(
                QRect(int(x_eac), int(y_a_label - mm(2)), int(mm(4)), mm(4)),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "A"
            )
            painter.drawText(
                QRect(int(x_eac), int(y_c_label - mm(2)), int(mm(4)), mm(4)),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "C"
            )

            # --- simbología de SV ---
            painter.setFont(font_small)

            y_simbolos_top = y_sv_top + mm(2)
            espacio_simbolos = mm(5)

            simbolos_sv = [
                ("△", "TEMP."),
                ("X", "T.A."),
                ("•", "PULSO"),
                ("○", "R.")
            ]

            for i, (simbolo, texto) in enumerate(simbolos_sv):
                yy = y_simbolos_top + i * espacio_simbolos

                painter.drawText(
                    QRect(int(x_eventos), int(yy), int(mm(4)), mm(4)),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    simbolo
                )
                painter.drawText(
                    QRect(int(x_eventos + mm(4)), int(yy), int(w_eventos + w_escala - mm(4)), mm(4)),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    texto
                )

            # --- título eventos ---
            painter.setFont(font_small_bold)
            y_titulo_eventos = y_sv_top + mm(24)

            painter.drawText(
                QRect(int(x_eventos), int(y_titulo_eventos), int(w_eventos + w_escala), mm(4)),
                Qt.AlignmentFlag.AlignLeft,
                "EVENTOS"
            )

            # --- lista eventos ---
            painter.setFont(font_small)

            y_eventos_txt = y_titulo_eventos + mm(5)
            espacio_eventos = mm(6)

            for i, txt in enumerate(eventos_labels):
                painter.drawText(
                    QRect(int(x_eventos), int(y_eventos_txt + i * espacio_eventos), int(w_eventos + w_escala), mm(4)),
                    Qt.AlignmentFlag.AlignLeft,
                    txt
                )

            if pagina_actual == 0:
                # =========================
                # TABLA DE MEDICAMENTOS
                # =========================
                y_tabla = y_eventos_abajo + mm(4)

                x_letra = area_x + mm(1)
                w_letra = mm(7)
                w_med = mm(48)
                w_dosis = mm(30)

                x1 = x_letra + w_letra
                x2 = x1 + w_med
                x3 = x2 + w_dosis

                alto_header = mm(5)
                alto_fila_med = mm(5)
                total_filas = len(graf.filas_meds)

                y_tabla_bottom = y_tabla + alto_header + total_filas * alto_fila_med

                painter.setPen(QPen(Qt.GlobalColor.black, 1))
                painter.drawRect(int(x_letra), int(y_tabla), int(x3 - x_letra), int(y_tabla_bottom - y_tabla))
                painter.drawLine(int(x1), int(y_tabla), int(x1), int(y_tabla_bottom))
                painter.drawLine(int(x2), int(y_tabla), int(x2), int(y_tabla_bottom))
                painter.drawLine(int(x_letra), int(y_tabla + alto_header), int(x3), int(y_tabla + alto_header))

                for i in range(total_filas):
                    yy = y_tabla + alto_header + (i + 1) * alto_fila_med
                    painter.drawLine(int(x_letra), int(yy), int(x3), int(yy))

                painter.setFont(font_small_bold)
                painter.drawText(QRect(int(x1), int(y_tabla), int(w_med), int(alto_header)),
                                Qt.AlignmentFlag.AlignCenter, "MEDICAMENTOS")
                painter.drawText(QRect(int(x2), int(y_tabla), int(w_dosis), int(alto_header)),
                                Qt.AlignmentFlag.AlignCenter, "DOSIS/VÍA")

                meds = graf.obtener_medicamentos_registrados()
                meds_por_fila = {m["fila"]: m for m in meds}

                painter.setFont(font_micro)
                for i, letra in enumerate(graf.filas_meds):
                    y_fila = y_tabla + alto_header + i * alto_fila_med

                    painter.drawText(QRect(int(x_letra), int(y_fila), int(w_letra), int(alto_fila_med)),
                                    Qt.AlignmentFlag.AlignCenter, letra)

                    med = meds_por_fila.get(letra, {})
                    nombre = med.get("medicamento", "")
                    dosis = med.get("dosis_via", "")

                    painter.drawText(
                        QRect(int(x1 + mm(0.8)), int(y_fila), int(w_med - mm(1.5)), int(alto_fila_med)),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        nombre
                    )

                    painter.drawText(
                        QRect(int(x2 + mm(0.8)), int(y_fila), int(w_dosis - mm(1.5)), int(alto_fila_med)),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        dosis
                    )

    except Exception as e:
        QMessageBox.critical(ventana, "Error", f"No se pudo generar el PDF.\n\n{e}")
        return
    finally:
        painter.end()

    return ruta_pdf


def guardar_pdf_desde_boton(self):
    exportar_a_pdf_imss(self)