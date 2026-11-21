"""El motor: junta reglas, percentiles y calidad de datos y evalúa un municipio.

Dado un municipio (con sus observaciones) y una actividad, devuelvo:
  - nota de riesgo (0-100)       } separadas, nunca mezcladas en una sola
  - nota de atractivo (0-100)    }
  - si cumple los requisitos mínimos: cumple / no_cumple / no_evaluable

Idea clave: si falta un dato importante NO invento nada. Lo digo (no_evaluable)
y explico el motivo, para que la API y el agente puedan contarlo.
"""

from __future__ import annotations

from sitewise.scoring.calidad import es_aproximado, motivo_no_utilizable
from sitewise.scoring.modelos import (
    OPERADORES,
    Componente,
    EstadoMinimo,
    Evaluacion,
    Nota,
    Observacion,
    Regla,
    ResultadoMinimo,
)
from sitewise.scoring.normalizacion import Normalizador
from sitewise.scoring.reglas import ConjuntoReglas


def combinar_estados(estados: list[EstadoMinimo]) -> EstadoMinimo:
    """Junto los estados de varios mínimos en uno solo.

    - Si UNO no se cumple, el resultado es no_cumple (aunque a otros les falten datos:
      ya sé seguro que no pasa).
    - Si ninguno falla pero alguno no se puede evaluar, el resultado es no_evaluable.
    - Solo digo "cumple" si hay al menos un mínimo y TODOS se cumplen.
    """
    if EstadoMinimo.NO_CUMPLE in estados:
        return EstadoMinimo.NO_CUMPLE
    if not estados or EstadoMinimo.NO_EVALUABLE in estados:
        return EstadoMinimo.NO_EVALUABLE
    return EstadoMinimo.CUMPLE


