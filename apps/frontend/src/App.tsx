import { useMemo, useRef, useState } from 'react'
import ConfiguracionInversion from './ConfiguracionInversion'
import EvaluacionMunicipal from './EvaluacionMunicipal'
import { useApiSitewise, useFichaMunicipal } from './useApiSitewise'
import type { ActividadesApi, ComparacionApi, EvaluacionApi, MapaActividadApi } from './useApiSitewise'
import { adaptarFicha, formatearIndicador, useIndicadores } from './useIndicadores'
import type { DatosIndicadores } from './useIndicadores'
import gruposIndicadores from './gruposIndicadores.json'
import { capasMapa, notaDeMapa, tonosMapa } from './capasMapa'
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

function ValorIndicador({ datos, codigo, id }: { datos: DatosIndicadores; codigo: string; id: string }) {
  const { texto, nota } = formatearIndicador(datos, codigo, id)
  return (
    <span className="valor-indicador">
      <strong>{texto}</strong>
      {nota && <span className="nota-indicador">{nota}</span>}
    </span>
  )
}

function PantallaSinMunicipios({ icono, titulo, descripcion, accion, onBuscar }: {
  icono: 'ficha' | 'comparar'
  titulo: string
  descripcion: string
  accion: string
  onBuscar: () => void
}) {
  return (
    <section className="estado-vacio" aria-labelledby="titulo-estado-vacio">
      <span className="icono-estado-vacio"><Icono nombre={icono} /></span>
      <h2 id="titulo-estado-vacio">{titulo}</h2>
      <p>{descripcion}</p>
      <button className="boton-principal" type="button" onClick={onBuscar}>
        <Icono nombre="buscar" />
        {accion}
      </button>
    </section>
  )
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
  const [actividad, setActividad] = useState('')
  const actividadesApi = useApiSitewise<ActividadesApi>('/actividades')
  const fichaApi = useFichaMunicipal(seccion !== 'Comparar' ? municipio?.cod_ine : undefined)
  const seleccionComparada = seccion === 'Comparar' ? comparados : []
  const primeraFicha = useFichaMunicipal(seleccionComparada[0]?.cod_ine)
  const segundaFicha = useFichaMunicipal(seleccionComparada[1]?.cod_ine)
  const terceraFicha = useFichaMunicipal(seleccionComparada[2]?.cod_ine)
  const evaluacionApi = useApiSitewise<EvaluacionApi>(
    seccion === 'Detalle' && municipio && actividad
      ? `/municipios/${municipio.cod_ine}/evaluacion/${encodeURIComponent(actividad)}`
      : null,
  )
  const comparacionApi = useApiSitewise<ComparacionApi>(
    seccion === 'Comparar' && comparados.length >= 2 && actividad
      ? '/comparar?' + new URLSearchParams({
        municipios: comparados.map((item) => item.cod_ine).join(','),
        actividad,
      })
      : null,
  )
  const capaMapa = capasMapa.find((capa) => capa.id === capaId) ?? capasMapa[0]
  const mapaActividadApi = useApiSitewise<MapaActividadApi>(
    seccion === 'Explorar' && capaMapa.dimension && actividad
      ? `/actividades/${encodeURIComponent(actividad)}/mapa` : null,
  )
  const filasMapa = mapaActividadApi.datos?.filas
  const puntuacionesMapa = useMemo(() => new Map(filasMapa?.map((fila) => [fila.cod_ine, fila])), [filasMapa])
  const { datos: tablaIndicadores, error: errorIndicadores } = useIndicadores(
    Boolean(municipio || comparados.length || capaMapa.cortes),
  )
  const datosFicha = fichaApi.datos ? adaptarFicha(fichaApi.datos) :
    fichaApi.estado === 'error' ? tablaIndicadores : null
  const fichasComparadas = [primeraFicha, segundaFicha, terceraFicha].slice(0, seleccionComparada.length)
  const datosComparados: DatosIndicadores = { indicadores: { ...tablaIndicadores?.indicadores }, municipios: {} }
  const respaldoComparado = fichasComparadas.some((ficha) => ficha.estado === 'error')
  const comparacionHomogenea = fichasComparadas.every((ficha) => ficha.estado === 'listo') ||
    fichasComparadas.every((ficha) => ficha.estado === 'error')
  fichasComparadas.forEach((ficha, indice) => {
    const codigo = seleccionComparada[indice].cod_ine
    const datos = ficha.datos ? adaptarFicha(ficha.datos) : ficha.estado === 'error' ? tablaIndicadores : null
    if (!datos) return
    Object.assign(datosComparados.indicadores, datos.indicadores)
    datosComparados.municipios[codigo] = datos.municipios[codigo] ?? {}
  })
  const notaMunicipioMapa = notaDeMapa(
    municipio ? puntuacionesMapa.get(municipio.cod_ine) : undefined, capaMapa.dimension,
  )
  const resumen = useRef<HTMLElementTagNameMap['article']>(null)
  const contenido = useRef<HTMLElementTagNameMap['section']>(null)
  const campoBusqueda = useRef<HTMLInputElement>(null)

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

  function abrirBuscador() {
    cambiarSeccion('Explorar')
    requestAnimationFrame(() => campoBusqueda.current?.focus())
  }

  function seleccionar(item: Municipio) {
    setMunicipio(item)
    setSeccion('Detalle')
    contenido.current?.focus()
  }

  function selectorActividad(id: string) {
    return (
      <ConfiguracionInversion id={id} actividades={actividadesApi.datos?.actividades ?? []}
        actividad={actividad} onCambiar={setActividad} estado={actividadesApi.estado}
        aviso={actividadesApi.datos?.aviso} />
    )
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
            {selectorActividad('actividad-explorar')}
          </details>

          {seccion === 'Explorar' && (
            <div className="explorar-contenido">
              <search className="buscador">
                <label htmlFor="municipio">Buscar municipio o provincia</label>
                <div className="campo-busqueda">
                  <Icono nombre="buscar" />
                  <input id="municipio" name="municipio" type="search" value={busqueda} ref={campoBusqueda}
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
                  {capaMapa.dimension && selectorActividad('actividad-mapa')}
                  {capaMapa.tramos && (
                    <div className="leyenda-mapa" aria-live="polite">
                      {(capaMapa.dimension ? mapaActividadApi.datos : tablaIndicadores) ? (
                        <ul aria-label={'Leyenda: ' + capaMapa.nombre}>
                          {capaMapa.tramos.map((tramo, indice) => (
                            <li key={tramo}><span aria-hidden="true" style={{ backgroundColor: `var(${tonosMapa[indice]})` }} />{tramo}</li>
                          ))}
                          <li><span aria-hidden="true" />{capaMapa.dimension ? 'Sin nota' : 'Sin dato'}</li>
                          {capaMapa.dimension && <li><span className="borde-nota-parcial" aria-hidden="true" />Nota parcial</li>}
                        </ul>
                      ) : (
                        <p>{capaMapa.dimension && !actividad ? 'Selecciona una actividad para ver las notas.' :
                          (capaMapa.dimension ? mapaActividadApi.estado === 'error' : errorIndicadores)
                            ? 'No se pudo cargar esta capa.' : 'Cargando datos de la capa…'}</p>
                      )}
                      {capaMapa.dimension && mapaActividadApi.datos && (
                        <p>Escala relativa de 0 a 100.
                          {mapaActividadApi.datos.reglas_provisionales && ' Evaluación orientativa · Reglas provisionales.'}
                        </p>
                      )}
                      {capaMapa.dimension && mapaActividadApi.datos && <p>{mapaActividadApi.datos.aviso_alcance}</p>}
                    </div>
                  )}
                </div>
                <MapaMunicipios datos={datos} error={error} codigoSeleccionado={municipio?.cod_ine}
                  capa={capaMapa} indicadores={tablaIndicadores} puntuaciones={puntuacionesMapa}
                  onSeleccionar={previsualizar} />
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
                  {datosFicha ? (
                    <dl className="indicadores-resumen">
                      {indicadoresResumen.map(([id, nombre]) => (
                        <div key={id}><dt>{nombre}</dt><dd><ValorIndicador datos={datosFicha} codigo={municipio.cod_ine} id={id} /></dd></div>
                      ))}
                      {capaMapa.cortes && !capaMapa.dimension && !indicadoresResumen.some(([id]) => id === capaId) && (
                        <div><dt>{capaMapa.nombre}</dt><dd><ValorIndicador datos={datosFicha} codigo={municipio.cod_ine} id={capaId} /></dd></div>
                      )}
                      {capaMapa.dimension && mapaActividadApi.datos && (
                        <div>
                          <dt>{capaMapa.nombre}</dt>
                          <dd>{notaMunicipioMapa ? `${notaMunicipioMapa.valor.toLocaleString('es-ES')} / 100` : 'Sin nota'}
                            {notaMunicipioMapa?.parcial && (
                              <span className="nota-indicador">Nota parcial · Cobertura: {notaMunicipioMapa.confianza.toLocaleString('es-ES', {
                                style: 'percent', maximumFractionDigits: 0,
                              })}</span>
                            )}
                          </dd>
                        </div>
                      )}
                    </dl>
                  ) : (
                    <p role="status">{fichaApi.estado === 'error' && errorIndicadores ?
                      'No se pudieron cargar los indicadores.' : 'Cargando indicadores…'}</p>
                  )}
                  {fichaApi.estado === 'error' && datosFicha && <p className="nota-pequena">Indicadores de la copia local.</p>}
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
                <div className="cabecera-informe">
                  <div className="identidad-municipio">
                    <span className="marca-municipio"><Icono nombre="pin" /></span>
                    <div>
                      <h2>{municipio.nombre}</h2>
                      <p>Provincia de {municipio.provincia}</p>
                    </div>
                  </div>
                  <div className="acciones-ficha">
                    <button type="button" onClick={() => cambiarSeccion('Explorar')}>Volver a Explorar</button>
                    {comparados.length > 0 && (
                      <button type="button" onClick={() => cambiarSeccion('Comparar')}>
                        Ver comparación ({comparados.length}/3)
                      </button>
                    )}
                    <button className="boton-principal" type="button"
                      aria-disabled={estaGuardado(municipio) || comparados.length >= 3}
                      aria-describedby="limite-comparacion" onClick={() => agregar(municipio)}>
                      <Icono nombre="comparar" />
                      {estaGuardado(municipio) ? 'Ya está en la comparación' : 'Añadir a comparar'}
                    </button>
                  </div>
                </div>
                <p id="limite-comparacion" className={comparados.length >= 3 && !estaGuardado(municipio) ? 'nota-pequena' : 'solo-lectura'}>
                  Puedes guardar hasta tres municipios. Para cambiar uno, quítalo en Comparar.
                </p>
                {fichaApi.estado === 'cargando' && <p role="status">Cargando ficha municipal…</p>}
                {fichaApi.estado === 'error' && (
                  datosFicha
                    ? <p role="status" className="nota-pequena">API no disponible. Se muestran los datos municipales de la copia local.</p>
                    : errorIndicadores
                      ? <p role="alert">No se pudieron cargar los indicadores municipales.</p>
                      : <p role="status">Cargando la copia local de los indicadores…</p>
                )}
                {datosFicha && (
                  <dl className="cifras-municipio">
                    {indicadoresResumen.map(([id, nombre]) => (
                      <div key={id}>
                        <dt>{nombre}</dt>
                        <dd><ValorIndicador datos={datosFicha} codigo={municipio.cod_ine} id={id} /></dd>
                      </div>
                    ))}
                  </dl>
                )}
                <section className="panel-actividad" aria-labelledby="titulo-evaluacion">
                  <h3 id="titulo-evaluacion">Evaluación por actividad</h3>
                  {selectorActividad('actividad-detalle')}
                  {evaluacionApi.estado === 'cargando' && <p role="status">Calculando evaluación…</p>}
                  {evaluacionApi.estado === 'error' && <p role="alert">No se pudo obtener la evaluación de este municipio.</p>}
                  {evaluacionApi.datos && (
                    <>
                      {evaluacionApi.datos.evaluacion.reglas_provisionales && (
                        <p className="aviso-reglas">Evaluación orientativa · Reglas provisionales</p>
                      )}
                      <EvaluacionMunicipal evaluacion={evaluacionApi.datos.evaluacion} datos={datosFicha} />
                      <p className="nota-actividad">{evaluacionApi.datos.aviso_alcance}</p>
                    </>
                  )}
                </section>
                {datosFicha && (
                  <>
                    <div className="panel-indicadores">
                      <table className="tabla-indicadores" role="table" aria-label="Indicadores municipales">
                        <thead role="rowgroup">
                          <tr role="row">
                            <th scope="col" role="columnheader">Indicador</th>
                            <th scope="col" role="columnheader">Valor</th>
                            <th scope="col" role="columnheader">Fuente y periodo</th>
                          </tr>
                        </thead>
                        {gruposIndicadores.map((grupo) => (
                          <tbody key={grupo.nombre} role="rowgroup">
                            <tr className="grupo-indicadores" role="row">
                              <th scope="rowgroup" role="rowheader" colSpan={3}>{grupo.nombre}</th>
                            </tr>
                              {grupo.indicadores.map((id) => {
                                const fuente = datosFicha.indicadores[id]
                                const dato = datosFicha.municipios[municipio.cod_ine]?.[id]
                                if (!fuente) return null
                                const url = dato?.url ?? fuente.url
                                const fecha = dato?.fecha_dato ?? fuente.fecha_dato
                                return (
                                  <tr key={id} role="row">
                                    <th scope="row" role="rowheader">{fuente.nombre}</th>
                                    <td role="cell"><ValorIndicador datos={datosFicha} codigo={municipio.cod_ine} id={id} /></td>
                                    <td className="fuente-indicador" role="cell">
                                      {/^https?:\/\//i.test(url) && !url.includes('{') ? <a href={url}>{fuente.fuente}</a> : fuente.fuente}
                                      {fecha && <> · {fecha.replace('consulta_', 'Consulta ')}</>}
                                      {dato?.metodo && <span className="metodo-indicador">{dato.metodo}</span>}
                                    </td>
                                  </tr>
                                )
                              })}
                          </tbody>
                        ))}
                      </table>
                    </div>
                    <p className="nota-pequena">Las distancias se miden en línea recta. El suelo cartografiado indica superficie industrial registrada en el catálogo.</p>
                  </>
                )}
              </article>
            ) : (
              <PantallaSinMunicipios icono="ficha" titulo="Consulta una ficha municipal"
                descripcion="Selecciona un municipio para ver sus indicadores, las fuentes y el periodo de cada dato."
                accion="Buscar municipio" onBuscar={abrirBuscador} />
            )
          )}

          {seccion === 'Comparar' && (comparados.length === 0 ? (
            <PantallaSinMunicipios icono="comparar" titulo="Compara municipios"
              descripcion="Añade hasta tres municipios desde Explorar o desde su ficha para ver sus indicadores lado a lado."
              accion="Buscar primer municipio" onBuscar={abrirBuscador} />
          ) : (
            <section className="informe-comparacion" aria-labelledby="titulo-comparar">
              <div className="cabecera-informe">
                <div>
                  <h2 id="titulo-comparar">Comparar municipios</h2>
                  <p>{comparados.length} de 3 municipios seleccionados</p>
                </div>
                {comparados.length < 3 && (
                  <button type="button" className="boton-principal" onClick={() => cambiarSeccion('Explorar')}>
                    Añadir otro municipio
                  </button>
                )}
              </div>

              {respaldoComparado && (
                <p role="status" className="nota-pequena">
                  {tablaIndicadores ? 'Se usa la copia local para los municipios cuya ficha no pudo cargarse desde la API.' :
                    errorIndicadores ? 'No se pudieron obtener los indicadores de algunos municipios.' : 'Cargando la copia local de los indicadores…'}
                </p>
              )}
              <ul className="municipios-comparados" aria-label="Municipios seleccionados">
                {comparados.map((item) => (
                  <li key={item.cod_ine}>
                    <div><strong>{item.nombre}</strong><span>{item.provincia}</span></div>
                    <div className="acciones-municipio">
                      <button type="button" onClick={() => seleccionar(item)} aria-label={'Ver ficha de ' + item.nombre}>Ver ficha</button>
                      <button type="button" onClick={() => quitar(item)} aria-label={'Quitar ' + item.nombre + ' de la comparación'}>Quitar</button>
                    </div>
                  </li>
                ))}
              </ul>
              <section className="panel-actividad" aria-labelledby="titulo-evaluacion-comparar">
                <h3 id="titulo-evaluacion-comparar">Evaluación por actividad</h3>
                {selectorActividad('actividad-comparar')}
                {comparados.length === 1 && <p className="nota-actividad">Añade otro municipio para comparar las evaluaciones.</p>}
                {comparacionApi.estado === 'cargando' && <p role="status">Calculando comparación…</p>}
                {comparacionApi.estado === 'error' && <p role="alert">No se pudo obtener la comparación por actividad.</p>}
                {comparacionApi.datos && (
                  <>
                    {comparacionApi.datos.reglas_provisionales && (
                      <p className="aviso-reglas">Evaluación orientativa · Reglas provisionales</p>
                    )}
                    <div className="evaluaciones-comparadas">
                      {comparacionApi.datos.evaluaciones.map(({ municipio: item, evaluacion }) => (
                        <section key={item.cod_ine}>
                          <h4>{item.nombre}</h4>
                          <EvaluacionMunicipal evaluacion={evaluacion} datos={datosComparados} />
                        </section>
                      ))}
                    </div>
                    <p className="nota-actividad">{comparacionApi.datos.aviso_comparacion} {comparacionApi.datos.aviso_alcance}</p>
                  </>
                )}
              </section>
              {comparados.length > 1 && (
                <p className="nota-pequena aviso-tabla-movil" id="ayuda-tabla-comparacion">Desplaza la tabla para ver todos los municipios.</p>
              )}
              <div className="tabla-comparacion" role="region" aria-labelledby="titulo-tabla"
                aria-describedby={comparados.length > 1 ? 'ayuda-tabla-comparacion' : undefined} tabIndex={0}>
                <table>
                  <caption id="titulo-tabla" className="solo-lectura">Comparación de indicadores municipales</caption>
                  <thead>
                    <tr>
                      <th scope="col">Indicador</th>
                      {comparados.map((item, indice) => (
                        <th scope="col" key={item.cod_ine}>
                          {item.nombre}
                          {fichasComparadas[indice].estado === 'error' && tablaIndicadores?.municipios[item.cod_ine] && (
                            <span className="origen-indicador nota-indicador">Copia local</span>
                          )}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  {gruposIndicadores.map((grupo) => (
                    <tbody key={grupo.nombre}>
                      <tr className="grupo-comparacion"><th scope="rowgroup" colSpan={comparados.length + 1}>{grupo.nombre}</th></tr>
                      {grupo.indicadores.map((id) => {
                        const indicador = datosComparados.indicadores[id]
                        if (!indicador) return null
                        const diferencia = diferencias[id]
                        const valores = comparados.map((item) => datosComparados.municipios[item.cod_ine]?.[id])
                        const orden = diferencia && comparacionHomogenea ? valores.map((dato) =>
                          dato?.estado === 'real' ? dato.valor * diferencia.sentido : NaN,
                        ) : []
                        const mejor = orden.length > 1 ? Math.max(...orden) : NaN
                        const unico = orden.filter((valor) => valor === mejor).length === 1
                        return (
                          <tr key={id}>
                            <th scope="row">{indicador.nombre}</th>
                            {comparados.map((item, indice) => (
                              <td key={item.cod_ine}>
                                {fichasComparadas[indice].estado === 'cargando' ? 'Cargando…' :
                                  <ValorIndicador datos={datosComparados} codigo={item.cod_ine} id={id} />}
                                {unico && orden[indice] === mejor && <strong className="diferencia-comparacion">{diferencia.texto}</strong>}
                              </td>
                            ))}
                          </tr>
                        )
                      })}
                    </tbody>
                  ))}
                </table>
              </div>
              <p className="nota-pequena">La selección se conserva mientras navegas y se borra al recargar la página.</p>
            </section>
          ))}
        </section>
      </main>
    </>
  )
}

export default App
