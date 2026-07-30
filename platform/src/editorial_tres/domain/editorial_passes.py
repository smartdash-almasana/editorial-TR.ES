"""Atomic editorial passes that propose changes without mutating a Work."""

from abc import ABC, abstractmethod
import hashlib

from pydantic import BaseModel, field_validator

from editorial_tres.domain.patches import Patch, PatchOperation
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
