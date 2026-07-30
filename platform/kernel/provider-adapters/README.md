# Provider Adapters

Capa de abstracción para proveedores de Inteligencia Artificial generativa.

## Responsabilidades
- Proporcionar una interfaz uniforme para invocación de LLMs y generadores de imagen.
- Implementar adaptadores específicos (e.g. Vertex AI como primer proveedor, Anthropic, OpenAI, o motores locales) sin acoplar la lógica del dominio.
- Gestionar reintentos, formato de payloads y manejo de errores de red/API.

## Limites
No toma decisiones de negocio ni define estrategias de prompt; solo ejecuta peticiones adaptando formatos.
