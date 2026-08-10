from __future__ import annotations

import os
import shlex
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal


class IntelliVueConnection(QObject):
    """Qt bridge for a complete PhilipsSession, including macOS cold-start DHCP."""

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
        self.helper_path = Path(__file__).with_name(
            "intellivue_dhcp_macos_helper.py"
        )

        self._session = None
        self._deteniendo = False
        self._preparing = False
        self._lock = threading.Lock()
        self._cancel = threading.Event()

        self._helper_stop_file = None
        self._helper_ready_file = None
        self._helper_error_file = None
        self._helper_log_file = None

    @property
    def activo(self):
        with self._lock:
            session = self._session
            preparing = self._preparing

        if preparing:
            return True
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
        if not self.helper_path.exists():
            raise FileNotFoundError(
                f"No existe el helper DHCP de macOS: {self.helper_path}"
            )

        package_dir = self.sdk_dir / "philips_intellivue"
        for filename in (
            "philips_session.py",
            "clinical_runner.py",
            "dhcp_service.py",
        ):
            path = package_dir / filename
            if not path.exists():
                raise FileNotFoundError(
                    f"Falta componente del SDK: {path}"
                )

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
        self._cancel.clear()
        self._deteniendo = False

        with self._lock:
            self._preparing = True

        self.estado_cambiado.emit("🟡 Preparando sesión IntelliVue…")

        threading.Thread(
            target=self._iniciar_worker,
            kwargs=dict(
                monitor_ip=str(monitor_ip),
                local_ip=str(local_ip),
                timeout=float(timeout),
                duration=float(duration),
                interface=str(interface),
                client_mac=str(client_mac),
            ),
            name="QtPhilipsSessionStart",
            daemon=True,
        ).start()

    def _iniciar_worker(
        self,
        *,
        monitor_ip,
        local_ip,
        timeout,
        duration,
        interface,
        client_mac,
    ):
        try:
            sdk_text = str(self.sdk_dir)
            if sdk_text not in sys.path:
                sys.path.insert(0, sdk_text)

            from philips_intellivue.clinical_runner import LiveVitalsRunner
            from philips_intellivue.philips_session import (
                PhilipsSession,
                PhilipsSessionConfig,
                ping_once,
            )

            # If the monitor already has its lease, no authorization is needed.
            if not ping_once(monitor_ip):
                self.estado_cambiado.emit(
                    "🟡 IntelliVue sin IPv4; solicitando autorización de macOS…"
                )
                self._start_privileged_dhcp(
                    interface=interface,
                    local_ip=local_ip,
                    monitor_ip=monitor_ip,
                    client_mac=client_mac,
                )

                self.estado_cambiado.emit(
                    "🟡 DHCP autorizado; esperando que el IntelliVue obtenga IP…"
                )
                deadline = time.monotonic() + 60.0
                while not self._cancel.is_set() and time.monotonic() < deadline:
                    if ping_once(monitor_ip):
                        break

                    error_file = self._helper_error_file
                    if error_file and error_file.exists():
                        detail = error_file.read_text(
                            encoding="utf-8",
                            errors="replace",
                        ).strip()
                        raise RuntimeError(
                            f"El helper DHCP terminó con error: {detail}"
                        )
                    time.sleep(0.5)
                else:
                    if self._cancel.is_set():
                        return
                    raise TimeoutError(
                        "El IntelliVue no obtuvo 192.168.50.2 dentro de 60 s."
                    )

            if self._cancel.is_set():
                return

            config = PhilipsSessionConfig(
                interface=interface,
                local_ip=local_ip,
                monitor_ip=monitor_ip,
                client_mac=client_mac,
                clinical_duration=duration,
                association_timeout=timeout,
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
                self._preparing = False

            session.start(background=True, clinical=True)

        except subprocess.CalledProcessError as exc:
            # osascript returns non-zero when authorization is cancelled.
            detail = (exc.stderr or exc.stdout or "").strip()
            if "User canceled" in detail or "(-128)" in detail:
                self.error_recibido.emit(
                    "Se canceló la autorización de macOS para iniciar DHCP."
                )
            else:
                self.error_recibido.emit(
                    f"No fue posible autorizar DHCP en macOS: {detail or exc}"
                )
            self.estado_cambiado.emit("🔴 Error de conexión IntelliVue")
            self._finish_failed_start()

        except Exception as exc:
            if not self._cancel.is_set():
                self.error_recibido.emit(str(exc))
                self.estado_cambiado.emit("🔴 Error de conexión IntelliVue")
            self._finish_failed_start()

    def _finish_failed_start(self):
        with self._lock:
            self._preparing = False
            self._session = None
        self._stop_privileged_dhcp()

    @staticmethod
    def _apple_script_string(text: str) -> str:
        return text.replace("\\", "\\\\").replace('"', '\\"')

    def _start_privileged_dhcp(
        self,
        *,
        interface,
        local_ip,
        monitor_ip,
        client_mac,
    ):
        token = uuid.uuid4().hex
        temp = Path(tempfile.gettempdir())

        self._helper_stop_file = temp / f"uss_anestesia_dhcp_{token}.stop"
        self._helper_ready_file = temp / f"uss_anestesia_dhcp_{token}.ready"
        self._helper_error_file = temp / f"uss_anestesia_dhcp_{token}.error"
        self._helper_log_file = temp / f"uss_anestesia_dhcp_{token}.log"

        for path in (
            self._helper_stop_file,
            self._helper_ready_file,
            self._helper_error_file,
            self._helper_log_file,
        ):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

        args = [
            str(self.python_path),
            str(self.helper_path),
            "--sdk-dir", str(self.sdk_dir),
            "--interface", interface,
            "--server-ip", local_ip,
            "--client-ip", monitor_ip,
            "--client-mac", client_mac,
            "--subnet", "255.255.255.0",
            "--lease", "3600",
            "--stop-file", str(self._helper_stop_file),
            "--ready-file", str(self._helper_ready_file),
            "--error-file", str(self._helper_error_file),
            "--parent-pid", str(os.getpid()),
        ]

        command = " ".join(shlex.quote(arg) for arg in args)
        command += (
            f" </dev/null >>{shlex.quote(str(self._helper_log_file))} 2>&1 &"
        )

        apple = (
            'do shell script "'
            + self._apple_script_string(command)
            + '" with administrator privileges'
        )

        subprocess.run(
            ["/usr/bin/osascript", "-e", apple],
            check=True,
            text=True,
            capture_output=True,
        )

        deadline = time.monotonic() + 8.0
        while not self._cancel.is_set() and time.monotonic() < deadline:
            if self._helper_ready_file.exists():
                return
            if self._helper_error_file.exists():
                detail = self._helper_error_file.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).strip()
                raise RuntimeError(
                    f"No se pudo iniciar DHCP privilegiado: {detail}"
                )
            time.sleep(0.1)

        if self._cancel.is_set():
            raise RuntimeError("Conexión cancelada")

        raise TimeoutError(
            "macOS autorizó el helper, pero DHCP no confirmó su inicio."
        )

    def _stop_privileged_dhcp(self):
        stop_file = self._helper_stop_file
        if stop_file is not None:
            try:
                stop_file.touch()
            except Exception:
                pass

        # Give the privileged helper a moment to close UDP/67 gracefully.
        time.sleep(0.3)

        for attr in (
            "_helper_stop_file",
            "_helper_ready_file",
            "_helper_error_file",
        ):
            path = getattr(self, attr, None)
            if path is not None:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                except Exception:
                    pass
                setattr(self, attr, None)

    def detener(self):
        self._cancel.set()

        with self._lock:
            session = self._session
            preparing = self._preparing

        if self._deteniendo:
            return

        self._deteniendo = True
        self.estado_cambiado.emit("🟡 Desconectando Philips IntelliVue…")

        threading.Thread(
            target=self._detener_worker,
            args=(session, preparing),
            name="QtPhilipsSessionStop",
            daemon=True,
        ).start()

    def _detener_worker(self, session, preparing):
        try:
            if session is not None:
                session.stop()
        except Exception as exc:
            self.error_recibido.emit(
                f"Error al detener PhilipsSession: {exc}"
            )
        finally:
            self._stop_privileged_dhcp()
            with self._lock:
                self._session = None
                self._preparing = False
            self._deteniendo = False
            self.estado_cambiado.emit("⚪ Philips IntelliVue desconectado")

    def _on_sample(self, sample):
        if isinstance(sample, dict):
            self.muestra_recibida.emit(sample)

    def _on_status(self, message):
        message = str(message)
        if "IntelliVue conectado — datos en vivo" in message:
            self.estado_cambiado.emit(
                "🟢 IntelliVue conectado — datos en vivo"
            )
        elif "reintentando" in message:
            self.estado_cambiado.emit(f"🟡 {message}")
        elif "Red IntelliVue lista" in message:
            self.estado_cambiado.emit(
                "🟡 Red lista; asociando IntelliVue…"
            )
        elif (
            "Association/MDS" in message
            or "iniciando Association" in message
        ):
            self.estado_cambiado.emit(
                "🟡 Asociando; esperando MDS y datos…"
            )
        elif message:
            self.estado_cambiado.emit(message)

    def _on_error(self, message):
        self.error_recibido.emit(str(message))
        self.estado_cambiado.emit("🔴 Error de conexión IntelliVue")

    def _on_state(self, state):
        value = getattr(state, "value", str(state))
        mapping = {
            "checking_network": "🟡 Verificando red IntelliVue…",
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