class MotorPuntuacion:
    """Evalúa municipios con las reglas y el universo de percentiles que le doy.

    No guarda nada del municipio que evalúa entre una llamada y otra, así que
    se puede usar desde la API con varias peticiones a la vez sin que se pisen.
    """

    def __init__(
        self,
        reglas: ConjuntoReglas,
        normalizador: Normalizador,
        min_confianza: float = 0.0,
        permitir_aproximados_en_minimos: bool = True,
    ):
        self.reglas = reglas
        self.normalizador = normalizador
        # Por defecto (0) calculo la nota con los datos que haya, y la marco como parcial
        # si faltan algunos. Si se sube, una nota con menos confianza queda no_evaluable.
        # Ver docs/architecture/decision-notas-parciales.md
        self.min_confianza = min_confianza
        # Un dato aproximado a escala municipal SÍ puede evaluar un mínimo (queda marcado).
        # Con False (modo estricto) ningún dato aproximado lo certifica.
        # Un proxy PROVINCIAL nunca certifica un mínimo, ni en modo normal.
        self.permitir_aproximados_en_minimos = permitir_aproximados_en_minimos

    # ------------------------------------------------------------------ público

    def evaluar(
        self,
        cod_ine: str,
        actividad: str,
        observaciones: dict[str, Observacion],
    ) -> Evaluacion:
        """`observaciones` es un diccionario {id_indicador: Observacion} de ese municipio."""
        reglas = self.reglas.de(actividad)
        if not reglas:
            raise ValueError(f"La actividad '{actividad}' no tiene reglas definidas.")

        minimos = self._evaluar_minimos(reglas, observaciones)
        estado_minimos = combinar_estados([m.estado for m in minimos])

        if not minimos:
            motivo_minimos = "La actividad no define requisitos mínimos."
        else:
            # Lista de los mínimos que no se pueden comprobar, para explicarlo.
            pendientes = [m.id_indicador for m in minimos if m.estado == EstadoMinimo.NO_EVALUABLE]
            motivo_minimos = f"No evaluables: {', '.join(pendientes)}." if pendientes else ""

        return Evaluacion(
            cod_ine=cod_ine,
            actividad=actividad,
            riesgo=self._calcular_nota("riesgo", reglas, observaciones),
            atractivo=self._calcular_nota("atractivo", reglas, observaciones),
            cumple_minimos=estado_minimos,
            motivo_minimos=motivo_minimos,
            minimos=minimos,
            reglas_provisionales=not all(r.aprobada for r in reglas),
            version_reglas=self.reglas.version,
        )

    # ------------------------------------------------------------------ mínimos

    def _evaluar_minimos(
        self, reglas: list[Regla], obs: dict[str, Observacion]
    ) -> list[ResultadoMinimo]:
        resultados = []
        for regla in reglas:
            if not regla.es_requisito_minimo:
                continue

            base = {
                "id_indicador": regla.id_indicador,
                "operador": regla.operador,
                "umbral": regla.umbral,
                "unidad": regla.unidad,
                "aprobada": regla.aprobada,
            }

            # Caso 1: la regla está a medias (falta el operador o el umbral).
            if not regla.minimo_completo:
                resultados.append(ResultadoMinimo(
                    **base, estado=EstadoMinimo.NO_EVALUABLE,
                    motivo="regla de mínimo incompleta (falta operador o umbral)",
                ))
                continue

            # Caso 2: no tengo el dato, o no es utilizable.
            o = obs.get(regla.id_indicador)
            motivo = (
                "el municipio no tiene observación de este indicador"
                if o is None
                else motivo_no_utilizable(
                    o.valor,
                    o.estado,
                    o.nivel_origen,
                    permitir_aproximados=self.permitir_aproximados_en_minimos,
                    permitir_proxies=False,  # un proxy provincial nunca certifica un mínimo
                )
            )
            if motivo:
                resultados.append(ResultadoMinimo(
                    **base, estado=EstadoMinimo.NO_EVALUABLE,
                    valor=o.valor if o else None, motivo=motivo,
                ))
                continue

            # Caso 3: tengo el dato, comparo. OPERADORES[">="] es la función "mayor o igual".
            cumple = OPERADORES[regla.operador](o.valor, regla.umbral)
            aproximado = es_aproximado(o.estado, o.nivel_origen)
            resultados.append(ResultadoMinimo(
                **base,
                estado=EstadoMinimo.CUMPLE if cumple else EstadoMinimo.NO_CUMPLE,
                valor=o.valor,
                aproximado=aproximado,
                # Si el dato es aproximado lo digo junto al resultado, para no darlo por exacto.
                aviso=(
                    f"evaluado con un dato aproximado (estado: {o.estado}, nivel: {o.nivel_origen})"
                    if aproximado else ""
                ),
            ))
        return resultados

    # -------------------------------------------------------------------- notas

    def _calcular_nota(
        self, dimension: str, reglas: list[Regla], obs: dict[str, Observacion]
    ) -> Nota:
        """Media ponderada de percentiles. `dimension` es 'riesgo' o 'atractivo'."""
        de_la_dimension = [r for r in reglas if r.uso == dimension]
        puntuables = [r for r in de_la_dimension if r.puntuable]
        sin_usar = len(de_la_dimension) - len(puntuables)

        if not puntuables:
            return Nota(
                dimension=dimension,
                estado="sin_reglas",
                motivo=f"La actividad no tiene reglas completas (peso y sentido) para {dimension}.",
            )

        componentes: list[Componente] = []
        suma_ponderada = 0.0  # suma de peso * percentil
        peso_con_dato = 0.0

        for regla in puntuables:
            o = obs.get(regla.id_indicador)
            motivo = (
                "el municipio no tiene observación de este indicador"
                if o is None
                else motivo_no_utilizable(o.valor, o.estado, o.nivel_origen, True)
            )
            percentil = None
            if not motivo:
                percentil = self.normalizador.percentil(regla.id_indicador, o.valor)
                if percentil is None:
                    motivo = "no hay universo de comparación para este indicador"

            comp = Componente(
                id_indicador=regla.id_indicador,
                peso=regla.peso,
                sentido=regla.sentido,
                valor=o.valor if o else None,
                estado_dato=o.estado if o else None,
                percentil=percentil,
                usado=not motivo,  # motivo vacío o None = el dato se puede usar
                aproximado=es_aproximado(o.estado, o.nivel_origen) if o else False,
                motivo=motivo or "",
                aprobada=regla.aprobada,
            )
            componentes.append(comp)

            if comp.usado:
                # Sentido inversa: valor bajo = nota alta, así que doy la vuelta al percentil.
                puntos = 100 - percentil if regla.sentido == "inversa" else percentil
                suma_ponderada += regla.peso * puntos
                peso_con_dato += regla.peso

        peso_total = sum(r.peso for r in puntuables)
        confianza = peso_con_dato / peso_total  # 1.0 = tengo todos los datos

        # Solo digo "no_evaluable" si no hay NINGÚN dato (o si el equipo exige un mínimo).
        if peso_con_dato == 0 or confianza < self.min_confianza:
            return Nota(
                dimension=dimension,
                estado="no_evaluable",
                confianza=round(confianza, 4),
                motivo=(
                    "no hay ningún dato utilizable"
                    if peso_con_dato == 0
                    else f"solo hay dato para el {confianza:.0%} del peso "
                    f"(mínimo exigido: {self.min_confianza:.0%})"
                ),
                componentes=componentes,
            )

        # Con todos los datos la nota es "calculada"; si falta alguno es "calculada_parcial"
        # y lo digo en el motivo, para que nadie la lea como una nota completa.
        avisos = []
        if confianza < 1:
            avisos.append(f"nota provisional: solo hay dato para el {confianza:.0%} del peso.")
        if sin_usar:
            avisos.append(f"{sin_usar} regla(s) sin peso o sentido no se han usado.")
        return Nota(
            dimension=dimension,
            estado="calculada" if confianza >= 1 else "calculada_parcial",
            nota=round(suma_ponderada / peso_con_dato, 2),
            confianza=round(confianza, 4),
            motivo=" ".join(avisos),
            componentes=componentes,
        )
