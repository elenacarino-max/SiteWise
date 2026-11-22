import { useRef, useState } from 'react'
import ConfiguracionInversion from './ConfiguracionInversion'
import { mostrarIndicador, useIndicadores } from './useIndicadores'
import gruposIndicadores from './gruposIndicadores.json'
import { capasMapa, tonosMapa } from './capasMapa'
import MapaMunicipios from './MapaMunicipios'
import type { Municipio } from './municipiosEjemplo'
import { useMunicipios } from './useMunicipios'
import './App.css'

const iconos = {
  desplegar: <path d="m6 9 6 6 6-6" />,
  inversion: <><path d="M4 6h16M4 12h16M4 18h16" /><path d="M8 4v4m8 2v4m-6 2v4" /></>,
  capas: <><path d="m12 2 10 5-10 5L2 7l10-5Z" /><path d="m2 12 10 5 10-5M2 17l10 5 10-5" /></>,
  pin: <><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></>,
  ficha: <><rect x="5" y="3" width="14" height="18" rx="2" /><path d="M9 8h6M9 12h6M9 16h4" /></>,
  comparar: <><rect x="3" y="8" width="13" height="13" rx="2" /><path d="M8 8V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-3" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5m0-8h.01" /></>,
  buscar: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4 4" /></>,
  asistente: <path d="M21 15a2 2 0 0 1-2 2H9l-5 4v-4a2 2 0 0 1-1-2V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z" />,
}

const pestanas = [
  { nombre: 'Explorar', icono: 'pin' },
  { nombre: 'Detalle', icono: 'ficha' },
  { nombre: 'Comparar', icono: 'comparar' },
] as const

const indicadoresResumen = [
  ['suelo_industrial_cartografiado_ha', 'Suelo cartografiado'],
  ['dist_recta_eje_autovia_km', 'Distancia a autovía'],
  ['dist_recta_ttm_km', 'Distancia a terminal de mercancías'],
]

const diferencias: Record<string, { sentido: number; texto: string }> = {
  dist_recta_eje_autovia_km: { sentido: -1, texto: 'Más cerca de autovía' },
  dist_recta_ttm_km: { sentido: -1, texto: 'Más cerca de terminal' },
  cobertura_ftth_pct: { sentido: 1, texto: 'Mayor cobertura de fibra' },
  cobertura_5g_pct: { sentido: 1, texto: 'Mayor cobertura 5G' },
}

function Icono({ nombre }: { nombre: keyof typeof iconos }) {
  return (
    <svg className="icono" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {iconos[nombre]}
    </svg>
  )
}

function normalizar(texto: string) {
  return texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es').trim()
}

