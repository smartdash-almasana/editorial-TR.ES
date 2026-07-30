"""Application commands."""
from typing import Any, Mapping, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from editorial_tres.domain.approvals import ApprovalGate
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.patches import Patch
class _Command(BaseModel):
    command_id: str; idempotency_key: str; tenant_id: TenantId; editorial_id: EditorialId; work_id: WorkId; actor_id: ActorId; branch: str = "main"; expected_version: Optional[int] = Field(default=None, ge=1)
    model_config = {"frozen": True}
    @field_validator("command_id", "idempotency_key")
    @classmethod
    def _required(cls, value):
        if not value or not value.strip(): raise ValueError("El valor es obligatorio.")
        return value.strip()
    @field_validator("branch")
    @classmethod
    def _validate_branch(cls, value):
        if not value or not value.strip(): raise ValueError("El nombre de la rama no puede estar vacío.")
        return value.strip()
class CreateWorkCommand(_Command): title: str; language: str
class AddContentBlockCommand(_Command):
    block_id: str; block_type: str; content: str = ""; parent_id: Optional[str] = None; position: int = Field(default=0, ge=0); language: str = "es"; status: str = "draft"; metadata: Mapping[str, Any] = Field(default_factory=dict); expected_version: int = Field(..., ge=1)
class EditContentBlockCommand(AddContentBlockCommand): pass
class RegisterDependencyCommand(_Command):
    source_resource_id: str; dependent_resource_id: str; source_resource_type: str; dependent_resource_type: str; source_version: int = Field(..., ge=1); metadata: Mapping[str, Any] = Field(default_factory=dict); expected_version: int = Field(..., ge=1)

class CreateBranchCommand(_Command):
    source_branch: str
    target_branch: str
    source_version: Optional[int] = Field(default=None, ge=1)

    @field_validator("source_branch", "target_branch")
    @classmethod
    def _validate_branch_names(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El nombre de la rama no puede estar vacío.")
        return value.strip()

    @model_validator(mode="after")
    def _sync_branch(self) -> "CreateBranchCommand":
        # Sincronizar el campo heredado 'branch' con 'target_branch'
        object.__setattr__(self, "branch", self.target_branch)
        return self

class ApplyApprovedPatchCommand(_Command):
    patch: Patch
    approval: ApprovalGate
    expected_version: int = Field(..., ge=1)

    @model_validator(mode="after")
    def _match_patch_scope(self) -> "ApplyApprovedPatchCommand":
        if self.approval.status != "approved":
            raise ValueError("El Patch sólo puede aplicarse con una aprobación aprobada.")
        if self.approval.patch_id != self.patch.patch_id:
            raise ValueError("La aprobación no corresponde al Patch.")
        scope = (self.tenant_id, self.editorial_id, self.work_id, self.branch)
        patch_scope = (self.patch.tenant_id, self.patch.editorial_id, self.patch.work_id, self.patch.branch)
        approval_scope = (self.approval.tenant_id, self.approval.editorial_id, self.approval.work_id, self.approval.branch)
        if scope != patch_scope or scope != approval_scope:
            raise ValueError("Comando, Patch y aprobación deben pertenecer al mismo ámbito editorial.")
        if self.expected_version != self.patch.source_version or self.expected_version != self.approval.source_version:
            raise ValueError("La aplicación debe apuntar exactamente a la versión fuente aprobada.")
        return self
