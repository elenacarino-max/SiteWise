"""Une el repositorio de datos con las respuestas de la API.

No guarda ningún dato de una petición entre una llamada y otra: así varias peticiones a la vez
no se pisan (el problema que tenía el estado compartido del analista del agente).
"""

from __future__ import annotations

from sitewise.db.repositorio import RepositorioCSV
from sitewise.scoring.calidad import es_aproximado, motivo_no_utilizable

from .schemas import FichaMunicipio, ListaMunicipios, Municipio, Salud, ValorIndicador


class Servicio:
    def __init__(self, repositorio: RepositorioCSV):
        self.repo = repositorio

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
