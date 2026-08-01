# ORoDev — Registro gobernado de candidatos de absorción

## Estado

Registro inicial inaugurado el 2026-07-31 a partir de:

- `informe_absorcion_piezas_oro.md`;
- `informe_hallazgos_TR_ES.md`.

Los informes fuente permanecen intactos. Este registro no confirma sus afirmaciones: las convierte en hipótesis gobernadas y separa explícitamente evidencia, licencia, capacidad, categoría, prerrequisitos, riesgos y decisión.

## Regla de interpretación

En este corte no se inspeccionaron los repositorios externos ni sus licencias. Por lo tanto:

- ninguna licencia está confirmada;
- ninguna capacidad externa está reproducida;
- ninguna pieza está aceptada;
- ninguna pieza modifica el roadmap vigente;
- no se autoriza fork, incorporación de dependencia ni implementación.

## Resumen del registro

| ID | Pieza externa | Capacidad extraíble provisional | Categoría TR.ES provisional | Decisión |
|---|---|---|---|---|
| ORO-001 | `lechmazur/writing` | señales estructuradas sobre elementos narrativos | reviewer | `POSTERGAR` |
| ORO-002 | `raestrada/storycraftr` | captura gobernada de worldbuilding | pendiente: research_method / ingesta de conocimiento | `POSTERGAR` |
| ORO-003 | `andreamorgar/poesIA` | corpus y métricas estilométricas | recurso editorial + reviewer | `INVESTIGAR` |
| ORO-004 | `nayracoop/literatura-digital` | representación y exportación hipertextual | genre + output | `POSTERGAR` |
| ORO-005 | `languagetool-org/languagetool` | detección gramatical y ortográfica | reviewer | `INVESTIGAR` |
| ORO-006 | `theJayTea/WritingTools` | señales de claridad, concisión y fluidez | reviewer probabilístico | `POSTERGAR` |
| ORO-007 | `LimHyungTae/awesome-claudecode-paper-proofreading` | criterios para preservación de intención autoral | fuente metodológica / reviewer probabilístico | `POSTERGAR` |
| ORO-008 | `Awesome-Story-Generation` | taxonomía investigable de tropos y estructuras | recurso editorial / research_method | `INVESTIGAR` |

---

## ORO-001 — `lechmazur/writing`

### Pieza externa

Benchmark narrativo citado por los informes exploratorios.

### Evidencia verificada

- Evidencia actual: únicamente descripción contenida en los informes preservados.
- Repositorio examinado directamente: no.
- Versión o commit: no identificado.
- Capacidad reproducida: no.
- Afirmaciones sobre “10 elementos narrativos”: pendientes de cotejo directo.

### Licencia

- Estado: `PENDIENTE_DE_VERIFICACIÓN`.
- No se autoriza reutilización de código, datasets ni prompts hasta examinar licencia y procedencia.

### Capacidad extraíble

Hipótesis: convertir dimensiones narrativas verificables en señales estructuradas con evidencia, sin emitir un veredicto estético ni mutar `Work`.

No se acepta como capacidad extraíble:

- un score único de “calidad literaria”;
- un quality gate automático;
- evaluación opaca dependiente de un modelo externo;
- reescritura o corrección automática.

### Categoría canónica TR.ES

- Categoría provisional: `reviewer`.
- Salida obligatoria futura: `ReviewFinding`.
- Naturaleza probable: mixta o probabilística; debe distinguir señales determinísticas de `JudgeRule`.

### Prerrequisitos

- cerrar `ReviewPlan` y composición automática de `ReviewEngine`;
- formalizar `DeterministicRule` y `JudgeRule`;
- cerrar provider desacoplado, calibración, confianza y golden sets;
- verificar si las dimensiones propuestas aportan algo no cubierto por reviewers nativos.

### Riesgos

- presentar juicio editorial como métrica objetiva;
- sesgo del benchmark o de su corpus;
- duplicación de structural, continuity y rhythm reviewers;
- dependencia de prompts o modelos no gobernados;
- saturación de findings.

### Decisión

`POSTERGAR`.

Fundamento: el valor potencial existe, pero depende del corte de juicio probabilístico y de una comparación rigurosa contra capacidades nativas.

Próxima acción permitida: investigación documental aislada después de verificar repositorio y licencia.

---

## ORO-002 — `raestrada/storycraftr`

### Pieza externa

CLI de worldbuilding y escritura asistida citada por los informes exploratorios.

