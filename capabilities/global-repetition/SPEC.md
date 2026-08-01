# Detección global de reiteraciones

## Estado

Capacidad experimental en integración.

GR-0 estableció exclusivamente el contrato DCD, sus schemas, el ciclo y la guardia mecánica. GR-1 adopta como candidato experimental una implementación opcional de revisión global asistida por LLM.

## Problema editorial

Una obra extensa puede repetir expresiones, imágenes, formulaciones o ideas en bloques alejados. El editor necesita descubrir candidatos, reunir sus apariciones y evaluarlos en contexto.

Descubrir una reiteración no significa que exista un defecto. Puede tratarse de un símbolo, un motivo, un eco deliberado, una caracterización, un recurso rítmico o una coincidencia irrelevante.

## Frontera de GR-1

```text
Work versionado
→ LLMGlobalRepetitionReviewer
→ StructuredLLMPort
→ GeminiStructuredLLMAdapter
→ salida JSON validada
→ citas verificadas contra bloques reales
→ ReviewFinding multibloque
→ decisión humana
```

La integración es opcional y no determinista. No modifica `Work`, no crea `Patch` y no determina intención autoral como hecho.

## Evidencia y trazabilidad

Cada hallazgo conserva:

- tenant, editorial, obra y rama;
- versión material exacta del manuscrito;
- proveedor y modelo;
- tipo de candidato y confianza;
- dos o más bloques relacionados;
- citas literales verificadas localmente.

La respuesta completa se rechaza si contiene bloques inexistentes, citas inventadas, apariciones duplicadas o una estructura inválida.

## Autoridad humana

La clasificación editorial pertenece al autor o al editor humano. Todo hallazgo requiere decisión humana antes de cualquier intervención.

Un hallazgo multibloque no puede alimentar una edición simple de un solo bloque. Una transformación posterior requiere seleccionar explícitamente una aparición y abrir una propuesta independiente.

## Límites de GR-1

GR-1 no incorpora:

- escritura o reescritura automática;
- creación directa de `Patch`;
- decisión editorial automática;
- UI, API, scheduler o base de datos;
- embeddings ni clustering local;
- fragmentación automática de obras que excedan los límites;
- certificación de calidad editorial;
- promoción a servicio productivo obligatorio.

## Criterio de avance

El corte puede integrarse como `EXPERIMENTAL` si pasan las pruebas focales y la regresión declarada sin llamadas reales al proveedor. La calidad editorial permanece pendiente de un corpus español anotado y de mediciones de precisión, recall, estabilidad, costo y latencia.
