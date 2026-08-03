"""Command-line entry point for the persistent private editorial factory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from editorial_tres.application.private_factory import (
    EditionApprovalInput,
    EditorialDecisionInput,
    PrivateEditorialFactory,
)
from editorial_tres.composition import compose_application
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.project_manifest import ProjectManifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Procesa un proyecto privado TR.ES de forma persistente."
    )
    parser.add_argument("project", type=Path, help="project.yaml o carpeta del proyecto")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--actor", required=True, help="Actor humano, por ejemplo actor.editora")
    parser.add_argument("--author")
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--database", type=Path)
    return parser


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _validate_project_expectations(manifest: ProjectManifest, manuscript) -> None:
    if manifest.source_sha256 and manuscript.source_sha256 != manifest.source_sha256:
        raise ValueError(
            "El SHA-256 de source_file no coincide con project.yaml; "
            "la ejecución fue detenida."
        )
    if (
        manifest.expected_word_count is not None
        and manuscript.word_count != manifest.expected_word_count
    ):
        raise ValueError(
            "La cantidad de palabras no coincide con expected_word_count de project.yaml."
        )
    if (
        manifest.expected_chapter_count is not None
        and len(manuscript.chapters) != manifest.expected_chapter_count
    ):
        raise ValueError(
            "La cantidad de capítulos no coincide con expected_chapter_count de project.yaml."
        )


def _scope(manifest: ProjectManifest, actor: str):
    return {
        "tenant_id": TenantId(value=manifest.tenant_id),
        "editorial_id": EditorialId(value=manifest.editorial_id),
        "work_id": WorkId(value=manifest.work_id),
        "actor_id": ActorId(value=actor),
        "language": manifest.language,
    }


def _write_review_template(output_dir: Path, findings) -> None:
    pending = [
        {
            "finding_id": finding.finding_id,
            "status": None,
            "reason": "",
            "evidence": finding.evidence,
            "proposal": finding.replacement_proposals[0].replacement_text,
            "classification": finding.editorial_classification,
        }
        for finding in findings
    ]
    _write_json(output_dir / "review-findings.json", pending)


def _write_publication(output_dir: Path, slug: str, result) -> None:
    (output_dir / "edition-master.json").write_text(
        result.master_edition.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{slug}.appbook.json").write_text(
        result.app_book.to_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{slug}.html").write_text(result.html, encoding="utf-8")
    (output_dir / f"{slug}.pdf").write_bytes(result.pdf_bytes)
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
    _write_json(output_dir / "factory-report.json", report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


def main() -> int:
    args = _parser().parse_args()
    if args.decisions is not None and args.approval is not None:
        raise ValueError(
            "Las decisiones y la aprobación final se realizan en ejecuciones separadas."
        )

    manifest = ProjectManifest.from_yaml(args.project)
    if manifest.workflow != "private-editorial-factory-v1":
        raise ValueError(
            "project.yaml debe declarar workflow: private-editorial-factory-v1."
        )
    source_path = manifest.resolve_source_path()
    source = source_path.read_text(encoding="utf-8")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    database_path = args.database or (args.output_dir / "factory.sqlite")
    scope = _scope(manifest, args.actor)

    with compose_application(database_path) as application:
        factory = PrivateEditorialFactory(
            event_store=application.event_store,
            work_projection=application.current_work_projection,
        )

        if args.approval is not None:
            approval = EditionApprovalInput.model_validate(_read_json(args.approval))
            result = factory.publish(
                source,
                approval=approval,
                author=args.author or manifest.author,
                publisher=manifest.publisher or "Editorial TR.ES",
                **scope,
            )
            _validate_project_expectations(manifest, result.manuscript)
            _write_publication(args.output_dir, manifest.output_slug, result)
            return 0

        if args.decisions is not None:
            payload = _read_json(args.decisions)
            if not isinstance(payload, list):
                raise ValueError("El archivo de decisiones debe contener una lista JSON.")
            decisions = tuple(
                EditorialDecisionInput.model_validate(item) for item in payload
            )
            prepared = factory.prepare(source, decisions=decisions, **scope)
            _validate_project_expectations(manifest, prepared.manuscript)
            _write_json(
                args.output_dir / "edition-approval.json",
                prepared.approval_template(),
            )
            print(
                "Las decisiones quedaron persistidas. Complete edition-approval.json "
                "para autorizar esta versión exacta."
            )
            return 3

        review = factory.review(source, **scope)
        _validate_project_expectations(manifest, review.manuscript)
        if review.findings:
            _write_review_template(args.output_dir, review.findings)
            print(
                "La revisión requiere decisiones explícitas; "
                "review-findings.json contiene campos pendientes e inválidos."
            )
            return 2

        prepared = factory.prepare(source, decisions=(), **scope)
        _write_json(
            args.output_dir / "edition-approval.json",
            prepared.approval_template(),
        )
        print(
            "La revisión no produjo findings. Complete edition-approval.json "
            "para autorizar esta versión exacta."
        )
        return 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
