# ADR-005 — Operaciones editoriales tipadas dentro de Patch

**Estado:** Aceptado  
**Fecha:** 2026-07-31

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
