import sys
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QComboBox, QCompleter
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

        self.setMinimumHeight(900)

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
        self.setMinimumSize(1400, 900)


        self.lbl_velocidad_sv = QLabel("Vel", self)
        self.lbl_velocidad_sv.setStyleSheet("color: black; font-size: 9px;")
        self.lbl_velocidad_sv.adjustSize()

        for _ in self.filas_meds:
            inp_med = QLineEdit(self)
            inp_med.setFrame(False)
            inp_med.setStyleSheet(estilo_tabla)
            inp_med.setCompleter(self.crear_completer_medicamentos())

            inp_dosis = LineEditConSufijo(self)
            inp_dosis.setFrame(False)
            inp_dosis.setStyleSheet(estilo_tabla)

            # 👉 color gris del sufijo/placeholder
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

        ancho = self.width()
        alto = self.height()

        margen_izq = 110
        margen_der = 20
        margen_sup = 120

        alto_header_meds = 22
        alto_fila_meds = 24
        total_filas_meds = len(self.filas_meds)

        # espacio para: TIEMPO + encabezado tabla + 13 filas + aire abajo
        margen_inf = 60 + alto_header_meds + (total_filas_meds * alto_fila_meds) + 30

        x0 = margen_izq
        y0 = margen_sup
        x1 = ancho - margen_der
        y1 = alto - margen_inf

        ancho_grafica = x1 - x0
        alto_grafica = y1 - y0

        painter.fillRect(self.rect(), QColor("white"))

        # Área principal
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawRect(x0, y0, ancho_grafica, alto_grafica)

        # Cuadrícula
        num_columnas = self.obtener_total_columnas_dibujo()
        ancho_col = 35  # ancho fijo por columna en pantalla

        ancho_grafica = num_columnas * ancho_col
        x1 = x0 + ancho_grafica

        nuevo_ancho_minimo = int(x1 + margen_der + 40)
        if self.minimumWidth() != nuevo_ancho_minimo:
            self.setMinimumWidth(nuevo_ancho_minimo)

        painter.setPen(QPen(QColor(180, 180, 180), 1))
        for i in range(1, num_columnas):
            x = int(x0 + i * ancho_col)
            painter.drawLine(x, y0, x, y1 - 1)

        num_filas = 12
        alto_fila = alto_grafica / num_filas
        for j in range(1, num_filas):
            y = int(y0 + j * alto_fila)
            painter.drawLine(x0, y, x1, y)

        # Líneas gruesas cada 15 min
        painter.setPen(QPen(QColor(120, 120, 120), 2))
        for i in range(0, num_columnas + 1, 3):
            x = int(x0 + i * ancho_col)
            painter.drawLine(x, y0, x, y1 - 1)

        # Línea superior de SV (redibujada al final para que quede limpia)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(x0, y0, x1, y0)

        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(x0, y1, x1, y1)

        # Escala izquierda
        painter.setFont(QFont("Arial", 8))
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        for valor in [40, 60, 80, 100, 120, 140, 160, 180, 200, 220, 240]:
            y = self.valor_a_y(valor, y0, y1)
            painter.drawText(x0 - 28, int(y + 4), str(valor))

        # Etiquetas de tiempo: 15, 30, 45, 60 y reinicia
        painter.setPen(QPen(Qt.GlobalColor.black, 2))

        # Minutos arriba de la gráfica principal
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setFont(QFont("Arial", 8))

        y_minutos = y0 - 6  # ajustable

        for i in range(num_columnas):
            minuto_real = (i + 1) * 5

            if minuto_real % 15 == 0:
                minuto_etiqueta = minuto_real % 60
                if minuto_etiqueta == 0:
                    minuto_etiqueta = 60

                texto = str(minuto_etiqueta)
                x = int(x0 + (i + 1) * ancho_col)

                rect = painter.fontMetrics().boundingRect(texto)
                x_texto = x - rect.width() / 2

                painter.drawText(int(x_texto), y_minutos, texto)

        painter.drawText(10, y1 + 20, "TIEMPO")

        # =========================
        # TABLA DE MEDICAMENTOS
        # =========================
        self.posicionar_tabla_medicamentos(x0, y1)
        self.draw_tabla_medicamentos(painter, y1)

        # painter.drawText(x0, 20, "Gráfica anestésica (cada cuadro = 5 min)")

        self.draw_eventos_abajo_sv(painter, x0, y1, ancho_col)

        # =========================
        # SpO2 + AGENTES ARRIBA
        # =========================
      
        # Área de agentes arriba de la gráfica
        alto_fila_ag = 20
        alto_franja_minutos = 16

        y_ag_top = y0 - alto_franja_minutos - (alto_fila_ag * 4)
        y_ag_bottom = y0 - alto_franja_minutos

        self.posicionar_botones_simulacion(x0, y_ag_top)
        
        # Texto centrado verticalmente en cada fila
        y_sevo = y_ag_top + 15
        y_flujo = y_ag_top + 35
        y_fio2 = y_ag_top + 55  
        y_spo2 = y_ag_top + 75

        # =========================
        # Cuadrícula de agentes
        # =========================
        painter.setPen(QPen(QColor(180, 180, 180), 1))

        # Verticales alineadas con la gráfica principal
        for i in range(num_columnas + 1):
            x = int(x0 + i * ancho_col)
            painter.drawLine(x, y_ag_top, x, y_ag_bottom)

        # Horizontales internas y superior (sin la inferior)
        for j in range(4):
            y = y_ag_top + j * alto_fila_ag
            painter.drawLine(x0, y, x1, y)

        # Líneas gruesas cada 15 min
        painter.setPen(QPen(QColor(120, 120, 120), 2))
        for i in range(0, num_columnas + 1, 3):
            x = int(x0 + i * ancho_col)
            painter.drawLine(x, y_ag_top, x, y_ag_bottom)

        # Bordes de la cuadrícula de agentes (sin borde inferior)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(x0, y_ag_top, x1, y_ag_top)         # borde superior
        painter.drawLine(x0, y_ag_top, x0, y_ag_bottom)      # borde izquierdo
        painter.drawLine(x1, y_ag_top, x1, y_ag_bottom)      # borde derecho

        # =========================
        # Cuadrícula de agentes
        # =========================

        # 1) Verticales internas finas, EXCEPTO las de cada 15 min
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        for i in range(1, num_columnas):  # sin bordes x0 y x1
            if i % 3 != 0:  # no dibujar aquí las de 15, 30, 45...
                x = int(x0 + i * ancho_col)
                painter.drawLine(x, y_ag_top, x, y_ag_bottom)

        # 2) Horizontales internas finas (sin superior ni inferior)
        for j in range(1, 4):  # solo divisiones internas
            y = y_ag_top + j * alto_fila_ag
            painter.drawLine(x0, y, x1, y)

        # 3) Verticales gruesas cada 15 min
        painter.setPen(QPen(QColor(120, 120, 120), 2))
        for i in range(3, num_columnas, 3):  # internas, sin bordes
            x = int(x0 + i * ancho_col)
            painter.drawLine(x, y_ag_top, x, y_ag_bottom)

        # 4) Bordes de agentes (solo superior, izquierdo y derecho)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(x0, y_ag_top, x1, y_ag_top)          # superior
        painter.drawLine(x0, y_ag_top, x0, y_ag_bottom)       # izquierdo
        painter.drawLine(x1, y_ag_top, x1, y_ag_bottom)       # derecho

        # Línea inferior de AGENTES al final, para que quede limpia
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(x0, y_ag_bottom, x1, y_ag_bottom)

        # Etiquetas izquierda
        painter.drawText(x0 - 70, y_spo2, "SpO₂")
        painter.drawText(x0 - 70, y_fio2, "FiO₂")
        painter.drawText(x0 - 70, y_flujo, "Flujo")
        painter.drawText(x0 - 70, y_sevo, "Sevo")

        # Valores alineados al tiempo
        # for t, s, f, fl, sv in zip(self.tiempos, self.spo2, self.fio2, self.flujo, self.sevo):
        #    x = self.tiempo_a_x(t, x0, ancho_col)
        #
        #    painter.drawText(int(x - 12), y_sevo, str(sv))
        #    painter.drawText(int(x - 12), y_flujo, str(fl))
        #    painter.drawText(int(x - 12), y_fio2, str(f))
        #    painter.drawText(int(x - 12), y_spo2, str(s))
        #
        # FC: puntos (sin línea)
        # painter.setPen(QPen(Qt.GlobalColor.black, 1))
        # painter.setBrush(QColor("black"))
        #
        # for t, p in zip(self.tiempos, self.pulso):
        # x = int(self.tiempo_a_x(t, x0, ancho_col))
        # y = int(self.valor_a_y(p, y0, y1))
        # painter.drawEllipse(QPointF(x, y), 2, 2)

        # TA: flechas sobre la línea de tiempo
        # painter.setPen(QPen(Qt.GlobalColor.black, 2))
        # painter.setBrush(Qt.BrushStyle.NoBrush)
        #
        # for t, sis, dia in zip(self.tiempos, self.ta_sistolica, self.ta_diastolica):
        #     x = x0 + ((t - 5) / 5) * ancho_col
        #     y_sis = self.valor_a_y(sis, y0, y1)
        #     y_dia = self.valor_a_y(dia, y0, y1)
        #
        #     painter.drawLine(int(x), int(y_sis), int(x - 4), int(y_sis - 6))
        #     painter.drawLine(int(x), int(y_sis), int(x + 4), int(y_sis - 6))
        #
        #     painter.drawLine(int(x), int(y_dia), int(x - 4), int(y_dia + 6))
        #     painter.drawLine(int(x), int(y_dia), int(x + 4), int(y_dia + 6))

        # Temperatura = triángulo
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # for t, temp in zip(self.tiempos, self.temperatura):
        #    x = self.tiempo_a_x(t, x0, ancho_col)
        #    y = self.temperatura_a_y(temp, y0, y1)
        #    self.dibujar_triangulo(painter, x, y, tamaño=8)
        
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawText(int(x0 - 105), int(y1 - 118), "EVENTOS")

        self.posicionar_botones_eventos(x0, y1)

        self.draw_agentes_simulados(painter)
        self.draw_sv_simulados(painter)
        self.draw_temperatura_simulada(painter)


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
        delta = hora_evento - self.hora_inicio
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

        y_texto = y1 + 16
        painter.setFont(QFont("Arial", 8))

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

        # Si es el primer evento, usarlo como referencia de tiempo
        if not self.eventos_registrados:
            self.hora_inicio = hora_actual

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

        for i in range(len(self.filas_meds)):
            y = y_tabla - 14 + alto_header + i * alto_fila

            # Más angosto para no tapar la línea divisoria
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
        self.datos_resp = []
        self.columna_actual = 0
        self.btn_iniciar_sv.setEnabled(True)
        self.btn_pausar_sv.setEnabled(False)
        self.btn_reiniciar_sv.setEnabled(True)
        self.update()

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


