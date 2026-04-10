import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout
)
from PyQt6.QtGui import QPainter, QPen, QColor, QPolygonF, QFont
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QLineEdit
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QScrollArea

class GraficaAnestesia(QWidget):
    def __init__(self):
        super().__init__()

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

        for _ in self.eventos_qx:
            inp = QLineEdit(self)
            inp.setPlaceholderText("hh:mm")
            inp.setMaxLength(5)
            inp.setAlignment(Qt.AlignmentFlag.AlignCenter)
            inp.setFrame(False)
            self.inputs_tiempos.append(inp)

        self.setMinimumHeight(900)

        self.botones_eventos = []

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

    def draw_ta_marker(self, painter, x, y_sys, y_dia):
        marker_half_width = 7
        marker_height = 5

        # Sistólica = ˅
        painter.drawLine(
            x - marker_half_width, y_sys - marker_height,
            x, y_sys
        )
        painter.drawLine(
            x + marker_half_width, y_sys - marker_height,
            x, y_sys
        )

        # Diastólica = ˄
        painter.drawLine(
            x - marker_half_width, y_dia + marker_height,
            x, y_dia
        )
        painter.drawLine(
            x + marker_half_width, y_dia + marker_height,
            x, y_dia
        )

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
    
    def draw_fc_point(self, painter, x, y):
        radius = 3
        painter.drawEllipse(x - radius, y - radius, radius * 2, radius * 2)
    
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
        margen_inf = 200

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
        num_columnas = 36
        ancho_col = ancho_grafica / num_columnas

        painter.setPen(QPen(QColor(180, 180, 180), 1))
        for i in range(1, num_columnas):
            x = int(x0 + i * ancho_col)
            painter.drawLine(x, y0, x, y1)

        num_filas = 12
        alto_fila = alto_grafica / num_filas
        for j in range(1, num_filas):
            y = int(y0 + j * alto_fila)
            painter.drawLine(x0, y, x1, y)

        # Líneas gruesas cada 15 min
        painter.setPen(QPen(QColor(120, 120, 120), 2))
        for i in range(0, num_columnas + 1, 3):
            x = int(x0 + i * ancho_col)
            painter.drawLine(x, y0, x, y1)

        # Línea superior de SV (redibujada al final para que quede limpia)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(x0, y0, x1, y0)

        # Escala izquierda
        painter.setFont(QFont("Arial", 8))
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        for valor in [40, 60, 80, 100, 120, 140, 160, 180, 200, 220, 240]:
            y = self.valor_a_y(valor, y0, y1)
            painter.drawText(x0 - 28, int(y + 4), str(valor))

        # Etiquetas de tiempo: 15, 30, 45, 60 y reinicia
        painter.setPen(QPen(Qt.GlobalColor.black, 1))

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

        painter.drawText(x0, 20, "Gráfica anestésica (cada cuadro = 5 min)")

        self.draw_eventos_abajo_sv(painter, x0, y1, ancho_col)

        # =========================
        # SpO2 + AGENTES ARRIBA
        # =========================
      
        # Área de agentes arriba de la gráfica
        alto_fila_ag = 20
        alto_franja_minutos = 16

        y_ag_top = y0 - alto_franja_minutos - (alto_fila_ag * 4)
        y_ag_bottom = y0 - alto_franja_minutos
        
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
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
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
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
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
        for t, s, f, fl, sv in zip(self.tiempos, self.spo2, self.fio2, self.flujo, self.sevo):
            x = self.tiempo_a_x(t, x0, ancho_col)

            painter.drawText(int(x - 12), y_sevo, str(sv))
            painter.drawText(int(x - 12), y_flujo, str(fl))
            painter.drawText(int(x - 12), y_fio2, str(f))
            painter.drawText(int(x - 12), y_spo2, str(s))
    
        # FC: puntos (sin línea)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setBrush(QColor("black"))

        for t, p in zip(self.tiempos, self.pulso):
            x = int(self.tiempo_a_x(t, x0, ancho_col))
            y = int(self.valor_a_y(p, y0, y1))
            painter.drawEllipse(QPointF(x, y), 2, 2)

        # TA: flechas sobre la línea de tiempo
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        for t, sis, dia in zip(self.tiempos, self.ta_sistolica, self.ta_diastolica):
            x = x0 + ((t - 5) / 5) * ancho_col
            y_sis = self.valor_a_y(sis, y0, y1)
            y_dia = self.valor_a_y(dia, y0, y1)

            # Sistólica: flecha hacia abajo
            painter.drawLine(int(x), int(y_sis), int(x - 4), int(y_sis - 6))
            painter.drawLine(int(x), int(y_sis), int(x + 4), int(y_sis - 6))

            # Diastólica: flecha hacia arriba
            painter.drawLine(int(x), int(y_dia), int(x - 4), int(y_dia + 6))
            painter.drawLine(int(x), int(y_dia), int(x + 4), int(y_dia + 6))

        # Temperatura = triángulo
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for t, temp in zip(self.tiempos, self.temperatura):
            x = self.tiempo_a_x(t, x0, ancho_col)
            y = self.temperatura_a_y(temp, y0, y1)
            self.dibujar_triangulo(painter, x, y, tamaño=8)
        
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawText(int(x0 - 105), int(y1 - 118), "EVENTOS")

        self.posicionar_botones_eventos(x0, y1)

        self.posicionar_inputs_tiempos(x0, y0, y1)

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

        self.filas_meds = [chr(ord('A') + i) for i in range(13)]  # A a M

        self.inputs_medicamentos = []
        self.inputs_dosis_via = []

        for _ in self.filas_meds:
            inp_med = QLineEdit(self)
            inp_med.setPlaceholderText("Medicamento")
            inp_med.setFrame(True)
            self.inputs_medicamentos.append(inp_med)

            inp_dosis = QLineEdit(self)
            inp_dosis.setPlaceholderText("Dosis/Vía")
            inp_dosis.setFrame(True)
            self.inputs_dosis_via.append(inp_dosis)

    def registrar_evento(self, numero_evento):
        numero_txt = str(numero_evento)
        registrados = [e["numero"] for e in self.eventos_registrados]

        # No repetir el mismo evento
        if numero_txt in registrados:
            QMessageBox.warning(
                self,
                "Evento ya registrado",
                f"El evento '{self.nombre_evento(numero_evento)}' ya fue registrado."
            )
            return

        # Validar secuencia
        if numero_evento > 1:
            previo_txt = str(numero_evento - 1)
            if previo_txt not in registrados:
                QMessageBox.warning(
                    self,
                    "Secuencia inválida",
                    f"No puedes registrar '{self.nombre_evento(numero_evento)}' sin haber registrado antes '{self.nombre_evento(numero_evento - 1)}'."
                )
                return

        ahora = datetime.now()
        hora_txt = ahora.strftime("%H:%M")

        self.eventos_registrados.append({
            "hora": ahora,
            "numero": numero_txt
        })

        indice = numero_evento - 1
        if 0 <= indice < len(self.inputs_tiempos):
            self.inputs_tiempos[indice].setText(hora_txt)
        
        self.actualizar_estado_botones()
        self.update()

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
    
    def deshacer_ultimo_evento(self):
        if not self.eventos_registrados:
            return

        ultimo = self.eventos_registrados.pop()
        numero = int(ultimo["numero"])

        # borrar hora del input correspondiente
        indice = numero - 1
        if 0 <= indice < len(self.inputs_tiempos):
            self.inputs_tiempos[indice].clear()

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

            self.inputs_medicamentos[i].setGeometry(x_med + 2, y + 2, 196, 20)
            self.inputs_dosis_via[i].setGeometry(x_dosis + 2, y + 2, 126, 20)

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
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        painter.drawText(x1 + 6, y0 + 15, "MEDICAMENTOS")
        painter.drawText(x2 + 6, y0 + 15, "DOSIS/VIA")

        # Letras A-M
        painter.setFont(QFont("Arial", 8))
        for i, letra in enumerate(self.filas_meds):
            y_texto = y0 + alto_header + i * alto_fila + 16
            painter.drawText(x0 + 6, y_texto, letra)

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

        grid.addWidget(QLabel("HGSZ #18:"), 1, 4)
        self.hgsz = QLineEdit()
        grid.addWidget(self.hgsz, 1, 5)

        grid.addWidget(QLabel("Diagnóstico preoperatorio:"), 2, 0)
        self.dx_pre = QLineEdit()
        grid.addWidget(self.dx_pre, 2, 1, 1, 5)

        grid.addWidget(QLabel("Procedimiento:"), 3, 0)
        self.proc = QLineEdit()
        grid.addWidget(self.proc, 3, 1, 1, 5)

        grid.addWidget(QLabel("Diagnóstico operatorio:"), 4, 0)
        self.dx_op = QLineEdit()
        grid.addWidget(self.dx_op, 4, 1, 1, 5)

        container_layout.addLayout(grid)

        self.grafica = GraficaAnestesia()
        container_layout.addWidget(self.grafica)

        self.print_btn = QPushButton("IMPRIMIR REGISTRO")
        container_layout.addWidget(self.print_btn)

        self.setLayout(layout)
    
app = QApplication(sys.argv)
window = RegistroAnestesia()
window.show()
sys.exit(app.exec())