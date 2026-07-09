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

            valor = float(valor)
            valor = max(vmin, min(vmax, valor))

            proporcion = (valor - vmin) / (vmax - vmin)
            return y_bottom - proporcion * (y_bottom - y_top)

        def draw_line_field(x, y, label, valor, label_w, line_w):
            painter.setFont(font_label)
            painter.drawText(x, y, label)

            painter.setFont(font_text)
            painter.drawText(x + label_w, y, str(valor))

            painter.setPen(QPen(Qt.GlobalColor.black, 1.5))
            painter.drawLine(x + label_w, y + mm(1.0), x + label_w + line_w, y + mm(1.0))

        def draw_field_inline(x, y, label, valor, label_w, field_w):
            painter.setFont(font_label)
            painter.drawText(
                QRect(int(x), int(y - mm(3)), int(label_w), mm(5)),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                label
            )

            text_x = x + label_w

            painter.setFont(font_text)
            painter.drawText(
                QRect(int(text_x), int(y - mm(3)), int(field_w), mm(5)),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                str(valor)
            )

            painter.setPen(QPen(Qt.GlobalColor.black, 1.5))
            painter.drawLine(
                int(text_x),
                int(y + mm(1.0)),
                int(text_x + field_w),
                int(y + mm(1.0))
            )

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

            painter.setPen(QPen(Qt.GlobalColor.black, 1.5))
            painter.drawLine(text_x, y + mm(1.0), x + total_w, y + mm(1.0))

        def draw_medico_field(x, y, label, valor, label_w, total_w):
            painter.setFont(font_label)
            painter.drawText(x, y, label)

            text_x = x + label_w
            text_w = total_w - label_w

            painter.setFont(font_text)
            texto = str(valor)

            # Calcula cuántas líneas podría necesitar
            fm = painter.fontMetrics()
            rect_calc = fm.boundingRect(
                QRect(0, 0, text_w, mm(30)),
                Qt.TextFlag.TextWordWrap,
                texto
            )

            alto_texto = max(mm(6), rect_calc.height() + mm(1))
            offset_y = mm(4.0)

            rect = QRect(text_x, y - offset_y, text_w, alto_texto)

            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                texto
            )

            linea_y = y + alto_texto - mm(5)

            painter.setPen(QPen(Qt.GlobalColor.black, 1.5))
            painter.drawLine(text_x, linea_y, x + total_w, linea_y)

            return linea_y

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

            painter.setPen(QPen(Qt.GlobalColor.black, 1.5))
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

            # Similar al punto de pantalla, pero escalado al PDF
            r = clamp(ref_escala * 0.12, mm(0.35), mm(0.9))
            painter.drawEllipse(QPointF(x, y), r, r)

        def draw_temp_triangle(x, y):
            painter.setPen(QPen(Qt.GlobalColor.black, pen_scaled(0.7, ref_escala)))
            painter.setBrush(Qt.BrushStyle.NoBrush)

            dx = clamp(ref_escala * 0.18, mm(0.6), mm(1.2))
            dy_up = clamp(ref_escala * 0.22, mm(0.8), mm(1.5))
            dy_down = clamp(ref_escala * 0.14, mm(0.5), mm(1.0))

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
        font_small_bold = QFont("Arial", 5.5, QFont.Weight.Bold)
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
        painter.setPen(QPen(Qt.GlobalColor.black, 1.5))
        painter.setFont(font_title)
        painter.drawText(
            QRect(area_x, y, area_w, mm(8)),
            Qt.AlignmentFlag.AlignCenter,
            "REGISTRO DE ANESTESIA Y RECUPERACIÓN"
        )

        painter.setFont(font_small)

        painter.drawText(
            QRect(area_x, y + mm(7), area_w, mm(4)),
            Qt.AlignmentFlag.AlignRight,
            f"Registro: {datos.get('metadata', {}).get('fecha_creacion', '')}"
        )

        y += mm(13)

        # =========================
        # ENCABEZADO estilo UI / IMSS
        # =========================

        x1 = area_x
        x2 = area_x + mm(95)

        # Fila 1: Nombre / NSS
        draw_field_inline(x1, y, "Nombre:", paciente["nombre"], mm(15), mm(70))
        draw_field_inline(x2, y, "NSS:", paciente["nss"], mm(10), mm(45))
        y += mm(7)

        # Fila 2: Edad / Sexo / Unidad
        draw_field_inline(x1, y, "Edad:", paciente["edad"], mm(12), mm(25))
        draw_field_inline(x1 + mm(50), y, "Sexo:", paciente["sexo"], mm(12), mm(30))
        draw_field_inline(x1 + mm(95), y, "Unidad:", paciente["unidad"], mm(16), mm(55))
        y += mm(7)

        # Campos largos
        x_texto_dx_cx = area_x + mm(43)

        linea_y = draw_wrapped_field(area_x, y, "Diagnóstico preoperatorio:", cirugia["dx_pre"], x_texto_dx_cx, area_w)
        y = linea_y + mm(7)

        linea_y = draw_wrapped_field(area_x, y, "Cirugía programada:", cirugia["cirugia_programada"], x_texto_dx_cx, area_w)
        y = linea_y + mm(7)

        linea_y = draw_wrapped_field(area_x, y, "Diagnóstico operatorio:", cirugia["dx_post"], x_texto_dx_cx, area_w)
        y = linea_y + mm(7)

        linea_y = draw_wrapped_field(area_x, y, "Cirugía realizada:", cirugia["cirugia_realizada"], x_texto_dx_cx, area_w)
        y = linea_y + mm(7)

        # Médicos
        draw_field_inline(
            area_x,
            y,
            "Anestesiólogo:",
            cirugia.get("anestesiologo", ""),
            mm(28),
            mm(60)
        )

        draw_field_inline(
            area_x + mm(100),
            y,
            "Cirujano:",
            cirugia.get("cirujano", ""),
            mm(18),
            mm(62)
        )

        y += mm(8)

        y_inicio_grafica = y - mm(8) 

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
        cols_meds = [m.get("col", 0) for m in getattr(graf, "marcas_medicamentos", [])]

        max_col_datos = max(cols_sv + cols_temp + cols_resp + cols_meds + [35])
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

            # Reducir densidad si columnas están muy comprimidas
            if ancho_col < mm(3):
                mostrar_agentes_cada = 3   # cada 15 min
            elif ancho_col < mm(4):
                mostrar_agentes_cada = 2   # cada 10 min
            else:
                mostrar_agentes_cada = 1   # cada 5 min normal

            y = y_inicio_grafica + mm(2)

            alto_fila_ag = mm(5)
            alto_banda_min = mm(4)
            alto_sv = mm(64)

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
            painter.setPen(QPen(Qt.GlobalColor.black, 1.5))
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

            painter.setPen(QPen(Qt.GlobalColor.black, 1.5))
            painter.setFont(font_small)

            y_sevo = y_ag_top + alto_fila_ag * 0.70
            y_flujo = y_ag_top + alto_fila_ag * 1.70
            y_fio2 = y_ag_top + alto_fila_ag * 2.70
            y_spo2 = y_ag_top + alto_fila_ag * 3.70

            label_w = w_eventos + w_escala - mm(1)

            painter.drawText(QRect(int(x_eventos), int(y_sevo - mm(1.7)), int(label_w), mm(3.5)),
                            Qt.AlignmentFlag.AlignRight, "Sevo (Vol%)")

            painter.drawText(QRect(int(x_eventos), int(y_flujo - mm(1.7)), int(label_w), mm(3.5)),
                            Qt.AlignmentFlag.AlignRight, "Flujo (L/min)")

            painter.drawText(QRect(int(x_eventos), int(y_fio2 - mm(1.7)), int(label_w), mm(3.5)),
                            Qt.AlignmentFlag.AlignRight, "FiO₂ (%)")

            painter.drawText(QRect(int(x_eventos), int(y_spo2 - mm(1.7)), int(label_w), mm(3.5)),
                            Qt.AlignmentFlag.AlignRight, "SpO₂ (%)")

            painter.setFont(font_micro)

            for d in graf.datos_sv:
                col_global = d.get("col", 0)

                if col_global < col_inicio or col_global >= col_fin:
                    continue

                col = col_global - col_inicio

                if col % mostrar_agentes_cada != 0:
                    continue

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
            # FRANJA DE MINUTOS / HORAS
            # =========================
            painter.setPen(QPen(Qt.GlobalColor.black, 1.5))
            painter.drawLine(int(x_grid), int(y_min_top), int(x_grid + w_grid), int(y_min_top))
            painter.drawLine(int(x_grid), int(y_min_bottom), int(x_grid + w_grid), int(y_min_bottom))

            painter.setFont(font_micro)

            hora_base = getattr(graf, "hora_base_rejilla", None)

            if hora_base is None:
                hora_base = getattr(graf, "hora_inicio", None)

            if hora_base is not None:
                # Hora inicial al inicio de la cuadrícula
                painter.setFont(font_small_bold)
                if pagina_actual == 0:
                    painter.drawText(
                        QRect(int(x_grid), int(y_min_top + mm(0.5)), mm(6), mm(3)),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        hora_base.strftime("%H")
                    )

                painter.setFont(font_micro)

                for i in range(1, num_columnas + 1):
                    minuto_total = (col_inicio + i) * 5
                    x_txt = x_grid + i * ancho_col

                    if minuto_total % 60 == 0:
                        hora_abs = hora_base.replace(
                            hour=(hora_base.hour + minuto_total // 60) % 24
                        )

                        painter.setFont(font_small_bold)
                        painter.drawText(
                            QRect(int(x_txt - mm(2.5)), int(y_min_top + mm(0.5)), mm(5), mm(3)),
                            Qt.AlignmentFlag.AlignCenter,
                            hora_abs.strftime("%H")
                        )

                    elif minuto_total % 15 == 0:
                        minuto = minuto_total % 60

                        painter.setFont(font_micro)
                        painter.drawText(
                            QRect(int(x_txt - mm(2.5)), int(y_min_top + mm(0.8)), mm(5), mm(3)),
                            Qt.AlignmentFlag.AlignCenter,
                            str(minuto)
                        )

            else:
                # Fallback viejo si no hay evento 1 todavía
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

            painter.setPen(QPen(Qt.GlobalColor.black, 1.5))
            painter.setFont(font_micro)

            for valor in [40, 60, 80, 100, 120, 140, 160, 180, 200, 220, 240]:
                yy = valor_a_y(valor, y_sv_top, y_sv_bottom)
                rect = QRect(int(x_escala), int(yy - mm(1.5)), int(w_escala - mm(1)), mm(3))
                painter.drawText(rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(valor))

            y_sv_datos_bottom = y_sv_bottom - (alto_fila * 3)   
            y_resp_top = y_sv_datos_bottom

            # Línea separadora arriba del bloque respiración
            y_sep_resp = y_sv_bottom - (alto_fila * 3)
            painter.setPen(QPen(Qt.GlobalColor.black, 1.5))
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

                # FC centrada en la columna, igual que en pantalla
                draw_fc_point(x_centro, y_fc)

            for d in graf.datos_temp:
                col_global = d.get("col", 0)

                if col_global < col_inicio or col_global >= col_fin:
                    continue

                col = col_global - col_inicio
                x_centro = x_grid + col * ancho_col + (ancho_col / 2)
                temp = float(d.get("temp", 36.5))

                y_temp = temperatura_a_y(
                    temp,
                    y_sv_top + mm(28),
                    y_sv_datos_bottom
                )
                draw_temp_triangle(x_centro, y_temp)

            # =========================
            # LETRAS DE MEDICAMENTOS EN PRIMERA COLUMNA
            # =========================
            painter.setFont(font_micro)
            painter.setPen(QPen(Qt.GlobalColor.black, 1))

            for i, letra in enumerate(graf.filas_meds):
                if i >= len(graf.inputs_medicamentos):
                    continue

                if not graf.inputs_medicamentos[i].text().strip():
                    continue

                y_letra = y_sv_top + i * alto_fila

                painter.drawText(
                    QRect(
                        int(x_grid + mm(0.5)),
                        int(y_letra),
                        int(ancho_col - mm(1)),
                        int(alto_fila)
                    ),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    letra
                )


            # =========================
            # MARCAS DE MEDICAMENTOS EN COLUMNA DE TIEMPO
            # =========================
            for marca in getattr(graf, "marcas_medicamentos", []):
                letra = marca.get("letra", "")
                col_global = marca.get("col", 0)

                if col_global < col_inicio or col_global >= col_fin:
                    continue

                if letra not in graf.filas_meds:
                    continue

                fila = graf.filas_meds.index(letra)
                col = col_global - col_inicio

                x = x_grid + col * ancho_col
                y_marca = y_sv_top + fila * alto_fila

                painter.setPen(QPen(Qt.GlobalColor.black, 1))
                painter.setBrush(QColor(70, 70, 70))

                puntos = QPolygonF([
                    QPointF(x + ancho_col, y_marca),
                    QPointF(x + ancho_col, y_marca + alto_fila),
                    QPointF(x + ancho_col / 2, y_marca + alto_fila),
                ])

                painter.drawPolygon(puntos)

            painter.setBrush(Qt.BrushStyle.NoBrush)

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
            # COLUMNA IZQUIERDA: SIMBOLOGÍA + EVENTOS
            # =========================
            painter.setPen(QPen(Qt.GlobalColor.black, 1.5))

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

            # --- números de eventos debajo de la cuadrícula SV ---
            painter.setFont(font_small_bold)
            painter.setPen(QPen(Qt.GlobalColor.black, 1.2))

            from collections import defaultdict

            eventos_por_columna = defaultdict(list)

            for ev in graf.eventos_registrados:
                numero = str(ev.get("numero", ""))
                hora = ev.get("hora", None)

                if not numero or hora is None:
                    continue

                minutos = graf.minutos_desde_inicio(hora)
                columna_global = minutos // 5

                if columna_global < col_inicio or columna_global >= col_fin:
                    continue

                columna_local = columna_global - col_inicio
                eventos_por_columna[columna_local].append(numero)

            y_num_eventos = y_sv_bottom + mm(1)

            for columna_local, numeros in eventos_por_columna.items():
                texto = ",".join(sorted(numeros, key=int))

                x_centro = x_grid + columna_local * ancho_col + ancho_col / 2

                painter.drawText(
                    QRect(
                        int(x_centro - mm(4)),
                        int(y_num_eventos),
                        int(mm(8)),
                        int(mm(4))
                    ),
                    Qt.AlignmentFlag.AlignCenter,
                    texto
                )

            if pagina_actual == 0:
                # =========================
                # MARCAS DE MEDICAMENTOS
                # =========================

                painter.setBrush(QColor(70, 70, 70))
                painter.setPen(QPen(Qt.GlobalColor.black, 1))

                alto_fila_med = (y_sv_bottom - y_sv_top) / 20

                for marca in graf.marcas_medicamentos:

                    letra = marca["letra"]
                    col = marca["col"]

                    if letra not in graf.filas_meds:
                        continue

                    fila = graf.filas_meds.index(letra)

                    x = x_grid + (col * ancho_col)

                    y = y_sv_top + (fila * alto_fila_med)

                    puntos = QPolygonF([
                        QPointF(x + ancho_col, y),
                        QPointF(x + ancho_col, y + alto_fila_med),
                        QPointF(x + ancho_col / 2, y + alto_fila_med),
                    ])

                    painter.drawPolygon(puntos)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(Qt.GlobalColor.black, 1.5))
                
                # =========================
                # TABLA DE MEDICAMENTOS
                # =========================
                y_tabla = y_sv_bottom + mm(9)

                x_letra = area_x + mm(1)
                w_letra = mm(8)
                w_med = mm(52)
                w_dosis = mm(28)

                x1 = x_letra + w_letra
                x2 = x1 + w_med
                x3 = x2 + w_dosis

                alto_header = mm(5)
                alto_fila_med = mm(6)
                total_filas = len(graf.filas_meds)

                y_tabla_bottom = y_tabla + alto_header + total_filas * alto_fila_med

                painter.setPen(QPen(Qt.GlobalColor.black, 1.5))
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

                # =========================
                # BLOQUES DERECHOS DINÁMICOS
                # MÉTODO/TÉCNICA + CASO OBSTÉTRICO + BALANCE HÍDRICO
                # =========================

                registro = ventana.obtener_registro_completo()

                x_bloque = mm(110)
                y_bloque = y_tabla
                w_bloque = mm(70)
                margen_bloque = mm(2)

                def texto_ml_pdf(valor):
                    texto = str(valor or "").strip()
                    if not texto:
                        return ""
                    limpio = texto.replace("mL", "").replace("ml", "").replace(",", "").strip()
                    if not limpio:
                        return ""
                    try:
                        return f"{float(limpio):,.0f}"
                    except Exception:
                        return texto.replace(" mL", "").replace("mL", "").strip()

                def numero_ml_pdf(valor):
                    texto = str(valor or "").strip()
                    limpio = texto.replace("mL", "").replace("ml", "").replace(",", "").replace("+", "").strip()
                    if not limpio:
                        return 0.0
                    try:
                        return float(limpio)
                    except Exception:
                        return 0.0

                def draw_titulo_bloque(x, y, w, titulo):
                    painter.setFont(QFont("Arial", 6, QFont.Weight.Bold))
                    painter.drawText(
                        QRect(int(x), int(y + mm(0.8)), int(w), int(mm(4.5))),
                        Qt.AlignmentFlag.AlignCenter,
                        titulo
                    )

                def alto_texto(texto, w, fuente=None, min_h=None):
                    if fuente:
                        painter.setFont(fuente)
                    fm = painter.fontMetrics()
                    h = fm.boundingRect(
                        QRect(0, 0, int(w), int(mm(30))),
                        Qt.TextFlag.TextWordWrap,
                        str(texto or "")
                    ).height()
                    if min_h is None:
                        min_h = mm(3.4)
                    return max(min_h, h + mm(0.3))

                def draw_texto_wrap(x, y, w, texto, fuente=None, bold=False):
                    if fuente is not None:
                        painter.setFont(fuente)
                    elif bold:
                        painter.setFont(QFont("Arial", 5.5, QFont.Weight.Bold))
                    else:
                        painter.setFont(QFont("Arial", 5.5))
                    h = alto_texto(texto, w)
                    painter.drawText(
                        QRect(int(x), int(y), int(w), int(h)),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                        str(texto or "")
                    )
                    return y + h

                def draw_metodo_tecnica(x, y, w):
                    tecnica = registro.get("tecnica_anestesica", {}) or {}
                    tipo = tecnica.get("tipo_anestesia", "") or ""
                    sub = tecnica.get("subtecnica", "") or ""
                    detalle = tecnica.get("detalle_regional", {}) or {}

                    lineas = []
                    if tipo:
                        lineas.append((f"(X) {tipo.upper()}", True, mm(5)))
                    if sub:
                        lineas.append((f"(X) {sub}", True, mm(6)))

                    # Detalle regional: sólo imprime lo que exista.
                    tipo_det = detalle.get("tipo", "")
                    subtipo = detalle.get("subtipo", "")
                    nivel = detalle.get("nivel", "")
                    tipo_aguja = detalle.get("tipo_aguja", "")
                    anestesico_local = detalle.get("anestesico_local", "")
                    sitio = detalle.get("sitio", "")

                    if tipo_det:
                        lineas.append((f"Tipo regional: {tipo_det}", False, mm(8)))
                    if subtipo:
                        lineas.append((f"Subtipo: {subtipo}", False, mm(8)))
                    if nivel:
                        lineas.append((f"Nivel: {nivel}", False, mm(8)))
                    if tipo_aguja:
                        lineas.append((f"Aguja: {tipo_aguja}", False, mm(8)))
                    if anestesico_local:
                        lineas.append((f"Anestésico local: {anestesico_local}", False, mm(8)))
                    if sitio:
                        lineas.append((f"Sitio: {sitio}", False, mm(8)))

                    if not lineas:
                        lineas.append(("Sin técnica registrada", False, mm(5)))

                    alto_header = mm(6)
                    alto_lineas = 0
                    font_normal = QFont("Arial", 6)
                    font_bold = QFont("Arial", 5.5, QFont.Weight.Bold)
                    for texto, bold, indent in lineas:
                        alto_lineas += alto_texto(texto, w - indent - mm(4), font_bold if bold else font_normal)

                    h = max(mm(15), alto_header + alto_lineas + mm(2.5))

                    painter.setPen(QPen(Qt.GlobalColor.black, 1))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(int(x), int(y), int(w), int(h))
                    draw_titulo_bloque(x, y, w, "MÉTODO Y TÉCNICA ANESTÉSICA")

                    y_cursor = y + alto_header
                    for texto, bold, indent in lineas:
                        fuente = font_bold if bold else font_normal
                        y_cursor = draw_texto_wrap(x + indent, y_cursor, w - indent - mm(4), texto, fuente=fuente)

                    return y + h

                def draw_caso_obstetrico(x, y, w):
                    caso_ob = registro.get("caso_obstetrico", registro.get("obstetrico", {})) or {}
                    if not caso_ob.get("activo"):
                        return y

                    sexo_rn = caso_ob.get("sexo_rn", "")
                    peso_rn = caso_ob.get("peso_rn", "")
                    talla_rn = caso_ob.get("talla_rn", "")
                    apgar_1 = caso_ob.get("apgar_1", "")
                    apgar_5 = caso_ob.get("apgar_5", "")
                    apgar_10 = caso_ob.get("apgar_10", "")
                    estado_rn = caso_ob.get("estado_rn", "")

                    lineas = [
                        (f"RN Sexo: {sexo_rn or ''}        Peso: {peso_rn or ''}        Talla: {talla_rn or ''}", False),
                        (f"Apgar 1 min: {apgar_1 or ''}        5 min: {apgar_5 or ''}        10 min: {apgar_10 or ''}", False),
                    ]
                    if estado_rn:
                        lineas.append((f"Estado al salir: {estado_rn}", False))

                    alto_header = mm(8)
                    font_normal = QFont("Arial", 6)
                    alto_lineas = sum(alto_texto(t, w - mm(6), font_normal) for t, _ in lineas)
                    h = max(mm(18), alto_header + alto_lineas + mm(2.5))

                    painter.setPen(QPen(Qt.GlobalColor.black, 1))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(int(x), int(y), int(w), int(h))
                    draw_titulo_bloque(x, y, w, "CASOS OBSTÉTRICOS")

                    y_cursor = y + alto_header
                    for texto, _ in lineas:
                        y_cursor = draw_texto_wrap(x + mm(3), y_cursor, w - mm(6), texto, fuente=font_normal)

                    return y + h

                def draw_balance_hidrico(x, y, w):
                    balance_h = registro.get("balance_hidrico", {}) or {}
                    ingresos_b = balance_h.get("ingresos", {}) or {}
                    egresos_b = balance_h.get("egresos", {}) or {}

                    filas_ing = [
                        ("Cristaloides", ingresos_b.get("cristaloides", "")),
                        ("Coloides", ingresos_b.get("coloides", "")),
                        ("Conc. Erit.", ingresos_b.get("ce", "")),
                        ("PFC", ingresos_b.get("pfc", "")),
                        ("Plaquetas", ingresos_b.get("plaquetas", "")),
                        ("Crioprecip.", ingresos_b.get("crioprecipitados", "")),
                        ("Otros", ingresos_b.get("otros", "")),
                    ]
                    filas_egr = [
                        ("Sangrado", egresos_b.get("sangrado", "")),
                        ("Diuresis", egresos_b.get("diuresis", "")),
                        ("Aspirado", egresos_b.get("aspirado_gastrico", "")),
                        ("Drenajes", egresos_b.get("drenajes", "")),
                        ("Otros", egresos_b.get("otros", "")),
                    ]

                    alto_header = mm(6)
                    alto_subheader = mm(4)
                    alto_fila = mm(3.6)
                    n_filas = max(len(filas_ing), len(filas_egr))
                    alto_totales = mm(5.5)
                    alto_balance = mm(6.5)
                    h = alto_header + alto_subheader + n_filas * alto_fila + alto_totales + alto_balance + mm(2.5)

                    painter.setPen(QPen(Qt.GlobalColor.black, 1))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(int(x), int(y), int(w), int(h))
                    draw_titulo_bloque(x, y, w, "BALANCE HÍDRICO")

                    x_mid = x + w / 2
                    painter.drawLine(int(x_mid), int(y + alto_header), int(x_mid), int(y + h - alto_balance - mm(1)))

                    x_ing = x + mm(3)
                    x_egr = x_mid + mm(3)
                    x_val_ing = x_mid - mm(4)
                    x_val_egr = x + w - mm(4)
                    col_w = w / 2 - mm(6)

                    painter.setFont(QFont("Arial", 5.5, QFont.Weight.Bold))
                    y_sub = y + alto_header + mm(2.6)
                    painter.drawText(int(x_ing), int(y_sub), "INGRESOS (mL)")
                    painter.drawText(int(x_egr), int(y_sub), "EGRESOS (mL)")

                    painter.setFont(QFont("Arial", 5))
                    y_f = y + alto_header + alto_subheader + mm(2.8)
                    for i in range(n_filas):
                        yy = y_f + i * alto_fila
                        if i < len(filas_ing):
                            lbl, val = filas_ing[i]
                            painter.drawText(int(x_ing), int(yy), lbl)
                            painter.drawText(
                                QRect(int(x_val_ing - mm(16)), int(yy - mm(3.2)), int(mm(15)), int(mm(4))),
                                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                                texto_ml_pdf(val)
                            )
                        if i < len(filas_egr):
                            lbl, val = filas_egr[i]
                            painter.drawText(int(x_egr), int(yy), lbl)
                            painter.drawText(
                                QRect(int(x_val_egr - mm(16)), int(yy - mm(3.2)), int(mm(15)), int(mm(4))),
                                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                                texto_ml_pdf(val)
                            )

                    y_sep = y + alto_header + alto_subheader + n_filas * alto_fila + mm(0.5)
                    painter.setPen(QPen(Qt.GlobalColor.black, 0.8))
                    painter.drawLine(int(x + mm(2)), int(y_sep), int(x + w - mm(2)), int(y_sep))
                    painter.setPen(QPen(Qt.GlobalColor.black, 1))

                    y_tot = y_sep + mm(3.8)
                    painter.setFont(QFont("Arial", 5.5, QFont.Weight.Bold))
                    painter.drawText(int(x_ing), int(y_tot), "Total")
                    painter.drawText(int(x_egr), int(y_tot), "Total")

                    total_ing = texto_ml_pdf(ingresos_b.get("total", ""))
                    total_egr = texto_ml_pdf(egresos_b.get("total", ""))
                    painter.drawText(
                        QRect(int(x_val_ing - mm(18)), int(y_tot - mm(4)), int(mm(17)), int(mm(5))),
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                        (total_ing + " mL") if total_ing else ""
                    )
                    painter.drawText(
                        QRect(int(x_val_egr - mm(18)), int(y_tot - mm(4)), int(mm(17)), int(mm(5))),
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                        (total_egr + " mL") if total_egr else ""
                    )

                    y_bn = y + h - alto_balance + mm(0.6)
                    painter.drawLine(int(x + mm(2)), int(y_bn - mm(1.5)), int(x + w - mm(2)), int(y_bn - mm(1.5)))

                    balance_txt = str(balance_h.get("balance_neto", "") or "0 mL")
                    balance_num = numero_ml_pdf(balance_txt)
                    es_positivo = balance_txt.strip().startswith("+") or balance_num > 0
                    es_negativo = balance_txt.strip().startswith("-") or balance_num < 0

                    painter.setFont(QFont("Arial", 6, QFont.Weight.Bold))
                    painter.drawText(int(x_ing), int(y_bn + mm(4)), "BALANCE NETO")

                    x_bn_box = x + w - mm(34)
                    y_bn_box = y_bn - mm(0.5)
                    w_bn_box = mm(30)
                    h_bn_box = mm(5.5)

                    if es_positivo:
                        painter.setBrush(QColor(232, 245, 233))
                        painter.setPen(QPen(QColor(0, 80, 0), 1.2))
                    elif es_negativo:
                        painter.setBrush(QColor(255, 235, 238))
                        painter.setPen(QPen(QColor(130, 0, 0), 1.2))
                    else:
                        painter.setBrush(QColor(238, 238, 238))
                        painter.setPen(QPen(Qt.GlobalColor.black, 1.2))

                    painter.drawRect(int(x_bn_box), int(y_bn_box), int(w_bn_box), int(h_bn_box))

                    if es_positivo:
                        painter.setPen(QPen(QColor(0, 80, 0), 1))
                    elif es_negativo:
                        painter.setPen(QPen(QColor(130, 0, 0), 1))
                    else:
                        painter.setPen(QPen(Qt.GlobalColor.black, 1))

                    painter.setFont(QFont("Arial", 6.5, QFont.Weight.Bold))
                    painter.drawText(
                        QRect(int(x_bn_box), int(y_bn_box), int(w_bn_box), int(h_bn_box)),
                        Qt.AlignmentFlag.AlignCenter,
                        balance_txt
                    )

                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.setPen(QPen(Qt.GlobalColor.black, 1))

                    return y + h

                # Dibujo en cadena: cada función devuelve el siguiente Y disponible.
                y_siguiente = draw_metodo_tecnica(x_bloque, y_bloque, w_bloque) + margen_bloque
                y_siguiente = draw_caso_obstetrico(x_bloque, y_siguiente, w_bloque) + margen_bloque
                y_siguiente = draw_balance_hidrico(x_bloque, y_siguiente, w_bloque)

    except Exception as e:
        QMessageBox.critical(ventana, "Error", f"No se pudo generar el PDF.\n\n{e}")
        return
    finally:
        painter.end()

    return ruta_pdf


def guardar_pdf_desde_boton(self):
    exportar_a_pdf_imss(self)