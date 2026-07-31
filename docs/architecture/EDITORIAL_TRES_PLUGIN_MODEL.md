# Editorial TR.ES — Modelo canónico de plugins

## Estado

Canónico en principios y categorías conceptuales. La implementación runtime debe verificarse y evolucionar por capacidad.

## Principio

El kernel sabe **fabricar obras**. Los plugins saben **cómo se comporta una clase de obra o capacidad editorial**.

Los plugins son enchufables y desenchufables. No pueden redefinir las invariantes del kernel.

## Categorías

### Plugin editorial

Aporta:

- constitución;
- políticas;
- terminología;
- roles;
- criterios de aprobación;
- estándares de fuentes;
- identidad institucional;
- branding editorial.

No debe mezclar una voz autoral particular con reglas institucionales.

### Plugin de género

Aporta la gramática de una clase de obra:

- tipos de unidad;
- estructuras válidas;
- proporción narrativa/argumentativa/visual;
- pasadas predeterminadas;
- reviewers requeridos;
- métricas relevantes;
- estrategia de compilación.

Ejemplos:

- novela: escenas, personajes, arcos, continuidad;
- ensayo: claims, evidencia, objeciones, progresión argumental;
- poesía: poemas, secuencias, motivos, métrica opcional;
- novela gráfica: escenas, páginas, paneles, diálogo y visual beats;
- ensayo visual: claims y visuales como unidades coordinadas.

### Plugin de voz autoral

Aporta:

- corpus aprobado;
- corpus rechazado;
- corpus hablado;
- perfil extraído;
- perfil aprobado;
- métricas;
- patrones y antipatrones;
- ejemplos positivos/negativos;
- evaluación de deriva.

No decide el narrador de una obra.

### Plugin de narrador

Aporta:

- persona;
- distancia;
- focalización;
- fiabilidad;
- temporalidad;
- relación con el lector;
- acceso a interioridad;
- restricciones de conocimiento.

### Plugin de estilo

Modula una obra sin redefinir la identidad permanente del autor.

Puede declarar convenciones como:

- minimalista;
- lírico;
- documental;
- académico;
- pastoral;
- periodístico;
- noir;
- epistolar.

### Plugin reviewer

Aporta:

- tipo de finding;
- reglas;
- scope;
- severidad;
- formato de evidencia;
- naturaleza determinística o probabilística;
- recomendación;
- herramienta/modelo requerido.

Nunca aplica el `Patch` directamente.

### Plugin de método de investigación

Categoría conceptual destinada a modular:

- descubrimiento de fuentes;
- jerarquía de evidencia;
- credibilidad;
- extracción de fragmentos;
- claims;
- contradicciones;
- formato de cita;
- actualización.

Puede variar entre investigación histórica, académica, periodística, teológica, documental, autobiográfica o worldbuilding de ficción.

### Plugin de tipo visual

Define la gramática de un activo:

- ilustración;
- diagrama;
- mapa;
- línea de tiempo;
- infografía;
- gráfico de datos;
- página de cómic;
- portada;
- lámina.

Declara inputs semánticos, restricciones y tipo de salida.

### Plugin de estilo visual

Aporta:

- paleta;
- texturas;
- iluminación;
- iconografía;
- lenguaje de formas;
- composición;
- tratamiento de personajes;
- consistencia de serie;
- prohibiciones visuales.

No decide qué debe representar el activo.

### Plugin workflow

Puede definir:

- secuencia de pasadas;
- paralelismo;
- gates;
- reintentos;
- reviewers requeridos;
- condiciones;
- presupuesto;
- escalamiento humano;
- criterios de finalización.

No puede saltarse `Patch`, trazabilidad ni aprobaciones obligatorias.

### Plugin output

Compila una edición aprobada hacia una salida concreta:

- PDF;
- EPUB;
- HTML;
- app-book;
- impresión;
- audio;
- presentación;
- fixed-layout;
- derivados.

El output compila; no reescribe creativamente la obra.

## PluginRuntime

El runtime de plugins debe, cuando se implemente plenamente, validar al menos:

- manifiesto;
- versión;
- compatibilidad;
- dependencias;
- permisos/capacidades;
- inputs y outputs;
- necesidad de modelos o herramientas;
- determinismo;
- riesgos;
- aislamiento.

La existencia de manifiestos o directorios de plugins no demuestra que el runtime esté implementado. Esa distinción debe mantenerse en la documentación de estado.

## Invariantes que ningún plugin puede violar

- obra vigente inmutable fuera de la aplicación autorizada de un `Patch`;
- trazabilidad de origen;
- separación reviewer/transformación;
- correspondencia entre propuesta y versión fuente;
- autoridad humana final cuando corresponda;
- aislamiento entre editoriales, autores, obras y ramas;
- una edición como proyección de la obra, no copia independiente.
