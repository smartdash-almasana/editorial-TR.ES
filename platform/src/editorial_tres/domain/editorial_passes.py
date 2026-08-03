"""Atomic editorial passes that propose changes without mutating a Work."""

from abc import ABC, abstractmethod
from difflib import SequenceMatcher
import hashlib

from pydantic import BaseModel, field_validator

from editorial_tres.domain.finding_decisions import FindingDecision
from editorial_tres.domain.patches import Patch, PatchOperation
from editorial_tres.domain.reviews import ReviewFinding
from editorial_tres.domain.work import Work


class EditorialPass(ABC):
    """Contract for a specialized pass over an immutable Work snapshot."""

    pass_id: str

    @abstractmethod
    def propose(self, work: Work, branch: str = "main") -> Patch:
        """Return a Patch proposal without mutating ``work``."""
        raise NotImplementedError


class DeterministicBlockEditPass(BaseModel, EditorialPass):
    """Minimal deterministic pass proving the Work -> Pass -> Patch boundary."""

    pass_id: str
    block_id: str
    replacement_content: str

    model_config = {"frozen": True}

    @field_validator("pass_id", "block_id", "replacement_content")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El valor es obligatorio.")
        return value.strip()

    def propose(self, work: Work, branch: str = "main") -> Patch:
        block = work.expression_graph.get_block(self.block_id)
        if block is None:
            raise ValueError(f"El bloque '{self.block_id}' no existe en la obra.")
        if block.content == self.replacement_content:
            raise ValueError("La pasada debe proponer un cambio real.")
        if not branch or not branch.strip():
            raise ValueError("La rama no puede estar vacía.")

        fingerprint = "|".join(
            (
                self.pass_id,
                work.tenant_id.value,
                work.editorial_id.value,
                work.work_id.value,
                branch.strip(),
                str(work.version),
                self.block_id,
                block.content,
                self.replacement_content,
            )
        )
        patch_id = f"patch-{hashlib.sha256(fingerprint.encode()).hexdigest()[:16]}"

        return Patch(
            patch_id=patch_id,
            pass_id=self.pass_id,
            tenant_id=work.tenant_id,
            editorial_id=work.editorial_id,
            work_id=work.work_id,
            branch=branch.strip(),
            source_version=work.version,
            operations=(
                PatchOperation(
                    block_id=self.block_id,
                    before_content=block.content,
                    after_content=self.replacement_content,
                ),
            ),
        )


class FindingDrivenBlockEditPass(BaseModel, EditorialPass):
    """Transformative pass allowed only from one explicitly accepted finding."""

    pass_id: str
    finding: ReviewFinding
    decision: FindingDecision
    replacement_content: str

    model_config = {"frozen": True}

    @field_validator("pass_id", "replacement_content")
    @classmethod
    def _required_finding_pass_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El valor es obligatorio.")
        return value.strip()

    def propose(self, work: Work, branch: str = "main") -> Patch:
        normalized_branch = branch.strip() if branch else ""
        if not normalized_branch:
            raise ValueError("La rama no puede estar vacía.")
        if self.decision.status != "accepted":
            raise ValueError("Sólo un ReviewFinding aceptado puede alimentar una pasada transformadora.")
        if self.decision.finding_id != self.finding.finding_id:
            raise ValueError("La decisión no corresponde al ReviewFinding.")

        work_scope = (
            work.tenant_id,
            work.editorial_id,
            work.work_id,
            normalized_branch,
        )
        finding_scope = (
            self.finding.tenant_id,
            self.finding.editorial_id,
            self.finding.work_id,
            self.finding.branch,
        )
        decision_scope = (
            self.decision.tenant_id,
            self.decision.editorial_id,
            self.decision.work_id,
            self.decision.branch,
        )
        if work_scope != finding_scope or work_scope != decision_scope:
            raise ValueError("Work, ReviewFinding y FindingDecision deben pertenecer al mismo ámbito editorial.")
        if self.finding.source_version != self.decision.source_version:
            raise ValueError("ReviewFinding y FindingDecision deben referir a la misma revisión del manuscrito.")
        if work.manuscript_version != self.finding.source_version:
            raise ValueError("El manuscrito cambió después del ReviewFinding aceptado.")
        if len(self.finding.related_target_ids) > 1:
            raise ValueError(
                "Un hallazgo multibloque no puede alimentar una edición simple de un solo bloque."
            )

        block = work.expression_graph.get_block(self.finding.target_id)
        if block is None:
            raise ValueError(f"El bloque '{self.finding.target_id}' no existe en la obra.")
        if block.content == self.replacement_content:
            raise ValueError("La pasada debe proponer un cambio real.")

        fingerprint = "|".join(
            (
                self.pass_id,
                self.finding.finding_id,
                self.decision.decision_id,
                work.tenant_id.value,
                work.editorial_id.value,
                work.work_id.value,
                normalized_branch,
                str(work.version),
                block.id,
                block.content,
                self.replacement_content,
            )
        )
        patch_id = f"patch-{hashlib.sha256(fingerprint.encode()).hexdigest()[:16]}"

        return Patch(
            patch_id=patch_id,
            pass_id=self.pass_id,
            tenant_id=work.tenant_id,
            editorial_id=work.editorial_id,
            work_id=work.work_id,
            branch=normalized_branch,
            source_version=work.version,
            operations=(
                PatchOperation(
                    block_id=block.id,
                    before_content=block.content,
                    after_content=self.replacement_content,
                ),
            ),
        )


