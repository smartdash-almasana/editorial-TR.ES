"""
Pruebas exhaustivas para el Event Store consciente de ramas y aislamiento.
"""

import pytest
from datetime import datetime, timezone
import uuid

from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.commits import EditorialCommit
from editorial_tres.domain.events import DomainEvent
from editorial_tres.domain.work import Work
from editorial_tres.infrastructure.memory.event_store import MemoryEventStore
from editorial_tres.application.projections import CurrentWorkProjection
from editorial_tres.application.commands import (
    CreateWorkCommand,
    AddContentBlockCommand,
    EditContentBlockCommand,
    RegisterDependencyCommand,
    CreateBranchCommand,
)
from editorial_tres.application.handlers import (
    CreateWorkHandler,
    AddContentBlockHandler,
    EditContentBlockHandler,
    RegisterDependencyHandler,
    CreateBranchHandler,
)
from editorial_tres.exceptions import (
    ConcurrencyError,
    BranchAlreadyExistsError,
    BranchNotFoundError,
    WorkNotFoundError,
    GraphCycleError,
)

@pytest.fixture
def store():
    return MemoryEventStore()

@pytest.fixture
def projection():
    return CurrentWorkProjection()

@pytest.fixture
def t():
    return TenantId(value="tenant.almasana")

@pytest.fixture
def e():
    return EditorialId(value="editorial.almasana")

@pytest.fixture
def w():
    return WorkId(value="work.yo-no-soy")

@pytest.fixture
def actor():
    return ActorId(value="actor.user-001")


# 1. Comportamiento anterior sobre main
def test_main_branch_legacy_behavior(store, projection, t, e, w, actor):
    cmd_create = CreateWorkCommand(
        command_id="cmd-1",
        idempotency_key="idem-1",
        tenant_id=t,
        editorial_id=e,
        work_id=w,
        actor_id=actor,
        title="Main Work",
        language="es"
    )
    CreateWorkHandler(store, projection).handle(cmd_create)

    cmd_add = AddContentBlockCommand(
        command_id="cmd-2",
        idempotency_key="idem-2",
        tenant_id=t,
        editorial_id=e,
        work_id=w,
        actor_id=actor,
        expected_version=1,
        block_id="block-1",
        block_type="paragraph",
        content="Contenido original"
    )
    AddContentBlockHandler(store, projection).handle(cmd_add)

    p_work = projection.get_work(t, e, w, branch="main")
    assert p_work.version == 2
    assert p_work.title == "Main Work"


# 2. Append independiente entre main y otra rama
def test_independent_append_between_branches(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Obra", language="es")
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="main", expected_version=1, block_id="b-main", block_type="paragraph", content="Bloque main")
    )

    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-4", idempotency_key="i-4", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="draft", expected_version=1, block_id="b-draft", block_type="paragraph", content="Bloque draft")
    )

    work_main = projection.get_work(t, e, w, branch="main")
    work_draft = projection.get_work(t, e, w, branch="draft")

    assert work_main.version == 2
    assert work_draft.version == 2

    events_main = store.get_events(t, e, w, branch="main")
    events_draft = store.get_events(t, e, w, branch="draft")

    assert any(e.payload.get("block", {}).get("id") == "b-main" for e in events_main if e.event_type == "content_block.added")
    assert not any(e.payload.get("block", {}).get("id") == "b-draft" for e in events_main if e.event_type == "content_block.added")

    assert any(e.payload.get("block", {}).get("id") == "b-draft" for e in events_draft if e.event_type == "content_block.added")
    assert not any(e.payload.get("block", {}).get("id") == "b-main" for e in events_draft if e.event_type == "content_block.added")


# 3. Versiones independientes por rama
def test_independent_versions_per_branch(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Obra", language="es")
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="main", expected_version=1, block_id="b-1", block_type="paragraph", content="a")
    )
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-4", idempotency_key="i-4", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="main", expected_version=2, block_id="b-2", block_type="paragraph", content="b")
    )

    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-5", idempotency_key="i-5", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="draft", expected_version=1, block_id="b-3", block_type="paragraph", content="c")
    )

    assert projection.get_work(t, e, w, branch="main").version == 3
    assert projection.get_work(t, e, w, branch="draft").version == 2


