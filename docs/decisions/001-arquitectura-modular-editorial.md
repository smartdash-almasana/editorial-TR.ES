# ADR-001 — Arquitectura Modular Editorial de Editorial TR.ES

**Estado:** Aceptado  
**Fecha:** 2026-07-30

---

## Contexto

Editorial TR.ES requiere constituirse como una fábrica editorial capaz de procesar múltiples obras, géneros, voces autorales, estilos de revisión y formatos de publicación (manuscritos, libros ilustrados, infografías, paquetes app-book, etc.). Se requiere una arquitectura modular, extensible, mantenible y protegida frente a cambios en los proveedores de IA o acoplamiento con plataformas de distribución.

---

## Decisiones Principales

### 1. Núcleo Editorial Neutral
El núcleo de la plataforma (`platform/kernel/`) es estrictamente agnóstico a cualquier género literario, autor o temática particular. Sus responsabilidades se limitan a la gestión del estado del manuscrito, la orquestación de flujos, el registro de auditoría y la interfaz con adaptadores.

### 2. Plugins Enchufables
Toda la variabilidad editorial se implementa mediante módulos enchufables (`plugins/`):
- `genres/`: estructuras por género.
- `voices/`: huellas de voz autoral (*Voice Fingerprint*).
- `narrators/`: perspectivas narrativas.
- `styles/`: manuales de estilo (*WRITING.md*).
- `reviewers/`: reglas linters deterministas (*Vale*, *Slopless*).
- `visuals/`: estilos gráficos y bibliotecas tipográficas.
- `workflows/`: ciclos de vida y estados de aprobación.
- `outputs/`: formateadores de salida.

### 3. Factoría Literaria
Unidad de producción dentro de la plataforma dedicada exclusivamente al desarrollo de la prosa, estructuración de capítulos y pulido textual conforme a los plugins de género, voz y estilo seleccionados.

### 4. Factoría Visual
Unidad de producción de primer nivel (central, no accesoria) encargada de infografías, láminas, portadas, ilustraciones y recursos para PDF y app-books. Separa rigurosamente el pipeline de producción (análisis conceptual → brief → generación → composición tipográfica → validación → aprobación → exportación). La composición de texto e infografía no depende exclusivamente de los modelos generativos de imágenes, sino de una capa tipográfica y vectorial independiente.

### 5. Adaptadores de Proveedores de IA
Toda interacción con Inteligencia Artificial generativa se canaliza a través de adaptadores (`platform/kernel/provider-adapters/`). Vertex AI será el primer proveedor integrado, pero la lógica de negocio no tiene conocimiento ni acoplamiento directo con sus APIs o SDKs específicos.

### 6. Control de Costos Obligatorio
Se establece un subsistema de control de costos (`platform/cost-control/`) que evalúa tokens, presupuestos y límites económicos pre-operación. Ninguna llamada a un proveedor de IA puede ejecutarse sin la validación presupuestaria previa de este subsistema.

### 7. Separación Respecto de TRES
Editorial TR.ES y TRES son repositorios y sistemas totalmente independientes. Editorial TR.ES produce, revisa y empaqueta obras aprobadas; TRES actúa como un consumidor externo que recibe dichos paquetes para su catálogo, publicación y lectura.

### 8. Fórmula Editorial Privada
La constitución editorial (`constitution/`), manuales de estilo internos, reglas deterministas y patrones de prompts constituyen la fórmula editorial privada del repositorio. Ninguna regla ni prompt puede violar la constitución universal.

### 9. Preparación Futura para SaaS
Aunque se inicia como un entorno de ejecución local guiado por Git y Markdown, la separación clara por subsistemas, contratos JSON/YAML y aislamiento de plugins prepara la plataforma para su futura exposición como servicio multi-tenant o SaaS.

---

## Qué NO se implementa todavía

En esta etapa inicial **no** se implementa:
- Frameworks web ni runtime de aplicación frontend/backend.
- Conexión real a servicios en la nube (Google Cloud, Vertex AI, etc.).
- Motores de bases de datos relacionales o vectoriales.
- Ejecución activa de linters ni agentes de IA.
- Proyectos literarios o contenido de producción real.

---

## Consecuencia

Se logra una base de arquitectura limpia, extensible y libre de deuda técnica de acoplamiento, estableciendo límites claros entre el kernel, los plugins, los proveedores de IA y los canales de distribución externos.
