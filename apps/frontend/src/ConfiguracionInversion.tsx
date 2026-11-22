import { useState } from 'react'

const catalogo: Record<string, readonly string[]> = {
  Agroalimentación: ['Planta de procesado de alimentos', 'Almacén frigorífico'],
  Energía: ['Planta solar fotovoltaica', 'Parque eólico'],
  Logística: ['Centro de distribución', 'Plataforma intermodal'],
  Manufactura: ['Fábrica de papel', 'Fábrica de cerámica'],
  Tecnología: ['Centro de datos'],
}

const rangos = ['Menos de 5 M€', 'De 5 a menos de 20 M€', '20 M€ o más']
const tolerancias = ['Baja', 'Equilibrada', 'Alta']

export default function ConfiguracionInversion() {
  const [sector, setSector] = useState('')
  const [actividad, setActividad] = useState('')

  return (
    <fieldset className="configuracion-inversion">
      <legend className="solo-lectura">Configuración de la inversión</legend>
      <div>
        <label htmlFor="sector">Sector</label>
        <select id="sector" name="sector" value={sector} onChange={(event) => {
          setSector(event.target.value)
          setActividad('')
        }}>
          <option value="">Seleccionar sector</option>
          {Object.keys(catalogo).map((opcion) => <option key={opcion}>{opcion}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="actividad">Industria o actividad</label>
        <select id="actividad" name="actividad" disabled={!sector} value={actividad}
          onChange={(event) => setActividad(event.target.value)}>
          <option value="">Seleccionar actividad</option>
          {(catalogo[sector] ?? []).map((opcion) => <option key={opcion}>{opcion}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="inversion">Inversión estimada</label>
        <select id="inversion" name="inversion" defaultValue="">
          <option value="">Seleccionar rango</option>
          {rangos.map((opcion) => <option key={opcion}>{opcion}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="tolerancia">Tolerancia al riesgo</label>
        <select id="tolerancia" name="tolerancia" defaultValue="">
          <option value="">Seleccionar nivel</option>
          {tolerancias.map((opcion) => <option key={opcion}>{opcion}</option>)}
        </select>
      </div>
    </fieldset>
  )
}
