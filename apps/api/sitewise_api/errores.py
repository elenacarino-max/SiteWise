"""Errores con un formato fijo, para que el frontend y el agente los distingan.

Todos los errores de la API devuelven:  {"error": "<codigo>", "mensaje": "<texto>"}
El `codigo` es estable (se puede comparar en código); el `mensaje` es para personas.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ErrorApi(Exception):
    def __init__(self, estado_http: int, codigo: str, mensaje: str):
        self.estado_http = estado_http
        self.codigo = codigo
        self.mensaje = mensaje


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorApi)
    async def _manejar(_: Request, error: ErrorApi) -> JSONResponse:
        return JSONResponse(
            status_code=error.estado_http,
            content={"error": error.codigo, "mensaje": error.mensaje},
        )
