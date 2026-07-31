# Editorial TR.ES — Kernel creativo canónico

## Estado

Canónico.

## Contrato central

La obra es un grafo semántico versionado. Cada operación editorial debe ser limitada, trazable y explícita. Los reviewers producen hallazgos. Las transformaciones producen `Patch`. La IA nunca sobrescribe silenciosamente el estado canónico. El autor y la editorial conservan autoridad final.

## Objetos fundamentales

### Work

Agregado raíz de una obra editorial. Mantiene identidad, versión y grafos especializados.

### WorkGraph

Concepto coordinador de la obra estructurada. No equivale a un archivo Markdown largo.

Integra y relaciona:

- `KnowledgeGraph`;
- `NarrativeGraph`;
- `ExpressionGraph`;
- `DependencyGraph`;
- bloques, claims, fuentes, símbolos, visuales, ediciones y dependencias.

### KnowledgeGraph

Representa lo que la obra afirma y en qué se apoya:

- conceptos;
- claims;
- fuentes;
- fragmentos;
- citas;
- evidencia;
- contradicciones;
- grados de certeza;
- referencias cruzadas.

### NarrativeGraph

Representa cómo se organiza la experiencia narrativa o argumental:

- partes;
- capítulos;
- escenas;
- secuencias;
- arcos;
- ritmo;
- revelaciones;
- objeciones;
- progresión;
- continuidad.

### ExpressionGraph

Representa la expresión concreta de la obra mediante bloques direccionables:

- párrafos;
- encabezados;
- diálogos;
- citas;
- poemas;
- notas;
- y futuros tipos definidos de forma compatible.

La voz autoral, el narrador y el estilo son capas distintas.

### ManuscriptState

Vista coherente de la obra en un momento editorial. Debe concentrar versión vigente, bloques, decisiones aceptadas, findings abiertos, patches pendientes, reglas aplicables, rama, dependencias, aprobaciones y elementos obsoletos.

No debe confundirse con almacenamiento o persistencia física.

### EditorialPass

Operación especializada y acotada sobre un snapshot de la obra.

Una pasada debe declarar, progresivamente según madurez:

- propósito;
- alcance;
- entradas;
- dependencias;
- reglas;
- output;
- si transforma o sólo analiza;
- herramientas/modelos requeridos;
- aprobación requerida;
- identidad/versionado de su implementación.

Las pasadas son atómicas. No existe un agente todopoderoso encargado de investigar, escribir, revisar, diseñar y publicar en una sola operación.

### Patch

Propuesta inmutable de transformación sobre una versión fuente concreta.

Un `Patch` no es el estado nuevo ni un commit completo. Es la propuesta auditable que debe poder ser aceptada o rechazada antes de afectar la obra.

### ApprovalGate

Compuerta humana explícita asociada a una propuesta y a la versión que la originó.

Una aprobación:

- debe corresponder al mismo ámbito editorial;
- no puede resolver dos veces la misma compuerta;
- no aplica por sí sola el `Patch`;
- registra actor, decisión y momento.

### Aplicación de Patch

Sólo un `Patch` aprobado puede aplicarse.

Debe verificarse:

- identidad de tenant/editorial/work/rama;
- versión fuente exacta;
- correspondencia entre aprobación y patch;
- que el contenido base siga siendo el esperado;
- idempotencia.

La aplicación genera eventos/versionado canónicos y reutiliza el mecanismo de invalidación existente.

### ReviewFinding

Hallazgo editorial estructurado producido por un reviewer.

Conceptualmente debe poder expresar:

- reviewer/tipo;
- target;
- versión;
- severidad;
- evidencia;
- explicación;
- regla;
- confianza cuando corresponda;
- recomendación;
- estado;
- posibles conflictos.

Un finding no modifica la obra.

### ReviewEngine

Ejecuta reviewers sobre el mismo estado, recopila findings y prepara la etapa de resolución. No aplica transformaciones.

La separación obligatoria es:

```text
Reviewer → ReviewFinding
EditorialPass transformadora → Patch
```

No:

```text
Reviewer → reescritura silenciosa
```

### DependencyGraph

Permite invalidación incremental. Cuando cambia un nodo, sólo deben marcarse como afectados los recursos que dependan directa o transitivamente de él.

Esto hace viable trabajar con obras largas sin regenerarlas completas.

### EditorialCommit

Agrupa eventos coherentes en una unidad versionada sobre una rama.

`Patch` y `Commit` tienen responsabilidades diferentes:

- `Patch`: propuesta;
- aprobación: decisión;
- aplicación: mutación autorizada;
- `EditorialCommit`: registro versionado de eventos ya aplicados.

## Memorias separadas

La arquitectura distingue cuatro ámbitos:

1. **Editorial**: constitución, políticas, reglas, terminología, identidad visual y criterios de aprobación.
2. **Autor**: corpus, voz aprobada, patrones, antipatrones y decisiones confirmadas.
3. **Obra**: grafos, fuentes, claims, símbolos, findings, patches, visuales, decisiones y ediciones.
4. **Pasada/sesión**: contexto mínimo requerido para una operación puntual.

No deben mezclarse. Más contexto no equivale a mejor calidad.

## Reglas determinísticas y juicios probabilísticos

Una validación estructural no tiene la misma naturaleza que un score de voz.

La evolución v2 distingue:

- `DeterministicRule`: resultado verificable y reproducible;
- `JudgeRule`: juicio probabilístico que debe incluir calibración, confianza e intervención humana en zonas ambiguas.

Nunca se debe presentar un juicio de LLM como hecho determinístico.

## Flujo creativo objetivo

```text
WorkGraph
→ Reviewer(s)
→ ReviewFinding(s)
→ aceptación / arbitraje
→ EditorialPass transformadora
→ Patch
→ ApprovalGate
→ aplicación
→ EditorialCommit / nueva versión
→ DependencyGraph invalida derivados
```

Este flujo debe demostrarse verticalmente antes de ampliar infraestructura periférica.

## Invariantes

- La IA no sobrescribe el estado canónico.
- Crítica y transformación son operaciones distintas.
- Voz autoral y narrador son conceptos diferentes.
- Los reviewers generan findings.
- Las transformaciones generan patches.
- Toda mutación autorizada es trazable y versionada.
- Los cambios locales no deben obligar a regenerar toda la obra.
- El humano conserva autoridad final en decisiones editoriales sensibles.
