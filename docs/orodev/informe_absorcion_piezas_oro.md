# 🏆 Informe de Absorción de Piezas de Oro
## Estrategia de Integración de Herramientas Externas en Editorial TR.ES

**Fecha:** 1 de agosto de 2026  
**Para:** Consejo Editorial de TR.ES  
**Tipo:** Documento estratégico de absorción tecnológica

---

## Resumen Ejecutivo

Este documento presenta las **piezas de oro** descubiertas en el ecosistema Git literario 2025-2026 y recomienda cómo **absorberlas como plugins** dentro de la arquitectura constitucional de Editorial TR.ES.

**Principio rector:** Ninguna pieza externa reemplaza la arquitectura canónica. Cada herramienta se transforma en un plugin que respeta la supremacía constitucional, nunca muta la obra, y requiere aprobación humana para cualquier transformación.

---

## 1. Filosofía de Absorción

### Lo que absorbemos vs. lo que rechazamos

**✅ Absorbemos:**
- Señales y hallazgos que enriquecen la detección
- Métricas cuantificables de calidad narrativa
- Corpus lingüísticos para análisis estilométrico
- Estructuras de worldbuilding persistente
- Taxonomías de tropos y arcos narrativos

**❌ Rechazamos:**
- Cualquier herramienta que reescriba automáticamente
- Pipelines que omitan la aprobación humana
- Sistemas que fusionen crítico y transformador
- Correcciones que no preserven la voz autoral

### La arquitectura TR.ES como marco de absorción

Toda pieza externa se convierte en un **plugin** que:
1. Produce `ReviewFinding` (nunca `Patch` directo)
2. Requiere `FindingDecision` humana
3. Respeta `AuthorMemory` y `EditorialMemory`
4. Se somete a la **supremacía constitucional**

---

## 2. Piezas de Oro y su Absorción como Plugins

### 💎 Pieza 1: `lechmazur/writing` (Benchmark Narrativo)

**Qué es:** Benchmark que evalúa 10 elementos narrativos obligatorios en textos generados por LLM (personajes, objetos, tono, motivación, etc.).

**Plugin candidato:** `reviewer.narrative_quality`

```yaml
id: reviewer.narrative_quality
version: 0.1.0
type: reviewer
name: Revisor de calidad narrativa
description: Evalúa la presencia y coherencia de los 10 elementos narrativos obligatorios sin emitir juicios estéticos.
capabilities:
  - character_presence_detection
  - object_tracking
  - tone_consistency_check
  - motivation_coherence_analysis
  - plot_progression_validation
  - dialogue_authenticity_assessment
  - setting_immersion_measurement
  - conflict_development_tracking
  - resolution_satisfaction_check
  - thematic_resonance_analysis
rules:
  - reviewer_never_mutates_work
  - findings_must_reference_source_version
  - narrative_signals_are_not_aesthetic_verdicts
behavior:
  finding_type: narrative.quality.signal
  scope: [manuscript_state]
  severity: info
  evidence_format: element_presence_score
  recommendation_policy: revisar si los elementos narrativos están presentes y coherentes
  nature: hybrid_deterministic_llm
```

**Valor para TR.ES:**
- Funciona como "panel de catadores" algorítmico
- Elimina sesgos de reputación en primera lectura
- Cuantifica elementos que antes eran subjetivos

**Cómo se absorbe:**
- Fork de la lógica de detección de elementos
- Integración como reviewer híbrido (determinista + LLM)
- Los 10 elementos se convierten en parámetros configurables
- Cada elemento produce un `ReviewFinding` con score

---

### 💎 Pieza 2: `raestrada/storycraftr` (CLI de Worldbuilding)

**Qué es:** Herramienta CLI para worldbuilding persistente, generación de esquemas y chat interactivo con IA. Soporta español nativo.

**Plugin candidato:** `workflows.worldbuilding_bridge`

```yaml
id: workflow.worldbuilding_bridge
version: 0.1.0
type: workflow
name: Flujo de worldbuilding persistente
description: Integra worldbuilding externo como memoria de obra persistente, alimentando AuthorMemory y PastWorkMemory.
capabilities:
  - world_state_persistence
  - character_registry_management
  - timeline_tracking
  - location_mapping
  - magic_system_documentation
rules:
  - worldbuilding_enriches_memories_not_work
  - human_approves_all_world_elements
  - world_elements_reference_source_version
behavior:
  output: enriches EditorMemory and PastWorkMemory
  approval_required: true
```

**Valor para TR.ES:**
- Reduce la fase de desarrollo de meses a semanas
- Worldbuilding persistente que alimenta las memorias del sistema
- Base para spin-offs y secuelas coherentes

