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
    ListaActividades,
    ListaMunicipios,
    Municipio,
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
        indicadores = []
        for d in self.repo.detalle_indicadores(cod_ine):
            motivo = motivo_no_utilizable(d["valor"], d["estado"], d["nivel_origen"])
            indicadores.append(ValorIndicador(
                **d,
                aproximado=es_aproximado(d["estado"], d["nivel_origen"]),
                utilizable=motivo is None,
                motivo_no_utilizable=motivo,
            ))
        return FichaMunicipio(municipio=municipio, indicadores=indicadores)

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