### Evidencia verificada

- Evidencia actual: descripciones de los informes preservados.
- Repositorio examinado directamente: no.
- Versión o commit: no identificado.
- Compatibilidad con español, persistencia y flujos reales: no verificadas.

### Licencia

- Estado: `PENDIENTE_DE_VERIFICACIÓN`.

### Capacidad extraíble

Hipótesis: capturar personajes, lugares, cronologías y reglas de mundo como propuestas estructuradas de conocimiento para una obra.

No se acepta:

- importar su pipeline completo;
- convertir una base externa en autoridad paralela a `WorkGraph`;
- alimentar supuestas memorias no canónicas;
- generar capítulos o mutar la obra sin `Patch` y aprobación.

### Categoría canónica TR.ES

- Encaje pendiente.
- Alternativas a evaluar: `research_method`, ingesta gobernada de `KnowledgeGraph` o futura pasada de constitución de obra.
- No se confirma como `workflow`: un bridge de datos no es necesariamente un workflow editorial.

### Prerrequisitos

- mutación gobernada de `KnowledgeGraph` y `NarrativeGraph`;
- relaciones semánticas tipadas;
- contrato de ingesta y procedencia;
- autoridad canónica única para worldbuilding;
- política explícita de aprobación de elementos de mundo.

### Riesgos

- segundo estado canónico fuera de TR.ES;
- duplicación entre world model y `WorkGraph`;
- importación de persistencia o IDs incompatibles;
- deuda de migración y mantenimiento de un fork;
- generación automática prematura.

### Decisión

`POSTERGAR`.

Fundamento: no existe todavía el contrato canónico necesario para incorporar worldbuilding externo sin duplicar autoridad.

---

## ORO-003 — `andreamorgar/poesIA`

### Pieza externa

Corpus poético español y posibles tareas de análisis estilométrico citados por los informes.

### Evidencia verificada

- Evidencia actual: descripción secundaria en los informes preservados.
- Corpus, procedencia, cobertura y calidad: no examinados.
- Modelos o algoritmos reutilizables: no identificados.

### Licencia

- Estado: `PENDIENTE_DE_VERIFICACIÓN`.
- Deben verificarse por separado licencia del código, licencia del corpus, derechos de los textos y condiciones de redistribución.

### Capacidad extraíble

Hipótesis doble:

1. corpus autorizado como recurso de investigación editorial;
2. métricas estilométricas determinísticas o reproducibles que produzcan señales, no parentescos autorales concluyentes.

No se acepta:

- afirmar “ADN de un autor” como hecho;
- usar similitud para atribución autoral no autorizada;
- incorporar textos sin procedencia y derechos claros;
- convertir el corpus en `AuthorMemory` de un autor específico.

### Categoría canónica TR.ES

- Recurso compartido: fuente editorial versionada, no estado de obra.
- Capacidad analítica eventual: `reviewer`.
- Puede requerir un futuro contrato de corpus o dataset, hoy no formalizado.

### Prerrequisitos

- evaluación legal y de procedencia;
- separación entre corpus editorial, AuthorMemory y WorkMemory;
- versión reproducible de métricas;
- definición de findings estilométricos sin juicio de calidad;
- pruebas sobre español y poesía contemporánea relevantes para TR.ES.

### Riesgos

- copyright y redistribución del corpus;
- falsa atribución o comparación reputacional;
- sesgo histórico, regional o de canon;
- homogeneización estética;
- métricas que no representen voz ni intención.

### Decisión

`INVESTIGAR`.

Fundamento: puede existir valor en corpus y métricas, pero primero debe resolverse procedencia, licencia y contrato de uso.

Próxima acción permitida: auditoría documental del repositorio y del corpus, sin integración.

---

## ORO-004 — `nayracoop/literatura-digital`

### Pieza externa

Herramienta de narrativa hipertextual no lineal citada por los informes.

### Evidencia verificada

- Evidencia actual: descripción de los informes preservados.
- Modelo de datos, formatos de exportación y capacidades visuales: no examinados.

### Licencia

- Estado: `PENDIENTE_DE_VERIFICACIÓN`.

### Capacidad extraíble

Hipótesis: conceptos de lexia, enlace y navegación no lineal que puedan representarse canónicamente y compilarse a una edición interactiva.

No se acepta:

- exportar desde una estructura ajena que duplique la obra;
- introducir lógica de Reader en el kernel creativo;
- tratar una app web externa como `EditionCompiler`;
- modificar la obra durante la exportación.

