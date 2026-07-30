# Workflow Engine

Motor de orquestación de flujos de trabajo editoriales.

## Responsabilidades
- Secuenciar las etapas de producción (investigación → redacción → revisión → producción visual → aprobación → exportación).
- Controlar las transiciones de estado de un proyecto según el plugin de workflow seleccionado.
- Garantizar que los pasos de aprobación humana se respeten antes de avanzar de fase.

## Limites
No toma decisiones editoriales ni ejecuta prompts directamente; coordina la secuencia de pasos invocando los componentes del kernel.
