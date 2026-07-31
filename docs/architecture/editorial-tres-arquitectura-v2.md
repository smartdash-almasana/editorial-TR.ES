# Editorial TR.ES — Arquitectura de oro v2

## 0. Punto de partida

La v1 resuelve bien el problema **creativo**: qué es una obra, cómo se preserva la voz, cómo se separan pasadas, cómo una obra produce múltiples ediciones. Eso no se toca.

Lo que falta es el problema **de sistemas**: qué pasa cuando esa obra tiene 300 páginas, 40 tipos de pasada, tres editoriales corriendo en paralelo y un editor humano que necesita meter mano. Ahí es donde un diseño elegante en el papel se rompe en producción. Este documento agrega esa capa, no reemplaza la anterior.

---

## 1. Lo que ya está bien resuelto (no tocar)

- WorkGraph como grafo estructurado en vez de un documento largo.
- Separación explícita voz-autoral / narrador.
- Pasadas atómicas y especializadas en vez de un agente todopoderoso.
- Manuscrito inmutable + propuesta de patch, en vez de sobrescritura directa.
- Edición como producto derivado del WorkGraph, no como copia independiente.
- Revisores como red de hallazgos (`ReviewFinding`), no como cadena única.
- Constitución editorial como reglas ejecutables, no como manifiesto.

---

## 2. Los ocho huecos que van a doler primero en producción

### 2.1 No hay motor de invalidación incremental

El documento dice que el objetivo es *"trabajar con libros de cientos de páginas sin volver a cargar todo el manuscrito"*, pero no hay ningún mecanismo que determine **qué volver a ejecutar** cuando algo cambia. La memoria de sesión acotada resuelve el contexto de una pasada, no la propagación de un cambio.

Si `block.chapter-03.section-02` cambia, ¿qué pasa con:
- las revisiones ya aceptadas sobre ese bloque,
- los visual briefs que lo referencian,
- las ediciones que ya lo compilaron?

Sin esto, cada corrección de tesis obliga a un rastreo manual del libro entero — exactamente lo que la arquitectura dice que quiere evitar.

**Propuesta:** un `DependencyGraph` explícito, estilo motor de build incremental (Bazel/Nx), donde cada nodo (bloque, claim, source, visual, edition) declara de qué depende, y un cambio dispara invalidación en cascada solamente sobre lo afectado.

```yaml
dependency_edge:
  from: block.chapter-03.section-02
  to:
    - claim.ego-modernity
    - source.augustine-confessions
    - visual.chapter-04.identity-fracture
  edge_type: derives_from
```

```yaml
invalidation_event:
  trigger: block.chapter-03.section-02 changed (v17 -> v18)
  cascades_to:
    - finding-239 (marked: stale)
    - visual.chapter-04.identity-fracture (marked: needs-review)
    - edition.yo-no-soy.app-book (marked: needs-recompile)
```

### 2.2 "Patch" no es lo mismo que control de versiones

El modelo actual (`manuscrito → pasada → propuesta → diff → aceptación → nueva versión`) describe *cómo cambia un bloque*, pero no *cómo se versiona la obra completa*. Faltan tres cosas que cualquier sistema de esta escala necesita: **ramas** (una edición experimental que no debe tocar la versión publicada), **tags** (v1.0 publicada, congelada) y **rollback** de la obra entera, no solo de un bloque.

**Propuesta:** modelar cada aceptación de patch como un `Commit` sobre el WorkGraph, y permitir branching real. No hace falta reinventar esto — puede apoyarse literalmente en git como motor de almacenamiento (cada bloque como archivo direccionable por contenido), con el WorkGraph como capa semántica encima.

```yaml
commit:
  id: commit-0042
  parent: commit-0041
  branch: main
  applies_patches:
    - pass-00421
  message: "revisión estructural cap. 5 aceptada"
  work_snapshot_hash: 8f2a1c...
```

### 2.3 Los evaluadores mezclan dos naturalezas distintas

