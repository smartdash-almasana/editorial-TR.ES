"""Command-line entry point for the private editorial factory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from editorial_tres.application.private_factory import (
    EditorialDecisionInput,
    PrivateEditorialFactory,
)
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Procesa un manuscrito privado TR.ES.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--author")
    parser.add_argument("--decisions", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    source = args.source.read_text(encoding="utf-8")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    factory = PrivateEditorialFactory()
    scope = {
        "tenant_id": TenantId(value="tenant.tres-private"),
        "editorial_id": EditorialId(value="editorial.tres"),
        "work_id": WorkId(value="work.una-luz-extrana-en-buenos-aires"),
        "actor_id": ActorId(value="actor.editorial-tres"),
    }
    review = factory.review(source, **scope)
+    if review.findings and args.decisions is None:
+        pending = [
+            {
+                "finding_id": finding.finding_id,
+                "status": "accepted" if finding.editorial_classification == "verified_error" else "rejected",
+                "reason": "REVISAR Y FUNDAMENTAR ANTES DE PUBLICAR",
+                "evidence": finding.evidence,
+                "proposal": finding.replacement_proposals[0].replacement_text,
+                "classification": finding.editorial_classification,
+            }
+            for finding in review.findings
+        ]
+        (args.output_dir / "review-findings.json").write_text(
+            json.dumps(pending, ensure_ascii=False, indent=2),
+            encoding="utf-8",
+        )
+        print("La revisión requiere decisiones explícitas; no se generó una edición.")
+        return 2
+    decisions = ()
+    if args.decisions is not None:
+        payload = json.loads(args.decisions.read_text(encoding="utf-8"))
+        decisions = tuple(EditorialDecisionInput.model_validate(item) for item in payload)
+    result = factory.process(
+        source,
+        author=args.author,
+        decisions=decisions,
+        **scope,
+    )
    (args.output_dir / "edition-master.json").write_text(
        result.master_edition.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "una-luz-extrana-en-buenos-aires.pdf").write_bytes(
        result.pdf_bytes
    )
    report = {
        "source_sha256": result.manuscript.source_sha256,
        "word_count": result.manuscript.word_count,
        "chapter_count": len(result.manuscript.chapters),
        "findings": len(result.findings),
        "accepted": result.accepted_count,
        "rejected": result.rejected_count,
        "source_manuscript_version": result.master_edition.source_manuscript_version,
        "edition_sha256": result.master_edition.digest(),
        "pdf_bytes": len(result.pdf_bytes),
    }
    (args.output_dir / "factory-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
