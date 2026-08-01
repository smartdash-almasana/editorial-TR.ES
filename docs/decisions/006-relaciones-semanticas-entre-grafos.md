# ADR-006 — Autoridad única para relaciones semánticas entre grafos

**Estado:** Aceptado en arquitectura; implementación incremental pendiente  
**Fecha:** 2026-07-31

## Contexto

`Work` contiene `KnowledgeGraph`, `NarrativeGraph`, `ExpressionGraph` y `DependencyGraph`. Los tres primeros representan dimensiones editoriales distintas. `DependencyGraph` soporta invalidación técnica mediante relaciones genéricas registradas manualmente.

El modelo no expresa todavía, como objetos canónicos y tipados, relaciones como:

- un bloque expresa una escena;
- un bloque cita o sustenta un claim;
- una escena establece una promesa narrativa;
- un recurso visual deriva de un fragmento;
- una edición contiene una proyección de un bloque.

Guardar la misma relación dentro de varios nodos y además en `DependencyGraph` crearía autoridades contradictorias.

## Decisión

Las relaciones semánticas transversales serán objetos canónicos de dominio con una única autoridad.

Se establece la separación:

```text
SemanticRelation = verdad editorial de la relación
DependencyGraph   = proyección técnica para invalidación
```

`DependencyGraph` no se convierte en fuente de verdad semántica. Puede derivarse de relaciones que impliquen dependencia, pero no todas las relaciones semánticas deben producir invalidación.

La implementación inicial podrá materializarse como una colección o grafo especializado dentro de `Work`; el nombre físico del contenedor no altera esta decisión. Lo obligatorio es preservar una sola autoridad y evitar duplicación en campos de ambos extremos.

## Contrato mínimo de `SemanticRelation`

Cada relación debe declarar:

- ID estable;
- tenant, editorial, work y rama;
- sujeto;
- tipo de sujeto;
- predicado tipado;
- objeto;
- tipo de objeto;
- versión fuente;
- autoridad u origen de la relación;
- metadata validada;
- estado vigente o retirado.

Predicados iniciales candidatos:

```text
expresses
cites
supports
contradicts
establishes
derived_from
illustrates
```

El catálogo definitivo se incorporará por cortes productivos, no como vocabulario ilimitado inicial.

## Reglas

1. Una relación tiene una sola residencia canónica.
2. Los nodos no duplican la misma relación como listas mutables propias.
3. Las consultas inversas se resuelven mediante índices o proyecciones.
4. Una relación que implique dependencia genera o actualiza la proyección correspondiente en `DependencyGraph` dentro del mismo commit.
5. Un plugin puede declarar vocabulario semántico sólo si su categoría y namespace están autorizados por ADR-007.
6. Ningún plugin crea, elimina o enlaza relaciones fuera del flujo aplicativo gobernado.

## Consecuencias

### Positivas

- los grafos dejan de operar como silos;
- la recuperación semántica puede usar relaciones explícitas;
- la invalidación se deriva de hechos canónicos en lugar de carga manual ad hoc;
- se evita duplicar autoridad entre nodos y dependencias;
- la futura factoría visual y el compilador pueden rastrear origen semántico.

### Negativas

- aparece un nuevo concepto de dominio;
- se requieren eventos, índices y validaciones intergrafo;
- debe definirse qué predicados generan dependencia técnica.

## Alternativas rechazadas

### Usar exclusivamente `DependencyGraph`

Rechazada porque mezcla semántica editorial con propagación técnica de stale state y convierte todas las relaciones en dependencias.

### Guardar referencias en ambos nodos

Rechazada por duplicación y riesgo de divergencia.

### Incorporar una base de grafos externa

Rechazada en esta etapa. El volumen y las consultas reales no justifican Neo4j ni infraestructura equivalente.

## Criterios de aceptación

1. Una relación `expresses` entre bloque y escena se reconstruye por replay.
2. No existe una segunda lista canónica de esa relación dentro de los nodos.
3. Cuando el predicado implica dependencia, su proyección técnica se actualiza atómicamente.
4. Cambiar o retirar la relación invalida sólo los derivados correspondientes.
5. `SemanticMemory` puede recuperar contexto por relaciones sin convertirse en autoridad.
