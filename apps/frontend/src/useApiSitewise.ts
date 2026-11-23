import { useEffect, useState } from 'react'

export type Actividad = { actividad: string; estado_reglas: string; version_reglas: string }
export type ActividadesApi = { actividades: Actividad[]; aviso: string }

export type FichaMunicipalApi = {
  municipio: { cod_ine: string }
  indicadores: {
    id_indicador: string
    nombre: string | null
    unidad: string | null
    valor: number | null
    estado: string | null
    aproximado: boolean
    utilizable: boolean
    metodo: string | null
    fuente_id: string | null
    fuente?: string | null
    url_fuente?: string | null
    fecha_dato: string | null
  }[]
}

export type EstadoMinimo = 'cumple' | 'no_cumple' | 'no_evaluable'

export type Nota = {
  nota: number | null
  estado: 'calculada' | 'calculada_parcial' | 'no_evaluable' | 'sin_reglas'
  confianza: number
  motivo: string
  componentes: {
    id_indicador: string
    peso: number
    percentil: number | null
    usado: boolean
    aproximado: boolean
    motivo: string
  }[]
}

export type Evaluacion = {
  cod_ine: string
  riesgo: Nota
  atractivo: Nota
  cumple_minimos: EstadoMinimo
  motivo_minimos: string
  reglas_provisionales: boolean
  minimos: { id_indicador: string; estado: EstadoMinimo; aviso: string; motivo: string }[]
}

export type EvaluacionApi = {
  municipio: { cod_ine: string; nombre: string }
  evaluacion: Evaluacion
  aviso_alcance: string
}

export type ComparacionApi = {
  evaluaciones: EvaluacionApi[]
  reglas_provisionales: boolean
  aviso_alcance: string
  aviso_comparacion: string
}

export type FilaMapaApi = {
  cod_ine: string
  riesgo_nota: number | null
  riesgo_estado: Nota['estado']
  riesgo_confianza: number
  atractivo_nota: number | null
  atractivo_estado: Nota['estado']
  atractivo_confianza: number
}

export type MapaActividadApi = {
  filas: FilaMapaApi[]
  reglas_provisionales: boolean
  aviso_alcance: string
}

const baseApi = (import.meta.env.VITE_SITEWISE_API_BASE_URL?.trim() || '/api').replace(/\/+$/, '')

type Resultado<T> =
  | { estado: 'inactivo' | 'cargando' | 'error'; datos?: never }
  | { estado: 'listo'; datos: T }

export function useApiSitewise<T>(ruta: string | null): Resultado<T> {
  const [resultado, setResultado] = useState<{ ruta: string; respuesta: Resultado<T> }>()

  useEffect(() => {
    if (!ruta) return
    const controlador = new AbortController()
    async function cargar(ruta: string) {
      try {
        const respuesta = await fetch(baseApi + ruta, {
          headers: { Accept: 'application/json' },
          signal: AbortSignal.any([controlador.signal, AbortSignal.timeout(30_000)]),
        })
        if (!respuesta.ok) throw new Error(String(respuesta.status))
        const datos: T = await respuesta.json()
        if (!controlador.signal.aborted) setResultado({ ruta, respuesta: { estado: 'listo', datos } })
      } catch {
        if (!controlador.signal.aborted) setResultado({ ruta, respuesta: { estado: 'error' } })
      }
    }
    void cargar(ruta)
    return () => controlador.abort()
  }, [ruta])

  if (!ruta) return { estado: 'inactivo' }
  return resultado?.ruta === ruta ? resultado.respuesta : { estado: 'cargando' }
}

export function useFichaMunicipal(codigo: string | undefined) {
  return useApiSitewise<FichaMunicipalApi>(codigo ? `/municipios/${codigo}/ficha` : null)
}
