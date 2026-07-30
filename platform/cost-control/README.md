# Control de Costos (Cost Control)

Subsistema de supervisión, estimación y límites presupuestarios obligatorio antes de toda operación con Inteligencia Artificial.

## Responsabilidades
- Interceptar toda solicitud de inferencia antes de ser despachada al adaptador de proveedores.
- Estimar el consumo de tokens y costos económicos proyectados de la operación.
- Aplicar políticas de límites máximos, cuotas por proyecto y presupuestos pre-aprobados.
- Bloquear llamadas a APIs de IA si exceden los umbrales configurados o si falta autorización explícita.

## Limites
No modifica las instrucciones del prompt ni la lógica del dominio; actúa exclusivamente como un gatekeeper presupuestario y de auditoría de costos.
