# App Book Format — Contrato arquitectónico

## Estado

Canónico como frontera entre producción editorial y experiencia de lectura. La serialización física concreta todavía debe diseñarse y validarse en implementación.

## Propósito

App Book Format es el contrato estructurado mediante el cual una edición aprobada sale de TR.ES Studio y puede ser consumida por App Book Reader sin acoplar ambos productos a sus implementaciones internas.

```text
WorkGraph
→ EditionProjector
→ EditionCompiler
→ AppBookPackage
→ App Book Format
→ App Book Reader
```

No es el WorkGraph completo, no es una base compartida y no transporta el historial interno de producción salvo aquello requerido por integridad, procedencia, derechos o auditoría.

## Principios

El formato debe ser:

- versionado;
- validable por schema;
- portable;
- independiente de la UI del Reader;
- independiente del runtime interno de Studio;
- explícito en referencias y assets;
- verificable en integridad;
- extensible sin romper ediciones existentes;
- capaz de representar una obra predominantemente textual, visual, sonora o híbrida.

## Contenido mínimo conceptual

### Manifest

Debe identificar al menos:

- identificador de edición;
- identificador de obra cuando corresponda;
- versión de edición;
- versión de App Book Format;
- título y metadatos públicos;
- idioma;
- orden de lectura;
- assets incluidos;
- capacidades habilitadas;
- checksums/integridad;
- referencias a artefactos descargables autorizados.

### Estructura editorial

Debe poder representar:

- partes;
- capítulos;
- secciones;
- bloques direccionables;
- orden y navegación;
- relaciones entre bloques y recursos.

### Citas, fuentes y bibliografía

Debe poder representar:

- cita textual;
- referencia;
- fuente;
- contexto navegable cuando esté disponible;
- relación con el bloque de origen;
- bibliografía por capítulo y global.

Esto habilita tooltips y navegación de fuentes sin incorporar lógica editorial de producción en el Reader.

### Recursos visuales

Debe poder vincular:

- ilustraciones;
- láminas;
- diagramas;
- gráficos;
- infografías;
- aperturas visuales;
- secuencias vinculadas a bloques o capítulos;
- texto alternativo/accesibilidad;
- dimensiones y metadatos requeridos para render.

### Audio

Debe poder expresar:

- pistas;
- capítulos o rangos asociados;
- sincronización texto/audio cuando exista;
- duración;
- pronunciaciones o metadata necesaria para reproducción;
- variantes autorizadas cuando corresponda.

### Actividades

Debe poder representar actividades vinculadas al contenido, incluyendo según género/producto:

- multiple choice;
- verdadero/falso;
- reflexión;
- autoevaluación;
- repaso;
- conceptos clave.

Una actividad debe poder enlazar al fragmento o concepto que la fundamenta.

### Artefactos tradicionales

Puede incluir o referenciar:

- PDF ilustrado;
- PDF imprimible;
- EPUB;
- otros derivados aprobados.

### Derechos de consumo

El formato puede expresar los metadatos de derechos necesarios para el consumo de la edición, pero no reemplaza al dominio comercial que decide compra, precio, regalías, suscripciones o liquidaciones.

## Capacidades del Reader derivadas del formato

El formato debe permitir que Reader implemente, sin consultar el kernel creativo:

```text
texto
↔ citas
↔ bibliografía
↔ ilustraciones/gráficos
↔ audio
↔ actividades
```

Esto sostiene una experiencia de lectura expandida dentro del mismo capítulo o recorrido editorial.

## Qué no debe contener

Como regla normal, App Book Format no debe exponer:

- prompts internos;
- cadenas de razonamiento;
- proveedores/modelos LLM usados;
- skills internas;
- findings editoriales internos no públicos;
- patches;
- ApprovalGate;
- historial completo de commits;
- costos de producción;
- secretos editoriales;
- credenciales;
- lógica de billing.

El Reader consume una edición aprobada, no el proceso con el que fue creada.

## Versionado y compatibilidad

La versión del formato y la versión de la edición son conceptos distintos.

```text
format_version
edition_version
```

Un nuevo release de Studio no debe obligar a recompilar todas las obras sólo por cambios internos. Un nuevo Reader debe poder determinar qué versiones del formato soporta.

Los cambios incompatibles en el formato requieren versión mayor o estrategia explícita de migración.

## Validación

Antes de publicar una edición App Book, el compilador debe poder verificar como mínimo:

- schema válido;
- referencias internas resolubles;
- orden de lectura coherente;
- assets existentes;
- checksums;
- citas/fuentes correctamente vinculadas cuando se declaran;
- audio referenciado existente;
- actividades con targets válidos;
- artefactos descargables existentes;
- versión de formato soportada.

## Relación con TR.ES Studio

Studio produce, revisa, aprueba y compila.

El `EditionCompiler` proyecta sólo lo necesario para la edición publicada. Las decisiones internas siguen en el dominio editorial.

## Relación con App Book Reader

Reader interpreta el contrato y aporta experiencia:

- navegación;
- render de texto;
- temas tipográficos;
- tooltips;
- swipe/navegación visual;
- reproducción de audio;
- actividades;
- guardados;
- offline;
- biblioteca;
- descargas autorizadas.

El formato define datos y relaciones; Reader define interacción y presentación.

## Regla de evolución

El formato debe evolucionar mediante casos reales de lectura y publicación, no por anticipación abstracta de todas las funciones futuras. Formato y Reader mínimo deben validarse juntos sobre obras reales.