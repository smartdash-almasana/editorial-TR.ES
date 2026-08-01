# Editorial TR.ES — Roadmap de ingeniería enterprise

## Estado

Roadmap canónico de construcción posterior a la auditoría arquitectónica de julio de 2026.

Este documento ordena capacidades. No convierte una capacidad pendiente en implementada y no sustituye `EDITORIAL_TRES_ENGINEERING_STATE.md`.

## Principio de ejecución

Cada corte debe seguir:

```text
arquitectura canónica
→ código real
→ gap verificado
→ capacidad acotada
→ test focal
→ actualización de estado
```

No se abre el corte siguiente mientras el anterior no tenga contrato, implementación, prueba focal y ausencia de regresión conocida dentro de su alcance.

## Decisiones rectoras

- ADR-004: composición editorial ejecutable por fases.
- ADR-005: operaciones editoriales tipadas dentro de `Patch`.
- ADR-006: autoridad única para relaciones semánticas entre grafos.
- ADR-007: extensibilidad gobernada del vocabulario editorial.
- ADR-008: evolución segura del event stream y observabilidad separada.

## Corte 1 — Composición ejecutable de revisión

### Objetivo

Convertir la composición declarativa actual en un `ReviewPlan` ejecutable sin configuración manual.

### Alcance

1. **Implementado:** corregir los IDs inconsistentes de reviewers requeridos por `genre.novel`.
2. **Implementado:** completar o crear manifests ejecutables para los reviewers realmente soportados.
3. **Implementado y cerrado:** introducir `ActivatedProjectComposition`.
4. **Implementado:** introducir `CapabilityFactoryRegistry` para reviewers.
5. **Implementado y cerrado:** introducir `ReviewPlan` y `ReviewPlanComposer` en aplicación.
6. **Implementado y cerrado:** construir `ReviewEngine` desde el plan sin ejecutarlo.
7. **Implementado y cerrado:** registrar y agregar el origen de cada reviewer: proyecto, género o workflow.

El Corte 1 queda cerrado. La evidencia final registró `10 passed` en focales, `87 passed` en regresión vecina, `232 passed` en suite completa y `git diff --check` sin errores. Los warnings LF→CRLF son informativos y no bloqueantes.

### Criterios de cierre

- una composición imposible falla antes de revisar una obra;
- `genre.novel` construye sus reviewers obligatorios;
- no hay reviewers duplicados;
- el orden es determinista;
- el piloto de novela construye `ReviewEngine` desde el plan sin wiring manual;
- reviewers siguen sin mutar `Work`.

### Fuera de alcance

- workflow executor general;
- providers;
- jueces probabilísticos;
- aplicación automática de patches.

## Corte 2 — Operaciones estructurales mínimas de Patch

**Estado:** `CLOSED_PASS`
**Evidencia de cierre:** `62 passed` en focales, `256 passed` en suite completa y espacios finales reportados corregidos; `git diff --check` debe reconfirmarse antes del commit.

### Objetivo

Permitir curado estructural gobernado sin abandonar `Patch → ApprovalGate → Commit`.

### Alcance

1. **Implementado:** convertir `PatchOperation` en unión discriminada.
2. **Implementado:** conservar `ReplaceContent`.
3. **Implementado:** agregar `InsertBlock`.
4. **Implementado:** agregar `DeleteBlock`.
5. **Implementado:** agregar `MoveBlock`.
6. **Implementado:** validar todas las precondiciones antes de persistir.
7. **Implementado:** aplicar el patch como un único commit atómico.
8. **Implementado:** invalidar derivados afectados.

### Criterios de cierre

- operaciones mixtas son all-or-nothing;
- los IDs se preservan donde corresponde;
- `move` valida origen y destino;
- `delete` tiene política explícita para dependientes;
- un patch stale no produce eventos;
- replay reconstruye exactamente el resultado.

### Fuera de alcance

- split/merge;
- inversión automática;
- rebasing;
- colaboración en tiempo real.

## Corte 3 — Mutación gobernada de NarrativeGraph y KnowledgeGraph

### Objetivo

Permitir que estructura y conocimiento evolucionen dentro del mismo event stream que la expresión.

### Alcance

1. Eventos narrativos mínimos: add y move.
2. Eventos de conocimiento mínimos: add y update.
3. Comandos/handlers explícitos para autoría e ingesta gobernada.
4. Propuestas estructurales automáticas únicamente mediante Patch cuando corresponda.
5. Extensión de `Work.apply()` y replay.
6. Commits multigrafo atómicos.
7. Validación global del snapshot final antes del append.

### Criterios de cierre

- narrativa, conocimiento y expresión se reconstruyen por replay;
- una operación multigrafo persiste completa o no persiste;
- no hay nodos huérfanos;
- ciclos y referencias inválidas se rechazan antes del commit;
- idempotencia preservada.

