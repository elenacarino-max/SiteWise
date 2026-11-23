import type { DatosIndicadores } from './useIndicadores'
import type { EstadoMinimo, Evaluacion, Nota } from './useApiSitewise'

const estados: Record<EstadoMinimo, string> = {
  cumple: 'Cumple',
  no_cumple: 'No cumple',
  no_evaluable: 'No evaluable',
}

const puntos = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 2 })
const porcentaje = new Intl.NumberFormat('es-ES', { style: 'percent', maximumFractionDigits: 0 })

function NotaEvaluada({ titulo, nota }: { titulo: string; nota: Nota }) {
  return (
    <div>
      <dt>{titulo}</dt>
      <dd>
        <strong>{nota.nota === null ? (nota.estado === 'sin_reglas' ? 'Sin reglas' : 'No evaluable') : puntos.format(nota.nota) + ' / 100'}</strong>
        {nota.estado === 'calculada_parcial' && (
          <span>Nota parcial · Cobertura de datos: {porcentaje.format(nota.confianza)}</span>
        )}
        {nota.motivo && <span>{nota.motivo}</span>}
      </dd>
    </div>
  )
}

export default function EvaluacionMunicipal({ evaluacion, datos }: {
  evaluacion: Evaluacion
  datos: DatosIndicadores | null
}) {
  const nombre = (id: string) => datos?.indicadores[id]?.nombre ?? id.replaceAll('_', ' ')

  return (
    <>
      <dl className="notas-actividad">
        <NotaEvaluada titulo="Riesgo relativo" nota={evaluacion.riesgo} />
        <NotaEvaluada titulo="Atractivo relativo" nota={evaluacion.atractivo} />
        <div>
          <dt>Requisitos mínimos</dt>
          <dd><strong>{estados[evaluacion.cumple_minimos]}</strong></dd>
        </div>
      </dl>
      {evaluacion.minimos.length > 0 ? (
        <details className="explicacion-evaluacion">
          <summary>Cómo se han evaluado los requisitos</summary>
          <ul>
            {evaluacion.minimos.map((minimo, indice) => (
              <li key={minimo.id_indicador + '-' + indice}>
                <strong>{nombre(minimo.id_indicador)} · {estados[minimo.estado]}</strong>
                {minimo.motivo && <div>{minimo.motivo}</div>}
                {minimo.aviso && <div>{minimo.aviso}</div>}
              </li>
            ))}
          </ul>
        </details>
      ) : evaluacion.motivo_minimos && <p className="nota-actividad">{evaluacion.motivo_minimos}</p>}
      {([evaluacion.riesgo, evaluacion.atractivo].some((nota) => nota.componentes.length > 0)) && (
        <details className="explicacion-evaluacion">
          <summary>Cómo se calculan las notas</summary>
          {([['Riesgo', evaluacion.riesgo], ['Atractivo', evaluacion.atractivo]] as const).map(([titulo, nota]) =>
            nota.componentes.length > 0 && (
              <div key={titulo}>
                <p><strong>{titulo}</strong></p>
                <ul>
                  {nota.componentes.map((componente, indice) => (
                    <li key={componente.id_indicador + '-' + indice}>
                      <strong>{nombre(componente.id_indicador)}</strong>
                      {' · Peso '}{puntos.format(componente.peso)}
                      {componente.percentil !== null && ' · Percentil ' + puntos.format(componente.percentil)}
                      {componente.aproximado && ' · Aproximado'}
                      {!componente.usado && <div>{componente.motivo || 'Sin valor utilizable para esta nota'}</div>}
                    </li>
                  ))}
                </ul>
              </div>
            ),
          )}
        </details>
      )}
    </>
  )
}
