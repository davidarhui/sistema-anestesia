from pathlib import Path
import json

from PyQt6.QtCore import QObject, QProcess, pyqtSignal


class IntelliVueConnection(QObject):
    """Conexión del Registro de Anestesia con USS Anestesia SDK.

    Ejecuta el lector IntelliVue como proceso separado, consume sus JSON Lines
    y expone una interfaz Qt mínima para la GUI. La lógica clínica permanece
    fuera de esta clase.
    """

    muestra_recibida = pyqtSignal(dict)
    estado_cambiado = pyqtSignal(str)
    error_recibido = pyqtSignal(str)

    def __init__(self, parent=None, sdk_dir=None):
        super().__init__(parent)

        self.sdk_dir = (
            Path(sdk_dir).expanduser()
            if sdk_dir is not None
            else Path.home() / "Developer" / "uss_anestesia_sdk"
        )

        self.python_path = self.sdk_dir / ".venv" / "bin" / "python3"
        self.script_path = self.sdk_dir / "examples" / "intellivue_live_vitals.py"

        self.process = QProcess(self)
        self.process.setProcessChannelMode(
            QProcess.ProcessChannelMode.SeparateChannels
        )

        self.process.started.connect(self._on_started)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_process_error)
        self.process.readyReadStandardOutput.connect(self._read_standard_output)
        self.process.readyReadStandardError.connect(self._read_standard_error)

        self._stdout_buffer = ""
        self._deteniendo = False

    @property
    def activo(self):
        return self.process.state() != QProcess.ProcessState.NotRunning

    def iniciar(
        self,
        monitor_ip="192.168.50.2",
        local_ip="192.168.50.1",
        timeout=15,
        duration=21600,
    ):
        if self.activo:
            raise RuntimeError("El lector IntelliVue ya está ejecutándose")

        if not self.python_path.exists():
            raise FileNotFoundError(
                f"No existe el Python del SDK: {self.python_path}"
            )

        if not self.script_path.exists():
            raise FileNotFoundError(
                f"No existe el lector IntelliVue: {self.script_path}"
            )

        self._deteniendo = False
        self._stdout_buffer = ""

        argumentos = [
            str(self.script_path),
            "--monitor-ip", str(monitor_ip),
            "--local-ip", str(local_ip),
            "--timeout", str(timeout),
            "--duration", str(duration),
            "--json",
        ]

        self.estado_cambiado.emit("Conectando con IntelliVue…")
        self.process.setWorkingDirectory(str(self.sdk_dir))
        self.process.start(str(self.python_path), argumentos)

    def detener(self):
        if not self.activo:
            self.estado_cambiado.emit("Philips IntelliVue desconectado")
            return

        self._deteniendo = True
        self.estado_cambiado.emit("Desconectando Philips IntelliVue…")

        self.process.terminate()

        if not self.process.waitForFinished(1500):
            self.process.kill()
            self.process.waitForFinished(1000)

    def _on_started(self):
        self.estado_cambiado.emit(
            "IntelliVue conectado; esperando datos clínicos…"
        )

    def _on_finished(self, exit_code, exit_status):
        self._stdout_buffer = ""
        estaba_deteniendo = self._deteniendo
        self._deteniendo = False

        if estaba_deteniendo or exit_code == 0:
            self.estado_cambiado.emit("IntelliVue desconectado")
        else:
            self.estado_cambiado.emit(
                f"Lector IntelliVue finalizado (código {exit_code})"
            )

    def _on_process_error(self, process_error):
        if self._deteniendo:
            return

        self.error_recibido.emit(
            f"Error de QProcess: {process_error.name}"
        )

    def _read_standard_output(self):
        chunk = bytes(
            self.process.readAllStandardOutput()
        ).decode("utf-8", errors="replace")

        self._stdout_buffer += chunk

        while "\n" in self._stdout_buffer:
            line, self._stdout_buffer = self._stdout_buffer.split("\n", 1)
            line = line.strip()

            if not line:
                continue

            try:
                muestra = json.loads(line)
            except json.JSONDecodeError as exc:
                self.error_recibido.emit(
                    "Línea JSON inválida recibida del SDK: "
                    f"{exc}: {line[:160]}"
                )
                continue

            if not isinstance(muestra, dict):
                self.error_recibido.emit(
                    "El SDK entregó JSON que no es un objeto"
                )
                continue

            self.muestra_recibida.emit(muestra)

    def _read_standard_error(self):
        message = bytes(
            self.process.readAllStandardError()
        ).decode("utf-8", errors="replace").strip()

        if message:
            self.error_recibido.emit(message)
