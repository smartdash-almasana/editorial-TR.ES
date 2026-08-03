from pathlib import Path


def test_every_python_module_compiles() -> None:
    source_root = Path(__file__).parents[1] / "src"
    modules = sorted(source_root.rglob("*.py"))

    assert modules
    for module in modules:
        compile(module.read_text(encoding="utf-8"), str(module), "exec")
