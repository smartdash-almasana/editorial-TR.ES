from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph, KnowledgeNode
from editorial_tres.domain.graphs.narrative import NarrativeGraph, NarrativeNode
from editorial_tres.domain.editorial_passes import DeterministicBlockEditPass
from editorial_tres.domain.graphs.dependency import DependencyGraph
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.reviews import RepeatedPhraseReviewer
from editorial_tres.domain.work import Work
from editorial_tres.semantic_memory import (
    AuthorMemory,
    ContextBuilder,
    EditorialMemory,
    MemoryRef,
    MemoryRetriever,
    RetrievalRequest,
    SemanticContextService,
    WorkMemoryProjection,
)


def _work(version: int = 1) -> Work:
    tenant_id = TenantId(value="tenant.demo")
    editorial_id = EditorialId(value="editorial.tres")
    work_id = WorkId(value="work.demo")

    expression = ExpressionGraph(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
    ).add_block(
        ContentBlock(
            id="block-1",
            block_type="paragraph",
            content="Texto canónico de prueba.",
            position=1,
        )
    )
    knowledge = KnowledgeGraph(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
    ).add_node(
        KnowledgeNode(id="concept-1", node_type="concept", title="Memoria")
    )
    narrative = NarrativeGraph(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
    ).add_node(
        NarrativeNode(id="chapter-1", node_type="chapter", title="Capítulo 1")
    )
    dependency = DependencyGraph(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
    )

    return Work(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title="Obra demo",
        language="es",
        version=version,
        knowledge_graph=knowledge,
        narrative_graph=narrative,
        expression_graph=expression,
        dependency_graph=dependency,
    )


def test_work_memory_projection_keeps_versioned_references_not_manuscript_copies():
    work = _work()

    memory = WorkMemoryProjection.from_work(work)

    assert memory.source_version == work.version
    assert {(ref.kind, ref.target_id) for ref in memory.refs} == {
        ("expression_block", "block-1"),
        ("knowledge_node", "concept-1"),
        ("narrative_node", "chapter-1"),
    }
    assert not hasattr(memory, "content")
    assert not hasattr(memory, "expression_blocks")


def test_context_builder_resolves_minimum_selected_context_from_canonical_work():
    work = _work()
    memory = WorkMemoryProjection.from_work(work)

    context = ContextBuilder().build(
        work,
        memory,
        purpose="revisar continuidad local",
        refs=[
            MemoryRef(kind="expression_block", target_id="block-1"),
            MemoryRef(kind="narrative_node", target_id="chapter-1"),
        ],
    )

    assert context.source_version == work.version
    assert context.purpose == "revisar continuidad local"
    assert [block.id for block in context.expression_blocks] == ["block-1"]
    assert [node.id for node in context.narrative_nodes] == ["chapter-1"]
    assert context.knowledge_nodes == []
    assert context.expression_blocks[0] is work.expression_graph.get_block("block-1")


def test_context_builder_rejects_stale_work_memory_projection():
    source_work = _work(version=1)
    current_work = _work(version=2)
    memory = WorkMemoryProjection.from_work(source_work)

    try:
        ContextBuilder().build(
            current_work,
            memory,
            purpose="revisar versión actual",
            refs=[MemoryRef(kind="expression_block", target_id="block-1")],
        )
    except ValueError as exc:
        assert "obsoleta" in str(exc)
    else:
        raise AssertionError("Una memoria obsoleta no debe producir PassMemory.")


def test_memory_retriever_selects_relevant_refs_without_changing_authority():
    work = _work()
    memory = WorkMemoryProjection.from_work(work)

    refs = MemoryRetriever().retrieve(
        work,
        memory,
        RetrievalRequest(query="memoria", max_results=3),
    )

    assert refs == [MemoryRef(kind="knowledge_node", target_id="concept-1")]
    assert memory.source_version == work.version


def test_context_builder_combines_separate_editorial_author_and_work_context_with_budgets():
    work = _work()
    memory = WorkMemoryProjection.from_work(work)
    editorial_memory = EditorialMemory(
        editorial_id=work.editorial_id,
        constitution=["La obra conserva trazabilidad."],
        policies=["Toda mutación requiere aprobación."],
        terminology=["Usar 'obra' como término canónico."],
    )
    author_memory = AuthorMemory(
        author_id="author.demo",
        invariants=["Prefiere precisión conceptual."],
        patterns=["Alterna frases breves y extensas."],
        anti_patterns=["Evitar tono genérico."],
    )

    context = ContextBuilder().build(
        work,
        memory,
        purpose="revisión de precisión",
        refs=[MemoryRef(kind="expression_block", target_id="block-1")],
        editorial_memory=editorial_memory,
        author_memory=author_memory,
        max_editorial_items=2,
        max_author_items=2,
    )

    assert context.editorial_context == [
        "La obra conserva trazabilidad.",
        "Toda mutación requiere aprobación.",
    ]
    assert context.author_context == [
        "Prefiere precisión conceptual.",
        "Alterna frases breves y extensas.",
    ]
    assert [block.id for block in context.expression_blocks] == ["block-1"]


def test_semantic_context_service_binds_reviewer_and_pass_to_same_work_snapshot():
    work = _work()
    memory = WorkMemoryProjection.from_work(work)
    prepared = SemanticContextService().prepare(
        work,
        memory,
        purpose="revisar y proponer cambio local",
        retrieval=RetrievalRequest(query="texto", kinds=["expression_block"]),
    )

    reviewer = RepeatedPhraseReviewer(
        reviewer_id="reviewer.test",
        phrase="prueba",
        minimum_occurrences=2,
    )
    findings = prepared.review(reviewer, work)
    assert findings == ()

    editorial_pass = DeterministicBlockEditPass(
        pass_id="pass.test",
        block_id="block-1",
        replacement_content="Texto canónico corregido.",
    )
    patch = prepared.propose(editorial_pass, work)

    assert patch.source_version == work.version
    assert patch.operations[0].block_id == "block-1"

    stale_work = _work(version=2)
    try:
        prepared.propose(editorial_pass, stale_work)
    except ValueError as exc:
        assert "snapshot" in str(exc)
    else:
        raise AssertionError("PassMemory no debe ejecutarse sobre una versión distinta de Work.")
