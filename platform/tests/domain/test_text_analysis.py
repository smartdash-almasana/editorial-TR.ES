import pytest
from pydantic import ValidationError

from editorial_tres.domain.graphs.dependency import DependencyGraph
from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph
from editorial_tres.domain.graphs.narrative import NarrativeGraph
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.text_analysis import (
    AnalyzedBlock,
    SpanishTextAnalyzer,
    TextAnalysisSnapshot,
    TextSpan,
)
from editorial_tres.domain.work import Work


TENANT = TenantId(value="tenant.almasana")
EDITORIAL = EditorialId(value="editorial.tres")
WORK = WorkId(value="work.textual-analysis")


def _work(
    blocks: tuple[ContentBlock, ...],
    *,
    language: str = "es",
    version: int = 4,
    manuscript_version: int = 3,
) -> Work:
    return Work(
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        title="Manuscrito de prueba",
        language=language,
        version=version,
        manuscript_version=manuscript_version,
        knowledge_graph=KnowledgeGraph(
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
        ),
        narrative_graph=NarrativeGraph(
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
        ),
        expression_graph=ExpressionGraph(
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            blocks={block.id: block for block in blocks},
        ),
        dependency_graph=DependencyGraph(
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
        ),
    )


def _paragraph(
    block_id: str,
    content: str,
    *,
    parent_id: str | None = None,
    position: int = 0,
    language: str = "es",
) -> ContentBlock:
    return ContentBlock(
        id=block_id,
        block_type="paragraph",
        content=content,
        parent_id=parent_id,
        position=position,
        language=language,
    )


def _analyze(work: Work) -> TextAnalysisSnapshot:
    return SpanishTextAnalyzer().analyze(work, branch_id="main")


def test_snapshot_is_bound_to_the_exact_editorial_manuscript_scope():
    snapshot = _analyze(_work((_paragraph("p1", "Cristo es nuestra paz."),)))

    assert snapshot.tenant_id == TENANT
    assert snapshot.editorial_id == EDITORIAL
    assert snapshot.work_id == WORK
    assert snapshot.branch_id == "main"
    assert snapshot.source_work_version == 4
    assert snapshot.source_manuscript_version == 3
    assert snapshot.language == "es"
    assert snapshot.snapshot_id.startswith("analysis.")


def test_analysis_follows_hierarchical_reading_order_deterministically():
    heading = ContentBlock(
        id="chapter",
        block_type="heading",
        content="Capítulo uno",
        position=1,
    )
    child = _paragraph(
        "child",
        "La gracia llegó primero.",
        parent_id="chapter",
        position=0,
    )
    closing = _paragraph("closing", "Y la esperanza permaneció.", position=2)

    first = _analyze(_work((closing, child, heading)))
    second = _analyze(_work((heading, closing, child)))

    assert first.reading_order == ("chapter", "child", "closing")
    assert first.snapshot_id == second.snapshot_id
    assert [
        span.span_id
        for block in first.blocks
        for span in (*block.paragraphs, *block.sentences, *block.tokens)
    ] == [
        span.span_id
        for block in second.blocks
        for span in (*block.paragraphs, *block.sentences, *block.tokens)
    ]


def test_snapshot_identity_includes_block_structure_not_only_text():
    heading = ContentBlock(
        id="heading",
        block_type="heading",
        content="Título",
        position=0,
    )
    nested = _paragraph(
        "body",
        "Mismo texto.",
        parent_id="heading",
        position=0,
    )
    root = _paragraph("body", "Mismo texto.", position=1)

    nested_snapshot = _analyze(_work((heading, nested)))
    root_snapshot = _analyze(_work((heading, root)))

    assert nested_snapshot.reading_order == root_snapshot.reading_order
    assert nested_snapshot.snapshot_id != root_snapshot.snapshot_id


