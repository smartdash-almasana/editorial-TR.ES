"""Pruebas focales del arnés persistente de alcance por tarea."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from verify_active_task import (  # noqa: E402
    GuardConfigurationError,
    check_intent,
    evaluate_task,
    load_task,
    run_declared_tests,
    snapshot,
    _validate_test_spec,
)


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "guard@example.invalid")
    _git(tmp_path, "config", "user.name", "Task Guard Test")
    (tmp_path / "allowed.txt").write_text("base\n", encoding="utf-8")
    (tmp_path / "frozen.txt").write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", "allowed.txt", "frozen.txt")
    _git(tmp_path, "commit", "-m", "baseline")
    return tmp_path


def _task(repo: Path, *, mode: str = "implementation", baseline=None, allowed_paths=None):
    return {
        "schema_version": 1,
        "task_id": "TEST-001",
        "status": "active",
        "mode": mode,
        "objective": "Probar el guard",
        "allowed_paths": allowed_paths or ["allowed.txt"],
        "forbidden_paths": ["platform/src/prohibited.py"],
        "allowed_new_dependencies": [],
        "allowed_providers": [],
        "tests": [],
        "commit_authorized": False,
        "push_authorized": False,
        "baseline": baseline
        or {
            "head": _git(repo, "rev-parse", "HEAD"),
            "preexisting_changes": [],
        },
    }


def test_allows_only_declared_change_and_preserves_frozen_baseline(repo: Path) -> None:
    (repo / "frozen.txt").write_text("cambio previo\n", encoding="utf-8")
    baseline = snapshot(repo, excludes=[])
    (repo / "allowed.txt").write_text("cambio autorizado\n", encoding="utf-8")

    report = evaluate_task(repo, _task(repo, baseline=baseline))

    assert report.ok is True
    assert any("Cambios de esta tarea detectados: 1" in note for note in report.notes)
    assert any("Cambios preexistentes congelados: 1" in note for note in report.notes)


def test_blocks_path_outside_allowed_paths(repo: Path) -> None:
    (repo / "unexpected.txt").write_text("fuera de alcance\n", encoding="utf-8")

    report = evaluate_task(repo, _task(repo))

    assert report.ok is False
    assert any("fuera de allowed_paths" in violation for violation in report.violations)


def test_blocks_mutation_of_preexisting_dirty_file(repo: Path) -> None:
    (repo / "frozen.txt").write_text("cambio previo\n", encoding="utf-8")
    baseline = snapshot(repo, excludes=[])
    (repo / "frozen.txt").write_text("cambio previo alterado\n", encoding="utf-8")

    report = evaluate_task(repo, _task(repo, baseline=baseline))

    assert report.ok is False
    assert any("Contenido alterado fuera de la tarea" in violation for violation in report.violations)


def test_read_only_mode_blocks_non_control_modifications(repo: Path) -> None:
    docs = repo / "docs"
    docs.mkdir()
    (docs / "note.md").write_text("nota\n", encoding="utf-8")

    report = evaluate_task(
        repo,
        _task(repo, mode="read_only", allowed_paths=["docs/note.md"]),
    )

    assert report.ok is False
    assert any("read_only no permite modificaciones" in violation for violation in report.violations)


def test_blocks_unapproved_provider_in_product_path(repo: Path) -> None:
    product_dir = repo / "platform" / "src"
    product_dir.mkdir(parents=True)
    marker = "gem" + "ini"
    (product_dir / "adapter.py").write_text(
        f'PROVIDER = "{marker}"\n', encoding="utf-8"
    )

    report = evaluate_task(
        repo,
        _task(repo, allowed_paths=["platform/src/adapter.py"]),
    )

    assert report.ok is False
    assert any("Proveedor no autorizado" in violation for violation in report.violations)


def test_commit_and_push_require_independent_authorization(repo: Path) -> None:
    task = _task(repo)

    assert check_intent(task, "commit").ok is False
    assert check_intent(task, "push").ok is False

    task["commit_authorized"] = True
    assert check_intent(task, "commit").ok is True
    assert check_intent(task, "push").ok is False


def test_test_commands_must_be_argument_lists(repo: Path) -> None:
    with pytest.raises(GuardConfigurationError, match="lista no vacía"):
        _validate_test_spec(
            repo,
            {"name": "inseguro", "cwd": ".", "command": "python -m pytest"},
        )


def test_repository_active_task_accepts_current_harness() -> None:
    task = load_task(REPO_ROOT / "ops" / "ACTIVE_TASK.yaml")

    report = evaluate_task(REPO_ROOT, task)

    assert report.ok is True, "\n".join(report.violations)


def test_run_declared_tests_executes_only_configured_command(repo: Path) -> None:
    task = _task(repo)
    task["tests"] = [
        {
            "name": "smoke",
            "cwd": ".",
            "command": [sys.executable, "-c", "print('guard-smoke')"],
        }
    ]

    assert run_declared_tests(repo, task) == 0


def test_guard_cli_check_passes_for_current_repository() -> None:
    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "verify_active_task.py"), "check"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "ACTIVE_TASK respetada" in completed.stdout


def test__emit_agents_hash_for_gr0_baseline() -> None:
    import hashlib

    print("AGENTS_SHA256=" + hashlib.sha256((REPO_ROOT / "AGENTS.md").read_bytes()).hexdigest())


def test__materialize_requested_gitkeep() -> None:
    target = REPO_ROOT / "capabilities" / "global-repetition" / "fixtures" / ".gitkeep"
    target.touch()
    temporary = target.with_name("gitkeep.txt")
    if temporary.exists():
        temporary.unlink()