class RegistroAnestesia(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Registro de Anestesia IMSS")
        self.resize(1100, 700)
        self.setMinimumSize(900, 600)

        layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        container_layout = QVBoxLayout(container)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        header = QLabel("REGISTRO DE ANESTESIA Y RECUPERACIÓN")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        container_layout.addWidget(header)

        grid = QGridLayout()

        grid.addWidget(QLabel("Nombre:"), 0, 0)
        self.nombre = QLineEdit()
        grid.addWidget(self.nombre, 0, 1)

        grid.addWidget(QLabel("NSS:"), 0, 2)
        self.nss = QLineEdit()
        grid.addWidget(self.nss, 0, 3)

        grid.addWidget(QLabel("Edad:"), 1, 0)
        self.edad = QLineEdit()
        grid.addWidget(self.edad, 1, 1)

        grid.addWidget(QLabel("Sexo:"), 1, 2)
        self.sexo = QLineEdit()
        grid.addWidget(self.sexo, 1, 3)

        grid.addWidget(QLabel("Unidad:"), 1, 4)
        self.unidad = QLineEdit()
        grid.addWidget(self.unidad, 1, 5)

        grid.addWidget(QLabel("Diagnóstico preoperatorio:"), 2, 0)
        self.dx_pre = QLineEdit()
        grid.addWidget(self.dx_pre, 2, 1, 1, 5)

        grid.addWidget(QLabel("Cirugía programada:"), 3, 0)
        self.cirugia_programada = QLineEdit()
        grid.addWidget(self.cirugia_programada, 3, 1, 1, 5)

        grid.addWidget(QLabel("Diagnóstico operatorio:"), 4, 0)
        self.dx_op = QLineEdit()
        grid.addWidget(self.dx_op, 4, 1, 1, 5)

        grid.addWidget(QLabel("Cirugía realizada:"), 5, 0)
        self.cirugia_realizada = QLineEdit()
        grid.addWidget(self.cirugia_realizada, 5, 1, 1, 5)

        container_layout.addLayout(grid)

        self.grafica = GraficaAnestesia()
        container_layout.addWidget(self.grafica)

        self.print_btn = QPushButton("EXPORTAR PDF + JSON")
        self.print_btn.clicked.connect(self.exportar_pdf_json)
        container_layout.addWidget(self.print_btn)
        
        self.load_btn = QPushButton("CARGAR JSON")
        self.load_btn.clicked.connect(self.cargar_json)
        container_layout.addWidget(self.load_btn)

        self.btn_debug = QPushButton("VER REGISTRO COMPLETO")
        self.btn_debug.clicked.connect(self.mostrar_registro)
        container_layout.addWidget(self.btn_debug)

        self.btn_nuevo = QPushButton("NUEVO REGISTRO")
        self.btn_nuevo.clicked.connect(self.nuevo_registro)

        self.btn_pdf = QPushButton("Guardar PDF")
        self.btn_pdf.clicked.connect(lambda: exportar_a_pdf_imss(self))

        container_layout.addWidget(self.btn_nuevo)

        self.cargar_demo()

        self.setLayout(layout)
        

    def obtener_registro_completo(self):
        registro = {
            "paciente": {
            "nombre": self.nombre.text(),
            "nss": self.nss.text(),
            "edad": self.edad.text(),
            "sexo": self.sexo.text(),
            "unidad": self.unidad.text()
        },
        "cirugia": {
            "dx_pre": self.dx_pre.text(),
            "cirugia_programada": self.cirugia_programada.text(),
            "dx_post": self.dx_op.text(),
            "cirugia_realizada": self.cirugia_realizada.text()
        },
            "eventos": self.grafica.eventos_registrados,
            "medicamentos": self.grafica.obtener_medicamentos_registrados()
        }

        return registro
    
    def cargar_demo(self):
        # =========================
        # Datos del paciente
        # =========================
        self.nombre.setText("David Arvizo Huitron")
        self.nss.setText("3298823465-7")
        self.edad.setText("42 años")
        self.sexo.setText("Masculino")
        self.unidad.setText("HGZ #18")

        # =========================
        # Datos quirúrgicos
        # =========================
        self.dx_pre.setText("Colecistitis aguda")
        self.cirugia_programada.setText("Colecistectomía laparoscópica")
        self.dx_op.setText("Úlcera gástrica perforada")
        self.cirugia_realizada.setText("Laparoscopía diagnóstica/Parche de Graham")

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

        try:
            # =========================
            # Paciente
            # =========================
            paciente = data.get("paciente", {})
            self.nombre.setText(str(paciente.get("nombre", "")))
            self.nss.setText(str(paciente.get("nss", "")))
            self.edad.setText(str(paciente.get("edad", "")))
            self.sexo.setText(str(paciente.get("sexo", "")))
            self.unidad.setText(str(paciente.get("unidad", "")))

            # =========================
            # Cirugía
            # =========================
            cirugia = data.get("cirugia", {})
            self.dx_pre.setText(str(cirugia.get("dx_pre", "")))
            self.proc.setText(str(cirugia.get("procedimiento", "")))
            self.dx_op.setText(str(cirugia.get("dx_post", "")))

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

    def nuevo_registro(self):
        # Paciente
        self.nombre.clear()
        self.nss.clear()
        self.edad.clear()
        self.sexo.clear()
        self.unidad.clear()

        # Cirugía
        self.dx_pre.clear()
        self.cirugia_programada.clear()
        self.dx_op.clear()
        self.cirugia_realizada.clear()

        # Medicamentos
        for inp in self.grafica.inputs_medicamentos:
            inp.clear()
        for inp in self.grafica.inputs_dosis_via:
            inp.clear()

        # Eventos
        self.grafica.eventos_registrados = []
        self.grafica.hora_inicio = datetime.now()
        self.grafica.actualizar_estado_botones()

        # Gráfica
        self.grafica.datos_sv = []
        self.grafica.datos_temp = []
        self.grafica.datos_resp = []
        self.grafica.columna_actual = 0

        self.grafica.timer_sv.stop()
        self.grafica.btn_iniciar_sv.setEnabled(True)
        self.grafica.btn_pausar_sv.setEnabled(False)

        self.grafica.update()

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