"""Leo los CSV del dataset y se los sirvo al resto del backend.

Uso los ficheros de `data/processed/sitewise_v03/` descritos en el diccionario:
  - municipios.csv   una fila por municipio (maestro territorial)
  - indicadores.csv  una fila por indicador (definición, unidad, fuente...)
  - valores.csv      una fila por municipio e indicador (formato largo, con estado)

Este "repositorio" es la única pieza que sabe de dónde salen los datos. Más adelante
se puede cambiar por una versión que lea de PostgreSQL sin tocar el motor ni la API.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

from sitewise.scoring.modelos import Observacion

FICHEROS = ("municipios.csv", "indicadores.csv", "valores.csv")


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


class RepositorioCSV:
    def __init__(self, directorio: str | Path):
        self.directorio = Path(directorio)
        faltan = [f for f in FICHEROS if not (self.directorio / f).is_file()]
        if faltan:
            raise DatosNoDisponibles(
                f"No encuentro {', '.join(faltan)} en '{self.directorio}'. "
                "Los datos no están en Git: pídele la entrega a Elena y ajusta SITEWISE_DATA_DIR."
            )

        # cod_ine SIEMPRE como texto de 5 dígitos: si pandas lo lee como número, se pierde
        # el cero inicial de "01001" (Álava) y se rompe el cruce entre ficheros.
        self.municipios = pd.read_csv(
            self.directorio / "municipios.csv", dtype={"cod_ine": str, "cod_provincia": str}
        )
        self.municipios["cod_ine"] = self.municipios["cod_ine"].str.zfill(5)
        self.municipios = self.municipios.set_index("cod_ine", drop=False)
        # Columna auxiliar para buscar sin tildes (no se devuelve a la API).
        self._busqueda = (
            self.municipios["nombre"].map(_sin_acentos)
        )

        self.indicadores = pd.read_csv(self.directorio / "indicadores.csv", dtype=str).set_index(
            "id_indicador", drop=False
        )

        valores = pd.read_csv(
            self.directorio / "valores.csv",
            dtype={"cod_ine": str, "id_indicador": str, "estado": str, "nivel_origen": str},
        )
        valores["cod_ine"] = valores["cod_ine"].str.zfill(5)
        valores["valor"] = pd.to_numeric(valores["valor"], errors="coerce")  # texto raro -> NaN
        self.valores = valores
        # Agrupo una sola vez por municipio para que pedir un municipio sea inmediato.
        self._por_municipio = {cod: grupo for cod, grupo in valores.groupby("cod_ine")}

    # ---------------------------------------------------------------- información

    def info(self) -> dict[str, Any]:
        return {
            "directorio": str(self.directorio),
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
            })
        return salida
