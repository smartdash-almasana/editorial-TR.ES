"""In-memory event store, with stream-scoped idempotency."""
from hashlib import sha256
from typing import Dict, List, Optional, Tuple
from editorial_tres.domain.commits import EditorialCommit
from editorial_tres.domain.events import DomainEvent
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.exceptions import ConcurrencyError, DuplicateCommitError, DuplicateEventError, InvalidCommitParentError, IdempotencyConflictError

class MemoryEventStore:
    def __init__(self) -> None:
        self._commits: Dict[str, EditorialCommit] = {}
        self._events: Dict[str, DomainEvent] = {}
        self._branches: Dict[str, List[str]] = {}
        self._idempotency: Dict[Tuple[str, str, str], Tuple[str, str]] = {}
    def _branch_key(self, tenant_id: TenantId, editorial_id: EditorialId, work_id: WorkId, branch: str = "main") -> str:
        return f"{tenant_id.value}:{editorial_id.value}:{work_id.value}:{branch}"
    def _idempotency_key(self, commit: EditorialCommit, command_type: str, key: str) -> Tuple[str, str, str]:
        return (self._branch_key(commit.tenant_id, commit.editorial_id, commit.work_id, commit.branch), command_type, key)
    def append_commit(self, commit: EditorialCommit, idempotency_key: Optional[str] = None, command_type: str = "legacy", payload_hash: Optional[str] = None) -> None:
        if commit.commit_id in self._commits: raise DuplicateCommitError(f"El commit con ID '{commit.commit_id}' ya existe.")
        if any((e.tenant_id,e.editorial_id,e.work_id)!=(commit.tenant_id,commit.editorial_id,commit.work_id) for e in commit.events): raise ValueError("Todos los eventos deben pertenecer al stream del commit.")
        if any(e.event_id in self._events for e in commit.events): raise DuplicateEventError("Un event_id ya existe.")
        stream = self._branch_key(commit.tenant_id,commit.editorial_id,commit.work_id,commit.branch); history=self._branches.get(stream,[])
        head_version=0
        if history:
            head=self._commits[history[-1]]; head_version=max(e.aggregate_version for e in head.events)
            if commit.parent_commit_id != head.commit_id: raise InvalidCommitParentError("El parent_commit_id debe coincidir con el head actual.")
        elif commit.parent_commit_id is not None: raise InvalidCommitParentError("El primer commit no tiene parent.")
        expected=list(range(head_version+1, head_version+len(commit.events)+1))
        actual=[e.aggregate_version for e in commit.events]
        if actual != expected: raise ConcurrencyError(f"Versiones no consecutivas: se esperaba {expected}, se recibió {actual}.")
        if idempotency_key:
            idem=self._idempotency_key(commit,command_type,idempotency_key)
            if idem in self._idempotency: raise IdempotencyConflictError(f"La idempotency_key '{idempotency_key}' ya fue utilizada.")
        self._commits[commit.commit_id]=commit; self._branches.setdefault(stream,[]).append(commit.commit_id)
        for event in commit.events: self._events[event.event_id]=event
        if idempotency_key: self._idempotency[self._idempotency_key(commit,command_type,idempotency_key)]=(commit.commit_id,payload_hash or "")
    def get_commits(self, tenant_id, editorial_id, work_id, branch="main") -> List[EditorialCommit]: return [self._commits[c] for c in self._branches.get(self._branch_key(tenant_id,editorial_id,work_id,branch),[])]
    def get_events(self, tenant_id, editorial_id, work_id, branch="main") -> List[DomainEvent]: return [e for c in self.get_commits(tenant_id,editorial_id,work_id,branch) for e in c.events]
    def get_head_commit(self, tenant_id, editorial_id, work_id, branch="main") -> Optional[EditorialCommit]:
        ids=self._branches.get(self._branch_key(tenant_id,editorial_id,work_id,branch),[]); return self._commits[ids[-1]] if ids else None
    def get_idempotent_commit(self, tenant_id, editorial_id, work_id, branch, command_type, key, payload_hash):
        stream=self._branch_key(tenant_id,editorial_id,work_id,branch); result=self._idempotency.get((stream,command_type,key))
        if not result: return None
        commit_id, stored_hash=result
        if stored_hash != payload_hash: raise IdempotencyConflictError("La idempotency_key fue reutilizada con un payload distinto.")
        return self._commits[commit_id]
    def has_idempotency_key(self, key): return any(item[2] == key for item in self._idempotency)
    def get_commits_by_idempotency_key(self, key):
        for (_,_, stored), (commit_id, _) in self._idempotency.items():
            if stored == key: return self._commits[commit_id]
        return None

    def branch_exists(self, tenant_id, editorial_id, work_id, branch: str) -> bool:
        return self._branch_key(tenant_id, editorial_id, work_id, branch) in self._branches
