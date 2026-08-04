---
title: "Ingeniería de Audiolibros — Editorial TR.ES"
document_id: "TR.ES-AUDIO-ENGINEERING"
version: "1.0"
status: "Arquitectura objetivo con implementación parcial"
updated: "2026-08-03"
language: "es"
---

# Ingeniería de Audiolibros — Editorial TR.ES

## 1. Propósito

Este documento define la arquitectura, el flujo de producción, el modelo de dominio y los criterios de calidad de la **Factoría Sonora de Editorial TR.ES**.

El objetivo no es solamente convertir texto en voz. El sistema debe producir audiolibros editoriales:

- trazables hasta la edición aprobada;
- segmentados;
- revisables;
- regenerables;
- versionados;
- sincronizables con App Book;
- exportables a formatos estándar;
- independientes de un único proveedor de voz;
- capaces de integrar narración sintética y humana.

La unidad real de producción no será el audiolibro completo, sino el **segmento narrado**.

## 2. Principio rector

> Un audiolibro profesional no debe generarse como un archivo único. Debe construirse como una colección de segmentos versionados, revisables, regenerables y finalmente ensamblados.

La edición escrita aprobada continúa siendo la fuente de verdad editorial.

La versión narrada puede adaptar el texto para una lectura oral correcta, pero nunca debe modificar silenciosamente la edición maestra.

## 3. Alcance

La Factoría Sonora debe cubrir el siguiente recorrido:

```text
Edición aprobada
        ↓
Preparación del texto narrado
        ↓
Definición de narración
        ↓
Diccionario de pronunciaciones
        ↓
Segmentación
        ↓
Generación de tomas
        ↓
Validación automática
        ↓
Revisión humana
        ↓
Alineación texto–audio
        ↓
Ensamblado del audiolibro
        ↓
Publicación y consumo en App Book
```

### 3.1 Incluido

- definición editorial de la narración;
- configuración de narrador, tono, ritmo y estilo;
- diccionario de pronunciaciones;
- preparación del texto hablado;
- segmentación por límites semánticos;
- generación de una o varias tomas por segmento;
- validación automática del audio generado;
- aprobación, rechazo y regeneración;
- reconstrucción por eventos;
- persistencia;
- aislamiento por obra y rama;
- ensamblado por capítulos;
- M4B;
- MP3 por capítulos;
- manifiesto de sincronización para App Book;
- metadatos editoriales;
- integración futura con motores locales o externos.

### 3.2 Fuera de alcance inicial

- estudio completo de audio profesional;
- edición multipista avanzada;
- doblaje cinematográfico;
- actuación coral compleja;
- mezcla musical;
- distribución comercial automática en plataformas externas;
- gestión contractual de narradores humanos;
- entrenamiento propio de modelos de voz.

## 4. Estado actual verificado

Al cierre de este documento, la plataforma ya cuenta con una primera base funcional para Factoría Sonora.

### 4.1 Implementado

- modelos de dominio para narración;
- `NarrationBrief`;
- `PronunciationEntry`;
- eventos tipados y serializables;
- persistencia en el Event Store existente;
- reconstrucción mediante `AudioProjection`;
- integración con `compose_application`;
- aislamiento entre obras;
- control de versión;
- idempotencia;
- reinicio y reconstrucción con `SQLiteEventStore`;
- pruebas focales de Factoría Sonora;
- suite completa de plataforma en verde.

### 4.2 Validación registrada

```text
Pruebas focales de audio: 9 aprobadas
Suite completa: 427 aprobadas
Guard de tarea activa: aprobado
Persistencia SQLite: aprobada
Aislamiento entre obras: aprobado
Conflicto de versión: aprobado
```

### 4.3 Próximo corte pendiente

El siguiente corte de implementación debe ser:

```text
AudioSegment persistido
```

Todavía no corresponde integrar motores reales de voz hasta cerrar correctamente el modelo persistido de segmentos.

## 5. Principios de diseño

### 5.1 La edición aprobada es la fuente

El texto narrado debe derivarse de una edición identificable y aprobada.

Cada pieza de audio debe poder responder:

