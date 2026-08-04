# Editorial TR.ES - Mesa Editorial

Interfaz web adaptada al diseño literario argentino con sidebar de navegación.

## Diseño implementado

✅ **Sidebar de navegación** con secciones:
- La mesa (dashboard)
- Nueva obra (crear proyecto)
- Obra abierta (detalle de obra)
- Talleres editoriales
- Observaciones (findings)
- Ediciones listas (outputs)

✅ **Estilo visual**:
- Paleta cálida (tonos tierra y ámbar)
- Tipografía Inter + Playfair Display para citas
- Cita literaria en el sidebar: "Editar es escuchar lo que el texto todavía intenta decir."
- Cards con hover elegante
- Animaciones suaves (fadeIn, slideIn)
- Badges de estado: Borrador, Leída, Aprobada, Exportada

✅ **Flujo completo**:
1. Dashboard con estadísticas y obras recientes
2. Formulario de nueva obra con drag-and-drop
3. Detalle de obra con pasos de progreso
4. Vista de observaciones (findings) con aceptar/descartar
5. Pantalla de ediciones listas con descargas (PDF, HTML, App Book)

## Cómo arrancar el servidor

### Paso 1: Abrir terminal en el directorio correcto

```bash
cd E:\BuenosPasos\editorial-TR.ES\web
```

### Paso 2: Verificar dependencias

```bash
pip install -r requirements-web.txt
```

### Paso 3: Verificar que el template carga

```bash
python verify_template.py
```

Debería mostrar todos los ✓ verdes.

### Paso 4: Iniciar el servidor

```bash
python run.py
```

Deberías ver:
```
============================================================
  Editorial TR.ES — Consola Web
  http://localhost:8000
============================================================

  Presioná Ctrl+C para detener el servidor.
```

### Paso 5: Abrir en el navegador

Abrí tu navegador y andá a: **http://localhost:8000**

## Estructura de archivos

```
editorial-TR.ES/web/
├── app.py              # Backend FastAPI (API endpoints)
├── template.py         # Frontend HTML/CSS/JS (NUEVO DISEÑO)
├── run.py              # Launcher del servidor
├── requirements-web.txt
├── verify_template.py  # Script de verificación
├── test_imports.py     # Test de imports
├── data/               # Base de datos SQLite + JSON
│   ├── projects.json
│   └── factory.sqlite
├── README.md
├── README_START.md
└── INSTRUCCIONES.md    # Este archivo
```

## API Endpoints

El backend expone estos endpoints (ya implementados en app.py):

- `GET /api/projects` - Listar proyectos
- `POST /api/projects` - Crear proyecto con manuscrito
- `GET /api/projects/{id}` - Detalle de proyecto
- `POST /api/projects/{id}/review` - Ejecutar revisión
- `GET /api/projects/{id}/findings` - Obtener findings
- `POST /api/projects/{id}/decisions` - Enviar decisiones
- `POST /api/projects/{id}/approve` - Aprobar edición
- `GET /api/projects/{id}/download/{format}` - Descargar export (pdf/html/appbook)

## Troubleshooting

### "Port 8000 already in use"

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <número> /F
```

### Error de imports

Verificá que exista `editorial-TR.ES\platform\src\editorial_tres\` y que el `run.py` esté agregando ese path (ya lo hace automáticamente).

### La página no muestra nada

1. Verificá que el servidor esté corriendo (`python run.py`)
2. Revisá la consola del navegador (F12) para errores de JavaScript
3. Verificá que `template.py` se importe correctamente con `python verify_template.py`

## Cambios realizados

### template.py (NUEVO DISEÑO)

**Antes**: Interfaz SaaS estándar con header superior
**Ahora**: Sidebar lateral con diseño literario argentino

**Características nuevas**:
- Sidebar con navegación por secciones
- Cita literaria en el footer del sidebar
- Dashboard con estadísticas (obras, atención, observaciones, ediciones)
- Progreso visual en detalle de obra (Ingreso → Lectura → Aprobación → Ediciones)
- Talleres editoriales como cards
- Findings con diseño editorial (original vs propuesta)
- Pantalla de ediciones listas con 3 formatos principales
- Tono "vos" argentino en toda la interfaz
- Paleta cálida (ámbar, tierra) en vez de azul corporativo

### app.py (SIN CAMBIOS)

El backend permanece intacto. Todos los endpoints funcionan igual.

## Próximos pasos

Si querés agregar funcionalidad:

1. **Dark mode**: Agregar toggle en el sidebar y variables CSS alternativas
2. **Autenticación**: Agregar login básico con tokens JWT
3. **Exportaciones adicionales**: Agregar más formatos (EPUB, DOCX)
4. **Historial de versiones**: Mostrar versiones anteriores de la obra
5. **Colaboración**: Permitir múltiples editores en una obra
