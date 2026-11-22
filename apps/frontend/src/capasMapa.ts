export const capasMapa = [
  { id: 'base', nombre: 'Municipios' },
  { id: 'suelo_industrial_cartografiado_ha', nombre: 'Suelo industrial cartografiado',
    cortes: [1, 10], tramos: ['Menos de 1 ha', 'De 1 a menos de 10 ha', '10 ha o más'] },
  { id: 'dist_recta_eje_autovia_km', nombre: 'Distancia a autovía o autopista',
    cortes: [5, 20], tramos: ['Menos de 5 km', 'De 5 a menos de 20 km', '20 km o más'] },
  { id: 'cobertura_ftth_pct', nombre: 'Cobertura de fibra',
    cortes: [50, 90], tramos: ['Menos del 50 %', 'Del 50 a menos del 90 %', '90 % o más'] },
  { id: 'cobertura_5g_pct', nombre: 'Cobertura 5G',
    cortes: [50, 90], tramos: ['Menos del 50 %', 'Del 50 a menos del 90 %', '90 % o más'] },
  { id: 'estres_hidrico_pct', nombre: 'Estrés hídrico',
    cortes: [40, 80], tramos: ['Menos del 40 %', 'Del 40 a menos del 80 %', '80 % o más'] },
]

export const tonosMapa = ['--mapa-tramo-1', '--mapa-tramo-2', '--mapa-tramo-3']

export function tramoMapa(valor: number, cortes: number[]) {
  const indice = cortes.findIndex((corte) => valor < corte)
  return indice === -1 ? cortes.length : indice
}