### Categoría canónica TR.ES

- Posible `genre` para gramática hipertextual.
- Posible `output` para compilación.
- La experiencia de lectura pertenece a App Book Format / TRES.APP, no al kernel.

### Prerrequisitos

- relaciones semánticas y navegación canónicas;
- `EditionCompiler`;
- App Book Format;
- frontera estable con TRES.APP;
- validación de edición no lineal.

### Riesgos

- mezclar producción y lectura;
- duplicar estructura narrativa;
- crear formato propietario sin contrato versionado;
- dependencia de UI o framework externo;
- accesibilidad y preservación digital.

### Decisión

`POSTERGAR`.

Fundamento: depende directamente de cortes futuros de compilación y formato de lectura.

---

## ORO-005 — `languagetool-org/languagetool`

### Pieza externa

Corrector gramatical y ortográfico citado por los informes.

### Evidencia verificada

- Evidencia actual: descripción secundaria en los informes preservados.
- Edición, versión, idiomas, reglas y modo de integración aplicables: no examinados en este registro.
- No se ha reproducido ninguna detección contra textos TR.ES.

### Licencia

- Estado: `PENDIENTE_DE_VERIFICACIÓN`.
- Debe verificarse la licencia exacta de la edición o componente que se evalúe y las condiciones de despliegue o servicio.

### Capacidad extraíble

Hipótesis: detecciones gramaticales, ortográficas y de puntuación con evidencia localizada y sugerencia opcional.

Salida futura permitida: `ReviewFinding`.

No se acepta:

- aplicación automática de reemplazos;
- presentar reglas de estilo general como mandato sobre prosa literaria;
- enviar manuscritos a servicios externos sin contrato de privacidad;
- confundir corrección normativa con preservación de voz.

### Categoría canónica TR.ES

- Categoría provisional: `reviewer` determinístico o híbrido según componente real.
- Debe operar como adapter reemplazable, no como dependencia del dominio.

### Prerrequisitos

- cerrar `ReviewPlan`;
- definir adapter y aislamiento de datos;
- establecer versión de reglas e idioma por proyecto;
- política de privacidad y ejecución local o remota;
- corpus de pruebas literarias en español;
- deduplicación con reviewers nativos.

### Riesgos

- falsos positivos deliberadamente literarios;
- normalización de voz;
- cambios de reglas entre versiones;
- licencia o términos incompatibles;
- filtración de manuscritos en integración remota;
- volumen excesivo de findings de baja relevancia.

### Decisión

`INVESTIGAR`.

Fundamento: es un candidato potencialmente útil y acotable, pero requiere verificación técnica, legal y editorial antes de aceptar su incorporación.

Próxima acción permitida: auditoría directa de una versión concreta y prueba aislada fuera del runtime productivo.

---

## ORO-006 — `theJayTea/WritingTools`

### Pieza externa

Herramienta de asistencia de escritura citada por los informes.

### Evidencia verificada

- Evidencia actual: descripción secundaria.
- Arquitectura, providers, prompts, privacidad y licencia: no examinados.
- Preservación de voz: no demostrada.

### Licencia

- Estado: `PENDIENTE_DE_VERIFICACIÓN`.

### Capacidad extraíble

Hipótesis: taxonomía de señales sobre claridad, redundancia, concisión y fluidez.

No se acepta:

- incorporar el producto completo;
- reescritura mediante provider externo;
- sugerencias sin evidencia ni trazabilidad;
- tratar preferencias de prosa general como calidad literaria universal.

### Categoría canónica TR.ES

- Posible fuente metodológica.
- Reviewer probabilístico sólo después de `JudgeRule` y provider gobernado.

### Prerrequisitos

- juicio probabilístico gobernado;
- providers desacoplados;
- trazabilidad de modelo, prompt y contexto;
- golden sets de preservación de voz;
- ReviewPlan y priorización de findings.

### Riesgos

- homogeneización;
- dependencia de modelos externos;
- prompts no reproducibles;
- privacidad;
- recomendaciones genéricas o incompatibles con la intención autoral.

### Decisión

`POSTERGAR`.

Fundamento: la propuesta depende de infraestructura probabilística expresamente posterior al núcleo actual.

---

## ORO-007 — `LimHyungTae/awesome-claudecode-paper-proofreading`

### Pieza externa

