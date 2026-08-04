# Editorial TR.ES - Consola Web

Interfaz web SaaS para la factoría editorial.

## Inicio rápido

### Windows
Doble clic en `start.bat` o ejecutá en terminal:
```bash
cd editorial-TR.ES/web
pip install -r requirements-web.txt
python run.py
```

### Linux/Mac
```bash
cd editorial-TR.ES/web
pip install -r requirements-web.txt
python run.py
```

## Verificar antes de iniciar

```bash
python test_imports.py
```

## Acceso

Una vez iniciado el servidor:
- **URL:** http://localhost:8000
- **API docs:** http://localhost:8000/docs

## Flujo de uso

1. **Dashboard** → Ver proyectos existentes
2. **Nuevo proyecto** → Cargar manuscrito (.txt)
3. **Detalle** → Ejecutar revisión
4. **Findings** → Aceptar/rechazar cada finding
5. **Aprobar** → Generar PDF, HTML, App Book
6. **Descargar** → Obtener archivos finales

## Estructura

```
web/
├── app.py              # Backend FastAPI
├── template.py         # Frontend HTML/CSS/JS (SPA)
├── run.py              # Launcher
├── start.bat           # Launcher Windows
├── test_imports.py     # Test de imports
├── requirements-web.txt
└── data/               # Se crea automáticamente
```

## Troubleshooting

### Error: "Module not found"
Verificá que `platform/src` esté en el path (ya lo hace `run.py` automáticamente).

### Error: "Port 8000 already in use"
```bash
# Matar proceso en puerto 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Error de imports de editorial_tres
Asegurate de que exista `editorial-TR.ES/platform/src/editorial_tres/`.

## Stack

- **Backend:** FastAPI + Uvicorn
- **Frontend:** Vanilla HTML/CSS/JS (SPA)
- **Motor:** PrivateEditorialFactory (existente)
- **Estilo:** SaaS premium, Inter font, animaciones suaves
