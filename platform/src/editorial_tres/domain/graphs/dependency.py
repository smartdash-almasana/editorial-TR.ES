"""Dependency graph for incremental invalidation of derived editorial resources."""
from typing import Any, List, Mapping, Optional, Tuple
from pydantic import BaseModel, Field, field_validator
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.exceptions import DuplicateNodeError

FRESH = "fresh"
STALE = "stale"

class ResourceDependency(BaseModel):
    tenant_id: TenantId
    editorial_id: EditorialId
    work_id: WorkId
    source_resource_id: str
    dependent_resource_id: str
    source_resource_type: str
    dependent_resource_type: str
    source_version: int = Field(ge=1)
    status: str = FRESH
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    model_config = {"frozen": True}

    @field_validator("status")
    @classmethod
    def _status(cls, value: str) -> str:
        if value not in {FRESH, STALE}:
            raise ValueError("El estado de dependencia debe ser fresh o stale.")
        return value

class DependencyGraph(BaseModel):
    tenant_id: TenantId
    editorial_id: EditorialId
    work_id: WorkId
    branch: str = "main"
    dependencies: Tuple[ResourceDependency, ...] = Field(default_factory=tuple)
    model_config = {"frozen": True}

    def register(self, dependency: ResourceDependency) -> "DependencyGraph":
        if (dependency.tenant_id, dependency.editorial_id, dependency.work_id) != (self.tenant_id, self.editorial_id, self.work_id):
            raise ValueError("La dependencia no pertenece al tenant, editorial y work del grafo.")
        if dependency.source_resource_id == dependency.dependent_resource_id:
            raise ValueError("Un recurso no puede depender de sí mismo.")
        identity = (dependency.source_resource_id, dependency.dependent_resource_id, dependency.source_resource_type, dependency.dependent_resource_type)
        if any((item.source_resource_id, item.dependent_resource_id, item.source_resource_type, item.dependent_resource_type) == identity for item in self.dependencies):
            raise DuplicateNodeError("La dependencia ya existe en el grafo.")
        return DependencyGraph(tenant_id=self.tenant_id, editorial_id=self.editorial_id, work_id=self.work_id, branch=self.branch, dependencies=(*self.dependencies, dependency))

    def direct_dependents(self, resource_id: str) -> List[ResourceDependency]:
        return sorted((item for item in self.dependencies if item.source_resource_id == resource_id), key=lambda item: (item.dependent_resource_type, item.dependent_resource_id))

    def incoming_dependencies(self, resource_id: str) -> List[ResourceDependency]:
        return sorted(
            (item for item in self.dependencies if item.dependent_resource_id == resource_id),
            key=lambda item: (item.source_resource_type, item.source_resource_id),
        )

    def transitive_dependents(self, resource_id: str) -> List[ResourceDependency]:
        result: List[ResourceDependency] = []
        visited = {resource_id}
        pending = list(self.direct_dependents(resource_id))
        while pending:
            dependency = pending.pop(0)
            dependent_id = dependency.dependent_resource_id
            if dependent_id in visited:
                continue
            visited.add(dependent_id)
            result.append(dependency)
            pending.extend(self.direct_dependents(dependent_id))
            pending.sort(key=lambda item: (item.dependent_resource_type, item.dependent_resource_id))
        return result

    def mark_stale(self, resource_id: str, source_version: int) -> "DependencyGraph":
        changed = False
        dependencies = []
        for item in self.dependencies:
            if item.dependent_resource_id == resource_id and item.status != STALE:
                item = item.model_copy(update={"status": STALE, "source_version": source_version})
                changed = True
            dependencies.append(item)
        if not changed:
            return self
        return DependencyGraph(tenant_id=self.tenant_id, editorial_id=self.editorial_id, work_id=self.work_id, branch=self.branch, dependencies=tuple(dependencies))

    def is_stale(self, resource_id: str) -> bool:
        return any(item.dependent_resource_id == resource_id and item.status == STALE for item in self.dependencies)

