"""Une el repositorio de datos con las respuestas de la API.

No guarda ningún dato de una petición entre una llamada y otra: así varias peticiones a la vez
no se pisan (el problema que tenía el estado compartido del analista del agente).
"""

from __future__ import annotations

from sitewise.db.repositorio import RepositorioCSV
from sitewise.scoring.calidad import es_aproximado, motivo_no_utilizable
from sitewise.scoring.motor import MotorPuntuacion
from sitewise.scoring.normalizacion import Normalizador
from sitewise.scoring.reglas import ConjuntoReglas

from .schemas import (
    FichaMunicipio,
    FilaResumen,
    IndicadorComparado,
    ListaActividades,
    ListaMunicipios,
    Municipio,
    RespuestaComparacion,
    RespuestaEvaluacion,
    ResumenActividad,
    Salud,
    ValorIndicador,
)


class Servicio:
    def __init__(self, repositorio: RepositorioCSV, reglas: ConjuntoReglas | None = None):
        self.repo = repositorio
        self.reglas = reglas or ConjuntoReglas([])
        # El normalizador aprende UNA vez cómo se reparten los valores en España (tarda unos
        # segundos con los datos reales). Después no cambia: las peticiones solo lo leen.
        self.motor = MotorPuntuacion(self.reglas, Normalizador(repositorio.valores))

    def salud(self) -> Salud:
        info = self.repo.info()
        return Salud(
            estado="ok",
            datos_cargados=True,
            municipios=info["municipios"],
            indicadores=info["indicadores"],
            observaciones=info["observaciones"],
        )

    def buscar(self, q, provincia, ccaa, limite: int, desplazamiento: int) -> ListaMunicipios:
        total, pagina = self.repo.buscar_municipios(q, provincia, ccaa, limite, desplazamiento)
        return ListaMunicipios(
            total=total,
            limite=limite,
            desplazamiento=desplazamiento,
            municipios=[Municipio(**m) for m in pagina],
        )

    def municipio(self, cod_ine: str) -> Municipio | None:
        datos = self.repo.municipio(cod_ine)
        return Municipio(**datos) if datos else None

    def ficha(self, cod_ine: str) -> FichaMunicipio | None:
        municipio = self.municipio(cod_ine)
        if municipio is None:
            return None
        indicadores = [self._valor_indicador(d) for d in self.repo.detalle_indicadores(cod_ine)]
        return FichaMunicipio(municipio=municipio, indicadores=indicadores)

    @staticmethod
    def _valor_indicador(d: dict) -> ValorIndicador:
        """Convierte una fila del repositorio en un valor con su trazabilidad y su utilizabilidad."""
        motivo = motivo_no_utilizable(d["valor"], d["estado"], d["nivel_origen"])
        return ValorIndicador(
            **d,
            aproximado=es_aproximado(d["estado"], d["nivel_origen"]),
            utilizable=motivo is None,
            motivo_no_utilizable=motivo,
        )

    # ------------------------------------------------------------------ actividades

    def existe_actividad(self, actividad: str) -> bool:
        return self.reglas.existe(actividad)

    def actividades(self) -> ListaActividades:
        resumenes = [ResumenActividad(**self.reglas.resumen(a)) for a in self.reglas.actividades()]
        if not resumenes:
            aviso = "Todavía no hay reglas de actividad cargadas: las aprueba el equipo."
        elif any(r.estado_reglas == "provisionales" for r in resumenes):
            aviso = "Hay reglas provisionales (sin aprobar): los resultados no son definitivos."
        else:
            aviso = ""
        return ListaActividades(actividades=resumenes, aviso=aviso)

    def evaluar(self, cod_ine: str, actividad: str) -> RespuestaEvaluacion | None:
        """Evalúa un municipio para una actividad. None si el municipio no existe.

        Quien llama debe comprobar antes que la actividad existe (`existe_actividad`).
        """
        municipio = self.municipio(cod_ine)
        if municipio is None:
            return None
        evaluacion = self.motor.evaluar(cod_ine, actividad, self.repo.observaciones(cod_ine))
        return RespuestaEvaluacion(municipio=municipio, evaluacion=evaluacion)

    def comparar(self, codigos: list[str], actividad: str) -> RespuestaComparacion:
        """Compara varios municipios (ya validados) para una actividad, en el orden pedido.

        Quien llama debe comprobar antes que los municipios y la actividad existen.
        """
        evaluaciones = [self.evaluar(cod, actividad) for cod in codigos]
        resumen = [
            FilaResumen(
                cod_ine=e.municipio.cod_ine,
                nombre=e.municipio.nombre,
                riesgo_nota=e.evaluacion.riesgo.nota,
                riesgo_estado=e.evaluacion.riesgo.estado,
                riesgo_confianza=e.evaluacion.riesgo.confianza,
                atractivo_nota=e.evaluacion.atractivo.nota,
                atractivo_estado=e.evaluacion.atractivo.estado,
                atractivo_confianza=e.evaluacion.atractivo.confianza,
                cumple_minimos=e.evaluacion.cumple_minimos.value,
            )
            for e in evaluaciones
        ]

        # Tabla indicador a indicador: solo los que usan las reglas de la actividad.
        detalle = {
            cod: {d["id_indicador"]: self._valor_indicador(d) for d in self.repo.detalle_indicadores(cod)}
            for cod in codigos
        }
        indicadores: list[IndicadorComparado] = []
        vistos: set[str] = set()
        for regla in self.reglas.de(actividad):
            if regla.id_indicador in vistos:
                continue
            vistos.add(regla.id_indicador)
            valores = {cod: detalle[cod].get(regla.id_indicador) for cod in codigos}
            ejemplo = next((v for v in valores.values() if v is not None), None)
            indicadores.append(IndicadorComparado(
                id_indicador=regla.id_indicador,
                nombre=ejemplo.nombre if ejemplo else None,
                unidad=(ejemplo.unidad if ejemplo else None) or regla.unidad or None,
                uso=regla.uso,
                valores=valores,
            ))

        primera = evaluaciones[0].evaluacion
        return RespuestaComparacion(
            actividad=actividad,
            version_reglas=primera.version_reglas,
            reglas_provisionales=primera.reglas_provisionales,
            resumen=resumen,
            indicadores=indicadores,
            evaluaciones=evaluaciones,
        )
