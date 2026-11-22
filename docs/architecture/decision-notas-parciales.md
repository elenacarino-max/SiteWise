# Decisión: notas con datos parciales

Fecha: 21 de noviembre de 2026. Responsable: Adriana (Backend API y cálculo).
Estado: **propuesta provisional**, pendiente de que el equipo la ratifique.

## Contexto

Para cada municipio y actividad calculo dos notas separadas, riesgo y atractivo, como una media
ponderada de percentiles (`src/sitewise/scoring/motor.py`). A veces falta el dato de algún
indicador: el estado es `pendiente`, `ocultado_menor5`, `sin_masa_catalogada`, etc.

Mi primera versión no calculaba la nota si faltaba más de la mitad del peso de los indicadores
(umbral del 50 %). Ese 50 % lo puse yo sin ninguna base, y ocultaba municipios que sí tenían
información útil.

## Decisión

1. **Calculo la nota con los datos disponibles**, siempre que haya al menos uno utilizable.
2. **Muestro siempre la `confianza`**: el peso de los indicadores con dato dividido por el peso
   total (de 0 a 1).
3. **Estados de una nota:**

   | Estado | Cuándo |
   |---|---|
   | `calculada` | Hay dato de todos los indicadores con peso (confianza = 1). |
   | `calculada_parcial` | Falta alguno. El campo `motivo` lo indica ("nota provisional: solo hay dato para el 33 % del peso"). |
   | `no_evaluable` | No hay ningún dato utilizable. |
   | `sin_reglas` | La actividad no tiene reglas completas (peso y sentido) para esa dimensión. |

4. El umbral `min_confianza` sigue existiendo, pero vale **0 por defecto**. Si el equipo decide
   exigir un mínimo (por ejemplo, 0,5), basta con cambiar ese parámetro.

## Lo que NO cambia

- **Los requisitos mínimos siguen otra regla:** si falta el dato de un mínimo, el resultado es
  `no_evaluable`, nunca `cumple`. El contrato del dataset y el plan del equipo lo exigen, y es
  distinto de una nota, que es una valoración orientativa.
- Un dato ausente nunca se convierte en 0.
- Un dato aproximado o provincial entra en la nota, pero se marca (`aproximado`). Para certificar un
  mínimo se aplica otra regla: ver `decision-minimos-y-datos-aproximados.md`.

## Por qué

- Ocultar la nota hace desaparecer el municipio del mapa y del ranking, y se pierde información.
- El plan solo exige `no_evaluable` para los mínimos, no para las notas.
- Una nota parcial no engaña mientras se muestre su confianza y quede marcada como provisional.

## Riesgo y cómo lo controlo

Una nota basada en un solo indicador puede parecer tan sólida como una completa.
Para evitarlo, la API devuelve siempre `estado`, `confianza` y `motivo`, y la interfaz y el
agente deben enseñarlos ("nota provisional") y no presentar la cifra sola.

## Pendiente de decidir con el equipo

- ¿Se mantiene `min_confianza = 0` o se fija un mínimo?
- ¿Cómo debe mostrar Gema las notas parciales en el mapa y el comparador?
- ¿El agente (Josema) debe avisar siempre que una nota sea parcial? Mi propuesta es que sí.

## Dónde está en el código

- Cálculo: `MotorPuntuacion._calcular_nota` en `src/sitewise/scoring/motor.py`.
- Pruebas: `tests/scoring/test_motor.py` (`test_falta_un_dato_calcula_nota_parcial`,
  `test_sin_ningun_dato_es_no_evaluable`, `test_min_confianza_configurable`).