- de qué obra proviene;
- de qué edición;
- de qué capítulo;
- de qué bloques editoriales;
- qué texto exacto se narró;
- qué versión de pronunciaciones utilizó;
- qué voz y motor lo generaron;
- qué toma fue aprobada.

### 5.2 El texto escrito y el texto hablado son entidades relacionadas

La lectura oral puede requerir:

- expandir abreviaturas;
- convertir números a palabras;
- resolver siglas;
- decidir cómo leer referencias bíblicas;
- omitir notas no narrables;
- insertar pausas;
- cambiar signos por instrucciones de lectura;
- adaptar citas;
- corregir secuencias difíciles para síntesis;
- asignar voces diferentes.

Ejemplo:

```text
Texto editorial:
Jn. 1:14

Texto hablado:
Juan, capítulo uno, versículo catorce
```

La transformación debe quedar registrada.

### 5.3 La segmentación debe respetar el sentido

La división debe seguir esta prioridad:

```text
párrafo
→ oración
→ frase
```

No se debe cortar el texto solamente por cantidad de caracteres.

### 5.4 Ningún motor de voz debe dominar el núcleo

El dominio no debe conocer nombres de proveedores concretos.

La aplicación debe pedir:

```text
Generar una toma para este segmento
con esta voz
con estas instrucciones
```

Un adaptador resolverá cómo comunicarse con cada motor.

### 5.5 Toda toma debe ser verificable

La generación de voz es no determinista. Cada toma debe pasar por controles automáticos y revisión humana antes de convertirse en audio aprobado.

### 5.6 El sistema debe ser reanudable

Una obra larga puede tardar horas. El proceso debe continuar desde el último segmento válido sin regenerar capítulos aprobados.

## 6. Modelo de dominio objetivo

### 6.1 NarrationBrief

Representa la definición editorial general de la narración.

Campos mínimos:

```text
brief_id
work_id
edition_id
language
narration_mode
primary_voice_id
secondary_voice_ids
tone
pace
expressiveness
pause_policy
biblical_reference_policy
quote_policy
footnote_policy
status
created_at
created_by
version
```

Debe responder preguntas como:

- ¿Quién narra?
- ¿Qué tono debe tener?
- ¿Qué velocidad?
- ¿Cómo se leen las citas?
- ¿Cómo se leen los versículos?
- ¿Se narran notas al pie?
- ¿Hay voces secundarias?
- ¿Se trata de audiolibro, devocional, enseñanza o dramatización?

### 6.2 PronunciationEntry

Representa una pronunciación editorial aprobada.

Campos mínimos:

```text
entry_id
work_id
term
normalized_term
spoken_form
language
phonetic_hint
scope
source
status
created_at
updated_at
version
```

Ámbitos posibles:

```text
global editorial
autor
obra
edición
capítulo
```

Casos de uso:

- nombres bíblicos;
- hebreo;
- griego;
- autores;
- lugares;
- siglas;
- abreviaturas;
- términos doctrinales;
- palabras extranjeras;
- pronunciaciones preferidas por el autor.

### 6.3 AudioSegment

Es la unidad central de producción.

Campos mínimos propuestos:

```text
segment_id
work_id
edition_id
chapter_id
source_block_ids
source_text
spoken_text
sequence
voice_id
pronunciation_revision
segment_policy
status
created_at
updated_at
version
```

Estados sugeridos:

```text
draft
ready
generating
generated
validation_failed
awaiting_review
approved
rejected
stale
```

### 6.4 AudioAsset

Representa una toma concreta generada o cargada.

Campos mínimos:

```text
asset_id
segment_id
take_number
provider
model
voice_id
audio_uri
format
sample_rate
channels
duration_ms
generation_parameters
source_text_hash
spoken_text_hash
validation_summary
created_at
status
```

Un segmento puede tener múltiples tomas:

```text
AudioSegment
├── toma 1 — rechazada
├── toma 2 — rechazada automáticamente
└── toma 3 — aprobada
```

### 6.5 AudioValidation

Representa el resultado del control automático.

Campos mínimos:

```text
validation_id
asset_id
transcript
similarity_score
missing_words
extra_words
repeated_words
cut_word_detected
initial_silence_ms
final_silence_ms
abnormal_pauses
integrated_loudness
peak_level
duration_expected_ms
duration_actual_ms
pronunciation_findings
result
created_at
```

Resultados posibles:

```text
pass
warning
fail
```

### 6.6 AudioApproval

Representa una decisión editorial humana.

Campos mínimos:

```text
approval_id
segment_id
asset_id
decision
reason
notes
reviewed_by
reviewed_at
version
```

Decisiones:

```text
approved
rejected
regenerate
replace_with_human_audio
```

### 6.7 AudiobookEdition

Representa una edición sonora publicable.

Campos mínimos:

```text
audiobook_edition_id
work_id
source_edition_id
narration_brief_id
title
author
narrator
language
chapter_order
approved_asset_ids
cover_asset_id
metadata
total_duration_ms
status
created_at
published_at
version
```

### 6.8 SyncManifest

Representa la sincronización entre App Book y audio.

Campos mínimos:

```text
manifest_id
audiobook_edition_id
chapter_id
segment_id
source_block_ids
audio_asset_id
start_ms
end_ms
word_timings
spoken_text
source_text
checksum
version
```

## 7. Comandos de aplicación

### 7.1 Definición de narración

```text
DefineNarrationBriefCommand
UpdateNarrationBriefCommand
ApproveNarrationBriefCommand
```

### 7.2 Pronunciaciones

```text
RegisterPronunciationEntryCommand
UpdatePronunciationEntryCommand
RemovePronunciationEntryCommand
```

### 7.3 Segmentos

```text
CreateAudioSegmentCommand
UpdateSpokenTextCommand
ReorderAudioSegmentCommand
MarkAudioSegmentReadyCommand
InvalidateAudioSegmentCommand
```

### 7.4 Tomas

```text
GenerateAudioTakeCommand
RegisterAudioAssetCommand
RegisterHumanAudioCommand
ValidateAudioAssetCommand
```

### 7.5 Revisión

```text
ApproveAudioAssetCommand
RejectAudioAssetCommand
RequestAudioRegenerationCommand
```

### 7.6 Edición sonora

```text
CreateAudiobookEditionCommand
AssembleAudiobookEditionCommand
PublishAudiobookEditionCommand
```

## 8. Eventos de dominio

Todos los cambios significativos deben quedar registrados como eventos tipados y serializables.

### 8.1 Narración

```text
NarrationBriefDefined
NarrationBriefUpdated
NarrationBriefApproved
```

### 8.2 Pronunciaciones

```text
PronunciationEntryRegistered
PronunciationEntryUpdated
PronunciationEntryRemoved
```

### 8.3 Segmentos

```text
AudioSegmentCreated
AudioSegmentSpokenTextUpdated
AudioSegmentReordered
AudioSegmentMarkedReady
AudioSegmentInvalidated
```

### 8.4 Tomas

```text
AudioTakeGenerationRequested
AudioAssetRegistered
HumanAudioRegistered
AudioAssetValidated
```

### 8.5 Aprobaciones

```text
AudioAssetApproved
AudioAssetRejected
AudioRegenerationRequested
```

### 8.6 Audiolibro

```text
AudiobookEditionCreated
AudiobookEditionAssembled
AudiobookEditionPublished
```

## 9. Proyecciones

### 9.1 AudioProjection

Debe reconstruir el estado sonoro completo de una obra:

- definición de narración vigente;
- pronunciaciones activas;
- segmentos;
- orden;
- tomas;
- validaciones;
- aprobaciones;
- edición sonora;
- estado de publicación.

### 9.2 SegmentReviewProjection

Vista optimizada para interfaz:

```text
segmento
texto fuente
texto hablado
voz
tomas
resultado automático
toma seleccionada
estado editorial
```

### 9.3 AudiobookProgressProjection

Debe calcular:

```text
segmentos totales
segmentos preparados
segmentos generados
segmentos validados
segmentos aprobados
segmentos rechazados
segmentos obsoletos
porcentaje de avance
duración estimada
duración aprobada
```

