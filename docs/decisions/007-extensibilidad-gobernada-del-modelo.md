# ADR-007 — Extensibilidad gobernada del vocabulario editorial

**Estado:** Aceptado  
**Fecha:** 2026-07-31

## Contexto

El modelo actual combina tres estrategias incompatibles:

- tipos de bloque cerrados en código;
- tipos narrativos cerrados en código;
- tipos de conocimiento y dependencias como strings libres;
- tipos de plugin cerrados y validados.

Esta asimetría obliga a modificar el kernel para algunos géneros y permite datos sin schema en otros. La arquitectura exige plugins extensibles sin permitir que redefinan invariantes.

## Decisión

Se adopta un modelo de vocabulario en dos niveles:

```text
vocabulario base del kernel
+
extensiones namespaced y autorizadas
```

### Vocabulario base

- lo define el kernel;
- es estable y versionado;
- no puede ser redefinido ni desregistrado por plugins;
- cubre las unidades universales necesarias para operar el sistema.

Ejemplos:

```text
kernel.expression.paragraph
kernel.expression.heading
kernel.narrative.part
kernel.narrative.chapter
kernel.narrative.scene
```

### Extensiones

- usan namespace del plugin propietario;
- declaran schema de datos y versión;
- se validan durante la activación de la composición;
- sólo pueden ser registradas por categorías autorizadas;
- no ejecutan código arbitrario dentro del kernel.

Ejemplos:

```text
genre.poetry.stanza
genre.novel.interlude
research.documentary.source
research.documentary.claim
```

## Permisos por categoría

- `GenrePlugin`: tipos narrativos y expresivos propios del género.
- `ResearchMethodPlugin`: tipos de conocimiento, fuente, evidencia y cita.
- `VisualTypePlugin`: tipos de activos y briefs visuales.
- `OutputPlugin`: schemas de proyección y artefactos de salida, no tipos canónicos de obra.
- `ReviewerPlugin`: findings y parámetros de diagnóstico; no vocabulario mutante de obra.
- `StylePlugin`, `AuthorVoicePlugin` y `NarratorPlugin`: restricciones y perfiles; no tipos estructurales.
- `WorkflowPlugin`: stages y gates; no tipos de nodos ni operaciones canónicas.

## Registro y validación

La composición activada deberá construir registros inmutables y scoped para:

- tipos de entidad;
- schemas de metadata;
- predicados semánticos;
- implementaciones de capacidades.

El registro pertenece al runtime de la composición activa, no a un singleton global mutable.

Una obra histórica debe conservar las versiones de vocabulario y schemas necesarias para su replay. La actualización de un plugin no reinterpreta silenciosamente datos persistidos.

## Consecuencias

### Positivas

- nuevos géneros sin modificar el kernel;
- validación al escribir, no interpretación ad hoc al leer;
- aislamiento por namespace y categoría;
- composiciones imposibles fallan antes de abrir la obra;
- los tipos base permanecen protegidos.

### Negativas

- manifests y behaviors requieren más metadata;
- se necesita versionado de schemas;
- hay que migrar gradualmente strings y conjuntos cerrados actuales.

## Decisiones rechazadas

- strings completamente libres como contrato productivo;
- un enum central que contenga todos los géneros futuros;
- permitir que cualquier plugin registre cualquier tipo;
- permitir validadores ejecutables arbitrarios suministrados por plugins;
- mutar registros globales compartidos entre proyectos.

## Criterios de aceptación

1. Un género registra un tipo namespaced autorizado sin modificar código del kernel.
2. Un plugin no puede redefinir un tipo `kernel.*`.
3. Un reviewer no puede registrar un tipo narrativo.
4. La composición falla si dos plugins reclaman el mismo namespace/tipo incompatible.
5. El schema y su versión quedan asociados a la composición que produjo los datos.
