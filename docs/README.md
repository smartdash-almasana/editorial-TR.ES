# Documentación — Editorial TR.ES

Este directorio contiene la documentación autoritativa del producto y su arquitectura.

## Orden de lectura recomendado

1. `architecture/EDITORIAL_TRES_PRODUCT_DEFINITION.md`
   - definición de producto;
   - doble factoría literaria/visual;
   - agnosticismo de género;
   - frontera con TRES.APP.

2. `architecture/EDITORIAL_TRES_CREATIVE_KERNEL.md`
   - invariantes del kernel creativo;
   - WorkGraph, pasadas, Patch, ApprovalGate, ReviewFinding, commits e invalidación.

3. `architecture/EDITORIAL_TRES_PLUGIN_MODEL.md`
   - categorías de plugins;
   - responsabilidades;
   - límites que ningún plugin puede violar.

4. `architecture/EDITORIAL_TRES_LITERARY_AND_VISUAL_FACTORIES.md`
   - relación entre producción literaria y visual;
   - visual briefs, composición determinística, sincronización y EditionCompiler.

5. `architecture/APP_BOOK_FORMAT_CONTRACT.md`
   - contrato versionado entre Studio y Reader;
   - contenido estructurado de una edición App Book;
   - compatibilidad, validación y límites de exposición.

6. `architecture/EDITORIAL_TRES_COMMERCIAL_PLATFORM_VISION.md`
   - TR.ES Studio, App Book Format y App Book Reader;
   - servicios editoriales comercializables;
   - fronteras entre núcleo editorial, comercio, lectura y analítica;
   - fases comerciales.

7. `architecture/EDITORIAL_TRES_ENGINEERING_STATE.md`
   - estado real y verificado del repositorio;
   - capacidades implementadas;
   - capacidades pendientes;
   - próximo corte recomendado.

8. `architecture/EDITORIAL_TRES_ENTERPRISE_ROADMAP.md`
   - secuencia canónica de cortes de ingeniería;
   - criterios de cierre y prerrequisitos;
   - decisiones explícitamente postergadas;
   - control antideriva antes de modificar runtime.

## Documentos complementarios

- `architecture/editorial-tres-arquitectura-v2.md`: evolución de la arquitectura de sistemas sobre la arquitectura creativa original.
- `architecture/neoliterary-kernel.md`: documento histórico del primer corte del kernel; no usar sus exclusiones como estado actual.
- `product/product-contract.md`: contrato de producto inicial; compatible con la definición canónica, pero menos completo.
- `decisions/`: ADRs y decisiones arquitectónicas numeradas.
  - ADR-004: composición editorial ejecutable por fases;
  - ADR-005: operaciones editoriales tipadas dentro de `Patch`;
  - ADR-006: autoridad única para relaciones semánticas entre grafos;
  - ADR-007: extensibilidad gobernada del vocabulario editorial;
  - ADR-008: evolución segura del event stream y observabilidad separada.

## Regla de autoridad

Ante contradicción entre un documento histórico y el estado actual:

1. los invariantes se resuelven con los documentos canónicos de arquitectura;
2. la implementación existente se resuelve con `EDITORIAL_TRES_ENGINEERING_STATE.md` y el código/tests reales;
3. los ADRs conservan el contexto de decisiones específicas;
4. ninguna conversación de chat debe ser considerada fuente de verdad superior a estos documentos.
