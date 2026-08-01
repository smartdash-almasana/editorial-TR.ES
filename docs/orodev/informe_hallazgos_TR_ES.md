# 🏆 Informe de Hallazgos: Ecosistema Git Literario (2025-2026)
## Estrategia de Empoderamiento para Editorial TR.ES

---

## 1. El Panorama: Repositorios Clave Descubiertos
El mapeo de la actividad en Git (2025-2026) revela que la literatura computacional ha madurado. Ya no se trata solo de "generar texto", sino de estructurar mundos, evaluar calidad narrativa y corregir estilo.

### A. Evaluación y Benchmarks (El Control de Calidad)
*   **`lechmazur/writing`**: Benchmark que evalúa 10 elementos narrativos obligatorios (tono, motivación, arcos) en textos generados por LLM.
*   **`LimHyungTae/awesome-claudecode-paper-proofreading`**: flujos de corrección que preservan la "filosofía" o voz original del autor.

### B. IDEs y Pipelines de Escritura (La Fábrica)
*   **`raestrada/storycraftr`**: CLI open-source para worldbuilding, esquemas y generación de capítulos. Soporta español nativo.
*   **`Novel-OS`**: Sistema de flujo estructurado que da contexto profundo a la IA para mantener la coherencia en ficción larga.

### C. Corrección y Estilo (El Pulido)
*   **`languagetool-org/languagetool`**: El estándar de oro para corrección gramatical multilingüe (híbrido: reglas + ML).
*   **`theJayTea/WritingTools`** & **`automattic/harper`**: Correctores ligeros que sugieren mejoras estilísticas sin reescribir la voz del autor.

### D. nichos Específicos (La Vanguardia)
*   **`andreamorgar/poesIA`**: Corpus de poesía española con tareas NLP para análisis estilométrico.
*   **`nayracoop/literatura-digital`**: Motor para narrativas hipertextuales no lineales (sin LLM).

---

## 2. Informe de ORO: Piezas Estratégicas para TR.ES
De la minería de estos repositorios, extraemos tres "Piezas de Oro" que pueden alterar la cadena de valor de la editorial.

### 💎 Pieza 1: El Pipeline Editorial Autónomo (`storycraftr`)
*   **El Hallazgo:** Convertir una premisa en un manuscrito estructurado vía CLI.
*   **Valor TR.ES:** Crear un "sello editorial asistido" donde los autores trabajen sobre una base tecnológica propietaria de la editorial, reduciendo la fase de *development* de meses a semanas.

### 💎 Pieza 2: El Panel de Catadores Algorítmico (`lechmazur/writing`)
*   **El Hallazgo:** Un checklist narrativo cuantificable.
*   **Valor TR.ES:** Implementar un *quality gate* interno. Ningún manuscrito pasa a maquetación sin superar la prueba de los 10 elementos narrativos, eliminando la subjetividad en la primera lectura.

### 💎 Pieza 3: El ADN Estilístico (`poesIA` + LLM)
*   **El Hallazgo:** Mapeo de firmas estilísticas históricas.
*   **Valor TR.ES:** Herramienta de pitching: "Si tu manuscrito tuviera el ADN de X autor de nuestro catálogo, ¿cuál sería?".

---

## 3. Aplicaciones Disruptivas (Ingeniería Inversa Editorial)

1.  **El "Lector Ciego" Digital:** Cruzar manuscritos entrantes por el benchmark de `lechmazur/writing` sin metadatos del autor. ¿El texto se sostiene por sí mismo?
2.  **La Biblioteca de Tropos Vivos:** Extraer taxonomías de `Awesome-Story-Generation` para detectar qué arcos narrativos están saturados en el mercado y cuáles son nichos sin explotar para TR.ES.
3.  **El Escritor Fantasma Institucional:** Un fork interno entrenado con el catálogo histórico de TR.ES para generar *spin-offs* o mantener vivas sagas clásicas.

---

## 4. Roadmap de Implementación

*   **Fase 1 (0-3 meses) - Infraestructura:** Fork privado de `storycraftr` como *Editorial OS*. Despliegue de API de `LanguageTool` en el equipo de corrección.
*   **Fase 2 (3-6 meses) - Diferenciación:** Lanzamiento del sello "TR.ES Experimental" usando `literatura-digital` para hipertexto.
*   **Fase 3 (6-12 meses) - Ecosistema:** Liberar un plugin público de TR.ES para Obsidian que integre estas herramientas, atrayendo a la comunidad de escritores hacia nuestro embudo.

