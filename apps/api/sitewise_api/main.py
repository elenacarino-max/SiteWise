"""Punto de entrada de la API.

Arranque (desde la raíz del repo):
    python -m uvicorn --app-dir apps/api sitewise_api.main:app --reload
Documentación interactiva: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import threading
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Path, Query, Request
from fastapi.middleware.gzip import GZipMiddleware

from sitewise.db.repositorio import DatosNoDisponibles, RepositorioCSV
from sitewise.scoring.modelos import EstadoMinimo
from sitewise.scoring.reglas import ErrorReglas, cargar_reglas

from .config import Ajustes
from .errores import ErrorApi, registrar_manejadores
from .schemas import (
    FichaMunicipio,
    ListaActividades,
    ListaMunicipios,
    ListaPerfiles,
    Municipio,
    RespuestaCercanos,
    RespuestaComparacion,
    RespuestaEvaluacion,
    RespuestaMapa,
    RespuestaRanking,
    RespuestaSimilares,
    Salud,
)
from .servicio import Servicio

# Tipos reutilizables: "Annotated" pega a cada parámetro su validación y su documentación.
CodIne = Annotated[str, Path(pattern=r"^\d{5}$", description="Código INE de 5 dígitos (con ceros iniciales)")]
Actividad = Annotated[str, Path(min_length=1, max_length=80, description="Nombre de la actividad (ver /actividades)")]


def crear_repositorio(ajustes: Ajustes):
    """Elijo de dónde leo los datos: PostgreSQL si hay URL de base de datos, y si no, los CSV."""
    if ajustes.url_base_datos:
        from sitewise.db.postgres import (
            RepositorioPostgres,  # import aquí: psycopg solo se pide si se usa
        )

        return RepositorioPostgres(ajustes.url_base_datos, ajustes.esquema_base_datos)
    return RepositorioCSV(ajustes.directorio_datos, ajustes.directorio_perfiles)


def obtener_servicio(request: Request) -> Servicio:
    """Carga los datos la primera vez que se necesitan (el CSV grande tarda unos segundos)."""
    estado = request.app.state
    if estado.servicio is None:
        with estado.candado:
            if estado.servicio is None:
                try:
                    reglas = cargar_reglas(estado.ajustes.ruta_reglas)
                    estado.servicio = Servicio(crear_repositorio(estado.ajustes), reglas)
                except DatosNoDisponibles as exc:
                    raise ErrorApi(503, "datos_no_disponibles", str(exc)) from exc
                except ErrorReglas as exc:
                    # El CSV de reglas tiene algo mal escrito: el mensaje dice en qué línea.
                    raise ErrorApi(500, "reglas_invalidas", str(exc)) from exc
    return estado.servicio


ServicioDep = Annotated[Servicio, Depends(obtener_servicio)]

MIN_COMPARAR, MAX_COMPARAR = 2, 3


def leer_codigos(municipios: list[str]) -> list[str]:
    """Acepta `?municipios=28079&municipios=44001` y también `?municipios=28079,44001`."""
    codigos = [c.strip() for texto in municipios for c in texto.split(",") if c.strip()]
    if not MIN_COMPARAR <= len(codigos) <= MAX_COMPARAR:
        raise ErrorApi(400, "comparacion_invalida", f"Hay que comparar entre {MIN_COMPARAR} y {MAX_COMPARAR} municipios.")
    malos = [c for c in codigos if not (len(c) == 5 and c.isdigit())]
    if malos:
        raise ErrorApi(400, "comparacion_invalida", f"Códigos INE no válidos (5 dígitos): {', '.join(malos)}.")
    if len(set(codigos)) != len(codigos):
        raise ErrorApi(400, "comparacion_invalida", "No se puede repetir un municipio en la comparación.")
    return codigos


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
    # El mapa completo son unos 2 MB de JSON: comprimido baja mucho. Solo comprime respuestas grandes.
    app.add_middleware(GZipMiddleware, minimum_size=1000)

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

    @app.get("/perfiles", response_model=ListaPerfiles, tags=["perfiles"])
    def listar_perfiles(servicio: ServicioDep) -> ListaPerfiles:
        """Los perfiles de municipios (clustering) con su descripción y las medianas de cada variable."""
        return servicio.perfiles()

    @app.get("/municipios/{cod_ine}/similares", response_model=RespuestaSimilares, tags=["perfiles"])
    def municipios_similares(
        cod_ine: CodIne,
        servicio: ServicioDep,
        provincia: str | None = None,
        ccaa: str | None = None,
        limite: Annotated[int, Query(ge=1, le=200)] = 10,
        desplazamiento: Annotated[int, Query(ge=0)] = 0,
    ) -> RespuestaSimilares:
        """Municipios con el mismo perfil, del más cercano al más lejano. No son notas ni una recomendación."""
        if servicio.municipio(cod_ine) is None:
            raise ErrorApi(404, "municipio_no_encontrado", f"No existe el municipio '{cod_ine}'.")
        respuesta = servicio.similares(cod_ine, provincia, ccaa, limite, desplazamiento)
        if respuesta is None:
            raise ErrorApi(
                404, "perfil_no_disponible",
                f"No hay perfil para el municipio '{cod_ine}' (los perfiles no están cargados o no lo incluyen).",
            )
        return respuesta

    @app.get("/municipios/{cod_ine}/cercanos", response_model=RespuestaCercanos, tags=["perfiles"])
    def municipios_cercanos(cod_ine: CodIne, servicio: ServicioDep) -> RespuestaCercanos:
        """Los 5 municipios más próximos en línea recta (útil para riesgos hídricos y naturales). No depende del perfil."""
        if servicio.municipio(cod_ine) is None:
            raise ErrorApi(404, "municipio_no_encontrado", f"No existe el municipio '{cod_ine}'.")
        respuesta = servicio.cercanos(cod_ine)
        if respuesta is None:
            raise ErrorApi(
                404, "cercanos_no_disponibles",
                f"No hay municipios cercanos para '{cod_ine}' (los datos de cercanos no están cargados o no lo incluyen).",
            )
        return respuesta

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

    @app.get("/comparar", response_model=RespuestaComparacion, tags=["actividades"])
    def comparar_municipios(
        servicio: ServicioDep,
        municipios: Annotated[
            list[str], Query(description="2 o 3 códigos INE, repetidos o separados por comas")
        ],
        actividad: Annotated[str, Query(min_length=1, max_length=80, description="Ver /actividades")],
    ) -> RespuestaComparacion:
        """Compara 2 o 3 municipios para una actividad: resumen, indicadores y evaluación de cada uno."""
        codigos = leer_codigos(municipios)
        inexistentes = [c for c in codigos if servicio.municipio(c) is None]
        if inexistentes:
            raise ErrorApi(404, "municipio_no_encontrado", f"No existe(n): {', '.join(inexistentes)}.")
        if not servicio.existe_actividad(actividad):
            raise ErrorApi(404, "actividad_no_encontrada", f"No hay reglas para la actividad '{actividad}'.")
        return servicio.comparar(codigos, actividad)

    def _exigir_actividad(servicio: Servicio, actividad: str) -> None:
        if not servicio.existe_actividad(actividad):
            raise ErrorApi(404, "actividad_no_encontrada", f"No hay reglas para la actividad '{actividad}'.")

    @app.get("/actividades/{actividad}/ranking", response_model=RespuestaRanking, tags=["actividades"])
    def ranking_actividad(
        actividad: Actividad,
        servicio: ServicioDep,
        ordenar_por: Annotated[Literal["atractivo", "riesgo"], Query(description="Dimensión por la que ordenar")] = "atractivo",
        orden: Annotated[
            Literal["mejor_primero", "peor_primero"],
            Query(description="Atractivo: mejor es más alto. Riesgo: mejor es más bajo"),
        ] = "mejor_primero",
        provincia: str | None = None,
        ccaa: str | None = None,
        cumple_minimos: Annotated[EstadoMinimo | None, Query(description="Filtra por estado de los mínimos")] = None,
        limite: Annotated[int, Query(ge=1, le=200)] = 50,
        desplazamiento: Annotated[int, Query(ge=0)] = 0,
    ) -> RespuestaRanking:
        """Municipios ordenados por UNA dimensión (nunca una nota única). La primera llamada tarda unos segundos."""
        _exigir_actividad(servicio, actividad)
        return servicio.ranking(
            actividad, ordenar_por, orden, provincia, ccaa,
            cumple_minimos.value if cumple_minimos else None, limite, desplazamiento,
        )

    @app.get("/actividades/{actividad}/mapa", response_model=RespuestaMapa, tags=["actividades"])
    def mapa_actividad(
        actividad: Actividad,
        servicio: ServicioDep,
        provincia: str | None = None,
        ccaa: str | None = None,
        cumple_minimos: Annotated[EstadoMinimo | None, Query(description="Filtra por estado de los mínimos")] = None,
    ) -> RespuestaMapa:
        """Todos los municipios con coordenadas y notas, sin paginar, para pintar el mapa."""
        _exigir_actividad(servicio, actividad)
        return servicio.mapa(
            actividad, provincia, ccaa, cumple_minimos.value if cumple_minimos else None
        )

    return app


app = crear_app()
