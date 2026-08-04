from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


MANUSCRIPT = """# El puerto y el río

CAPÍTULO I
El comienzo

La gracia  permanece . Llegó,partió.
"""


@pytest.fixture()
def web_app(tmp_path, monkeypatch):
    module = importlib.import_module("app")
    monkeypatch.setattr(module, "_PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(module, "_EXPORTS_DIR", tmp_path / "exports")
    monkeypatch.setattr(module, "_WEB_DATA", tmp_path / "web-data")
    monkeypatch.setattr(module, "_PROJECTS_INDEX", tmp_path / "web-data" / "projects.json")
    monkeypatch.setattr(module, "_DATABASE_PATH", tmp_path / "web-data" / "factory.sqlite")
    return module


@pytest.fixture()
def client(web_app):
    with TestClient(web_app.app) as test_client:
        yield test_client


def create_project(client: TestClient, title: str = "El puerto y el río") -> dict:
    response = client.post(
        "/api/projects",
        data={"title": title, "author": "Auditora", "language": "es"},
        files={"manuscript": ("manuscrito.md", MANUSCRIPT.encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_title_with_accents_generates_safe_work_id(client):
    created = create_project(client, title="El puerto y el río")

    assert created["id"] == "el-puerto-y-el-rio"

    review = client.post(f"/api/projects/{created['id']}/review")

    assert review.status_code == 200, review.text


def test_creation_and_review_use_same_persisted_source(client, web_app):
    created = create_project(client, title="Fuente persistida")
    manuscript_path = web_app._PROJECTS_DIR / created["id"] / "manuscript.txt"

    assert manuscript_path.read_text(encoding="utf-8") == MANUSCRIPT

    first_review = client.post(f"/api/projects/{created['id']}/review")
    second_review = client.post(f"/api/projects/{created['id']}/review")

    assert first_review.status_code == 200, first_review.text
    assert second_review.status_code == 200, second_review.text


def test_successful_review_is_accessible_from_web(client):
    created = create_project(client, title="Revisión web")

    review = client.post(f"/api/projects/{created['id']}/review")
    detail = client.get(f"/api/projects/{created['id']}")
    findings = client.get(f"/api/projects/{created['id']}/findings")

    assert review.status_code == 200, review.text
    assert detail.status_code == 200, detail.text
    assert findings.status_code == 200, findings.text
    assert detail.json()["status"] == "revisado"
    assert isinstance(detail.json()["findings"], list)
    assert isinstance(findings.json()["findings"], list)


def test_failed_review_returns_clear_message(client):
    response = client.post(
        "/api/projects",
        data={"title": "Manuscrito inválido", "author": "Auditora", "language": "es"},
        files={"manuscript": ("manuscrito.md", "Texto sin capítulos".encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 200, response.text

    review = client.post(f"/api/projects/{response.json()['id']}/review")

    assert review.status_code == 500
    assert "No se pudo completar la revisión" in review.json()["detail"]
    assert "título y capítulos válidos" in review.json()["detail"]


def reviewed_project(client: TestClient, title: str = "Flujo editorial completo") -> tuple[dict, list[dict]]:
    created = create_project(client, title=title)
    review = client.post(f"/api/projects/{created['id']}/review")
    assert review.status_code == 200, review.text
    findings_response = client.get(f"/api/projects/{created['id']}/findings")
    assert findings_response.status_code == 200, findings_response.text
    findings = findings_response.json()["findings"]
    assert findings
    return created, findings


def complete_decisions(findings: list[dict]) -> list[dict]:
    return [
        {
            "finding_id": finding["finding_id"],
            "status": "accepted",
            "reason": "Corrección aceptada durante la revisión editorial.",
        }
        for finding in findings
    ]


def test_incomplete_decisions_are_rejected_clearly(client):
    created, findings = reviewed_project(client, title="Decisiones incompletas")

    response = client.post(
        f"/api/projects/{created['id']}/decisions",
        json=complete_decisions(findings[:-1]),
    )

    assert response.status_code == 400, response.text
    assert "todas las observaciones" in response.json()["detail"]
    assert "Faltan" in response.json()["detail"]


def test_invalid_approval_is_rejected_clearly(client):
    created, findings = reviewed_project(client, title="Aprobación inválida")
    decisions = client.post(
        f"/api/projects/{created['id']}/decisions",
        json=complete_decisions(findings),
    )
    assert decisions.status_code == 200, decisions.text

    detail = client.get(f"/api/projects/{created['id']}")
    assert detail.status_code == 200, detail.text
    template = detail.json()["approval"]
    invalid = {
        **template,
        "source_work_version": template["source_work_version"] + 1,
        "status": "approved",
        "actor_id": "actor.editora",
        "reason": "Aprobación editorial de prueba.",
        "decided_at": "2026-08-04T12:00:00+00:00",
    }

    response = client.post(
        f"/api/projects/{created['id']}/approve",
        json=invalid,
    )

    assert response.status_code == 400, response.text
    assert "no corresponde a la plantilla preparada" in response.json()["detail"]
    assert "source_work_version" in response.json()["detail"]


def test_complete_web_flow_publishes_and_downloads_all_formats(client):
    created, findings = reviewed_project(client)

    decisions = client.post(
        f"/api/projects/{created['id']}/decisions",
        json=complete_decisions(findings),
    )
    assert decisions.status_code == 200, decisions.text
    assert decisions.json()["accepted"] == len(findings)
    assert decisions.json()["rejected"] == 0

    detail = client.get(f"/api/projects/{created['id']}")
    assert detail.status_code == 200, detail.text
    approval_template = detail.json()["approval"]
    assert approval_template
    assert approval_template["source_work_version"] > 1

    approval = {
        **approval_template,
        "status": "approved",
        "actor_id": "actor.editora",
        "reason": "Edición completa aprobada para publicación.",
        "decided_at": "2026-08-04T12:00:00+00:00",
    }
    published = client.post(
        f"/api/projects/{created['id']}/approve",
        json=approval,
    )
    assert published.status_code == 200, published.text
    assert published.json()["report"]["accepted"] == len(findings)

    pdf = client.get(f"/api/projects/{created['id']}/download/pdf")
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")

    html = client.get(f"/api/projects/{created['id']}/download/html")
    assert html.status_code == 200, html.text
    assert html.headers["content-type"].startswith("text/html")
    assert "<html" in html.text.lower()

    appbook = client.get(f"/api/projects/{created['id']}/download/appbook")
    assert appbook.status_code == 200, appbook.text
    assert appbook.headers["content-type"].startswith("application/json")
    payload = appbook.json()
    assert payload