## Corte 4 — Relaciones semánticas tipadas

### Objetivo

Conectar estructura, expresión y conocimiento mediante una autoridad canónica única.

### Alcance

1. Introducir `SemanticRelation` y su contenedor canónico.
2. Implementar predicados mínimos requeridos por casos reales.
3. Eventos de link/unlink.
4. Validación de origen, destino, scope y versión.
5. Proyección hacia `DependencyGraph` cuando la relación implique invalidación.
6. Consultas directas e inversas mediante proyección/indexación.
7. Integración de lectura con `SemanticMemory`.

### Criterios de cierre

- no se duplica una relación dentro de nodos;
- replay reconstruye relaciones;
- retirar una relación actualiza la invalidación derivada;
- memoria recupera por relación sin convertirse en autoridad;
- las consultas permanecen deterministas.

## Corte 5 — Extensibilidad gobernada y namespaced

### Objetivo

Permitir nuevos géneros y métodos de investigación sin strings libres ni cambios ad hoc en el kernel.

### Alcance

1. Definir vocabulario base `kernel.*`.
2. Introducir registros scoped e inmutables por composición.
3. Autorizar extensiones por categoría de plugin.
4. Versionar schemas de metadata.
5. Impedir redefinición de tipos base.
6. Migrar progresivamente tipos cerrados y strings libres.
7. Validar colisiones de namespace durante activación.

### Criterios de cierre

- un género agrega un tipo autorizado sin cambiar código del kernel;
- un reviewer no puede registrar estructura narrativa;
- una colisión de schema falla temprano;
- obras históricas conservan la versión de vocabulario que las originó.

## Corte 6 — Evolución y rendimiento medidos

### Objetivo

Preparar el event stream para evolución segura y medir cuándo necesita optimización.

### Alcance

1. Incorporar `schema_version` a eventos nuevos con compatibilidad para versión 1.
2. Definir registro mínimo de upcasters, sin implementaciones especulativas.
3. Crear benchmark reproducible de replay sobre obras crecientes.
4. Implementar snapshots sólo si el benchmark demuestra necesidad.
5. Verificar recuperación de proyecciones después de interrupción.
6. Definir correlación por `trace_id` sin almacenar telemetría pesada en el stream.

### Criterios de cierre

- replay histórico estable;
- benchmark versionado y repetible;
- cualquier snapshot es descartable;
- ninguna optimización cambia la autoridad del stream.

## Corte 7 — Juicio probabilístico gobernado

### Objetivo

Incorporar IA sin presentar juicio probabilístico como hecho ni permitir mutación silenciosa.

### Prerrequisitos

Cortes 1 a 5 cerrados. Corte 6 al menos con versionado de eventos y contrato de observabilidad.

### Alcance

1. Formalizar `DeterministicRule` y `JudgeRule`.
2. Representar incertidumbre y calibración en findings probabilísticos.
3. Definir `PassExecutionRecord` fuera del stream canónico.
4. Construir corpus gold por género/capacidad.
5. Incorporar provider adapter bajo contrato estable.
6. Ejecutar la primera capacidad probabilística como finding o Patch, nunca como mutación directa.

### Criterios de cierre

- provider reemplazable;
- modelo, prompt, contexto y costo trazables;
- golden tests detectan regresiones;
- zonas ambiguas escalan a humano;
- la aplicación exige ApprovalGate.

## Corte 8 — Workflow durable, compilación y factorías

Este corte se abre sólo después de demostrar el núcleo editorial completo.

Capacidades posibles:

- workflow executor por stages;
- reanudación de pasadas costosas;
- factoría visual;
- `EditionCompiler`;
- App Book Format;
- proyecciones PDF/EPUB/HTML;
- TR.ES Studio.

Cada capacidad deberá abrirse como corte independiente; esta sección no autoriza una implementación monolítica.

## Decisiones explícitamente postergadas

No forman parte del roadmap inmediato:

- CRDT/Yjs dentro del kernel;
- OT o edición colaborativa a nivel carácter;
- rebasing semántico automático;
- sagas o Temporal;
- microservicios;
- base de grafos externa;
- snapshots por umbral arbitrario;
- cache distribuida;
- orquestador omnipotente;
- generación LLM antes de composición y revisión gobernadas.

## Control antideriva por corte

Antes de modificar código, responder y registrar:

1. ¿Qué capacidad productiva agrega?
2. ¿Qué autoridad existente respeta?
3. ¿Cuál es el gap comprobado en código?
4. ¿Cuál es el primer archivo que cambia?
5. ¿Qué invariante podría romperse?
6. ¿Qué test focal demuestra la capacidad?
7. ¿Qué queda explícitamente fuera?

Si una respuesta no puede sostenerse con documentos canónicos, código y tests, el corte no se abre.