**Cómo se absorbe:**
- Bridge que convierte worldbuilding externo en `PastWorkMemory`
- Los elementos de mundo (personajes, lugares, sistemas) se registran como metadata
- El workflow requiere aprobación antes de integrar elementos al canon

---

### 💎 Pieza 3: `andreamorgar/poesIA` (Corpus Poético Español)

**Qué es:** Corpus escrapeado de poesía española con tareas NLP para análisis estilométrico.

**Plugin candidato:** `reviewer.stylometric_analysis`

```yaml
id: reviewer.stylometric_analysis
version: 0.1.0
type: reviewer
name: Revisor estilométrico
description: Analiza la firma estilística del texto comparándola con corpus histórico de poesía española sin emitir juicios de valor.
capabilities:
  - vocabulary_richness_measurement
  - sentence_complexity_analysis
  - metaphor_density_detection
  - rhythm_pattern_recognition
  - authorial_fingerprint_comparison
  - historical_style_mapping
rules:
  - reviewer_never_mutates_work
  - stylometric_signals_are_not_quality_verdicts
  - comparisons_reference_corpus_version
behavior:
  finding_type: style.stylometric.signal
  scope: [expression_block, manuscript_state]
  severity: info
  evidence_format: metric_scores_with_corpus_reference
  recommendation_policy: revisar si la firma estilística es coherente con la voz autoral declarada
  nature: hybrid_deterministic_ml
```

**Valor para TR.ES:**
- Base de datos propia para sellos de poesía contemporánea
- Detección de voces emergentes por comparación con corpus histórico
- Herramienta de pitching: "Tu manuscrito tiene el ADN estilístico de X autor"

**Cómo se absorbe:**
- Corpus se integra como `EditorialMemory` (recurso compartido)
- Análisis estilométrico produce señales, no correcciones
- Comparaciones con corpus histórico se registran en findings

---

### 💎 Pieza 4: `nayracoop/literatura-digital` (Narrativa Hipertextual)

**Qué es:** App web para crear historias no lineales con distintas visualizaciones (sin LLM).

**Plugin candidato:** `outputs.hypertext_manuscript`

```yaml
id: output.hypertext_manuscript
version: 0.1.0
type: output
name: Formateador de manuscrito hipertextual
description: Exporta la obra como narrativa hipertextual no lineal, preservando la estructura de lexias y enlaces.
capabilities:
  - lexia_structure_export
  - hyperlink_generation
  - non_linear_navigation_map
  - interactive_visualization
rules:
  - output_preserves_authorial_structure
  - hypertext_respects_work_integrity
  - export_references_source_version
behavior:
  output_format: hypertext_web_app
  preserves: [lexias, links, navigation_structure]
```

**Valor para TR.ES:**
- Nuevo sello editorial: "TR.ES Experimental"
- Narrativas hipertextuales para literatura digital
- Diferenciación en mercado de vanguardia

**Cómo se absorbe:**
- Plugin de output que exporta la obra como app web interactiva
- Preserva la estructura de lexias definida por el autor
- No modifica la obra, solo la formatea para consumo no lineal

---

### 💎 Pieza 5: `languagetool-org/languagetool` (Corrección Gramatical)

**Qué es:** Corrector de gramática y estilo para 25+ idiomas, incluyendo español. Híbrido: reglas + ML.

**Plugin candidato:** `reviewer.grammar_style`

```yaml
id: reviewer.grammar_style
version: 0.1.0
type: reviewer
name: Revisor de gramática y estilo
description: Detecta errores gramaticales y sugiere mejoras estilísticas sin reescribir ni modificar la voz autoral.
capabilities:
  - grammar_error_detection
  - spelling_correction_suggestion
  - style_improvement_recommendation
  - punctuation_analysis
  - false_friends_detection
  - gender_neutrality_check
rules:
  - reviewer_never_mutates_work
  - grammar_signals_preserve_authorial_voice
  - suggestions_reference_language_tool_version
behavior:
  finding_type: expression.grammar.signal
  scope: [expression_block]
  severity: warning
  evidence_format: error_excerpt_with_suggestion
  recommendation_policy: revisar si la corrección preserva la voz autoral
  nature: hybrid_rules_ml
```

**Valor para TR.ES:**
- API interna para el equipo de corrección
- Detección multilingüe (español, catalán, gallego, euskera)
- Base para corrección literaria profesional

**Cómo se absorbe:**
- Integración de LanguageTool API como backend
- Produce `ReviewFinding` con sugerencia, no corrección automática
- El humano decide si aplicar o rechazar cada sugerencia

