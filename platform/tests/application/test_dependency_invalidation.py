import pytest
from editorial_tres.application.commands import AddContentBlockCommand, CreateWorkCommand, EditContentBlockCommand, RegisterDependencyCommand
from editorial_tres.application.handlers import AddContentBlockHandler, CreateWorkHandler, EditContentBlockHandler, RegisterDependencyHandler
from editorial_tres.application.projections import CurrentWorkProjection
from editorial_tres.domain.graphs.dependency import DependencyGraph, ResourceDependency, STALE
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.work import Work
from editorial_tres.exceptions import DuplicateNodeError
from editorial_tres.infrastructure.memory.event_store import MemoryEventStore

TENANT = TenantId(value="tenant.acme")
EDITORIAL = EditorialId(value="editorial.acme")
WORK = WorkId(value="work.dependencies")
ACTOR = ActorId(value="actor.editor")

def dependency(source, dependent, *, tenant=TENANT, editorial=EDITORIAL, work=WORK, source_type="content_block", dependent_type="pdf"):
    return ResourceDependency(tenant_id=tenant, editorial_id=editorial, work_id=work, source_resource_id=source, dependent_resource_id=dependent, source_resource_type=source_type, dependent_resource_type=dependent_type, source_version=1)

def graph(*items, branch="main"):
    value = DependencyGraph(tenant_id=TENANT, editorial_id=EDITORIAL, work_id=WORK, branch=branch)
    for item in items:
        value = value.register(item)
    return value

def command(cls, **overrides):
    values = dict(command_id="cmd", idempotency_key="key", tenant_id=TENANT, editorial_id=EDITORIAL, work_id=WORK, actor_id=ACTOR, expected_version=1)
    values.update(overrides)
    return cls(**values)

def setup_work():
    store, projection = MemoryEventStore(), CurrentWorkProjection()
    CreateWorkHandler(store, projection).handle(command(CreateWorkCommand, command_id="create", idempotency_key="create", expected_version=None, title="Dependencies", language="es"))
    AddContentBlockHandler(store, projection).handle(command(AddContentBlockCommand, command_id="add-source", idempotency_key="add-source", expected_version=1, block_id="block-1", block_type="paragraph", content="Source"))
    AddContentBlockHandler(store, projection).handle(command(AddContentBlockCommand, command_id="add-unrelated", idempotency_key="add-unrelated", expected_version=2, block_id="block-2", block_type="paragraph", content="Unrelated"))
    return store, projection

def register(store, projection, source, dependent, expected_version, key, dependent_type="pdf"):
    return RegisterDependencyHandler(store, projection).handle(command(RegisterDependencyCommand, command_id=f"register-{key}", idempotency_key=f"register-{key}", expected_version=expected_version, source_resource_id=source, dependent_resource_id=dependent, source_resource_type="content_block", dependent_resource_type=dependent_type, source_version=1))

def test_direct_and_transitive_dependencies_are_deterministic():
    value = graph(dependency("block", "summary", dependent_type="summary"), dependency("summary", "pdf"), dependency("block", "metadata", dependent_type="metadata"))
    assert [item.dependent_resource_id for item in value.direct_dependents("block")] == ["metadata", "summary"]
    assert [item.dependent_resource_id for item in value.transitive_dependents("block")] == ["metadata", "summary", "pdf"]

def test_multiple_and_missing_dependencies():
    value = graph(dependency("block", "pdf"), dependency("block", "audio", dependent_type="audio"))
    assert [item.dependent_resource_id for item in value.transitive_dependents("block")] == ["audio", "pdf"]
    assert value.transitive_dependents("unrelated") == []

def test_duplicate_cross_scope_and_branch_isolation():
    value = graph(dependency("block", "pdf"))
    with pytest.raises(DuplicateNodeError): value.register(dependency("block", "pdf"))
    with pytest.raises(ValueError): value.register(dependency("block", "other", tenant=TenantId(value="tenant.other")))
    other_branch = graph(dependency("block", "draft-pdf"), branch="draft")
    assert value.transitive_dependents("block")[0].dependent_resource_id == "pdf"
    assert other_branch.transitive_dependents("block")[0].dependent_resource_id == "draft-pdf"

