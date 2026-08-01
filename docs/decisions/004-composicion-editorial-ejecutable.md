# ADR-004 — Composición editorial ejecutable por fases

**Estado:** Aceptado  
**Fecha:** 2026-07-31

## Contexto

El repositorio ya distingue:

- `ProjectManifest` y `PluginManifest`;
- resolución estática mediante `compose_project()`;
- activación y validación de behaviors mediante `PluginRuntime`;
- contratos de dominio `Reviewer`, `ReviewEngine` y `EditorialPass`.

Sin embargo, la composición declarativa no se traduce todavía en un plan editorial ejecutable. Las fuentes de reviewers —proyecto, género y workflow— no se reconcilian, y una composición estáticamente válida puede contener plugins que no sean activables o construibles.

## Decisión

La composición editorial se divide en cuatro fases explícitas:

```text
ProjectManifest + PluginManifest[]
→ ProjectComposition
→ ActivatedProjectComposition
→ ReviewPlan
→ ReviewEngine
```

### 1. `ProjectComposition`

Responsabilidad estática:

- resolver IDs;
- validar dependencias;
- validar compatibilidad;
- fijar orden determinista.

No construye capacidades ejecutables.

### 2. `ActivatedProjectComposition`

Responsabilidad runtime:

- activar cada plugin resuelto;
- validar su behavior;
- verificar que las capacidades requeridas existen;
- fallar antes de ejecutar una obra si la composición no puede materializarse.

### 3. `CapabilityFactoryRegistry`

Registro explícito que resuelve:

```text
implementation_id → constructor validado
```

Evita que `PluginRuntime` crezca como un switch central de implementaciones. Los plugins declaran comportamiento; no obtienen acceso directo a `Work` ni a mecanismos de mutación.

### 4. `ReviewPlanComposer`

Componente de aplicación que reconcilia, en orden determinista:

- reviewers explícitos del proyecto;
- reviewers requeridos por género;
- reviewers requeridos por workflow.

Produce un `ReviewPlan` trazable con:

- reviewer ID;
- origen de la exigencia;
- implementation ID;
- configuración;
- naturaleza determinística o probabilística;
- orden;
- motivo de inclusión.

El `ReviewPlan` construye el `ReviewEngine`; no ejecuta transformaciones ni approvals.

## Estado de implementación — 2026-08-01

Implementado y revalidado:

- IDs canónicos de reviewers requeridos por `genre.novel`;
- manifests ejecutables para `reviewer.structural`, `reviewer.continuity`, `reviewer.rhythm` y `reviewer.repetition`;
- `CapabilityFactoryRegistry` con validación de tipo de retorno, errores normalizados y registry canónico congelado;
- `ActivatedProjectComposition` y `activate_project_composition()`;
- activación de la composición estática en `composition_order`;
- descubrimiento explícito de reviewers requeridos contra `PluginRegistry`;
- deduplicación de reviewers exigidos por proyecto, género y workflow;
- verificación fail-fast de existencia, activación, implementation registrada y construcción mediante factory;
- aislamiento de la activación dentro de un `PluginRuntime` local a la operación;
- ausencia de dependencia sobre `Work`, `ReviewPlan` o `ReviewEngine` en la fase de activación.

Implementado y revalidado:

- `ReviewRequirementOrigin` con procedencia y razón tipadas;
- `ReviewPlanEntry` con orden basado en 1, reviewer ID, implementation ID, naturaleza, configuración canónica y reviewer construido;
- `ReviewPlan` inmutable con construcción de `ReviewEngine` sin ejecución;
- `ReviewPlanComposer` en capa de aplicación;
- reconciliación determinista proyecto → género → workflow;
- preservación de todos los orígenes cuando un reviewer es requerido por más de una fuente;
- rechazo de divergencias entre `ActivatedProjectComposition` y el plan;
- piloto de `genre.novel` sin wiring manual de reviewers.

ADR-004 queda implementado y cerrado hasta la construcción del `ReviewEngine`, sin ejecutar reviewers sobre `Work` durante la composición.

Evidencia final:

```text
10 passed in 3.42s
87 passed in 4.23s
232 passed in 5.74s
git diff --check: PASS
```

Los warnings LF→CRLF informados por Git son no bloqueantes y no representan errores de formato.

## Ubicación por capas

- **Dominio:** `Reviewer`, `ReviewFinding`, `ReviewEngine`, `EditorialPass`.
- **Plugins:** requisitos y behaviors declarativos.
- **Plugin runtime:** activación y validación.
- **Aplicación:** composición del plan ejecutable.

## Consecuencias

### Positivas

- separación clara entre resolución, activación y ejecución;
- fallos tempranos para composiciones imposibles;
- trazabilidad de por qué se ejecuta cada reviewer;
- incorporación de nuevas implementaciones sin modificar un switch central;
- kernel neutral respecto de géneros y manifiestos.

### Negativas

- aparece una fase adicional de composición;
- se requiere un contrato nuevo para `ReviewPlan` y errores específicos de activación/construcción.

## Decisiones rechazadas

- un `EditorialOrchestrator` omnipotente que componga reviewers, ejecute workflows, aplique patches y compile ediciones;
- construir capacidades directamente dentro de `compose_project()`;
- permitir que plugins invoquen handlers o muten `Work`;
- conectar providers antes de cerrar esta composición.

## Criterios de aceptación

1. `genre.novel` no puede activarse si exige un reviewer inexistente o no construible.
2. Proyecto, género y workflow se reconcilian sin duplicados y en orden determinista.
3. El plan registra el origen de cada reviewer.
4. El `ReviewEngine` se construye sin configuración manual en el piloto de novela.
5. Ningún reviewer modifica `Work` ni crea/aplica patches.
