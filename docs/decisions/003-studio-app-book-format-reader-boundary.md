# ADR-003 — TR.ES Studio, App Book Format y App Book Reader

**Estado:** Aceptado  
**Fecha:** 2026-07-30

## Contexto

La arquitectura inicial separó la fábrica editorial del producto de lectura/publicación. La evolución comercial aclaró que la plataforma tendrá dos productos públicos —uno para autores y otro para lectores— y necesita un contrato estable que desacople producción y consumo.

Sin ese contrato, Studio y Reader tenderían a compartir modelos internos, base de datos o estructuras privadas, dificultando evolución, compatibilidad y publicación de largo plazo.

## Decisión

Editorial TR.ES adopta esta topología de producto:

```text
Editorial TR.ES
├── TR.ES Studio
├── App Book Format
└── App Book Reader
```

### TR.ES Studio

Producto SaaS para autores, editores y sellos. Orquesta capacidades editoriales, visuales y de compilación para transformar manuscritos en ediciones aprobadas y publicables.

### App Book Format

Contrato estructurado, versionado y validable de una edición App Book aprobada. Desacopla Studio del Reader.

### App Book Reader

Aplicación de lectura y biblioteca. Consume App Book Format y aporta interacción, reproducción, offline, guardados, actividades y descubrimiento.

## Fronteras

No se define un único núcleo compartido para editorial, comercio y lectura.

Se mantienen separados:

- núcleo editorial;
- contrato App Book;
- dominio comercial;
- dominio de lectura;
- analítica.

Precio, compras, regalías, suscripciones, créditos y ventas no forman parte del `WorkGraph`.

El Reader no recibe prompts, modelos, skills, findings, patches, ApprovalGates ni costos internos de producción.

## Compatibilidad con ADR-000

ADR-000 sigue vigente en su principio central: la fórmula editorial interna permanece separada del runtime de lectura y sólo se publican ediciones aprobadas.

Esta ADR refina la frontera previa:

```text
antes:
Editorial Factory → paquete de publicación → TRES

ahora:
TR.ES Studio → App Book Format → App Book Reader
```

Las responsabilidades de comercio, catálogo y marketplace deben mantenerse como dominio separado aunque puedan presentarse dentro de la experiencia de Studio o Reader.

## Consecuencias

- `EditionCompiler` debe producir un artefacto App Book estructurado, no UI específica.
- App Book Format necesita versionado y validación propios.
- Studio y Reader pueden evolucionar independientemente dentro de compatibilidad declarada.
- las obras publicadas no dependen del proveedor LLM ni de la implementación interna que las produjo;
- el SaaS comercial puede desarrollarse progresivamente sin contaminar el kernel creativo;
- la fase inicial debe validar Format y Reader juntos sobre obras reales.