## 10. Flujo editorial completo

### 10.1 Preparación

1. Seleccionar una edición aprobada.
2. Crear `NarrationBrief`.
3. Definir narrador, estilo, ritmo y reglas.
4. Resolver abreviaturas y referencias.
5. Crear o completar pronunciaciones.

### 10.2 Segmentación

1. Recorrer capítulos y bloques.
2. Identificar párrafos narrables.
3. Excluir componentes no narrables.
4. Derivar `spoken_text`.
5. Crear segmentos respetando límites semánticos.
6. Asignar secuencia y voz.

### 10.3 Generación

1. Seleccionar segmento listo.
2. Resolver pronunciaciones activas.
3. Enviar solicitud al adaptador.
4. Registrar parámetros.
5. Guardar toma como `AudioAsset`.
6. Ejecutar validación automática.

### 10.4 Validación

Cada toma debe controlar al menos:

- duración esperada;
- silencio inicial;
- silencio final;
- pausas internas;
- volumen;
- pico máximo;
- palabras cortadas;
- repeticiones;
- omisiones;
- palabras inventadas;
- similitud entre texto y transcripción;
- pronunciaciones críticas.

### 10.5 Reintento inteligente

Ante un fallo:

1. regenerar con otra semilla;
2. disminuir variabilidad;
3. ajustar puntuación;
4. dividir el segmento;
5. agregar una pronunciación;
6. cambiar de voz;
7. cambiar de motor;
8. enviar a narración humana.

### 10.6 Revisión humana

La interfaz debe permitir:

- reproducir una toma;
- ver texto fuente;
- ver texto hablado;
- ver errores detectados;
- comparar tomas;
- aprobar;
- rechazar;
- regenerar;
- reemplazar;
- dejar una nota.

### 10.7 Ensamblado

1. Verificar que todos los segmentos estén aprobados.
2. Ordenar por capítulo y secuencia.
3. Normalizar volumen.
4. Unir segmentos.
5. Insertar pausas.
6. Generar capítulos.
7. Incorporar portada.
8. Escribir metadatos.
9. Exportar M4B.
10. Exportar MP3 por capítulo.
11. Generar manifiesto App Book.

## 11. Validación automática

### 11.1 Transcripción de control

El audio generado debe ser transcripto nuevamente.

Después se compara:

```text
spoken_text esperado
vs.
transcripción obtenida
```

### 11.2 Métricas mínimas

```text
similaridad de texto
palabras omitidas
palabras agregadas
palabras repetidas
errores de nombres propios
duración anormal
silencios anormales
volumen insuficiente
clipping
palabra final cortada
```

### 11.3 Umbrales iniciales

```text
similaridad >= 0.97        → aprobado automáticamente
0.93 a 0.969               → revisión humana
< 0.93                     → regeneración
palabra crítica incorrecta → fallo obligatorio
clipping detectado         → fallo obligatorio
```

Estos valores deben calibrarse con obras reales en español.

## 12. Motores y adaptadores

### 12.1 Contrato común

Todo motor debe implementar conceptualmente:

```text
generate(
    text,
    voice,
    language,
    instructions,
    pronunciation_map,
    generation_parameters
) -> GeneratedAudio
```

### 12.2 Motores candidatos

#### Qwen3-TTS

Uso previsto:

- narración principal;
- español;
- clonación autorizada;
- diseño de voz;
- instrucciones de tono y ritmo.

#### Chatterbox

Uso previsto:

- alternativa expresiva;
- comparación de resultados;
- contingencia;
- clonación multilingüe.

#### Kokoro

Uso previsto:

- previsualizaciones;
- borradores;
- equipos sin GPU potente;
- generación rápida.

### 12.3 Política de aislamiento

Los motores pueden requerir versiones incompatibles de Python, Torch o CUDA.

Por ello deben ejecutarse en entornos separados:

```text
núcleo editorial
├── adaptador Qwen3-TTS
├── adaptador Chatterbox
├── adaptador Kokoro
└── servicio de validación
```

