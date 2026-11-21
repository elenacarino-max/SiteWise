"""Leo las reglas de cada actividad desde un CSV.

El CSV tiene las columnas de `plantilla_pesos_actividad.csv` más una que añado,
`sentido` (directa / inversa). Los pesos y mínimos NO los pongo yo en el código:
salen del fichero que apruebe el equipo (así lo pide configs/README.md).
Una regla sin `aprobado_por` y `fecha_aprobacion` queda como PROVISIONAL.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from pydantic import ValidationError

from sitewise.scoring.modelos import OPERADORES, SENTIDOS, USOS, Regla


class ErrorReglas(ValueError):
    """Lo lanzo cuando el CSV tiene algo mal escrito (operador raro, peso no numérico...)."""


def _texto(fila: dict[str, str | None], clave: str) -> str:
    # csv.DictReader da None si la celda falta; lo convierto en "" y quito espacios.
    return (fila.get(clave) or "").strip()


def _numero(fila: dict[str, str | None], clave: str, linea: int) -> float | None:
    bruto = _texto(fila, clave)
    if not bruto:
        return None  # celda vacía = sin valor (no es un error)
    try:
        return float(bruto.replace(",", "."))  # acepto coma decimal: 0,5
    except ValueError as exc:
        raise ErrorReglas(f"línea {linea}: '{clave}' no es un número ({bruto!r})") from exc


def _booleano(texto: str) -> bool:
    """Interpreto 'sí', 'si', 'true', '1', 'x'... como verdadero."""
    return texto.strip().lower() in {"1", "si", "sí", "s", "true", "verdadero", "x", "yes"}


class ConjuntoReglas:
    """Todas las reglas del fichero, agrupadas por actividad."""

    def __init__(self, reglas: list[Regla], version: str = "sin_reglas"):
        self.version = version  # huella del fichero: sirve para saber con qué reglas se calculó
        self._por_actividad: dict[str, list[Regla]] = {}
        for regla in reglas:
            self._por_actividad.setdefault(regla.actividad, []).append(regla)

    def actividades(self) -> list[str]:
        return sorted(self._por_actividad)

    def existe(self, actividad: str) -> bool:
        return actividad in self._por_actividad

    def de(self, actividad: str) -> list[Regla]:
        return list(self._por_actividad.get(actividad, []))

    def resumen(self, actividad: str) -> dict[str, object]:
        """Datos para listar la actividad en la API: cuántas reglas, si están aprobadas..."""
        reglas = self.de(actividad)
        aprobadas = sum(r.aprobada for r in reglas)
        # Solo digo "aprobadas" si TODAS lo están; si no, provisionales.
        estado = "aprobadas" if reglas and aprobadas == len(reglas) else "provisionales"
        return {
            "actividad": actividad,
            "estado_reglas": estado,
            "n_reglas": len(reglas),
            "n_minimos": sum(r.es_requisito_minimo for r in reglas),
            "n_puntuables": sum(r.puntuable for r in reglas),
            "n_aprobadas": aprobadas,
            "version_reglas": self.version,
        }


def cargar_reglas(ruta: str | Path) -> ConjuntoReglas:
    """Leo el CSV. Si el fichero no existe devuelvo un conjunto vacío (todo pendiente)."""
    ruta = Path(ruta)
    if not ruta.is_file():
        return ConjuntoReglas([])

    contenido = ruta.read_bytes()
    # Huella corta del contenido: si alguien cambia un peso, cambia la versión.
    version = hashlib.sha1(contenido).hexdigest()[:8]
    # utf-8-sig quita la marca BOM que Excel añade al guardar CSV
    lector = csv.DictReader(contenido.decode("utf-8-sig").splitlines())
    reglas: list[Regla] = []

    # start=2 porque la línea 1 es la cabecera: así el número de línea coincide con Excel.
    for linea, fila in enumerate(lector, start=2):
        if not any((v or "").strip() for v in fila.values()):
            continue  # salto las filas completamente vacías

        uso = _texto(fila, "uso_en_actividad").lower() or "contexto"
        operador = _texto(fila, "operador") or None
        sentido = _texto(fila, "sentido").lower() or None

        # Valido los valores cerrados para fallar pronto y con un mensaje claro.
        if uso not in USOS:
            raise ErrorReglas(f"línea {linea}: uso_en_actividad '{uso}' no válido ({USOS})")
        if operador is not None and operador not in OPERADORES:
            raise ErrorReglas(f"línea {linea}: operador '{operador}' no válido")
        if sentido is not None and sentido not in SENTIDOS:
            raise ErrorReglas(f"línea {linea}: sentido '{sentido}' no válido ({SENTIDOS})")

        try:
            reglas.append(Regla(
                actividad=_texto(fila, "actividad"),
                id_indicador=_texto(fila, "id_indicador"),
                uso=uso,
                peso=_numero(fila, "peso", linea),
                es_requisito_minimo=_booleano(_texto(fila, "es_requisito_minimo")),
                operador=operador,
                umbral=_numero(fila, "umbral", linea),
                unidad=_texto(fila, "unidad"),
                sentido=sentido,
                justificacion=_texto(fila, "justificacion"),
                aprobado_por=_texto(fila, "aprobado_por"),
                fecha_aprobacion=_texto(fila, "fecha_aprobacion"),
            ))
        except ValidationError as exc:
            raise ErrorReglas(f"línea {linea}: {exc}") from exc

    return ConjuntoReglas(reglas, version=version)
