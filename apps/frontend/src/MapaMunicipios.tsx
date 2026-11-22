import { useMemo } from 'react'
import { GeoJSON, MapContainer, useMapEvents } from 'react-leaflet'
import { Path } from 'leaflet'
import type { LatLngBoundsExpression } from 'leaflet'
import type { Feature, FeatureCollection, LineString, Position } from 'geojson'
import type { Municipio } from './municipiosEjemplo'
import type { Contornos, DatosMunicipio } from './useMunicipios'
import { tonosMapa, tramoMapa } from './capasMapa'
import type { capasMapa } from './capasMapa'
import type { DatosIndicadores } from './useIndicadores'
import 'leaflet/dist/leaflet.css'

type Props = {
  datos: Contornos | null
  error: boolean
  codigoSeleccionado?: string
  capa: typeof capasMapa[number]
  indicadores: DatosIndicadores | null
  onSeleccionar: (municipio: Municipio) => void
}

type PropiedadesLimiteProvincia = {
  cod_provincias: string[]
}

type LimitesProvincia = FeatureCollection<LineString, PropiedadesLimiteProvincia>

const encuadrePrincipal: LatLngBoundsExpression = [[35.6, -9.5], [44, 4.5]]

function ReencuadrarMapaPrincipal() {
  const mapa = useMapEvents({
    resize() {
      mapa.fitBounds(encuadrePrincipal, { animate: false })
    },
  })

  return null
}

function crearLimitesProvincia(datos: Contornos | null): LimitesProvincia | null {
  if (!datos) return null

  const tramos = new Map<
    string,
    { coordenadas: [Position, Position]; provincias: Set<string> }
  >()

  for (const municipio of datos.features) {
    const geometria = municipio.geometry
    if (!geometria) continue

    const anillos: Position[][] = geometria.type === 'Polygon'
      ? geometria.coordinates
      : geometria.type === 'MultiPolygon'
        ? geometria.coordinates.flat()
        : []
    const provincia = String(municipio.properties.cod_provincia).padStart(2, '0')

    for (const anillo of anillos) {
      for (let indice = 0; indice < anillo.length - 1; indice += 1) {
        const inicio = anillo[indice]
        const fin = anillo[indice + 1]
        const claveInicio = `${inicio[0].toFixed(8)},${inicio[1].toFixed(8)}`
        const claveFin = `${fin[0].toFixed(8)},${fin[1].toFixed(8)}`
        const clave = claveInicio < claveFin
          ? `${claveInicio}|${claveFin}`
          : `${claveFin}|${claveInicio}`
        const tramo = tramos.get(clave)

        if (tramo) {
          tramo.provincias.add(provincia)
        } else {
          tramos.set(clave, {
            coordenadas: [inicio, fin],
            provincias: new Set([provincia]),
          })
        }
      }
    }
  }

  const features: Feature<LineString, PropiedadesLimiteProvincia>[] = []
  for (const tramo of tramos.values()) {
    if (tramo.provincias.size < 2) continue

    features.push({
      type: 'Feature',
      properties: { cod_provincias: [...tramo.provincias] },
      geometry: { type: 'LineString', coordinates: tramo.coordenadas },
    })
  }

  return { type: 'FeatureCollection', features }
}

