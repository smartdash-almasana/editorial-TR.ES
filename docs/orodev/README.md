# ORoDev — Hallazgos y candidatos de absorción

## Estado

Espacio documental gobernado para registrar hallazgos externos con posible valor para Editorial TR.ES.

Fecha de inauguración: 2026-07-31.

Este directorio no es autoridad arquitectónica ni autoriza implementación. Su función es conservar descubrimientos, separar evidencia de hipótesis y preparar decisiones posteriores sin contaminar el roadmap canónico.

## Autoridad documental

El orden de autoridad es:

```text
ADR y arquitectura canónica
→ estado de ingeniería verificado
→ roadmap autorizado
→ registro gobernado de candidatos
→ informes exploratorios preservados
```

Por lo tanto:

- un hallazgo no es una capacidad;
- una herramienta externa no es un plugin TR.ES;
- una idea prometedora no altera el roadmap;
- una decisión `ACEPTAR` no autoriza implementación inmediata;
- toda incorporación debe abrirse después como capacidad acotada, con contrato, implementación y pruebas.

## Fuentes preservadas

Los documentos exploratorios originales se conservan sin modificación:

- `informe_hallazgos_TR_ES.md`;
- `informe_absorcion_piezas_oro.md`.

Contienen hipótesis, comparaciones y propuestas preliminares. Deben leerse como material de descubrimiento, no como descripción verificada del producto ni del estado técnico.

## Flujo gobernado

Todo candidato debe recorrer:

```text
pieza externa
→ evidencia verificada
→ licencia
→ capacidad extraíble
→ categoría canónica TR.ES
→ prerrequisitos
→ riesgos
→ decisión
```

No se permite omitir campos ni reemplazar evidencia con entusiasmo estratégico.

## Decisiones permitidas

### `ACEPTAR`

La capacidad externa tiene evidencia suficiente, encaje arquitectónico claro, licencia compatible y prerrequisitos satisfechos. La aceptación sólo habilita proponer un corte futuro; no autoriza implementación automática.

### `INVESTIGAR`

Existe una hipótesis razonable de valor, pero faltan verificaciones sobre repositorio, algoritmo, licencia, calidad, datos, seguridad o encaje arquitectónico.

### `RECHAZAR`

La pieza contradice invariantes, no aporta capacidad diferenciada, tiene licencia incompatible, riesgo inaceptable o costo superior al valor.

### `POSTERGAR`

El valor potencial existe, pero depende de capacidades canónicas todavía no cerradas o queda fuera del roadmap vigente.

## Evidencia mínima

Antes de pasar un candidato a `ACEPTAR` deben existir, como mínimo:

1. repositorio y versión o commit examinados;
2. licencia identificada y evaluada;
3. capacidad concreta separada del producto externo completo;
4. comparación con capacidades nativas existentes;
5. categoría canónica TR.ES confirmada;
6. prerrequisitos técnicos satisfechos;
7. riesgos de seguridad, mantenimiento, datos y dependencia documentados;
8. estrategia de adaptación sin duplicar autoridad ni introducir mutación silenciosa;
9. decisión explícita con responsable y fecha.

## Estructura

```text
docs/orodev/
├── README.md
├── REGISTRO_CANDIDATOS_ABSORCION.md
├── informe_hallazgos_TR_ES.md
├── informe_absorcion_piezas_oro.md
└── candidatos/
    └── PLANTILLA_CANDIDATO.md
```

Cuando un candidato requiera investigación profunda, debe obtener un archivo propio dentro de `candidatos/` usando la plantilla canónica.

## Fronteras no negociables

Ningún candidato puede:

- sustituir `Work` o `WorkGraph` como autoridad;
- mutar una obra fuera de `Patch → ApprovalGate → aplicación`;
- permitir que un reviewer reescriba;
- convertir memoria, corpus, embedding o herramienta externa en segunda fuente de verdad;
- introducir providers o juicio probabilístico antes de sus prerrequisitos canónicos;
- mezclar Reader, comercio, billing o marketplace con el kernel creativo;
- alterar el roadmap por el solo hecho de aparecer en este registro.
