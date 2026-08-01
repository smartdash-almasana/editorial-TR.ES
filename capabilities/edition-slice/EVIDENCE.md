# Evidencia — Proyección y publicación de ediciones (Edition Slice)

## ES-0

Estado: CLOSED_PASS

### Commit base

`675266f5e2d06585f928a6d4d192aa74babfc76b`

### Objetivo

Proyectar obras aprobadas a EditionSnapshot, empaquetar AppBookPackage v1 estático determinista (con checksums SHA-256) y renderizar a HTML.

### Exclusiones preservadas

`AGENTS.md`, `tools/verify_active_task.py` y los cuatro laboratorios preexistentes permanecen congelados y fuera del corte.

### Verificaciones

- edition-slice-focal: 50 passed (1.31s)
- platform-suite-strict: 314 passed (13.29s)
- git-diff-check: PASS

### Decisión

La validación y la proyección de ediciones (Edition Slice) concluyeron de forma impecable en verde. El ciclo ES-0 queda cerrado y certificado conforme a `ops/ACTIVE_TASK.yaml`.
