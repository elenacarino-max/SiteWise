import { useState } from 'react'
import { useApiSitewise } from './useApiSitewise'
import type { EstadoMinimo, FilaMapaApi } from './useApiSitewise'
import type { Municipio } from './municipiosEjemplo'

type Dimension = 'atractivo' | 'riesgo'
type FilaRanking = FilaMapaApi & Omit<Municipio, 'provincia'> & {
  provincia: string | null
  posicion: number
  cumple_minimos: EstadoMinimo
}
type RespuestaRanking = {
  total: number
  sin_nota: number
  filas: FilaRanking[]
  reglas_provisionales: boolean
  aviso_alcance: string
}

const porPagina = 20
const requisitos: Record<EstadoMinimo, string> = {
  cumple: 'Cumple',
  no_cumple: 'No cumple',
  no_evaluable: 'No evaluable',
}

export default function RankingActividad({ actividad, onVerFicha, onComparar, estaGuardado, comparacionLlena }: {
  actividad: string
  onVerFicha: (municipio: Municipio) => void
  onComparar: (municipio: Municipio) => void
  estaGuardado: (municipio: Municipio) => boolean
  comparacionLlena: boolean
}) {
  const [dimension, setDimension] = useState<Dimension>('atractivo')
  const [pagina, setPagina] = useState(0)
  const params = new URLSearchParams({
    ordenar_por: dimension,
    limite: String(porPagina),
    desplazamiento: String(pagina * porPagina),
  })
  const resultado = useApiSitewise<RespuestaRanking>(`/actividades/${encodeURIComponent(actividad)}/ranking?${params}`)
  const ranking = resultado.datos
  const nombreDimension = dimension === 'atractivo' ? 'Atractivo relativo' : 'Riesgo relativo'

  return (
    <div className="ranking-actividad">
      <div className="selector-actividad">
        <label htmlFor="dimension-ranking">Ordenar por</label>
        <select id="dimension-ranking" value={dimension} onChange={(evento) => {
          setDimension(evento.target.value === 'riesgo' ? 'riesgo' : 'atractivo')
          setPagina(0)
        }}>
          <option value="atractivo">Atractivo relativo · de mayor a menor</option>
          <option value="riesgo">Riesgo relativo · de menor a mayor</option>
        </select>
      </div>
      {resultado.estado === 'error' && <p role="alert">No se pudo cargar el ranking de esta actividad.</p>}
      {ranking?.reglas_provisionales && <p className="aviso-reglas">Evaluación orientativa · Reglas provisionales</p>}
      <p role="status" className="nota-actividad">
        {resultado.estado === 'cargando' && 'Cargando ranking…'}
        {ranking && (ranking.total > 0
          ? `Municipios ${pagina * porPagina + 1}–${pagina * porPagina + ranking.filas.length} de ${ranking.total.toLocaleString('es-ES')} con nota.`
          : 'No hay municipios con nota en esta dimensión.')}
        {ranking && ranking.sin_nota > 0 && ` Sin nota: ${ranking.sin_nota.toLocaleString('es-ES')}.`}
      </p>
      {ranking && ranking.filas.length > 0 && (
        <div className="tabla-comparacion tabla-ranking" role="region" aria-labelledby="titulo-tabla-ranking" tabIndex={0}>
          <table>
            <caption id="titulo-tabla-ranking" className="solo-lectura">Ranking por {nombreDimension.toLowerCase()}</caption>
            <thead>
              <tr>
                <th scope="col">Municipio</th>
                <th scope="col" aria-sort={dimension === 'riesgo' ? 'ascending' : 'descending'}>{nombreDimension}</th>
                <th scope="col">Requisitos mínimos</th>
                <th scope="col">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {ranking.filas.map((fila) => {
                const municipio = { ...fila, provincia: fila.provincia ?? 'Provincia sin dato' }
                const guardado = estaGuardado(municipio)
                const nota = fila[`${dimension}_nota`]
                return (
                  <tr key={fila.cod_ine}>
                    <th scope="row">
                      <span className="nota-indicador">#{fila.posicion}</span> {fila.nombre}
                      <span className="provincia-ranking">{municipio.provincia}</span>
                    </th>
                    <td>
                      <strong>{nota === null ? 'Sin nota' : `${nota.toLocaleString('es-ES')} / 100`}</strong>
                      {fila[`${dimension}_estado`] === 'calculada_parcial' && (
                        <span className="provincia-ranking">Nota parcial · Cobertura: {fila[`${dimension}_confianza`]
                          .toLocaleString('es-ES', { style: 'percent', maximumFractionDigits: 0 })}</span>
                      )}
                    </td>
                    <td>{requisitos[fila.cumple_minimos]}</td>
                    <td><div className="acciones-municipio">
                      <button type="button" aria-label={`Ver ficha de ${fila.nombre}`} onClick={() => onVerFicha(municipio)}>Ver ficha</button>
                      <button type="button" aria-label={`${guardado ? 'En la comparación' : 'Añadir a comparar'}: ${fila.nombre}`}
                        disabled={guardado || comparacionLlena} onClick={() => onComparar(municipio)}>
                        {guardado ? 'En la comparación' : 'Añadir a comparar'}
                      </button>
                    </div></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      {(pagina > 0 || (ranking && ranking.total > porPagina)) && (
        <div className="paginacion-ranking" role="group" aria-label="Paginación del ranking">
          <button type="button" disabled={pagina === 0 || resultado.estado === 'cargando'}
            onClick={() => setPagina(pagina - 1)}>Anterior</button>
          <button type="button" disabled={!ranking || (pagina + 1) * porPagina >= ranking.total}
            onClick={() => setPagina(pagina + 1)}>Siguiente</button>
        </div>
      )}
      {comparacionLlena && <p className="nota-actividad">Ya hay tres municipios en Comparar. Quita uno para añadir otro.</p>}
      {ranking && <p className="nota-actividad">{ranking.aviso_alcance}</p>}
    </div>
  )
}
