# Editorial TR.ES — Estado de ingeniería

## Estado

Documento operativo. Debe reflejar únicamente capacidades verificadas en el repositorio.

Fecha de corte: 2026-08-01.

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

### Corrección de integridad del Patch

Implementada, validada localmente y certificada por CI publicado:

- `deep_freeze()` congela recursivamente mappings, listas y sets del dominio;
- `deep_to_jsonable()` convierte recursivamente sólo en fronteras JSON/SQLite;
- `Patch` declara `patch_schema_version` y calcula un SHA-256 canónico sobre scope, versión, operaciones ordenadas, precondiciones, bloques y metadata completa;
- `ApprovalGate.for_patch()` conserva `patch_digest`;
- `ApplyApprovedPatchCommand` y `ApplyApprovedPatchHandler` recalculan y verifican el digest antes de idempotencia o persistencia;
- aprobaciones legacy sin digest fallan de forma segura y requieren nueva aprobación;
- SQLite persiste payloads mediante la conversión recursiva central;
- existe workflow de GitHub Actions para suite normal, suite estricta con warnings como errores y control de whitespace.

El commit `cb16ff3` se conserva como base de las operaciones estructurales y `dedf64f` cierra su frontera de integridad. La certificación final registró `88 passed` en focales, `268 passed` en suite completa, `268 passed` con `-W error`, round-trip SQLite cubierto, `git diff --check` limpio y el workflow `Platform strict integrity` en verde. El estado operativo definitivo es `CLOSED_PASS`.

## Suite conocida

Última revalidación completa recibida después de implementar `ReviewPlanComposer` y `ReviewPlan`:

```text
10 passed in 3.42s  — focales de ReviewPlanComposer y ReviewPlan
87 passed in 4.23s  — regresión vecina de composición, runtime y reviewers
232 passed in 5.74s — suite completa
```

Los tres comandos finalizaron con exit code `0` y sin tracebacks. `git diff --check` no reportó errores de formato ni marcadores de conflicto en los paths del corte. Las advertencias LF→CRLF son informativas y no constituyen fallo de validación.

La revalidación cubre también `ActivatedProjectComposition`, `CapabilityFactoryRegistry`, `PluginRuntime`, `ReviewEngine` y los pilotos literarios vecinos.

## Plugins y composición ejecutable

Verificado en el repo:

- manifiestos;
- registro y descubrimiento mediante `PluginRegistry`;
- resolución estática de dependencias y compatibilidad;
- orden determinista de `ProjectComposition`;
- activación y validación tipada de behaviors mediante `PluginRuntime`;
- construcción de reviewers mediante `CapabilityFactoryRegistry`;
- registry canónico congelado y registries nuevos extensibles;
- `ActivatedProjectComposition` como fase runtime separada de `compose_project()`;
- activación de plugins en `composition_order`;
- descubrimiento explícito de reviewers requeridos por proyecto, género y workflow;
- deduplicación determinista de requirements;
- fallos tempranos ante reviewer inexistente, behavior inválido, implementación desconocida o factory incapaz de construir;
- materialización de los tres reviewers exigidos por `genre.novel`.

Frontera demostrada:

```text
ProjectManifest + PluginManifest[]
→ ProjectComposition
→ ActivatedProjectComposition
→ ReviewPlanComposer
→ ReviewPlan
→ ReviewEngine construido, no ejecutado
```

La fase de activación no recibe `Work`, no crea `ReviewPlan`, no construye `ReviewEngine` y no ejecuta reviewers. El runtime usado durante la activación es local a la operación, por lo que un fallo no deja un `PluginRuntime` externo parcialmente mutado.

La composición automática del plan y la construcción del `ReviewEngine` están demostradas. No debe afirmarse todavía que el plan se ejecute automáticamente sobre `Work` desde manifiestos ni que exista un workflow executor integral.

## Estado de capacidades canónicas de runtime

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

Puente diagnóstico → decisión → transformación implementado y probado:

```text
ReviewFinding
→ FindingDecision
→ FindingDrivenBlockEditPass
→ Patch
```

`FindingDecision` conserva el scope y la versión del finding, admite estados `accepted`, `rejected` y `escalated`, y no modifica `Work`. Sólo un finding aceptado y aún vigente puede alimentar una pasada transformadora. La pasada genera un `Patch`; no aplica el cambio ni omite `ApprovalGate`.

Persistencia de revisión implementada y probada sobre el stream canónico de la obra:

```text
ReviewEngine
→ ReviewFinding persistido
→ FindingDecision persistida
→ replay / consulta de ReviewHistory
→ FindingDrivenBlockEditPass
→ Patch
```

