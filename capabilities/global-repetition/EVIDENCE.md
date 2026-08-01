# Evidencia — Detección global de reiteraciones

## GR-0

Estado: CLOSED_PASS

### Commit base

`68e12c85f9c77a38fc4b8536a97129113c35c281`

### Commit de cierre

`79f945dd19f70be490209e93fbf64bf01f3556cf`

### Entrega

Contrato DCD, schemas, declaración de capacidad, ciclo GR-0, tarea activa, guardia mecánica y pruebas focales.

### Verificaciones

- active-task-guard-focal: 12 passed
- platform-suite: 291 passed
- platform-suite-strict: 291 passed
- git-diff-check: PASS
- HEAD y origin/main: `79f945dd19f70be490209e93fbf64bf01f3556cf`

### Decisión

GR-0 queda cerrado como arnés declarativo. La implementación experimental no formó parte de su commit.

## GR-1

Estado: CLOSED_PASS

### Objetivo

Integrar de forma gobernada el reviewer LLM de reiteraciones globales, su adaptador Gemini, plugin, controles multibloque y pruebas directas.

### Exclusiones preservadas

`AGENTS.md`, `tools/verify_active_task.py` y los cuatro laboratorios preexistentes permanecen congelados y fuera del corte.

### Verificaciones

- global-repetition-focal: 68 passed (1.12s)
- platform-suite-strict: 291 passed (13.78s)
- git-diff-check: PASS
- HEAD: 79f945dd19f70be490209e93fbf64bf01f3556cf

### Decisión

La validación y la integración del reviewer LLM global de reiteraciones y su adaptador Gemini concluyeron exitosamente en verde. El ciclo queda cerrado y certificado conforme a `ops/ACTIVE_TASK.yaml`.
