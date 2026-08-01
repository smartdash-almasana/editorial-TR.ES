# Editorial TR.ES — Factorías literaria y visual

## Estado

Canónico.

## Principio

Editorial TR.ES tiene dos pilares productivos de igual jerarquía:

```text
                 WorkGraph
                /         \
   factoría literaria   factoría visual
                \         /
             EditionCompiler
```

La visualidad no se agrega al final como decoración. Texto y visuales derivan de la misma semántica de obra y deben mantenerse sincronizados.

## Factoría literaria

Responsabilidades:

- investigación y organización de fuentes;
- claims y evidencia;
- arquitectura narrativa o argumental;
- escritura por bloques;
- preservación de voz;
- narrador y estilo;
- revisión especializada;
- findings;
- patches;
- versiones aprobadas.

Su operación normal es incremental: una pasada trabaja sobre un target acotado y produce análisis o propuesta, no una regeneración completa del libro.

## Factoría visual

Responsabilidades:

- detectar oportunidades visuales;
- construir briefs;
- gestionar símbolos y referencias;
- producir arte y variantes;
- producir gráficos y diagramas;
- componer tipografía y layout;
- revisar consistencia y legibilidad;
- mantener trazabilidad hacia los bloques que dieron origen al activo.

## Visual opportunity

Una pasada puede detectar que un bloque, claim, secuencia o símbolo se beneficiaría de un recurso visual para:

- explicar;
- condensar;
- comparar;
- orientar;
- emocionar;
- representar un símbolo;
- mostrar secuencia;
- crear ritmo editorial.

Una oportunidad no genera automáticamente una imagen.

## Visual brief

El brief es el contrato entre la semántica de la obra y la producción visual.

Debe poder expresar, según el tipo de activo:

- propósito;
- bloques vinculados;
- claim o idea central;
- función narrativa;
- audiencia;
- tipo visual;
- símbolos;
- composición;
- restricciones;
- referencias;
- estilo;
- formato;
- accesibilidad;
- elementos prohibidos;
- versión/hash de la fuente semántica.

## Arte generativo vs composición editorial

El generador visual puede producir:

- bocetos;
- fondos;
- ilustraciones;
- recursos gráficos;
- variantes de portada;
- material visual sin tipografía final.

Editorial TR.ES debe conservar por código el control de:

- dimensiones;
- safe areas;
- layout;
- tipografía;
- texto final;
- wrapping;
- jerarquía;
- ortografía;
- pies y créditos;
- numeración;
- gráficos de datos cuando sean determinísticos;
- diagramas reproducibles;
- exportación;
- checksums;
- manifests;
- accesibilidad.

## Regla de texto en imágenes

Se descarta delegar páginas o infografías completas cargadas de texto a un modelo de imagen como mecanismo normal.

Motivos:

- errores ortográficos;
- deformación tipográfica;
- regeneraciones costosas;
- imposibilidad de corrección granular;
- accesibilidad deficiente;
- traducción difícil;
- baja trazabilidad.

El arte y la composición tipográfica son capas distintas.

## Gráficos y diagramas

Cuando la obra contiene datos o relaciones estructuradas:

```text
semántica / datos
→ propuesta conceptual opcional de IA
→ renderer determinístico
→ activo versionado
```

El sistema debe preferir un gráfico reproducible a una imagen raster generada cuando la información pueda representarse determinísticamente.

## Ilustraciones

Una ilustración aprobada debe poder conservar:

- brief;
- prompts relevantes;
- referencias;
- modelo o artista;
- parámetros reproducibles cuando existan;
- linked blocks;
- versión fuente;
- aprobación;
- derechos/procedencia.

## Sincronización e invalidación visual

Un visual depende de contenido semántico concreto. Si cambia su fuente, debe poder quedar marcado como obsoleto o pendiente de revisión.

Objetivo:

```text
block cambia
→ DependencyGraph detecta visual dependiente
→ visual stale / needs-review
→ revisión selectiva
```

No se regenera automáticamente todo el universo visual.

## Género y proporción texto/visual

La proporción entre factorías no es fija.

Ejemplos:

- novela: NarrativeGraph dominante, visual opcional;
- ensayo: conocimiento/argumentación dominante, gráficos explicativos opcionales;
- poesía: ExpressionGraph dominante, visual muy selectivo;
- novela gráfica: literatura y visual equilibradas;
- libro ilustrado: visual puede conducir la experiencia;
- ensayo visual: claim y visual funcionan como unidad coordinada.

Esto lo modulan plugins de género y visuales, no forks del kernel.

## EditionCompiler

Las dos factorías convergen en la compilación de una edición.

`EditionCompiler` debe resolver, progresivamente:

- selección de bloques;
- orden;
- activos;
- referencias;
- navegación;
- diseño;
- formato;
- exportación.

Una edición es una proyección del `WorkGraph`.

Posibles outputs:

- PDF ilustrado;
- PDF imprimible;
- EPUB;
- HTML;
- edición impresa;
- AppBookEdition;
- audio y derivados futuros.

## Frontera con App Book Format y TRES.APP

Las dos factorías convergen en `EditionCompiler`, que proyecta una edición aprobada hacia salidas concretas.

Para App Book, el resultado no debe ser una pantalla ni una estructura privada de Studio, sino un paquete que cumpla `App Book Format`:

```text
WorkGraph
→ factorías literaria + visual
→ EditionProjector / EditionCompiler
→ AppBookPackage
→ App Book Format
→ TRES.APP / App Book Reader
```

El formato transporta estructura editorial, bloques, citas, fuentes, bibliografía, visuales, audio, actividades, artefactos y metadatos de consumo necesarios, sin exponer el historial interno de producción.

TRES.APP consume esa edición y ofrece la experiencia interactiva de lectura. Funciones como tooltips de citas, swipe de ilustraciones, temas de lectura, audio, actividades, guardados, biblioteca, offline y progreso pertenecen al Reader, no al kernel de producción.

La especificación arquitectónica del contrato está en `APP_BOOK_FORMAT_CONTRACT.md`.