---

### 💎 Pieza 6: `theJayTea/WritingTools` (Revisión Estilo Apple Intelligence)

**Qué es:** Herramienta de corrección estilo Apple Intelligence para Windows, Linux y macOS.

**Plugin candidato:** `reviewer.prose_refinement`

```yaml
id: reviewer.prose_refinement
version: 0.1.0
type: reviewer
name: Revisor de refinamiento de prosa
description: Sugiere mejoras de prosa (claridad, concisión, fluidez) sin reescribir ni modificar la voz autoral.
capabilities:
  - clarity_improvement_suggestion
  - conciseness_recommendation
  - flow_enhancement_advice
  - redundancy_detection
  - passive_voice_analysis
rules:
  - reviewer_never_mutates_work
  - prose_signals_preserve_authorial_intent
  - suggestions_reference_writing_tools_version
behavior:
  finding_type: expression.prose.signal
  scope: [expression_block, paragraph]
  severity: info
  evidence_format: original_excerpt_with_improvement_suggestion
  recommendation_policy: revisar si la mejora preserva la intención autoral
  nature: llm_assisted
```

**Valor para TR.ES:**
- Plugin para el equipo de corrección de estilo
- Mejoras de prosa que respetan la voz del autor
- Diferenciación: "corregir sin corregir"

**Cómo se absorbe:**
- Integración como reviewer LLM-asistido
- Produce sugerencias de refinamiento, no reescrituras
- Cada sugerencia requiere aprobación humana

---

### 💎 Pieza 7: `LimHyungTae/awesome-claudecode-paper-proofreading` (Preservación de Voz)

**Qué es:** Flujos de corrección que preservan la "filosofía" o voz original del autor durante proofreading.

**Plugin candidato:** `reviewer.authorial_intent`

```yaml
id: reviewer.authorial_intent
version: 0.1.0
type: reviewer
name: Revisor de intención autoral
description: Detecta cuándo una corrección podría alterar la filosofía o voz original del autor, alertando al editor.
capabilities:
  - authorial_voice_preservation_check
  - philosophical_intent_detection
  - stylistic_signature_analysis
  - voice_drift_prevention
rules:
  - reviewer_never_mutates_work
  - intent_signals_protect_authorial_philosophy
  - comparisons_reference_author_memory
behavior:
  finding_type: voice.authorial_intent.signal
  scope: [expression_block, manuscript_state]
  severity: warning
  evidence_format: voice_comparison_with_author_memory
  recommendation_policy: revisar si la corrección preserva la filosofía autoral
  nature: llm_assisted
```

**Valor para TR.ES:**
- Protección contra la homogeneización de voz
- Alerta cuando una corrección altera la "filosofía" del autor
- Diferenciación: "corrección que respeta, no reemplaza"

**Cómo se absorbe:**
- Comparación con `AuthorMemory` para detectar desviaciones
- Produce alertas cuando una corrección podría alterar la voz
- El humano decide si la corrección es apropiada

---

### 💎 Pieza 8: `Awesome-Story-Generation` (Taxonomía de Tropos)

**Qué es:** Lista exhaustiva de papers sobre generación de historias y narrativa en la era de los LLM.

**Plugin candidato:** `reviewer.tropes_taxonomy`

```yaml
id: reviewer.tropes_taxonomy
version: 0.1.0
type: reviewer
name: Revisor de taxonomía de tropos
description: Identifica tropos narrativos presentes en la obra y los mapea contra taxonomía actualizada de story generation.
capabilities:
  - trope_identification
  - archetype_recognition
  - narrative_structure_mapping
  - genre_convention_analysis
  - trope_subversion_detection
rules:
  - reviewer_never_mutates_work
  - trope_signals_are_not_quality_verdicts
  - taxonomy_references_paper_version
behavior:
  finding_type: narrative.trope.signal
  scope: [manuscript_state, chapter]
  severity: info
  evidence_format: trope_list_with_evidence
  recommendation_policy: revisar si los tropos son deliberados o accidentales
  nature: hybrid_deterministic_llm
```

**Valor para TR.ES:**
- Biblioteca de tropos vivos para estrategia editorial
- Detección de nichos sin explotar
- Herramienta de pitching: "Tu obra usa estos 5 tropos de forma original"

**Cómo se absorbe:**
- Taxonomía se integra como `EditorialMemory` (recurso compartido)
- Identificación de tropos produce señales, no juicios
- Mapeo contra papers actualizados de story generation

---

## 3. Priorización de Absorción

### 🔴 Fase 1: Infraestructura crítica (0-3 meses)

