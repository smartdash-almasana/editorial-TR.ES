# Kernel (Núcleo Técnico)

Subsistemas centrales agnósticos a la temática editorial. Encargados de mantener el estado, orquestar flujos de trabajo, gestionar plugins y garantizar la trazabilidad.

## Componentes

- `manuscript-state/`: Gestión del estado persistente e incremental del manuscrito (inspirado en el concepto de *Scriptorium*).
- `workflow-engine/`: Motor determinista de orquestación de fases de producción y revisión.
- `plugin-registry/`: Descubrimiento, validación y carga dinámica de plugins.
- `prompt-runtime/`: Ejecución, formateo y composición de patrones de prompting (inspirado en patrones tipo *Fabric*).
- `review-ledger/`: Registro inmutable y trazable de revisiones, sugerencias y aprobaciones (concepto *Writing Intelligence*).
- `source-management/`: Gestión de fuentes, investigación y notas de contexto separadas de la redacción (concepto *STORM*).
- `publication-packages/`: Ensamblado de artefactos y generación de paquetes finales listos para consumo (TRES u otros distribuidores).
- `provider-adapters/`: Abstracción de modelos y proveedores de IA (Vertex AI, Anthropic, OpenAI, locales).