Colección o flujo de proofreading citado como referencia para preservación de voz e intención.

### Evidencia verificada

- Evidencia actual: caracterización contenida en los informes preservados.
- Naturaleza exacta del recurso, papers, prompts o código: no examinada.
- Capacidad ejecutable reutilizable: no demostrada.

### Licencia

- Estado: `PENDIENTE_DE_VERIFICACIÓN`.
- Cada recurso enlazado puede tener licencia y condiciones diferentes.

### Capacidad extraíble

Hipótesis: criterios, protocolos o corpus de evaluación para medir si una propuesta de corrección altera rasgos autorales aprobados.

No se acepta:

- “detectar filosofía del autor” como hecho objetivo;
- comparar contra una memoria no versionada;
- asignar intención mediante inferencia opaca;
- usar un reviewer como corrector.

### Categoría canónica TR.ES

- Primero: fuente metodológica de investigación.
- Eventualmente: reviewer probabilístico o guard de evaluación de patches.
- El encaje exacto queda pendiente.

### Prerrequisitos

- AuthorMemory runtime gobernada y versionada;
- separación entre voz, narrador, estilo e intención local;
- JudgeRule, calibración y escalamiento humano;
- dataset de cambios aceptados y rechazados;
- contrato de evaluación de propuestas, no de mutación.

### Riesgos

- esencialismo de voz;
- congelar la evolución autoral;
- falsa atribución de intención;
- dependencia de prompts o modelos;
- uso de materiales enlazados con licencias heterogéneas.

### Decisión

`POSTERGAR`.

Fundamento: la idea es estratégicamente relevante, pero todavía no existe el runtime canónico necesario para evaluarla sin sobreafirmar.

---

## ORO-008 — `Awesome-Story-Generation`

### Pieza externa

Colección bibliográfica sobre generación de historias citada como posible fuente de taxonomías.

### Evidencia verificada

- Evidencia actual: mención en los informes preservados.
- Papers, cobertura, actualización y taxonomías concretas: no examinados.
- No se ha identificado una implementación directamente absorbible.

### Licencia

- Estado: `PENDIENTE_DE_VERIFICACIÓN`.
- La lista, sus metadatos y cada paper deben tratarse por separado.

### Capacidad extraíble

Hipótesis: mapa bibliográfico y vocabulario investigable sobre tropos, estructuras, evaluación narrativa y métodos experimentales.

No se acepta:

- convertir una lista de papers en reviewer automáticamente;
- afirmar saturación de mercado a partir de bibliografía académica;
- importar taxonomías sin fuente, versión y definición;
- usar tropos como veredicto de originalidad.

### Categoría canónica TR.ES

- Recurso de investigación editorial.
- Posible `research_method` para construir taxonomías versionadas.
- Eventual reviewer sólo después de definir relaciones semánticas y evidencia textual.

### Prerrequisitos

- selección y lectura de fuentes primarias;
- taxonomía versionada y namespaced;
- extensibilidad gobernada del vocabulario;
- criterios claros para evidencia de un tropo;
- separación entre clasificación y juicio de calidad.

### Riesgos

- taxonomía inconsistente o superpuesta;
- dependencia de definiciones académicas heterogéneas;
- inferencias comerciales sin datos de mercado;
- sobreclasificación de obras;
- actualización permanente del corpus bibliográfico.

### Decisión

`INVESTIGAR`.

Fundamento: puede aportar conocimiento y vocabulario, pero no constituye por sí mismo una capacidad ejecutable.

Próxima acción permitida: curaduría bibliográfica y definición de una pregunta de investigación acotada.

---

## Hallazgos adicionales en espera de admisión

El informe `informe_hallazgos_TR_ES.md` también menciona, entre otros:

- `Novel-OS`;
- `automattic/harper`.

No ingresan aún como candidatos gobernados porque el documento de absorción preservado no los desarrolla con suficiente separación de capacidad. Deben usar `candidatos/PLANTILLA_CANDIDATO.md` antes de obtener ID y decisión.

## Próximo movimiento autorizado

Este registro no habilita desarrollo. El próximo movimiento sobre un candidato individual es únicamente:

```text
seleccionar candidato
→ abrir ficha propia
→ verificar repositorio y versión
→ verificar licencia
→ demostrar capacidad real
→ comparar contra TR.ES
→ actualizar decisión
```

El desarrollo principal de Editorial TR.ES continúa regido por ADR, estado de ingeniería y roadmap canónicos.
