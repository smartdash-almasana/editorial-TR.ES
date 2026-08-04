"""Quick launcher for the Editorial TR.ES web console."""

import sys
from pathlib import Path

# Ensure the web directory is on the path so template.py can be imported
_WEB_DIR = Path(__file__).resolve().parent
if str(_WEB_DIR) not in sys.path:
    sys.path.insert(0, str(_WEB_DIR))

# Ensure platform/src is on the path
_PLATFORM_SRC = _WEB_DIR.parent / "platform" / "src"
if str(_PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(_PLATFORM_SRC))


def main() -> None:
    import uvicorn

    print("=" * 60)
    print("  Editorial TR.ES — Consola Web")
    print("  http://localhost:8000")
    print("=" * 60)
    print()
    print("  Presioná Ctrl+C para detener el servidor.")
    print()

    from app import app

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
