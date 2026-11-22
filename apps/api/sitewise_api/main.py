"""Punto de entrada de la API.

Arranque (desde la raíz del repo):
    python -m uvicorn --app-dir apps/api sitewise_api.main:app --reload
Documentación interactiva: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import threading
from typing import Annotated

from fastapi import Depends, FastAPI, Path, Query, Request

from sitewise.db.repositorio import DatosNoDisponibles, RepositorioCSV
from sitewise.scoring.reglas import ErrorReglas, cargar_reglas

from .config import Ajustes
from .errores import ErrorApi, registrar_manejadores
from .schemas import (
    FichaMunicipio,
    ListaActividades,
    ListaMunicipios,
    Municipio,
    RespuestaEvaluacion,
    Salud,
)
from .servicio import Servicio

# Tipos reutilizables: "Annotated" pega a cada parámetro su validación y su documentación.
CodIne = Annotated[str, Path(pattern=r"^\d{5}$", description="Código INE de 5 dígitos (con ceros iniciales)")]
Actividad = Annotated[str, Path(min_length=1, max_length=80, description="Nombre de la actividad (ver /actividades)")]


def obtener_servicio(request: Request) -> Servicio:
    """Carga los datos la primera vez que se necesitan (el CSV grande tarda unos segundos)."""
    estado = request.app.state
    if estado.servicio is None:
        with estado.candado:
            if estado.servicio is None:
                try:
                    reglas = cargar_reglas(estado.ajustes.ruta_reglas)
                    estado.servicio = Servicio(RepositorioCSV(estado.ajustes.directorio_datos), reglas)
                except DatosNoDisponibles as exc:
                    raise ErrorApi(503, "datos_no_disponibles", str(exc)) from exc
                except ErrorReglas as exc:
                    # El CSV de reglas tiene algo mal escrito: el mensaje dice en qué línea.
                    raise ErrorApi(500, "reglas_invalidas", str(exc)) from exc
    return estado.servicio


ServicioDep = Annotated[Servicio, Depends(obtener_servicio)]


def crear_app(ajustes: Ajustes | None = None) -> FastAPI:
    app = FastAPI(
        title="SiteWise API",
        version="0.1.0",
        description="Municipios, fichas y valoraciones para comparar ubicaciones empresariales.",
    )
    app.state.ajustes = ajustes or Ajustes.desde_entorno()
    app.state.servicio = None
    app.state.candado = threading.Lock()
    registrar_manejadores(app)

    @app.get("/health", response_model=Salud, tags=["estado"])
    def health(request: Request) -> Salud:
        """Dice si la API está viva y si tiene los datos cargados (nunca devuelve error)."""
        try:
            return obtener_servicio(request).salud()
        except ErrorApi as exc:
            return Salud(estado="ok", datos_cargados=False, detalle=exc.mensaje)

    @app.get("/municipios", response_model=ListaMunicipios, tags=["municipios"])
    def listar_municipios(
        servicio: ServicioDep,
        q: Annotated[str | None, Query(description="Texto del nombre (sin tildes ni mayúsculas)")] = None,
        provincia: str | None = None,
        ccaa: str | None = None,
        limite: Annotated[int, Query(ge=1, le=200)] = 50,
        desplazamiento: Annotated[int, Query(ge=0)] = 0,
    ) -> ListaMunicipios:
        return servicio.buscar(q, provincia, ccaa, limite, desplazamiento)

    @app.get("/municipios/{cod_ine}", response_model=Municipio, tags=["municipios"])
    def obtener_municipio(cod_ine: CodIne, servicio: ServicioDep) -> Municipio:
        municipio = servicio.municipio(cod_ine)
        if municipio is None:
            raise ErrorApi(404, "municipio_no_encontrado", f"No existe el municipio '{cod_ine}'.")
        return municipio

    @app.get("/municipios/{cod_ine}/ficha", response_model=FichaMunicipio, tags=["municipios"])
    def ficha_municipio(cod_ine: CodIne, servicio: ServicioDep) -> FichaMunicipio:
        """Todos los indicadores del municipio con valor, estado, fecha, fuente y limitaciones."""
        ficha = servicio.ficha(cod_ine)
        if ficha is None:
            raise ErrorApi(404, "municipio_no_encontrado", f"No existe el municipio '{cod_ine}'.")
        return ficha

    @app.get("/actividades", response_model=ListaActividades, tags=["actividades"])
    def listar_actividades(servicio: ServicioDep) -> ListaActividades:
        """Actividades con reglas cargadas y si esas reglas están aprobadas o son provisionales."""
        return servicio.actividades()

    @app.get(
        "/municipios/{cod_ine}/evaluacion/{actividad}",
        response_model=RespuestaEvaluacion,
        tags=["actividades"],
    )
    def evaluar_municipio(cod_ine: CodIne, actividad: Actividad, servicio: ServicioDep) -> RespuestaEvaluacion:
        """Riesgo y atractivo (por separado) y requisitos mínimos de un municipio para una actividad."""
        if servicio.municipio(cod_ine) is None:
            raise ErrorApi(404, "municipio_no_encontrado", f"No existe el municipio '{cod_ine}'.")
        if not servicio.existe_actividad(actividad):
            raise ErrorApi(404, "actividad_no_encontrada", f"No hay reglas para la actividad '{actividad}'.")
        return servicio.evaluar(cod_ine, actividad)

    return app


app = crear_app()
