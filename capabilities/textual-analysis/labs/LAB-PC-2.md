# LAB-PC-2 — Evaluación ciega del corrector sobre textos completos

## Estado

**CLOSED_PASS — EVALUACIÓN COMPLETADA**

El corpus y la adjudicación quedaron congelados antes de la primera ejecución.
La evaluación, la regresión vecina y el guard finalizaron en PASS. El cierre
certifica el laboratorio y sus métricas; no declara corrección automática completa.

## Pregunta que responde

¿El corrector español actual mejora textos completos nuevos con precisión
suficiente y sin alterar voz, significado o dialecto válidos?

El laboratorio no incorpora reglas, no modifica código productivo y no aplica
correcciones automáticas.

## Base congelada

- HEAD productivo: `3adea17be6773c04e6de8ff798aaba144b9fca60`.
- Textos: 3.
- Errores normativos adjudicados: 37.
- Controles correctos o de voz: 7.
- Casos gobernados por las reglas productivas incorporadas por defecto: 29.
- Casos gobernados al reconstruir además la configuración de PC-3/PC-4: 30.
- Casos fuera de ambos perfiles: 7.
- Reutilización de textos de PC-3 o LAB-PC-1: no.

## Textos

1. **La última luz del taller** — narrativa rioplatense.
2. **La biblioteca de barrio** — ensayo comunitario.
3. **El pan compartido** — relato cristiano breve.

Son piezas originales completas creadas para este laboratorio. Contienen errores
naturales, pasajes correctos, voseo, oralidad citada y decisiones literarias que
deben preservarse.

## Dos perfiles medidos

### `builtin_default`

Ejecuta las clases productivas como quedan al instanciarlas sin configuración
externa:

- `SpanishOrthotypographicCorrector()`
- `SpanishGrammarCorrector()`

### `pc3_configured_profile`

Ejecuta las mismas clases y reconstruye exactamente la configuración versionada
que usaron PC-3 y PC-4 desde
`tests/fixtures/el_puerto_y_el_rio_gold.json`.

Esta segunda medición es necesaria porque el 90% informado en PC-5 corresponde
a ese perfil configurado. La configuración léxica, contextual y de concordancia
no aparece incorporada por defecto en una composición productiva.

## Resultados observados

| Métrica | `builtin_default` | `pc3_configured_profile` |
|---|---:|---:|
| Errores adjudicados | 37 | 37 |
| Hallazgos | 29 | 31 |
| Verdaderos positivos | 29 | 30 |
| Falsos positivos | 0 | 1 |
| Omisiones | 8 | 7 |
| Precisión | 100% | 96,77% |
| Recall | 78,38% | 81,08% |
| F1 | 87,88% | 88,24% |
| Recall del catálogo gobernado | 100% | 100% |
| Correcciones peligrosas | 0 | 1 |
| Duplicados | 0 | 0 |

El perfil por defecto detectó sus 29 casos gobernados sin falsos positivos ni
alteraciones peligrosas. El perfil reconstruido agregó un único acierto, pero
también intentó cambiar el pretérito válido `rio` por `río`, alterando un
control correcto.

Las ocho omisiones del perfil seleccionado quedaron distribuidas entre dequeísmo,
acentuación general y contextual, concordancia sujeto-verbo, ortografía léxica,
forma verbal y segmentación de palabras.

## Verificación

- Evaluación ciega: 2 pruebas aprobadas.
- Regresión vecina: 51 pruebas aprobadas.
- Guard: PASS.
- Fuente y `Work`: inmutables.
- Patch creado: no.
- Corrección automática: no.

## Restricciones

- Sin LLM ni proveedor externo.
- Sin nuevas dependencias.
- Sin modificación de `platform/src/**`.
- Sin Patch.
- Sin corrección automática.
- Sin extrapolar resultados al español general.
- Sin afirmar validación doctrinal o de género cristiano.

## Decisión

Se conserva `builtin_default` como perfil productivo prudente. La capacidad
queda validada como asistente editorial con revisión humana obligatoria, no como
corrector automático integral.

No se incorpora `pc3_configured_profile`: su mejora de recall es marginal y
produce una corrección peligrosa. No se abren reglas nuevas por cada omisión.

El siguiente laboratorio debe usar un manuscrito completo real como corpus
congelado y ejecutar el perfil productivo sin modificar reglas ni código durante
la evaluación.
