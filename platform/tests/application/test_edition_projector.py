import pytest

from editorial_tres.application.edition_projector import EditionProjector
from editorial_tres.domain.graphs.dependency import DependencyGraph
from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph
from editorial_tres.domain.graphs.narrative import NarrativeGraph
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.work import Work


T = TenantId(value="tenant.almasana")
E = EditorialId(value="editorial.tres")
W = WorkId(value="work.casa-del-rio")


def _work(blocks, *, status="approved", version=8, manuscript_version=6):
    return Work(
        tenant_id=T,
        editorial_id=E,
        work_id=W,
        title="La casa del río",
        language="es",
        status=status,
        version=version,
        manuscript_version=manuscript_version,
        knowledge_graph=KnowledgeGraph(
            tenant_id=T, editorial_id=E, work_id=W
        ),
        narrative_graph=NarrativeGraph(
            tenant_id=T, editorial_id=E, work_id=W
        ),
        expression_graph=ExpressionGraph(
            tenant_id=T,
            editorial_id=E,
            work_id=W,
            blocks={block.id: block for block in blocks},
        ),
        dependency_graph=DependencyGraph(
            tenant_id=T, editorial_id=E, work_id=W
        ),
    )


def _realistic_blocks():
    return (
        ContentBlock(
            id="draft-note",
            block_type="note",
            content="No publicar.",
            position=0,
            status="draft",
        ),
        ContentBlock(
            id="chapter",
            block_type="heading",
            content="La casa del río",
            position=1,
            status="approved",
        ),
        ContentBlock(
            id="paragraph",
            block_type="paragraph",
            content="La casa miraba el agua desde hacía cien años.",
            parent_id="chapter",
            position=0,
            status="approved",
            metadata={"role": "opening"},
        ),
        ContentBlock(
            id="closing",
            block_type="paragraph",
            content="Al amanecer, el río devolvió el silencio.",
            position=2,
            status="approved",
        ),
    )


def test_projects_only_approved_blocks_in_hierarchical_reading_order():
    snapshot = EditionProjector().project(
        _work(_realistic_blocks()),
        edition_id="edition.casa-del-rio.v1",
        edition_version=3,
        public_metadata={"author": "Autora de prueba"},
    )

    assert snapshot.edition_id == "edition.casa-del-rio.v1"
    assert snapshot.edition_version == 3
    assert snapshot.source_work_version == 8
    assert snapshot.source_manuscript_version == 6
    assert snapshot.reading_order == ("chapter", "paragraph", "closing")
    assert tuple(block.id for block in snapshot.blocks) == snapshot.reading_order
    assert "draft-note" not in snapshot.reading_order
    assert snapshot.blocks[1].metadata["role"] == "opening"


def test_projection_is_deterministic_independent_of_mapping_insertion_order():
    original = _work(_realistic_blocks())
    reversed_work = _work(tuple(reversed(_realistic_blocks())))
    projector = EditionProjector()
    assert projector.project(original).digest() == projector.project(
        reversed_work
    ).digest()


@pytest.mark.parametrize("status", ["conceived", "structured", "drafting", "review"])
def test_rejects_work_that_is_not_approved(status):
    with pytest.raises(ValueError, match="Work aprobada"):
        EditionProjector().project(_work(_realistic_blocks(), status=status))


def test_rejects_work_without_approved_content():
    blocks = (
        ContentBlock(
            id="draft",
            block_type="paragraph",
            content="Todavía en trabajo.",
            status="draft",
        ),
    )
    with pytest.raises(ValueError, match="no contiene bloques aprobados"):
        EditionProjector().project(_work(blocks))


def test_rejects_approved_child_whose_parent_is_not_approved():
    blocks = (
        ContentBlock(
            id="draft-parent",
            block_type="heading",
            content="Pendiente",
            status="draft",
        ),
        ContentBlock(
            id="approved-child",
            block_type="paragraph",
            content="Texto aprobado.",
            parent_id="draft-parent",
            status="approved",
        ),
    )
    with pytest.raises(ValueError, match="padre no aprobado"):
        EditionProjector().project(_work(blocks))


def test_rejects_empty_approved_heading_as_non_publishable():
    blocks = (
        ContentBlock(
            id="empty-heading",
            block_type="heading",
            content=" ",
            status="approved",
        ),
    )
    with pytest.raises(ValueError, match="no tiene contenido publicable"):
        EditionProjector().project(_work(blocks))


def test_snapshot_detects_a_later_manuscript_change():
    work = _work(_realistic_blocks())
    snapshot = EditionProjector().project(work)
    changed = work.model_copy(
        update={"version": 9, "manuscript_version": 7}
    )
    assert snapshot.is_stale_for(changed) is True
