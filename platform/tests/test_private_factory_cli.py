import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path


SOURCE = """OBRA EJECUTABLE

CAPÍTULO I
EL TALLER

El taller tenía  dos puertas.

La editora volvió al amanecer.
"""


def _run_cli(platform: Path, *args: object) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    source_path = str(platform / "src")
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (source_path, environment.get("PYTHONPATH")))
    )
    environment["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "editorial_tres.private_factory_cli",
            *(str(arg) for arg in args),
        ],
        cwd=platform,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_cli_runs_persistent_human_gates_and_all_public_derivatives(tmp_path) -> None:
    platform = Path(__file__).parents[1]
    project = tmp_path / "project"
    output = tmp_path / "output"
    project.mkdir()
    (project / "manuscript.txt").write_text(SOURCE, encoding="utf-8")
    source_sha256 = hashlib.sha256(SOURCE.encode("utf-8")).hexdigest()
    (project / "project.yaml").write_text(
        "\n".join(
            (
                "schema_version: 1",
                "project_id: obra-ejecutable",
                "title: OBRA EJECUTABLE",
                "publisher: Editorial TR.ES",
                "language: es",
                "source_file: manuscript.txt",
                f"source_sha256: {source_sha256}",
                "expected_chapter_count: 1",
                "workflow: private-editorial-factory-v1",
            )
        ),
        encoding="utf-8",
    )

    review = _run_cli(platform, project, output, "--actor", "actor.editora")

    assert review.returncode == 2, review.stderr
    pending = json.loads((output / "review-findings.json").read_text(encoding="utf-8"))
    assert pending[0]["status"] is None
    assert pending[0]["reason"] == ""
    assert not (output / "obra-ejecutable.pdf").exists()

    pending[0]["status"] = "accepted"
    pending[0]["reason"] = "Espacio duplicado confirmado por la editora."
    decisions = output / "decisions.json"
    decisions.write_text(json.dumps(pending, ensure_ascii=False), encoding="utf-8")
    prepared = _run_cli(
        platform,
        project,
        output,
        "--actor",
        "actor.editora",
        "--decisions",
        decisions,
    )

    assert prepared.returncode == 3, prepared.stderr
    approval_path = output / "edition-approval.json"
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    assert approval["status"] is None
    assert approval["reason"] == ""
    approval.update(
        status="approved",
        actor_id="actor.directora-editorial",
        reason="Esta versión exacta queda autorizada para publicación.",
        decided_at="2026-08-03T12:00:00+00:00",
    )
    approval_path.write_text(
        json.dumps(approval, ensure_ascii=False),
        encoding="utf-8",
    )

    published = _run_cli(
        platform,
        project,
        output,
        "--actor",
        "actor.directora-editorial",
        "--approval",
        approval_path,
    )

    assert published.returncode == 0, published.stderr
    assert (output / "obra-ejecutable.pdf").read_bytes().startswith(b"%PDF-")
    assert (output / "obra-ejecutable.html").read_text(encoding="utf-8").startswith(
        "<!doctype html>"
    )
    package = json.loads(
        (output / "obra-ejecutable.appbook.json").read_text(encoding="utf-8")
    )
    assert package["manifest"]["work_id"] == "work.obra-ejecutable"
    assert len(package["blocks"]) == 3
    assert package["blocks"][1]["id"] == "chapter-01-paragraph-001"
    assert package["blocks"][2]["id"] == "chapter-01-paragraph-002"
    assert "El taller tenía dos puertas." in json.dumps(package, ensure_ascii=False)

    with closing(sqlite3.connect(output / "factory.sqlite")) as connection:
        event_count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        approval_count = connection.execute(
            "SELECT COUNT(*) FROM edition_approvals"
        ).fetchone()[0]
    assert event_count >= 6
    assert approval_count == 1


def test_cli_module_imports_without_syntax_error() -> None:
    platform = Path(__file__).parents[1]
    completed = _run_cli(platform, "--help")

    assert completed.returncode == 0, completed.stderr
    assert "project.yaml" in completed.stdout
