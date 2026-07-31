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

5. `architecture/EDITORIAL_TRES_ENGINEERING_STATE.md`
   - estado real y verificado del repositorio;
   - capacidades implementadas;
   - capacidades pendientes;
   - próximo corte recomendado.

## Documentos complementarios

- `architecture/editorial-tres-arquitectura-v2.md`: evolución de la arquitectura de sistemas sobre la arquitectura creativa original.
- `architecture/neoliterary-kernel.md`: documento histórico del primer corte del kernel; no usar sus exclusiones como estado actual.
- `product/product-contract.md`: contrato de producto inicial; compatible con la definición canónica, pero menos completo.
- `decisions/`: ADRs y decisiones arquitectónicas numeradas.

## Regla de autoridad

Ante contradicción entre un documento histórico y el estado actual:

1. los invariantes se resuelven con los documentos canónicos de arquitectura;
2. la implementación existente se resuelve con `EDITORIAL_TRES_ENGINEERING_STATE.md` y el código/tests reales;
3. los ADRs conservan el contexto de decisiones específicas;
4. ninguna conversación de chat debe ser considerada fuente de verdad superior a estos documentos.