def test_spanish_dialogue_quotes_and_punctuation_remain_in_exact_sentences():
    content = (
        "—¿Volverás mañana? —preguntó Ana.\n"
        "«Sí —dijo él—, volveré.»"
    )
    block = _analyze(_work((_paragraph("dialogue", content),))).blocks[0]

    assert tuple(span.evidence for span in block.paragraphs) == (
        "—¿Volverás mañana? —preguntó Ana.",
        "«Sí —dijo él—, volveré.»",
    )
    assert tuple(span.evidence for span in block.sentences) == (
        "—¿Volverás mañana? —preguntó Ana.",
        "«Sí —dijo él—, volveré.»",
    )
    assert tuple(token.evidence for token in block.tokens) == (
        "Volverás",
        "mañana",
        "preguntó",
        "Ana",
        "Sí",
        "dijo",
        "él",
        "volveré",
    )


def test_common_spanish_abbreviations_do_not_split_sentences():
    block = _analyze(
        _work(
            (
                _paragraph(
                    "p1",
                    "El Sr. Pérez llegó. Después leyó el cap. 3.",
                ),
            )
        )
    ).blocks[0]

    assert tuple(span.evidence for span in block.sentences) == (
        "El Sr. Pérez llegó.",
        "Después leyó el cap. 3.",
    )


def test_decimal_dot_does_not_split_a_sentence():
    block = _analyze(
        _work((_paragraph("p1", "La relación fue 3.14. Luego cambió."),))
    ).blocks[0]

    assert tuple(span.evidence for span in block.sentences) == (
        "La relación fue 3.14.",
        "Luego cambió.",
    )
    assert "3.14" in tuple(token.evidence for token in block.tokens)


def test_ellipsis_followed_by_lowercase_continues_the_sentence():
    block = _analyze(
        _work((_paragraph("p1", "Esperó... y siguió. Después descansó."),))
    ).blocks[0]

    assert tuple(span.evidence for span in block.sentences) == (
        "Esperó... y siguió.",
        "Después descansó.",
    )


def test_every_emitted_span_recovers_the_exact_source_evidence():
    content = "Primera línea.\n\n  Segunda línea, con espacios.  "
    snapshot = _analyze(_work((_paragraph("p1", content),)))
    block = snapshot.blocks[0]

    for span in (*block.paragraphs, *block.sentences, *block.tokens):
        assert snapshot.evidence_for(span.span_id) == content[span.start : span.end]


def test_span_ids_change_with_material_version_but_not_review_only_version():
    work = _work((_paragraph("p1", "Texto estable."),), version=4, manuscript_version=3)
    first = _analyze(work)
    review_only = _analyze(
        _work(
            (_paragraph("p1", "Texto estable."),),
            version=5,
            manuscript_version=3,
        )
    )
    material_change = _analyze(
        _work(
            (_paragraph("p1", "Texto estable."),),
            version=5,
            manuscript_version=4,
        )
    )

    assert first.snapshot_id == review_only.snapshot_id
    assert first.blocks[0].tokens[0].span_id == review_only.blocks[0].tokens[0].span_id
    assert first.snapshot_id != material_change.snapshot_id
    assert (
        first.blocks[0].tokens[0].span_id
        != material_change.blocks[0].tokens[0].span_id
    )


def test_analysis_does_not_mutate_work_or_its_expression_graph():
    work = _work((_paragraph("p1", "Texto sin mutación."),))
    before = work.model_dump(mode="json")

    _analyze(work)

    assert work.model_dump(mode="json") == before


def test_snapshot_and_nested_models_are_immutable_and_json_serializable():
    snapshot = _analyze(_work((_paragraph("p1", "Texto inmutable."),)))

    with pytest.raises(ValidationError):
        snapshot.branch_id = "otra"
    with pytest.raises(ValidationError):
        snapshot.blocks[0].content = "Alterado"

    dumped = snapshot.model_dump(mode="json")
    assert dumped["blocks"][0]["sentences"][0]["evidence"] == "Texto inmutable."


def test_empty_heading_is_preserved_without_fabricating_spans():
    heading = ContentBlock(
        id="heading",
        block_type="heading",
        content="",
        position=0,
    )
    snapshot = _analyze(_work((heading,)))

    assert snapshot.reading_order == ("heading",)
    assert snapshot.blocks[0].content == ""
    assert snapshot.blocks[0].paragraphs == ()
    assert snapshot.blocks[0].sentences == ()
    assert snapshot.blocks[0].tokens == ()


