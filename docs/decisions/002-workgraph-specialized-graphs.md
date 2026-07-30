# ADR-002: Grafos Especializados para el Dominio Editorial

## Estado

Aceptado (Corte 1)

## Contexto

El dominio editorial requiere representar tres dimensiones
fundamentales de una obra literaria:

1. **Conocimiento**: Conceptos, fuentes, evidencias, controversias.
2. **Narrativa**: Estructura jerárquica (partes, capítulos, escenas).
3. **Expresión**: Bloques de contenido textual (párrafos, diálogos).

## Decisión

Implementar tres clases de grafo separadas con semántica específica
en lugar de un grafo genérico:

- `KnowledgeGraph` para el conocimiento de la obra
- `NarrativeGraph` para la estructura narrativa
- `ExpressionGraph` para la expresión textual

### Consecuencias

**Positivas:**
- Cada grafo puede tener sus propias reglas de validación
- Los nodos tienen tipos específicos con campos relevantes
- La serialización es más clara y auto-documentada
- El código es más mantenible y extensible

**Negativas:**
- Tres implementaciones en lugar de una
- Mayor cantidad de código inicial

## Alternativas Consideradas

### Grafo Genérico
Un único `Graph` con nodos genéricos. Rechazado porque:
- Las reglas de validación son muy distintas entre dimensiones
- Los campos de los nodos son diferentes
- La semántica se pierde en un modelo genérico
- Las extensiones futuras serían más difíciles

### Grafo Relacional
Usar tablas SQL en lugar de grafos en memoria. Rechazado porque:
- El Corte 1 usa Event Sourcing en memoria
- Los grafos son parte del estado del agregado
- La persistencia se delega al Event Store

## Implementación

```python
class KnowledgeGraph(BaseGraph):
    work_id: WorkId
    nodes: Dict[str, KnowledgeNode]

class NarrativeGraph(BaseGraph):
    work_id: WorkId
    nodes: Dict[str, NarrativeNode]
    # Valida: ciclos, padres, orden

class ExpressionGraph(BaseModel):
    work_id: WorkId
    blocks: Dict[str, ContentBlock]
    # Valida: contenido, tipos, estados
```

## Reglas de Validación

### KnowledgeGraph
- IDs únicos
- Padre existente
- Preparado para nodos de conocimiento

### NarrativeGraph
- IDs únicos
- Padre existente
- Sin ciclos jerárquicos
- Posición no negativa
- Orden determinista

### ExpressionGraph
- IDs únicos
- Padre existente
- Contenido no vacío (salvo headings)
- Tipos permitidos: paragraph, heading, dialogue, quote, poem, note
- Estados: draft, revised, approved
