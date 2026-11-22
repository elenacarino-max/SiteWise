"""Une el repositorio de datos con las respuestas de la API.

No guarda ningún dato de una petición entre una llamada y otra: así varias peticiones a la vez
no se pisan (el problema que tenía el estado compartido del analista del agente).
"""

from __future__ import annotations

import threading

from sitewise.db.repositorio import RepositorioCSV, sin_acentos
from sitewise.scoring.calidad import es_aproximado, motivo_no_utilizable
from sitewise.scoring.motor import MotorPuntuacion
from sitewise.scoring.normalizacion import Normalizador
from sitewise.scoring.reglas import ConjuntoReglas

from .schemas import (
    FichaMunicipio,
    FilaMapa,
    FilaRanking,
    FilaResumen,
    IndicadorComparado,
    ListaActividades,
    ListaMunicipios,
    Municipio,
    RespuestaComparacion,
    RespuestaEvaluacion,
    RespuestaMapa,
    RespuestaRanking,
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
        # Evaluar los 8.132 municipios tarda un rato: lo hago UNA vez por actividad y guardo el resultado.
        # Las reglas no cambian mientras la API está arrancada, así que la caché no se queda vieja.
        self._cache_actividades: dict[str, list[FilaMapa]] = {}
        self._candado_cache = threading.Lock()

    def salud(self) -> Salud:
        info = self.repo.info()
        return Salud(
            estado="ok",
            datos_cargados=True,
            origen=info["origen"],
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

    # ------------------------------------------------------------- ranking y mapa

    def _todos(self, actividad: str) -> list[FilaMapa]:
        """Todos los municipios evaluados para una actividad (se calcula la primera vez)."""
        if actividad not in self._cache_actividades:
            with self._candado_cache:
                if actividad not in self._cache_actividades:
                    filas = []
                    for cod, m in self.repo.municipios.iterrows():
                        ev = self.motor.evaluar(cod, actividad, self.repo.observaciones(cod))
                        datos = Municipio(**self.repo.municipio(cod))
                        filas.append(FilaMapa(
                            cod_ine=cod,
                            nombre=datos.nombre,
                            provincia=datos.provincia,
                            ccaa=datos.ccaa,
                            lat=datos.lat,
                            lon=datos.lon,
                            riesgo_nota=ev.riesgo.nota,
                            riesgo_estado=ev.riesgo.estado,
                            riesgo_confianza=ev.riesgo.confianza,
                            atractivo_nota=ev.atractivo.nota,
                            atractivo_estado=ev.atractivo.estado,
                            atractivo_confianza=ev.atractivo.confianza,
                            cumple_minimos=ev.cumple_minimos.value,
                        ))
                    self._cache_actividades[actividad] = filas
        return self._cache_actividades[actividad]

    def _filtrar(self, actividad: str, provincia, ccaa, cumple_minimos) -> list[FilaMapa]:
        filas = self._todos(actividad)
        if provincia:
            filas = [f for f in filas if sin_acentos(f.provincia or "") == sin_acentos(provincia)]
        if ccaa:
            filas = [f for f in filas if sin_acentos(f.ccaa or "") == sin_acentos(ccaa)]
        if cumple_minimos:
            filas = [f for f in filas if f.cumple_minimos == cumple_minimos]
        return filas

    def _estado_reglas(self, actividad: str) -> tuple[str, bool]:
        resumen = self.reglas.resumen(actividad)
        return self.reglas.version, resumen["estado_reglas"] != "aprobadas"

    def ranking(
        self, actividad, ordenar_por, orden, provincia, ccaa, cumple_minimos, limite, desplazamiento
    ) -> RespuestaRanking:
        """Ordena por una sola dimensión. Atractivo: más alto es mejor. Riesgo: más bajo es mejor."""
        filtradas = self._filtrar(actividad, provincia, ccaa, cumple_minimos)
        campo = f"{ordenar_por}_nota"
        con_nota = [f for f in filtradas if getattr(f, campo) is not None]
        signo = -1 if ordenar_por == "atractivo" else 1  # atractivo: de mayor a menor; riesgo: de menor a mayor
        # Empates: desempato por código INE para que el orden sea siempre el mismo.
        con_nota.sort(key=lambda f: (signo * getattr(f, campo), f.cod_ine))
        if orden == "peor_primero":
            con_nota.reverse()
        pagina = con_nota[desplazamiento : desplazamiento + limite]
        version, provisionales = self._estado_reglas(actividad)
        return RespuestaRanking(
            actividad=actividad,
            ordenado_por=ordenar_por,
            orden=orden,
            total=len(con_nota),
            sin_nota=len(filtradas) - len(con_nota),
            limite=limite,
            desplazamiento=desplazamiento,
            filas=[
                FilaRanking(**f.model_dump(), posicion=desplazamiento + i + 1)
                for i, f in enumerate(pagina)
            ],
            version_reglas=version,
            reglas_provisionales=provisionales,
        )

    def mapa(self, actividad, provincia, ccaa, cumple_minimos) -> RespuestaMapa:
        filtradas = self._filtrar(actividad, provincia, ccaa, cumple_minimos)
        version, provisionales = self._estado_reglas(actividad)
        return RespuestaMapa(
            actividad=actividad,
            total=len(filtradas),
            filas=filtradas,
            version_reglas=version,
            reglas_provisionales=provisionales,
        )
