from __future__ import annotations

import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal


class IntelliVueConnection(QObject):
    """Puente Qt entre Registro de Anestesia y PhilipsSession."""

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
        self._session = None
        self._deteniendo = False
        self._lock = threading.Lock()

    @property
    def activo(self):
        with self._lock:
            session = self._session
        if session is None:
            return False
        try:
            state = session.state.value
        except Exception:
            return False
        return state not in {"idle", "error"}

    def _validar_sdk(self):
        if not self.sdk_dir.exists():
            raise FileNotFoundError(
                f"No existe el SDK USS Anestesia: {self.sdk_dir}"
            )
        if not self.python_path.exists():
            raise FileNotFoundError(
                f"No existe el Python del SDK: {self.python_path}"
            )
        package_dir = self.sdk_dir / "philips_intellivue"
        for filename in ("philips_session.py", "clinical_runner.py", "dhcp_service.py"):
            path = package_dir / filename
            if not path.exists():
                raise FileNotFoundError(f"Falta componente del SDK: {path}")

    def iniciar(
        self,
        monitor_ip="192.168.50.2",
        local_ip="192.168.50.1",
        timeout=15,
        duration=21600,
        interface="en8",
        client_mac="00:09:fb:88:bf:13",
    ):
        if self.activo:
            raise RuntimeError("La conexión IntelliVue ya está en curso")

        self._validar_sdk()

        sdk_text = str(self.sdk_dir)
        if sdk_text not in sys.path:
            sys.path.insert(0, sdk_text)

        from philips_intellivue.clinical_runner import LiveVitalsRunner
        from philips_intellivue.philips_session import (
            PhilipsSession,
            PhilipsSessionConfig,
        )

        config = PhilipsSessionConfig(
            interface=str(interface),
            local_ip=str(local_ip),
            monitor_ip=str(monitor_ip),
            client_mac=str(client_mac),
            clinical_duration=float(duration),
            association_timeout=float(timeout),
        )

        def clinical_factory(**callbacks):
            return LiveVitalsRunner(
                sdk_dir=self.sdk_dir,
                python_executable=self.python_path,
                **callbacks,
            )

        session = PhilipsSession(
            config,
            on_status=self._on_status,
            on_error=self._on_error,
            on_state=self._on_state,
            on_sample=self._on_sample,
            clinical_factory=clinical_factory,
        )

        with self._lock:
            self._session = session
        self._deteniendo = False

        self.estado_cambiado.emit("🟡 Preparando sesión IntelliVue…")
        session.start(background=True, clinical=True)

    def detener(self):
        with self._lock:
            session = self._session

        if session is None:
            self.estado_cambiado.emit("⚪ Philips IntelliVue desconectado")
            return

        if self._deteniendo:
            return

        self._deteniendo = True
        self.estado_cambiado.emit("🟡 Desconectando Philips IntelliVue…")

        threading.Thread(
            target=self._detener_worker,
            args=(session,),
            name="QtPhilipsSessionStop",
            daemon=True,
        ).start()

    def _detener_worker(self, session):
        try:
            session.stop()
        except Exception as exc:
            self.error_recibido.emit(f"Error al detener PhilipsSession: {exc}")
        finally:
            with self._lock:
                if self._session is session:
                    self._session = None
            self._deteniendo = False
            self.estado_cambiado.emit("⚪ Philips IntelliVue desconectado")

    def _on_sample(self, sample):
        if isinstance(sample, dict):
            self.muestra_recibida.emit(sample)

    def _on_status(self, message):
        message = str(message)
        if "IntelliVue conectado — datos en vivo" in message:
            self.estado_cambiado.emit("🟢 IntelliVue conectado — datos en vivo")
        elif message.startswith("DHCP:"):
            self.estado_cambiado.emit(f"🟡 {message}")
        elif "reintentando" in message:
            self.estado_cambiado.emit(f"🟡 {message}")
        elif "Red IntelliVue lista" in message:
            self.estado_cambiado.emit("🟡 Red lista; asociando IntelliVue…")
        elif "Association/MDS" in message or "iniciando Association" in message:
            self.estado_cambiado.emit("🟡 Asociando; esperando MDS y datos…")
        elif message:
            self.estado_cambiado.emit(message)

    def _on_error(self, message):
        text = str(message)
        lower = text.lower()
        if (
            "permission" in lower
            or "operation not permitted" in lower
            or "udp/67" in lower
            or "puerto 67" in lower
        ):
            text = (
                "macOS no autorizó abrir el servicio DHCP (UDP/67). "
                "La PhilipsSession ya está integrada al Registro, pero para una "
                "conexión desde cero falta el helper de autorización nativo de macOS. "
                f"Detalle: {message}"
            )
        self.error_recibido.emit(text)
        self.estado_cambiado.emit("🔴 Error de conexión IntelliVue")

    def _on_state(self, state):
        value = getattr(state, "value", str(state))
        mapping = {
            "checking_network": "🟡 Verificando red IntelliVue…",
            "starting_dhcp": "🟡 Preparando DHCP/BootP…",
            "waiting_for_lease": "🟡 Esperando IP del IntelliVue…",
            "waiting_for_monitor": "🟡 Esperando que el monitor quede disponible…",
            "network_ready": "🟡 Red lista; preparando asociación…",
            "associating": "🟡 Asociando con IntelliVue…",
            "waiting_for_data": "🟡 Esperando MDS y primera muestra clínica…",
            "streaming": "🟢 IntelliVue conectado — datos en vivo",
            "stopping": "🟡 Desconectando Philips IntelliVue…",
            "idle": "⚪ Philips IntelliVue desconectado",
            "error": "🔴 Error de conexión IntelliVue",
        }
        text = mapping.get(value)
        if text:
            self.estado_cambiado.emit(text)
