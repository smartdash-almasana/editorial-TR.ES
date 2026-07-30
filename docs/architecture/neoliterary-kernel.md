# Arquitectura del Núcleo Neoliterario

## Resumen

El núcleo neoliterario de Editorial TR.ES implementa un flujo vertical
ejecutable basado en Domain-Driven Design, Event Sourcing y CQRS.

## Work como Agregado Raíz

`Work` es el agregado raíz del dominio editorial. Representa una obra
literaria en su totalidad y es el punto de entrada para todas las
mutaciones del estado de la obra.

Responsabilidades:
- Mantener la identidad enterprise (tenant_id, editorial_id, work_id)
- Contener los tres grafos especializados
- Emitir eventos de dominio ante cada mutación
- Controlar la versión del agregado
- Impedir mutaciones directas de su estado interno

## Grafos Especializados

El dominio utiliza tres grafos con semántica diferenciada:

### KnowledgeGraph
Aloja el conocimiento de la obra: conceptos, afirmaciones, fuentes,
fragmentos de fuentes, evidencias y controversias. En este corte
comienza vacío pero está preparado para alojar estos nodos.

### NarrativeGraph
Aloja la estructura narrativa: partes, capítulos, escenas, arcos,
transiciones, promesas y líneas temporales. Valida integridad
jerárquica, ausencia de ciclos y orden determinista.

### ExpressionGraph
Aloja la expresión textual mediante `ContentBlock`: párrafos,
encabezados, diálogos, citas, poemas y notas. Cada bloque tiene
tipo, contenido, estado y metadatos.

## Evento como Cambio Atómico

Cada mutación del agregado se representa como un `DomainEvent`
inmutable que captura:
- Qué cambió (event_type)
- Cuándo cambió (occurred_at)
- Quién lo cambió (actor_id)
- El estado resultante (payload)

## Commit como Conjunto Coherente

`EditorialCommit` agrupa eventos relacionados en una unidad
transaccional. Un commit:
- Tiene una rama (branch)
- Apunta a un commit padre (parent_commit_id)
- Contiene al menos un evento
- Incluye un mensaje descriptivo

## Proyección como Vista de Lectura

`CurrentWorkProjection` mantiene una vista de lectura optimizada
para consultas, independiente del agregado. Se actualiza aplicando
eventos de dominio sin guardar referencias mutables al agregado.

## Por Qué No Git como Motor Runtime

Git es un sistema de control de versiones diseñado para código
fuente, no para dominio editorial. Las razones para no usar Git
como motor runtime incluyen:

1. **Semántica de dominio**: Los commits editoriales tienen reglas
   específicas de versión, estado y grafos que Git no conoce.
2. **Event Sourcing**: El sistema requiere replay de eventos para
   reconstruir estado, no diffs de archivos.
3. **Proyecciones CQRS**: Las vistas de lectura se construyen
   aplicando eventos, no leyendo archivos.
4. **Idempotencia**: Los comandos deben ser idempotentes, lo cual
   requiere tracking de idempotency keys.
5. **Validación de dominio**: Los grafos tienen reglas de integridad
   que Git no puede validar.

## Qué Queda Fuera de Este Corte

Este corte (Corte 1) implementa únicamente el flujo vertical de
creación de obra. Quedan fuera:

- DependencyGraph
- Invalidación de caché
- Patch Engine
- Integración con IA
- Sistema de Vertex
- Control de costos
- Frontend
- API REST/GraphQL
- Persistencia PostgreSQL
- Workers asíncronos
- Autenticación y autorización
- Funcionalidades SaaS
- Factoría visual
- Compiladores de salida
