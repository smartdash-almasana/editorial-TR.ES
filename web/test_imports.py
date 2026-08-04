#!/usr/bin/env python3
"""Quick test to verify all imports work before starting the server."""

import sys
from pathlib import Path

# Setup paths
_WEB_DIR = Path(__file__).resolve().parent
if str(_WEB_DIR) not in sys.path:
    sys.path.insert(0, str(_WEB_DIR))

_PLATFORM_SRC = _WEB_DIR.parent / "platform" / "src"
if str(_PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(_PLATFORM_SRC))


def test_imports():
    print("Testing imports...")

    try:
        from template import INDEX_HTML
        print("  ✓ template.py OK")
    except Exception as e:
        print(f"  ✗ template.py FAILED: {e}")
        return False

    try:
        import fastapi
        print(f"  ✓ FastAPI {fastapi.__version__} OK")
    except ImportError:
        print("  ✗ FastAPI not installed. Run: pip install -r requirements-web.txt")
        return False

    try:
        from editorial_tres.application.private_factory import (
            EditionApprovalInput,
            EditorialDecisionInput,
            PrivateEditorialFactory,
        )
        print("  ✓ PrivateEditorialFactory OK")
    except Exception as e:
        print(f"  ✗ PrivateEditorialFactory FAILED: {e}")
        return False

    try:
        from editorial_tres.composition import compose_application
        print("  ✓ compose_application OK")
    except Exception as e:
        print(f"  ✗ compose_application FAILED: {e}")
        return False

    try:
        from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
        print("  ✓ Domain identifiers OK")
    except Exception as e:
        print(f"  ✗ Domain identifiers FAILED: {e}")
        return False

    print("\n✅ All imports successful! Ready to start server.")
    return True


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
