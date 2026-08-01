# Detección global de reiteraciones

## Estado

Capacidad declarada. No existe todavía implementación editorial ni algoritmo promovido al runtime.

## Problema editorial

Una obra extensa puede repetir expresiones, imágenes, formulaciones o ideas en bloques alejados. El editor necesita descubrir esos candidatos y reunir sus apariciones para evaluarlos en contexto.

Descubrir una reiteración no significa que exista un defecto. Puede tratarse de un símbolo, un motivo, un eco deliberado, una caracterización, un recurso rítmico o una coincidencia irrelevante.

## Resultado conceptual

La capacidad futura deberá reunir evidencia multibloque vinculada al mismo manuscrito y a su versión material. Cada aparición deberá conservar su texto original y su localización verificable.

## Autoridad humana

La clasificación editorial pertenece al autor o al editor humano. El sistema no determina automáticamente intención, legitimidad estética ni necesidad de corrección.

## Límite de transformación

La detección no modifica `Work`, no aplica reemplazos y no crea un `Patch` directamente. Una eventual intervención requerirá una decisión humana y una propuesta de transformación independiente.

## Alcance inicial

El alcance inicial es exclusivamente experimental y declarativo. GR-0 establece el contrato DCD, sus schemas, el ciclo autorizado y su guardia mecánica.

## Relación futura con el kernel

Una promoción posterior, expresamente autorizada y sustentada por evidencia, podrá adoptar la frontera existente:

```text
Reviewer
→ ReviewFinding
→ decisión humana
→ propuesta de transformación
→ Patch
→ ApprovalGate
```

## Capacidades no implementadas

Este corte no implementa:

- extracción de unidades textuales;
- descubrimiento literal;
- near-duplicates;
- embeddings;
- clustering semántico;
- LLM;
- integración con proveedores;
- persistencia de evidencia multibloque;
- clasificación humana persistente;
- transformación de apariciones;
- plugin productivo;
- UI, API, scheduler o base de datos nueva.
