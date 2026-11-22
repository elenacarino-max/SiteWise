"""Convierto un valor en un percentil (0-100) comparándolo con todos los municipios.

Por qué percentil: los indicadores tienen unidades distintas (km, %, hectáreas...).
Con el percentil todos quedan en la misma escala y se pueden combinar con pesos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sitewise.scoring.calidad import ESTADOS_SIN_VALOR


class Normalizador:
    """Aprende una vez cómo se reparten los valores de cada indicador en España.

    Después, `percentil()` dice en qué posición queda un valor concreto.
    No depende del municipio que evalúo: el "universo" es siempre el mismo.
    """

    def __init__(self, observaciones: pd.DataFrame):
        # `observaciones` es la tabla larga de valores.csv: una fila por municipio e
        # indicador, con las columnas id_indicador, valor y estado.
        estado = observaciones["estado"].fillna("") if "estado" in observaciones else ""
        valor = pd.to_numeric(observaciones["valor"], errors="coerce")  # texto raro -> NaN

        # Me quedo solo con los valores utilizables: con número y sin estado "sin valor".
        mascara = valor.notna() & ~pd.Series(estado, index=observaciones.index).isin(ESTADOS_SIN_VALOR)
        utiles = pd.DataFrame({"id": observaciones["id_indicador"], "valor": valor})[mascara]

        # Guardo, para cada indicador, sus valores ordenados de menor a mayor.
        # Con la lista ordenada puedo calcular el percentil muy rápido.
        self._orden: dict[str, np.ndarray] = {
            str(k): np.sort(g.to_numpy(dtype=float)) for k, g in utiles.groupby("id")["valor"]
        }

    def n(self, id_indicador: str) -> int:
        """Cuántos municipios tienen dato utilizable de este indicador."""
        return len(self._orden.get(id_indicador, ()))

    def percentil(self, id_indicador: str, valor: float) -> float | None:
        """Percentil de `valor`. Devuelve None si no hay universo para ese indicador.

        Uso el "rango medio": los valores por debajo cuentan entero y los iguales
        cuentan a medias. Ejemplo con [10, 20, 30, 40] y valor 30:
        2 por debajo + 1 igual => (2 + 3) / (2 * 4) = 0,625 => 62,5
        """
        orden = self._orden.get(id_indicador)
        if orden is None or len(orden) == 0:
            return None
        # searchsorted 'left' = cuántos valores hay estrictamente menores
        # searchsorted 'right' = cuántos son menores o iguales
        menores = np.searchsorted(orden, valor, side="left")
        menores_o_iguales = np.searchsorted(orden, valor, side="right")
        return float(100.0 * (menores + menores_o_iguales) / (2 * len(orden)))
