"""Leo los CSV del dataset y se los sirvo al resto del backend.

Uso los ficheros de `data/processed/sitewise_v03/` descritos en el diccionario:
  - municipios.csv   una fila por municipio (maestro territorial)
  - indicadores.csv  una fila por indicador (definición, unidad, fuente...)
  - valores_app.csv  una fila por municipio e indicador (formato largo, con estado). Es el que
                     prepara el notebook 09 para la app. Si no existe, uso valores.csv.

Este "repositorio" es la única pieza que sabe de dónde salen los datos. Más adelante
se puede cambiar por una versión que lea de PostgreSQL sin tocar el motor ni la API.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

from sitewise.scoring.modelos import Observacion

FICHEROS = ("municipios.csv", "indicadores.csv")  # los de valores se eligen con `fichero_valores`

# De valores_app.csv solo leo las columnas que uso (el fichero pesa unos 120 MB).
COLUMNAS_VALORES = frozenset({
    "cod_ine", "id_indicador", "valor", "estado", "nivel_origen", "fecha_dato", "fuente_id",
    "naturaleza", "metodo", "estado_app", "estimado_app", "k_vecinos",
    "distancia_media_km", "distancia_maxima_km",
})


def fichero_valores(directorio: str | Path) -> Path:
    """valores_app.csv si existe (incluye las estimaciones de agua del notebook 09); si no, valores.csv."""
    directorio = Path(directorio)
    app = directorio / "valores_app.csv"
    return app if app.is_file() else directorio / "valores.csv"


class DatosNoDisponibles(RuntimeError):
    """Lo lanzo si falta el directorio o alguno de los CSV (los datos no están en Git)."""


def _sin_acentos(texto: str) -> str:
    """'Álava' -> 'alava'. Sirve para buscar sin preocuparse de mayúsculas ni tildes."""
    descompuesto = unicodedata.normalize("NFD", str(texto))
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn").lower().strip()


sin_acentos = _sin_acentos  # nombre público: lo usa también la API para filtrar


def _limpiar(valor: Any) -> Any:
    """Convierto los huecos de pandas (NaN) en None y los números de numpy en normales.

    Lo necesito para que la API pueda devolver JSON: NaN no es JSON válido.
    """
    if pd.isna(valor):
        return None
    return valor.item() if hasattr(valor, "item") else valor


def _entero(valor: Any) -> int | None:
    valor = _limpiar(valor)
    return None if valor is None else int(valor)


class RepositorioCSV:
    origen = "csv"

    def __init__(self, directorio: str | Path):
        self.directorio = Path(directorio)
        self.fichero_valores = fichero_valores(self.directorio)
        faltan = [f for f in FICHEROS if not (self.directorio / f).is_file()]
        if not self.fichero_valores.is_file():
            faltan.append("valores_app.csv o valores.csv")
        if faltan:
            raise DatosNoDisponibles(
                f"No encuentro {', '.join(faltan)} en '{self.directorio}'. "
                "Los datos no están en Git: pídele la entrega a Elena y ajusta SITEWISE_DATA_DIR."
            )

        # cod_ine SIEMPRE como texto de 5 dígitos: si pandas lo lee como número, se pierde
        # el cero inicial de "01001" (Álava) y se rompe el cruce entre ficheros.
        municipios = pd.read_csv(
            self.directorio / "municipios.csv", dtype={"cod_ine": str, "cod_provincia": str}
        )
        indicadores = pd.read_csv(self.directorio / "indicadores.csv", dtype=str)
        valores = pd.read_csv(
            self.fichero_valores,
            usecols=lambda columna: columna in COLUMNAS_VALORES,
            dtype={
                "cod_ine": str, "id_indicador": str, "estado": str, "nivel_origen": str,
                "estado_app": str, "estimado_app": str,
            },
        )
        self._preparar(municipios, indicadores, valores)

    def _preparar(self, municipios: pd.DataFrame, indicadores: pd.DataFrame, valores: pd.DataFrame) -> None:
        """Deja las tres tablas listas para consultar. Lo comparte el repositorio de PostgreSQL.

        Así los datos se tratan igual vengan de un CSV o de la base de datos.
        """
        municipios["cod_ine"] = municipios["cod_ine"].str.zfill(5)
        self.municipios = municipios.set_index("cod_ine", drop=False)
        # Columna auxiliar para buscar sin tildes (no se devuelve a la API).
        self._busqueda = self.municipios["nombre"].map(_sin_acentos)

        self.indicadores = indicadores.set_index("id_indicador", drop=False)

        valores["cod_ine"] = valores["cod_ine"].str.zfill(5)
        valores["valor"] = pd.to_numeric(valores["valor"], errors="coerce")  # texto raro -> NaN
        if "estimado_app" in valores.columns:
            # Las 722 estimaciones de agua (media de los 5 vecinos con dato) conservan su estado de origen
            # ("sin_masa_catalogada"), que es un estado sin valor. Pero ahora SÍ tienen valor y son
            # aproximadas: para calcular uso el estado de la app. El resto de filas NO cambian de estado:
            # por ejemplo "sin_poligonos_en_catalogo" sigue sin ser utilizable aunque la app lo llame aproximado.
            estimado = valores["estimado_app"].astype(str).str.lower().eq("true")
            valores["estimado_app"] = estimado
            if "estado_app" in valores.columns:
                valores.loc[estimado, "estado"] = valores.loc[estimado, "estado_app"]
        self.valores = valores
        # Agrupo una sola vez por municipio para que pedir un municipio sea inmediato.
        self._por_municipio = {cod: grupo for cod, grupo in valores.groupby("cod_ine")}

    # ---------------------------------------------------------------- información

    def info(self) -> dict[str, Any]:
        return {
            "origen": self.origen,
            "valores_fichero": self.fichero_valores.name if hasattr(self, "fichero_valores") else None,
            "municipios": len(self.municipios),
            "indicadores": len(self.indicadores),
            "observaciones": len(self.valores),
        }

    # ------------------------------------------------------------------ municipios

    def buscar_municipios(
        self,
        q: str | None = None,
        provincia: str | None = None,
        ccaa: str | None = None,
        limite: int = 50,
        desplazamiento: int = 0,
    ) -> tuple[int, list[dict[str, Any]]]:
        """Devuelvo (total que cumple el filtro, la página pedida)."""
        filtro = pd.Series(True, index=self.municipios.index)
        if q:
            filtro &= self._busqueda.str.contains(_sin_acentos(q), regex=False)
        if provincia:
            filtro &= self.municipios["provincia"].map(_sin_acentos) == _sin_acentos(provincia)
        if ccaa:
            filtro &= self.municipios["ccaa"].map(_sin_acentos) == _sin_acentos(ccaa)

        encontrados = self.municipios[filtro].sort_values("nombre")
        pagina = encontrados.iloc[desplazamiento : desplazamiento + limite]
        return len(encontrados), [self._fila_municipio(f) for _, f in pagina.iterrows()]

    def municipio(self, cod_ine: str) -> dict[str, Any] | None:
        """Datos del maestro de un municipio, o None si no existe."""
        if cod_ine not in self.municipios.index:
            return None
        return self._fila_municipio(self.municipios.loc[cod_ine])

    @staticmethod
    def _fila_municipio(fila: pd.Series) -> dict[str, Any]:
        return {k: _limpiar(v) for k, v in fila.items()}

    # ------------------------------------------------------------------ indicadores

    def observaciones(self, cod_ine: str) -> dict[str, Observacion]:
        """Lo que necesita el motor: {id_indicador: Observacion} de ese municipio."""
        grupo = self._por_municipio.get(cod_ine)
        if grupo is None:
            return {}
        return {
            f.id_indicador: Observacion(
                _limpiar(f.valor),
                _limpiar(f.estado),
                _limpiar(f.nivel_origen) if "nivel_origen" in grupo.columns else None,
            )
            for f in grupo.itertuples()
        }

    def detalle_indicadores(self, cod_ine: str) -> list[dict[str, Any]]:
        """Cada indicador del municipio con su valor Y su trazabilidad (unidad, fuente, fecha...).

        Muestro siempre estado, fecha y fuente: el diccionario pide que sean visibles.
        """
        grupo = self._por_municipio.get(cod_ine)
        if grupo is None:
            return []
        salida = []
        for f in grupo.itertuples():
            estimado = bool(getattr(f, "estimado_app", False))
            meta = self.indicadores.loc[f.id_indicador] if f.id_indicador in self.indicadores.index else None
            salida.append({
                "id_indicador": f.id_indicador,
                "nombre": _limpiar(meta["nombre"]) if meta is not None and "nombre" in meta else None,
                "bloque": _limpiar(meta["bloque"]) if meta is not None and "bloque" in meta else None,
                "tipo": _limpiar(meta["tipo"]) if meta is not None and "tipo" in meta else None,
                "unidad": _limpiar(meta["unidad"]) if meta is not None and "unidad" in meta else None,
                "limitaciones": (
                    _limpiar(meta["limitaciones"]) if meta is not None and "limitaciones" in meta else None
                ),
                "valor": _limpiar(f.valor),
                "estado": _limpiar(f.estado),
                "nivel_origen": _limpiar(getattr(f, "nivel_origen", None)),
                "fecha_dato": _limpiar(getattr(f, "fecha_dato", None)),
                "fuente_id": _limpiar(getattr(f, "fuente_id", None)),
                "naturaleza": _limpiar(getattr(f, "naturaleza", None)),
                # Solo en los valores estimados (vecinos): cómo se estimó y con qué distancias.
                "estimado": estimado,
                "metodo": _limpiar(getattr(f, "metodo", None)) if estimado else None,
                "vecinos": _entero(getattr(f, "k_vecinos", None)) if estimado else None,
                "distancia_media_km": _limpiar(getattr(f, "distancia_media_km", None)) if estimado else None,
                "distancia_maxima_km": _limpiar(getattr(f, "distancia_maxima_km", None)) if estimado else None,
            })
        return salida