En una primera etapa pueden ser procesos locales aislados. No es obligatorio convertirlos inmediatamente en microservicios distribuidos.

## 13. Integración con App Book

### 13.1 Capacidades de consumo

App Book debe permitir:

- leer;
- escuchar;
- cambiar entre lectura y audio;
- comenzar desde un párrafo;
- resaltar el texto actual;
- avanzar por capítulos;
- guardar posición;
- descargar audio;
- usar audio sin conexión;
- retomar desde el último segmento;
- acceder a notas, referencias y glosario.

### 13.2 Sincronización

Cada segmento aprobado debe incluir:

```text
block_id
segment_id
audio_asset_id
start_ms
end_ms
spoken_text
source_text
word_timings opcionales
```

### 13.3 Degradación controlada

La sincronización debe admitir tres niveles:

```text
Nivel 1: capítulo
Nivel 2: segmento o párrafo
Nivel 3: palabra
```

Para el MVP, el nivel 2 es suficiente.

### 13.4 Manifiesto conceptual

```json
{
  "audiobook_edition_id": "audio-edition-001",
  "work_id": "work-001",
  "chapters": [
    {
      "chapter_id": "chapter-01",
      "audio": "chapter-01.mp3",
      "segments": [
        {
          "segment_id": "seg-001",
          "block_ids": ["block-001"],
          "start_ms": 0,
          "end_ms": 12450,
          "text": "En el principio..."
        }
      ]
    }
  ]
}
```

## 14. Formatos de salida

### 14.1 Obligatorios

- M4B completo;
- MP3 por capítulo;
- WAV maestro opcional;
- portada;
- metadatos;
- manifiesto App Book;
- informe de validación.

### 14.2 Metadatos

```text
título
subtítulo
autor
narrador
editorial
idioma
descripción
fecha
duración
capítulos
portada
identificador de obra
identificador de edición
```

### 14.3 Compatibilidad

La salida debe funcionar:

- dentro de App Book;
- en reproductores estándar;
- en Audiobookshelf;
- en dispositivos móviles;
- fuera de línea.

## 15. Invalidación y dependencias

### 15.1 Regla principal

Si cambia el texto fuente de un bloque utilizado por un segmento aprobado:

```text
segmento → stale
asset aprobado → stale
capítulo ensamblado → stale
audiobook edition → stale
manifest → stale
```

### 15.2 Dependencias mínimas

```text
Edition
  ↓
SourceBlock
  ↓
AudioSegment
  ↓
AudioAsset
  ↓
AudioApproval
  ↓
AudiobookEdition
  ↓
SyncManifest
```

### 15.3 Inmutabilidad histórica

Las versiones anteriores no deben borrarse.

Debe quedar disponible:

- qué se narró;
- cuándo;
- con qué edición;
- con qué pronunciación;
- con qué voz;
- quién lo aprobó.

## 16. Persistencia y concurrencia

### 16.1 Event Store

Todos los eventos son persistidos en el stream de la obra y rama correspondiente.

### 16.2 Control de versión

Cada comando de escritura debe utilizar:

```text
expected_version
```

Un conflicto de versión debe fallar sin escribir eventos parciales.

### 16.3 Idempotencia

Los comandos deben admitir una clave idempotente.

Repetir una solicitud ya aplicada no debe duplicar:

- pronunciaciones;
- segmentos;
- tomas;
- aprobaciones;
- ediciones sonoras.

### 16.4 Aislamiento

Una obra no puede leer ni modificar:

- pronunciaciones de otra obra;
- segmentos de otra obra;
- tomas de otra obra;
- ediciones sonoras de otra obra.

Las ramas editoriales también deben permanecer aisladas.

## 17. Interfaz web objetivo

### 17.1 Pantallas principales

#### Configuración de narración

- narrador;
- tono;
- ritmo;
- idioma;
- reglas de citas;
- reglas de referencias bíblicas;
- notas al pie;
- voces secundarias.

#### Pronunciaciones

- término;
- pronunciación;
- alcance;
- vista previa;
- historial;
- aprobación.

#### Segmentos

- capítulo;
- orden;
- texto fuente;
- texto hablado;
- voz;
- estado;
- dependencias;
- cambios pendientes.

