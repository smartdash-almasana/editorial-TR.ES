"""Application commands."""
from typing import Any, Mapping, Optional
from pydantic import BaseModel, Field, field_validator
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
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
    def _main_only(cls, value):
        if value != "main": raise ValueError("En este corte sólo está habilitada la rama 'main'.")
        return value
class CreateWorkCommand(_Command): title: str; language: str
class AddContentBlockCommand(_Command):
    block_id: str; block_type: str; content: str = ""; parent_id: Optional[str] = None; position: int = Field(default=0, ge=0); language: str = "es"; status: str = "draft"; metadata: Mapping[str, Any] = Field(default_factory=dict); expected_version: int = Field(..., ge=1)
class EditContentBlockCommand(AddContentBlockCommand): pass
class RegisterDependencyCommand(_Command):
    source_resource_id: str; dependent_resource_id: str; source_resource_type: str; dependent_resource_type: str; source_version: int = Field(..., ge=1); metadata: Mapping[str, Any] = Field(default_factory=dict); expected_version: int = Field(..., ge=1)
