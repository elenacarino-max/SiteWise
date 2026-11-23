import { useEffect, useState } from 'react'
import type { FichaMunicipalApi } from './useApiSitewise'

type Valor = {
  valor: number
  estado: 'real' | 'aproximado'
  metodo?: string
  url?: string
  fecha_dato?: string
  nota?: string
  sinPoligonos?: boolean
}
export type DatosIndicadores = {
  indicadores: Record<string, { nombre: string; unidad: string; fuente: string; url: string; fecha_dato: string }>
  municipios: Record<string, Record<string, Valor | undefined>>
}

export function adaptarFicha({ municipio, indicadores }: FichaMunicipalApi): DatosIndicadores {
  const definiciones: DatosIndicadores['indicadores'] = {}
  const valores: Record<string, Valor> = {}
  for (const dato of indicadores) {
    const id = dato.id_indicador
    definiciones[id] = {
      nombre: dato.nombre ?? id.replaceAll('_', ' '),
      unidad: dato.unidad ?? '',
      fuente: dato.fuente ?? dato.fuente_id ?? 'Fuente no disponible',
      url: dato.url_fuente ?? '',
      fecha_dato: dato.fecha_dato ?? '',
    }
    if (dato.valor === null) continue
    const sinPoligonos = dato.estado === 'sin_poligonos_en_catalogo'
    if (!dato.utilizable && !sinPoligonos) continue
    valores[id] = {
      valor: dato.valor,
      estado: dato.aproximado ? 'aproximado' : 'real',
      metodo: dato.metodo ?? undefined,
      sinPoligonos,
      nota: dato.estado === 'calculado_sobre_masas_catalogadas' ? 'Sobre masas catalogadas' : undefined,
    }
  }
  return { indicadores: definiciones, municipios: { [municipio.cod_ine]: valores } }
}

export function useIndicadores(activo: boolean) {
  const [datos, setDatos] = useState<DatosIndicadores | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!activo || datos) return

    const controlador = new AbortController()
    async function cargar() {
      try {
        const respuesta = await fetch(import.meta.env.BASE_URL + 'indicadores-municipales.json', {
          signal: controlador.signal,
        })
        if (!respuesta.ok) throw new Error('No se pudieron cargar los indicadores')
        const tabla: DatosIndicadores = await respuesta.json()
        if (!controlador.signal.aborted) {
          setError(false)
          setDatos(tabla)
        }
      } catch {
        if (!controlador.signal.aborted) setError(true)
      }
    }
    void cargar()
    return () => controlador.abort()
  }, [activo, datos])

  return { datos, error }
}

export function formatearIndicador(
  datos: DatosIndicadores | null,
  codigo: string,
  id: string,
) {
  const dato = datos?.municipios[codigo]?.[id]
  const indicador = datos?.indicadores[id]
  if (!dato || !indicador) return { texto: 'Sin dato', nota: '' }
  if (id.startsWith('suelo_industrial_cartografiado') && dato.valor === 0 && dato.sinPoligonos !== false) {
    return { texto: `0 ${indicador.unidad} cartografiado`, nota: 'Sin polígonos en el catálogo' }
  }
  const valor = dato.valor.toLocaleString('es-ES', { maximumFractionDigits: 2 })
  const nota = [dato.estado === 'aproximado' ? 'Aproximado' : '', dato.nota].filter(Boolean).join(' · ')
  return { texto: [valor, indicador.unidad].filter(Boolean).join(' '), nota }
}

export function mostrarIndicador(datos: DatosIndicadores | null, codigo: string, id: string) {
  const { texto, nota } = formatearIndicador(datos, codigo, id)
  return nota ? texto + (nota === 'Aproximado' ? ' (aproximado)' : ' · sin polígonos en el catálogo') : texto
}