**Plugins a absorber primero:**

1. **`reviewer.grammar_style`** (LanguageTool)
   - Razón: Corrección gramatical es necesidad inmediata
   - Impacto: Reduce carga del equipo de corrección
   - Riesgo: Bajo (herramienta madura)

2. **`reviewer.narrative_quality`** (lechmazur/writing)
   - Razón: Control de calidad narrativo es diferenciador
   - Impacto: Standard de calidad cuantificable
   - Riesgo: Medio (requiere integración LLM)

3. **`reviewer.authorial_intent`** (awesome-claudecode)
   - Razón: Protección de voz autoral es valor único
   - Impacto: Diferenciación frente a corrección automática
   - Riesgo: Bajo (comparación con AuthorMemory)

### 🟡 Fase 2: Diferenciación editorial (3-6 meses)

**Plugins a absorber:**

4. **`reviewer.stylometric_analysis`** (poesIA)
   - Razón: Análisis estilométrico es nicho de vanguardia
   - Impacto: Sello de poesía contemporánea
   - Riesgo: Medio (requiere corpus español)

5. **`reviewer.tropes_taxonomy`** (Awesome-Story-Generation)
   - Razón: Taxonomía de tropos es herramienta estratégica
   - Impacto: Estrategia de adquisición basada en datos
   - Riesgo: Bajo (integración de papers)

6. **`workflow.worldbuilding_bridge`** (storycraftr)
   - Razón: Worldbuilding persistente acelera desarrollo
   - Impacto: Reducción de fase de development
   - Riesgo: Medio (integración CLI)

### 🟢 Fase 3: Ecosistema abierto (6-12 meses)

**Plugins a absorber:**

7. **`reviewer.prose_refinement`** (WritingTools)
   - Razón: Refinamiento de prosa es mejora incremental
   - Impacto: Plugin para autores contratados
   - Riesgo: Bajo (herramienta ligera)

8. **`output.hypertext_manuscript`** (literatura-digital)
   - Razón: Narrativa hipertextual es experimentación
   - Impacto: Sello "TR.ES Experimental"
   - Riesgo: Alto (nuevo formato de salida)

---

## 4. Roadmap de Implementación

### Arquitectura de absorción

```
Pieza externa → Fork de lógica → Plugin TR.ES → Reviewer/Workflow/Output
                                      ↓
                              Produce ReviewFinding
                                      ↓
                              Requiere FindingDecision
                                      ↓
                              Humano aprueba/rechaza
                                      ↓
                              Si aprueba → Patch → ApprovalGate → Commit
```

### Pasos técnicos para cada pieza

1. **Fork y aislamiento**
   - Clonar repositorio externo
   - Extraer solo la lógica de detección/análisis
   - Eliminar cualquier código de reescritura automática

2. **Adaptación a plugin TR.ES**
   - Crear `plugin.yaml` con estructura canónica
   - Escribir `SKILL.md` con descripción y reglas
   - Definir capabilities, rules, behavior

3. **Integración con memorias**
   - Conectar con `AuthorMemory` para comparaciones
   - Alimentar `EditorialMemory` con corpus/taxonomías
   - Enriquecer `PastWorkMemory` con worldbuilding

4. **Testing constitucional**
   - Verificar que nunca muta la obra
   - Confirmar que produce solo `ReviewFinding`
   - Validar que requiere aprobación humana

5. **Despliegue incremental**
   - Activar en modo "solo señales" (severity: info)
   - Recoger feedback del equipo editorial
   - Ajustar parámetros y thresholds
   - Promover a severity: warning si es útil

---

## 5. Riesgos y Mitigaciones

### Riesgo 1: Dependencia de herramientas externas

**Problema:** Si el repositorio externo se abandona, perdemos capacidad.

**Mitigación:**
- Fork completo de la lógica crítica
- Documentación de algoritmos internos
- Capacitación del equipo en los fundamentos

### Riesgo 2: Complejidad de integración LLM

**Problema:** Reviewers híbridos (determinista + LLM) son difíciles de mantener.

**Mitigación:**
- Empezar con reviewers deterministas puros
- Introducir LLM solo cuando sea indispensable
- Monitorear costos y latencia

### Riesgo 3: Sobrecarga de señales

**Problema:** Demasiados reviewers producen demasiados findings, saturando al humano.

**Mitigación:**
- Severity graduada (info, warning, error)
- Configuración por proyecto (activar solo reviewers relevantes)
- Dashboard de findings priorizados

### Riesgo 4: Pérdida de voz autoral

**Problema:** Correcciones automáticas homogeneizan la voz.

