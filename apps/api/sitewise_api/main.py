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

from .config import Ajustes
from .errores import ErrorApi, registrar_manejadores
from .schemas import FichaMunicipio, ListaMunicipios, Municipio, Salud
from .servicio import Servicio

# Tipos reutilizables: "Annotated" pega a cada parámetro su validación y su documentación.
CodIne = Annotated[str, Path(pattern=r"^\d{5}$", description="Código INE de 5 dígitos (con ceros iniciales)")]


def obtener_servicio(request: Request) -> Servicio:
    """Carga los datos la primera vez que se necesitan (el CSV grande tarda unos segundos)."""
    estado = request.app.state
    if estado.servicio is None:
        with estado.candado:
            if estado.servicio is None:
                try:
                    estado.servicio = Servicio(RepositorioCSV(estado.ajustes.directorio_datos))
                except DatosNoDisponibles as exc:
                    raise ErrorApi(503, "datos_no_disponibles", str(exc)) from exc
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

    return app


app = crear_app()
