// Municipios de ejemplo para desarrollar la interfaz.
export type Municipio = {
  cod_ine: string
  nombre: string
  provincia: string
  lat: number
  lon: number
}

export const municipiosEjemplo: Municipio[] = [
  { cod_ine: '50297', nombre: 'Zaragoza', provincia: 'Zaragoza', lat: 41.6488, lon: -0.8891 },
  { cod_ine: '47186', nombre: 'Valladolid', provincia: 'Valladolid', lat: 41.6523, lon: -4.7245 },
  { cod_ine: '29067', nombre: 'Málaga', provincia: 'Málaga', lat: 36.7213, lon: -4.4214 },
  { cod_ine: '28005', nombre: 'Alcalá de Henares', provincia: 'Madrid', lat: 40.4818, lon: -3.3641 },
  { cod_ine: '36057', nombre: 'Vigo', provincia: 'Pontevedra', lat: 42.2406, lon: -8.7207 },
]