@pytest.mark.parametrize("language", ["en", "pt-BR", ""])
def test_unsupported_work_language_is_rejected(language):
    with pytest.raises((ValueError, ValidationError), match="idioma|Idioma|obligatorio"):
        _analyze(_work((_paragraph("p1", "Texto."),), language=language))


def test_unsupported_block_language_is_rejected_explicitly():
    work = _work((_paragraph("p1", "Foreign text.", language="en"),))

    with pytest.raises(ValueError, match="bloque 'p1'.*no soportado"):
        _analyze(work)


def test_span_rejects_overlapping_intervals_of_the_same_kind():
    content = "abcdefghij"
    first = TextSpan(
        span_id="span.first",
        kind="paragraph",
        block_id="p1",
        start=0,
        end=6,
        evidence=content[0:6],
        ordinal=0,
    )
    second = TextSpan(
        span_id="span.second",
        kind="paragraph",
        block_id="p1",
        start=5,
        end=10,
        evidence=content[5:10],
        ordinal=1,
    )

    with pytest.raises(ValidationError, match="superponerse"):
        AnalyzedBlock(
            block_id="p1",
            block_type="paragraph",
            position=0,
            language="es",
            content=content,
            paragraphs=(first, second),
        )


def test_span_rejects_evidence_that_does_not_match_source_offsets():
    span = TextSpan(
        span_id="span.invalid-evidence",
        kind="paragraph",
        block_id="p1",
        start=0,
        end=5,
        evidence="xxxxx",
        ordinal=0,
    )

    with pytest.raises(ValidationError, match="no coincide"):
        AnalyzedBlock(
            block_id="p1",
            block_type="paragraph",
            position=0,
            language="es",
            content="abcde",
            paragraphs=(span,),
        )


def test_sentence_must_be_nested_in_its_declared_paragraph():
    paragraph = TextSpan(
        span_id="span.paragraph",
        kind="paragraph",
        block_id="p1",
        start=0,
        end=5,
        evidence="abcde",
        ordinal=0,
    )
    sentence = TextSpan(
        span_id="span.sentence",
        kind="sentence",
        block_id="p1",
        start=5,
        end=10,
        evidence="fghij",
        ordinal=0,
        parent_span_id=paragraph.span_id,
    )

    with pytest.raises(ValidationError, match="contenida"):
        AnalyzedBlock(
            block_id="p1",
            block_type="paragraph",
            position=0,
            language="es",
            content="abcdefghij",
            paragraphs=(paragraph,),
            sentences=(sentence,),
        )


def test_unresolvable_expression_hierarchy_is_rejected():
    first = _paragraph("first", "Uno.", parent_id="second")
    second = _paragraph("second", "Dos.", parent_id="first")
    work = _work((first, second))

    with pytest.raises(ValueError, match="orden de lectura resoluble"):
        _analyze(work)


def test_span_lookup_rejects_unknown_identifier():
    snapshot = _analyze(_work((_paragraph("p1", "Texto."),)))

    with pytest.raises(KeyError, match="Span desconocido"):
        snapshot.evidence_for("span.unknown")


def test_staleness_tracks_scope_branch_and_material_version():
    work = _work((_paragraph("p1", "Texto."),), version=4, manuscript_version=3)
    snapshot = _analyze(work)

    review_only = _work(
        (_paragraph("p1", "Texto."),),
        version=5,
        manuscript_version=3,
    )
    material_change = _work(
        (_paragraph("p1", "Texto."),),
        version=5,
        manuscript_version=4,
    )

    assert snapshot.is_stale_for(review_only, branch_id="main") is False
    assert snapshot.is_stale_for(review_only, branch_id="draft") is True
    assert snapshot.is_stale_for(material_change, branch_id="main") is True


def test_spanish_regional_language_tag_is_supported():
    snapshot = _analyze(
        _work(
            (_paragraph("p1", "La obra permanece.", language="es-AR"),),
            language="es-AR",
        )
    )

    assert snapshot.language == "es-ar"
    assert snapshot.blocks[0].language == "es-ar"