#### Revisión de tomas

- reproductor;
- forma de onda opcional;
- comparación de tomas;
- transcripción;
- errores;
- aprobar;
- rechazar;
- regenerar.

#### Ensamblado

- progreso por capítulos;
- segmentos faltantes;
- duración;
- portada;
- metadatos;
- salida M4B;
- salida MP3;
- manifiesto App Book.

### 17.2 Lenguaje para usuario

La interfaz no debe mostrar términos internos innecesarios.

```text
AudioSegment       → Fragmento narrado
AudioAsset         → Toma
AudioApproval      → Revisión
AudiobookEdition   → Edición de audiolibro
SyncManifest       → Sincronización con App Book
```

## 18. Observabilidad

### 18.1 Registro operativo

Cada generación debe registrar:

```text
obra
segmento
motor
modelo
voz
duración
tiempo de proceso
reintentos
resultado de validación
decisión editorial
```

### 18.2 Métricas

```text
segmentos por hora
porcentaje de tomas aprobadas al primer intento
reintentos promedio
errores por motor
errores por voz
errores de pronunciación
costo estimado por hora final
tiempo humano de revisión
duración total aprobada
```

### 18.3 Trazabilidad

Debe poder reconstruirse:

```text
texto aprobado
→ texto hablado
→ solicitud
→ toma
→ validación
→ aprobación
→ archivo final
```

## 19. Seguridad, derechos y consentimiento

### 19.1 Clonación de voz

No se debe clonar una voz sin autorización verificable.

Cada perfil de voz clonada debe registrar:

```text
titular
consentimiento
alcance autorizado
fecha
material de referencia
restricciones
revocación
```

### 19.2 Protección de archivos

Las muestras de voz y audios maestros deben tener:

- acceso restringido;
- almacenamiento privado;
- cifrado cuando corresponda;
- registro de acceso;
- política de eliminación.

### 19.3 Licencias

Antes de incorporar un motor se debe verificar:

- licencia del código;
- licencia de pesos;
- uso comercial;
- restricciones de distribución;
- restricciones de voces;
- obligaciones de atribución.

Un repositorio técnicamente excelente no debe convertirse en dependencia central si su licencia comercial es incierta.

## 20. Estrategia de pruebas

### 20.1 Dominio

- validación de invariantes;
- estados permitidos;
- orden de segmentos;
- relación entre segmentos y bloques;
- selección de toma aprobada;
- invalidación.

### 20.2 Aplicación

- comandos;
- handlers;
- idempotencia;
- conflictos de versión;
- aislamiento;
- composición.

### 20.3 Persistencia

- reinicio SQLite;
- replay;
- eventos tipados;
- serialización;
- atomicidad;
- ramas.

### 20.4 Adaptadores

- contrato común;
- errores del proveedor;
- timeouts;
- archivos corruptos;
- reintentos;
- cancelación;
- resultados deterministas en pruebas mediante dobles.

### 20.5 Validación de audio

- omisiones;
- repeticiones;
- palabras inventadas;
- silencios;
- clipping;
- volumen;
- palabra cortada;
- pronunciaciones.

### 20.6 Ensamblado

- orden;
- capítulos;
- duración;
- metadatos;
- portada;
- M4B;
- MP3;
- manifiesto.

## 21. Criterios de aceptación del MVP

El MVP de Factoría Sonora estará completo cuando permita:

1. seleccionar una edición aprobada;
2. crear una definición de narración;
3. registrar pronunciaciones;
4. generar segmentos persistidos;
5. asociar cada segmento con bloques editoriales;
6. registrar varias tomas por segmento;
7. ejecutar validación automática;
8. aprobar o rechazar una toma;
9. invalidar audio cuando cambia el texto;
10. reconstruir todo mediante replay;
11. reanudar después de reiniciar SQLite;
12. ensamblar MP3 por capítulos;
13. ensamblar M4B;
14. generar manifiesto App Book;
15. reproducir audio sincronizado por segmento;
16. mantener trazabilidad editorial completa.

## 22. Plan de implementación por cortes