Componentes actuales:

- eventos `review.finding_recorded` y `review.finding_decided`;
- `RecordReviewFindingCommand` / `RecordReviewFindingHandler`;
- `DecideReviewFindingCommand` / `DecideReviewFindingHandler`;
- `ReviewHistory` como read model inmutable reconstruible por replay;
- wiring en `compose_application()` con SQLite;
- consulta `EditorialApplication.review_history(...)`;
- idempotencia de registro y decisión;
- rechazo de decisiones sobre findings inexistentes, ya decididos o stale;
- persistencia y replay verificados después de reiniciar SQLite.

Los eventos de revisión avanzan la versión del stream, pero no mutan el manuscrito. Un finding no queda stale por el mero hecho de ser persistido: la obsolescencia se determina por mutaciones reales del manuscrito posteriores a la versión fuente del diagnóstico.

Siguen pendientes arbitraje entre findings y reviewers probabilísticos.

### ManuscriptState completo

Pendiente como objeto runtime integral.

El estado de obra existe distribuido entre agregado, grafos, eventos, commits, dependencias y proyección, pero no se debe afirmar que el `ManuscriptState` canónico completo ya esté materializado.

### ReviewPlan / ReviewPlanComposer

Implementado, probado y cerrado.

Componentes agregados:

- `application/review_plan.py`;
- `ReviewRequirementOrigin`;
- `ReviewPlanEntry`;
- `ReviewPlan`;
- `ReviewPlanComposer`;
- `InvalidReviewPlanError`;
- vista pública `ReviewEngine.reviewer_ids` para verificar el orden sin exponer instancias internas.

Responsabilidades implementadas:

- reconciliación determinista de reviewers explícitos del proyecto, requeridos por género y requeridos por workflow;
- deduplicación por reviewer conservando todos sus orígenes;
- procedencia, razón de inclusión, orden, implementation ID y naturaleza trazables;
- snapshot JSON canónico del behavior declarativo, incluidos scope, severidad, políticas y parámetros;
- construcción de reviewers mediante `CapabilityFactoryRegistry`;
- construcción de `ReviewEngine` desde el plan sin wiring manual;
- rechazo de divergencias entre los requirements activados y los reconciliados;
- rechazo de planes vacíos o de reviewers requeridos ausentes de la vista activada.

La composición del plan no recibe `Work`, no ejecuta reviewers, no produce findings y no crea ni aplica patches. La capacidad quedó verificada con 10 focales, 87 pruebas vecinas, 232 pruebas completas y `git diff --check` exitoso.

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

ADR-004 queda cerrado de extremo a extremo hasta esta frontera verificada:

```text
ProjectComposition
→ ActivatedProjectComposition
→ ReviewPlanComposer
→ ReviewPlan
→ ReviewEngine construido, no ejecutado
```

El Corte 2 — Operaciones estructurales mínimas de Patch queda cerrado y certificado sobre `cb16ff3` + `dedf64f`.

### Piloto editorial privado y publicación (Corte de integración)

Se ha completado y validado el piloto editorial privado de extremo a extremo (`test_private_editorial_factory_v1.py`):
- Generación de `ReviewFinding` y registro de decisiones humanas explícitas (`accepted`/`rejected`).
- Conversión de findings aceptados a `Patch`, evaluación en `ApprovalGate` y aplicación del parche atómico en el manuscrito, conservando consistencia sin persistencia parcial.
- Proyección de la obra aprobada a `EditionSnapshot` inmutable, empaquetado a `AppBookPackage` v1 estático determinista (con checksums SHA-256) y renderizado estático a HTML legible.
- Se conserva como pendiente (fuera de este alcance) la transición persistente de `Work` a un estado `approved` rígido en base de datos.

No abrir todavía workflow executor general, providers, jueces probabilísticos, factoría visual, scheduler, UI, API ni TRES.APP.

## Frontera de producto

La arquitectura comercial vigente distingue:

- `TR.ES Studio`: producto SaaS para autores/editores/sellos, construido sobre la fábrica editorial;
- `App Book Format`: contrato versionado entre producción y consumo;
- `TRES.APP / App Book Reader`: runtime de lectura, biblioteca y experiencia del lector.

Los dominios de comercio, acceso, ventas, regalías, suscripciones y créditos son conceptualmente separados del `WorkGraph`, aunque sus experiencias puedan integrarse en Studio o Reader.

Esta definición es arquitectura de producto. No implica que Studio SaaS, App Book Format completo, marketplace, billing o Reader estén implementados en este repositorio.

No mezclar responsabilidades de lector interactivo ni lógica comercial dentro del kernel creativo.