La constitución define `voice_drift_score < 0.25` con la misma sintaxis que `changes_require_patch`. Pero son cosas muy diferentes: la segunda es un check determinístico (verdadero/falso), la primera es el juicio probabilístico de un modelo. Tratarlas igual genera falsa confianza — un "error" de voice-drift no es un hecho, es una estimación con margen de ruido.

**Propuesta:** separar `DeterministicRule` de `JudgeRule`. La segunda necesita calibración contra casos gold, muestreo repetido para estabilidad, y una banda de incertidumbre cerca del umbral que dispare revisión humana en lugar de aceptar/rechazar automático.

```yaml
judge_rule:
  id: preserve-author-voice
  metric: voice_drift_score
  threshold: 0.25
  calibration_set: golden.voice.almasana.v3
  confidence_band: 0.05        # dentro de este margen -> requiere revisión humana
  sampling: 3                  # se evalúa 3 veces, se promedia
```

### 2.4 No hay árbitro de hallazgos contradictorios

Los revisores actúan en paralelo e independiente ("red, no cadena"), lo cual está bien, pero eso garantiza que van a chocar: el revisor estructural pide mover un bloque, el revisor de voz pide no tocar el ritmo de esa sección. No existe una pasada que resuelva ese conflicto — solo pasadas que corrigen "hallazgos aceptados", sin decir quién decide qué se acepta cuando dos reviewers se contradicen.

**Propuesta:** una pasada `review.arbitrate` que reciba el conjunto de `ReviewFinding` en conflicto y produzca una resolución priorizada, o escale a humano si la severidad es alta en ambos lados.

```yaml
arbitration:
  id: arbitration-0071
  conflicting_findings:
    - finding-239   # voice-drift
    - finding-240   # structural
  resolution: apply-structural-first-then-revoice
  escalate_to_human: false
```

### 2.5 No hay compuertas humanas explícitas

Todo el pipeline está diseñado para ser automatizable de punta a punta. Pero una editorial real —sobre todo una con línea doctrinal o pastoral, como mencionás en el ejemplo de Almasana— necesita puntos de aprobación humana **obligatoria**, no opcional: el autor aprueba la arquitectura antes de que se escriba, un editor humano aprueba antes de compilar la edición final.

**Propuesta:** agregar `requires_human_approval` a `EditorialPass`, y un objeto `ApprovalGate` que bloquee el flujo hasta recibir una decisión humana.

```yaml
approval_gate:
  id: gate-architecture-yo-no-soy
  stage: post-architecture-design
  status: pending
  required_role: author
  blocks: [draft.expand-scene]   # no se puede avanzar sin esta aprobación
```

### 2.6 No hay detección de obsolescencia visual

Un `visual_brief` se vincula a `linked_blocks`, pero si esos bloques cambian después de que el activo visual fue aprobado, nada marca ese activo como desactualizado. Es el mismo problema que 2.1 pero específico de la sincronización entre fábricas.

**Propuesta:** cada `visual_asset` guarda el hash del bloque en el momento de aprobación (`source_hash`); si el hash del bloque cambia, el activo pasa automáticamente a `stale` y dispara una nueva pasada `visual.review-staleness`.

### 2.7 No hay control de presupuesto ni scheduler

Con decenas de tipos de pasada por libro (investigación, arquitectura, borrador, cuatro tipos de revisión, brief visual, composición...), el costo en tokens y tiempo puede crecer sin control, y no hay ninguna pieza que decida *en qué orden* correr las pasadas ni que evite recomputar lo que no cambió.

**Propuesta:** un `PassScheduler` que se apoye en el `DependencyGraph` (2.1) para ejecutar solo lo invalidado, con un `Budget` por obra/editorial.

```yaml
budget:
  scope: work.yo-no-soy
  token_limit_monthly: 4_000_000
  spent: 1_240_000
  alert_threshold: 0.8
```

### 2.8 No hay multi-tenencia real

El documento se define como "editorial de editoriales", pero el modelo de datos no contempla aislamiento entre editoriales/clientes: permisos por rol, cuotas de uso, ni separación de datos. Si esto va a alojar el sello de un cliente externo junto con Almasana, hace falta esa capa desde el modelo de datos, no como agregado posterior.

