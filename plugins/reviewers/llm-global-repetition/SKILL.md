# Revisor LLM de reiteraciones globales

Reviewer literario asistido por LLM para manuscritos divididos en múltiples bloques.

## Función

- descubre repeticiones literales, casi duplicados y ecos semánticos;
- reúne imágenes recurrentes, motivos narrativos y latiguillos posibles;
- devuelve citas textuales con `block_id` y nivel de confianza;
- verifica cada cita contra el manuscrito antes de crear un `ReviewFinding`;
- conserva la versión exacta del manuscrito y el modelo proveedor usado.

## Límites

- no modifica `Work`;
- no crea `Patch`;
- no afirma intención autoral como un hecho;
- no decide si una reiteración es correcta o defectuosa;
- no permite que un hallazgo multibloque alimente una edición simple;
- requiere decisión humana para cualquier intervención editorial.

## Configuración

La API key se toma de `GEMINI_API_KEY` por defecto. El modelo es configurable mediante el manifest y comienza con `gemini-3.6-flash`.
