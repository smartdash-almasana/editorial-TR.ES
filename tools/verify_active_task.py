#!/usr/bin/env python3
"""Guardia ejecutable para limitar cada tarea al alcance aprobado.

Uso:
    python tools/verify_active_task.py check
    python tools/verify_active_task.py run-tests
    python tools/verify_active_task.py intent commit
    python tools/verify_active_task.py intent push
    python tools/verify_active_task.py snapshot --exclude AGENTS.md --exclude ops/ACTIVE_TASK.yaml

El guard no modifica archivos del repositorio. `run-tests` ejecuta únicamente
comandos declarados como listas de argumentos en ops/ACTIVE_TASK.yaml.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

try:
    import yaml
except ImportError:  # pragma: no cover - fallback útil fuera del entorno del repo
    yaml = None


TASK_SCHEMA_VERSION = 1
VALID_MODES = {"read_only", "design", "implementation", "validation"}
CONTROL_PATHS = {"ops/ACTIVE_TASK.yaml"}
DEFAULT_DEPENDENCY_FILES = (
    "platform/pyproject.toml",
    "**/requirements*.txt",
    "**/poetry.lock",
    "**/uv.lock",
    "**/package.json",
    "**/package-lock.json",
    "**/pnpm-lock.yaml",
    "**/yarn.lock",
)
DEFAULT_PROVIDER_SCAN_PATHS = (
    "platform/src/**",
    "plugins/**",
    "platform/pyproject.toml",
)
DEFAULT_PROVIDER_MARKERS: Mapping[str, tuple[str, ...]] = {
    "openai": ("openai", "gpt-", "chatgpt"),
    "google": ("gemini", "vertex ai", "google.generativeai"),
    "anthropic": ("anthropic", "claude"),
    "mistral": ("mistral",),
    "cohere": ("cohere",),
    "groq": ("groq",),
    "ollama": ("ollama",),
}


class GuardConfigurationError(ValueError):
    """La tarea activa es inválida o ambigua."""


@dataclass(frozen=True)
class WorktreeChange:
    status: str
    path: str
    original_path: str | None = None


@dataclass
class GuardReport:
    violations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations

    def require_ok(self) -> None:
        if self.ok:
            return
        raise RuntimeError("\n".join(self.violations))


def _run_git(repo_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=check,
    )


def _normalize_repo_path(raw: str) -> str:
    candidate = raw.replace("\\", "/").strip()
    if not candidate:
        raise GuardConfigurationError("Una ruta del contrato está vacía.")
    path = PurePosixPath(candidate)
    if path.is_absolute() or ".." in path.parts:
        raise GuardConfigurationError(f"Ruta insegura en ACTIVE_TASK: {raw!r}")
    normalized = path.as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _matches(path: str, patterns: Iterable[str]) -> bool:
    normalized = _normalize_repo_path(path)
    for raw_pattern in patterns:
        pattern = _normalize_repo_path(str(raw_pattern))
        if pattern.endswith("/") and normalized.startswith(pattern):
            return True
        if fnmatch.fnmatchcase(normalized, pattern):
            return True
        if normalized == pattern:
            return True
    return False


def _hash_path(path: Path) -> str:
    if not path.exists() and not path.is_symlink():
        return "MISSING"
    if path.is_symlink():
        return hashlib.sha256(os.readlink(path).encode("utf-8")).hexdigest()
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    digest = hashlib.sha256()
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(child.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(child.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _load_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise GuardConfigurationError(f"No existe la tarea activa: {path}")
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text)
    else:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise GuardConfigurationError(
                "PyYAML no está instalado y ACTIVE_TASK.yaml no contiene JSON válido."
            ) from exc
    if not isinstance(data, dict):
        raise GuardConfigurationError("ACTIVE_TASK.yaml debe contener un mapping raíz.")
    return data


def load_task(path: Path) -> dict[str, Any]:
    task = _load_mapping(path)
    required = {
        "schema_version",
        "task_id",
        "status",
        "mode",
        "objective",
        "allowed_paths",
        "forbidden_paths",
        "allowed_new_dependencies",
        "allowed_providers",
        "tests",
        "commit_authorized",
        "push_authorized",
        "baseline",
    }
    missing = sorted(required - task.keys())
    if missing:
        raise GuardConfigurationError(
            f"ACTIVE_TASK.yaml omite campos obligatorios: {', '.join(missing)}"
        )
    if task["schema_version"] != TASK_SCHEMA_VERSION:
        raise GuardConfigurationError(
            f"schema_version no soportado: {task['schema_version']!r}; esperado {TASK_SCHEMA_VERSION}."
        )
    if task["status"] != "active":
        raise GuardConfigurationError("La tarea no está activa.")
    if task["mode"] not in VALID_MODES:
        raise GuardConfigurationError(
            f"Modo inválido: {task['mode']!r}. Valores: {sorted(VALID_MODES)}"
        )
    if not isinstance(task["allowed_paths"], list):
        raise GuardConfigurationError("allowed_paths debe ser una lista.")
    if not isinstance(task["forbidden_paths"], list):
        raise GuardConfigurationError("forbidden_paths debe ser una lista.")
    if not isinstance(task["allowed_new_dependencies"], list):
        raise GuardConfigurationError("allowed_new_dependencies debe ser una lista.")
    if not isinstance(task["allowed_providers"], list):
        raise GuardConfigurationError("allowed_providers debe ser una lista.")
    if not isinstance(task["tests"], list):
        raise GuardConfigurationError("tests debe ser una lista.")
    if not isinstance(task["baseline"], dict):
        raise GuardConfigurationError("baseline debe ser un mapping.")
    if "head" not in task["baseline"] or "preexisting_changes" not in task["baseline"]:
        raise GuardConfigurationError("baseline requiere head y preexisting_changes.")
    if not isinstance(task["baseline"]["preexisting_changes"], list):
        raise GuardConfigurationError("baseline.preexisting_changes debe ser una lista.")
    return task


def list_worktree_changes(repo_root: Path) -> list[WorktreeChange]:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    parts = completed.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    changes: list[WorktreeChange] = []
    index = 0
    while index < len(parts):
        entry = parts[index]
        index += 1
        if not entry:
            continue
        if len(entry) < 4:
            raise RuntimeError(f"Entrada inesperada de git status: {entry!r}")
        status = entry[:2]
        path = _normalize_repo_path(entry[3:])
        original_path: str | None = None
        if "R" in status or "C" in status:
            if index >= len(parts):
                raise RuntimeError("git status reportó rename/copy sin ruta de origen.")
            original_path = _normalize_repo_path(parts[index])
            index += 1
        changes.append(WorktreeChange(status=status, path=path, original_path=original_path))
    return changes


def _baseline_by_path(task: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for entry in task["baseline"]["preexisting_changes"]:
        if not isinstance(entry, dict):
            raise GuardConfigurationError("Cada cambio preexistente debe ser un mapping.")
        required = {"path", "status", "sha256"}
        missing = required - entry.keys()
        if missing:
            raise GuardConfigurationError(
                f"Cambio preexistente incompleto: faltan {', '.join(sorted(missing))}."
            )
        path = _normalize_repo_path(str(entry["path"]))
        if path in result:
            raise GuardConfigurationError(f"Cambio preexistente duplicado: {path}")
        result[path] = entry
    return result


def _added_text(repo_root: Path, change: WorktreeChange) -> str:
    path = repo_root / change.path
    if change.status == "??":
        try:
            return path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return ""
    chunks: list[str] = []
    for args in (
        ("diff", "--unified=0", "--", change.path),
        ("diff", "--cached", "--unified=0", "--", change.path),
    ):
        completed = _run_git(repo_root, *args, check=False)
        if completed.returncode not in (0, 1):
            continue
        chunks.extend(
            line[1:]
            for line in completed.stdout.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
    return "\n".join(chunks)


def _validate_design_mode(path: str) -> bool:
    if path in CONTROL_PATHS or path == "AGENTS.md":
        return True
    suffix = Path(path).suffix.lower()
    return path.startswith("docs/") and suffix in {".md", ".yaml", ".yml", ".json"}


def evaluate_task(repo_root: Path, task: Mapping[str, Any]) -> GuardReport:
    report = GuardReport()
    repo_root = repo_root.resolve()
    current_head = _run_git(repo_root, "rev-parse", "HEAD").stdout.strip()
    expected_head = str(task["baseline"]["head"]).strip()
    allow_parent_head = bool(task["baseline"].get("allow_parent_head", False))

    head_ok = (current_head == expected_head)
    if not head_ok and allow_parent_head:
        parent_head_proc = _run_git(repo_root, "rev-parse", "HEAD^", check=False)
        if parent_head_proc.returncode == 0:
            parent_head = parent_head_proc.stdout.strip()
            if parent_head == expected_head:
                head_ok = True

    if not head_ok:
        if allow_parent_head:
            report.violations.append(
                f"HEAD o su padre cambió sin actualizar el contrato: esperado {expected_head}, actual HEAD {current_head}."
            )
        else:
            report.violations.append(
                f"HEAD cambió sin actualizar el contrato: esperado {expected_head}, actual {current_head}."
            )

    allowed_paths = [_normalize_repo_path(str(item)) for item in task["allowed_paths"]]
    forbidden_paths = [_normalize_repo_path(str(item)) for item in task["forbidden_paths"]]
    baseline = _baseline_by_path(task)
    changes = list_worktree_changes(repo_root)
    current_by_path = {change.path: change for change in changes}

    allow_absent_preexisting = bool(task["baseline"].get("allow_absent_preexisting", False))
    materialized_paths = [path for path in baseline if (repo_root / path).exists() or path in current_by_path]

    if allow_absent_preexisting and len(materialized_paths) == 0:
        pass
    else:
        for path, expected in baseline.items():
            change = current_by_path.get(path)
            if change is None:
                report.violations.append(
                    f"El cambio preexistente desapareció o fue incorporado sin autorización: {path}."
                )
                continue
            if change.status != str(expected["status"]):
                report.violations.append(
                    f"Estado alterado para cambio preexistente {path}: "
                    f"esperado {expected['status']!r}, actual {change.status!r}."
                )
            actual_hash = _hash_path(repo_root / path)
            if actual_hash != str(expected["sha256"]):
                report.violations.append(
                    f"Contenido alterado fuera de la tarea activa: {path}."
                )

    task_changes: list[WorktreeChange] = []
    for change in changes:
        if change.path in baseline:
            continue
        task_changes.append(change)
        if _matches(change.path, forbidden_paths):
            report.violations.append(f"Ruta expresamente prohibida modificada: {change.path}.")
            continue
        if not _matches(change.path, allowed_paths):
            report.violations.append(f"Ruta fuera de allowed_paths: {change.path}.")

    mode = str(task["mode"])
    non_control_changes = [c for c in task_changes if c.path not in CONTROL_PATHS]
    if mode in {"read_only", "validation"} and non_control_changes:
        report.violations.append(
            f"El modo {mode} no permite modificaciones: "
            + ", ".join(change.path for change in non_control_changes)
            + "."
        )
    elif mode == "design":
        invalid_design_paths = [c.path for c in non_control_changes if not _validate_design_mode(c.path)]
        if invalid_design_paths:
            report.violations.append(
                "El modo design sólo admite documentación gobernada: "
                + ", ".join(invalid_design_paths)
                + "."
            )

    dependency_patterns = task.get("dependency_files", DEFAULT_DEPENDENCY_FILES)
    dependency_change_authorized = bool(task.get("dependency_file_changes_authorized", False))
    changed_dependency_files = [
        change.path for change in task_changes if _matches(change.path, dependency_patterns)
    ]
    if changed_dependency_files and not dependency_change_authorized:
        report.violations.append(
            "Archivos de dependencias modificados sin autorización explícita: "
            + ", ".join(changed_dependency_files)
            + "."
        )
    if changed_dependency_files and not task["allowed_new_dependencies"]:
        report.violations.append(
            "La tarea modifica dependencias pero allowed_new_dependencies está vacío."
        )

    provider_scan_paths = task.get("provider_scan_paths", DEFAULT_PROVIDER_SCAN_PATHS)
    provider_markers = task.get("provider_markers", DEFAULT_PROVIDER_MARKERS)
    allowed_providers = {str(item).strip().lower() for item in task["allowed_providers"]}
    for change in task_changes:
        if not _matches(change.path, provider_scan_paths):
            continue
        added = _added_text(repo_root, change).casefold()
        for provider, markers in provider_markers.items():
            provider_name = str(provider).casefold()
            if provider_name in allowed_providers:
                continue
            if any(str(marker).casefold() in added for marker in markers):
                report.violations.append(
                    f"Proveedor no autorizado detectado en líneas agregadas de {change.path}: {provider}."
                )

    diff_check = _run_git(repo_root, "diff", "--check", check=False)
    if diff_check.returncode != 0:
        report.violations.append(
            "git diff --check falló:\n" + (diff_check.stdout + diff_check.stderr).strip()
        )

    report.notes.append(f"Tarea: {task['task_id']} — modo {mode}.")
    report.notes.append(f"Cambios de esta tarea detectados: {len(task_changes)}.")
    report.notes.append(f"Cambios preexistentes congelados: {len(baseline)}.")
    return report


def _validate_test_spec(repo_root: Path, spec: Mapping[str, Any]) -> tuple[str, Path, list[str]]:
    if not isinstance(spec, Mapping):
        raise GuardConfigurationError("Cada test debe ser un mapping.")
    name = str(spec.get("name", "")).strip()
    cwd_raw = str(spec.get("cwd", ".")).strip() or "."
    command = spec.get("command")
    if not name:
        raise GuardConfigurationError("Cada test debe declarar name.")
    if not isinstance(command, list) or not command or not all(
        isinstance(item, str) and item for item in command
    ):
        raise GuardConfigurationError(
            f"El test {name!r} debe declarar command como lista no vacía de strings."
        )
    cwd_rel = _normalize_repo_path(cwd_raw) if cwd_raw != "." else "."
    cwd = (repo_root / cwd_rel).resolve()
    try:
        cwd.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise GuardConfigurationError(f"cwd fuera del repositorio para test {name!r}.") from exc
    if not cwd.is_dir():
        raise GuardConfigurationError(f"cwd inexistente para test {name!r}: {cwd_rel}")
    return name, cwd, list(command)


def run_declared_tests(repo_root: Path, task: Mapping[str, Any]) -> int:
    preflight = evaluate_task(repo_root, task)
    _print_report(preflight)
    if not preflight.ok:
        return 2
    for spec in task["tests"]:
        name, cwd, command = _validate_test_spec(repo_root, spec)
        print(f"\n[TEST] {name}: {' '.join(command)}")
        completed = subprocess.run(command, cwd=cwd, check=False)
        if completed.returncode != 0:
            print(f"[FAIL] {name}: exit code {completed.returncode}")
            return completed.returncode or 1
        print(f"[PASS] {name}")
    postflight = evaluate_task(repo_root, task)
    _print_report(postflight)
    return 0 if postflight.ok else 2


def check_intent(task: Mapping[str, Any], intent: str) -> GuardReport:
    report = GuardReport()
    key = f"{intent}_authorized"
    if intent not in {"commit", "push"}:
        report.violations.append(f"Intent no soportado: {intent}.")
    elif not bool(task.get(key, False)):
        report.violations.append(f"{intent.upper()} bloqueado por ACTIVE_TASK.yaml ({key}: false).")
    else:
        report.notes.append(f"{intent.upper()} autorizado por la tarea {task['task_id']}.")
    return report


def snapshot(repo_root: Path, excludes: Sequence[str]) -> dict[str, Any]:
    excluded = [_normalize_repo_path(item) for item in excludes]
    entries = []
    for change in list_worktree_changes(repo_root):
        if _matches(change.path, excluded):
            continue
        entries.append(
            {
                "path": change.path,
                "status": change.status,
                "sha256": _hash_path(repo_root / change.path),
            }
        )
    return {
        "head": _run_git(repo_root, "rev-parse", "HEAD").stdout.strip(),
        "preexisting_changes": entries,
    }


def _print_report(report: GuardReport) -> None:
    for note in report.notes:
        print(f"[INFO] {note}")
    for violation in report.violations:
        print(f"[BLOCK] {violation}", file=sys.stderr)
    print("[PASS] ACTIVE_TASK respetada." if report.ok else "[FAIL] ACTIVE_TASK violada.")


def _repo_root_from_script() -> Path:
    root = Path(__file__).resolve().parents[1]
    completed = _run_git(root, "rev-parse", "--show-toplevel")
    return Path(completed.stdout.strip()).resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task-file",
        default="ops/ACTIVE_TASK.yaml",
        help="Ruta relativa al repositorio del contrato activo.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="Valida alcance, baseline y políticas.")
    subparsers.add_parser("run-tests", help="Valida y ejecuta sólo los tests declarados.")
    intent_parser = subparsers.add_parser("intent", help="Comprueba autorización de commit o push.")
    intent_parser.add_argument("intent", choices=("commit", "push"))
    snapshot_parser = subparsers.add_parser(
        "snapshot", help="Imprime el baseline YAML del worktree actual."
    )
    snapshot_parser.add_argument("--exclude", action="append", default=[])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = _repo_root_from_script()
    if args.command == "snapshot":
        data = snapshot(repo_root, args.exclude)
        if yaml is not None:
            print(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), end="")
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    task_path = repo_root / _normalize_repo_path(args.task_file)
    try:
        task = load_task(task_path)
        if args.command == "check":
            report = evaluate_task(repo_root, task)
            _print_report(report)
            return 0 if report.ok else 2
        if args.command == "run-tests":
            return run_declared_tests(repo_root, task)
        if args.command == "intent":
            report = check_intent(task, args.intent)
            _print_report(report)
            return 0 if report.ok else 2
    except (GuardConfigurationError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
