# ADR-005 — Operaciones editoriales tipadas dentro de Patch

**Estado:** Aceptado — implementación cerrada (`CLOSED_PASS`)
**Fecha:** 2026-07-31
**Última actualización:** 2026-08-01

## Contexto

`Patch` ya es una propuesta inmutable, versionada y sujeta a `ApprovalGate`. Actualmente, `PatchOperation` sólo admite `replace_content` sobre un bloque existente.

Ese contrato alcanza para corrección textual, pero no puede expresar de forma semántica y atómica operaciones editoriales habituales como insertar, eliminar o mover bloques. Simularlas mediante varios comandos o reemplazos textuales perdería intención, trazabilidad y consistencia.

## Decisión

`Patch` seguirá siendo la unidad aprobable y contendrá una secuencia no vacía de operaciones tipadas.

Primer catálogo autorizado:

```text
ReplaceContent
InsertBlock
DeleteBlock
MoveBlock
```

Cada operación será un modelo inmutable con discriminador y precondiciones propias.

### `ReplaceContent`

Debe conservar:

- `block_id`;
- contenido esperado anterior;
- contenido propuesto posterior.

### `InsertBlock`

Debe declarar:

- ID nuevo estable;
- tipo de bloque;
- contenido;
- padre o contenedor;
- posición;
- metadata validada.

### `DeleteBlock`

Debe declarar:

- ID del bloque;
- estado previo suficiente para impedir eliminación sobre una versión diferente;
- política explícita para dependientes.

### `MoveBlock`

Debe declarar:

- ID del bloque;
- contenedor y posición esperados;
- contenedor y posición propuestos.

## Atomicidad y aplicación

- un `Patch` se aprueba o rechaza como unidad;
- todas sus operaciones se validan contra el mismo snapshot fuente;
- la aplicación produce un único `EditorialCommit`;
- si una precondición falla, no se persiste ninguna operación del patch;
- la aplicación genera eventos canónicos e invalidación de derivados;
- un plugin o una pasada nunca aplica operaciones directamente.

## Frontera con edición manual e ingesta

Los comandos explícitos de autoría o ingesta pueden existir como casos de uso de aplicación auditables. Las transformaciones propuestas por reviewers, pasadas automáticas o modelos deben ingresar siempre mediante:

```text
EditorialPass → Patch → ApprovalGate → aplicación
```

## Consecuencias

### Positivas

- el historial expresa la intención editorial del cambio;
- inserciones, eliminaciones y movimientos pueden ser atómicos;
- se preservan IDs y dependencias;
- la interfaz futura podrá presentar diffs estructurales comprensibles;
- se evita multiplicar caminos especiales de mutación.

### Negativas

- `ApplyApprovedPatchHandler` deberá validar varias variantes;
- aparecen nuevos eventos de dominio;
- las operaciones mixtas requieren validación global antes de persistir.

## Decisiones postergadas

No se incorporan en el primer corte:

- `SplitBlock`;
- `MergeBlocks`;
- anotaciones inline;
- inversión automática;
- `StepMap` posicional;
- rebasing automático;
- CRDT u OT.

Estas capacidades sólo se abrirán mediante un caso productivo y un test que demuestre su necesidad.

## Criterios de aceptación

1. Un patch mixto `replace + insert` se aplica completo o no se aplica.
2. `delete` invalida o rechaza dependencias según una política explícita.
3. `move` conserva el ID del bloque y valida origen/destino.
4. Un patch stale o con before-state incorrecto no produce eventos.
5. El flujo `Pass → Patch → ApprovalGate → Commit` permanece intacto.


## Estado de implementación — 2026-08-01

La decisión está implementada en el núcleo editorial con el siguiente contrato operativo:

```text
ReplaceContentOperation
InsertBlockOperation
DeleteBlockOperation
MoveBlockOperation
```

La aplicación preserva las siguientes garantías:

- unión discriminada e inmutable dentro de `Patch`;
- compatibilidad del reemplazo textual existente;
- prevalidación de todas las operaciones antes de construir eventos;
- validación de inserciones contra el snapshot fuente;
- eliminación con estado previo completo, rechazo de hijos y política explícita `dependent_policy="reject"`;
- movimiento con origen y destino explícitos, preservación de ID y detección de ciclos;
- un único `EditorialCommit` por Patch aprobado;
- ausencia de persistencia parcial ante cualquier precondición inválida;
- eventos canónicos `content_block.added`, `content_block.edited`, `content_block.deleted` y `content_block.moved`;
- invalidación de derivados en reemplazos y movimientos;
- replay equivalente en memoria y SQLite.

La certificación integral combina las cuatro operaciones sobre IDs distintos, verifica el orden determinístico de eventos, el replay exacto y el aborto completo ante un `before-state` inválido.

## Integridad material de la aprobación

Una aprobación autoriza una versión material exacta del Patch, no solamente su identidad declarada. El contrato reforzado exige:

```text
Patch profundamente inmutable
→ representación JSON canónica y versionada
→ SHA-256
→ ApprovalGate.patch_digest
→ verificación antes de idempotencia o persistencia
```

`patch_id` continúa identificando la propuesta y `patch_digest` identifica el contenido exacto aprobado. Toda aprobación histórica sin digest requiere una nueva decisión humana. La metadata anidada se congela recursivamente en dominio y sólo se convierte a estructuras mutables en la frontera JSON/SQLite.

**Estado operativo:** `CLOSED_PASS`
**Evidencia final:** `88 passed` en focales, `268 passed` en suite completa, `268 passed` con `-W error`, round-trip SQLite cubierto, `git diff --check` limpio y workflow `Platform strict integrity` en verde.
**Commit técnico de cierre:** `dedf64f` (`fix(editorial): enforce patch approval integrity`).
