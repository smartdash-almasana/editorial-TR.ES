# Plugins Editoriales

Directorio de módulos enchufables que definen los aspectos de contenido, estilo, reglas y entregables de la plataforma Editorial TR.ES.

## Estructura Típica de un Plugin

Un plugin individual podrá contener los siguientes elementos:

```text
plugin.yaml
SKILL.md
prompts/
rules/
schemas/
examples/
counterexamples/
fixtures/
tests/
```

## Composición por Proyecto

Cada proyecto editorial seleccionará y compondrá sus plugins mediante una estructura conceptual similar a:

```yaml
genre:      # Plugin de género literario
voice:      # Plugin de voz autoral (Voice Fingerprint)
narrator:   # Plugin de voz narrativa
styles:     # Plugins de estilos y normas (WRITING.md)
reviewers:  # Plugins de revisores deterministas/IA (Vale, Slopless)
visuals:    # Plugins de identidad y artefactos visuales
workflow:   # Plugin de proceso y ciclo de vida
outputs:    # Plugins de formato de salida y exportación
```

*Nota: El esquema final y formal de declaración de plugins se definirá en fases posteriores.*

## Categorías de Plugins

- `genres/`: Géneros literarios y sus estructuras narrativas específicas.
- `voices/`: Perfiles y huellas de voz autoral (*Voice Fingerprint*).
- `narrators/`: Tipos de narradores y perspectivas (primera persona, omnisciente, etc.).
- `styles/`: Normas estilísticas y manuales de redacción (*WRITING.md*).
- `reviewers/`: Reglas deterministas de revisión, higiene lingüística y anti-patrones (*Vale*, *Slopless*).
- `visuals/`: Estilos gráficos, bibliotecas de assets y paletas visuales.
- `workflows/`: Definiciones de ciclos de vida de proyecto y secuencias de aprobación.
- `outputs/`: Formateadores y preparadores de entregables (PDF, app-book, etc.).
