# Editorial TR.ES — Definición canónica de producto

## Estado

Canónico.

## Qué es Editorial TR.ES

Editorial TR.ES es una **factoría editorial enterprise, multimodal y agnóstica de género** para producir obras literarias y visuales con identidad propia, trazabilidad, revisión profesional y múltiples ediciones derivadas de una misma obra estructurada.

No es un chatbot de escritura, un CMS, una colección de prompts ni un agente autónomo que genera libros completos de una sola vez.

Su unidad de trabajo no es un documento monolítico, sino una obra estructurada y versionada mediante un `WorkGraph` compuesto por conocimiento, narrativa, expresión, dependencias y activos vinculados.

## Propósito

La plataforma debe poder constituir editoriales, constituir obras y producirlas de extremo a extremo:

```text
constitución editorial
→ constitución de obra
→ investigación y fuentes
→ arquitectura
→ producción literaria
→ revisión especializada
→ producción visual
→ aprobación
→ versión editorial
→ compilación de edición
```

La IA amplía capacidad creativa y editorial, pero no sustituye la autoridad del autor ni del editor humano.

## Dos pilares productivos de igual jerarquía

### Factoría literaria

Produce y revisa:

- conocimiento y fuentes;
- arquitectura de obra;
- narrativa;
- expresión;
- voz autoral;
- narrador;
- estilo;
- manuscrito;
- hallazgos editoriales;
- propuestas de cambio.

### Factoría visual

Produce y revisa:

- oportunidades visuales;
- briefs;
- ilustraciones;
- gráficos;
- diagramas;
- infografías;
- portadas;
- aperturas;
- secuencias visuales;
- activos derivados.

La factoría visual no es decoración posterior. Consume la misma semántica de la obra y debe mantenerse sincronizada con ella.

El modelo generativo puede producir arte, fondos, bocetos o recursos gráficos. La plataforma conserva por código el control de tipografía, ortografía, texto final, diagramación, gráficos determinísticos, composición y exportación.

## Agnosticismo de género

El kernel no está diseñado alrededor de un único tipo de libro. Debe soportar desde obras predominantemente narrativas hasta obras predominantemente visuales.

Ejemplos compatibles:

- novela;
- cuento;
- ensayo;
- tratado;
- poesía;
- devocional;
- biografía;
- crónica;
- novela gráfica;
- cómic;
- libro ilustrado;
- ensayo visual;
- infografía narrativa;
- manual;
- obra académica;
- obra interactiva.

El comportamiento específico se aporta mediante plugins, sin modificar las invariantes del kernel.

## Plugins

Los plugins son órganos enchufables y desenchufables. No son el corazón del sistema.

Categorías conceptuales:

- editorial;
- género;
- voz autoral;
- narrador;
- estilo;
- reviewer;
- método de investigación;
- tipo visual;
- estilo visual;
- workflow;
- output.

Un plugin puede cambiar estrategias, reglas, pasadas, reviewers o composición, pero nunca puede violar:

- inmutabilidad de la obra vigente;
- uso obligatorio de `Patch` para transformaciones;
- trazabilidad;
- separación crítica/transformación;
- aprobación humana cuando corresponda;
- aislamiento entre obra, autor y editorial.

## Una obra, múltiples ediciones

Una edición es una proyección derivada del mismo `WorkGraph`, no una copia divergente del manuscrito.

Posibles salidas:

- PDF ilustrado;
- PDF imprimible;
- EPUB;
- HTML;
- edición impresa;
- app-book;
- audio;
- derivados visuales.

## Arquitectura de producto: Studio + Format + Reader

Editorial TR.ES se expresa comercialmente mediante dos productos públicos y un contrato central:

```text
Editorial TR.ES
├── TR.ES Studio
│   producción, revisión, diseño, conversión y publicación
├── App Book Format
│   contrato versionado de edición
└── App Book Reader
    lectura, biblioteca, descubrimiento y consumo
```

`TR.ES Studio` es el producto para autores, editores y sellos. Se monta sobre el kernel y las factorías para ofrecer diagnóstico, corrección, revisión, producción visual y sonora, compilación y publicación.

`App Book Format` desacopla producción y consumo. Es el paquete estructurado, validable y versionado que representa una edición App Book aprobada.

`E:\BuenosPasos\TRES.APP` es el runtime lector de App Book Reader. Hace leer la edición: navegación, tooltips, swipe visual, temas de lectura, audio, actividades, guardados, progreso, biblioteca, offline y descargas autorizadas.

La frontera conceptual es:

```text
WorkGraph
→ EditionProjector / EditionCompiler
→ AppBookPackage / App Book Format
→ TRES.APP / App Book Reader
```

El Reader no debe conocer prompts, skills, modelos, findings, patches, costos ni decisiones internas de producción. Recibe una edición aprobada.

La arquitectura comercial completa y las fronteras entre núcleo editorial, dominio comercial, lectura y analítica se documentan en `EDITORIAL_TRES_COMMERCIAL_PLATFORM_VISION.md`. El contrato del formato se documenta en `APP_BOOK_FORMAT_CONTRACT.md`.

## Criterio rector

Toda capacidad nueva debe responder a esta pregunta:

> ¿Mejora la capacidad de producir una obra literaria y visual profesional, preservando identidad, trazabilidad y coherencia entre ediciones?

Si no contribuye a ese objetivo, no pertenece al núcleo productivo inmediato.
