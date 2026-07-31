# Editorial TR.ES — Estado de ingeniería

## Estado

Documento operativo. Debe reflejar únicamente capacidades verificadas en el repositorio.

Fecha de corte: 2026-07-30.

## Regla de lectura

Este documento no redefine la arquitectura. Su función es separar:

- **arquitectura canónica**: lo que el sistema debe ser;
- **implementación verificada**: lo que el repo ya ejecuta;
- **pendiente**: lo que todavía no debe darse por existente.

## Capacidades verificadas

### Work y grafos especializados

Implementado:

- `Work` como agregado inmutable;
- `KnowledgeGraph` base;
- `NarrativeGraph` base;
- `ExpressionGraph`;
- `ContentBlock`;
- `DependencyGraph`;
- pertenencia por tenant/editorial/work.

La coordinación conceptual `WorkGraph` existe en arquitectura; en runtime actual la obra se materializa mediante `Work` conteniendo los grafos especializados.

### Event sourcing y versionado

Implementado:

- `DomainEvent`;
- replay de obra;
- `EditorialCommit`;
- EventStore en memoria;
- SQLiteEventStore persistente;
- reconstrucción de proyección;
- idempotencia de comandos;
- control de versión esperada;
- ramas;
- fork histórico;
- genealogía/origin event;
- aislamiento por tenant/editorial/work/rama.

### Invalidación incremental

Implementado:

- registro de dependencias;
- dependientes directos y transitivos;
- invalidación de recursos derivados;
- replay de estado stale;
- aislamiento de invalidación entre scopes.

### Flujo creativo mínimo

Implementado y probado:

```text
Work
→ EditorialPass
→ Patch
→ ApprovalGate
→ ApplyApprovedPatch
→ eventos canónicos
→ EditorialCommit / nueva versión
→ invalidación de dependencias
```

Componentes actuales:

- `domain/editorial_passes.py`;
- `domain/patches.py`;
- `domain/approvals.py`;
- `ApplyApprovedPatchCommand`;
- `ApplyApprovedPatchHandler`.

Propiedades verificadas:

- la pasada propone sin mutar `Work`;
- el `Patch` está ligado a tenant/editorial/work/rama/versión fuente;
- no se permiten operaciones no-op;
- la aprobación es inmutable;
- sólo un patch aprobado puede aplicarse;
- la aplicación exige la versión exacta que originó el patch;
- se valida el contenido base antes de reemplazarlo;
- se reutilizan eventos canónicos de edición;
- se invalidan dependientes transitivos;
- la aplicación es idempotente.

## Suite conocida

Última ejecución completa posterior al corte de aplicación de Patch:

```text
136 passed in 2.30s
```

Esto es evidencia del estado observado en este corte, no una garantía permanente. Debe actualizarse cuando cambie el código.

## Plugins

Verificado en el repo:

- manifiestos;
- registro/descubrimiento;
- resolución de dependencias;
- compatibilidad;
- orden determinista de composición;
- categorías existentes de género, voz, narrador, estilo, reviewer, visual, output y workflow en la composición.

No debe afirmarse todavía que existe un `PluginRuntime` capaz de ejecutar plenamente capacidades editoriales. La composición de manifiestos no equivale a ejecución del comportamiento del plugin.

## Capacidades canónicas todavía no demostradas como runtime completo

### ReviewFinding / ReviewEngine

Implementado en corte mínimo y probado:

```text
Work → Reviewer → ReviewFinding
```

Componentes actuales:

- `domain/reviews.py`;
- `ReviewFinding` inmutable y ligado a tenant/editorial/work/rama/versión fuente;
- contrato abstracto `Reviewer`;
- `RepeatedPhraseReviewer` determinístico como reviewer mínimo de prueba;
- `ReviewEngine` para ejecutar reviewers independientes y agregar findings en orden determinístico.

Propiedades verificadas:

- ningún reviewer modifica `Work`;
- un reviewer puede devolver cero o más findings;
- el mismo snapshot produce el mismo `finding_id`;
- findings conservan target, severidad, evidencia, descripción y recomendación;
- `ReviewEngine` rechaza `reviewer_id` duplicados;
- el engine agrega hallazgos sin crear ni aplicar patches.

Todavía pendiente:

```text
findings aceptados
→ EditorialPass transformadora
→ Patch
```

También siguen pendientes arbitraje, reviewers probabilísticos, persistencia de findings y aceptación/rechazo de findings como flujo de aplicación.

### ManuscriptState completo

Pendiente como objeto runtime integral.

El estado de obra existe distribuido entre agregado, grafos, eventos, commits, dependencias y proyección, pero no se debe afirmar que el `ManuscriptState` canónico completo ya esté materializado.

### PluginRuntime real

Pendiente.

Debe ejecutar capacidades enchufables sin permitir que violen invariantes del kernel.

### SemanticMemory

Pendiente.

Debe preservar separación entre memoria editorial, autoral, de obra y de pasada.

### Factoría visual operativa

Pendiente.

Existen arquitectura y categorías de plugins, pero todavía no está demostrado el circuito:

```text
bloque/claim
→ visual opportunity
→ visual brief
→ activo
→ composición
→ revisión
→ aprobación
→ invalidación por cambio de fuente
```

### EditionCompiler

Pendiente como compilador operativo completo.

La arquitectura exige múltiples ediciones derivadas de la misma obra, pero no debe afirmarse que el runtime actual ya compile PDF, EPUB o AppBookEdition de extremo a extremo.

### Reglas determinísticas vs JudgeRule

Pendiente de formalización runtime.

### Arbitraje de findings

Pendiente y posterior a demostrar primero `ReviewFinding` y reviewers independientes.

### Scheduler / Budget / Cost Control

Pendiente. No debe adelantarse al corazón creativo.

### Observabilidad y golden sets

Pendiente.

## Documentos anteriores y posible obsolescencia

`docs/architecture/neoliterary-kernel.md` describe un corte histórico temprano. Algunas de sus exclusiones ya no reflejan el estado actual: allí se declaraban fuera `DependencyGraph` y `Patch Engine`, capacidades que hoy sí existen.

Por lo tanto:

- conservarlo como documento histórico del Corte 1;
- no usar su sección "Qué queda fuera de este corte" como estado actual;
- usar este documento para estado de implementación.

`docs/architecture/editorial-tres-arquitectura-v2.md` conserva la evolución arquitectónica de sistemas y sigue siendo referencia conceptual complementaria.

## Próximo corte recomendado

Implementar únicamente el puente editorial entre diagnóstico y transformación:

```text
ReviewFinding aceptado
→ EditorialPass transformadora
→ Patch
```

Condiciones:

- aceptar/rechazar findings de forma explícita y trazable;
- ningún finding modifica `Work`;
- ningún finding aceptado aplica un cambio por sí mismo;
- la pasada transformadora debe consumir únicamente findings aceptados;
- el resultado sigue siendo un `Patch` sujeto a `ApprovalGate` antes de aplicarse;
- tests focales;
- suite completa;
- no abrir todavía factoría visual, scheduler, UI, API ni TRES.APP.

## Frontera de producto

- `Editorial TR.ES`: produce, revisa, versiona y compila obras.
- `TRES.APP`: consume una edición app-book y ofrece la experiencia de lectura.

No mezclar responsabilidades de lector interactivo dentro del kernel creativo.
