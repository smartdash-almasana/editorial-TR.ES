# Contrato de producto — Editorial TR.ES

## Definición

Editorial TR.ES es una plataforma privada de creación literaria y visual, diseñada para concebir obras originales y convertirlas tanto en experiencias app-book como en formatos de lectura tradicionales.

## Propósito

La plataforma debe permitir:

* investigar y organizar fuentes;
* diseñar la arquitectura de una obra;
* escribir y revisar manuscritos;
* preservar voces autorales;
* incorporar voces narrativas;
* combinar géneros y estilos enchufables;
* producir infografías, láminas, ilustraciones y diagramas;
* aprobar versiones editoriales;
* compilar una misma obra en múltiples formatos.

## Principio de fuente única

No se escribirá una versión independiente para cada formato.

Una única obra estructurada deberá alimentar:

* app-book;
* libro impreso;
* PDF ilustrado;
* PDF de lectura;
* EPUB;
* Kindle;
* audiolibro;
* piezas visuales derivadas.

## Dos factorías centrales

### Factoría literaria

Compone de forma enchufable:

* género;
* voz autoral;
* voz narrativa;
* estilo;
* reglas editoriales;
* revisores;
* fuentes;
* workflow.

### Factoría visual

Produce:

* infografías;
* láminas;
* ilustraciones;
* diagramas conceptuales;
* portadas;
* aperturas de capítulos;
* secuencias visuales;
* piezas pedagógicas.

La generación visual podrá utilizar modelos de Vertex AI, pero la tipografía, la ortografía y la composición editorial final no deben depender exclusivamente del generador de imágenes.

## Arquitectura modular

Los géneros, voces, narradores, estilos, revisores, workflows, visuales y formatos de salida deben incorporarse mediante plugins versionados.

Un plugin no será solamente un prompt. Podrá incluir:

* manifiesto;
* skill;
* prompts;
* reglas;
* schemas;
* ejemplos;
* contraejemplos;
* fixtures;
* tests.

## Relación con TRES

Editorial TR.ES produce, revisa y aprueba las obras.

TRES recibe paquetes de publicación aprobados y permite:

* catalogarlos;
* distribuirlos;
* leerlos como app-book;
* visualizar recursos;
* descargar formatos tradicionales.

La fórmula editorial privada no debe formar parte del repositorio TRES.

## Fuera de alcance actual

Por ahora no se construyen:

* SaaS;
* multi-tenant;
* suscripciones;
* facturación;
* marketplace;
* administración comercial;
* cuentas de múltiples editoriales.

## Primer resultado operativo

La primera versión deberá completar este circuito:

```text
proyecto literario
→ composición de género, voz y estilo
→ manuscrito
→ revisión
→ brief visual
→ generación y composición visual
→ aprobación
→ paquete app-book
→ PDF o EPUB tradicional
```

## Criterio rector

Toda decisión técnica deberá responder a esta pregunta:

> ¿Ayuda a producir una obra literaria y visual original, preservarla y publicarla coherentemente en múltiples formatos?

Si no contribuye directamente a ese objetivo, queda fuera del alcance inicial.
