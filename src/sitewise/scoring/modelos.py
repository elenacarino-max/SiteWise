"""Las "formas" de los datos del cálculo: reglas, observaciones y resultados.

Uso pydantic para que cada objeto se valide solo y la API pueda devolverlos como JSON
sin escribir conversiones a mano.
"""

from __future__ import annotations

import operator
from enum import StrEnum
from typing import NamedTuple

from pydantic import BaseModel

# Cada símbolo del CSV ("<=", ">"...) apunta a su función de Python.
# Así comparo con OPERADORES[">="](valor, umbral) sin escribir cinco if.
OPERADORES = {
    ">=": operator.ge,
    ">": operator.gt,
    "<=": operator.le,
    "<": operator.lt,
    "==": operator.eq,
}
USOS = ("riesgo", "atractivo", "contexto")
SENTIDOS = ("directa", "inversa")


class EstadoMinimo(StrEnum):
    """Los tres estados que pide el plan para un requisito mínimo."""

    CUMPLE = "cumple"
    NO_CUMPLE = "no_cumple"
    NO_EVALUABLE = "no_evaluable"  # falta el dato: NUNCA se interpreta como "cumple"


class Observacion(NamedTuple):
    """Lo que dice el dataset de un indicador en un municipio (una fila de valores.csv)."""

    valor: float | None
    estado: str | None = None
    nivel_origen: str | None = None


class Regla(BaseModel, frozen=True):
    """Una fila del CSV de reglas por actividad.

    `sentido` es la columna que añado yo:
      - directa: valor alto -> nota alta
      - inversa: valor bajo -> nota alta (por ejemplo, distancia a la autovía)
    En riesgo, nota alta = MÁS riesgo. En atractivo, nota alta = MÁS atractivo.
    """

    actividad: str
    id_indicador: str
    uso: str = "contexto"
    peso: float | None = None
    es_requisito_minimo: bool = False
    operador: str | None = None
    umbral: float | None = None
    unidad: str = ""
    sentido: str | None = None
    justificacion: str = ""
    aprobado_por: str = ""
    fecha_aprobacion: str = ""

    @property
    def aprobada(self) -> bool:
        """Está aprobada solo si alguien la firmó y puso fecha."""
        return bool(self.aprobado_por.strip() and self.fecha_aprobacion.strip())

    @property
    def minimo_completo(self) -> bool:
        """Es un mínimo y tiene todo lo necesario para comprobarlo."""
        return self.es_requisito_minimo and self.operador in OPERADORES and self.umbral is not None

    @property
    def puntuable(self) -> bool:
        """Entra en una nota si es de riesgo/atractivo y tiene peso y sentido."""
        return (
            self.uso in ("riesgo", "atractivo")
            and self.peso is not None
            and self.peso > 0
            and self.sentido in SENTIDOS
        )


# --- Resultados (los usará el motor en el paso 2) ---


class ResultadoMinimo(BaseModel):
    """Resultado de comprobar UN requisito mínimo."""

    id_indicador: str
    operador: str | None
    umbral: float | None
    unidad: str = ""
    estado: EstadoMinimo
    valor: float | None = None
    motivo: str = ""  # por qué es no_evaluable, si lo es
    aprobada: bool = False


class Componente(BaseModel):
    """Cuánto aporta un indicador a una nota (sirve para explicar el resultado)."""

    id_indicador: str
    peso: float
    sentido: str
    valor: float | None = None
    estado_dato: str | None = None
    percentil: float | None = None
    usado: bool
    aproximado: bool = False
    motivo: str = ""
    aprobada: bool = False


class Nota(BaseModel):
    """Nota de UNA dimensión. Riesgo y atractivo van separados, nunca mezclados."""

    dimension: str  # riesgo | atractivo
    estado: str  # calculada | no_evaluable | sin_reglas
    nota: float | None = None  # de 0 a 100
    confianza: float = 0.0  # peso con dato / peso total (0 a 1)
    motivo: str = ""
    componentes: list[Componente] = []


class Evaluacion(BaseModel):
    """Todo el resultado de evaluar un municipio para una actividad."""

    cod_ine: str
    actividad: str
    riesgo: Nota
    atractivo: Nota
    cumple_minimos: EstadoMinimo
    motivo_minimos: str = ""
    minimos: list[ResultadoMinimo] = []
    reglas_provisionales: bool = True
    version_reglas: str = ""
