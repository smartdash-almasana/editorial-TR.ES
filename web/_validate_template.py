"""Validación rápida del template.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    import template
except Exception as e:
    print(f"IMPORT_ERROR: {e}")
    sys.exit(2)

html = getattr(template, "INDEX_HTML", None)
if not html:
    print("NO_INDEX_HTML")
    sys.exit(3)

checks = {
    "sidebar": 'class="app-sidebar"' in html,
    "brand_TR": 'brand-logo">TR</div>' in html,
    "menu_la_mesa": "La mesa" in html,
    "menu_nueva": "Nueva obra" in html,
    "menu_obra": "Obra abierta" in html,
    "menu_talleres": "Talleres editoriales" in html,
    "menu_obs": "Observaciones" in html,
    "menu_eds": "Ediciones listas" in html,
    "quote": "Editar es escuchar" in html,
    "hero": "Taller privado de edición" in html,
    "stats": "Obras en la mesa" in html,
    "works_grid": "works-grid" in html,
    "form": "new-work-form" in html,
    "dropzone": "Acercá el manuscrito" in html,
    "steps": "progress-steps" in html,
    "talleres": "talleres-grid" in html,
    "findings": "Observaciones del" in html,
    "text_blocks": "text-block original" in html and "text-block proposal" in html,
    "descartar_aceptar": "Descartar" in html and "Aceptar" in html,
    "downloads": "Libro para imprimir" in html and "Libro interactivo" in html,
    "modal": "modal-created" in html,
    "js_loadWorks": "function loadWorks" in html,
    "js_api": "/api/projects" in html,
    "palette": "#b45309" in html,
    "inter_font": "Inter" in html,
    "playfair_font": "Playfair" in html,
}

print(f"INDEX_HTML_LEN: {len(html)}")
missing = [k for k, v in checks.items() if not v]
if missing:
    print(f"MISSING: {missing}")
    sys.exit(4)
print("ALL_CHECKS_OK")
