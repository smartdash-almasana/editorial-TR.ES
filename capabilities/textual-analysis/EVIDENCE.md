# Evidencia — Análisis textual trazable en español (Textual Analysis)

## PT-0

Estado: CLOSED_PASS

### Commit base

`a4296089d1fd9cdf60c248e5c0711a56969c4201`

### Objetivo

Construir un análisis de textos inmutable, determinista y trazable en español mediante spans (párrafos, oraciones y tokens) con coordenadas exactas ligadas a un bloque.

### Exclusiones preservadas

`AGENTS.md`, `tools/verify_active_task.py` y los cuatro laboratorios preexistentes permanecen congelados y fuera del corte.

### Verificaciones

- textual-analysis-focal: 23 passed (0.60s)
- textual-analysis-neighbor: 38 passed (0.60s)
- platform-suite-strict: 338 passed (13.42s)
- git-diff-check: PASS

### Decisión

El piloto de análisis textual trazable en español concluyó en verde con éxito absoluto. El ciclo PT-0 queda cerrado y certificado conforme a `ops/ACTIVE_TASK.yaml`.

## PC-0

Estado: CLOSED_PASS

### Commit base

`2c2598339fca423251b0ff1127f853f8d1e25dc2`

### Objetivo

Construir un contrato de hallazgos de diagnóstico editorial (`ReviewFinding`) trazable, que admita referencias cruzadas a spans de análisis de texto (`TextSpan`) para alineación literaria y corrección.

### Exclusiones preservadas

`AGENTS.md`, `tools/verify_active_task.py` y los cuatro laboratorios preexistentes permanecen congelados y fuera del corte.

### Verificaciones

- editorial-diagnostic-focal: 12 passed (0.58s)
- editorial-diagnostic-neighbor: 45 passed (0.85s)
- platform-suite-strict: 350 passed (14.05s)
- git-diff-check: PASS

### Decisión

La validación y la vinculación trazable de hallazgos editoriales diagnósticos con spans de análisis de texto en español concluyeron exitosamente en verde. El ciclo PC-0 queda cerrado y certificado conforme a `ops/ACTIVE_TASK.yaml`.

## PC-1

Estado: CLOSED_PASS

### Commit base

`e1a3abbdf40e7dfa4143a5fa99d38331a7aa79d2`

### Objetivo

Construir el primer corrector ortográfico y ortotipográfico determinístico, sin dependencias y trazable sobre spans canónicos de `PT-0`, con propuestas inmutables que no modifican la obra ni crean `Patch` automáticamente.

### Exclusiones preservadas

`AGENTS.md`, `tools/verify_active_task.py` y los cuatro laboratorios preexistentes permanecen congelados y fuera del corte.

### Verificaciones

- spanish-orthotypographic-corrector-focal: 16 passed (0.64s)
- spanish-orthotypographic-corrector-neighbor: 40 passed (0.75s)
- platform-suite-strict: 366 passed (13.77s)
- git-diff-check: PASS
- ACTIVE_TASK postflight: PASS

### Decisión

El corrector ortográfico y ortotipográfico determinístico v1 concluyó en verde. Produce hallazgos normativos trazables y ordenados sobre spans canónicos, conserva propuestas inmutables y no aplica cambios automáticamente. El ciclo PC-1 queda cerrado y certificado conforme a `ops/ACTIVE_TASK.yaml`.

## PC-2

Estado: CLOSED_PASS

### Commit base

`9d80e85c159ff4e8d8f803d359ae902150cd203f`

### Objetivo

Construir un corrector gramatical español determinístico, sin dependencias y trazable sobre spans canónicos de `PT-0`, con separación explícita entre errores verificados y problemas probables, sin modificar la obra ni aplicar correcciones automáticamente.

### Exclusiones preservadas

`AGENTS.md`, `tools/verify_active_task.py` y los cuatro laboratorios preexistentes permanecen congelados y fuera del corte.

### Verificaciones

- spanish-grammar-corrector-focal: 21 passed (0.69s)
- spanish-grammar-corrector-neighbor: 56 passed (0.85s)
- platform-suite-strict: 387 passed (16.05s)
- ACTIVE_TASK preflight y postflight: PASS

### Decisión

El corrector gramatical español determinístico v1 concluyó en verde. Detecta construcciones gramaticales explícitamente gobernadas, distingue `verified_error` de `probable_issue`, produce hallazgos trazables y ordenados sobre spans canónicos y no aplica cambios automáticamente. El ciclo PC-2 queda cerrado y certificado conforme a `ops/ACTIVE_TASK.yaml`.
