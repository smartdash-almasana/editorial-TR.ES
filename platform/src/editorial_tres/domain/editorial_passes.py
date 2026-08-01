"""Atomic editorial passes that propose changes without mutating a Work."""

from abc import ABC, abstractmethod
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
            work.version,
        )
        finding_scope = (
            self.finding.tenant_id,
            self.finding.editorial_id,
            self.finding.work_id,
            self.finding.branch,
            self.finding.source_version,
        )
        decision_scope = (
            self.decision.tenant_id,
            self.decision.editorial_id,
            self.decision.work_id,
            self.decision.branch,
            self.decision.source_version,
        )
        if work_scope != finding_scope or work_scope != decision_scope:
            raise ValueError("Work, ReviewFinding y FindingDecision deben referir al mismo snapshot editorial.")

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