# 4. Creación de rama desde última versión
def test_create_branch_from_last_version(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Obra", language="es")
    )
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="main", expected_version=1, block_id="b-1", block_type="paragraph", content="a")
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    events_draft = store.get_events(t, e, w, branch="draft")
    assert len(events_draft) == 2
    assert events_draft[0].event_type == "work.created"
    assert events_draft[1].event_type == "content_block.added"
    assert projection.get_work(t, e, w, branch="draft").version == 2


# 5. Creación desde una versión histórica
def test_create_branch_from_historical_version(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Obra", language="es")
    )
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="main", expected_version=1, block_id="b-1", block_type="paragraph", content="a")
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft", source_version=1)
    )

    events_draft = store.get_events(t, e, w, branch="draft")
    assert len(events_draft) == 1
    assert events_draft[0].event_type == "work.created"
    assert projection.get_work(t, e, w, branch="draft").version == 1


# 6. Estado inicial correcto después del fork
def test_initial_state_after_fork(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Fork Work", language="es")
    )
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="main", expected_version=1, block_id="b-1", block_type="paragraph", content="Hello")
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    work_draft = projection.get_work(t, e, w, branch="draft")
    assert work_draft.title == "Fork Work"
    assert work_draft.version == 2


# 7. Divergencia entre fuente y destino
def test_divergence_between_source_and_target_branches(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Obra", language="es")
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="main", expected_version=1, block_id="b-main", block_type="paragraph", content="Main")
    )

    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-4", idempotency_key="i-4", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="draft", expected_version=1, block_id="b-draft", block_type="paragraph", content="Draft")
    )

    work_main = Work.replay(store.get_events(t, e, w, branch="main"))
    work_draft = Work.replay(store.get_events(t, e, w, branch="draft"))

    assert "b-main" in work_main.expression_graph.blocks
    assert "b-draft" not in work_main.expression_graph.blocks

    assert "b-draft" in work_draft.expression_graph.blocks
    assert "b-main" not in work_draft.expression_graph.blocks


# 8. Rama fuente inexistente
def test_nonexistent_source_branch(store, projection, t, e, w, actor):
    with pytest.raises(BranchNotFoundError):
        CreateBranchHandler(store, projection).handle(
            CreateBranchCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="nonexistent", target_branch="draft")
        )


# 9. Rama destino duplicada
def test_duplicate_target_branch(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Obra", language="es")
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    with pytest.raises(BranchAlreadyExistsError):
        CreateBranchHandler(store, projection).handle(
            CreateBranchCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
        )


# 10. Versión de corte inválida
def test_invalid_cutoff_version(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Obra", language="es")
    )

    with pytest.raises(ConcurrencyError):
        CreateBranchHandler(store, projection).handle(
            CreateBranchCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft", source_version=99)
        )


# 11. Idempotencia de creación
def test_branch_creation_idempotency(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Obra", language="es")
    )

    cmd = CreateBranchCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")

    res1 = CreateBranchHandler(store, projection).handle(cmd)
    res2 = CreateBranchHandler(store, projection).handle(cmd)

    assert res1.commit_id == res2.commit_id


# 12. Aislamiento entre tenants
def test_isolation_between_tenants(store, projection, e, w, actor):
    t1 = TenantId(value="tenant.one")
    t2 = TenantId(value="tenant.two")

    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t1, editorial_id=e, work_id=w, actor_id=actor, title="T1", language="es")
    )
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t2, editorial_id=e, work_id=w, actor_id=actor, title="T2", language="es")
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t1, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    assert store.branch_exists(t1, e, w, "draft") is True
    assert store.branch_exists(t2, e, w, "draft") is False


