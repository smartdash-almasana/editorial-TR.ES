# Arquitectura General — Editorial TR.ES

## Visión de la Plataforma

Editorial TR.ES es una fábrica editorial modular, extensible y automatizada, diseñada para constituir, investigar, redactar, revisar, ilustrar y empaquetar obras literarias de alta calidad. 

La arquitectura desacopla estrictamente el núcleo técnico de la plataforma (*kernel*) de los conocimientos específicos del dominio editorial, los cuales se empaquetan como **plugins enchufables**.

---

## Flujo General de Trabajo

```text
Proyecto editorial
→ composición de plugins
→ investigación
→ manuscrito
→ revisiones
→ producción visual
→ aprobación humana
→ paquete de publicación
→ TRES u otro canal
```

---

## Conceptos Arquitectónicos Incorporados

La plataforma integra conceptualmente los siguientes patrones clave:

1. **Inkwell (Proyectos Markdown):** Las obras residen como proyectos en formato Markdown estructurado, legibles y editables por humanos sin herramientas propietarias.
2. **STORM (Investigación Separada):** La recolección de fuentes, notas y contexto se gestiona de forma independiente a la redacción del texto final para evitar alucinaciones y mantener rigor documental.
3. **Scriptorium (Manuscript State):** El manuscrito cuenta con un subsistema de estado persistente, versionado e incremental que rastrea la evolución del texto.
4. **Voice Fingerprint (Voz Autoral):** Perfiles estilísticos y de tono derivados de corpus literarios preexistentes, empaquetados en plugins de voz.
5. **WRITING.md (Manuales y Políticas de Estilo):** Definición explícita de reglas ortotipográficas, ritmo y transformaciones del texto.
6. **Vale & Slopless (Revisión Determinista Anti-LLM):** Motor de reglas linters y filtros lingüísticos deterministas que detectan muletillas de IA (*slop*), clichés y fallas de estilo antes o durante la revisión.
7. **Writing Intelligence (Review Ledger):** Un registro inmutable (*ledger*) de todas las observaciones, revisiones y decisiones editoriales, asegurando trazabilidad completa.
8. **Smart Connections (Memoria Semántica Local):** Red de conexiones semánticas y contexto almacenada localmente en Markdown/vectores locales, manteniéndose fuera del runtime SaaS y preservando la privacidad del conocimiento editorial.
9. **Fabric (Patrones y Orquestación de Prompts):** Modulación modular y reutilizable de patrones de prompting inyectados con contexto y restricciones constitucionales.

---

## Sub-sistemas Principales

- **Kernel:** Subsistemas neutros de estado, orquestación, plugins, prompts, auditoría, fuentes, paquetes y adaptadores.
- **Factoría Literaria:** Generación y refinamiento de prosa y estructura narrativa.
- **Factoría Visual:** Unidad central de producción de infografías, láminas, portadas e ilustraciones con separación estricta entre el arte generativo y la composición tipográfica/vectorial.
- **Control de Costos:** Interceptor presupuestario que evalúa y limita el uso de tokens y costo económico antes de cualquier llamada a proveedores de IA.
