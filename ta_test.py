import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPainter, QPen
from PyQt6.QtCore import Qt


class TAWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prueba TA - Registro Anestesia")
        self.resize(1000, 650)

        # Columnas de tiempo (cada 5 min)
        self.time_columns = ["08:00", "08:05", "08:10", "08:15", "08:20", "08:25"]

        # Datos TA: (hora, sistolica, diastolica)
        self.ta_data = [
            ("08:00", 120, 80),
            ("08:05", 118, 78),
            ("08:10", 130, 85),
            ("08:15", 110, 70),
            ("08:20", 125, 82),
        ]

    def map_bp_to_y(self, value, top, bottom, bp_min=40, bp_max=200):
        value = max(bp_min, min(bp_max, value))
        proportion = (value - bp_min) / (bp_max - bp_min)
        y = bottom - proportion * (bottom - top)
        return int(y)

    def get_x_for_time(self, time_str, left, col_width):
        if time_str in self.time_columns:
            index = self.time_columns.index(time_str)
            return int(left + index * col_width + col_width / 2)
        return None

    def draw_ta_marker(self, painter, x, y_sys, y_dia):
        # Sistólica: flecha hacia abajo
        painter.drawLine(x, y_sys - 8, x, y_sys + 8)
        painter.drawLine(x - 4, y_sys + 4, x, y_sys + 8)
        painter.drawLine(x + 4, y_sys + 4, x, y_sys + 8)

        # Diastólica: flecha hacia arriba
        painter.drawLine(x, y_dia - 8, x, y_dia + 8)
        painter.drawLine(x - 4, y_dia - 4, x, y_dia - 8)
        painter.drawLine(x + 4, y_dia - 4, x, y_dia - 8)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Área de la gráfica
        left = 100
        right = 900
        top = 80
        bottom = 560

        # Borde
        painter.drawRect(left, top, right - left, bottom - top)

        # Escala lateral (40 a 200)
        for value in range(40, 201, 20):
            y = self.map_bp_to_y(value, top, bottom)
            painter.drawText(55, y + 5, str(value))
            painter.drawLine(left, y, right, y)

        # Columnas de tiempo
        col_width = 100
        for i, time_str in enumerate(self.time_columns):
            x = int(left + i * col_width + col_width / 2)
            painter.drawLine(x, top, x, bottom)
            painter.drawText(x - 18, bottom + 25, time_str)

        # Dibujar TA
        pen = QPen()
        pen.setWidth(2)
        painter.setPen(pen)

        for hora, sistolica, diastolica in self.ta_data:
            x = self.get_x_for_time(hora, left, col_width)
            if x is None:
                continue

            y_sys = self.map_bp_to_y(sistolica, top, bottom)
            y_dia = self.map_bp_to_y(diastolica, top, bottom)

            self.draw_ta_marker(painter, x, y_sys, y_dia)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TAWidget()
    window.show()
    sys.exit(app.exec())