function App() {
  const { datos, municipios, error } = useMunicipios()
  const [seccion, setSeccion] = useState('Explorar')
  const [busqueda, setBusqueda] = useState('')
  const [preguntaAsistente, setPreguntaAsistente] = useState('')
  const [municipio, setMunicipio] = useState<Municipio | null>(null)
  const [comparados, setComparados] = useState<Municipio[]>([])
  const [aviso, setAviso] = useState('')
  const [capaId, setCapaId] = useState('suelo_industrial_cartografiado_ha')
  const capaMapa = capasMapa.find((capa) => capa.id === capaId) ?? capasMapa[0]
  const { datos: tablaIndicadores, error: errorIndicadores } = useIndicadores(
    Boolean(municipio || comparados.length || capaMapa.cortes),
  )
  const resumen = useRef<HTMLElementTagNameMap['article']>(null)
  const contenido = useRef<HTMLElementTagNameMap['section']>(null)

  function estaGuardado(item: Municipio) {
    return comparados.some((guardado) =>
      guardado.nombre === item.nombre && guardado.provincia === item.provincia,
    )
  }

  function agregar(item: Municipio) {
    if (estaGuardado(item)) {
      setAviso(item.nombre + ' ya está en la comparación.')
      return
    }
    if (comparados.length >= 3) {
      setAviso('Ya tienes tres municipios. Quita uno en Comparar para añadir otro.')
      return
    }
    setComparados((actuales) => [...actuales, item])
    setAviso(item.nombre + ' añadido a la comparación.')
  }

  function quitar(item: Municipio) {
    setComparados((actuales) => actuales.filter((guardado) =>
      guardado.nombre !== item.nombre || guardado.provincia !== item.provincia,
    ))
    setAviso(item.nombre + ' eliminado de la comparación.')
    contenido.current?.focus()
  }

  const textoBusqueda = normalizar(busqueda)
  const hayBusqueda = textoBusqueda.length >= 2
  const resultados = !hayBusqueda
    ? []
    : municipios
        .filter((item) =>
          normalizar(item.nombre + ' ' + item.provincia).includes(textoBusqueda),
        )
        .slice(0, 20)

  function cambiarSeccion(nombre: string) {
    setSeccion(nombre)
    if (nombre === 'Explorar') setAviso('')
    contenido.current?.focus()
  }

  function previsualizar(item: Municipio, desdeBusqueda = false) {
    setMunicipio(item)
    setBusqueda('')
    if (desdeBusqueda) requestAnimationFrame(() => resumen.current?.focus())
  }

  function seleccionar(item: Municipio) {
    setMunicipio(item)
    setSeccion('Detalle')
    contenido.current?.focus()
  }

  return (
    <>
      <header className="cabecera-sitewise">
        <div className="marca-sitewise">
          <Icono nombre="capas" />
          <h1>SiteWise</h1>
        </div>
        <div className="navegacion" role="group" aria-label="Seleccionar sección">
          {pestanas.map(({ nombre, icono }) => {
            const sinContenido =
              (nombre === 'Detalle' && !municipio) ||
              (nombre === 'Comparar' && comparados.length === 0)

            return (
              <button
                key={nombre}
                className={sinContenido ? 'pestana-atenuada' : undefined}
                type="button"
                aria-pressed={seccion === nombre}
                onClick={() => cambiarSeccion(nombre)}
              >
                <Icono nombre={icono} />
                <span>{nombre}{nombre === 'Comparar' && comparados.length > 0 ? ' (' + comparados.length + ')' : ''}</span>
              </button>
            )
          })}
        </div>
      </header>

      <main>
        <section ref={contenido} tabIndex={-1}>
          <p className="estado-accion" role="status">{aviso}</p>

          <details className="panel-inversion" hidden={seccion !== 'Explorar'}>
            <summary className="titulo-desplegable">
              <Icono nombre="inversion" />
              Configuración de inversión
              <span className="flecha-desplegable"><Icono nombre="desplegar" /></span>
            </summary>
            <p className="estado-evaluacion"><Icono nombre="info" /> La evaluación territorial aún no está disponible</p>
            <ConfiguracionInversion />
          </details>

          {seccion === 'Explorar' && (
            <div className="explorar-contenido">
              <search className="buscador">
                <label htmlFor="municipio">Buscar municipio o provincia</label>
                <div className="campo-busqueda">
                  <Icono nombre="buscar" />
                  <input id="municipio" name="municipio" type="search" value={busqueda}
                    onChange={(event) => setBusqueda(event.target.value)}
                    autoCorrect="off" autoCapitalize="none" spellCheck={false}
                    placeholder="Buscar municipio o provincia…" />
                </div>

                {hayBusqueda && (
                  <section className="zona-resultados" aria-live="polite">
                    <h2>Resultados de búsqueda ({resultados.length})</h2>
                    {resultados.length > 0 ? (
                      <ul className="resultados" role="list">
                        {resultados.map((item) => (
                          <li key={item.cod_ine}>
                            <button type="button" onClick={() => previsualizar(item, true)}>
                              <strong>{item.nombre}</strong>
                              <span>Provincia: {item.provincia}</span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>{error
                        ? 'El buscador no está disponible porque ha fallado la carga.'
                        : !datos
                          ? 'Cargando municipios…'
                          : 'No hay coincidencias. Prueba con otro nombre o provincia.'}</p>
                    )}
                  </section>
                )}

                {busqueda.trim().length === 1 && (
                  <p className="ayuda-resultados">Añade otra letra para empezar la búsqueda.</p>
                )}
              </search>

              <div className="explorar-mapa">
                <div className="controles-mapa">
                  <div className="selector-capa">
                    <label htmlFor="capa-mapa"><Icono nombre="capas" /> Capa del mapa</label>
                    <select id="capa-mapa" value={capaId} onChange={(evento) => setCapaId(evento.target.value)}>
                      {capasMapa.map((capa) => <option key={capa.id} value={capa.id}>{capa.nombre}</option>)}
                    </select>
                  </div>
                  {capaMapa.tramos && (
                    <div className="leyenda-mapa" aria-live="polite">
                      {tablaIndicadores ? (
                        <ul aria-label={'Leyenda: ' + capaMapa.nombre}>
                          {capaMapa.tramos.map((tramo, indice) => (
                            <li key={tramo}><span aria-hidden="true" style={{ backgroundColor: `var(${tonosMapa[indice]})` }} />{tramo}</li>
                          ))}
                          <li><span aria-hidden="true" />Sin dato</li>
                        </ul>
                      ) : (
                        <p>{errorIndicadores ? 'No se pudo cargar esta capa.' : 'Cargando datos de la capa…'}</p>
                      )}
                    </div>
                  )}
                </div>
                <MapaMunicipios datos={datos} error={error} codigoSeleccionado={municipio?.cod_ine}
                  capa={capaMapa} indicadores={tablaIndicadores} onSeleccionar={previsualizar} />
              </div>

              {municipio && (
                <article className="resumen-municipal" ref={resumen} tabIndex={-1} aria-labelledby="municipio-seleccionado">
                  <div className="cabecera-municipio" aria-live="polite">
                    <span className="marca-municipio"><Icono nombre="pin" /></span>
                    <div>
                      <h2 id="municipio-seleccionado">{municipio.nombre}</h2>
                      <p className="provincia-resumen">Provincia: {municipio.provincia}</p>
                    </div>
                  </div>
                  {tablaIndicadores ? (
                    <dl className="indicadores-resumen">
                      {indicadoresResumen.map(([id, nombre]) => (
                        <div key={id}><dt>{nombre}</dt><dd>{mostrarIndicador(tablaIndicadores, municipio.cod_ine, id)}</dd></div>
                      ))}
                      {capaMapa.cortes && !indicadoresResumen.some(([id]) => id === capaId) && (
                        <div><dt>{capaMapa.nombre}</dt><dd>{mostrarIndicador(tablaIndicadores, municipio.cod_ine, capaId)}</dd></div>
                      )}
                    </dl>
                  ) : (
                    <p role="status">{errorIndicadores ? 'No se pudieron cargar los indicadores.' : 'Cargando indicadores…'}</p>
                  )}
                  <div className="acciones-resumen">
                    <button className="boton-principal" type="button" onClick={() => seleccionar(municipio)}>
                      Ver ficha
                    </button>
                    <button type="button" className="boton-comparar"
                      aria-disabled={estaGuardado(municipio) || comparados.length >= 3}
                      onClick={() => agregar(municipio)}>
                      {estaGuardado(municipio) ? 'En la comparación' :
                        comparados.length >= 3 ? 'Comparación completa' : 'Añadir a comparar'}
                    </button>
                  </div>
                </article>
              )}

              <details className="chatbot-sitewise">
                <summary className="titulo-desplegable">
                  <Icono nombre="asistente" />
                  Asistente SiteWise
                  <span className="flecha-desplegable"><Icono nombre="desplegar" /></span>
                </summary>
                <div className="campo-asistente">
                  <label htmlFor="pregunta-asistente">Tu pregunta</label>
                  <textarea id="pregunta-asistente" name="pregunta" rows={3}
                    value={preguntaAsistente} onChange={(evento) => setPreguntaAsistente(evento.target.value)}
                    aria-describedby="estado-envio-asistente" />
                  <p id="estado-envio-asistente">El envío estará disponible cuando se conecte el asistente.</p>
                  <button type="button" disabled>Enviar</button>
                </div>
                <ul className="preguntas-asistente" role="list" aria-label="Preguntas de ejemplo">
                  <li>¿Qué suelo industrial hay en este municipio?</li>
                  <li>¿Cómo está conectado para el transporte de mercancías?</li>
                  <li>¿Qué riesgos debería revisar antes de instalarme?</li>
                </ul>
              </details>
            </div>
          )}

          {seccion === 'Detalle' && (
            municipio ? (
              <article className="detalle-municipal">
                <h2>{municipio.nombre}</h2>
                <p>Provincia: {municipio.provincia}</p>
                {errorIndicadores && <p role="alert">No se pudieron cargar los indicadores municipales.</p>}
                {!tablaIndicadores && !errorIndicadores && <p role="status">Cargando indicadores municipales…</p>}
                {tablaIndicadores && (
                  <>
                    {gruposIndicadores.map((grupo) => (
                      <section key={grupo.nombre} className="bloque-indicadores">
                        <h3>{grupo.nombre}</h3>
                        <dl className="ficha-indicadores">
                          {grupo.indicadores.map((id) => {
                            const fuente = tablaIndicadores.indicadores[id]
                            const dato = tablaIndicadores.municipios[municipio.cod_ine]?.[id]
                            if (!fuente) return null
                            const url = dato?.url ?? fuente.url
                            const fecha = dato?.fecha_dato ?? fuente.fecha_dato
                            return (
                              <div key={id}>
                                <dt>{fuente.nombre}</dt>
                                <dd>{mostrarIndicador(tablaIndicadores, municipio.cod_ine, id)}</dd>
                                <dd className="fuente-indicador">
                                  {url && !url.includes('{') ? <a href={url}>{fuente.fuente}</a> : fuente.fuente}
                                  {fecha && <> · {fecha.replace('consulta_', 'Consulta ')}</>}
                                  {dato?.metodo && <span className="metodo-indicador">{dato.metodo}</span>}
                                </dd>
                              </div>
                            )
                          })}
                        </dl>
                      </section>
                    ))}
                    <p className="nota-pequena">Las distancias se miden en línea recta. El suelo cartografiado indica superficie industrial registrada en el catálogo.</p>
                  </>
                )}
                <div className="acciones-ficha">
                  <button
                    className="boton-principal"
                    type="button"
                    aria-disabled={estaGuardado(municipio) || comparados.length >= 3}
                    aria-describedby="limite-comparacion"
                    onClick={() => agregar(municipio)}
                  >
                    <Icono nombre="comparar" />
                    {estaGuardado(municipio) ? 'Ya está en la comparación' : 'Añadir a comparar'}
                  </button>
                  <button type="button" onClick={() => cambiarSeccion('Comparar')}>
                    Ver comparación ({comparados.length}/3)
                  </button>
                  <button type="button" onClick={() => cambiarSeccion('Explorar')}>
                    Volver al buscador
                  </button>
                </div>
                <p id="limite-comparacion">Puedes guardar hasta tres municipios. Para cambiar uno, quítalo en Comparar.</p>
              </article>
            ) : (
              <div className="estado-vacio">
                <p>Selecciona un municipio para ver su ficha.</p>
                <button type="button" onClick={() => cambiarSeccion('Explorar')}>
                  Ir a Explorar
                </button>
              </div>
            )
          )}

          {seccion === 'Comparar' && (
            <>
              <p className="nota-pequena">
                {comparados.length} de 3 municipios seleccionados. La selección se conserva mientras navegas y se borra al recargar la página.
              </p>

              <div className="tarjetas-comparacion" aria-label="Municipios de la comparación">
                {[0, 1, 2].map((indice) => {
                  const item = comparados[indice]
                  return (
                    <article className="tarjeta-municipio" key={item ? item.cod_ine : `vacio-${indice}`}>
                      {item ? (
                        <>
                          <span className="numero-tarjeta">Municipio {indice + 1}</span>
                          <h3>{item.nombre}</h3>
                          <p>{item.provincia}</p>
                          <button type="button" onClick={() => quitar(item)}>
                            Quitar
                          </button>
                        </>
                      ) : (
                        <button
                          className="boton-anadir"
                          type="button"
                          onClick={() => cambiarSeccion('Explorar')}
                        >
                          + Añadir municipio
                        </button>
                      )}
                    </article>
                  )
                })}
              </div>

              {comparados.length > 0 && errorIndicadores && <p role="alert">No se pudieron cargar los indicadores municipales.</p>}
              {comparados.length > 0 && !tablaIndicadores && !errorIndicadores && <p role="status">Cargando indicadores municipales…</p>}
              {comparados.length > 0 && (
                <div className="tabla-comparacion" role="region" aria-labelledby="titulo-tabla" tabIndex={0}>
                  <table>
                    <caption id="titulo-tabla">Comparación de municipios</caption>
                    <thead>
                      <tr>
                        <th scope="col">Información</th>
                        {comparados.map((item) => (
                          <th scope="col" key={item.cod_ine}>{item.nombre}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <th scope="row">Provincia</th>
                        {comparados.map((item) => (
                          <td key={item.cod_ine}>{item.provincia}</td>
                        ))}
                      </tr>
                    </tbody>
                    {tablaIndicadores && gruposIndicadores.map((grupo) => (
                      <tbody key={grupo.nombre}>
                        <tr className="grupo-comparacion"><th scope="rowgroup" colSpan={comparados.length + 1}>{grupo.nombre}</th></tr>
                        {grupo.indicadores.map((id) => {
                          const indicador = tablaIndicadores.indicadores[id]
                          if (!indicador) return null
                          const diferencia = diferencias[id]
                          const valores = comparados.map((item) => tablaIndicadores.municipios[item.cod_ine]?.[id])
                          const orden = diferencia ? valores.map((dato) =>
                            dato?.estado === 'real' ? dato.valor * diferencia.sentido : NaN,
                          ) : []
                          const mejor = orden.length > 1 ? Math.max(...orden) : NaN
                          const unico = orden.filter((valor) => valor === mejor).length === 1
                          return (
                            <tr key={id}>
                              <th scope="row">{indicador.nombre}</th>
                              {comparados.map((item, indice) => (
                                <td key={item.cod_ine}>
                                  {mostrarIndicador(tablaIndicadores, item.cod_ine, id)}
                                  {unico && orden[indice] === mejor && <strong className="diferencia-comparacion">{diferencia.texto}</strong>}
                                </td>
                              ))}
                            </tr>
                          )
                        })}
                      </tbody>
                    ))}
                    <tbody>
                      <tr>
                        <th scope="row">Acciones</th>
                        {comparados.map((item) => (
                          <td key={item.cod_ine}>
                            <button type="button" onClick={() => seleccionar(item)} aria-label={'Ver ficha de ' + item.nombre}>
                              Ver ficha
                            </button>
                          </td>
                        ))}
                      </tr>
                    </tbody>
                  </table>
                </div>
              )}

              <button type="button" onClick={() => cambiarSeccion('Explorar')}>
                {comparados.length === 0 ? 'Ir a Explorar' : 'Buscar otro municipio'}
              </button>
            </>
          )}
        </section>
      </main>
    </>
  )
}

export default App
