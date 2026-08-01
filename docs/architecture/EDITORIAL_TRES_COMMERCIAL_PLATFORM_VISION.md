# Editorial TR.ES — Visión canónica de plataforma comercial

## Estado

Canónico como arquitectura de producto y dirección comercial. Los precios, porcentajes, límites de planes y tarifas concretas se consideran hipótesis comerciales hasta contar con costos operativos medidos.

## Principio

Editorial TR.ES se organiza como una sola plataforma con dos productos públicos y un contrato interno central:

```text
Editorial TR.ES
├── TR.ES Studio
│   creación / edición / producción / publicación
│
├── App Book Format
│   contrato versionado de edición
│
└── App Book Reader
    lectura / biblioteca / descubrimiento / consumo
```

La empresa controla la cadena desde la transformación editorial de una obra hasta su experiencia de lectura, sin convertir esa cadena en un único dominio técnico acoplado.

## 1. TR.ES Studio

Producto SaaS destinado a autores, editores y sellos.

Promesa de producto:

> Convertí tu manuscrito en una obra digital viva, publicable y vendible.

Capacidades comerciales previstas:

- carga de manuscrito;
- diagnóstico editorial;
- corrección ortográfica, gramatical y ortotipográfica;
- corrección de estilo;
- estructuración narrativa o argumental;
- revisión especializada por género;
- informes editoriales profesionales;
- diseño de portada, contratapa y cubierta;
- ilustraciones, diagramas, gráficos e infografías;
- producción de audio;
- creación de actividades pedagógicas;
- citas, fuentes y bibliografía;
- conversión a App Book;
- generación de PDF/EPUB y otros outputs;
- fijación de precio;
- publicación;
- analítica de producción, venta y lectura disponible para el autor.

Studio no debe exponer la complejidad interna del kernel. Un autor contrata resultados editoriales y servicios, no pipelines técnicos.

## 2. App Book Reader

Producto gratuito para lectores y runtime de las ediciones App Book.

Promesa de producto:

> Leé, escuchá, explorá y comprendé una obra como nunca antes.

Capacidades previstas:

- lectura limpia;
- selección de fuente, tamaño, interlineado y fondo;
- audio sincronizado;
- navegación por ilustraciones y gráficos vinculados;
- tooltips de citas y referencias;
- bibliografía navegable;
- actividades y preguntas;
- notas, subrayados, marcadores y citas guardadas;
- lectura offline;
- descarga de PDF autorizado;
- biblioteca personal;
- descubrimiento y marketplace.

El Reader recibe una edición aprobada. No conoce qué LLM, skill, reviewer, Patch o costo de producción intervino en su fabricación.

## 3. App Book Format

Es el contrato que desacopla producción y consumo.

No es una aplicación ni una base de datos compartida. Es un paquete estructurado, versionado y validable que representa una edición App Book aprobada.

Debe poder contener, según la edición:

- manifest;
- metadatos;
- capítulos y estructura de navegación;
- bloques de texto;
- citas y referencias;
- fuentes y bibliografía;
- ilustraciones;
- gráficos y diagramas;
- audio y sincronización;
- actividades;
- PDFs y otros artefactos asociados;
- derechos de consumo necesarios;
- versión de formato;
- versión de edición;
- checksums e integridad de assets.

La evolución del formato debe contemplar compatibilidad hacia atrás cuando corresponda, para que Reader pueda seguir consumiendo obras publicadas aunque Studio evolucione.

## Frontera de dominios

Una sola plataforma no significa un único núcleo de dominio.

### Núcleo editorial

Autoridad sobre:

- obra;
- contenido;
- conocimiento y fuentes;
- narrativa;
- expresión;
- citas;
- bibliografía;
- visuales editoriales;
- audio editorial;
- actividades;
- versiones;
- ediciones.

### Contrato App Book

Transporta una edición aprobada entre producción y consumo.