class AcceptedFindingDecision(BaseModel):
    """One exact diagnostic proposal explicitly accepted by an editor."""

    finding: ReviewFinding
    decision: FindingDecision

    model_config = {"frozen": True}


class ApprovedFindingCorrectionsPass(BaseModel, EditorialPass):
    """Collapse non-overlapping accepted span replacements into one atomic Patch."""

    pass_id: str
    accepted: tuple[AcceptedFindingDecision, ...]

    model_config = {"frozen": True}

    @field_validator("pass_id")
    @classmethod
    def _required_approved_pass_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El pass_id es obligatorio.")
        return value.strip()

    @field_validator("accepted")
    @classmethod
    def _non_empty_accepted(
        cls, value: tuple[AcceptedFindingDecision, ...]
    ) -> tuple[AcceptedFindingDecision, ...]:
        if not value:
            raise ValueError("La pasada requiere al menos un finding aceptado.")
        finding_ids = tuple(item.finding.finding_id for item in value)
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("Un finding aceptado no puede aplicarse dos veces.")
        return value

    def propose(self, work: Work, branch: str = "main") -> Patch:
        normalized_branch = branch.strip() if branch else ""
        if not normalized_branch:
            raise ValueError("La rama no puede estar vacía.")

        replacements: dict[str, list[tuple[int, int, str, str]]] = {}
        material_ids: list[str] = []
        for item in self.accepted:
            finding = item.finding
            decision = item.decision
            if decision.status != "accepted" or decision.finding_id != finding.finding_id:
                raise ValueError("Cada corrección debe corresponder a una decisión aceptada.")
            scope = (work.tenant_id, work.editorial_id, work.work_id, normalized_branch)
            finding_scope = (
                finding.tenant_id,
                finding.editorial_id,
                finding.work_id,
                finding.branch,
            )
            decision_scope = (
                decision.tenant_id,
                decision.editorial_id,
                decision.work_id,
                decision.branch,
            )
            if scope != finding_scope or scope != decision_scope:
                raise ValueError("Work, finding y decisión deben compartir alcance editorial.")
            if finding.source_version != decision.source_version:
                raise ValueError("Finding y decisión deben compartir revisión material.")
            if work.manuscript_version != finding.source_version:
                raise ValueError("El manuscrito cambió después del diagnóstico aceptado.")
            if finding.text_binding is None or len(finding.replacement_proposals) != 1:
                raise ValueError("La corrección aceptada requiere un span y una propuesta única.")

            span = finding.text_binding.span
            replacement = finding.replacement_proposals[0].replacement_text
            block = work.expression_graph.get_block(span.block_id)
            if block is None:
                raise ValueError(f"El bloque '{span.block_id}' ya no existe.")
            if block.content[span.start : span.end] != span.evidence:
                raise ValueError("La evidencia aceptada ya no coincide con el bloque fuente.")
            for local_start, local_end, inserted in self._atomic_edits(
                span.evidence,
                replacement,
            ):
                absolute_start = span.start + local_start
                absolute_end = span.start + local_end
                replacements.setdefault(span.block_id, []).append(
                    (
                        absolute_start,
                        absolute_end,
                        block.content[absolute_start:absolute_end],
                        inserted,
                    )
                )
            material_ids.extend((finding.finding_id, decision.decision_id))

        operations: list[PatchOperation] = []
        reading_order = tuple(block.id for block in work.expression_graph.get_all_blocks())
        for block_id in sorted(replacements, key=reading_order.index):
            block = work.expression_graph.get_block(block_id)
            assert block is not None
            edits = sorted(
                set(replacements[block_id]),
                key=lambda item: (item[0], item[1], item[3]),
            )
            previous_end = -1
            for start, end, _, _ in edits:
                if start < previous_end:
                    raise ValueError(
                        "Dos correcciones aceptadas se superponen; requieren arbitraje humano."
                    )
                previous_end = end
            corrected = block.content
            for start, end, evidence, replacement in reversed(edits):
                if corrected[start:end] != evidence:
                    raise ValueError("La aplicación conjunta perdió correspondencia textual.")
                corrected = corrected[:start] + replacement + corrected[end:]
            if corrected == block.content:
                raise ValueError("La pasada aceptada no produjo un cambio material.")
            operations.append(
                PatchOperation(
                    block_id=block_id,
                    before_content=block.content,
                    after_content=corrected,
                )
            )

        fingerprint = "|".join(
            (
                self.pass_id,
                work.tenant_id.value,
                work.editorial_id.value,
                work.work_id.value,
                normalized_branch,
                str(work.version),
                *material_ids,
                *(operation.after_content for operation in operations),
            )
        )
        return Patch(
            patch_id=f"patch-{hashlib.sha256(fingerprint.encode()).hexdigest()[:16]}",
            pass_id=self.pass_id,
            tenant_id=work.tenant_id,
            editorial_id=work.editorial_id,
            work_id=work.work_id,
            branch=normalized_branch,
            source_version=work.version,
            operations=tuple(operations),
        )

    @staticmethod
    def _atomic_edits(source: str, replacement: str) -> tuple[tuple[int, int, str], ...]:
        edits = tuple(
            (source_start, source_end, replacement[target_start:target_end])
            for tag, source_start, source_end, target_start, target_end in SequenceMatcher(
                a=source,
                b=replacement,
                autojunk=False,
            ).get_opcodes()
            if tag != "equal"
        )
        if not edits:
            raise ValueError("La propuesta aceptada no contiene un cambio textual.")
        return edits
