import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout
)
from PyQt6.QtGui import QPainter, QPen, QColor, QPolygonF, QFont
from PyQt6.QtCore import Qt, QPointF


class GraficaAnestesia(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(520)

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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        ancho = self.width()
        alto = self.height()

        margen_izq = 80
        margen_der = 20
        margen_sup = 120
        margen_inf = 130

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

        # Escala izquierda
        painter.setFont(QFont("Arial", 8))
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        for valor in [40, 60, 80, 100, 120, 140, 160, 180, 200, 220, 240]:
            y = self.valor_a_y(valor, y0, y1)
            painter.drawText(40, int(y + 4), str(valor))

        # Etiquetas de tiempo
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        for i in range(num_columnas):
            tiempo = (i + 1) * 5
            x = int(x0 + i * ancho_col + ancho_col / 2)
            if tiempo % 15 == 0:
                painter.drawText(x - 10, y1 + 20, str(tiempo))

        painter.drawText(15, y0 + 20, "SV")
        painter.drawText(10, y1 + 20, "TIEMPOS")
        painter.drawText(x0, 20, "Gráfica anestésica (cada cuadro = 5 min)")

        # =========================
        # SpO2 + AGENTES ARRIBA
        # =========================

        y_spo2 = y0 - 20
        y_fio2 = y0 - 40
        y_flujo = y0 - 60
        y_sevo = y0 - 80

        painter.setFont(QFont("Arial", 9))
        painter.setPen(QPen(Qt.GlobalColor.black, 1))

        # Etiquetas izquierda
        painter.drawText(x0 - 70, y_spo2, "SpO₂")
        painter.drawText(x0 - 70, y_fio2, "FiO₂")
        painter.drawText(x0 - 70, y_flujo, "Flujo")
        painter.drawText(x0 - 70, y_sevo, "Sevo")

        # Valores alineados al tiempo
        for t, s, f, fl, sv in zip(self.tiempos, self.spo2, self.fio2, self.flujo, self.sevo):
            x = self.tiempo_a_x(t, x0, ancho_col)

            painter.drawText(int(x - 12), y_spo2, str(s))
            painter.drawText(int(x - 12), y_fio2, str(f))
            painter.drawText(int(x - 12), y_flujo, str(fl))
            painter.drawText(int(x - 12), y_sevo, str(sv))
    
        # Pulso = círculo
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for t, p in zip(self.tiempos, self.pulso):
            x = self.tiempo_a_x(t, x0, ancho_col)
            y = self.valor_a_y(p, y0, y1)
            painter.drawEllipse(QPointF(x, y), 4, 4)

        # TA: ambas flechas en la misma columna de tiempo
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(QColor("black"))
        for t, sis, dia in zip(self.tiempos, self.ta_sistolica, self.ta_diastolica):
            x = self.tiempo_a_x(t, x0, ancho_col)
            y_sis = self.valor_a_y(sis, y0, y1)
            y_dia = self.valor_a_y(dia, y0, y1)
            self.dibujar_flecha(painter, x, y_sis, direccion="abajo", tamaño=10)
            self.dibujar_flecha(painter, x, y_dia, direccion="arriba", tamaño=10)

        # Temperatura = triángulo
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for t, temp in zip(self.tiempos, self.temperatura):
            x = self.tiempo_a_x(t, x0, ancho_col)
            y = self.temperatura_a_y(temp, y0, y1)
            self.dibujar_triangulo(painter, x, y, tamaño=8)

        
        painter.setFont(QFont("Arial", 9))
        painter.drawText(x0 - 70, y_fio2, "FiO₂")
        painter.drawText(x0 - 70, y_flujo, "Flujo")
        painter.drawText(x0 - 70, y_sevo, "Sevo")

        for t, v in zip(self.tiempos, self.fio2):
            x = self.tiempo_a_x(t, x0, ancho_col)
            painter.drawText(int(x - 12), y_fio2, v)

        for t, v in zip(self.tiempos, self.flujo):
            x = self.tiempo_a_x(t, x0, ancho_col)
            painter.drawText(int(x - 10), y_flujo, v)

        for t, v in zip(self.tiempos, self.sevo):
            x = self.tiempo_a_x(t, x0, ancho_col)
            painter.drawText(int(x - 12), y_sevo, v)


class RegistroAnestesia(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Registro de Anestesia IMSS")
        self.setGeometry(100, 100, 1200, 860)

        layout = QVBoxLayout()

        header = QLabel("REGISTRO DE ANESTESIA Y RECUPERACIÓN")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

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

        layout.addLayout(grid)

        self.grafica = GraficaAnestesia()
        layout.addWidget(self.grafica)

        eventos_layout = QHBoxLayout()

        self.btn1 = QPushButton("1. Entrada Qx")
        self.btn2 = QPushButton("2. Inicio Anestesia")
        self.btn3 = QPushButton("3. Inicio Cirugía")
        self.btn4 = QPushButton("4. Fin Cirugía")
        self.btn5 = QPushButton("5. Fin Anestesia")
        self.btn6 = QPushButton("6. Salida Qx")

        for btn in [self.btn1, self.btn2, self.btn3, self.btn4, self.btn5, self.btn6]:
            eventos_layout.addWidget(btn)

        layout.addLayout(eventos_layout)

        self.print_btn = QPushButton("IMPRIMIR REGISTRO")
        layout.addWidget(self.print_btn)

        self.setLayout(layout)


app = QApplication(sys.argv)
window = RegistroAnestesia()
window.show()
sys.exit(app.exec())