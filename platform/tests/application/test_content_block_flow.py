import pytest
from editorial_tres.application.commands import AddContentBlockCommand, CreateWorkCommand, EditContentBlockCommand
from editorial_tres.application.handlers import AddContentBlockHandler, CreateWorkHandler, EditContentBlockHandler
from editorial_tres.application.projections import CurrentWorkProjection
from editorial_tres.domain.commits import EditorialCommit
from editorial_tres.domain.events import create_content_block_added_event
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.work import Work
from editorial_tres.exceptions import ConcurrencyError, IdempotencyConflictError
from editorial_tres.infrastructure.memory.event_store import MemoryEventStore

T=TenantId(value="tenant.acme"); E=EditorialId(value="editorial.acme"); W=WorkId(value="work.one"); A=ActorId(value="actor.editor")
def setup_work():
    store=MemoryEventStore(); projection=CurrentWorkProjection()
    CreateWorkHandler(store,projection).handle(CreateWorkCommand(command_id="create",idempotency_key="create-key",tenant_id=T,editorial_id=E,work_id=W,actor_id=A,title="One",language="es"))
    return store,projection
def add(command_id="add", key="add-key", content="Primer bloque", version=1):
    return AddContentBlockCommand(command_id=command_id,idempotency_key=key,tenant_id=T,editorial_id=E,work_id=W,actor_id=A,expected_version=version,block_id="b1",block_type="paragraph",content=content)
def test_add_edit_and_replay():
    store, projection=setup_work(); added=AddContentBlockHandler(store,projection).handle(add())
    assert added.version == 2
    edited=EditContentBlockHandler(store,projection).handle(EditContentBlockCommand(**{**add("edit","edit-key","Editado",2).model_dump(), "expected_version":2}))
    assert edited.version == 3
    replayed=Work.replay(store.get_events(T,E,W)); assert replayed.expression_graph.get_block("b1").content == "Editado"
    assert projection.get_work(T,E,W).version == 3
def test_idempotency_and_payload_conflict():
    store, projection=setup_work(); handler=AddContentBlockHandler(store,projection)
    first=handler.handle(add()); assert handler.handle(add()).commit_id == first.commit_id
    with pytest.raises(IdempotencyConflictError): handler.handle(add(content="Distinto"))
def test_incorrect_concurrency_and_projection_idempotency():
    store, projection=setup_work(); event=store.get_events(T,E,W)[0]
    projection.apply(event); projection.apply(event); assert projection.get_work(T,E,W).version == 1
    with pytest.raises(ConcurrencyError): AddContentBlockHandler(store,projection).handle(add(version=4))
def test_tenant_and_editorial_isolation_and_filtered_listing():
    store, projection=setup_work(); other_t=TenantId(value="tenant.other"); other_e=EditorialId(value="editorial.other")
    CreateWorkHandler(store,projection).handle(CreateWorkCommand(command_id="other",idempotency_key="create-key",tenant_id=other_t,editorial_id=other_e,work_id=W,actor_id=A,title="Other",language="es"))
    assert len(projection.list_works(T,E)) == 1
    assert len(projection.list_works(other_t,other_e)) == 1
def test_consecutive_versions_in_a_multi_event_commit_and_cross_work_blocked():
    store, _=setup_work(); now=store.get_events(T,E,W)[0].occurred_at
    event2=create_content_block_added_event(event_id="evt-two",tenant_id=T,editorial_id=E,work_id=W,aggregate_version=2,actor_id=A,occurred_at=now,block={"id":"b2","block_type":"paragraph","content":"two"})
    event3=create_content_block_added_event(event_id="evt-three",tenant_id=T,editorial_id=E,work_id=W,aggregate_version=3,actor_id=A,occurred_at=now,block={"id":"b3","block_type":"paragraph","content":"three"})
    head=store.get_head_commit(T,E,W); store.append_commit(EditorialCommit(commit_id="commit-batch",tenant_id=T,editorial_id=E,work_id=W,parent_commit_id=head.commit_id,events=(event2,event3),message="batch",actor_id=A))
    assert [e.aggregate_version for e in store.get_events(T,E,W)] == [1,2,3]
    other=WorkId(value="work.other")
    with pytest.raises(ValueError): store.append_commit(EditorialCommit(commit_id="bad-cross",tenant_id=T,editorial_id=E,work_id=W,parent_commit_id="commit-batch",events=(create_content_block_added_event(event_id="evt-cross",tenant_id=T,editorial_id=E,work_id=other,aggregate_version=4,actor_id=A,block={"id":"x","block_type":"paragraph","content":"x"}),),message="bad",actor_id=A))

def test_work_rejects_cross_work_graph():
    from editorial_tres.domain.graphs.expression import ExpressionGraph
    from editorial_tres.domain.graphs.knowledge import KnowledgeGraph
    from editorial_tres.domain.graphs.narrative import NarrativeGraph
    with pytest.raises(ValueError):
        Work(tenant_id=T, editorial_id=E, work_id=W, title="bad", language="es",
             knowledge_graph=KnowledgeGraph(tenant_id=T, editorial_id=E, work_id=W),
             narrative_graph=NarrativeGraph(tenant_id=T, editorial_id=E, work_id=W),
             expression_graph=ExpressionGraph(tenant_id=T, editorial_id=E, work_id=WorkId(value="work.other")))
