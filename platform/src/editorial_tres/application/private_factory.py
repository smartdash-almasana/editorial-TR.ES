"""Executable private editorial factory for complete plain-text manuscripts."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Literal

from pydantic import BaseModel, Field, field_validator

from editorial_tres.application.app_book_compiler import AppBookCompiler, AppBookPackage
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
from editorial_tres.domain.review_history import ReviewHistory
from editorial_tres.domain.reviews import ReviewFinding
from editorial_tres.domain.text_analysis import SpanishTextAnalyzer, TextAnalysisSnapshot
from editorial_tres.domain.work import Work
from editorial_tres.infrastructure.html_edition_renderer import HtmlEditionRenderer
from editorial_tres.infrastructure.memory.event_store import MemoryEventStore
from editorial_tres.infrastructure.pdf_edition_renderer import PdfEditionRenderer


_CHAPTER = re.compile(r"^CAPÍTULO\s+([IVXLCDM]+)$", flags=re.IGNORECASE)
_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n+")


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

    @property
    def paragraphs(self) -> tuple[str, ...]:
        """Preserve paragraph boundaries without interpreting literary semantics."""

        return tuple(
            paragraph
            for paragraph in _PARAGRAPH_BREAK.split(self.body)
            if paragraph.strip()
        )


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


class EditionApprovalInput(BaseModel):
    """Human publication authorization bound to one exact prepared Work."""

    approval_id: str
    work_id: str
    source_work_version: int = Field(ge=1)
    source_manuscript_version: int = Field(ge=1)
    status: Literal["approved"]
    actor_id: str
    reason: str
    decided_at: datetime

    model_config = {"frozen": True}

    @field_validator("approval_id", "work_id", "actor_id", "reason")
    @classmethod
    def _required_approval_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La aprobación final requiere identidad, actor y fundamento.")
        return normalized

    def approve(self, work: Work) -> EditionApproval:
        if (
            self.work_id != work.work_id.value
            or self.source_work_version != work.version
            or self.source_manuscript_version != work.manuscript_version
        ):
            raise ValueError("La aprobación no corresponde al snapshot editorial preparado.")
        return EditionApproval.for_work(
            work,
            approval_id=self.approval_id,
        ).approve(
            actor_id=ActorId(value=self.actor_id),
            reason=self.reason,
            decided_at=self.decided_at,
        )


@dataclass(frozen=True)
class PrivateFactoryReviewResult:
    manuscript: ParsedManuscript
    analysis: TextAnalysisSnapshot
    findings: tuple[ReviewFinding, ...]
    reviewed_work: Work


@dataclass(frozen=True)
class PrivateFactoryPreparedResult:
    manuscript: ParsedManuscript
    analysis: TextAnalysisSnapshot
    findings: tuple[ReviewFinding, ...]
    decisions: tuple[FindingDecision, ...]
    final_work: Work
    pending_approval: EditionApproval

    @property
    def accepted_count(self) -> int:
        return sum(decision.status == "accepted" for decision in self.decisions)

    @property
    def rejected_count(self) -> int:
        return sum(decision.status == "rejected" for decision in self.decisions)

    def approval_template(self) -> dict[str, object]:
        return {
            "approval_id": self.pending_approval.approval_id,
            "work_id": self.pending_approval.work_id.value,
            "source_work_version": self.pending_approval.source_work_version,
            "source_manuscript_version": self.pending_approval.source_manuscript_version,
            "status": None,
            "actor_id": "",
            "reason": "",
            "decided_at": None,
        }


@dataclass(frozen=True)
class PrivateFactoryResult:
    manuscript: ParsedManuscript
    analysis: TextAnalysisSnapshot
    findings: tuple[ReviewFinding, ...]
    decisions: tuple[FindingDecision, ...]
    final_work: Work
    master_edition: EditionSnapshot
    app_book: AppBookPackage
    html: str
    pdf_bytes: bytes
    edition_approval: EditionApproval

    @property
    def accepted_count(self) -> int:
        return sum(decision.status == "accepted" for decision in self.decisions)

    @property
    def rejected_count(self) -> int:
        return sum(decision.status == "rejected" for decision in self.decisions)


class PrivateEditorialFactory:
    """Govern a persistent manuscript from ingestion to public derivatives."""

    def __init__(
        self,
        *,
        event_store: Any | None = None,
        work_projection: CurrentWorkProjection | None = None,
        parser: PlainTextManuscriptParser | None = None,
        analyzer: SpanishTextAnalyzer | None = None,
        orthotypographic: SpanishOrthotypographicCorrector | None = None,
        grammar: SpanishGrammarCorrector | None = None,
        projector: EditionProjector | None = None,
        app_book_compiler: AppBookCompiler | None = None,
        html_renderer: HtmlEditionRenderer | None = None,
        pdf_renderer: PdfEditionRenderer | None = None,
    ) -> None:
        self._store = event_store if event_store is not None else MemoryEventStore()
        self._projection = work_projection or CurrentWorkProjection()
        self._parser = parser or PlainTextManuscriptParser()
        self._analyzer = analyzer or SpanishTextAnalyzer()
        self._orthotypographic = orthotypographic or SpanishOrthotypographicCorrector()
        self._grammar = grammar or SpanishGrammarCorrector()
        self._projector = projector or EditionProjector()
        self._app_book_compiler = app_book_compiler or AppBookCompiler()
        self._html_renderer = html_renderer or HtmlEditionRenderer()
        self._pdf_renderer = pdf_renderer or PdfEditionRenderer()

    def review(
        self,
        source: str,
        *,
        tenant_id: TenantId,
        editorial_id: EditorialId,
        work_id: WorkId,
        actor_id: ActorId,
        language: str = "es",
    ) -> PrivateFactoryReviewResult:
        manuscript = self._parser.parse(source)
        work = self._load_or_ingest(
            manuscript,
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
            actor_id=actor_id,
            language=language,
        )
        analysis = self._analyzer.analyze(work, branch_id="main")
        findings = self._analyze(analysis)
        reviewed_work = self._persist_findings(
            work,
            findings=findings,
            actor_id=actor_id,
        )
        return PrivateFactoryReviewResult(
            manuscript=manuscript,
            analysis=analysis,
            findings=findings,
            reviewed_work=reviewed_work,
        )

    def prepare(
        self,
        source: str,
        *,
        tenant_id: TenantId,
        editorial_id: EditorialId,
        work_id: WorkId,
        actor_id: ActorId,
        language: str = "es",
        decisions: Iterable[EditorialDecisionInput] = (),
        decided_at: datetime | None = None,
    ) -> PrivateFactoryPreparedResult:
        manuscript = self._parser.parse(source)
        work = self._load_or_ingest(
            manuscript,
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
            actor_id=actor_id,
            language=language,
        )
        analysis = self._analyzer.analyze(work, branch_id="main")
        findings = self._analyze(analysis)
        reviewed_work = self._persist_findings(
            work,
            findings=findings,
            actor_id=actor_id,
        )
        timestamp = decided_at or datetime.now(timezone.utc)
        resolved = self._resolve_decisions(
            findings,
            decisions=tuple(decisions),
            actor_id=actor_id,
            decided_at=timestamp,
        )
        decided_work = self._persist_decisions(
            reviewed_work,
            decisions=resolved,
            actor_id=actor_id,
        )
        accepted = tuple(
            AcceptedFindingDecision(finding=finding, decision=decision)
            for finding, decision in zip(findings, resolved, strict=True)
            if decision.status == "accepted"
        )
        final_work = self._apply_accepted(
            decided_work,
            accepted=accepted,
            actor_id=actor_id,
            decided_at=timestamp,
        )
        pending_approval = EditionApproval.for_work(
            final_work,
            approval_id=f"edition-approval.{final_work.work_id.value}.v1",
        )
        return PrivateFactoryPreparedResult(
            manuscript=manuscript,
            analysis=analysis,
            findings=findings,
            decisions=resolved,
            final_work=final_work,
            pending_approval=pending_approval,
        )

    def publish(
        self,
        source: str,
        *,
        tenant_id: TenantId,
        editorial_id: EditorialId,
        work_id: WorkId,
        actor_id: ActorId,
        approval: EditionApprovalInput,
        language: str = "es",
        author: str | None = None,
        publisher: str = "Editorial TR.ES",
    ) -> PrivateFactoryResult:
        manuscript = self._parser.parse(source)
        final_work = self._load_existing(
            manuscript,
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
            language=language,
        )
        history = ReviewHistory.replay(
            self._store.get_events(tenant_id, editorial_id, work_id)
        )
        unresolved = history.unresolved_findings()
        if unresolved:
            raise ValueError("La obra todavía contiene findings sin decisión editorial.")

        edition_approval = approval.approve(final_work)
        self._store.save_edition_approval(edition_approval)
        persisted_approval = self._store.get_edition_approval(
            edition_approval.approval_id
        )
        if persisted_approval != edition_approval:
            raise RuntimeError("La aprobación editorial final no pudo persistirse.")

        public_metadata: dict[str, object] = {
            "publisher": publisher.strip() or "Editorial TR.ES",
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
            approval=persisted_approval,
        )
        app_book = self._app_book_compiler.compile(master)
        html = self._html_renderer.render(master)
        pdf_bytes = self._pdf_renderer.render(master)
        findings = tuple(history.findings.values())
        decisions = tuple(
            history.decisions[finding.finding_id]
            for finding in findings
        )
        return PrivateFactoryResult(
            manuscript=manuscript,
            analysis=self._analyzer.analyze(final_work, branch_id="main"),
            findings=findings,
            decisions=decisions,
            final_work=final_work,
            master_edition=master,
            app_book=app_book,
            html=html,
            pdf_bytes=pdf_bytes,
            edition_approval=persisted_approval,
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

    def _load_or_ingest(
        self,
        manuscript: ParsedManuscript,
        *,
        tenant_id: TenantId,
        editorial_id: EditorialId,
        work_id: WorkId,
        actor_id: ActorId,
        language: str,
    ) -> Work:
        events = self._store.get_events(tenant_id, editorial_id, work_id)
        if events:
            return self._load_existing(
                manuscript,
                tenant_id=tenant_id,
                editorial_id=editorial_id,
                work_id=work_id,
                language=language,
            )
        return self._ingest(
            manuscript,
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
            actor_id=actor_id,
            language=language,
        )

    def _load_existing(
        self,
        manuscript: ParsedManuscript,
        *,
        tenant_id: TenantId,
        editorial_id: EditorialId,
        work_id: WorkId,
        language: str,
    ) -> Work:
        events = self._store.get_events(tenant_id, editorial_id, work_id)
        if not events:
            raise ValueError("La obra todavía no fue ingerida en la factoría persistente.")
        work = Work.replay(events)
        hashes = {
            str(block.metadata.get("source_sha256"))
            for block in work.expression_graph.blocks.values()
            if block.metadata.get("source_sha256") is not None
        }
        if hashes != {manuscript.source_sha256}:
            raise ValueError("La fuente actual no coincide con la obra persistida.")
        if work.language != language.strip():
            raise ValueError("El idioma actual no coincide con la obra persistida.")
        self._projection.rebuild_work(events)
        return work

    def _ingest(
        self,
        manuscript: ParsedManuscript,
        *,
        tenant_id: TenantId,
        editorial_id: EditorialId,
        work_id: WorkId,
        actor_id: ActorId,
        language: str,
    ) -> Work:
        import uuid
        from editorial_tres.domain.commits import EditorialCommit
        from editorial_tres.domain.events import create_work_created_event, create_content_block_added_event
        from pydantic import BaseModel

        now = datetime.now(timezone.utc)
        events = []

        created_event = create_work_created_event(
            event_id=f"evt-{uuid.uuid4().hex[:16]}",
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
            title=manuscript.title,
            language=language,
            actor_id=actor_id,
            occurred_at=now,
        )
        events.append(created_event)

        version = 1
        for chapter in manuscript.chapters:
            chapter_id = f"chapter-{chapter.ordinal:02d}"
            blocks = [
                (
                    chapter_id,
                    "heading",
                    f"{chapter.label}\n{chapter.title}",
                    None,
                    chapter.ordinal - 1,
                    {
                        "chapter_ordinal": chapter.ordinal,
                        "source_sha256": manuscript.source_sha256,
                    },
                )
            ]
            blocks.extend(
                (
                    f"{chapter_id}-paragraph-{paragraph_ordinal:03d}",
                    "paragraph",
                    paragraph,
                    chapter_id,
                    paragraph_ordinal - 1,
                    {
                        "chapter_ordinal": chapter.ordinal,
                        "paragraph_ordinal": paragraph_ordinal,
                        "source_sha256": manuscript.source_sha256,
                    },
                )
                for paragraph_ordinal, paragraph in enumerate(
                    chapter.paragraphs,
                    start=1,
                )
            )
            for block_id, block_type, content, parent_id, position, metadata in blocks:
                version += 1
                block = {
                    "id": block_id,
                    "block_type": block_type,
                    "content": content,
                    "parent_id": parent_id,
                    "position": position,
                    "language": language,
                    "status": "revised",
                    "metadata": dict(metadata),
                }
                event = create_content_block_added_event(
                    event_id=f"evt-{uuid.uuid4().hex[:16]}",
                    tenant_id=tenant_id,
                    editorial_id=editorial_id,
                    work_id=work_id,
                    aggregate_version=version,
                    actor_id=actor_id,
                    occurred_at=now,
                    block=block,
                )
                events.append(event)

        commit = EditorialCommit(
            commit_id=f"commit-{uuid.uuid4().hex[:16]}",
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
            branch="main",
            parent_commit_id=None,
            events=tuple(events),
            message=f"Ingestión por lote: {manuscript.title}",
            actor_id=actor_id,
            created_at=now,
        )

        class IngestCommand(BaseModel):
            tenant_id: str
            editorial_id: str
            work_id: str
            title: str

        dummy_cmd = IngestCommand(
            tenant_id=tenant_id.value,
            editorial_id=editorial_id.value,
            work_id=work_id.value,
            title=manuscript.title,
        )
        cmd_hash = hashlib.sha256(dummy_cmd.model_dump_json().encode()).hexdigest()

        self._store.append_commit(
            commit,
            idempotency_key=f"factory-ingest.{work_id.value}",
            command_type="IngestCommand",
            payload_hash=cmd_hash,
        )
        self._projection.rebuild_work(
            self._store.get_events(tenant_id, editorial_id, work_id),
            branch="main",
        )
        return Work.replay(self._store.get_events(tenant_id, editorial_id, work_id))

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

    def _persist_findings(
        self,
        work: Work,
        *,
        findings: tuple[ReviewFinding, ...],
        actor_id: ActorId,
    ) -> Work:
        history = ReviewHistory.replay(
            self._store.get_events(work.tenant_id, work.editorial_id, work.work_id)
        )
        version = work.version
        record = RecordReviewFindingHandler(self._store, self._projection)
        for finding in findings:
            existing = history.get_finding(finding.finding_id)
            if existing is not None:
                if (
                    existing.finding_id != finding.finding_id
                    or existing.reviewer_id != finding.reviewer_id
                    or existing.finding_type != finding.finding_type
                    or existing.target_id != finding.target_id
                    or existing.evidence != finding.evidence
                ):
                    raise ValueError(
                        f"El finding '{finding.finding_id}' cambió respecto del persistido."
                    )
                continue
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
        return Work.replay(
            self._store.get_events(work.tenant_id, work.editorial_id, work.work_id)
        )

    def _persist_decisions(
        self,
        work: Work,
        *,
        decisions: tuple[FindingDecision, ...],
        actor_id: ActorId,
    ) -> Work:
        history = ReviewHistory.replay(
            self._store.get_events(work.tenant_id, work.editorial_id, work.work_id)
        )
        version = work.version
        decide = DecideReviewFindingHandler(self._store, self._projection)
        for decision in decisions:
            existing = history.get_decision(decision.finding_id)
            if existing is not None:
                if (
                    existing.status != decision.status
                    or existing.reason != decision.reason
                    or existing.decided_by != decision.decided_by
                ):
                    raise ValueError(
                        f"El finding '{decision.finding_id}' ya posee otra decisión."
                    )
                continue
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
            self._store.get_events(work.tenant_id, work.editorial_id, work.work_id)
        )

    def _apply_accepted(
        self,
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
        ApplyApprovedPatchHandler(self._store, self._projection).handle(
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
            self._store.get_events(work.tenant_id, work.editorial_id, work.work_id)
        )
