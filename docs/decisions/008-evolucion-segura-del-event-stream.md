# ADR-008 — Evolución segura del event stream y observabilidad separada

**Estado:** Aceptado  
**Fecha:** 2026-07-31

## Contexto

El event stream es la fuente de verdad para reconstruir `Work`. Los eventos actuales no declaran una versión explícita de schema. Cada handler reconstruye el agregado desde el stream completo. La observabilidad de futuras pasadas probabilísticas —prompt, modelo, parámetros, contexto, costo y respuesta técnica— tampoco tiene residencia definida.

Agregar tipos de operaciones, eventos narrativos, relaciones semánticas y vocabularios versionados hará inevitable la evolución de schemas. Esa evolución debe prepararse sin introducir snapshots, migraciones o telemetría pesada antes de que exista evidencia operativa.

## Decisión

### Versionado de eventos

Todo evento canónico deberá declarar:

```text
schema_version: int
```

- la versión inicial es `1`;
- el tipo de evento y su schema evolucionan de manera explícita;
- el replay nunca reinterpretará silenciosamente un payload antiguo con un contrato nuevo;
- cuando exista una incompatibilidad real se incorporará un upcaster determinista y testeado.

### Upcasting

Los upcasters:

- transforman payloads históricos hacia la representación actual durante lectura;
- no reescriben el event stream original;
- se registran por `event_type` y versión;
- deben ser puros, deterministas y cubiertos por tests de replay histórico.

No se implementará un framework de upcasting hasta que exista la primera evolución incompatible, pero el campo de versión debe precederla.

### Snapshots

Los snapshots son una optimización, no autoridad.

- sólo se implementarán después de un benchmark reproducible;
- incluirán versión del agregado y versión de schema;
- un snapshot incompatible se descarta y el sistema vuelve al replay desde eventos;
- nunca reemplazan el stream ni se usan para ocultar eventos inválidos.

No se adopta un umbral arbitrario de cantidad de eventos como decisión arquitectónica.

### Proyecciones

Las proyecciones son derivadas y reconstruibles. Una caída entre persistencia del commit y actualización de una proyección no corrompe la obra. La recuperación debe ser idempotente.

### Observabilidad de pasadas

La evidencia técnica de una ejecución vive fuera del stream canónico.

El event stream podrá guardar un `trace_id` o `execution_id` correlacionable. Un almacén separado conservará, según política de retención:

- pass/reviewer ID y versión;
- modelo y versión;
- prompt o hash/versionado de prompt;
- parámetros;
- referencias de memoria/contexto;
- tiempos, reintentos y resultado técnico;
- tokens y costo;
- validaciones;
- salida cruda cuando la política lo permita.

Los hechos editoriales resultantes —finding, decisión, patch, aprobación, commit— permanecen en el dominio canónico.

## Consecuencias

### Positivas

- replay histórico estable;
- evolución explícita de contratos;
- snapshots medidos y descartables;
- event stream libre de telemetría voluminosa;
- trazabilidad completa mediante correlación.

### Negativas

- cada evento y schema necesita disciplina de versión;
- futuras migraciones requieren mantener upcasters;
- la observabilidad introduce un almacén adicional cuando existan pasadas probabilísticas.

## Decisiones postergadas

- snapshots antes de benchmark;
- cache distribuida;
- EventStoreDB dedicado;
- blue/green projections;
- Temporal o sagas;
- tracing distribuido pesado;
- rebasing automático.

## Criterios de aceptación

1. Eventos nuevos declaran `schema_version` y eventos antiguos se leen como versión 1.
2. Un replay con schema histórico produce el mismo estado esperado mediante upcast cuando corresponda.
3. Un snapshot incompatible puede descartarse sin pérdida de información.
4. La telemetría no forma parte del payload de `Work` ni del stream editorial salvo su identificador de correlación.
5. La suite demuestra que las proyecciones pueden reconstruirse después de una interrupción.
