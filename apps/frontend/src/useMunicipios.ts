import { useEffect, useMemo, useState } from 'react'
import type { FeatureCollection, Geometry } from 'geojson'
import type { Municipio } from './municipiosEjemplo'

export type DatosMunicipio = Municipio & {
  cod_ine: string
  cod_provincia: string
}

export type Contornos = FeatureCollection<Geometry, DatosMunicipio>

export function useMunicipios() {
  const [datos, setDatos] = useState<Contornos | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    const controlador = new AbortController()

    async function cargar() {
      try {
        const respuesta = await fetch('/mapas/municipios.geojson', {
          signal: controlador.signal,
        })

        if (!respuesta.ok) throw new Error('No se pudo cargar el mapa')

        const contenido: Contornos = await respuesta.json()

        if (
          contenido.type !== 'FeatureCollection' ||
          !Array.isArray(contenido.features)
        ) {
          throw new Error('Formato de mapa incorrecto')
        }

        if (!controlador.signal.aborted) setDatos(contenido)
      } catch {
        if (!controlador.signal.aborted) setError(true)
      }
    }

    cargar()
    return () => controlador.abort()
  }, [])

  // Aprovechamos los datos del mapa para crear la lista del buscador.
  const municipios = useMemo(() => {
    return datos?.features.map(({ properties: item }) => ({
      cod_ine: String(item.cod_ine).padStart(5, '0'),
      nombre: item.nombre,
      provincia: item.provincia,
      lat: Number(item.lat),
      lon: Number(item.lon),
    })) ?? []
  }, [datos])

  return { datos, municipios, error }
}