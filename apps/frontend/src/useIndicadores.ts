import { useEffect, useState } from 'react'

type Valor = {
  valor: number
  estado: 'real' | 'aproximado'
  metodo?: string
  url?: string
  fecha_dato?: string
}
export type DatosIndicadores = {
  indicadores: Record<string, { nombre: string; unidad: string; fuente: string; url: string; fecha_dato: string }>
  municipios: Record<string, Record<string, Valor | undefined>>
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
  if (id.startsWith('suelo_industrial_cartografiado') && dato.valor === 0) {
    return { texto: `0 ${indicador.unidad} cartografiado`, nota: 'Sin polígonos en el catálogo' }
  }
  const valor = dato.valor.toLocaleString('es-ES', { maximumFractionDigits: 2 })
  return { texto: valor + ' ' + indicador.unidad, nota: dato.estado === 'aproximado' ? 'Aproximado' : '' }
}

export function mostrarIndicador(datos: DatosIndicadores | null, codigo: string, id: string) {
  const { texto, nota } = formatearIndicador(datos, codigo, id)
  return nota ? texto + (nota === 'Aproximado' ? ' (aproximado)' : ' · sin polígonos en el catálogo') : texto
}
