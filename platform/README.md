# Platform

Núcleo técnico de Editorial TR.ES. Contiene los subsistemas de ejecución, orquestación, factorías de producción y control de costos.

## Estructura

- `kernel/`: Subsistemas fundamentales (estado del manuscrito, motor de flujo, registro de plugins, runtime de prompts, ledger de revisión, gestión de fuentes, paquetes de publicación y adaptadores de proveedores).
- `factories/`: Factorías de producción especializadas (`literary` para manuscritos y `visual` para artefactos gráficos).
- `cost-control/`: Sistema de supervisión, estimación y límites de costos/tokens pre-operación de IA.

## Responsabilidades y Límites

La plataforma es agnóstica de los contenidos editoriales y géneros específicos. Ejecuta flujos de trabajo orquestando plugins y adaptadores bajo las reglas definidas en `constitution/`.
