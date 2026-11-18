"""
Módulo loader.py: Carga y transformación del CSV municipal y documentación
para el sistema RAG de SiteWise.
"""

import os
from typing import Any

import pandas as pd


class SiteWiseLoader:
    """Cargador de datos municipales y documentación técnica para SiteWise."""

    def __init__(self, data_path: str = "data/processed/sitewise_v03"):
        self.data_path = data_path

    @staticmethod
    def _clasificar_nivel(
        val: Any,
        bajo: float,
        alto: float,
        etiquetas: tuple[str, str, str] = ("bajo", "moderado", "alto"),
    ) -> str:
        if pd.isna(val):
            return "dato no disponible"
        if val < bajo:
            return etiquetas[0]
        if val < alto:
            return etiquetas[1]
        return etiquetas[2]

    @staticmethod
    def _fmt(val: Any, sufijo: str = "", decimales: int = 1) -> str:
        if pd.isna(val):
            return "N/D"
        if isinstance(val, (int, float)):
            if decimales > 0:
                return f"{val:.{decimales}f}{sufijo}"
            return f"{round(val)}{sufijo}"
        return f"{val}{sufijo}"

    def _construir_ficha_municipio(self, row: pd.Series) -> dict[str, Any]:
        """Transforma una fila del dataset en una ficha textual rica y sus metadatos."""
        cod_ine = str(row.get("cod_ine", "N/D"))
        nombre = str(row.get("nombre", "Desconocido"))
        provincia = str(row.get("provincia", "Desconocida"))
        ccaa = str(row.get("ccaa", "Desconocida"))

        cluster_val = row.get("cluster_perfil", row.get("cluster", None))
        cluster_str = str(cluster_val) if pd.notna(cluster_val) else "Pendiente de asignar"
        linea_cluster = (
            f" | Perfil de clúster: {cluster_str}" if pd.notna(cluster_val) else ""
        )

        pob = (
            row.get("poblacion_2025")
            if pd.notna(row.get("poblacion_2025"))
            else row.get("poblacion_2024")
        )
        var_pob = row.get("variacion_poblacion_pct")
        densidad = row.get("densidad_hab_km2")
        superficie = row.get("superficie_km2")

        tendencia_pob = (
            "crecimiento demográfico"
            if pd.notna(var_pob) and var_pob > 0
            else "pérdida o estancamiento de población"
        )
        perfil_urbano = self._clasificar_nivel(
            densidad,
            50,
            300,
            ("entorno rural de baja densidad", "entorno semiurbano", "entorno urbano denso"),
        )

        paro_tot = row.get("paro_total")
        var_paro = row.get("paro_variacion_interanual_pct")
        contratos = row.get("contratos_total")

        sectores_paro = {
            "agricultura": row.get("paro_agricultura") if pd.notna(row.get("paro_agricultura")) else 0,
            "construcción": row.get("paro_construccion") if pd.notna(row.get("paro_construccion")) else 0,
            "industria": row.get("paro_industria") if pd.notna(row.get("paro_industria")) else 0,
            "servicios": row.get("paro_servicios") if pd.notna(row.get("paro_servicios")) else 0,
        }
        sector_principal = (
            max(sectores_paro, key=sectores_paro.get)
            if sum(sectores_paro.values()) > 0
            else "no determinado"
        )

        suelo_ha = row.get("suelo_industrial_cartografiado_ha")
        suelo_pct = row.get("suelo_industrial_cartografiado_pct")
        autovia = row.get("dist_recta_eje_autovia_km")
        ttm = row.get("dist_recta_ttm_km")
        intermodal = row.get("dist_recta_ttm_intermodal_km")

        acceso_viario = self._clasificar_nivel(
            autovia,
            5,
            20,
            ("acceso inmediato a autovía", "buena conexión viaria", "alejado de ejes de autovía"),
        )
        
        if pd.notna(suelo_ha) and suelo_ha > 0:
            tiene_suelo = f"{self._fmt(suelo_ha, ' ha')} ({self._fmt(suelo_pct, '%')} del término municipal)"
        else:
            tiene_suelo = "sin polígonos industriales detectados en el catálogo cartografiado"

        ftth = row.get("cobertura_ftth_pct")
        c_1gbps = row.get("cobertura_1gbps_pct")
        c_5g = row.get("cobertura_5g_pct")
        tiepi = row.get("tiepi_horas_prov_2021")
        niepi = row.get("niepi_prov_2021")

        estres = row.get("estres_hidrico_pct")
        agotamiento = row.get("agotamiento_hidrico_pct")
        sub_cuant = row.get("agua_subterranea_mal_estado_cuantitativo_pct")
        sub_quim = row.get("agua_subterranea_mal_estado_quimico_pct")

        nivel_riesgo_hidrico = self._clasificar_nivel(
            estres,
            20,
            40,
            ("bajo estrés hídrico", "estrés hídrico moderado", "estrés hídrico severo"),
        )

        incendios_n = row.get("siniestros_forestales_2006_2015_n")
        ha_quemadas = row.get("superficie_forestal_afectada_2006_2015_ha")
        eventos_cnih = row.get("eventos_cnih_2000_2023_n")
        ultimo_cnih = row.get("ultimo_anio_cnih_2000_2023")

        ghi = row.get("irradiacion_ghi_kwh_m2_anio")
        viento = row.get("viento_100m_media_m_s")

        text_content = (
            f"PERFIL MUNICIPAL DE {nombre.upper()} (INE: {cod_ine}) | Provincia: {provincia} | CCAA: {ccaa}{linea_cluster}.\n"
            f"1. DEMOGRAFÍA Y TERRITORIO: Municipio con {self._fmt(pob, ' habitantes', 0)} en una superficie de {self._fmt(superficie, ' km²')}, "
            f"clasificado como {perfil_urbano} ({self._fmt(densidad, ' hab/km²')}). Presenta {tendencia_pob} ({self._fmt(var_pob, '%')}).\n"
            f"2. EMPLEO Y MERCADO LABORAL: Registra {self._fmt(paro_tot, ' personas desempleadas', 0)} (variación interanual del {self._fmt(var_paro, '%')}) "
            f"y {self._fmt(contratos, ' contratos', 0)}. El mayor volumen de disponibilidad laboral se concentra en el sector {sector_principal} "
            f"(Industria: {self._fmt(sectores_paro['industria'], '', 0)}, Servicios: {self._fmt(sectores_paro['servicios'], '', 0)}, "
            f"Construcción: {self._fmt(sectores_paro['construcción'], '', 0)}, Agricultura: {self._fmt(sectores_paro['agricultura'], '', 0)}).\n"
            f"3. SUELO INDUSTRIAL Y LOGÍSTICA: Dispone de {tiene_suelo}. Presenta {acceso_viario} ({self._fmt(autovia, ' km')} en línea recta), "
            f"distancia a terminal de transporte de mercancías de {self._fmt(ttm, ' km')} e intermodal de {self._fmt(intermodal, ' km')}.\n"
            f"4. CONECTIVIDAD Y SUMINISTRO ELÉCTRICO: Cobertura de fibra FTTH del {self._fmt(ftth, '%')}, velocidad 1 Gbps del {self._fmt(c_1gbps, '%')} "
            f"y cobertura móvil 5G del {self._fmt(c_5g, '%')}. Calidad de red eléctrica provincial (2021): TIEPI de {self._fmt(tiepi, ' horas', 2)} y NIEPI de {self._fmt(niepi, '', 2)}.\n"
            f"5. RIESGOS AMBIENTALES E HÍDRICOS: Situación de {nivel_riesgo_hidrico} ({self._fmt(estres, '%')}) y agotamiento hídrico del {self._fmt(agotamiento, '%')}. "
            f"Aguas subterráneas en mal estado: {self._fmt(sub_cuant, '%')} cuantitativo y {self._fmt(sub_quim, '%')} químico. "
            f"Histórico de riesgos: {self._fmt(incendios_n, ' siniestros forestales', 0)} (2006-2015, {self._fmt(ha_quemadas, ' ha')} afectadas) "
            f"y {self._fmt(eventos_cnih, ' eventos extremos CNIH', 0)} (2000-2023, último en {self._fmt(ultimo_cnih, '', 0)}).\n"
            f"6. POTENCIAL ENERGÉTICO RENOVABLE: Irradiación solar GHI de {self._fmt(ghi, ' kWh/m²/año', 0)} y velocidad media del viento a 100m de {self._fmt(viento, ' m/s', 2)}."
        )

        raw_metadata = {
            "source_type": "ficha_municipal",
            "cod_ine": cod_ine,
            "nombre": nombre,
            "provincia": provincia,
            "ccaa": ccaa,
            "cluster": cluster_str,
            "poblacion": float(pob) if pd.notna(pob) else -1.0,
            "suelo_industrial_ha": float(suelo_ha) if pd.notna(suelo_ha) else 0.0,
            "dist_autovia_km": float(autovia) if pd.notna(autovia) else -1.0,
            "estres_hidrico_pct": float(estres) if pd.notna(estres) else -1.0,
            "cobertura_ftth_pct": float(ftth) if pd.notna(ftth) else -1.0,
            "irradiacion_ghi": float(ghi) if pd.notna(ghi) else -1.0,
        }

        return {"content": text_content, "metadata": raw_metadata}

    def load_csv_municipalities(self, filename: str = "dataset_municipal.csv") -> list[dict[str, Any]]:
        """Lee el CSV municipal y genera fichas descriptivas estructuradas."""
        file_path = os.path.join(self.data_path, filename)
        if not os.path.exists(file_path):
            print(f"[Advertencia] No se encontró el archivo en {file_path}.")
            return []

        df = pd.read_csv(file_path, dtype={"cod_ine": str, "cod_provincia": str})
        documents = [self._construir_ficha_municipio(row) for _, row in df.iterrows()]
        print(f"[Éxito] Se han procesado {len(documents)} fichas municipales desde {filename}.")
        return documents

    def load_markdown_docs(self, docs_dir: str = "docs/") -> list[dict[str, Any]]:
        """Carga documentación metodológica, fuentes y gobernanza en Markdown."""
        documents = []
        if not os.path.exists(docs_dir):
            return documents

        for root, _, files in os.walk(docs_dir):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            documents.append({
                                "content": content,
                                "metadata": {
                                    "source_type": "documentacion",
                                    "source": file_path,
                                },
                            })
        print(f"[Éxito] Se han cargado {len(documents)} documentos Markdown desde {docs_dir}.")
        return documents

    def load_all(
        self, csv_filename: str = "dataset_municipal.csv", docs_dir: str = "docs/"
    ) -> list[dict[str, Any]]:
        """Carga conjunta de fichas municipales y documentación técnica."""
        return self.load_csv_municipalities(csv_filename) + self.load_markdown_docs(docs_dir)

if __name__ == "__main__":
    # Prueba rápida de ejecución directa
    loader = SiteWiseLoader()
    docs = loader.load_all()
    if docs:
        print("\n--- EJEMPLO DE DOCUMENTO GENERADO ---")
        print(docs[0]["content"])
        print("\n--- METADATOS ---")
        print(docs[0]["metadata"])