# Revisión LLM de reiteraciones globales — V1

## Estado

Implementado como capacidad opcional y no destructiva.

```text
implementation_id: llm_global_repetition
plugin_id: reviewer.llm-global-repetition
provider inicial: Google Gemini
modelo inicial: gemini-3.6-flash
```

## Problema

Una novela puede reiterar una frase, imagen, motivo o idea en capítulos distintos y con formulaciones diferentes. La coincidencia literal por bloque no puede descubrir:

- paráfrasis;
- ecos semánticos;
- imágenes recurrentes;
- motivos narrativos;
- latiguillos de personaje con variación;
- redundancias conceptuales distribuidas.

## Investigación

### Embeddings

Los embeddings permiten representar fragmentos por significado y recuperar pasajes similares sin exigir las mismas palabras. Sentence Transformers documenta similitud semántica, clustering, búsqueda y minería de paráfrasis; Multilingual E5 fue entrenado específicamente con pares multilingües y es una opción local viable para una futura fase de preselección.

Fuentes primarias:

- https://sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html
- https://www.sbert.net/docs/quickstart.html
- https://arxiv.org/abs/2402.05672
- https://arxiv.org/abs/2212.03533

### LLM con salida estructurada

Gemini admite salida restringida mediante JSON Schema, lo que permite pedir clusters tipados en lugar de texto libre. Gemini 3.6 Flash es un modelo estable con contexto de hasta 1.048.576 tokens y salida estructurada. La API oficial permite `generateContent` por REST con `responseFormat` y schema JSON.

Fuentes oficiales:

- https://ai.google.dev/gemini-api/docs/structured-output
- https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash
- https://ai.google.dev/gemini-api/docs/text-generation

## Decisión de arquitectura

La solución V1 utiliza un LLM para descubrir candidatos semánticos y aplica controles locales obligatorios:

```text
Work versionado
→ bloques con IDs estables
→ prompt literario
→ Gemini con JSON Schema
→ validación Pydantic
→ verificación literal de cada cita contra su bloque
→ ReviewFinding multibloque
→ decisión humana
```

El LLM no edita, no crea patches y no determina intención autoral como hecho.

## Salida estructurada

Cada cluster contiene:

- `cluster_id`;
- `candidate_type` controlado;
- `canonical_label`;
- explicación;
- confianza;
- dos o más apariciones;
- `block_id`;
- cita literal;
- razón local.

Tipos admitidos:

```text
literal_repetition
near_duplicate
semantic_echo
recurring_image
narrative_motif
character_catchphrase
possible_redundancy
requires_context
```

## Controles contra alucinación

TR.ES rechaza la respuesta completa si:

- el modelo cita un bloque inexistente;
- una cita no aparece literalmente en el bloque indicado;
- un cluster no abarca al menos dos bloques;
- se duplica una aparición;
- la estructura no cumple el schema.

Los clusters por debajo de la confianza configurada no generan hallazgo.

## Seguridad de transformación

Un hallazgo con múltiples bloques no puede alimentar `FindingDrivenBlockEditPass`.

```text
hallazgo multibloque
→ clasificación humana
→ selección explícita de una aparición
→ nueva propuesta concreta
→ aprobación independiente
→ patch
```

Esto evita que una conclusión global modifique accidentalmente sólo el primer bloque.

## Proveedor

La primera implementación usa Gemini REST mediante un adaptador reemplazable. El dominio depende de `StructuredLLMPort`, no de Google.

Configuración:

```text
GEMINI_API_KEY
EDITORIAL_TRES_GEMINI_MODEL opcional
EDITORIAL_TRES_GEMINI_TIMEOUT_SECONDS opcional
```

El manifest del plugin usa inicialmente `gemini-3.6-flash`.

## Escala de V1

V1 envía hasta:

- 250 bloques;
- 300.000 caracteres;

por ejecución. Superado el límite, falla explícitamente y exige fragmentación gobernada. No trunca silenciosamente.

## Evolución recomendada

Para obras muy extensas, agregar una fase local de embeddings:

```text
segmentación
→ embeddings multilingües
→ vecinos semánticos / clustering
→ LLM sólo sobre candidatos
→ verificación local
→ revisión humana
```

Esto reduce costo, evita comparación cuadrática mediante LLM y mantiene explicabilidad. El candidato local inicial a evaluar es `multilingual-e5`, pero no debe adoptarse sin un corpus español anotado.

## Criterio de éxito pendiente

La integración está técnicamente ejecutable, pero su calidad editorial no está certificada hasta medirla sobre un corpus anotado con:

- motivos deliberados;
- redundancias involuntarias;
- paráfrasis;
- latiguillos;
- falsos positivos por nombres y vocabulario común.

Métricas mínimas:

- precisión y recall por tipo;
- hallazgos por mil palabras;
- tasa de aceptación humana;
- estabilidad entre ejecuciones;
- costo y latencia por 100.000 palabras.