# 13. Aislamiento entre editoriales
def test_isolation_between_editorials(store, projection, t, w, actor):
    e1 = EditorialId(value="editorial.one")
    e2 = EditorialId(value="editorial.two")

    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e1, work_id=w, actor_id=actor, title="E1", language="es")
    )
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e2, work_id=w, actor_id=actor, title="E2", language="es")
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e1, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    assert store.branch_exists(t, e1, w, "draft") is True
    assert store.branch_exists(t, e2, w, "draft") is False


# 14. Aislamiento entre obras
def test_isolation_between_works(store, projection, t, e, actor):
    w1 = WorkId(value="work.one")
    w2 = WorkId(value="work.two")

    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w1, actor_id=actor, title="W1", language="es")
    )
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w2, actor_id=actor, title="W2", language="es")
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w1, actor_id=actor, source_branch="main", target_branch="draft")
    )

    assert store.branch_exists(t, e, w1, "draft") is True
    assert store.branch_exists(t, e, w2, "draft") is False


# 15. Aislamiento entre ramas
def test_isolation_between_branches(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Obra", language="es")
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft-a")
    )
    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft-b")
    )

    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-4", idempotency_key="i-4", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="draft-a", expected_version=1, block_id="b-a", block_type="paragraph", content="Contenido A")
    )

    assert projection.get_work(t, e, w, branch="draft-a").version == 2
    assert projection.get_work(t, e, w, branch="draft-b").version == 1


# 16. Replay completo de una rama
def test_replay_complete_branch(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Replay Work", language="es")
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="draft", expected_version=1, block_id="b-1", block_type="paragraph", content="First draft content")
    )

    events = store.get_events(t, e, w, branch="draft")
    work = Work.replay(events)

    assert work.version == 2
    assert "b-1" in work.expression_graph.blocks
    assert work.expression_graph.blocks["b-1"].content == "First draft content"


# 17. Dependencias reconstruidas después del fork
def test_dependencies_rebuilt_after_fork(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Deps Work", language="es")
    )
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="main", expected_version=1, block_id="b-1", block_type="paragraph", content="Contenido 1")
    )
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="main", expected_version=2, block_id="b-2", block_type="paragraph", content="Contenido 2")
    )
    RegisterDependencyHandler(store, projection).handle(
        RegisterDependencyCommand(command_id="c-4", idempotency_key="i-4", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="main", expected_version=3, source_resource_id="b-1", dependent_resource_id="b-2", source_resource_type="block", dependent_resource_type="block", source_version=2)
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-5", idempotency_key="i-5", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    work_draft = Work.replay(store.get_events(t, e, w, branch="draft"))
    assert len(work_draft.dependency_graph.dependencies) == 1
    dep = work_draft.dependency_graph.dependencies[0]
    assert dep.source_resource_id == "b-1"
    assert dep.dependent_resource_id == "b-2"


# 18. Invalidación limitada a la rama editada
def test_invalidation_limited_to_edited_branch(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Deps Work", language="es")
    )
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="main", expected_version=1, block_id="b-1", block_type="paragraph", content="Contenido 1")
    )
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="main", expected_version=2, block_id="b-2", block_type="paragraph", content="Contenido 2")
    )
    RegisterDependencyHandler(store, projection).handle(
        RegisterDependencyCommand(command_id="c-4", idempotency_key="i-4", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="main", expected_version=3, source_resource_id="b-1", dependent_resource_id="b-2", source_resource_type="block", dependent_resource_type="block", source_version=2)
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-5", idempotency_key="i-5", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    EditContentBlockHandler(store, projection).handle(
        EditContentBlockCommand(command_id="c-6", idempotency_key="i-6", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="draft", expected_version=4, block_id="b-1", block_type="paragraph", content="New content")
    )

    work_main = Work.replay(store.get_events(t, e, w, branch="main"))
    work_draft = Work.replay(store.get_events(t, e, w, branch="draft"))

    assert work_main.dependency_graph.dependencies[0].status == "fresh"
    assert work_draft.dependency_graph.dependencies[0].status == "stale"


