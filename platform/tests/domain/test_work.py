"""
Pruebas para el agregado Work.
"""

import pytest

from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph
from editorial_tres.domain.graphs.narrative import NarrativeGraph, NarrativeNode
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.work import Work
from editorial_tres.exceptions import (
    DuplicateNodeError,
    GraphCycleError,
    MissingParentNodeError,
)


def _make_ids():
    return (
        TenantId(value="tenant.almasana"),
        EditorialId(value="editorial.almasana"),
        WorkId(value="work.yo-no-soy"),
        ActorId(value="actor.user-001"),
    )


def test_create_work_empty_graphs():
    tenant_id, editorial_id, work_id, actor_id = _make_ids()
    work = Work.create(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title="Yo no soy",
        language="es",
        actor_id=actor_id,
        event_id="evt-001",
    )
    assert work.title == "Yo no soy"
    assert len(work.knowledge_graph.nodes) == 0
    assert len(work.narrative_graph.nodes) == 0
    assert len(work.expression_graph.blocks) == 0


def test_work_initial_status_conceived():
    tenant_id, editorial_id, work_id, actor_id = _make_ids()
    work = Work.create(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title="Test",
        language="es",
        actor_id=actor_id,
        event_id="evt-001",
    )
    assert work.status == "conceived"


def test_work_initial_version_one():
    tenant_id, editorial_id, work_id, actor_id = _make_ids()
    work = Work.create(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title="Test",
        language="es",
        actor_id=actor_id,
        event_id="evt-001",
    )
    assert work.version == 1


def test_narrative_nodes_ordered():
    tenant_id, editorial_id, work_id, actor_id = _make_ids()
    work = Work.create(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title="Test",
        language="es",
        actor_id=actor_id,
        event_id="evt-001",
    )
    ng = work.narrative_graph

    n1 = NarrativeNode(id="part-1", node_type="part", title="Parte 1", position=0)
    n2 = NarrativeNode(id="part-2", node_type="part", title="Parte 2", position=1)
    n3 = NarrativeNode(id="part-3", node_type="part", title="Parte 3", position=2)

    ng = ng.add_node(n2)
    ng = ng.add_node(n1)
    ng = ng.add_node(n3)

    all_nodes = ng.get_all_nodes()
    assert [n.id for n in all_nodes] == ["part-1", "part-2", "part-3"]


def test_narrative_missing_parent():
    tenant_id, editorial_id, work_id, actor_id = _make_ids()
    work = Work.create(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title="Test",
        language="es",
        actor_id=actor_id,
        event_id="evt-001",
    )
    ng = work.narrative_graph
    child = NarrativeNode(
        id="chap-1", node_type="chapter", title="Cap 1", parent_id="nonexistent"
    )
    with pytest.raises(MissingParentNodeError):
        ng.add_node(child)


def test_narrative_cycle_detection():
    tenant_id, editorial_id, work_id, actor_id = _make_ids()
    work = Work.create(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title="Test",
        language="es",
        actor_id=actor_id,
        event_id="evt-001",
    )
    ng = work.narrative_graph

    n1 = NarrativeNode(id="n1", node_type="part", title="N1")
    ng = ng.add_node(n1)

    n2 = NarrativeNode(id="n2", node_type="part", title="N2", parent_id="n1")
    ng = ng.add_node(n2)

    # Intentar crear ciclo: n1 -> n2 -> n1 (actualizar n1 con parent n2)
    n1_cycle = NarrativeNode(id="n1", node_type="part", title="N1", parent_id="n2")
    # Esto debería fallar porque n1 ya existe (DuplicateNodeError)
    # Pero primero verificamos que el check de ciclo funcione
    # Creamos un nuevo grafo para probar ciclos
    ng2 = NarrativeGraph(work_id=work_id, nodes={})
    a = NarrativeNode(id="a", node_type="part", title="A")
    ng2 = ng2.add_node(a)
    b = NarrativeNode(id="b", node_type="part", title="B", parent_id="a")
    ng2 = ng2.add_node(b)

    # Intentar agregar c con parent b, y luego intentar agregar
    # un nodo que cierre el ciclo
    c = NarrativeNode(id="c", node_type="part", title="C", parent_id="b")
    ng2 = ng2.add_node(c)

    # Intentar actualizar 'a' con parent 'c' causaría ciclo
    # Como no podemos modificar, agregamos un nuevo nodo que
    # tenga parent que cause ciclo
    # En realidad, la detección de ciclos se da al agregar un nodo
    # cuyo parent chain lleva de vuelta al propio nodo
    # Vamos a probarlo de otra forma: crear un grafo donde
    # intentamos agregar un nodo cuyo parent es él mismo
    ng3 = NarrativeGraph(work_id=work_id, nodes={})
    self_ref = NarrativeNode(id="self", node_type="part", title="Self", parent_id="self")
    # Esto no causaría ciclo porque el nodo no existe aún,
    # pero al agregarlo, el check de ciclo detecta que parent_id == id
    # Revisemos la implementación...
    # En _check_no_cycle, current_id = parent_id, y si current_id == node.id, lanza GraphCycleError
    with pytest.raises(GraphCycleError):
        ng3.add_node(self_ref)


def test_content_block_creation():
    tenant_id, editorial_id, work_id, actor_id = _make_ids()
    work = Work.create(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title="Test",
        language="es",
        actor_id=actor_id,
        event_id="evt-001",
    )
    eg = work.expression_graph

    block = ContentBlock(
        id="block-1",
        block_type="paragraph",
        content="Este es un párrafo de prueba.",
        language="es",
        status="draft",
    )
    eg = eg.add_block(block)
    assert eg.has_block("block-1")
    retrieved = eg.get_block("block-1")
    assert retrieved is not None
    assert retrieved.content == "Este es un párrafo de prueba."


def test_duplicate_node_rejection():
    tenant_id, editorial_id, work_id, actor_id = _make_ids()
    work = Work.create(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title="Test",
        language="es",
        actor_id=actor_id,
        event_id="evt-001",
    )
    ng = work.narrative_graph
    n1 = NarrativeNode(id="n1", node_type="part", title="N1")
    ng = ng.add_node(n1)

    n1_dup = NarrativeNode(id="n1", node_type="chapter", title="N1 duplicado")
    with pytest.raises(DuplicateNodeError):
        ng.add_node(n1_dup)


def test_work_serialization():
    tenant_id, editorial_id, work_id, actor_id = _make_ids()
    work = Work.create(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title="Test Serialization",
        language="es",
        actor_id=actor_id,
        event_id="evt-001",
    )
    data = work.model_dump()
    restored = Work.model_validate(data)
    assert restored.title == work.title
    assert restored.version == work.version
    assert restored.status == work.status
    assert restored.tenant_id == work.tenant_id
    assert restored.editorial_id == work.editorial_id
    assert restored.work_id == work.work_id
    assert restored.created_at == work.created_at
    assert restored.updated_at == work.updated_at


def test_work_empty_title_rejected():
    tenant_id, editorial_id, work_id, actor_id = _make_ids()
    with pytest.raises(Exception):
        Work.create(
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
            title="",
            language="es",
            actor_id=actor_id,
            event_id="evt-001",
        )
