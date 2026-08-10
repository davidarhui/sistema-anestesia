# Módulo Philips IntelliVue

Versión corregida para macOS: el listener se une explícitamente al grupo multicast IPv6 `ff02::1` sobre la interfaz seleccionada.

## Ejecución

```bash
python3 philips_discovery_cli.py --interface en8 --hex
```

La versión actual es pasiva y no envía comandos al monitor.

Correcciones de esta revisión:
- elimina la falsa segunda MAC derivada del EUI-64 IPv6;
- conserva correctamente el cero final de `A.00.30`.
