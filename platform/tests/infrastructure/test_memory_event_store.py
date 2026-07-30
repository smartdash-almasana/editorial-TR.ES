"""
Pruebas para el Event Store en memoria.
"""

import pytest

from editorial_tres.domain.commits import EditorialCommit
from editorial_tres.domain.events import DomainEvent
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.exceptions import (
    DuplicateCommitError,
    DuplicateEventError,
    InvalidCommitParentError,
)
from editorial_tres.infrastructure.memory.event_store import MemoryEventStore


def _make_event(event_id: str, version: int = 1) -> DomainEvent:
    return DomainEvent(
        event_id=event_id,
        event_type="work.created",
        tenant_id=TenantId(value="tenant.almasana"),
        editorial_id=EditorialId(value="editorial.almasana"),
        work_id=WorkId(value="work.yo-no-soy"),
        aggregate_version=version,
        actor_id=ActorId(value="actor.user-001"),
        payload={"title": "Test"},
    )


def _make_commit(
    commit_id: str,
    events: list,
    parent_commit_id: str = None,
    idempotency_key: str = None,
) -> EditorialCommit:
    return EditorialCommit(
        commit_id=commit_id,
        tenant_id=TenantId(value="tenant.almasana"),
        editorial_id=EditorialId(value="editorial.almasana"),
        work_id=WorkId(value="work.yo-no-soy"),
        branch="main",
        parent_commit_id=parent_commit_id,
        events=events,
        message="Test commit",
        actor_id=ActorId(value="actor.user-001"),
    )


def test_append_and_retrieve_commit():
    store = MemoryEventStore()
    event = _make_event("evt-001")
    commit = _make_commit("commit-001", [event])
    store.append_commit(commit, idempotency_key="key-001")

    commits = store.get_commits(
        commit.tenant_id, commit.editorial_id, commit.work_id
    )
    assert len(commits) == 1
    assert commits[0].commit_id == "commit-001"


def test_duplicate_commit_rejected():
    store = MemoryEventStore()
    event = _make_event("evt-001")
    commit = _make_commit("commit-001", [event])
    store.append_commit(commit)

    with pytest.raises(DuplicateCommitError):
        store.append_commit(commit)


def test_duplicate_event_rejected():
    store = MemoryEventStore()
    event = _make_event("evt-001")
    commit1 = _make_commit("commit-001", [event])
    store.append_commit(commit1)

    # Intentar agregar un commit con el mismo event_id
    commit2 = _make_commit("commit-002", [event])
    with pytest.raises(DuplicateEventError):
        store.append_commit(commit2)


def test_invalid_parent_commit():
    store = MemoryEventStore()
    event1 = _make_event("evt-001")
    commit1 = _make_commit("commit-001", [event1])
    store.append_commit(commit1)

    event2 = _make_event("evt-002", version=2)
    commit2 = _make_commit(
        "commit-002", [event2], parent_commit_id="nonexistent-parent"
    )
    with pytest.raises(InvalidCommitParentError):
        store.append_commit(commit2)


def test_get_head_commit():
    store = MemoryEventStore()
    event1 = _make_event("evt-001")
    commit1 = _make_commit("commit-001", [event1])
    store.append_commit(commit1)

    head = store.get_head_commit(
        commit1.tenant_id, commit1.editorial_id, commit1.work_id
    )
    assert head is not None
    assert head.commit_id == "commit-001"


def test_get_head_commit_empty():
    store = MemoryEventStore()
    head = store.get_head_commit(
        TenantId(value="tenant.almasana"),
        EditorialId(value="editorial.almasana"),
        WorkId(value="work.nonexistent"),
    )
    assert head is None


def test_idempotency_key_check():
    store = MemoryEventStore()
    event = _make_event("evt-001")
    commit = _make_commit("commit-001", [event])
    store.append_commit(commit, idempotency_key="key-001")

    assert store.has_idempotency_key("key-001") is True
    assert store.has_idempotency_key("key-002") is False


def test_get_events():
    store = MemoryEventStore()
    event = _make_event("evt-001")
    commit = _make_commit("commit-001", [event])
    store.append_commit(commit)

    events = store.get_events(
        commit.tenant_id, commit.editorial_id, commit.work_id
    )
    assert len(events) == 1
    assert events[0].event_id == "evt-001"


def test_get_commits_by_idempotency_key():
    store = MemoryEventStore()
    event = _make_event("evt-001")
    commit = _make_commit("commit-001", [event])
    store.append_commit(commit, idempotency_key="key-001")

    retrieved = store.get_commits_by_idempotency_key("key-001")
    assert retrieved is not None
    assert retrieved.commit_id == "commit-001"

    not_found = store.get_commits_by_idempotency_key("nonexistent")
    assert not_found is None
