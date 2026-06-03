import sys
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QComboBox, QCompleter, QFormLayout
)
from PyQt6.QtGui import QPainter, QPen, QColor, QPolygonF, QFont, QPalette
from PyQt6.QtCore import Qt, QPointF, QRect, QTimer
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtGui import QPageSize
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import QStringListModel
from PyQt6.QtWidgets import QRadioButton, QButtonGroup, QStackedWidget, QSizePolicy, QCheckBox
from exportar_pdf_imss import exportar_a_pdf_imss
import json

class LineEditConSufijo(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sufijo_sugerido = ""

    def setSufijoSugerido(self, texto):
        self.sufijo_sugerido = texto or ""
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        if not self.sufijo_sugerido:
            return

        texto = self.text().strip()

        if not texto:
            return

        if not self._texto_compatible(texto):
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        fm = self.fontMetrics()
        x_texto = 6 + fm.horizontalAdvance(texto) + 4
        y_texto = int((self.height() + fm.ascent() - fm.descent()) / 2)

        color = self.palette().color(QPalette.ColorRole.PlaceholderText)
        painter.setPen(color)
        painter.drawText(x_texto, y_texto, self.sufijo_sugerido)

    def _texto_compatible(self, texto):
        if not texto:
            return False

        texto = texto.replace(",", ".")
        try:
            float(texto)
            return True
        except ValueError:
            return False

    def convertir_a_texto_final(self):
        texto = self.text().strip()

        if not self.sufijo_sugerido:
            return

        if not texto:
            return

        if not self._texto_compatible(texto):
            return

        texto_final = f"{texto} {self.sufijo_sugerido}".strip()

        if texto_final == self.text():
            return

        self.blockSignals(True)
        self.setText(texto_final)
        self.blockSignals(False)

        self.sufijo_sugerido = ""
        self.update()

    def focusOutEvent(self, event):
        self.convertir_a_texto_final()
        super().focusOutEvent(event)

class CuadriculaSV(QWidget):
    def __init__(self, grafica_padre):
        super().__init__()
        self.grafica = grafica_padre

        self.ancho_col = 35
        self.num_columnas = 72
        self.alto_agentes = 80
        self.alto_minutos = 16
        self.alto_sv = 380

        self.setFixedSize(
            self.num_columnas * self.ancho_col,
            self.alto_agentes + self.alto_minutos + self.alto_sv
        )

        self.setStyleSheet("background-color: white;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("white"))

        x0 = 0
        y_ag_top = 0
        y_ag_bottom = y_ag_top + self.alto_agentes
        y_min_top = y_ag_bottom
        y_min_bottom = y_min_top + self.alto_minutos
        y_sv_top = y_min_bottom
        y_sv_bottom = y_sv_top + self.alto_sv

        x1 = self.width()
        ancho_col = self.ancho_col
        num_columnas = self.num_columnas

        # =========================
        # AGENTES
        # =========================
        alto_fila_ag = self.alto_agentes / 4

        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawRect(x0, y_ag_top, x1 - x0, self.alto_agentes)

        painter.setPen(QPen(QColor(180, 180, 180), 1))
        for j in range(1, 4):
            y = int(y_ag_top + j * alto_fila_ag)
            painter.drawLine(x0, y, x1, y)

        for i in range(1, num_columnas):
            x = int(x0 + i * ancho_col)
            painter.drawLine(x, y_ag_top, x, y_ag_bottom)

        painter.setPen(QPen(QColor(120, 120, 120), 2))
        for i in range(0, num_columnas + 1, 3):
            x = int(x0 + i * ancho_col)
            painter.drawLine(x, y_ag_top, x, y_ag_bottom)

        # =========================
        # MINUTOS / HORAS
        # =========================
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(x0, y_min_top, x1, y_min_top)
        painter.drawLine(x0, y_min_bottom, x1, y_min_bottom)

        font_hora = QFont("Arial", 9, QFont.Weight.Bold)
        font_min = QFont("Arial", 8)

        painter.setFont(font_hora)

        hora_base = self.grafica.hora_base_rejilla

        if hora_base is not None:
            # Hora cero
            painter.drawText(x0 + 2, y_min_top + 12, hora_base.strftime("%H"))

            for i in range(1, num_columnas + 1):
                minuto_total = i * 5
                x = int(x0 + i * ancho_col)

                if minuto_total % 60 == 0:
                    hora = hora_base.replace(hour=(hora_base.hour + minuto_total // 60) % 24)
                    texto = hora.strftime("%H")

                    painter.setFont(font_hora)
                    painter.drawText(x - 8, y_min_top + 12, texto)

                elif minuto_total % 15 == 0:
                    minuto = minuto_total % 60
                    painter.setFont(font_min)
                    painter.drawText(x - 8, y_min_top + 12, str(minuto))
        else:
            for i in range(num_columnas):
                minuto_real = (i + 1) * 5

                if minuto_real % 15 == 0:
                    minuto_etiqueta = minuto_real % 60
                    if minuto_etiqueta == 0:
                        minuto_etiqueta = 60

                    x = int(x0 + (i + 1) * ancho_col)
                    painter.drawText(x - 8, y_min_top + 12, str(minuto_etiqueta))

        # =========================
        # CUADRÍCULA SV
        # =========================
        painter.setPen(QPen(Qt.GlobalColor.black, 2))

        # Borde SV sin línea inferior, para que no se empalme con el scroll horizontal
        painter.drawLine(x0, y_sv_top, x1, y_sv_top)        # superior
        painter.drawLine(x0, y_sv_top, x0, y_sv_bottom)     # izquierdo
        painter.drawLine(x1, y_sv_top, x1, y_sv_bottom)     # derecho
        # painter.drawLine(x0, y_sv_bottom, x1, y_sv_bottom)  # inferior desactivado

        num_filas = 20
        alto_fila = self.alto_sv / num_filas

        for j in range(1, num_filas):
            y = int(y_sv_top + j * alto_fila)

            if j % 2 == 0:
                painter.setPen(QPen(QColor(130, 130, 130), 1))
            else:
                painter.setPen(QPen(QColor(200, 200, 200), 1))

            painter.drawLine(x0, y, x1, y)

        painter.setPen(QPen(QColor(180, 180, 180), 1))
        for i in range(1, num_columnas):
            x = int(x0 + i * ancho_col)
            painter.drawLine(x, y_sv_top, x, y_sv_bottom)

        painter.setPen(QPen(QColor(120, 120, 120), 2))
        for i in range(0, num_columnas + 1, 3):
            x = int(x0 + i * ancho_col)
            painter.drawLine(x, y_sv_top, x, y_sv_bottom)

        # =========================
        # SIGNOS VITALES SIMULADOS
        # =========================
        y_sv_datos_bottom = y_sv_bottom - (alto_fila * 3)

        # Línea separadora de respiración
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(x0, int(y_sv_datos_bottom), x1, int(y_sv_datos_bottom))

        # TA y FC
        for d in self.grafica.datos_sv:
            col = d.get("col", 0)

            x_linea = x0 + col * ancho_col
            x_centro = x_linea + ancho_col / 2

            y_tas = self.grafica.valor_a_y(d["tas"], y_sv_top, y_sv_datos_bottom)
            y_tad = self.grafica.valor_a_y(d["tad"], y_sv_top, y_sv_datos_bottom)
            y_fc = self.grafica.valor_a_y(d["fc"], y_sv_top, y_sv_datos_bottom)

            self.grafica.draw_ta_marker(painter, x_linea, y_tas, up=False)
            self.grafica.draw_ta_marker(painter, x_linea, y_tad, up=True)
            self.grafica.draw_fc_point(painter, x_centro, y_fc)

        # Temperatura
        for d in self.grafica.datos_temp:
            col = d.get("col", 0)

            x_centro = x0 + col * ancho_col + ancho_col / 2
            y_temp = self.grafica.temperatura_a_y(
                d["temp"],
                y_sv_top,
                y_sv_datos_bottom
            )

            self.grafica.dibujar_triangulo(painter, x_centro, y_temp, tamaño=6)

        # Respiración C/A/E
        for d in self.grafica.datos_resp:
            col = d.get("col", 0)
            modo = d.get("modo", "")

            x_centro = x0 + col * ancho_col + ancho_col / 2

            if modo == "C":
                y_resp = y_sv_bottom - alto_fila * 0.5
            elif modo == "A":
                y_resp = y_sv_bottom - alto_fila * 1.5
            elif modo == "E":
                y_resp = y_sv_bottom - alto_fila * 2.5
            else:
                continue

            painter.setPen(QPen(Qt.GlobalColor.black, 2))

            if modo == "E":
                painter.setBrush(QColor("black"))
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)

            painter.drawEllipse(QPointF(x_centro, y_resp), 4, 4)

        # Agentes arriba
        painter.setFont(QFont("Arial", 8))
        painter.setPen(QPen(Qt.GlobalColor.black, 1))

        for d in self.grafica.datos_sv:
            col = d.get("col", 0)
            x_centro = x0 + col * ancho_col + ancho_col / 2

            painter.drawText(int(x_centro - 10), int(y_ag_top + alto_fila_ag * 0.70), f'{d["sevo"]:.1f}')
            painter.drawText(int(x_centro - 10), int(y_ag_top + alto_fila_ag * 1.70), f'{d["flujo"]:.1f}')
            painter.drawText(int(x_centro - 10), int(y_ag_top + alto_fila_ag * 2.70), str(d["fio2"]))
            painter.drawText(int(x_centro - 10), int(y_ag_top + alto_fila_ag * 3.70), str(d["spo2"]))

        # =========================
        # MARCAS DE MEDICAMENTOS
        # =========================
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        alto_fila_med = alto_fila

        for i, letra in enumerate(self.grafica.filas_meds):
            if i >= len(self.grafica.inputs_medicamentos):
                continue

            if not self.grafica.inputs_medicamentos[i].text().strip():
                continue

            y = y_sv_top + i * alto_fila_med
            painter.drawText(
                QRect(int(x0 + 2), int(y), int(ancho_col - 4), int(alto_fila_med)),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                letra
            )

        painter.setBrush(QColor(70, 70, 70))

        for marca in self.grafica.marcas_medicamentos:
            letra = marca["letra"]
            col = marca["col"]

            if letra not in self.grafica.filas_meds:
                continue

            fila = self.grafica.filas_meds.index(letra)

            x = x0 + col * ancho_col
            y = y_sv_top + fila * alto_fila_med

            puntos = QPolygonF([
                QPointF(x + ancho_col, y),
                QPointF(x + ancho_col, y + alto_fila_med),
                QPointF(x + ancho_col / 2, y + alto_fila_med),
            ])

            painter.drawPolygon(puntos)
        
class GraficaAnestesia(QWidget):
    def __init__(self):
        super().__init__()

        self.datos_sv = []
        self.columna_actual = 0
        self.max_columnas = 72  # 00,05,10,...55
        self.velocidad_sim_ms = 2000
        self.datos_temp = []
        self.datos_resp = []   # {"col": int, "modo": "C"|"A"|"E"}

        self.timer_sv = QTimer(self)
        self.timer_sv.timeout.connect(self.agregar_dato_simulado)
        self.timer_sv.setInterval(self.velocidad_sim_ms)

        # =========================
        # TIEMPOS CLÍNICOS (inputs)
        # =========================

        self.eventos_qx = [
            "1. Entrada Qx",
            "2. Inicio anest.",
            "3. Inicio cirugía",
            "4. Fin cirugía",
            "5. Fin anest.",
            "6. Salida Qx"
        ]

        self.inputs_tiempos = []

        self.setFixedSize(1400, 1120)

        self.botones_eventos = []

        self.eventos_titulos = [
            "1. Entrada Qx",
            "2. Inicio anest.",
            "3. Inicio cirugía",
            "4. Fin cirugía",
            "5. Fin anest.",
            "6. Salida Qx"
        ]

        for i, evento in enumerate(self.eventos_qx, start=1):
            btn = QPushButton(evento, self)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, n=i: self.registrar_evento(n))
            self.botones_eventos.append(btn)

        self.btn_deshacer = QPushButton("↺", self)
        self.btn_deshacer.setToolTip("Deshacer último evento")
        self.btn_deshacer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deshacer.clicked.connect(self.deshacer_ultimo_evento)
        self.btn_deshacer.setFixedSize(24, 20)
        self.btn_deshacer.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                color: black;
                font-size: 13px;
            }
            QPushButton:hover {
                color: #555;
            }
        """)

        self.btn_iniciar_sv = QPushButton("Inicio", self)
        self.btn_iniciar_sv.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_iniciar_sv.clicked.connect(self.iniciar_simulacion_sv)

        self.btn_pausar_sv = QPushButton("Pausa", self)
        self.btn_pausar_sv.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pausar_sv.clicked.connect(self.pausar_simulacion_sv)

        self.btn_reiniciar_sv = QPushButton("Reinicio", self)
        self.btn_reiniciar_sv.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reiniciar_sv.clicked.connect(self.reiniciar_simulacion_sv)

        for btn in [self.btn_iniciar_sv, self.btn_pausar_sv, self.btn_reiniciar_sv]:
            btn.setFixedSize(90, 18)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: black;
                    border: 2px solid black;
                    border-radius: 3px;
                    font-size: 10px;
                    padding: 0px 3px;
                }
                QPushButton:hover {
                    background-color: #f2f2f2;
                }
                QPushButton:pressed {
                    background-color: #e6e6e6;
                }
            """)

        self.btn_reiniciar_sv.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: black;
                border: 2px solid black;
                border-radius: 3px;
                font-size: 10px;
                padding-top: 1px;
                padding-bottom: 1px;
                }
            """)

        self.btn_pausar_sv.setEnabled(False)
        self.btn_reiniciar_sv.setEnabled(True)
        self.combo_velocidad_sv = QComboBox(self)
        self.combo_velocidad_sv.addItems(["1x", "2x", "5x", "10x"])
        self.combo_velocidad_sv.setCurrentText("1x")
        self.combo_velocidad_sv.currentTextChanged.connect(self.cambiar_velocidad_simulacion)
        self.combo_velocidad_sv.setStyleSheet("""
            QComboBox {
                background-color: white;
                color: black;
                border: 1px solid black;
                border-radius: 3px;
                font-size: 9px;
                padding: 1px 6px;
            }
        """)
        self.combo_velocidad_sv.setFixedSize(70, 20)

        # Cada columna = 5 minutos
        self.time_columns = [
            "00", "05", "10", "15", "20", "25",
            "30", "35", "40", "45", "50", "55"
        ]

        # Datos TA: (minuto, sistolica, diastolica)
        self.ta_data = [
            ("00", 120, 80),
            ("05", 118, 78),
            ("10", 130, 85),
            ("15", 110, 70),
            ("20", 125, 82),
            ("25", 122, 79),
            ("30", 128, 84),
            ("35", 116, 76),
            ("40", 121, 81),
            ("45", 115, 74),
        ]

        self.fc_data = [
            ("00", 78),
            ("05", 82),
            ("10", 88),
            ("15", 76),
            ("20", 84),
            ("25", 80),
            ("30", 86),
            ("35", 79),
            ("40", 81),
            ("45", 75),
        ]

        self.spo2_data = [
            ("00", 98), ("05", 97), ("10", 99), ("15", 96),
            ("20", 98), ("25", 97), ("30", 99), ("35", 98),
        ]

        self.fio2_data = [
            ("00", 40), ("05", 40), ("10", 45), ("15", 50),
            ("20", 50), ("25", 45), ("30", 40), ("35", 40),
        ]

        self.flow_data = [
            ("00", 2.0), ("05", 2.0), ("10", 2.5), ("15", 3.0),
            ("20", 3.0), ("25", 2.5), ("30", 2.0), ("35", 2.0),
        ]

        self.sevo_data = [
            ("00", 2.0), ("05", 2.2), ("10", 2.5), ("15", 2.8),
            ("20", 2.5), ("25", 2.3), ("30", 2.0), ("35", 2.0),
        ]

        # Cuadro base: una celda cuadrada
        self.cell_size = 35

        # Área de gráfica
        self.graph_left = 120
        self.graph_top = 200

        self.total_columns = len(self.time_columns)
        self.total_rows = 16  # de 40 a 200 en pasos de 10 => 16 intervalos

        self.graph_right = self.graph_left + self.total_columns * self.cell_size
        self.graph_bottom = self.graph_top + self.total_rows * self.cell_size

        self.column_width = self.cell_size

        self.bp_min = 40
        self.bp_max = 200

        # Datos de ejemplo cada 5 min
        self.tiempos = [5, 10, 15, 20, 25, 30, 35, 40, 45]
        self.pulso = [82, 80, 78, 76, 79, 81, 80, 77, 75]
        self.ta_sistolica = [118, 116, 114, 110, 112, 115, 113, 109, 108]
        self.ta_diastolica = [72, 70, 68, 66, 67, 69, 68, 65, 64]
        self.spo2 = [99, 99, 98, 98, 99, 99, 98, 97, 98]
        self.temperatura = [36.5, 36.4, 36.4, 36.3, 36.3, 36.4, 36.5, 36.4, 36.4]

        self.fio2 = ["1.0", "1.0", "0.8", "0.8", "0.7", "0.7", "0.6", "0.6", "0.5"]
        self.flujo = ["2", "2", "2", "2", "1.5", "1.5", "1", "1", "1"]
        self.sevo = ["2.0", "2.0", "2.0", "1.8", "1.8", "1.5", "1.5", "1.2", "1.0"]

        self.eventos_registrados = []   # lista de eventos: {"hora": ..., "numero": ...}
        self.hora_inicio = datetime.now()
        self.hora_base_rejilla = None
        
        self.actualizar_estado_botones()

        self.filas_meds = [chr(ord('A') + i) for i in range(13)]
        self.inputs_medicamentos = []
        self.inputs_dosis_via = []
        estilo_tabla = """
            QLineEdit {
                border: none;
                background: white;
                color: black;
                selection-background-color: #cce8ff;
                selection-color: black;
            }
            QLineEdit[echoMode="0"] {
            }
        """

        self.lista_medicamentos = [
            "Atropina",
            "Bupivacaína",
            "Bupivacaína pesada",
            "Cefalotina",
            "Ceftriaxona",
            "Clindamicina",
            "Dexmedetomidina",
            "Diazepam",
            "Diclofenaco",
            "Dexametasona",
            "Efedrina",
            "Epinefrina",
            "Etomidato",
            "Fentanilo",
            "Flumazenil",
            "Glicopirrolato",
            "Ketamina",
            "Lidocaína",
            "Lidocaína/epinefrina",
            "Metamizol",
            "Metoclopramida",
            "Midazolam",
            "Morfina",
            "Nalbufina",
            "Naloxona",
            "Neostigmina",
            "Nitroglicerina",
            "Norepinefrina",
            "Ondansetrón",
            "Paracetamol",
            "Propofol",
            "Rocuronio",
            "Sevoflurano",
            "Succinilcolina",
            "Sugammadex",
            "Tramadol",
            "Vecuronio"
        ]

        self.alias_medicamentos = {
            "fenta": "Fentanilo",
            "fentan": "Fentanilo",
            "dex": "Dexmedetomidina",
            "dexa": "Dexametasona",
            "rocu": "Rocuronio",
            "vecu": "Vecuronio",
            "suxa": "Succinilcolina",
            "succi": "Succinilcolina",
            "lido": "Lidocaína",
            "bupi": "Bupivacaína",
            "bupi pesada": "Bupivacaína pesada",
            "ket": "Ketamina",
            "mid": "Midazolam",
            "prop": "Propofol",
            "ondan": "Ondansetrón",
            "metro": "Metoclopramida",
            "trama": "Tramadol",
            "morf": "Morfina",
        }

        self.dosis_sugeridas = {
            "Atropina": "mg IV",
            "Bupivacaína": "mL regional",
            "Bupivacaína pesada": "mg IT",
            "Cefalotina": "g IV",
            "Ceftriaxona": "g IV",
            "Clindamicina": "mg IV",
            "Dexmedetomidina": "µg IV",
            "Diazepam": "mg IV",
            "Diclofenaco": "mg IV",
            "Dexametasona": "mg IV",
            "Efedrina": "mg IV",
            "Epinefrina": "µg IV",
            "Etomidato": "mg IV",
            "Fentanilo": "µg IV",
            "Flumazenil": "mg IV",
            "Glicopirrolato": "mg IV",
            "Ketamina": "mg IV",
            "Lidocaína": "mg IV",
            "Lidocaína/epinefrina": "mL PD",
            "Metamizol": "g IV",
            "Metoclopramida": "mg IV",
            "Midazolam": "mg IV",
            "Morfina": "mg IV",
            "Nalbufina": "mg IV",
            "Naloxona": "mg IV",
            "Neostigmina": "mg IV",
            "Nitroglicerina": "µg IV",
            "Norepinefrina": "µg IV",
            "Ondansetrón": "mg IV",
            "Paracetamol": "g IV",
            "Propofol": "mg IV",
            "Rocuronio": "mg IV",
            "Sevoflurano": "% inhalado",
            "Succinilcolina": "mg IV",
            "Sugammadex": "mg IV",
            "Tramadol": "mg IV",
            "Vecuronio": "mg IV",
        }

        self.botones_medicamentos = []
        self.marcas_medicamentos = []

        self.setMinimumSize(1400, 1120)
        self.cuadricula_sv = CuadriculaSV(self)
        self.scroll_cuadricula = QScrollArea(self)
        self.scroll_cuadricula.setWidgetResizable(False)
        self.scroll_cuadricula.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_cuadricula.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_cuadricula.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_cuadricula.setLineWidth(0)
        self.scroll_cuadricula.setMidLineWidth(0)
        self.scroll_cuadricula.viewport().setStyleSheet("background: transparent; border: none;")
        self.scroll_cuadricula.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:horizontal {
                background: transparent;
                height: 8px;
                margin: 0px 18px 0px 18px;
            }

            QScrollBar::handle:horizontal {
                background: rgba(90, 90, 90, 110);
                border-radius: 4px;
                min-width: 60px;
            }

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                width: 0px;
            }

            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
            }
        """)
        self.scroll_cuadricula.setWidget(self.cuadricula_sv)

        self.borde_izq_sv = QWidget(self)
        self.borde_inf_sv = QWidget(self)
        self.borde_der_sv = QWidget(self)

        self.borde_izq_ag = QWidget(self)
        self.borde_der_ag = QWidget(self)
        self.borde_sup_ag = QWidget(self)
        self.borde_inf_ag = QWidget(self)

        for borde in [
            self.borde_izq_sv,
            self.borde_der_sv,
            self.borde_inf_sv,
            self.borde_izq_ag,
            self.borde_der_ag,
            self.borde_sup_ag,
            self.borde_inf_ag
        ]:
            borde.setStyleSheet("background-color: black;")

        self.lbl_velocidad_sv = QLabel("Vel", self)
        self.lbl_velocidad_sv.setStyleSheet("color: black; font-size: 9px;")
        self.lbl_velocidad_sv.adjustSize()

        for letra in self.filas_meds:
            inp_med = QLineEdit(self)
            inp_med.setFrame(False)
            inp_med.setStyleSheet(estilo_tabla)
            inp_med.setCompleter(self.crear_completer_medicamentos())

            inp_dosis = LineEditConSufijo(self)
            inp_dosis.setFrame(False)
            inp_dosis.setStyleSheet(estilo_tabla)

            btn_med = QPushButton(letra, self)
            btn_med.setFixedSize(18, 18)
            btn_med.setVisible(False)
            btn_med.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: black;
                    border: 1px solid black;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #eeeeee;
                }
            """)

            btn_med.clicked.connect(
                lambda _, l=letra: self.registrar_marca_medicamento(l)
            )

            inp_med.textChanged.connect(
                lambda texto, b=btn_med: b.setVisible(bool(texto.strip()))
            )

            pal = inp_dosis.palette()
            pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("gray"))
            inp_dosis.setPalette(pal)

            inp_med.editingFinished.connect(
                lambda campo_med=inp_med, campo_dosis=inp_dosis:
                self.preparar_sugerencia_dosis(campo_med, campo_dosis)
            )

            inp_dosis.textEdited.connect(
                lambda _, campo=inp_dosis: self.aplicar_normalizacion(campo)
            )

            self.inputs_medicamentos.append(inp_med)
            self.inputs_dosis_via.append(inp_dosis)
            self.botones_medicamentos.append(btn_med)

        self.contenedor_tipo_anestesia = QWidget(self)
        layout_tipo = QVBoxLayout(self.contenedor_tipo_anestesia)
        layout_tipo.setContentsMargins(12, 24, 10, 10)
        layout_tipo.setSpacing(8)

        self.rb_anestesia_general = QRadioButton("GENERAL")
        self.rb_anestesia_regional = QRadioButton("REGIONAL")
        self.rb_anestesia_combinada = QRadioButton("COMBINADA")

        self.stack_tecnica = QStackedWidget()

        # GENERAL
        pagina_general = QWidget()
        layout_general = QVBoxLayout(pagina_general)
        layout_general.setContentsMargins(28, 8, 4, 4)
        layout_general.setSpacing(6)

        self.rb_general_balanceada = QRadioButton("Balanceada")
        self.rb_general_tiva = QRadioButton("TIVA")
        self.rb_general_inhalada = QRadioButton("Inhalada")

        self.grupo_tecnica_general = QButtonGroup(self)
        self.grupo_tecnica_general.addButton(self.rb_general_balanceada)
        self.grupo_tecnica_general.addButton(self.rb_general_tiva)
        self.grupo_tecnica_general.addButton(self.rb_general_inhalada)

        layout_general.addWidget(self.rb_general_balanceada)
        layout_general.addWidget(self.rb_general_tiva)
        layout_general.addWidget(self.rb_general_inhalada)

        # REGIONAL
        pagina_regional = QWidget()
        layout_regional = QVBoxLayout(pagina_regional)
        layout_regional.setContentsMargins(28, 8, 4, 4)
        layout_regional.setSpacing(6)

        self.rb_regional_neuroaxial = QRadioButton("Bloqueo neuroaxial")
        self.rb_regional_periferico = QRadioButton("Bloqueo periférico")
        self.rb_regional_local = QRadioButton("Local")

        # =========================
        # DETALLE REGIONAL
        # =========================
        self.lbl_detalle_regional = QLabel("Detalle regional")

        self.rb_intratecal = QRadioButton("Intratecal")
        self.rb_peridural = QRadioButton("Peridural")
        
        self.rb_intratecal.setStyleSheet("margin-left: 18px;")
        self.rb_peridural.setStyleSheet("margin-left: 18px;")

        self.grupo_neuroaxial = QButtonGroup(self)
        self.grupo_neuroaxial.addButton(self.rb_intratecal)
        self.grupo_neuroaxial.addButton(self.rb_peridural)

        self.input_nivel_puncion = QLineEdit()
        self.input_nivel_puncion.setPlaceholderText("Nivel punción")
        self.input_tipo_aguja = QLineEdit()
        self.input_tipo_aguja.setPlaceholderText("Tipo de aguja")

        self.input_anestesico_local = QLineEdit()
        self.input_anestesico_local.setPlaceholderText("Anestésico local")

        self.input_nivel_puncion.setContentsMargins(0, 0, 0, 0)
        self.input_tipo_aguja.setContentsMargins(0, 0, 0, 0)
        self.input_anestesico_local.setContentsMargins(0, 0, 0, 0)

        self.rb_troncular = QRadioButton("Troncular")
        self.rb_plexo = QRadioButton("Plexo")

        self.grupo_periferico = QButtonGroup(self)
        self.grupo_periferico.addButton(self.rb_troncular)
        self.grupo_periferico.addButton(self.rb_plexo)

        self.input_sitio_bloqueo = QLineEdit()
        self.input_sitio_bloqueo.setPlaceholderText("Sitio / plexo")

        self.input_nivel_puncion.setContentsMargins(0, 0, 0, 0)
        self.input_tipo_aguja.setContentsMargins(0, 0, 0, 0)
        self.input_anestesico_local.setContentsMargins(0, 0, 0, 0)

        for inp in [
            self.input_nivel_puncion,
            self.input_tipo_aguja,
            self.input_anestesico_local,
            self.input_sitio_bloqueo
        ]:
            inp.setFixedSize(170, 24)
            inp.setStyleSheet("""
                QLineEdit {
                    background-color: transparent;
                    color: black;
                    border: none;
                    border-bottom: 1px solid #666;
                    font-size: 10px;
                    padding-left: 2px;
                    padding-bottom: 1px;
                }
            """)

        self.grupo_tecnica_regional = QButtonGroup(self)

        self.grupo_tecnica_regional = QButtonGroup(self)
        self.grupo_tecnica_regional.addButton(self.rb_regional_neuroaxial)
        self.grupo_tecnica_regional.addButton(self.rb_regional_periferico)
        self.grupo_tecnica_regional.addButton(self.rb_regional_local)

        layout_regional.addWidget(self.rb_regional_neuroaxial)

        sub_neuro = QVBoxLayout()
        sub_neuro.setContentsMargins(24, 4, 0, 16)
        sub_neuro.setSpacing(10)

        sub_neuro.addWidget(self.rb_intratecal)
        sub_neuro.addWidget(self.rb_peridural)

        layout_regional.addLayout(sub_neuro)

        layout_regional.addWidget(self.rb_regional_periferico)

        sub_periferico = QVBoxLayout()
        sub_periferico.setContentsMargins(24, 4, 0, 6)
        sub_periferico.setSpacing(5)

        sub_periferico.addWidget(self.rb_troncular)
        sub_periferico.addWidget(self.rb_plexo)
        sub_periferico.addWidget(self.input_sitio_bloqueo)

        layout_regional.addLayout(sub_periferico)

        layout_regional.addWidget(self.rb_regional_local)

        # COMBINADA
        pagina_combinada = QWidget()
        layout_combinada = QVBoxLayout(pagina_combinada)
        layout_combinada.setContentsMargins(28, 8, 4, 4)
        layout_combinada.setSpacing(6)

        self.rb_combinada_general_regional = QRadioButton("General + regional")
        self.rb_combinada_general_periferico = QRadioButton("General + bloqueo periférico")

        self.grupo_tecnica_combinada = QButtonGroup(self)
        self.grupo_tecnica_combinada.addButton(self.rb_combinada_general_regional)
        self.grupo_tecnica_combinada.addButton(self.rb_combinada_general_periferico)

        layout_combinada.addWidget(self.rb_combinada_general_regional)
        layout_combinada.addWidget(self.rb_combinada_general_periferico)

        self.stack_tecnica.addWidget(pagina_general)
        self.stack_tecnica.addWidget(pagina_regional)
        self.stack_tecnica.addWidget(pagina_combinada)

        layout_tipo.addWidget(self.rb_anestesia_general)
        layout_tipo.addWidget(self.rb_anestesia_regional)
        layout_tipo.addWidget(self.rb_anestesia_combinada)
        layout_tipo.addWidget(self.stack_tecnica)
        layout_tipo.addStretch()

        self.grupo_tipo_anestesia = QButtonGroup(self)
        self.grupo_tipo_anestesia.addButton(self.rb_anestesia_general)
        self.grupo_tipo_anestesia.addButton(self.rb_anestesia_regional)
        self.grupo_tipo_anestesia.addButton(self.rb_anestesia_combinada)

        self.rb_anestesia_general.setChecked(True)
        self.rb_general_balanceada.setChecked(True)

        self.rb_anestesia_general.toggled.connect(self.actualizar_tecnica_anestesica)
        self.rb_anestesia_regional.toggled.connect(self.actualizar_tecnica_anestesica)
        self.rb_anestesia_combinada.toggled.connect(self.actualizar_tecnica_anestesica)
        self.rb_regional_neuroaxial.toggled.connect(self.actualizar_detalle_regional)
        self.rb_regional_periferico.toggled.connect(self.actualizar_detalle_regional)
        self.rb_regional_local.toggled.connect(self.actualizar_detalle_regional)

        self.rb_intratecal.toggled.connect(self.update)
        self.rb_peridural.toggled.connect(self.update)
        self.rb_troncular.toggled.connect(self.update)
        self.rb_plexo.toggled.connect(self.update)

        # =========================
        # CASOS OBSTÉTRICOS
        # =========================

        self.contenedor_obstetricos = QWidget(self)

        self.chk_caso_obstetrico = QCheckBox("Activar", self.contenedor_obstetricos)
        self.chk_caso_obstetrico.setChecked(False)
        self.chk_caso_obstetrico.setStyleSheet("""
            QCheckBox {
                color: black;
                background-color: transparent;
                font-size: 10px;
                font-weight: bold;
                padding-left: 2px;
            }
        """)

        layout_obs = QVBoxLayout(self.contenedor_obstetricos)
        layout_obs.setContentsMargins(10, 28, 10, 10)
        layout_obs.setSpacing(8)

        # Expulsión placenta
        fila_placenta = QHBoxLayout()
        fila_placenta.setContentsMargins(0, 14, 0, 0)

        self.rb_placenta_espontanea = QRadioButton("Espontánea")
        self.rb_placenta_manual = QRadioButton("Manual")

        self.grupo_placenta = QButtonGroup(self)
        self.grupo_placenta.addButton(self.rb_placenta_espontanea)
        self.grupo_placenta.addButton(self.rb_placenta_manual)

        fila_placenta.addWidget(QLabel("Expulsión placenta:"))
        fila_placenta.addWidget(self.rb_placenta_espontanea)
        fila_placenta.addWidget(self.rb_placenta_manual)
        fila_placenta.addStretch()

        layout_obs.addLayout(fila_placenta)

        # RN
        fila_rn1 = QHBoxLayout()

        self.chk_rn_masculino = QCheckBox("♂")
        self.chk_rn_femenino = QCheckBox("♀")
        self.chk_rn_indeterminado = QCheckBox("Indeterminado")

        self.grupo_sexo_rn = QButtonGroup(self)
        self.grupo_sexo_rn.setExclusive(True)
        self.grupo_sexo_rn.addButton(self.chk_rn_masculino)
        self.grupo_sexo_rn.addButton(self.chk_rn_femenino)
        self.grupo_sexo_rn.addButton(self.chk_rn_indeterminado)

        for chk in [self.chk_rn_masculino, self.chk_rn_femenino]:
            chk.setStyleSheet("""
                QCheckBox {
                    color: black;
                    background-color: transparent;
                    font-size: 13px;
                    font-weight: bold;
                }
            """)

        self.input_rn_peso = LineEditConSufijo()
        self.input_rn_peso.setPlaceholderText("kg")
        self.input_rn_peso.setSufijoSugerido("kg")
        self.input_rn_peso.editingFinished.connect(
            lambda: self.normalizar_sufijo_lineedit(self.input_rn_peso, "kg")
        )

        self.input_rn_talla = LineEditConSufijo()
        self.input_rn_talla.setPlaceholderText("cm")
        self.input_rn_talla.setSufijoSugerido("cm")
        self.input_rn_talla.editingFinished.connect(
            lambda: self.normalizar_sufijo_lineedit(self.input_rn_talla, "cm")
        )

        for inp in [
            self.input_rn_peso,
            self.input_rn_talla
        ]:
            inp.setFixedWidth(80)

        fila_rn1.addWidget(QLabel("RN"))
        fila_rn1.addWidget(self.chk_rn_masculino)
        fila_rn1.addWidget(self.chk_rn_femenino)
        fila_rn1.addWidget(self.chk_rn_indeterminado)
        fila_rn1.addWidget(self.input_rn_peso)
        fila_rn1.addWidget(self.input_rn_talla)
        fila_rn1.addStretch()

        layout_obs.addLayout(fila_rn1)

        # Apgar
        fila_apgar = QHBoxLayout()

        self.input_apgar_1 = QLineEdit()
        self.input_apgar_5 = QLineEdit()
        self.input_apgar_10 = QLineEdit()

        for inp in [
            self.input_apgar_1,
            self.input_apgar_5,
            self.input_apgar_10
        ]:
            inp.setFixedWidth(45)

        fila_apgar.addWidget(QLabel("Apgar"))
        fila_apgar.addWidget(QLabel("1 min"))
        fila_apgar.addWidget(self.input_apgar_1)

        fila_apgar.addWidget(QLabel("5 min"))
        fila_apgar.addWidget(self.input_apgar_5)

        fila_apgar.addWidget(QLabel("10 min"))
        fila_apgar.addWidget(self.input_apgar_10)

        fila_apgar.addStretch()

        layout_obs.addLayout(fila_apgar)

        # Estado al salir
        self.input_estado_rn = QLineEdit()
        self.input_estado_rn.setPlaceholderText(
            "Estado general al salir del quirófano"
        )

        layout_obs.addWidget(self.input_estado_rn)

        self.contenedor_obstetricos.setStyleSheet("""
            QWidget {
                background-color: transparent;
                color: black;
                font-size: 10px;
            }

            QLineEdit {
                background-color: white;
                border: 1px solid #999;
                padding-left: 3px;
                height: 18px;
            }

            QRadioButton {
                spacing: 4px;
            }
        """)

        self.actualizar_tecnica_anestesica()
        self.actualizar_detalle_regional()

    def obtener_total_columnas_dibujo(self):
        columnas_minimas = 36

        cols_sv = [d.get("col", 0) for d in self.datos_sv]
        cols_temp = [d.get("col", 0) for d in self.datos_temp]
        cols_resp = [d.get("col", 0) for d in self.datos_resp]

        max_col = max(cols_sv + cols_temp + cols_resp + [columnas_minimas - 1])

        return max(columnas_minimas, max_col + 1)
            
    def normalizar_unidades(self, texto):
        return (
            texto.replace("MCG", "µg")
                .replace("mcg", "µg")
                .replace("Mcg", "µg")
                .replace("uG", "µg")
                .replace("ug", "µg")
        )



    def cambiar_velocidad_simulacion(self, texto):
        mapa = {
            "1x": 2000,
            "2x": 1000,
            "5x": 400,
            "10x": 200,
        }

        self.velocidad_sim_ms = mapa.get(texto, 2000)
        self.timer_sv.setInterval(self.velocidad_sim_ms)

    def posicionar_botones_eventos(self, x0, y1):
        x_boton = x0 - 105
        paso = 18
        n = len(self.botones_eventos)

        # subir ligeramente los eventos para dar espacio
        y_inicio = y1 - (n - 1) * paso - 10

        for i, btn in enumerate(self.botones_eventos):
            y = y_inicio + i * paso
            btn.setGeometry(int(x_boton), int(y - 10), 95, 20)
            btn.raise_()

        # === POSICIÓN DEL TÍTULO EVENTOS ===
        y_eventos = y1 - 118
        x_eventos = x0 - 105

        # botón alineado a la derecha del texto
        self.btn_deshacer.setGeometry(
            int(x_eventos + 55),   # ajustable
            int(y_eventos - 14),   # misma altura visual
            28,
            22
        )
        self.btn_deshacer.raise_()
            
    def valor_a_y(self, valor, y0, y1):
        vmin = 40
        vmax = 240
        valor = max(vmin, min(vmax, valor))
        proporcion = (valor - vmin) / (vmax - vmin)
        return y1 - proporcion * (y1 - y0)

    def temperatura_a_y(self, valor, y0, y1):
        # Escala visual para temperatura dentro de la misma gráfica
        vmin = 34.0
        vmax = 40.0
        valor = max(vmin, min(vmax, valor))
        proporcion = (valor - vmin) / (vmax - vmin)
        return y1 - proporcion * (y1 - y0)

    def tiempo_a_x(self, tiempo_min, x0, ancho_col):
        indice = (tiempo_min // 5) - 1
        return x0 + indice * ancho_col + ancho_col / 2

    def dibujar_flecha(self, painter, x, y, direccion="arriba", tamaño=12):
        if direccion == "arriba":
            puntos = QPolygonF([
                QPointF(x, y - tamaño),
                QPointF(x - 5, y),
                QPointF(x + 5, y),
            ])
        else:
            puntos = QPolygonF([
                QPointF(x, y + tamaño),
                QPointF(x - 5, y),
                QPointF(x + 5, y),
            ])
        painter.drawPolygon(puntos)

    def dibujar_triangulo(self, painter, x, y, tamaño=10):
        puntos = QPolygonF([
            QPointF(x, y - tamaño),
            QPointF(x - 6, y + 4),
            QPointF(x + 6, y + 4),
        ])
        painter.drawPolygon(puntos)

    def map_bp_to_y(self, value):
        value = max(self.bp_min, min(self.bp_max, value))

        total_range = self.bp_max - self.bp_min
        pixels_per_unit = (self.graph_bottom - self.graph_top) / total_range

        y = self.graph_bottom - ((value - self.bp_min) * pixels_per_unit)
        return int(y)

    def get_column_left(self, time_str):
        if time_str in self.time_columns:
            index = self.time_columns.index(time_str)
            return int(self.graph_left + index * self.column_width)
        return None

    def get_x_for_time(self, time_str):
        col_left = self.get_column_left(time_str)
        if col_left is None:
            return None
        return int(col_left)



    def draw_grid(self, painter):
        left = self.graph_left
        right = self.graph_right
        top = self.graph_top
        bottom = self.graph_bottom

        # Borde exterior
        border_pen = QPen()
        border_pen.setWidth(1)
        painter.setPen(border_pen)
        painter.drawRect(left, top, right - left, bottom - top)

        painter.setFont(QFont("Arial", 8))

        # Líneas horizontales cada 10 mmHg (cuadros)
        for i, value in enumerate(range(self.bp_min, self.bp_max + 1, 10)):
            y = int(bottom - i * self.cell_size)

            pen = QPen()
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(left, y, right, y)

            if value % 20 == 0:
                painter.drawText(left - 35, y + 4, str(value))

        # Líneas verticales en bordes de columna
        for i in range(self.total_columns + 1):
            x = int(left + i * self.column_width)

            pen = QPen()
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(x, top, x, bottom)

        # Etiquetas de minuto centradas dentro de cada celda
        for i, minute in enumerate(self.time_columns):
            cell_left = int(left + i * self.column_width)
            x_center = int(cell_left + self.column_width / 2)

            if minute in {"15", "30", "45"}:
                painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            else:
                painter.setFont(QFont("Arial", 8))

            painter.drawText(x_center - 10, bottom + 20, minute)

        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(x_center - 8, bottom + 15, minute)

    def draw_ta_data(self, painter):
        pen = QPen()
        pen.setWidth(2)
        painter.setPen(pen)

        for minuto, sistolica, diastolica in self.ta_data:
            x = self.get_x_for_time(minuto)
            if x is None:
                continue

            y_sys = self.map_bp_to_y(sistolica)
            y_dia = self.map_bp_to_y(diastolica)

            self.draw_ta_marker(painter, x, y_sys, y_dia)

    def get_fc_x_for_time(self, time_str):
        col_left = self.get_column_left(time_str)
        if col_left is None:
            return None
        return int(col_left + self.column_width / 2)

    def map_fc_to_y_center(self, value):
        value = max(self.bp_min, min(self.bp_max, value))

        # cuántos cuadros arriba del mínimo
        steps_from_min = round((value - self.bp_min) / 10)

        y_line = self.graph_bottom - (steps_from_min * self.cell_size)

        # mover al centro del cuadro
        return int(y_line - self.cell_size / 2)


    def draw_fc_data(self, painter):
        pen = QPen()
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.SolidPattern)

        for minuto, fc in self.fc_data:
            x = self.get_fc_x_for_time(minuto)
            if x is None:
                continue

            y = self.map_fc_to_y_center(fc)
            self.draw_fc_point(painter, x, y)

    def draw_agent_row(self, painter, label, data, y):
        painter.setFont(QFont("Arial", 8))
        painter.drawText(self.graph_left - 60, y + 4, label)

        for minute, value in data:
            x = self.get_fc_x_for_time(minute)
            if x is None:
                continue

            text = str(value)
            painter.drawText(x - 10, y + 4, text)

    def draw_agents(self, painter):
        top = self.graph_top - 140
        row_height = 32

        y_spo2 = top + 20
        y_fio2 = top + 52
        y_flow = top + 84
        y_sevo = top + 116

        self.draw_agent_row(painter, "SpO2", self.spo2_data, y_spo2)
        self.draw_agent_row(painter, "FiO2", self.fio2_data, y_fio2)
        self.draw_agent_row(painter, "Flujo", self.flow_data, y_flow)
        self.draw_agent_row(painter, "Sevo", self.sevo_data, y_sevo)

    def draw_agents_grid(self, painter):
        left = self.graph_left
        right = self.graph_right

        top = self.graph_top - 140
        bottom = self.graph_top - 10

        # Borde exterior
        pen = QPen()
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(left, top, right - left, bottom - top)

        # Líneas horizontales internas (4 filas)
        row_height = (bottom - top) / 4

        for i in range(1, 4):
            y = int(top + i * row_height)
            painter.drawLine(left, y, right, y)

        # Líneas verticales alineadas con las columnas
        for i in range(self.total_columns + 1):
            x = int(left + i * self.column_width)
            painter.drawLine(x, top, x, bottom)

        # Etiqueta lateral AGENTES
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        painter.drawText(left - 70, top - 8, "AGENTES")

    def posicionar_inputs_tiempos(self, x0, y0, y1):
        x_input = x0 - 48

        paso = 18
        n = len(self.inputs_tiempos)

        y_inicio = y1 - (n - 1) * paso

        for i, inp in enumerate(self.inputs_tiempos):
            y = y_inicio + i * paso

            inp.setGeometry(
                int(x_input),
                int(y - 10),
                44,
                20
            )

    def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillRect(self.rect(), QColor("white"))

            margen_izq = 110
            margen_sup = 120

            x0 = margen_izq
            y0 = margen_sup

            ancho_col = 35
            ancho_scroll = int(36 * ancho_col) + 2
            alto_barra = self.scroll_cuadricula.horizontalScrollBar().sizeHint().height()
            alto_scroll = self.cuadricula_sv.height() + alto_barra + 8

            y_scroll_top = y0 - 96

            # =========================
            # BOTONES SIMULACIÓN
            # =========================
            self.posicionar_botones_simulacion(x0, y_scroll_top)

            # =========================
            # SCROLL HORIZONTAL DE SV
            # =========================
            self.scroll_cuadricula.setGeometry(
                int(x0),
                int(y_scroll_top),
                int(ancho_scroll),
                int(alto_scroll)
            )
            self.scroll_cuadricula.raise_()

            # =========================
            # BORDES FIJOS AGENTES Y SV
            # =========================

            y_ag_top = y_scroll_top
            y_ag_bottom = y_ag_top + 80

            y_sv_top = y_scroll_top + 96
            y_sv_bottom = y_sv_top + 380

            # ---- SV ----

            self.borde_izq_sv.setGeometry(
                int(x0),
                int(y_sv_top),
                2,
                380
            )

            self.borde_der_sv.setGeometry(
                int(x0 + ancho_scroll - 2),
                int(y_sv_top),
                2,
                380
            )

            self.borde_inf_sv.setGeometry(
                int(x0),
                int(y_sv_bottom - 1),
                int(ancho_scroll),
                2
            )

            # ---- AGENTES ----

            self.borde_sup_ag.setGeometry(
                int(x0),
                int(y_ag_top),
                int(ancho_scroll),
                2
            )

            self.borde_inf_ag.setGeometry(
                int(x0),
                int(y_ag_bottom - 1),
                int(ancho_scroll),
                2
            )

            self.borde_izq_ag.setGeometry(
                int(x0),
                int(y_ag_top),
                2,
                80
            )

            self.borde_der_ag.setGeometry(
                int(x0 + ancho_scroll - 2),
                int(y_ag_top),
                2,
                80
            )

            # Traer encima del scroll
            for borde in [
                self.borde_izq_sv,
                self.borde_der_sv,
                self.borde_inf_sv,
                self.borde_sup_ag,
                self.borde_inf_ag,
                self.borde_izq_ag,
                self.borde_der_ag
            ]:
                borde.raise_()

            # Bordes fijos de la cuadrícula, NO se mueven con el scroll
            y_sv_top = y_scroll_top + 96
            y_sv_bottom = y_sv_top + 380
            y_ag_top = y_scroll_top
            y_ag_bottom = y_ag_top + 80

            self.borde_izq_sv.setGeometry(
                int(x0),
                int(y_sv_top),
                2,
                int(380)
            )

            self.borde_inf_sv.setGeometry(
                int(x0),
                int(y_sv_bottom - 1),
                int(ancho_scroll),
                2
            )

            self.borde_izq_sv.raise_()
            self.borde_inf_sv.raise_()

            # Línea inferior limpia de la cuadrícula, sin borde del scroll
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.drawLine(
                int(x0),
                int(y_scroll_top + self.cuadricula_sv.height() - 1),
                int(x0 + ancho_scroll),
                int(y_scroll_top + self.cuadricula_sv.height() - 1)
            )

            # =========================
            # ETIQUETAS FIJAS IZQUIERDAS
            # =========================
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))

            painter.drawText(x0 - 70, y_scroll_top + 18, "Sevo")
            painter.drawText(x0 - 70, y_scroll_top + 38, "Flujo")
            painter.drawText(x0 - 70, y_scroll_top + 58, "FiO₂")
            painter.drawText(x0 - 70, y_scroll_top + 78, "SpO₂")

            y_sv_top = y_scroll_top + 96
            y_sv_bottom = y_sv_top + 380

            painter.drawText(x0 - 105, y_sv_top + 240, "EVENTOS")
            y_tiempo = y_sv_bottom + 34

            painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            painter.drawText(10, y_tiempo, "TIEMPO")

            painter.setFont(QFont("Arial", 8))
            for valor in [40, 60, 80, 100, 120, 140, 160, 180, 200, 220, 240]:
                y_val = self.valor_a_y(valor, y_sv_top, y_sv_bottom)
                painter.drawText(x0 - 28, int(y_val + 4), str(valor))

            # =========================
            # TABLA DE MEDICAMENTOS Y TÉCNICA
            # =========================
            y_tabla_top = y_scroll_top + alto_scroll + 28

            # Tus funciones suman internamente +28 px aprox,
            # por eso mandamos y_tabla_top - 28
            y_ref_tabla = y_tabla_top - 28

            self.posicionar_tabla_medicamentos(x0, y_ref_tabla)
            self.draw_tabla_medicamentos(painter, y_ref_tabla)

            self.posicionar_botones_eventos(x0, y_sv_bottom)
            self.btn_deshacer.raise_()

            self.draw_eventos_abajo_sv(painter, x0, y_sv_bottom, ancho_col)


    def aplicar_estilo_boton_evento(self, btn, estado):
        if estado == "activo":
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    border: none;
                    background-color: transparent;
                    color: black;
                    font-size: 11px;
                    padding-left: 0px;
                    font-weight: bold;
                }
            """)
        elif estado == "usado":
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    border: none;
                    background-color: transparent;
                    color: #7a7a7a;
                    font-size: 11px;
                    padding-left: 0px;
                }
            """)
        else:  # bloqueado
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    border: none;
                    background-color: transparent;
                    color: #b5b5b5;
                    font-size: 11px;
                    padding-left: 0px;
                }
            """)

    def actualizar_estado_botones(self):
        registrados = {e["numero"] for e in self.eventos_registrados}

        for i, btn in enumerate(self.botones_eventos, start=1):
            numero_txt = str(i)

            # Si ya fue registrado
            if numero_txt in registrados:
                btn.setEnabled(False)
                self.aplicar_estilo_boton_evento(btn, "usado")
                continue

            # Evento 1
            if i == 1:
                activo = "1" not in registrados
                btn.setEnabled(activo)
                self.aplicar_estilo_boton_evento(btn, "activo" if activo else "usado")
                continue

            # Los demás dependen del previo
            previo_txt = str(i - 1)
            activo = previo_txt in registrados

            btn.setEnabled(activo)
            if activo:
                self.aplicar_estilo_boton_evento(btn, "activo")
            else:
                self.aplicar_estilo_boton_evento(btn, "bloqueado")



    def minutos_desde_inicio(self, hora_evento):
        if self.hora_base_rejilla is None:
            return 0

        delta = hora_evento - self.hora_base_rejilla
        return int(delta.total_seconds() // 60)
        
    def x_columna_tiempo(self, minutos, x0, ancho_col):
        columna = minutos // 5
        return x0 + columna * ancho_col + ancho_col / 2

    def draw_eventos_abajo_sv(self, painter, x0, y1, ancho_col):
        if not self.eventos_registrados:
            return

        from collections import defaultdict

        eventos_por_columna = defaultdict(list)

        for evento in self.eventos_registrados:
            minutos = self.minutos_desde_inicio(evento["hora"])
            columna = minutos // 5

            if columna < 0:
                columna = 0
            if columna > 35:
                columna = 35

            eventos_por_columna[columna].append(evento["numero"])

        y_texto = y1 + 34
        painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))

        for columna, numeros in eventos_por_columna.items():
            x_centro = x0 + columna * ancho_col + ancho_col / 2
            numeros_ordenados = sorted(numeros, key=int)
            texto = ",".join(numeros_ordenados)

            rect = painter.fontMetrics().boundingRect(texto)
            x_texto = x_centro - rect.width() / 2

            painter.drawText(int(x_texto), int(y_texto), texto)

    def nombre_evento(self, numero_evento):
        texto = self.eventos_qx[numero_evento - 1]
        return texto.split(". ", 1)[1]        
    
    def registrar_evento(self, numero_evento):
        hora_actual = datetime.now()

        if numero_evento == 1:
            self.hora_inicio = hora_actual

            self.hora_base_rejilla = hora_actual.replace(
                minute=0,
                second=0,
                microsecond=0
            )

        self.eventos_registrados.append({
            "hora": hora_actual,
            "numero": str(numero_evento)
        })

        self.actualizar_estado_botones()
        self.update()
    
    def deshacer_ultimo_evento(self):
        if not self.eventos_registrados:
            return

        ultimo = self.eventos_registrados.pop()
        self.actualizar_estado_botones()
        self.update()

    def posicionar_tabla_medicamentos(self, x0, y1):
        x_letra = 18
        x_med = 42
        x_dosis = 250

        y_tabla = y1 + 42
        alto_header = 22
        alto_fila = 24

        # Posición del bloque "Tipo de anestesia" a la derecha de medicamentos
        x_tipo = 390
        y_tipo = y_tabla - 14   # MISMO Y QUE EL RECTÁNGULO
        
        w_tipo = 420
        h_tipo = 260

        self.x_tipo_panel = x_tipo
        self.y_tipo_panel = y_tipo

        self.contenedor_tipo_anestesia.setGeometry(x_tipo + 5, y_tipo + 5, 420, 260)
        self.contenedor_tipo_anestesia.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
            QRadioButton {
                color: black;
                background-color: white;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        self.contenedor_tipo_anestesia.show()
        self.contenedor_tipo_anestesia.raise_()

        # =========================
        # PANEL OBSTÉTRICO
        # =========================

        x_obs = x_tipo
        y_obs = y_tipo + h_tipo + 22

        w_obs = 420
        h_obs = 170

        self.chk_caso_obstetrico.setGeometry(
            12,
            4,
            90,
            20
        )
        self.chk_caso_obstetrico.show()
        self.chk_caso_obstetrico.raise_()

        self.contenedor_obstetricos.setGeometry(
            x_obs + 5,
            y_obs + 5,
            w_obs - 10,
            h_obs - 10
        )

        self.contenedor_obstetricos.show()
        self.contenedor_obstetricos.raise_()

        # Inputs neuroaxiales manuales, dentro del panel
        x_input = 175
        y_input = 88
        w_input = 155
        h_input = 20
        espacio = 24

        for inp in [
            self.input_nivel_puncion,
            self.input_tipo_aguja,
            self.input_anestesico_local
        ]:
            if inp.parent() is not self.contenedor_tipo_anestesia:
                inp.setParent(self.contenedor_tipo_anestesia)

        self.input_nivel_puncion.setGeometry(x_input, y_input, w_input, h_input)
        self.input_tipo_aguja.setGeometry(x_input, y_input + espacio, w_input, h_input)
        self.input_anestesico_local.setGeometry(x_input, y_input + espacio * 2, w_input, h_input)

        for inp in [
            self.input_nivel_puncion,
            self.input_tipo_aguja,
            self.input_anestesico_local
        ]:
            inp.raise_()

        for i in range(len(self.filas_meds)):
            y = y_tabla - 14 + alto_header + i * alto_fila

            # Más angosto para no tapar la línea divisoria
            self.botones_medicamentos[i].setGeometry(x_letra + 1, y + 3, 18, 18)
            self.inputs_medicamentos[i].setGeometry(x_med + 2, y + 2, 188, 20)
            self.inputs_dosis_via[i].setGeometry(x_dosis + 2, y + 2, 114, 20)
            

    def draw_tabla_medicamentos(self, painter, y1):
        x_letra = 18
        x_med = 42
        x_dosis = 250

        w_letra = 20
        w_med = 200
        w_dosis = 130

        y_tabla = y1 + 42
        alto_header = 22
        alto_fila = 24
        total_filas = len(self.filas_meds)

        x0 = x_letra
        x1 = x0 + w_letra
        x2 = x1 + w_med
        x3 = x2 + w_dosis

        y0 = y_tabla - 14
        y1_tabla = y0 + alto_header + total_filas * alto_fila

        painter.setPen(QPen(Qt.GlobalColor.black, 1))

        # Borde exterior
        painter.drawRect(x0, y0, x3 - x0, y1_tabla - y0)

        # Verticales
        painter.drawLine(x1, y0, x1, y1_tabla)
        painter.drawLine(x2, y0, x2, y1_tabla)

        # Línea debajo del encabezado
        painter.drawLine(x0, y0 + alto_header, x3, y0 + alto_header)

        # Horizontales de filas
        for i in range(total_filas):
            y = y0 + alto_header + (i + 1) * alto_fila
            painter.drawLine(x0, y, x3, y)

        # Encabezados
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))

        # Rectángulos de cada celda de encabezado
        rect_meds = QRect(int(x1), int(y0), int(x2 - x1), int(alto_header))
        rect_dosis = QRect(int(x2), int(y0), int(x3 - x2), int(alto_header))

        # Dibujar texto centrado
        painter.drawText(rect_meds, Qt.AlignmentFlag.AlignCenter, "MEDICAMENTOS")
        painter.drawText(rect_dosis, Qt.AlignmentFlag.AlignCenter, "DOSIS/VIA")

        # Letras A-M
        painter.setFont(QFont("Arial", 8))

        for i, letra in enumerate(self.filas_meds):
            rect_letra = QRect(
                int(x0),
                int(y0 + alto_header + i * alto_fila),
                int(x1 - x0),
                int(alto_fila)
            )

            painter.drawText(rect_letra, Qt.AlignmentFlag.AlignCenter, letra)

        # =========================
        # MÉTODO Y TÉCNICA ANESTÉSICA
        # =========================
        x_tipo = 390
        y_tipo = y0
        w_tipo = 420
        h_tipo = 260

        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawRect(x_tipo, y_tipo, w_tipo, h_tipo)

        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(
            QRect(x_tipo, y_tipo, w_tipo, alto_header),
            Qt.AlignmentFlag.AlignCenter,
            "MÉTODO Y TÉCNICA ANESTÉSICA"
        )

        # =========================
        # CASOS OBSTÉTRICOS
        # =========================

        x_obs = x_tipo
        y_obs = y_tipo + h_tipo + 24

        w_obs = 420
        h_obs = 170

        # borde completo del recuadro obstétrico
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawRect(x_obs, y_obs, w_obs, h_obs)

        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(
            QRect(x_obs, y_obs + 4, w_obs, alto_header),
            Qt.AlignmentFlag.AlignCenter,
            "CASOS OBSTÉTRICOS"
        )

    def registrar_marca_medicamento(self, letra):
        if not any(e["numero"] == "1" for e in self.eventos_registrados):
            QMessageBox.warning(
                self,
                "Evento requerido",
                "Primero registra la llegada del paciente a quirófano."
            )
            return

        ahora = datetime.now()
        minutos = self.minutos_desde_inicio(ahora)
        col = minutos // 5

        if col < 0:
            col = 0

        if col >= self.cuadricula_sv.num_columnas:
            col = self.cuadricula_sv.num_columnas - 1

        self.marcas_medicamentos.append({
            "letra": letra,
            "col": col
        })

        self.cuadricula_sv.update()

    def draw_temperatura_simulada(self, painter):
        if not self.datos_temp:
            return

        ancho = self.width()
        alto = self.height()

        margen_izq = 110
        margen_der = 20
        margen_sup = 120

        alto_header_meds = 22
        alto_fila_meds = 24
        total_filas_meds = len(self.filas_meds)
        margen_inf = 60 + alto_header_meds + (total_filas_meds * alto_fila_meds) + 30

        x0 = margen_izq
        y0 = margen_sup
        x1 = ancho - margen_der
        y1 = alto - margen_inf

        ancho_grafica = x1 - x0
        num_columnas = self.obtener_total_columnas_dibujo()
        ancho_col = 35
        alto_scroll = 496
        ancho_grafica = num_columnas * ancho_col
        x1 = x0 + ancho_grafica

        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        for d in self.datos_temp:
            col = d["col"]
            temp = d["temp"]

            x = x0 + (col * ancho_col) + (ancho_col / 2)
            y = self.temperatura_a_y(temp, y0, y1)

            self.dibujar_triangulo(painter, x, y, tamaño=6)

    def normalizar_sufijo_lineedit(self, lineedit, sufijo):
        texto = lineedit.text().strip()

        if not texto:
            return

        if texto.lower().endswith(sufijo.lower()):
            return

        lineedit.setText(f"{texto} {sufijo}")

    def obtener_medicamentos_registrados(self):
        medicamentos = []

        for i, letra in enumerate(self.filas_meds):
            nombre = self.inputs_medicamentos[i].text().strip()
            dosis_via = self.inputs_dosis_via[i].text().strip()

            if nombre or dosis_via:
                medicamentos.append({
                    "fila": letra,
                    "medicamento": nombre,
                    "dosis_via": dosis_via
                })

        return medicamentos
    
    def agregar_dato_simulado(self):
        if self.columna_actual >= self.max_columnas:
            self.timer_sv.stop()
            self.btn_iniciar_sv.setEnabled(False)
            self.btn_pausar_sv.setEnabled(False)
            self.btn_reiniciar_sv.setEnabled(True)
            return

        if not self.datos_sv:
            fc_base = 78
            tas_base = 120
            tad_base = 80
            spo2_base = 98
            fio2_base = 50
            flujo_base = 2.0
            sevo_base = 2.0
        else:
            ultimo = self.datos_sv[-1]
            fc_base = ultimo["fc"]
            tas_base = ultimo["tas"]
            tad_base = ultimo["tad"]
            spo2_base = ultimo["spo2"]
            fio2_base = ultimo["fio2"]
            flujo_base = ultimo["flujo"]
            sevo_base = ultimo["sevo"]

        fc = max(45, min(140, fc_base + random.randint(-5, 5)))
        tas = max(80, min(180, tas_base + random.randint(-8, 8)))
        tad = max(40, min(110, tad_base + random.randint(-5, 5)))

        if tad >= tas:
            tad = tas - 10

        spo2 = max(88, min(100, spo2_base + random.randint(-1, 1)))
        fio2 = max(21, min(100, fio2_base + random.choice([-5, 0, 5])))
        flujo = max(0.5, min(10.0, round(flujo_base + random.choice([-0.5, 0, 0.5]), 1)))
        sevo = max(0.0, min(8.0, round(sevo_base + random.choice([-0.2, 0, 0.2]), 1)))

        self.datos_sv.append({
            "col": self.columna_actual,
            "fc": fc,
            "tas": tas,
            "tad": tad,
            "spo2": spo2,
            "fio2": fio2,
            "flujo": flujo,
            "sevo": sevo,
        })

        if not self.datos_resp:
            modo_base = "C"
        else:
            modo_base = self.datos_resp[-1]["modo"]

        # simulación simple
        if self.columna_actual < 8:
            modo = "C"
        elif self.columna_actual < 10:
            modo = "A"
        else:
            modo = "E"

        self.datos_resp.append({
            "col": self.columna_actual,
            "modo": modo
        })

        if self.columna_actual % 3 == 0:
            if not self.datos_temp:
                temp_base = 36.5
            else:
                temp_base = self.datos_temp[-1]["temp"]

            temp = round(max(35.0, min(38.5, temp_base + random.choice([-0.1, 0.0, 0.1]))), 1)

            self.datos_temp.append({
                "col": self.columna_actual,
                "temp": temp,
            })

        self.columna_actual += 1
        self.update()
        self.cuadricula_sv.update()

    
    def draw_sv_simulados(self, painter):
        if not self.datos_sv:
            return

        ancho = self.width()
        alto = self.height()

        margen_izq = 110
        margen_der = 20
        margen_sup = 120

        alto_header_meds = 22
        alto_fila_meds = 24
        total_filas_meds = len(self.filas_meds)
        margen_inf = 60 + alto_header_meds + (total_filas_meds * alto_fila_meds) + 30

        x0 = margen_izq
        y0 = margen_sup
        x1 = ancho - margen_der
        y1 = alto - margen_inf

        ancho_grafica = x1 - x0
        num_columnas = self.obtener_total_columnas_dibujo()
        ancho_col = 35
        ancho_grafica = num_columnas * ancho_col
        x1 = x0 + ancho_grafica

        for d in self.datos_sv:
            col = d["col"]

            x_linea_tiempo = x0 + (col * ancho_col)
            x_centro = x_linea_tiempo + (ancho_col / 2)

            y_tas = self.valor_a_y(d["tas"], y0, y1)
            y_tad = self.valor_a_y(d["tad"], y0, y1)
            y_fc = self.valor_a_y(d["fc"], y0, y1)

            self.draw_ta_marker(painter, x_linea_tiempo, y_tas, up=False)
            self.draw_ta_marker(painter, x_linea_tiempo, y_tad, up=True)
            self.draw_fc_point(painter, x_centro, y_fc)


    def draw_ta_marker(self, painter, x, y, up=True):
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if up:
            painter.drawLine(int(x), int(y), int(x - 4), int(y + 6))
            painter.drawLine(int(x), int(y), int(x + 4), int(y + 6))
        else:
            painter.drawLine(int(x), int(y), int(x - 4), int(y - 6))
            painter.drawLine(int(x), int(y), int(x + 4), int(y - 6))

    def draw_fc_point(self, painter, x, y):
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setBrush(QColor("black"))
        painter.drawEllipse(QPointF(x, y), 2, 2)

    def draw_agentes_simulados(self, painter):
        if not self.datos_sv:
            return

        ancho = self.width()
        alto = self.height()

        margen_izq = 110
        margen_der = 20
        margen_sup = 120

        alto_header_meds = 22
        alto_fila_meds = 24
        total_filas_meds = len(self.filas_meds)
        margen_inf = 60 + alto_header_meds + (total_filas_meds * alto_fila_meds) + 30

        x0 = margen_izq
        y0 = margen_sup
        x1 = ancho - margen_der

        ancho_grafica = x1 - x0
        num_columnas = self.obtener_total_columnas_dibujo()
        ancho_col = 35
        ancho_grafica = num_columnas * ancho_col
        x1 = x0 + ancho_grafica

        alto_fila_ag = 20
        alto_franja_minutos = 16

        y_ag_top = y0 - alto_franja_minutos - (alto_fila_ag * 4)

        y_sevo = y_ag_top + 15
        y_flujo = y_ag_top + 35
        y_fio2 = y_ag_top + 55
        y_spo2 = y_ag_top + 75

        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setFont(QFont("Arial", 8))

        for d in self.datos_sv:
            if not all(k in d for k in ("col", "spo2", "fio2", "flujo", "sevo")):
                continue

            col = d["col"]
            x = x0 + (col * ancho_col) + (ancho_col / 2)

            painter.drawText(int(x - 12), y_sevo, f'{d["sevo"]:.1f}')
            painter.drawText(int(x - 12), y_flujo, f'{d["flujo"]:.1f}')
            painter.drawText(int(x - 12), y_fio2, str(d["fio2"]))
            painter.drawText(int(x - 12), y_spo2, str(d["spo2"]))


    def iniciar_simulacion_sv(self):
        if self.columna_actual >= self.max_columnas:
            return

        self.agregar_dato_simulado()  # genera un dato inmediato

        self.timer_sv.start()
        self.btn_iniciar_sv.setEnabled(False)
        self.btn_pausar_sv.setEnabled(True)
        self.btn_reiniciar_sv.setEnabled(True)

    def pausar_simulacion_sv(self):
        self.timer_sv.stop()
        self.btn_iniciar_sv.setEnabled(True)
        self.btn_pausar_sv.setEnabled(False)

    def reiniciar_simulacion_sv(self):
        self.timer_sv.stop()

        self.datos_sv = []
        self.datos_temp = []
        self.datos_resp = []
        self.marcas_medicamentos = []

        self.columna_actual = 0

        self.btn_iniciar_sv.setEnabled(True)
        self.btn_pausar_sv.setEnabled(False)
        self.btn_reiniciar_sv.setEnabled(True)

        self.update()
        self.cuadricula_sv.update()

    def posicionar_botones_simulacion(self, x0, y_ag_top):
        y_botones = y_ag_top - 25
        x_inicio = x0 + 250
        separacion = 102

        self.btn_iniciar_sv.move(int(x_inicio), int(y_botones))
        self.btn_pausar_sv.move(int(x_inicio + separacion), int(y_botones))
        self.btn_reiniciar_sv.move(int(x_inicio + (2 * separacion)), int(y_botones))

        x_vel = int(x_inicio + (3 * separacion) + 10)
        self.lbl_velocidad_sv.move(x_vel, int(y_botones + 3))
        self.lbl_velocidad_sv.adjustSize()

        self.combo_velocidad_sv.move(x_vel + 28, int(y_botones))

    def aplicar_normalizacion(self, input_field):
        texto = input_field.text()
        nuevo = self.normalizar_unidades(texto)

        if texto == nuevo:
            return

        pos = input_field.cursorPosition()

        input_field.blockSignals(True)
        input_field.setText(nuevo)
        input_field.setCursorPosition(min(pos, len(nuevo)))
        input_field.blockSignals(False)

    def crear_completer_medicamentos(self):
        model = QStringListModel(self.lista_medicamentos, self)

        completer = QCompleter(self)
        completer.setModel(model)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        completer.setCompletionMode(QCompleter.CompletionMode.InlineCompletion)
        
        return completer
    
    def normalizar_medicamento(self, texto):
        t = texto.strip().lower()

        for alias, nombre_real in self.alias_medicamentos.items():
            if t == alias:
                return nombre_real

        return texto

    def preparar_sugerencia_dosis(self, input_med, input_dosis):
        texto_original = input_med.text().strip()

        if not texto_original:
            input_dosis.setSufijoSugerido("")
            return

        nombre_normalizado = self.normalizar_medicamento(texto_original).strip()

        if texto_original != nombre_normalizado:
            input_med.blockSignals(True)
            input_med.setText(nombre_normalizado)
            input_med.blockSignals(False)

        sugerencia = self.dosis_sugeridas.get(nombre_normalizado, "")
        input_dosis.setSufijoSugerido(sugerencia)

    def actualizar_tecnica_anestesica(self):
        if self.rb_anestesia_general.isChecked():
            self.stack_tecnica.setCurrentIndex(0)

            if not any([
                self.rb_general_balanceada.isChecked(),
                self.rb_general_tiva.isChecked(),
                self.rb_general_inhalada.isChecked()
            ]):
                self.rb_general_balanceada.setChecked(True)

        elif self.rb_anestesia_regional.isChecked():
            self.stack_tecnica.setCurrentIndex(1)

            if not any([
                self.rb_regional_neuroaxial.isChecked(),
                self.rb_regional_periferico.isChecked(),
                self.rb_regional_local.isChecked()
            ]):
                self.rb_regional_neuroaxial.setChecked(True)

            self.actualizar_detalle_regional()

        elif self.rb_anestesia_combinada.isChecked():
            self.stack_tecnica.setCurrentIndex(2)

            if not any([
                self.rb_combinada_general_regional.isChecked(),
                self.rb_combinada_general_periferico.isChecked()
            ]):
                self.rb_combinada_general_regional.setChecked(True)
            
        self.actualizar_detalle_regional()

    def actualizar_detalle_regional(self):
        es_regional = self.rb_anestesia_regional.isChecked()
        es_neuroaxial = self.rb_regional_neuroaxial.isChecked()
        es_periferico = self.rb_regional_periferico.isChecked()
        # Ocultar radios internos porque ahora usamos inputs manuales
        self.rb_intratecal.setVisible(False)
        self.rb_peridural.setVisible(False)
        self.rb_troncular.setVisible(False)
        self.rb_plexo.setVisible(False)

        # 🔴 SI NO ES REGIONAL → ocultar todo
        if not es_regional:
            for w in [
                self.rb_intratecal,
                self.rb_peridural,
                self.input_nivel_puncion,
                self.input_tipo_aguja,
                self.input_anestesico_local,
                self.rb_troncular,
                self.rb_plexo,
                self.input_sitio_bloqueo
            ]:
                w.setVisible(False)
            return

        # 🟢 NEUROAXIAL
        for w in [
            self.rb_intratecal,
            self.rb_peridural,
            self.input_nivel_puncion,
            self.input_tipo_aguja,
            self.input_anestesico_local
        ]:
            w.setVisible(es_neuroaxial)

        # 🔵 PERIFÉRICO
        for w in [
            self.rb_troncular,
            self.rb_plexo,
            self.input_sitio_bloqueo
        ]:
            w.setVisible(es_periferico)

        # Defaults automáticos (UX clínico)
        if es_neuroaxial and not any([
            self.rb_intratecal.isChecked(),
            self.rb_peridural.isChecked()
        ]):
            self.rb_intratecal.setChecked(True)

        if es_periferico and not any([
            self.rb_troncular.isChecked(),
            self.rb_plexo.isChecked()
        ]):
            self.rb_plexo.setChecked(True)