---

## 5. Contraste con la Arquitectura Real de Editorial TR.ES

Al leer los documentos canónicos del repositorio (`EDITORIAL_TRES_PRODUCT_DEFINITION.md`, `EDITORIAL_TRES_CREATIVE_KERNEL.md`, `EDITORIAL_TRES_PLUGIN_MODEL.md`), descubrimos que **TR.ES ya tiene respuestas arquitectónicas** a las preocupaciones que plantean estas herramientas externas.

### 5.1 Lo que TR.ES ya construyó (y supera a las herramientas externas)

| Capacidad | Herramienta externa | TR.ES ya tiene |
|---|---|---|
| **Revisión literaria** | `lechmazur/writing` (10 elementos) | `ReviewEngine` + reviewers especializados (continuity, rhythm, structural, repetition, voice_drift) con `ReviewFinding` inmutables |
| **Corrección de estilo** | `LanguageTool` | `VoiceDriftReviewer` con drift markers configurables por obra/autor |
| **Estructuración** | `storycraftr` (CLI) | `WorkGraph` (Knowledge + Narrative + Expression + Dependency) con event sourcing |
| **Trazabilidad** | Ninguna herramienta externa la tiene | `Patch` → `ApprovalGate` → `EditorialCommit` con invalidación incremental |
| **Separación crítica/transformación** | Confusa en herramientas LLM | Explícita: "Reviewer → ReviewFinding, Pass → Patch" — nunca "Reviewer → reescritura silenciosa" |
| **Memorias separadas** | Inexistente | Editorial / Autor / Obra / Pasada con fronteras claras |

### 5.2 Lo que TR.ES todavía no tiene (y podría importar del ecosistema)

1.  **Benchmarks narrativos estandarizados** — `lechmazur/writing` ofrece un checklist de 10 elementos que podría convertirse en un *reviewer* más dentro del `ReviewEngine`.
2.  **Corpus poético en español** — `poesIA` podría alimentar el `AuthorMemory` de un plugin de voz autoral para poesía.
3.  **Hipertexto interactivo** — `literatura-digital` podría inspirar un plugin de género para narrativa no lineal que hoy no existe en TR.ES.
4.  **Pipeline de worldbuilding** — `storycraftr` tiene flujos CLI que podrían integrarse como *pasadas* de constitución de obra antes de entrar al `WorkGraph`.

### 5.3 Integración natural: los hallazgos externos como *plugins* de TR.ES

La arquitectura de plugins de TR.ES ya está diseñada para absorber estas herramientas sin romper el kernel:

```
plugins/
├── reviewers/
│   ├── continuity/           ← ya existe
│   ├── rhythm/               ← ya existe
│   ├── structural/           ← ya existe
│   └── narrative_checklist/  ← NUEVO: inspirado en lechmazur/writing
├── genres/
│   ├── novel/                ← ya existe
│   ├── essay/                ← ya existe
│   └── hypertext/            ← NUEVO: inspirado en literatura-digital
├── voices/
│   ├── default/              ← ya existe
│   └── poetry_corpora/       ← NUEVO: usando el corpus de poesIA
└── research_methods/
    ├── documentary/          ← ya existe
    └── worldbuilding_cli/    ← NUEVO: integrando flujos de storycraftr
```

---

## 6. Respuestas Socráticas: El Consejo Editorial se Responde a Sí Mismo

### Pregunta 1: ¿Estamos eliminando los sesgos humanos o reemplazándolos por los sesgos de los LLM?

**Respuesta desde la Constitución de TR.ES:**

La arquitectura ya responde a esto con tres invariantes:

1. **Supremacía constitucional:** "Las reglas definidas en `constitution/` prevalecen sobre cualquier instrucción de prompt o plugin." Esto significa que **ningún LLM puede vulnerar los principios editoriales**.
2. **Separación crítica/transformación:** Un reviewer nunca reescribe. Produce un `ReviewFinding` que es inmutable y trazable. El humano decide si aceptarlo, rechazarlo o escalar.
3. **Principio de creatividad:** "La memoria preserva identidad, continuidad y profundidad, pero no determina la siguiente expresión. El sistema debe evitar que la memoria se convierta en un mecanismo de repetición estadística."

