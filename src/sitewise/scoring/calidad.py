"""Decido cuándo un dato se puede usar para calcular.

Reglas que sigo (vienen del diccionario del dataset, apartado "Reglas de uso"):
- Que falte un dato NO significa que valga 0. Si no hay valor, no lo invento.
- Un dato aproximado o provincial (un "proxy") no lo uso para certificar un
  requisito mínimo, porque no es una medición del municipio.
"""

from __future__ import annotations

import math

# Estados del dataset v0.3 en los que NO hay un valor utilizable.
# (la lista sale de la tabla "Valores controlados de estado" del diccionario)
ESTADOS_SIN_VALOR = frozenset({
    "base_cero",
    "blanco_fuente",
    "ocultado_menor5",
    "fusion_con_celdas_no_publicadas",
    "cobertura_insuficiente",
    "sin_cobertura_suficiente",
    "sin_datos_comparables",
    "sin_destino_catalogado_en_tierra",
    "sin_masa_catalogada",
    "sin_poligonos_en_catalogo",
    "pendiente",
})

# Estados en los que el valor es una estimación, no una medición directa.
ESTADOS_APROXIMADOS = frozenset({"aproximado", "aproximado_modelo"})


def es_nulo(valor: float | None) -> bool:
    """True si no hay valor: None o NaN (pandas usa NaN para los huecos)."""
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


def es_aproximado(estado: str | None, nivel_origen: str | None) -> bool:
    """True si el dato es un proxy: estado aproximado o procedente de nivel provincial."""
    # "estado or ''" evita errores cuando estado viene como None
    return (estado or "") in ESTADOS_APROXIMADOS or "provinc" in (nivel_origen or "").lower()


def motivo_no_utilizable(
    valor: float | None,
    estado: str | None,
    nivel_origen: str | None,
    permitir_aproximados: bool = True,
) -> str | None:
    """Devuelve el motivo por el que el dato no sirve, o None si SÍ se puede usar.

    Devuelvo el motivo (y no solo True/False) para poder enseñárselo al usuario
    en la API: "no evaluable porque ...".
    """
    if es_nulo(valor):
        return f"sin valor (estado: {estado or 'desconocido'})"
    if (estado or "") in ESTADOS_SIN_VALOR:
        return f"estado '{estado}': el dato no es utilizable"
    if not permitir_aproximados and es_aproximado(estado, nivel_origen):
        return "dato aproximado o proxy: no certifica un requisito municipal"
    return None
