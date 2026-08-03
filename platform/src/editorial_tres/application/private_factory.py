"""Executable private editorial factory for complete plain-text manuscripts."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Literal

from pydantic import BaseModel, field_validator

from editorial_tres.application.commands import (
    AddContentBlockCommand,
    ApplyApprovedPatchCommand,
    CreateWorkCommand,
    DecideReviewFindingCommand,
    RecordReviewFindingCommand,
)
from editorial_tres.application.edition_projector import EditionProjector
from editorial_tres.application.handlers import (
    AddContentBlockHandler,
    ApplyApprovedPatchHandler,
    CreateWorkHandler,
    DecideReviewFindingHandler,
    RecordReviewFindingHandler,
)
from editorial_tres.application.projections import CurrentWorkProjection
from editorial_tres.domain.approvals import ApprovalGate
from editorial_tres.domain.edition import EditionApproval, EditionSnapshot
from editorial_tres.domain.editorial_passes import (
    AcceptedFindingDecision,
    ApprovedFindingCorrectionsPass,
)
from editorial_tres.domain.finding_decisions import FindingDecision
from editorial_tres.domain.grammar import SpanishGrammarCorrector
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.proofreading import SpanishOrthotypographicCorrector
from editorial_tres.domain.reviews import ReviewFinding
from editorial_tres.domain.text_analysis import SpanishTextAnalyzer, TextAnalysisSnapshot
from editorial_tres.domain.work import Work
from editorial_tres.infrastructure.memory.event_store import MemoryEventStore
from editorial_tres.infrastructure.pdf_edition_renderer import PdfEditionRenderer


_CHAPTER = re.compile(r"^CAPÍTULO\s+([IVXLCDM]+)$", flags=re.IGNORECASE)


class ManuscriptChapter(BaseModel):
    """One chapter preserved from the submitted plain-text manuscript."""

    ordinal: int
    label: str
    title: str
    body: str

    model_config = {"frozen": True}

    @field_validator("label", "title", "body")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Cada capítulo debe conservar etiqueta, título y contenido.")
        return value.strip()


class ParsedManuscript(BaseModel):
    """Immutable, source-identifiable manuscript structure."""

    title: str
    source_sha256: str
    word_count: int
    chapters: tuple[ManuscriptChapter, ...]

    model_config = {"frozen": True}


class PlainTextManuscriptParser:
    """Parse TR.ES plain-text chapter conventions without rewriting prose."""

    def parse(self, source: str) -> ParsedManuscript:
        normalized = source.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
        if not normalized.strip():
            raise ValueError("El manuscrito no puede estar vacío.")
        lines = normalized.split("\n")
        nonempty = [index for index, line in enumerate(lines) if line.strip()]
        if not nonempty:
            raise ValueError("El manuscrito no contiene texto utilizable.")
        title_index = nonempty[0]
        title = lines[title_index].strip()

        starts = [
            index
            for index, line in enumerate(lines)
            if _CHAPTER.fullmatch(line.strip())
        ]
        if not starts:
            raise ValueError("El manuscrito debe declarar al menos un CAPÍTULO romano.")
        if any(line.strip() for line in lines[title_index + 1 : starts[0]]):
            raise ValueError("Hay contenido no estructurado entre el título y el primer capítulo.")

        chapters: list[ManuscriptChapter] = []
        for ordinal, start in enumerate(starts, start=1):
            end = starts[ordinal] if ordinal < len(starts) else len(lines)
            label = lines[start].strip()
            title_line = next(
                (index for index in range(start + 1, end) if lines[index].strip()),
                None,
            )
            if title_line is None:
                raise ValueError(f"{label} no declara título ni contenido.")
            chapter_title = lines[title_line].strip()
            body = "\n".join(lines[title_line + 1 : end]).strip()
            if not body:
                raise ValueError(f"{label} no contiene cuerpo narrativo.")
            chapters.append(
                ManuscriptChapter(
                    ordinal=ordinal,
                    label=label,
                    title=chapter_title,
                    body=body,
                )
            )

        return ParsedManuscript(
            title=title,
            source_sha256=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            word_count=len(re.findall(r"\S+", normalized)),
            chapters=tuple(chapters),
        )


DecisionStatus = Literal["accepted", "rejected"]


class EditorialDecisionInput(BaseModel):
    """Explicit operator decision for exactly one generated finding."""

    finding_id: str
    status: DecisionStatus
    reason: str

    model_config = {"frozen": True}

    @field_validator("finding_id", "reason")
    @classmethod
    def _required_decision_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("La decisión editorial requiere identidad y fundamento.")
        return value.strip()


@dataclass(frozen=True)
class PrivateFactoryReviewResult:
    manuscript: ParsedManuscript
    analysis: TextAnalysisSnapshot
    findings: tuple[ReviewFinding, ...]


@dataclass(frozen=True)
class PrivateFactoryResult:
    manuscript: ParsedManuscript
    analysis: TextAnalysisSnapshot
    findings: tuple[ReviewFinding, ...]
    decisions: tuple[FindingDecision, ...]
    final_work: Work
    master_edition: EditionSnapshot
    pdf_bytes: bytes

    @property
    def accepted_count(self) -> int:
        return sum(decision.status == "accepted" for decision in self.decisions)

    @property
    def rejected_count(self) -> int:
        return sum(decision.status == "rejected" for decision in self.decisions)


class PrivateEditorialFactory:
    """Run one governed manuscript from ingestion to master edition and PDF."""

    def __init__(self) -> None:
        self._parser = PlainTextManuscriptParser()
        self._analyzer = SpanishTextAnalyzer()
        self._orthotypographic = SpanishOrthotypographicCorrector()
        self._grammar = SpanishGrammarCorrector()
        self._projector = EditionProjector()
        self._pdf_renderer = PdfEditionRenderer()

    def review(
        self,
        source: str,
        *,
        tenant_id: TenantId,
        editorial_id: EditorialId,
        work_id: WorkId,
        actor_id: ActorId,
    ) -> PrivateFactoryReviewResult:
        manuscript = self._parser.parse(source)
        _, _, work = self._ingest(
            manuscript,
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
            actor_id=actor_id,
        )
        analysis = self._analyzer.analyze(work, branch_id="main")
        findings = self._analyze(analysis)
        return PrivateFactoryReviewResult(
            manuscript=manuscript,
            analysis=analysis,
            findings=findings,
        )

    def process(
        self,
        source: str,
        *,
        tenant_id: TenantId,
        editorial_id: EditorialId,
        work_id: WorkId,
        actor_id: ActorId,
        author: str | None = None,
        decisions: Iterable[EditorialDecisionInput] = (),
        decided_at: datetime | None = None,
    ) -> PrivateFactoryResult:
        manuscript = self._parser.parse(source)
        store, projection, work = self._ingest(
            manuscript,
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
            actor_id=actor_id,
        )
        analysis = self._analyzer.analyze(work, branch_id="main")
        findings = self._analyze(analysis)
        resolved = self._resolve_decisions(
            findings,
            decisions=tuple(decisions),
            actor_id=actor_id,
            decided_at=decided_at or datetime.now(timezone.utc),
        )
        decided_work = self._persist_review(
            store,
            projection,
            work,
            findings=findings,
            decisions=resolved,
            actor_id=actor_id,
        )
        accepted = tuple(
            AcceptedFindingDecision(finding=finding, decision=decision)
            for finding, decision in zip(findings, resolved, strict=True)
            if decision.status == "accepted"
        )
        final_work = self._apply_accepted(
            store,
            projection,
            decided_work,
            accepted=accepted,
            actor_id=actor_id,
            decided_at=decided_at or datetime.now(timezone.utc),
        )
        edition_approval = EditionApproval.for_work(
            final_work,
            approval_id=f"edition-approval.{final_work.work_id.value}.v1",
        ).approve(
            actor_id=actor_id,
            reason="Revisión editorial resuelta; se autoriza la edición maestra.",
            decided_at=decided_at or datetime.now(timezone.utc),
        )
        public_metadata = {
            "publisher": "Editorial TR.ES",
            "source_sha256": manuscript.source_sha256,
            "chapter_count": len(manuscript.chapters),
            "word_count": manuscript.word_count,
        }
        if author is not None and author.strip():
            public_metadata["author"] = author.strip()
        master = self._projector.project(
            final_work,
            edition_id=f"edition.{final_work.work_id.value}.v1",
            edition_version=1,
            public_metadata=public_metadata,
            approval=edition_approval,
        )
        pdf_bytes = self._pdf_renderer.render(master)
        return PrivateFactoryResult(
            manuscript=manuscript,
            analysis=analysis,
            findings=findings,
            decisions=resolved,
            final_work=final_work,
            master_edition=master,
            pdf_bytes=pdf_bytes,
        )

    def _analyze(
        self,
        analysis: TextAnalysisSnapshot,
    ) -> tuple[ReviewFinding, ...]:
        return tuple(
            sorted(
                (
                    *self._orthotypographic.analyze(analysis),
                    *self._grammar.analyze(analysis),
                ),
                key=lambda item: (
                    analysis.reading_order.index(item.target_id),
                    item.text_binding.span.start if item.text_binding else -1,
                    item.finding_id,
                ),
            )
        )

    @staticmethod
    def _ingest(
        manuscript: ParsedManuscript,
        *,
        tenant_id: TenantId,
        editorial_id: EditorialId,
        work_id: WorkId,
        actor_id: ActorId,
    ) -> tuple[MemoryEventStore, CurrentWorkProjection, Work]:
        store = MemoryEventStore()
        projection = CurrentWorkProjection()
        result = CreateWorkHandler(store, projection).handle(
            CreateWorkCommand(
                command_id=f"factory-create.{work_id.value}",
                idempotency_key=f"factory-create.{work_id.value}",
                tenant_id=tenant_id,
                editorial_id=editorial_id,
                work_id=work_id,
                actor_id=actor_id,
                title=manuscript.title,
                language="es",
            )
        )
        version = result.version
        add = AddContentBlockHandler(store, projection)
        for chapter in manuscript.chapters:
            chapter_id = f"chapter-{chapter.ordinal:02d}"
            for block_id, block_type, content, parent_id, position, metadata in (
                (
                    chapter_id,
                    "heading",
                    f"{chapter.label}\n{chapter.title}",
                    None,
                    chapter.ordinal - 1,
                    {"chapter_ordinal": chapter.ordinal},
                ),
                (
                    f"{chapter_id}-body",
                    "paragraph",
                    chapter.body,
                    chapter_id,
                    0,
                    {"chapter_ordinal": chapter.ordinal},
                ),
            ):
                result = add.handle(
                    AddContentBlockCommand(
                        command_id=f"factory-add.{block_id}",
                        idempotency_key=f"factory-add.{block_id}",
                        tenant_id=tenant_id,
                        editorial_id=editorial_id,
                        work_id=work_id,
                        actor_id=actor_id,
                        expected_version=version,
                        block_id=block_id,
                        block_type=block_type,
                        content=content,
                        parent_id=parent_id,
                        position=position,
                        language="es",
                        status="revised",
                        metadata=metadata,
                    )
                )
                version = result.version
        return store, projection, Work.replay(
            store.get_events(tenant_id, editorial_id, work_id)
        )

    @staticmethod
    def _resolve_decisions(
        findings: tuple[ReviewFinding, ...],
        *,
        decisions: tuple[EditorialDecisionInput, ...],
        actor_id: ActorId,
        decided_at: datetime,
    ) -> tuple[FindingDecision, ...]:
        by_id = {decision.finding_id: decision for decision in decisions}
        if len(by_id) != len(decisions):
            raise ValueError("No puede haber dos decisiones para el mismo finding.")
        expected = {finding.finding_id for finding in findings}
        if set(by_id) != expected:
            missing = sorted(expected - set(by_id))
            unexpected = sorted(set(by_id) - expected)
            raise ValueError(
                "Toda revisión debe quedar resuelta exactamente una vez; "
                f"faltan={missing}, inesperadas={unexpected}."
            )
        resolved: list[FindingDecision] = []
        for finding in findings:
            supplied = by_id[finding.finding_id]
            pending = FindingDecision.for_finding(
                finding,
                decision_id=f"decision.{finding.finding_id}",
            )
            action = pending.accept if supplied.status == "accepted" else pending.reject
            resolved.append(
                action(
                    actor_id=actor_id,
                    reason=supplied.reason,
                    decided_at=decided_at,
                )
            )
        return tuple(resolved)

    @staticmethod
    def _persist_review(
        store: MemoryEventStore,
        projection: CurrentWorkProjection,
        work: Work,
        *,
        findings: tuple[ReviewFinding, ...],
        decisions: tuple[FindingDecision, ...],
        actor_id: ActorId,
    ) -> Work:
        version = work.version
        record = RecordReviewFindingHandler(store, projection)
        decide = DecideReviewFindingHandler(store, projection)
        for finding in findings:
            result = record.handle(
                RecordReviewFindingCommand(
                    command_id=f"factory-record.{finding.finding_id}",
                    idempotency_key=f"factory-record.{finding.finding_id}",
                    tenant_id=work.tenant_id,
                    editorial_id=work.editorial_id,
                    work_id=work.work_id,
                    actor_id=actor_id,
                    expected_version=version,
                    finding=finding,
                )
            )
            version = result.version
        for decision in decisions:
            result = decide.handle(
                DecideReviewFindingCommand(
                    command_id=f"factory-decide.{decision.decision_id}",
                    idempotency_key=f"factory-decide.{decision.decision_id}",
                    tenant_id=work.tenant_id,
                    editorial_id=work.editorial_id,
                    work_id=work.work_id,
                    actor_id=actor_id,
                    expected_version=version,
                    decision=decision,
                )
            )
            version = result.version
        return Work.replay(
            store.get_events(work.tenant_id, work.editorial_id, work.work_id)
        )

    @staticmethod
    def _apply_accepted(
        store: MemoryEventStore,
        projection: CurrentWorkProjection,
        work: Work,
        *,
        accepted: tuple[AcceptedFindingDecision, ...],
        actor_id: ActorId,
        decided_at: datetime,
    ) -> Work:
        if not accepted:
            return work
        patch = ApprovedFindingCorrectionsPass(
            pass_id="pass.private-factory-approved-corrections.v1",
            accepted=accepted,
        ).propose(work)
        approval = ApprovalGate.for_patch(
            patch,
            gate_id="gate.private-factory-approved-corrections.v1",
            required_role="editor",
        ).approve(
            actor_id=actor_id,
            reason="Aplicar únicamente correcciones revisadas y aceptadas.",
            decided_at=decided_at,
        )
        ApplyApprovedPatchHandler(store, projection).handle(
            ApplyApprovedPatchCommand(
                command_id="factory-apply-approved-corrections.v1",
                idempotency_key="factory-apply-approved-corrections.v1",
                tenant_id=work.tenant_id,
                editorial_id=work.editorial_id,
                work_id=work.work_id,
                actor_id=actor_id,
                expected_version=patch.source_version,
                patch=patch,
                approval=approval,
            )
        )
        return Work.replay(
            store.get_events(work.tenant_id, work.editorial_id, work.work_id)
        )
