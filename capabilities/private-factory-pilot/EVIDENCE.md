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

## PF-1

Estado: CLOSED_PASS

### Objetivo

Procesar un manuscrito completo en texto plano mediante el núcleo real: ingesta estructurada, análisis y corrección congelados, decisiones editoriales explícitas, aplicación exclusiva de cambios aceptados, edición maestra y PDF.

### Manuscrito comprobado

- Título: **Una luz extraña en Buenos Aires**.
- Extensión: 9.000 palabras.
- Estructura: 9 capítulos, 18 bloques editoriales.
- SHA-256 de fuente: `2aa46a5b780d6729b86ed4429f72a0f2847659531ab5abf19231d0cb3ba9ab6a`.
- Hallazgos del perfil productivo congelado: 0.
- Cambios aplicados: 0; el sistema no inventó actividad ni alteró la voz.

### Salidas

- EditionSnapshot v1: SHA-256 `fc8af2fb3c35c38c298c2f61a8da786e94aa27c369f327616f94d6d381b2e7e0`.
- PDF A5: 68 páginas, 100.112 bytes en la ejecución final de certificación.
- Informe de factoría JSON con identidad de fuente, métricas y checksum de edición.

### Verificaciones

- focal integrado y manuscrito real: 9 passed (4.96s).
- regresión vecina: 67 passed (1.09s).
- suite completa estricta: 411 passed (21.82s).
- guard de ACTIVE_TASK incluido en la suite: PASS.
- inspección visual: portada, apertura de capítulo, cuerpo con diálogos y página final sin clipping, solapamientos ni glifos rotos.
- extracción de texto: tildes, raya de diálogo, capítulo IX y cierre recuperados correctamente.

### Autoauditoría

- Se preservaron los nueve cambios históricos congelados.
- No se añadieron reglas específicas para favorecer el manuscrito.
- Hallazgos múltiples compatibles dentro de un mismo span se componen como ediciones atómicas; conflictos reales siguen requiriendo arbitraje humano.
- La autorización de edición queda ligada a versiones global y material exactas; un snapshot stale no queda autorizado.
- El nombre de autor no se inventa cuando la fuente no lo declara.

### Decisión

PF-1 queda cerrado. Editorial TR.ES ya demuestra sobre una obra completa el recorrido hasta edición maestra y PDF; EPUB/Kindle y App Book Reader continúan fuera de este corte.