class RegistroAnestesia(QWidget):
    def __init__(self):
        super().__init__()
        self.fecha_creacion_registro = datetime.now()

        self.setWindowTitle("Registro de Anestesia IMSS")
        ANCHO_VENTANA = 1400
        ALTO_VENTANA = 900

        self.resize(ANCHO_VENTANA, ALTO_VENTANA)
        self.setMinimumWidth(ANCHO_VENTANA)
        self.setMaximumWidth(ANCHO_VENTANA)
        self.setMinimumHeight(700)

        layout = QVBoxLayout()
        
        header = QLabel("REGISTRO DE ANESTESIA Y RECUPERACIÓN")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")


        grid = QVBoxLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)

        ANCHO_CAMPO = 320
        ANCHO_CORTO = 120

        def fila_simple(texto, campo):
            fila = QHBoxLayout()
            fila.setSpacing(3)

            label = QLabel(texto)
            label.setFixedWidth(140)

            fila.addWidget(label)
            fila.addWidget(campo)
            fila.addStretch()

            grid.addLayout(fila)


        def fila_doble(texto1, campo1, texto2, campo2):
            fila = QHBoxLayout()
            fila.setSpacing(3)

            label1 = QLabel(texto1)
            label1.setFixedWidth(80)

            label2 = QLabel(texto2)
            label2.setFixedWidth(80)

            fila.addWidget(label1)
            fila.addWidget(campo1)

            fila.addSpacing(20)

            fila.addWidget(label2)
            fila.addWidget(campo2)

            fila.addStretch()

            grid.addLayout(fila)


        def fila_triple(texto1, campo1, texto2, campo2, texto3, campo3):
            fila = QHBoxLayout()
            fila.setSpacing(3)

            label1 = QLabel(texto1)
            label1.setFixedWidth(50)

            label2 = QLabel(texto2)
            label2.setFixedWidth(45)

            label3 = QLabel(texto3)
            label3.setFixedWidth(60)

            fila.addWidget(label1)
            fila.addWidget(campo1)

            fila.addSpacing(15)

            fila.addWidget(label2)
            fila.addWidget(campo2)

            fila.addSpacing(15)

            fila.addWidget(label3)
            fila.addWidget(campo3)

            fila.addStretch()

            grid.addLayout(fila)

        # =========================
        # CAMPOS
        # =========================

        self.nombre = QLineEdit()
        self.nombre.setFixedWidth(320)

        self.nss = QLineEdit()
        self.nss.setFixedWidth(200)

        fila_doble("Nombre:", self.nombre, "NSS:", self.nss)

        self.edad = QLineEdit()
        self.edad.setFixedWidth(80)

        self.sexo = QComboBox()
        self.sexo.setFixedWidth(140)

        self.sexo.addItems([
            "♂ Masculino",
            "♀ Femenino",
            "Indeterminado"
        ])

        self.unidad = QLineEdit()
        self.unidad.setFixedWidth(200)

        fila_triple("Edad:", self.edad, "Sexo:", self.sexo, "Unidad:", self.unidad)

        self.dx_pre = QLineEdit()
        self.dx_pre.setFixedWidth(400)
        fila_simple("Diagnóstico preoperatorio:", self.dx_pre)

        self.cirugia_programada = QLineEdit()
        self.cirugia_programada.setFixedWidth(400)
        fila_simple("Cirugía programada:", self.cirugia_programada)

        self.dx_post = QLineEdit()
        self.dx_post.setFixedWidth(400)
        fila_simple("Diagnóstico postoperatorio:", self.dx_post)

        self.cirugia_realizada = QLineEdit()
        self.cirugia_realizada.setFixedWidth(400)
        fila_simple("Cirugía realizada:", self.cirugia_realizada)

        self.anestesiologo = QLineEdit()
        self.anestesiologo.setFixedWidth(250)

        self.cirujano = QLineEdit()
        self.cirujano.setFixedWidth(250)

        fila_doble("Anestesiólogo:", self.anestesiologo, "Cirujano:", self.cirujano)
        # =========================
        # ENCABEZADO FIJO
        # =========================
        layout.addWidget(header)
        layout.addLayout(grid)

        # =========================
        # SCROLL SOLO PARA LA GRÁFICA
        # =========================
        self.grafica = GraficaAnestesia()

        scroll_grafica = QScrollArea()
        scroll_grafica.setWidgetResizable(False)
        scroll_grafica.setWidget(self.grafica)
        scroll_grafica.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_grafica.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(scroll_grafica, stretch=1)

        self.print_btn = QPushButton("EXPORTAR PDF + JSON")
        self.print_btn.clicked.connect(self.exportar_pdf_json)
        

        self.load_btn = QPushButton("CARGAR JSON")
        self.load_btn.clicked.connect(self.cargar_json)


        self.btn_debug = QPushButton("VER REGISTRO COMPLETO")
        self.btn_debug.clicked.connect(self.mostrar_registro)


        self.btn_nuevo = QPushButton("NUEVO REGISTRO")
        self.btn_nuevo.clicked.connect(self.nuevo_registro)

        # =========================
        # BOTONES FIJOS ABAJO
        # =========================
        botones_layout = QVBoxLayout()
        botones_layout.setContentsMargins(20, 8, 20, 8)
        botones_layout.setSpacing(8)

        for btn in [
            self.print_btn,
            self.load_btn,
            self.btn_debug,
            self.btn_nuevo
        ]:
            btn.setFixedWidth(500)
            botones_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addLayout(botones_layout)

        self.btn_pdf = QPushButton("Guardar PDF")
        self.btn_pdf.clicked.connect(lambda: exportar_a_pdf_imss(self))

        self.cargar_demo()

        self.setLayout(layout)
        

    def obtener_registro_completo(self):
        registro = {
            "metadata": {
            "fecha_creacion": self.fecha_creacion_registro.strftime("%Y-%m-%d %H:%M:%S"),
            "fecha_exportacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
            "paciente": {
            "nombre": self.nombre.text(),
            "nss": self.nss.text(),
            "edad": self.edad.text(),
            "sexo": self.sexo.currentText(),
            "unidad": self.unidad.text()
        },
        "cirugia": {
            "dx_pre": self.dx_pre.text(),
            "cirugia_programada": self.cirugia_programada.text(),
            "dx_post": self.dx_post.text(),
            "cirugia_realizada": self.cirugia_realizada.text(),
            "anestesiologo": self.anestesiologo.text(),
            "cirujano": self.cirujano.text()
        },
            "eventos": self.grafica.eventos_registrados,
            "medicamentos": self.grafica.obtener_medicamentos_registrados()
        }
        
        if self.grafica.rb_anestesia_general.isChecked():
            tipo_anestesia = "General"
        elif self.grafica.rb_anestesia_regional.isChecked():
            tipo_anestesia = "Regional"
        elif self.grafica.rb_anestesia_combinada.isChecked():
            tipo_anestesia = "Combinada"
        else:
            tipo_anestesia = ""

        subtecnica = ""

        if self.grafica.rb_anestesia_general.isChecked():
            if self.grafica.rb_general_balanceada.isChecked():
                subtecnica = "Balanceada"
            elif self.grafica.rb_general_tiva.isChecked():
                subtecnica = "TIVA"
            elif self.grafica.rb_general_inhalada.isChecked():
                subtecnica = "Inhalada"

        elif self.grafica.rb_anestesia_regional.isChecked():
            if self.grafica.rb_regional_neuroaxial.isChecked():
                subtecnica = "Neuroaxial"
            elif self.grafica.rb_regional_periferico.isChecked():
                subtecnica = "Periférico"
            elif self.grafica.rb_regional_local.isChecked():
                subtecnica = "Local"

        elif self.grafica.rb_anestesia_combinada.isChecked():
            if self.grafica.rb_combinada_general_regional.isChecked():
                subtecnica = "General + regional"
            elif self.grafica.rb_combinada_general_periferico.isChecked():
                subtecnica = "General + periférico"

        detalle_regional = {}

        if self.grafica.rb_regional_neuroaxial.isChecked():
            detalle_regional["tipo"] = "Neuroaxial"

            if self.grafica.rb_intratecal.isChecked():
                detalle_regional["subtipo"] = "Intratecal"
            elif self.grafica.rb_peridural.isChecked():
                detalle_regional["subtipo"] = "Peridural"

            detalle_regional["nivel"] = self.grafica.input_nivel_puncion.text()
            detalle_regional["tipo_aguja"] = self.grafica.input_tipo_aguja.text()
            detalle_regional["anestesico_local"] = self.grafica.input_anestesico_local.text()

        elif self.grafica.rb_regional_periferico.isChecked():
            detalle_regional["tipo"] = "Periférico"

            if self.grafica.rb_troncular.isChecked():
                detalle_regional["subtipo"] = "Troncular"
            elif self.grafica.rb_plexo.isChecked():
                detalle_regional["subtipo"] = "Plexo"

            detalle_regional["sitio"] = self.grafica.input_sitio_bloqueo.text()

        registro["tecnica_anestesica"] = {
            "tipo_anestesia": tipo_anestesia,
            "subtecnica": subtecnica,
            "detalle_regional": detalle_regional
        }

        registro["caso_obstetrico"] = {
            "activo": self.grafica.chk_caso_obstetrico.isChecked(),
            "sexo_rn": (
                "Masculino" if self.grafica.chk_rn_masculino.isChecked()
                else "Femenino" if self.grafica.chk_rn_femenino.isChecked()
                else "Indeterminado" if self.grafica.chk_rn_indeterminado.isChecked()
                else ""
            ),
            "peso_rn": self.grafica.input_rn_peso.text(),
            "talla_rn": self.grafica.input_rn_talla.text(),
            "apgar_1": self.grafica.input_apgar_1.text(),
            "apgar_5": self.grafica.input_apgar_5.text(),
            "apgar_10": self.grafica.input_apgar_10.text(),
            "estado_rn": self.grafica.input_estado_rn.text(),
        }

        return registro


    def cargar_demo(self):
        # =========================
        # Datos del paciente
        # =========================
        self.nombre.setText("Juan Perez García")
        self.nss.setText("3298823465-7")
        self.edad.setText("42 años")
        self.sexo.setCurrentText("Masculino")
        self.unidad.setText("HGZ #18")

        # =========================
        # Datos quirúrgicos
        # =========================
        self.dx_pre.setText("Colecistitis aguda")
        self.cirugia_programada.setText("Colecistectomía laparoscópica")
        self.dx_post.setText("Úlcera gástrica perforada")
        self.cirugia_realizada.setText("Laparoscopía diagnóstica/Parche de Graham")
        self.anestesiologo.setText("Dr. David Arvizo Huitron")
        self.cirujano.setText("Dr. Germán Felipe Wong Sánchez-Espino")

        # =========================
        # Medicamentos demo
        # =========================
        meds_demo = [
            ("A", "Midazolam", "2 mg IV"),
            ("B", "Fentanilo", "500 µg IV"),
            ("C", "Propofol", "150 mg IV"),
            ("D", "Cisatracurio", "13 mg IV"),
            ("E", "Metamizol", "2 g IV"),
            ("F", "Ondansetrón", "8 mg IV"),
        ]

        for inp in self.grafica.inputs_medicamentos:
            inp.clear()
        for inp in self.grafica.inputs_dosis_via:
            inp.clear()

        for fila, med, dosis in meds_demo:
            idx = ord(fila) - ord("A")
            if 0 <= idx < len(self.grafica.inputs_medicamentos):
                self.grafica.inputs_medicamentos[idx].setText(med)
                self.grafica.inputs_dosis_via[idx].setText(dosis)

        # =========================
        # Signos vitales demo
        # =========================
        self.grafica.datos_sv = []
        self.grafica.datos_temp = []
        self.grafica.datos_resp = []
        self.grafica.columna_actual = 0

        import random

        # 12 columnas = 60 min
        for i in range(48):
            tas = random.randint(110, 140)
            tad = random.randint(70, 90)
            fc = random.randint(60, 90)
            spo2 = random.randint(97, 100)
            fio2 = random.choice([40, 45, 50, 55, 60, 65, 70, 75, 80, 85])
            flujo = random.choice([1.0, 1.5, 2.0, 2.5, 3.0])
            sevo = random.choice([1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0])

            self.grafica.datos_sv.append({
                "col": i,
                "fc": fc,
                "tas": tas,
                "tad": tad,
                "spo2": spo2,
                "fio2": fio2,
                "flujo": flujo,
                "sevo": sevo,
            })

            # temperatura cada 15 min
            if i % 3 == 0:
                self.grafica.datos_temp.append({
                    "col": i,
                    "temp": round(36.2 + random.random() * 1.0, 1)
                })

            # respiración demo
            if i < 8:
                modo = "C"
            elif i < 10:
                modo = "A"
            else:
                modo = "E"

            self.grafica.datos_resp.append({
                "col": i,
                "modo": modo
            })

        self.grafica.columna_actual = len(self.grafica.datos_sv)
        self.grafica.update()
    
    def mostrar_registro(self):
        registro = self.obtener_registro_completo()
        print(registro)


    def exportar_pdf_json(self):
        ruta_base, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar PDF y JSON",
            "registro_anestesia",
            "Archivos PDF (*.pdf);;Todos los archivos (*)"
        )

        if not ruta_base:
            return

        if ruta_base.lower().endswith(".pdf"):
            ruta_base = ruta_base[:-4]

        ruta_pdf = ruta_base + ".pdf"
        ruta_json = ruta_base + ".json"

        try:
            exportar_a_pdf_imss(self, ruta_pdf)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo generar el PDF IMSS.\n\n{e}")
            return

        registro = self.obtener_registro_completo()
        registro["signos_vitales_simulados"] = self.grafica.datos_sv
        registro["temperatura_simulada"] = self.grafica.datos_temp
        registro["respiracion_simulada"] = self.grafica.datos_resp

        eventos_limpios = []
        for evento in self.grafica.eventos_registrados:
            eventos_limpios.append({
                "numero": evento["numero"],
                "hora": evento["hora"].strftime("%Y-%m-%d %H:%M:%S")
            })

        registro["eventos"] = eventos_limpios

        try:
            with open(ruta_json, "w", encoding="utf-8") as f:
                json.dump(registro, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Se generó el PDF, pero no se pudo guardar el JSON.\n\n{e}"
            )
            return

        QMessageBox.information(
            self,
            "Exportación completada",
            f"Se guardaron:\n\nPDF: {ruta_pdf}\nJSON: {ruta_json}"
        )

    
        
    def cargar_json(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Cargar JSON",
            "",
            "Archivos JSON (*.json)"
        )

        if not ruta:
            return

        try:
            with open(ruta, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo leer el archivo JSON.\n\n{e}")
            return

        metadata = data.get("metadata", {})
        fecha_creacion = metadata.get("fecha_creacion", "")

        try:
            self.fecha_creacion_registro = datetime.strptime(fecha_creacion, "%Y-%m-%d %H:%M:%S")
        except Exception:
            self.fecha_creacion_registro = datetime.now()

        try:
            # =========================
            # Paciente
            # =========================
            paciente = data.get("paciente", {})
            self.nombre.setText(str(paciente.get("nombre", "")))
            self.nss.setText(str(paciente.get("nss", "")))
            self.edad.setText(str(paciente.get("edad", "")))
            self.sexo.setCurrentText(str(paciente.get("sexo", "")))
            self.unidad.setText(str(paciente.get("unidad", "")))

            # =========================
            # Cirugía
            # =========================
            cirugia = data.get("cirugia", {})
            self.dx_pre.setText(str(cirugia.get("dx_pre", "")))
            self.cirugia_programada.setText(str(cirugia.get("cirugia_programada", "")))
            self.dx_post.setText(str(cirugia.get("dx_post", "")))
            self.cirugia_realizada.setText(str(cirugia.get("cirugia_realizada", "")))
            self.anestesiologo.setText(str(cirugia.get("anestesiologo", "")))
            self.cirujano.setText(str(cirugia.get("cirujano", "")))

            # =========================
            # Medicamentos
            # =========================
            for inp in self.grafica.inputs_medicamentos:
                inp.setText("")
            for inp in self.grafica.inputs_dosis_via:
                inp.setText("")

            medicamentos = data.get("medicamentos", [])
            for med in medicamentos:
                fila = med.get("fila", "")
                if not fila:
                    continue

                idx = ord(fila.upper()) - ord("A")
                if 0 <= idx < len(self.grafica.inputs_medicamentos):
                    self.grafica.inputs_medicamentos[idx].setText(str(med.get("medicamento", "")))
                    self.grafica.inputs_dosis_via[idx].setText(str(med.get("dosis_via", "")))

            # =========================
            # Técnica anestésica
            # =========================
            tecnica = data.get("tecnica_anestesica", {})
            tipo = tecnica.get("tipo_anestesia", "")
            sub = tecnica.get("subtecnica", "")

            # Reset de selección
            for rb in [
                self.grafica.rb_general_balanceada,
                self.grafica.rb_general_tiva,
                self.grafica.rb_general_inhalada,
                self.grafica.rb_regional_neuroaxial,
                self.grafica.rb_regional_periferico,
                self.grafica.rb_regional_local,
                self.grafica.rb_combinada_general_regional,
                self.grafica.rb_combinada_general_periferico
            ]:
                rb.setChecked(False)

            # Aplicar subtecnica
            if sub == "Balanceada":
                self.grafica.rb_general_balanceada.setChecked(True)
            elif sub == "TIVA":
                self.grafica.rb_general_tiva.setChecked(True)
            elif sub == "Inhalada":
                self.grafica.rb_general_inhalada.setChecked(True)

            elif sub == "Neuroaxial":
                self.grafica.rb_regional_neuroaxial.setChecked(True)
            elif sub == "Periférico":
                self.grafica.rb_regional_periferico.setChecked(True)
            elif sub == "Local":
                self.grafica.rb_regional_local.setChecked(True)

            elif sub == "General + regional":
                self.grafica.rb_combinada_general_regional.setChecked(True)
            elif sub == "General + periférico":
                self.grafica.rb_combinada_general_periferico.setChecked(True)

            if tipo == "General":
                self.grafica.rb_anestesia_general.setChecked(True)
            elif tipo == "Regional":
                self.grafica.rb_anestesia_regional.setChecked(True)
            elif tipo == "Combinada":
                self.grafica.rb_anestesia_combinada.setChecked(True)
            else:
                self.grafica.rb_anestesia_general.setChecked(True)

            # =========================
            # Caso obstétrico / RN
            # =========================
            caso_ob = data.get("caso_obstetrico", {})

            self.grafica.chk_caso_obstetrico.setChecked(
                bool(caso_ob.get("activo", False))
            )

            sexo_rn = caso_ob.get("sexo_rn", "")

            self.grafica.chk_rn_masculino.setChecked(sexo_rn == "Masculino")
            self.grafica.chk_rn_femenino.setChecked(sexo_rn == "Femenino")
            self.grafica.chk_rn_indeterminado.setChecked(sexo_rn == "Indeterminado")

            self.grafica.input_rn_peso.setText(str(caso_ob.get("peso_rn", "")))
            self.grafica.input_rn_talla.setText(str(caso_ob.get("talla_rn", "")))

            self.grafica.input_apgar_1.setText(str(caso_ob.get("apgar_1", "")))
            self.grafica.input_apgar_5.setText(str(caso_ob.get("apgar_5", "")))
            self.grafica.input_apgar_10.setText(str(caso_ob.get("apgar_10", "")))

            self.grafica.input_estado_rn.setText(str(caso_ob.get("estado_rn", "")))

            # =========================
            # Eventos
            # =========================
            self.grafica.eventos_registrados = []
            eventos = data.get("eventos", [])

            for ev in eventos:
                hora_str = ev.get("hora", "")
                numero = str(ev.get("numero", ""))

                try:
                    hora_dt = datetime.strptime(hora_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue

                self.grafica.eventos_registrados.append({
                    "hora": hora_dt,
                    "numero": numero
                })

            # Ajustar hora_inicio según el primer evento si existe
            if self.grafica.eventos_registrados:
                self.grafica.hora_inicio = min(e["hora"] for e in self.grafica.eventos_registrados)
            else:
                self.grafica.hora_inicio = datetime.now()

            self.grafica.actualizar_estado_botones()

            # =========================
            # Signos vitales y temperatura
            # =========================
            self.grafica.datos_sv = data.get("signos_vitales_simulados", [])
            self.grafica.datos_temp = data.get("temperatura_simulada", [])
            self.grafica.datos_resp = data.get("respiracion_simulada", [])

            # Ajustar columna actual para continuar desde el último punto
            if self.grafica.datos_sv:
                ultima_col = max(d.get("col", 0) for d in self.grafica.datos_sv)
                self.grafica.columna_actual = ultima_col + 1
            else:
                self.grafica.columna_actual = 0

            # Si ya está completa la simulación, detener timer
            if self.grafica.columna_actual >= self.grafica.max_columnas:
                self.grafica.timer_sv.stop()
                self.grafica.btn_iniciar_sv.setEnabled(False)
                self.grafica.btn_pausar_sv.setEnabled(False)
                self.grafica.btn_reiniciar_sv.setEnabled(True)
            else:
                self.grafica.timer_sv.stop()
                self.grafica.btn_iniciar_sv.setEnabled(True)
                self.grafica.btn_pausar_sv.setEnabled(False)
                self.grafica.btn_reiniciar_sv.setEnabled(True)

            self.grafica.update()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo cargar completamente el JSON.\n\n{e}")
            return

        QMessageBox.information(self, "JSON cargado", f"Se cargó correctamente:\n{ruta}")

    def cargar_datos_generales_por_defecto(self):
        # Datos del paciente
        self.nombre.setText("Juan Perez García")
        self.nss.setText("3298823465-7")
        self.edad.setText("42 años")
        self.sexo.setCurrentText("Masculino")
        self.unidad.setText("HGZ #18")

        # Datos quirúrgicos
        self.dx_pre.setText("Colecistitis aguda")
        self.cirugia_programada.setText("Colecistectomía laparoscópica")
        self.dx_post.setText("Úlcera gástrica perforada")
        self.cirugia_realizada.setText("Laparoscopía diagnóstica/Parche de Graham")

        # Médicos
        self.anestesiologo.setText("Dr. David Arvizo Huitron")
        self.cirujano.setText("Dr. Germán Felipe Wong Sánchez-Espino")

    def nuevo_registro(self):
        self.fecha_creacion_registro = datetime.now()

        # Paciente
        self.nombre.clear()
        self.nss.clear()
        self.edad.clear()
        self.sexo.setCurrentIndex(0)

        # Cirugía
        self.dx_pre.clear()
        self.cirugia_programada.clear()
        self.dx_post.clear()
        self.cirugia_realizada.clear()

        # Eventos
        self.grafica.eventos_registrados = []
        self.grafica.hora_inicio = datetime.now()
        self.grafica.actualizar_estado_botones()

        # Gráfica / simulación
        self.grafica.datos_sv = []
        self.grafica.datos_temp = []
        self.grafica.datos_resp = []
        self.grafica.columna_actual = 0

        self.grafica.timer_sv.stop()
        self.grafica.btn_iniciar_sv.setEnabled(True)
        self.grafica.btn_pausar_sv.setEnabled(False)

        self.grafica.update()

        self.cargar_datos_generales_por_defecto()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setFont(QFont("Arial", 10))
    app.setStyleSheet("""
        QWidget {
            font-size: 10pt;
        }
    """)

    window = RegistroAnestesia()
    window.show()

    sys.exit(app.exec())