def test_cycle_does_not_loop_or_invalidate_source():
    value = graph(dependency("block", "summary"), dependency("summary", "pdf"), dependency("pdf", "block"))
    assert [item.dependent_resource_id for item in value.transitive_dependents("block")] == ["summary", "pdf"]

def test_edit_invalidates_only_direct_and_transitive_derivatives_and_replays():
    store, projection = setup_work()
    register(store, projection, "block-1", "summary-1", 3, "summary", "summary")
    register(store, projection, "summary-1", "pdf-1", 4, "pdf")
    register(store, projection, "block-2", "audio-2", 5, "audio", "audio")
    result = EditContentBlockHandler(store, projection).handle(command(EditContentBlockCommand, command_id="edit", idempotency_key="edit", expected_version=6, block_id="block-1", block_type="paragraph", content="Edited"))
    assert result.version == 9
    replayed = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    assert replayed.expression_graph.get_block("block-1").content == "Edited"
    assert replayed.dependency_graph.is_stale("summary-1")
    assert replayed.dependency_graph.is_stale("pdf-1")
    assert next(item for item in replayed.dependency_graph.dependencies if item.dependent_resource_id == "summary-1").source_version == 7
    assert not replayed.dependency_graph.is_stale("audio-2")
    assert not replayed.dependency_graph.is_stale("block-1")
    assert projection.get_work(TENANT, EDITORIAL, WORK).stale_resource_ids == ("pdf-1", "summary-1")

def test_edit_without_dependencies_leaves_only_the_content_event():
    store, projection = setup_work()
    result = EditContentBlockHandler(store, projection).handle(command(EditContentBlockCommand, command_id="edit", idempotency_key="edit", expected_version=3, block_id="block-1", block_type="paragraph", content="Edited"))
    assert result.version == 4
    assert projection.get_work(TENANT, EDITORIAL, WORK).stale_resource_ids == ()

def test_invalidation_is_idempotent():
    store, projection = setup_work(); register(store, projection, "block-1", "pdf-1", 3, "pdf")
    edit = command(EditContentBlockCommand, command_id="edit", idempotency_key="edit", expected_version=4, block_id="block-1", block_type="paragraph", content="Edited")
    first = EditContentBlockHandler(store, projection).handle(edit)
    second = EditContentBlockHandler(store, projection).handle(edit)
    assert second.commit_id == first.commit_id
    assert len([event for event in store.get_events(TENANT, EDITORIAL, WORK) if event.event_type == "derived_resource.invalidated"]) == 1

def test_work_and_editorial_tenant_scopes_do_not_contaminate():
    store, projection = setup_work(); register(store, projection, "block-1", "pdf-1", 3, "pdf")
    other_work = WorkId(value="work.other")
    other_tenant = TenantId(value="tenant.other")
    other_editorial = EditorialId(value="editorial.other")
    for tenant, editorial, work, key in ((TENANT, EDITORIAL, other_work, "work"), (other_tenant, EDITORIAL, WORK, "tenant"), (TENANT, other_editorial, WORK, "editorial")):
        CreateWorkHandler(store, projection).handle(CreateWorkCommand(command_id=f"create-{key}", idempotency_key=f"create-{key}", tenant_id=tenant, editorial_id=editorial, work_id=work, actor_id=ACTOR, title=key, language="es"))
    assert projection.get_work(TENANT, EDITORIAL, WORK).stale_resource_ids == ()
    assert all(projection.get_work(tenant, editorial, work).stale_resource_ids == () for tenant, editorial, work, _ in ((TENANT, EDITORIAL, other_work, "work"), (other_tenant, EDITORIAL, WORK, "tenant"), (TENANT, other_editorial, WORK, "editorial")))