### Corte 1 — AudioSegment persistido

- comando;
- evento;
- handler;
- proyección;
- SQLite;
- aislamiento;
- idempotencia;
- control de versión;
- vínculo con bloques;
- orden por capítulo.

### Corte 2 — Invalidación

- dependencia con bloques editoriales;
- invalidación transitiva;
- estado `stale`;
- replay;
- pruebas.

### Corte 3 — AudioAsset persistido

- registro de toma;
- archivo;
- proveedor;
- modelo;
- voz;
- parámetros;
- historial.

### Corte 4 — Validación automática

- transcripción;
- comparación;
- silencios;
- volumen;
- resultado;
- reintentos.

### Corte 5 — Aprobación editorial

- aprobar;
- rechazar;
- regenerar;
- toma vigente;
- auditoría.

### Corte 6 — Primer adaptador de voz

Motor recomendado para primer piloto:

```text
Qwen3-TTS
```

Motor rápido de apoyo:

```text
Kokoro
```

Motor alternativo:

```text
Chatterbox
```

### Corte 7 — Ensamblado

- WAV maestro;
- MP3 por capítulo;
- M4B;
- portada;
- metadatos.

### Corte 8 — Sincronización App Book

- tiempos por segmento;
- manifiesto;
- reproductor;
- resaltado por bloque;
- lectura sin conexión.

### Corte 9 — Interfaz web

- configuración;
- pronunciaciones;
- segmentos;
- tomas;
- revisión;
- progreso;
- publicación.

## 23. Referencias técnicas estudiadas

### `DrewThomasson/ebook2audiobook`

Aportes:

- separación entre importación, generación y ensamblado;
- sesiones reanudables;
- soporte de múltiples motores;
- capítulos;
- metadatos;
- múltiples formatos.

### `lukaszliniewicz/Pandrator`

Aportes:

- flujo editorial completo;
- revisión humana por segmento;
- comparación de tomas;
- regeneración parcial;
- exportación final.

### `zeropointnine/tts-audiobook-tool`

Aportes:

- transcripción de control;
- comparación texto–audio;
- reintentos;
- selección de mejor toma;
- control de silencios;
- normalización;
- validación específica para audiolibros.

### `denizsafak/abogen`

Aportes:

- audio sincronizado;
- subtítulos;
- lectura mientras se escucha;
- experiencia local simplificada.

### `aedocw/epub2tts`

Aportes:

- reanudación por capítulo;
- verificación mediante transcripción;
- capítulos;
- portada;
- procesamiento controlado.

### `p0n1/epub_to_audiobook`

Aportes:

- MP3 por capítulo;
- compatibilidad con reproductores;
- metadatos;
- interoperabilidad.

### `QwenLM/Qwen3-TTS`

Aportes:

- español;
- clonación autorizada;
- diseño de voces;
- instrucciones de tono y ritmo.

### `resemble-ai/chatterbox`

Aportes:

- voz expresiva;
- clonación multilingüe;
- motor alternativo.

### `hexgrad/kokoro`

Aportes:

- bajo consumo;
- previsualización;
- generación rápida.

### `m-bain/whisperX`

Aportes:

- transcripción;
- alineación;
- tiempos por palabra.

### `sandreas/m4b-tool`

Aportes:

- ensamblado M4B;
- capítulos;
- portada;
- descripción;
- metadatos.

## 24. Decisión arquitectónica final

La Factoría Sonora de Editorial TR.ES no será un botón que “convierte un libro en audio”.

Será un sistema editorial donde:

- cada fragmento está ligado a su fuente;
- cada pronunciación queda registrada;
- cada toma puede compararse;
- cada error puede detectarse;
- cada aprobación tiene autoría;
- cada modificación invalida lo derivado;
- cada edición sonora puede reconstruirse;
- cada audiolibro puede publicarse fuera de la plataforma;
- cada segmento puede reutilizarse dentro de App Book.

El diferencial de TR.ES no será utilizar inteligencia artificial para generar voz.

El diferencial será convertir esa voz en una **edición sonora trazable, gobernada, revisable y publicable**.
