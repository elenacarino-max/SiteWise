import type { Actividad } from './useApiSitewise'

const nombres: Record<string, string> = {
  centro_logistico: 'Centro logístico',
  industria_agua: 'Industria intensiva en agua',
}

export default function ConfiguracionInversion({ id, actividades, actividad, onCambiar, estado, aviso }: {
  id: string
  actividades: Actividad[]
  actividad: string
  onCambiar: (actividad: string) => void
  estado: 'inactivo' | 'cargando' | 'listo' | 'error'
  aviso?: string
}) {
  return (
    <div className="selector-actividad">
      <label htmlFor={id}>Actividad evaluada</label>
      <select id={id} value={actividad} onChange={(evento) => onCambiar(evento.target.value)}
        disabled={actividades.length === 0} aria-describedby={id + '-estado'}>
        <option value="">Selecciona una actividad</option>
        {actividades.map(({ actividad: codigo }) => (
          <option key={codigo} value={codigo}>{nombres[codigo] ?? codigo.replaceAll('_', ' ')}</option>
        ))}
      </select>
      <p id={id + '-estado'} role="status">
        {estado === 'cargando' ? 'Cargando actividades…' :
          estado === 'error' ? 'No se pudo conectar con la API de evaluación. Los datos municipales siguen disponibles.' :
          aviso || 'Las notas dependen de la actividad elegida.'}
      </p>
    </div>
  )
}