**Conclusión:** TR.ES no reemplaza sesgos — los *hace visibles*. Un `VoiceDriftReviewer` no dice "esto está mal", dice "aquí hay 3 marcadores configurados de posible deriva de voz". El editor humano decide si es deriva real o evolución deliberada.

---

### Pregunta 2: ¿Cuál es el valor irreemplazable del editor humano frente al autor?

**Respuesta desde el flujo creativo canónico:**

El editor humano es el único que puede operar estas compuertas:

```
ReviewFinding → FindingDecision (accepted/rejected/escalated)
Patch → ApprovalGate (approved/rejected)
```

El valor irreemplazable es **la autoridad sobre la ambigüedad**. Cuando el `RhythmReviewer` detecta una secuencia de 6 oraciones uniformes, el sistema pregunta: "¿Es deliberado o mecánico?". Solo el editor humano puede responder esa pregunta con contexto literario, histórico y biográfico del autor.

El editor humano de TR.ES aporta:

- **Juicio estético** sobre hallazgos que el sistema marca pero no resuelve.
- **Responsabilidad institucional** sobre la aprobación final (`ApprovalGate`).
- **Mediación entre la voz del autor y la constitución de la editorial.**
- **Criterio sobre cuándo un `Patch` es una mejora legítima o una homogeneización.**

---

### Pregunta 3: ¿Qué herramienta encontrará mayor resistencia visceral de los autores?

**Respuesta desde el principio de creatividad:**

La herramienta más amenazante para un autor es el **`VoiceDriftReviewer`** — y es exactamente por eso que TR.ES lo diseña como *diagnóstico*, no como *corrección*.

La resistencia visceral vendrá de:

1. **"Me están vigilando el estilo"** — El autor puede sentir que un sistema que detecta "deriva de voz" lo está encasillando. La respuesta arquitectónica: `AuthorMemory` distingue entre *invariantes de voz*, *patrones frecuentes*, *recursos ocasionales*, *antipatrones*, *evolución*, *excepciones deliberadas*. No es una jaula, es un espejo.
2. **"Me están corrigiendo sin preguntarme"** — Esto TR.ES lo resuelve con el flujo: el reviewer produce un `ReviewFinding`, el editor toma una `FindingDecision`, y solo si se acepta se genera un `Patch` que requiere `ApprovalGate`. **Nada se aplica sin dos niveles de aprobación humana.**
3. **"Van a generar libros sin mí"** — La Constitución dice textualmente: "La IA amplía capacidad creativa y editorial, pero no sustituye la autoridad del autor ni del editor humano." Y el flujo lo demuestra: sin `Patch` aprobado, no hay mutación del `Work`.

---

## 7. Conclusión Ejecutiva

Editorial TR.ES no necesita *adoptar* las herramientas del ecosistema Git literario — necesita **absorber sus ideas como plugins gobernados**.

La arquitectura de TR.ES ya es más sofisticada que cualquier herramienta externa descubierta, porque:

- Tiene **Constitución con supremacía** (ninguna herramienta externa la tiene).
- Tiene **separación estricta entre diagnóstico y transformación** (la mayoría de herramientas LLM no la tiene).
- Tiene **trazabilidad completa vía event sourcing** (inexistente en el ecosistema).
- Tiene **memorias separadas** (editorial, autor, obra, pasada) cuando las herramientas externas mezclan todo.

Las herramientas externas son **fuentes de inspiración para nuevos plugins**, no reemplazos del kernel. El `ReviewEngine` de TR.ES puede ejecutar un reviewer inspirado en `lechmazur/writing` con la misma gobernanza que ejecuta el `RhythmReviewer` nativo.

**El verdadero oro no está en los repositorios externos — está en que TR.ES ya construyó el marco capaz de absorberlos sin perder identidad.**

---
*Documento generado para el Consejo Editorial de TR.ES | Ciclo 2025-2026*
*Integra: Mapeo de ecosistema Git literario + Auditoría de arquitectura interna*
