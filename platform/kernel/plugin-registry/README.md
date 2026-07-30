# Plugin Registry

Registro y motor de descubrimiento de plugins de la plataforma.

## Responsabilidades
- Cargar, validar y verificar la compatibilidad de plugins (géneros, voces, revisores, estilos, visuales, etc.).
- Componer la configuración activa para un proyecto según su manifiesto de plugins.
- Validar las reglas y contratos expuestos en cada `plugin.yaml`.

## Limites
No define el contenido de los plugins; solo gestiona su ciclo de vida y resolución dentro del sistema.
