"""Editorial TR.ES - Minimal SaaS Web Console.

Wraps the existing PrivateEditorialFactory with a clean FastAPI backend.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure the web directory itself is on sys.path for `from template import ...`
_WEB_DIR = Path(__file__).resolve().parent
if str(_WEB_DIR) not in sys.path:
    sys.path.insert(0, str(_WEB_DIR))

# Ensure platform/src is on sys.path for direct imports
_PLATFORM_SRC = _WEB_DIR.parent / "platform" / "src"
if str(_PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(_PLATFORM_SRC))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from editorial_tres.application.private_factory import (
    EditionApprovalInput,
    EditorialDecisionInput,
    PrivateEditorialFactory,
)
from editorial_tres.composition import compose_application
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId

from template import INDEX_HTML

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent
_PROJECTS_DIR = _ROOT.parent / "projects"
_EXPORTS_DIR = _ROOT.parent / "exports"
_WEB_DATA = _ROOT / "data"
_PROJECTS_INDEX = _WEB_DATA / "projects.json"
_DATABASE_PATH = _WEB_DATA / "factory.sqlite"

_DEFAULT_TENANT = "tenant.tres-private"
_DEFAULT_EDITORIAL = "editorial.tres"
_DEFAULT_ACTOR = "actor.editora"
_DEFAULT_WORKFLOW = "private-editorial-factory-v1"
_DEFAULT_PUBLISHER = "Editorial TR.ES"

# ---------------------------------------------------------------------------
# Projects index (simple JSON store for UI metadata)
# ---------------------------------------------------------------------------


def _load_index() -> dict[str, Any]:
    if _PROJECTS_INDEX.exists():
        try:
            return json.loads(_PROJECTS_INDEX.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"projects": {}}


def _save_index(data: dict[str, Any]) -> None:
    _PROJECTS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    _PROJECTS_INDEX.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.strip().lower())
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or f"project-{uuid.uuid4().hex[:8]}"


def _project_status(project_id: str) -> str:
    """Derive status from the state of files in the project directory."""
    project_dir = _PROJECTS_DIR / project_id
    if not project_dir.exists():
        return "missing"
    exports_dir = _EXPORTS_DIR / project_id
    if exports_dir.exists() and any(exports_dir.glob("*.pdf")):
        return "exportado"
    approval_file = project_dir / "edition-approval.json"
    if approval_file.exists():
        try:
            data = json.loads(approval_file.read_text(encoding="utf-8"))
            if data.get("status") == "approved":
                return "aprobado"
        except Exception:
            pass
        # Has approval template but not yet approved; check if decisions exist
        decisions_file = project_dir / "decisions.json"
        if decisions_file.exists():
            return "revisado"
    findings_file = project_dir / "review-findings.json"
    if findings_file.exists():
        return "revisado"
    return "borrador"


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Editorial TR.ES Console", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (we serve the index.html from the same directory)
_STATIC_DIR = _ROOT / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_factory():
    """Return a PrivateEditorialFactory wired to the shared SQLite database."""
    _DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    application = compose_application(_DATABASE_PATH)
    factory = PrivateEditorialFactory(
        event_store=application.event_store,
        work_projection=application.current_work_projection,
    )
    return factory, application


def _scope_for(project_id: str, language: str = "es") -> dict:
    return {
        "tenant_id": TenantId(value=_DEFAULT_TENANT),
        "editorial_id": EditorialId(value=_DEFAULT_EDITORIAL),
        "work_id": WorkId(value=f"work.{project_id}"),
        "actor_id": ActorId(value=_DEFAULT_ACTOR),
        "language": language,
    }


# ---------------------------------------------------------------------------
# HTML entry point
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(INDEX_HTML)


# ---------------------------------------------------------------------------
# API: Projects
# ---------------------------------------------------------------------------


@app.get("/api/projects")
async def list_projects():
    index = _load_index()
    projects = []
    for pid, meta in index.get("projects", {}).items():
        projects.append(
            {
                "id": pid,
                "title": meta.get("title", pid),
                "author": meta.get("author", ""),
                "language": meta.get("language", "es"),
                "status": _project_status(pid),
                "created_at": meta.get("created_at", ""),
                "word_count": meta.get("word_count", 0),
                "chapter_count": meta.get("chapter_count", 0),
            }
        )
    # Sort by created_at descending
    projects.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    return {"projects": projects}


@app.post("/api/projects")
async def create_project(
    title: str = Form(...),
    author: str = Form(""),
    language: str = Form("es"),
    manuscript: UploadFile = File(...),
):
    """Create a new project with an uploaded manuscript."""
    if not title.strip():
        raise HTTPException(status_code=400, detail="El título es obligatorio.")

    content = await manuscript.read()
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="El manuscrito está vacío.")

    text = content.decode("utf-8", errors="replace")
    sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    word_count = len(re.findall(r"\S+", text))

    # Count chapters (CAPÍTULO roman)
    chapter_count = len(
        re.findall(r"^CAPÍTULO\s+[IVXLCDM]+$", text, flags=re.MULTILINE | re.IGNORECASE)
    )

    project_id = _slugify(title)
    project_dir = _PROJECTS_DIR / project_id
    if project_dir.exists():
        # Avoid collision
        project_id = f"{project_id}-{uuid.uuid4().hex[:6]}"
        project_dir = _PROJECTS_DIR / project_id

    project_dir.mkdir(parents=True, exist_ok=True)
    exports_dir = _EXPORTS_DIR / project_id
    exports_dir.mkdir(parents=True, exist_ok=True)

    # Write manuscript
    manuscript_path = project_dir / "manuscript.txt"
    manuscript_path.write_text(text, encoding="utf-8")

    # Write project.yaml
    yaml_content = (
        f"schema_version: 1\n"
        f"project_id: {project_id}\n"
        f"title: \"{title.strip()}\"\n"
        f"publisher: \"{_DEFAULT_PUBLISHER}\"\n"
        f"author: \"{author.strip()}\"\n"
        f"language: {language.strip() or 'es'}\n"
        f"source_file: manuscript.txt\n"
        f"source_sha256: {sha256}\n"
        f"expected_word_count: {word_count}\n"
        f"expected_chapter_count: {chapter_count}\n"
        f"workflow: {_DEFAULT_WORKFLOW}\n"
    )
    (project_dir / "project.yaml").write_text(yaml_content, encoding="utf-8")

    # Save to index
    index = _load_index()
    index["projects"][project_id] = {
        "title": title.strip(),
        "author": author.strip(),
        "language": language.strip() or "es",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "word_count": word_count,
        "chapter_count": chapter_count,
        "source_sha256": sha256,
    }
    _save_index(index)

    return {
        "id": project_id,
        "title": title.strip(),
        "status": _project_status(project_id),
        "word_count": word_count,
        "chapter_count": chapter_count,
        "message": "Proyecto creado exitosamente.",
    }


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    index = _load_index()
    meta = index.get("projects", {}).get(project_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")

    project_dir = _PROJECTS_DIR / project_id
    status = _project_status(project_id)

    # Load findings if available
    findings = []
    findings_file = project_dir / "review-findings.json"
    if findings_file.exists():
        try:
            findings = json.loads(findings_file.read_text(encoding="utf-8"))
        except Exception:
            findings = []

    # Check for decisions
    decisions = []
    decisions_file = project_dir / "decisions.json"
    if decisions_file.exists():
        try:
            decisions = json.loads(decisions_file.read_text(encoding="utf-8"))
        except Exception:
            decisions = []

    # Check for approval
    approval = None
    approval_file = project_dir / "edition-approval.json"
    if approval_file.exists():
        try:
            approval = json.loads(approval_file.read_text(encoding="utf-8"))
        except Exception:
            approval = None

    # Check for exports
    exports_dir = _EXPORTS_DIR / project_id
    exports = {}
    if exports_dir.exists():
        for ext in ("pdf", "html", "appbook.json"):
            pattern = f"*.{ext}" if ext != "appbook.json" else "*.appbook.json"
            files = list(exports_dir.glob(pattern))
            if files:
                exports[ext] = files[0].name

    return {
        "id": project_id,
        "title": meta.get("title", project_id),
        "author": meta.get("author", ""),
        "language": meta.get("language", "es"),
        "status": status,
        "created_at": meta.get("created_at", ""),
        "word_count": meta.get("word_count", 0),
        "chapter_count": meta.get("chapter_count", 0),
        "findings": findings,
        "decisions": decisions,
        "approval": approval,
        "exports": exports,
    }


@app.post("/api/projects/{project_id}/review")
async def run_review(project_id: str):
    """Execute the editorial review on the manuscript."""
    index = _load_index()
    meta = index.get("projects", {}).get(project_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")

    project_dir = _PROJECTS_DIR / project_id
    manuscript_path = project_dir / "manuscript.txt"
    if not manuscript_path.exists():
        raise HTTPException(status_code=400, detail="Manuscrito no encontrado.")

    source = manuscript_path.read_text(encoding="utf-8")
    scope = _scope_for(project_id, meta.get("language", "es"))

    application = None
    try:
        factory, application = _get_factory()
        review_result = factory.review(source, **scope)

        findings_file = project_dir / "review-findings.json"
        if review_result.findings:
            pending = [
                {
                    "finding_id": f.finding_id,
                    "status": None,
                    "reason": "",
                    "evidence": f.evidence,
                    "proposal": f.replacement_proposals[0].replacement_text
                    if f.replacement_proposals
                    else "",
                    "classification": f.editorial_classification,
                    "finding_type": f.finding_type,
                    "target_id": f.target_id,
                }
                for f in review_result.findings
            ]
            findings_file.write_text(
                json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        else:
            findings_file.write_text("[]", encoding="utf-8")

        return {
            "message": f"Revisión completada. {len(review_result.findings)} findings generados.",
            "findings_count": len(review_result.findings),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo completar la revisión. "
                "Verificá que el manuscrito tenga título y capítulos válidos. "
                f"Detalle técnico: {exc}"
            ),
        )
    finally:
        if application is not None:
            application.close()


@app.get("/api/projects/{project_id}/findings")
async def get_findings(project_id: str):
    project_dir = _PROJECTS_DIR / project_id
    findings_file = project_dir / "review-findings.json"
    if not findings_file.exists():
        return {"findings": []}
    try:
        data = json.loads(findings_file.read_text(encoding="utf-8"))
        return {"findings": data}
    except Exception:
        return {"findings": []}


@app.post("/api/projects/{project_id}/decisions")
async def submit_decisions(project_id: str, decisions: list[dict]):
    """Accept or reject findings and prepare the edition."""
    index = _load_index()
    meta = index.get("projects", {}).get(project_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")

    project_dir = _PROJECTS_DIR / project_id
    manuscript_path = project_dir / "manuscript.txt"
    if not manuscript_path.exists():
        raise HTTPException(status_code=400, detail="Manuscrito no encontrado.")

    source = manuscript_path.read_text(encoding="utf-8")
    scope = _scope_for(project_id, meta.get("language", "es"))

    findings_file = project_dir / "review-findings.json"
    if not findings_file.exists():
        raise HTTPException(
            status_code=400,
            detail="La obra todavía no tiene una revisión editorial.",
        )
    try:
        stored_findings = json.loads(findings_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudieron leer las observaciones persistidas: {exc}",
        )

    expected_ids = {item.get("finding_id") for item in stored_findings}
    supplied_ids = {item.get("finding_id") for item in decisions}
    if supplied_ids != expected_ids or len(decisions) != len(expected_ids):
        missing = sorted(value for value in expected_ids - supplied_ids if value)
        unexpected = sorted(value for value in supplied_ids - expected_ids if value)
        raise HTTPException(
            status_code=400,
            detail=(
                "Debés decidir todas las observaciones exactamente una vez. "
                f"Faltan: {missing}. Inesperadas: {unexpected}."
            ),
        )

    decision_inputs = []
    for d in decisions:
        if "finding_id" not in d or "status" not in d or "reason" not in d:
            raise HTTPException(
                status_code=400,
                detail="Cada decisión debe tener finding_id, status y reason.",
            )
        if d["status"] not in ("accepted", "rejected"):
            raise HTTPException(
                status_code=400,
                detail=f"Status inválido: {d['status']}. Debe ser 'accepted' o 'rejected'.",
            )
        if not str(d["reason"]).strip():
            raise HTTPException(
                status_code=400,
                detail=f"La decisión sobre {d['finding_id']} requiere un fundamento.",
            )
        decision_inputs.append(
            EditorialDecisionInput(
                finding_id=d["finding_id"],
                status=d["status"],
                reason=d["reason"],
            )
        )

    application = None
    try:
        factory, application = _get_factory()
        prepared = factory.prepare(
            source,
            decisions=tuple(decision_inputs),
            **scope,
        )

        # Write approval template
        approval_template = prepared.approval_template()
        approval_file = project_dir / "edition-approval.json"
        approval_file.write_text(
            json.dumps(approval_template, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Save decisions locally for UI
        decisions_file = project_dir / "decisions.json"
        decisions_file.write_text(
            json.dumps(
                [
                    {
                        "finding_id": d.finding_id,
                        "status": d.status,
                        "reason": d.reason,
                    }
                    for d in decision_inputs
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return {
            "message": "Decisiones registradas. Edición preparada para aprobación.",
            "accepted": prepared.accepted_count,
            "rejected": prepared.rejected_count,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al procesar decisiones: {exc}")
    finally:
        if application is not None:
            application.close()


@app.post("/api/projects/{project_id}/approve")
async def approve_edition(project_id: str, approval_data: dict):
    """Approve the edition and generate final outputs."""
    index = _load_index()
    meta = index.get("projects", {}).get(project_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado.")

    project_dir = _PROJECTS_DIR / project_id
    manuscript_path = project_dir / "manuscript.txt"
    if not manuscript_path.exists():
        raise HTTPException(status_code=400, detail="Manuscrito no encontrado.")

    source = manuscript_path.read_text(encoding="utf-8")
    scope = _scope_for(project_id, meta.get("language", "es"))

    approval_file = project_dir / "edition-approval.json"
    if not approval_file.exists():
        raise HTTPException(
            status_code=400,
            detail="La edición todavía no fue preparada para aprobación.",
        )
    try:
        approval_template = json.loads(approval_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo leer la plantilla de aprobación: {exc}",
        )

    # Validate approval data
    required_fields = [
        "approval_id",
        "work_id",
        "source_work_version",
        "source_manuscript_version",
        "status",
        "actor_id",
        "reason",
        "decided_at",
    ]
    for field in required_fields:
        if field not in approval_data:
            raise HTTPException(
                status_code=400, detail=f"Falta el campo: {field}"
            )

    if approval_data.get("status") != "approved":
        raise HTTPException(
            status_code=400, detail="El status debe ser 'approved'."
        )

    bound_fields = (
        "approval_id",
        "work_id",
        "source_work_version",
        "source_manuscript_version",
    )
    mismatched = [
        field
        for field in bound_fields
        if approval_data.get(field) != approval_template.get(field)
    ]
    if mismatched:
        raise HTTPException(
            status_code=400,
            detail=(
                "La aprobación no corresponde a la plantilla preparada. "
                f"Campos incompatibles: {mismatched}."
            ),
        )

    try:
        approval_input = EditionApprovalInput.model_validate(approval_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Datos de aprobación inválidos: {exc}")

    application = None
    try:
        factory, application = _get_factory()
        result = factory.publish(
            source,
            approval=approval_input,
            author=meta.get("author") or None,
            publisher=_DEFAULT_PUBLISHER,
            **scope,
        )

        # Write outputs to exports directory
        exports_dir = _EXPORTS_DIR / project_id
        exports_dir.mkdir(parents=True, exist_ok=True)

        slug = project_id

        # Write files
        (exports_dir / "edition-master.json").write_text(
            result.master_edition.model_dump_json(indent=2), encoding="utf-8"
        )
        (exports_dir / f"{slug}.appbook.json").write_text(
            result.app_book.to_json(indent=2), encoding="utf-8"
        )
        (exports_dir / f"{slug}.html").write_text(result.html, encoding="utf-8")
        (exports_dir / f"{slug}.pdf").write_bytes(result.pdf_bytes)

        # Factory report
        report = {
            "project_id": slug,
            "work_id": result.final_work.work_id.value,
            "source_sha256": result.manuscript.source_sha256,
            "word_count": result.manuscript.word_count,
            "chapter_count": len(result.manuscript.chapters),
            "block_count": len(result.master_edition.blocks),
            "findings": len(result.findings),
            "accepted": result.accepted_count,
            "rejected": result.rejected_count,
            "source_work_version": result.master_edition.source_work_version,
            "source_manuscript_version": result.master_edition.source_manuscript_version,
            "edition_sha256": result.master_edition.digest(),
            "app_book_package_sha256": result.app_book.checksums["package"],
            "approval_id": result.edition_approval.approval_id,
            "pdf_bytes": len(result.pdf_bytes),
        }
        (exports_dir / "factory-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Update approval file with final status
        approval_file = project_dir / "edition-approval.json"
        final_approval = {
            **approval_data,
            "status": "approved",
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
        approval_file.write_text(
            json.dumps(final_approval, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return {
            "message": "Edición aprobada y publicada exitosamente.",
            "report": report,
            "exports": {
                "pdf": f"{slug}.pdf",
                "html": f"{slug}.html",
                "appbook": f"{slug}.appbook.json",
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al aprobar: {exc}")
    finally:
        if application is not None:
            application.close()


@app.get("/api/projects/{project_id}/download/{format}")
async def download_export(project_id: str, format: str):
    """Download an exported file (pdf, html, appbook)."""
    exports_dir = _EXPORTS_DIR / project_id
    if not exports_dir.exists():
        raise HTTPException(status_code=404, detail="No hay exports disponibles.")

    slug = project_id
    file_map = {
        "pdf": f"{slug}.pdf",
        "html": f"{slug}.html",
        "appbook": f"{slug}.appbook.json",
    }

    filename = file_map.get(format)
    if not filename:
        raise HTTPException(
            status_code=400, detail=f"Formato no soportado: {format}"
        )

    file_path = exports_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {filename}")

    media_type = {
        "pdf": "application/pdf",
        "html": "text/html",
        "appbook": "application/json",
    }.get(format, "application/octet-stream")

    return FileResponse(
        str(file_path),
        media_type=media_type,
        filename=filename,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("  Editorial TR.ES - Consola Web")
    print("  http://localhost:8000")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