**Mitigación:**
- Plugin `reviewer.authorial_intent` como guardián
- Comparación obligatoria con `AuthorMemory`
- Aprobación humana como compuerta final

---

## 6. Métricas de Éxito

### Métricas de absorción

- **Cobertura:** % de piezas externas absorbidas como plugins
- **Utilidad:** % de findings que el humano aprueba (vs. rechaza)
- **Eficiencia:** Reducción de tiempo en fase de corrección
- **Calidad:** Mejora en coherencia narrativa (medida por reviewer.narrative_quality)

### Métricas editoriales

- **Velocidad:** Reducción de tiempo de development (worldbuilding)
- **Diferenciación:** Nuevos sellos editoriales lanzados (poesía, experimental)
- **Satisfacción:** Autores reportan que su voz fue preservada
- **Innovación:** % de obras que usan narrativa hipertextual

---

## 7. Conclusión

La estrategia de absorción convierte herramientas externas en **extensiones constitucionales** de Editorial TR.ES. Cada pieza se transforma en un plugin que:

1. **Respeta la supremacía constitucional** (ningún plugin vulnera las reglas)
2. **Nunca muta la obra** (solo produce señales)
3. **Requiere aprobación humana** (el humano es la compuerta final)
4. **Preserva la voz autoral** (comparación con AuthorMemory)

**El oro no está afuera — está en el marco que TR.ES ya construyó para absorberlo sin perder identidad.**

---

## Apéndice: Resumen de Plugins Candidatos

| # | Pieza externa | Plugin TR.ES | Tipo | Prioridad |
|---|---|---|---|---|
| 1 | lechmazur/writing | reviewer.narrative_quality | Reviewer | 🔴 Alta |
| 2 | raestrada/storycraftr | workflow.worldbuilding_bridge | Workflow | 🟡 Media |
| 3 | andreamorgar/poesIA | reviewer.stylometric_analysis | Reviewer | 🟡 Media |
| 4 | nayracoop/literatura-digital | output.hypertext_manuscript | Output | 🟢 Baja |
| 5 | languagetool-org/languagetool | reviewer.grammar_style | Reviewer | 🔴 Alta |
| 6 | theJayTea/WritingTools | reviewer.prose_refinement | Reviewer | 🟢 Baja |
| 7 | LimHyungTae/awesome-claudecode | reviewer.authorial_intent | Reviewer | 🔴 Alta |
| 8 | Awesome-Story-Generation | reviewer.tropes_taxonomy | Reviewer | 🟡 Media |

---

## 8. Preguntas Socráticas para el Consejo Editorial

Antes de proceder con la absorción, el Consejo debe considerar estas preguntas fundamentales:

### 🔍 Pregunta 1: Sobre la absorción
Si absorbemos estas 8 piezas como plugins, ¿estamos **fortaleciendo** la arquitectura constitucional de TR.ES, o estamos **diluyendo** su identidad al depender de herramientas externas?

- **Argumento a favor:** Cada pieza se transforma en plugin que respeta la supremacía constitucional
- **Argumento en contra:** La dependencia de forks externos crea deuda técnica y riesgo de abandono
- **Decisión requerida:** ¿Cuál es el umbral de complejidad que estamos dispuestos a absorber?

### 🔍 Pregunta 2: Sobre la priorización
He marcado como 🔴 Alta prioridad los reviewers de calidad narrativa, gramática y preservación de voz. ¿Estás de acuerdo con esta priorización, o crees que deberíamos empezar por otra pieza (quizás el worldbuilding bridge para acelerar el desarrollo)?

- **Prioridad actual:** `reviewer.grammar_style` → `reviewer.narrative_quality` → `reviewer.authorial_intent`
- **Alternativa:** Empezar con `workflow.worldbuilding_bridge` para reducir fase de development
- **Decisión requerida:** ¿Qué necesitamos primero: calidad o velocidad?

### 🔍 Pregunta 3: Sobre el riesgo
El documento menciona el riesgo de "sobrecarga de señales" — demasiados reviewers producen demasiados findings que saturan al humano. ¿Cómo crees que deberíamos diseñar el dashboard de findings priorizados para evitar esta fatiga editorial?

- **Opción A:** Severity graduada (info, warning, error) con configuración por proyecto
- **Opción B:** Dashboard inteligente que agrupa findings por tipo y relevancia
- **Opción C:** Modo "solo señales críticas" por defecto, activable según necesidad
- **Decisión requerida:** ¿Cuál es la capacidad de atención del equipo editorial?

---

**Documento preparado para el Consejo Editorial de TR.ES**  
**Ciclo estratégico 2026-2027**