No contiene historial interno de producción salvo metadatos de procedencia requeridos por integridad, derechos o auditoría.

### Dominio comercial

Autoridad sobre:

- producto vendible;
- oferta;
- precio;
- compra;
- acceso comercial;
- derechos comerciales;
- regalías;
- ventas;
- liquidaciones;
- planes;
- suscripciones;
- créditos;
- órdenes de servicio.

Estos conceptos no pertenecen al `WorkGraph`.

### Dominio de lectura

Autoridad sobre:

- biblioteca personal;
- progreso;
- notas;
- subrayados;
- marcadores;
- preferencias;
- descargas/offline;
- actividad del lector.

### Analítica

Puede integrar métricas de:

- producción;
- conversión editorial;
- consumo de recursos;
- ventas;
- lectura;
- engagement;
- conversión comercial.

Debe mantener separación entre datos de dominio y agregados analíticos.

## Cadena de valor

```text
AUTOR
  ↓
TR.ES Studio
  ↓
producción / revisión / aprobación
  ↓
EditionCompiler
  ↓
App Book Format
  ↓
catálogo / comercio / acceso
  ↓
App Book Reader
  ↓
LECTOR
```

## Servicios editoriales comercializables

Las ofertas comerciales se montan sobre capacidades del kernel y las factorías; no se implementan como lógica paralela.

Ejemplos:

- diagnóstico inicial = composición de reviewers + síntesis de findings;
- corrección básica = reglas determinísticas + pasadas transformadoras;
- corrección de estilo = reviewer/pasada + voz autoral + aprobación;
- informe literario = composición de reviewers de género y especialidad;
- portada = brief + factoría visual + composición tipográfica determinística;
- conversión App Book = proyección/compilación de edición;
- audio = producción de activo + sincronización + edición;
- actividades = producción pedagógica asociada a bloques/conceptos.

## Modelo económico

La dirección comercial contempla tres fuentes de ingreso complementarias:

```text
suscripción SaaS
+ servicios y producción por obra / créditos
+ participación en ventas
```

Como hipótesis inicial se consideran planes desde aproximadamente US$10/mes, servicios editoriales pagos, créditos para operaciones intensivas y una participación orientativa del 12% de ventas netas. Ningún valor queda fijado como contrato económico hasta validar costos, márgenes, proveedores y carga humana real.

## Efecto de red buscado

```text
más autores
→ más obras
→ mejor catálogo
→ más lectores
→ más ventas
→ mayor atractivo para nuevos autores
```

Y:

```text
más lectores
→ más señales de lectura
→ mejores informes y decisiones editoriales
→ mejores obras
→ mayor conversión y retención
```

La analítica no debe convertirse en autoridad creativa: informa al autor/editor, no reemplaza su criterio.

## Fases comerciales previstas

### Fase 1 — Formato y lector

- definir y validar App Book Format;
- construir Reader funcional junto al formato;
- publicar las obras propias iniciales;
- demostrar la experiencia de lectura.

### Fase 2 — Studio asistido

- carga de manuscritos;
- diagnóstico;
- corrección;
- conversión semiautomática;
- portada;
- audio;
- publicación asistida;
- intervención humana fuerte donde sea necesaria.

### Fase 3 — SaaS autoservicio

- editor completo;
- catálogo de servicios;
- créditos;
- billing;
- analytics;
- regalías;
- publicación autoservicio.

### Fase 4 — Marketplace

- catálogo externo;
- recomendaciones;
- autores y sellos;
- afiliados;
- clubes;
- licencias;
- expansión de distribución.

## Identidad de marca

Arquitectura de marca recomendada:

```text
Editorial TR.ES
├── TR.ES Studio — crear, transformar y publicar
└── App Book — leer y descubrir
```

Definición resumida:

> TR.ES transforma obras. App Book transforma la lectura.

La plataforma comercial se diseña alrededor de esa dualidad sin sacrificar la separación de dominios.