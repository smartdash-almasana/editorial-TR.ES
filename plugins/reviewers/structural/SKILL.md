# Reviewer estructural

Reviewer determinístico que inspecciona bloques de expresión sin mutar `Work`.

Capacidades:

- detectar párrafos exactamente duplicados dentro de un bloque;
- detectar reiteraciones de frases temáticas declaradas en la configuración;
- producir `ReviewFinding` trazables contra la versión fuente.

No reescribe contenido, no crea `Patch` y no aplica cambios.