# 19. Ciclos del grafo aislados por rama
def test_graph_cycles_isolated_per_branch(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Deps Work", language="es")
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    work_main = Work.replay(store.get_events(t, e, w, branch="main"))
    work_draft = Work.replay(store.get_events(t, e, w, branch="draft"))

    from editorial_tres.domain.graphs.narrative import NarrativeNode
    node_cycle = NarrativeNode(id="self-ref", node_type="part", title="Self", parent_id="self-ref")

    with pytest.raises(GraphCycleError):
        work_draft.narrative_graph.add_node(node_cycle)

    assert "self-ref" not in work_main.narrative_graph.nodes


# 20. Proyección predeterminada compatible con main
def test_projection_default_falls_back_to_main(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Obra", language="es")
    )

    assert projection.has_work(t, e, w) is True
    work = projection.get_work(t, e, w)
    assert work.title == "Obra"

    works = projection.list_works(t, e)
    assert len(works) == 1
    assert works[0].work_id == w


def test_fork_commit_records_structured_genealogy(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Obra", language="es")
    )
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, expected_version=1, block_id="b-1", block_type="paragraph", content="Contenido")
    )

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    fork_commit = store.get_commits(t, e, w, branch="draft")[0]
    assert fork_commit.parent_branch == "main"
    assert fork_commit.parent_branch_version == 2


def test_forked_events_record_origin_event_ids(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Obra", language="es")
    )
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, expected_version=1, block_id="b-1", block_type="paragraph", content="Contenido")
    )
    source_events = store.get_events(t, e, w, branch="main")

    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    copied_events = store.get_events(t, e, w, branch="draft")
    for source_event, copied_event in zip(source_events, copied_events):
        assert copied_event.event_id != source_event.event_id
        assert copied_event.origin_event_id == source_event.event_id
        assert copied_event.payload == source_event.payload


def test_new_events_and_later_commits_have_no_fork_metadata(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Obra", language="es")
    )
    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-2", idempotency_key="i-2", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )

    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(command_id="c-3", idempotency_key="i-3", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="draft", expected_version=1, block_id="b-1", block_type="paragraph", content="Nuevo")
    )

    later_commit = store.get_commits(t, e, w, branch="draft")[1]
    assert later_commit.parent_branch is None
    assert later_commit.parent_branch_version is None
    assert later_commit.events[0].origin_event_id is None


def test_fork_replay_and_invalidation_remain_operational(store, projection, t, e, w, actor):
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(command_id="c-1", idempotency_key="i-1", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, title="Obra", language="es")
    )
    for version, block_id in ((1, "b-1"), (2, "b-2")):
        AddContentBlockHandler(store, projection).handle(
            AddContentBlockCommand(command_id=f"c-{version + 1}", idempotency_key=f"i-{version + 1}", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, expected_version=version, block_id=block_id, block_type="paragraph", content=block_id)
        )
    RegisterDependencyHandler(store, projection).handle(
        RegisterDependencyCommand(command_id="c-4", idempotency_key="i-4", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, expected_version=3, source_resource_id="b-1", dependent_resource_id="b-2", source_resource_type="block", dependent_resource_type="block", source_version=2)
    )
    CreateBranchHandler(store, projection).handle(
        CreateBranchCommand(command_id="c-5", idempotency_key="i-5", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, source_branch="main", target_branch="draft")
    )
    EditContentBlockHandler(store, projection).handle(
        EditContentBlockCommand(command_id="c-6", idempotency_key="i-6", tenant_id=t, editorial_id=e, work_id=w, actor_id=actor, branch="draft", expected_version=4, block_id="b-1", block_type="paragraph", content="Editado")
    )

    replayed_draft = Work.replay(store.get_events(t, e, w, branch="draft"))
    assert replayed_draft.dependency_graph.dependencies[0].status == "stale"
    projected_draft = projection.get_work(t, e, w, branch="draft")
    assert projected_draft.version == replayed_draft.version
    assert projected_draft.stale_resource_ids == ("b-2",)