---

## 3. Huecos secundarios, pero importantes a mediano plazo

**Anclaje de fuentes a texto exacto.** Hoy `sources: [source.augustine-confessions]` apunta a un ID de fuente completo, no a un rango exacto de texto. Para evitar alucinación de citas —algo especialmente sensible en contenido pastoral/doctrinal— conviene que cada `claim` referencie un span exacto (offset o hash de fragmento) dentro del documento fuente, verificable de forma automática.

**Observabilidad y golden sets.** No hay manera de detectar una regresión cuando cambian el modelo o un prompt de reviewer. Conviene un set de obras de referencia con hallazgos esperados, corrido como test de regresión antes de cualquier cambio en las pasadas.

**Simulador de lector.** Antes de compilar una edición, una pasada que simule la reacción del lector objetivo (comprensión, enganche, dudas) — barata de agregar dado que ya existe la categoría "reviewer", y detecta problemas de recepción que un revisor estructural no ve.

**Traducción y derechos como piezas futuras.** El mismo WorkGraph podría alimentar una tercera fábrica de traducción, y el modelo `Edition` podría llevar metadata de derechos/ISBN/distribución cuando el sistema publique de verdad, no solo compile.

---

## 4. Árbol de repo actualizado

```text
kernel/
├── work_graph/
├── manuscript_state/
├── editorial_passes/
├── patch_engine/
├── workflow_engine/
├── review_engine/
├── plugin_runtime/
├── semantic_memory/
├── edition_compiler/
├── dependency_graph/      # nuevo — invalidación incremental
├── version_control/       # nuevo — commits, branches, tags
├── pass_scheduler/         # nuevo — orden de ejecución + presupuesto
├── approval_gates/         # nuevo — compuertas humanas
└── tenancy/                 # nuevo — aislamiento por editorial/cliente

models/
├── ... (los existentes)
├── commit.py
├── dependency_edge.py
├── approval_gate.py
├── budget.py
├── review_arbitration.py
└── visual_staleness_flag.py
```

---

## 5. Los primeros objetos, actualizados

El documento original identifica bien el núcleo mínimo:

```text
Work + ContentBlock + WorkGraph + ManuscriptState + EditorialPass + Patch
```

Yo agregaría dos piezas a esa lista fundacional, porque sin ellas las promesas del resto del diseño no se cumplen en la práctica:

```text
Work + ContentBlock + WorkGraph + ManuscriptState + EditorialPass + Patch
+ DependencyGraph   (sin esto, "sin recargar el libro entero" es solo una aspiración)
+ Commit            (sin esto, "Patch" no es control de versiones, es solo un diff puntual)
```

Todo lo demás de esta v2 (árbitro, presupuesto, multi-tenencia, observabilidad) puede construirse sobre esos ocho objetos una vez que el motor funcione con un caso real — no hace falta resolverlo todo antes de escribir el primer libro.

---

## 6. Orden de implementación sugerido

1. `DependencyGraph` + invalidación incremental — es lo que hace viable trabajar con libros largos.
2. `Commit` / versionado real sobre el WorkGraph — antes de tener múltiples ediciones en paralelo.
3. `ApprovalGate` — antes de correr el sistema con contenido pastoral/doctrinal real.
4. Separación `DeterministicRule` / `JudgeRule` en la constitución — antes de confiar en los revisores para aceptar cambios sin supervisión.
5. Recién después: árbitro de conflictos, presupuesto/scheduler, multi-tenencia, observabilidad y golden sets.

---

## 7. Definición ampliada

> La arquitectura de oro de Editorial TR.ES es un WorkGraph **versionado por commits reales**, atravesado por pasadas editoriales atómicas **ejecutadas solo donde un grafo de dependencias detecta cambio**, evaluado por reglas que **distinguen lo determinístico de lo probabilístico**, protegido por **compuertas de aprobación humana** en los puntos que lo requieren, acompañado por una factoría visual **sincronizada activamente** con el estado literario, y compilado en múltiples ediciones dentro de un sistema que **aísla editoriales y controla su propio costo**.
