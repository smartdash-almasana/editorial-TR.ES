# Editorial TR.ES — Consola Web

Interfaz web mínima estilo SaaS para operar la factoría editorial existente.

## Requisitos

- Python 3.10+
- Dependencias de la plataforma (`platform/requirements.txt` o equivalente)
- Dependencias web (ver abajo)

## Instalación

```bash
cd editorial-TR.ES/web
pip install -r requirements-web.txt
```

También necesitás tener instalado el paquete `editorial-tres` desde `platform/`:

```bash
cd ../platform
pip install -e .
```

## Ejecución

```bash
cd editorial-TR.ES/web
python app.py
```

La consola estará disponible en: **http://localhost:8000**

## Flujo de uso

1. **Dashboard**: Ver proyectos existentes o crear uno nuevo.
2. **Crear proyecto**: Cargar título, autor, idioma y manuscrito (.txt).
3. **Detalle de proyecto**: Ver estado y acciones disponibles.
4. **Ejecutar revisión**: Analizar el manuscrito y generar findings.
5. **Ver findings**: Aceptar o rechazar cada finding con un motivo.
6. **Aprobar edición**: Autorizar la versión final.
7. **Descargar**: PDF, HTML y App Book JSON.

## Arquitectura

- **Backend**: FastAPI que llama directamente a `PrivateEditorialFactory` (sin subprocess).
- **Frontend**: HTML + CSS + JS vanilla, servido como string desde `template.py`.
- **Persistencia**: SQLite (factoría) + JSON local (metadatos de UI).
- **Manuscritos**: Se guardan en `projects/{project-id}/manuscript.txt`.
- **Exports**: Se guardan en `exports/{project-id}/`.

## Estructura de archivos

```
web/
├── app.py              # FastAPI backend + entry point
├── template.py         # HTML/CSS/JS del frontend
├── requirements-web.txt
├── README.md
└── data/               # Creado automáticamente
    ├── projects.json   # Índice de proyectos
    └── factory.sqlite  # Base de datos de la factoría
```

## Notas

- No se modifica la factoría existente.
- No se usa subprocess para llamar a la CLI.
- Todo el wiring se hace directamente con los servicios Python existentes.
