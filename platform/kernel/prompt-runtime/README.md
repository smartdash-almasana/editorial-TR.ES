# Prompt Runtime

Entorno de ejecución y composición de patrones de interacción con modelos (inspirado en patrones tipo Fabric).

## Responsabilidades
- Inyectar contexto, reglas de la constitución y directivas del plugin en las plantillas de prompts.
- Gestionar la estructuración de entradas y salidas para llamadas a LLMs.
- Aplicar filtros de cumplimiento normativo y constitución sobre las instrucciones enviadas al proveedor.

## Limites
No se conecta directamente a APIs específicas de IA; utiliza `provider-adapters` para el envío final.
