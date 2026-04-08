import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPainter, QPen, QFont
from PyQt6.QtCore import Qt


class TAWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TA estilo IMSS ajustada")
        self.resize(1200, 950)

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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        self.draw_agents_grid(painter)
        self.draw_agents(painter)
        self.draw_grid(painter)
        self.draw_ta_data(painter)
        self.draw_fc_data(painter)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TAWidget()
    window.show()
    sys.exit(app.exec())