# Evidencia — Piloto editorial privado y publicación (Private Factory Pilot)

## PF-0

Estado: CLOSED_PASS

### Commit base

`a4296089d1fd9cdf60c248e5c0711a56969c4201`

### Objetivo

Demostrar un flujo editorial privado gobernado de extremo a extremo, desde la obra original (`Work`) hasta la publicación en `AppBookPackage` v1 y HTML estático, incluyendo decisiones humanas explícitas y aplicación atómica de parches.

### Exclusiones preservadas

`AGENTS.md`, `tools/verify_active_task.py` y los cuatro laboratorios preexistentes permanecen congelados y fuera del corte.

### Verificaciones

- private-factory-pilot-focal: 50 passed (1.56s)
- platform-suite-strict: 315 passed (14.24s)
- git-diff-check: PASS

### Decisión

El piloto editorial de extremo a extremo concluyó de forma impecable en verde, logrando la integración funcional completa sin vulnerar ninguna precondición de consistencia. El ciclo PF-0 queda cerrado y certificado conforme a `ops/ACTIVE_TASK.yaml`.
