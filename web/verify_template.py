#!/usr/bin/env python3
"""Quick verification that the template loads correctly."""

import sys
from pathlib import Path

_WEB_DIR = Path(__file__).resolve().parent
if str(_WEB_DIR) not in sys.path:
    sys.path.insert(0, str(_WEB_DIR))

def verify():
    print("=" * 60)
    print("Verificando template Editorial TR.ES...")
    print("=" * 60)

    try:
        from template import INDEX_HTML
        print(f"✓ Template importado correctamente")
        print(f"  Tamaño: {len(INDEX_HTML):,} caracteres")

        # Check key elements
        checks = [
            ("Sidebar con 'La mesa'", "La mesa" in INDEX_HTML),
            ("Sidebar con 'Nueva obra'", "Nueva obra" in INDEX_HTML),
            ("Sidebar con 'Observaciones'", "Observaciones" in INDEX_HTML),
            ("Sidebar con 'Ediciones listas'", "Ediciones listas" in INDEX_HTML),
            ("Cita literaria", "Editar es escuchar" in INDEX_HTML),
            ("Dashboard con stats", "stat-works" in INDEX_HTML),
            ("Form de nueva obra", "createTitle" in INDEX_HTML),
            ("Vista de findings", "findingsContent" in INDEX_HTML),
            ("Vista de output", "outputContent" in INDEX_HTML),
            ("API endpoints", "/api/projects" in INDEX_HTML),
            ("JavaScript funcional", "function navigate" in INDEX_HTML),
            ("CSS variables", "--accent-primary" in INDEX_HTML),
        ]

        print("\n✓ Verificación de contenido:")
        all_ok = True
        for desc, ok in checks:
            status = "✓" if ok else "✗"
            print(f"  {status} {desc}")
            if not ok:
                all_ok = False

        if all_ok:
            print("\n✅ Template verificado exitosamente!")
            print("\nPara iniciar el servidor:")
            print("  cd editorial-TR.ES/web")
            print("  python run.py")
            print("\nLuego abrí: http://localhost:8000")
            return True
        else:
            print("\n⚠️  Algunos elementos faltan en el template.")
            return False

    except Exception as e:
        print(f"✗ Error al importar template: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