export default function MapaMunicipios({ datos, error, codigoSeleccionado, capa, indicadores, onSeleccionar }: Props) {
  const limitesProvincia = useMemo(() => crearLimitesProvincia(datos), [datos])
  const estilos = useMemo(() => {
    const css = getComputedStyle(document.documentElement)
    const color = (variable: string) => css.getPropertyValue(variable).trim()
    const base = { color: color('--map-line'), weight: 0.3, fillColor: color('--map-fill'), fillOpacity: 1 }
    const tonos = tonosMapa.map(color)
    const cortes = capa.cortes
    return {
      base,
      acento: color('--accent'),
      halo: color('--surface'),
      provincia: color('--province-border'),
      municipio: (feature?: Feature) => {
        if (!feature?.properties || !cortes) return base
        const codigo = String(feature.properties.cod_ine).padStart(5, '0')
        const dato = indicadores?.municipios[codigo]?.[capa.id]
        return dato ? { ...base, fillColor: tonos[tramoMapa(dato.valor, cortes)] } : base
      },
    }
  }, [capa, indicadores])

  const seleccionado = useMemo(() => datos?.features.find((item) =>
    String(item.properties.cod_ine).padStart(5, '0') === codigoSeleccionado,
  ), [datos, codigoSeleccionado])

  if (error) {
    return <p role="alert">No se pudieron cargar los municipios. Recarga la página para volver a intentarlo.</p>
  }

  if (!datos) return <p role="status">Cargando municipios de España.</p>

  const features = datos.features
  function dibujar(canarias: boolean) {
    const zona: Contornos = {
      type: 'FeatureCollection',
      features: features.filter((municipio) => {
        const provincia = String(municipio.properties.cod_provincia)
        const esCanarias = provincia === '35' || provincia === '38'
        return esCanarias === canarias
      }),
    }

    return (
      <GeoJSON
        data={zona}
        style={estilos.municipio}
        onEachFeature={(feature, capa) => {
          const municipio = feature.properties as DatosMunicipio
          const etiqueta = document.createElement('span')
          etiqueta.textContent = `${municipio.nombre} · ${municipio.provincia}`
          capa.bindTooltip(etiqueta, { sticky: true })

          capa.on('mouseover', () => {
            if (capa instanceof Path) {
              capa.setStyle({ weight: 1.6 })
            }
          })

          capa.on('mouseout', () => {
            if (capa instanceof Path) capa.setStyle({ weight: estilos.base.weight })
          })

          capa.on('click', () => {
            onSeleccionar({
              cod_ine: String(municipio.cod_ine).padStart(5, '0'),
              nombre: municipio.nombre,
              provincia: municipio.provincia,
              lat: Number(municipio.lat),
              lon: Number(municipio.lon),
            })
          })
        }}
      />
    )
  }

  function dibujarSeleccion(canarias: boolean) {
    if (!seleccionado) return null
    const provincia = String(seleccionado.properties.cod_provincia)
    if ((provincia === '35' || provincia === '38') !== canarias) return null

    return (
      <>
        <GeoJSON key={codigoSeleccionado + '-halo'} data={seleccionado}
          style={{ color: estilos.halo, fill: false, weight: 6, opacity: capa.cortes ? 1 : 0 }}
          interactive={false} />
        <GeoJSON key={codigoSeleccionado} data={seleccionado}
          style={{ color: estilos.acento, fillColor: estilos.acento, fillOpacity: capa.cortes ? 0 : 0.65, weight: 3 }}
          interactive={false} />
      </>
    )
  }

  function dibujarLimitesProvincia(canarias: boolean) {
    if (!limitesProvincia) return null

    const codigosCanarias = new Set(['35', '38'])
    const limites = limitesProvincia.features.filter((limite) =>
      limite.properties.cod_provincias.some((codigo) => codigosCanarias.has(codigo)) === canarias,
    )

    if (limites.length === 0) return null

    const zona: LimitesProvincia = { type: 'FeatureCollection', features: limites }
    return (
      <>
        <GeoJSON
          data={zona}
          style={{ color: estilos.halo, weight: 3.6, fill: false }}
          interactive={false}
        />
        <GeoJSON
          data={zona}
          style={{ color: estilos.provincia, weight: 1.5, fill: false }}
          interactive={false}
        />
      </>
    )
  }

  return (
    <div>
      <div className="mapa-marco">
        <MapContainer
          bounds={encuadrePrincipal}
          zoomSnap={0.1}
          className="mapa-municipios mapa-principal"
          scrollWheelZoom={false}
          dragging={false}
          doubleClickZoom={false}
          touchZoom={false}
          boxZoom={false}
          keyboard={false}
          zoomControl={false}
          attributionControl={false}
          preferCanvas
        >
          <ReencuadrarMapaPrincipal />
          {dibujar(false)}
          {dibujarLimitesProvincia(false)}
          {dibujarSeleccion(false)}
        </MapContainer>

        <div className="mapa-canarias">
          <MapContainer
            bounds={[[27.5, -18.3], [29.5, -13.3]]}
            zoomSnap={0.1}
            className="mapa-municipios mapa-islas"
            scrollWheelZoom={false}
            dragging={false}
            doubleClickZoom={false}
            touchZoom={false}
            boxZoom={false}
            keyboard={false}
            zoomControl={false}
            attributionControl={false}
            preferCanvas
          >
            {dibujar(true)}
            {dibujarLimitesProvincia(true)}
            {dibujarSeleccion(true)}
          </MapContainer>
        </div>
      </div>

    </div>
  )
}
