from pathlib import Path
import json
import shutil
import socket
import subprocess

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal


class IntelliVueConnection(QObject):
    """Puente Qt entre Registro de Anestesia y USS Anestesia SDK.

    Fase 2 del Patch 003:
    - valida que la IP local esté configurada;
    - comprueba que el IntelliVue responda en red;
    - expone estados claros durante la conexión;
    - mantiene el lector clínico del SDK en un proceso separado.

    La preparación automática por DHCP se añadirá en la siguiente fase.
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

        # Proceso auxiliar para el ping de preflight. Mantenerlo separado evita
        # congelar la GUI mientras esperamos respuesta del monitor.
        self.preflight = QProcess(self)
        self.preflight.setProcessChannelMode(
            QProcess.ProcessChannelMode.SeparateChannels
        )
        self.preflight.finished.connect(self._on_preflight_finished)
        self.preflight.errorOccurred.connect(self._on_preflight_error)

        self._stdout_buffer = ""
        self._deteniendo = False
        self._conectando = False
        self._datos_recibidos = False
        self._preflight_cancelado = False

        self._monitor_ip = "192.168.50.2"
        self._local_ip = "192.168.50.1"
        self._timeout = 15
        self._duration = 21600

    @property
    def activo(self):
        return (
            self._conectando
            or self.preflight.state() != QProcess.ProcessState.NotRunning
            or self.process.state() != QProcess.ProcessState.NotRunning
        )

    def iniciar(
        self,
        monitor_ip="192.168.50.2",
        local_ip="192.168.50.1",
        timeout=15,
        duration=21600,
    ):
        if self.activo:
            raise RuntimeError("La conexión IntelliVue ya está en curso")

        self._validar_sdk()

        self._monitor_ip = str(monitor_ip)
        self._local_ip = str(local_ip)
        self._timeout = int(timeout)
        self._duration = int(duration)

        self._deteniendo = False
        self._conectando = True
        self._datos_recibidos = False
        self._preflight_cancelado = False
        self._stdout_buffer = ""

        self.estado_cambiado.emit(
            f"🟡 Verificando red local {self._local_ip}…"
        )

        # Deja que Qt pinte el estado antes de ejecutar la comprobación local.
        QTimer.singleShot(0, self._preflight_local)

    def detener(self):
        if not self.activo:
            self.estado_cambiado.emit("⚪ Philips IntelliVue desconectado")
            return

        self._deteniendo = True
        self._conectando = False
        self._preflight_cancelado = True
        self.estado_cambiado.emit("🟡 Desconectando Philips IntelliVue…")

        if self.preflight.state() != QProcess.ProcessState.NotRunning:
            self.preflight.kill()
            self.preflight.waitForFinished(500)

        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(1500):
                self.process.kill()
                self.process.waitForFinished(1000)
        else:
            self._deteniendo = False
            self.estado_cambiado.emit("⚪ Philips IntelliVue desconectado")

    def _validar_sdk(self):
        if not self.python_path.exists():
            raise FileNotFoundError(
                f"No existe el Python del SDK: {self.python_path}"
            )
        if not self.script_path.exists():
            raise FileNotFoundError(
                f"No existe el lector IntelliVue: {self.script_path}"
            )

    def _preflight_local(self):
        if self._deteniendo:
            return

        # bind() verifica de forma portable que esa IPv4 pertenece actualmente
        # al Mac; no depende del nombre de la interfaz (en8 puede cambiar).
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((self._local_ip, 0))
        except OSError as exc:
            self._fallar_conexion(
                f"La IP local {self._local_ip} no está configurada en este Mac. "
                "La red IntelliVue todavía no está preparada. "
                f"Detalle: {exc}"
            )
            return
        finally:
            sock.close()

        self.estado_cambiado.emit(
            f"🟡 Buscando IntelliVue en {self._monitor_ip}…"
        )
        self._iniciar_ping()

    def _iniciar_ping(self):
        ping = shutil.which("ping")
        if not ping:
            # Es muy improbable en macOS; si falta, no impedimos la asociación.
            self.estado_cambiado.emit(
                "🟡 No se pudo ejecutar ping; intentando asociación…"
            )
            self._iniciar_lector()
            return

        # macOS usa -W en milisegundos. En otros Unix puede variar, por eso
        # además hay un timeout externo con QTimer.
        argumentos = ["-c", "1", "-W", "1000", self._monitor_ip]
        self.preflight.start(ping, argumentos)
        QTimer.singleShot(2500, self._timeout_preflight)

    def _timeout_preflight(self):
        if self.preflight.state() == QProcess.ProcessState.NotRunning:
            return
        self._preflight_cancelado = True
        self.preflight.kill()
        self._fallar_conexion(
            f"El IntelliVue {self._monitor_ip} no respondió al ping. "
            "Revisa cable, DHCP/IP del monitor y conexión Ethernet."
        )

    def _on_preflight_finished(self, exit_code, exit_status):
        if self._deteniendo or self._preflight_cancelado:
            self._preflight_cancelado = False
            return

        if exit_code != 0:
            stderr = bytes(
                self.preflight.readAllStandardError()
            ).decode("utf-8", errors="replace").strip()
            extra = f" ({stderr})" if stderr else ""
            self._fallar_conexion(
                f"El IntelliVue {self._monitor_ip} no respondió al ping{extra}. "
                "Revisa cable, DHCP/IP del monitor y conexión Ethernet."
            )
            return

        self.estado_cambiado.emit(
            f"🟡 IntelliVue encontrado en {self._monitor_ip}; asociando…"
        )
        self._iniciar_lector()

    def _on_preflight_error(self, process_error):
        if self._deteniendo or self._preflight_cancelado:
            return

        # Si por algún motivo ping no puede arrancar, dejamos que el protocolo
        # IntelliVue sea la comprobación definitiva de conectividad.
        self.estado_cambiado.emit(
            "🟡 No se pudo comprobar ping; intentando asociación…"
        )
        self._iniciar_lector()

    def _iniciar_lector(self):
        if self._deteniendo:
            return

        argumentos = [
            str(self.script_path),
            "--monitor-ip", self._monitor_ip,
            "--local-ip", self._local_ip,
            "--timeout", str(self._timeout),
            "--duration", str(self._duration),
            "--json",
        ]

        self.process.setWorkingDirectory(str(self.sdk_dir))
        self.process.start(str(self.python_path), argumentos)

    def _on_started(self):
        self._conectando = True
        self.estado_cambiado.emit(
            "🟡 Asociación iniciada; esperando MDS y datos clínicos…"
        )

    def _on_finished(self, exit_code, exit_status):
        self._stdout_buffer = ""
        estaba_deteniendo = self._deteniendo
        habia_datos = self._datos_recibidos

        self._deteniendo = False
        self._conectando = False
        self._datos_recibidos = False

        if estaba_deteniendo or exit_code == 0:
            self.estado_cambiado.emit("⚪ IntelliVue desconectado")
        elif habia_datos:
            self.estado_cambiado.emit(
                f"🔴 Se perdió la conexión IntelliVue (código {exit_code})"
            )
        else:
            self.estado_cambiado.emit(
                f"🔴 No fue posible asociar con IntelliVue (código {exit_code})"
            )

    def _on_process_error(self, process_error):
        if self._deteniendo:
            return

        self._conectando = False
        self.error_recibido.emit(
            f"Error al ejecutar el lector IntelliVue: {process_error.name}"
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

            if not self._datos_recibidos:
                self._datos_recibidos = True
                self._conectando = False
                self.estado_cambiado.emit(
                    "🟢 IntelliVue conectado — datos en vivo"
                )

            self.muestra_recibida.emit(muestra)

    def _read_standard_error(self):
        message = bytes(
            self.process.readAllStandardError()
        ).decode("utf-8", errors="replace").strip()

        if message and not self._deteniendo:
            # stderr del lector se conserva para diagnóstico en terminal/UI.
            self.error_recibido.emit(message)

    def _fallar_conexion(self, mensaje):
        self._conectando = False
        self._datos_recibidos = False
        self.estado_cambiado.emit("🔴 IntelliVue no disponible")
        self.error_recibido.emit(mensaje)
