from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph
from editorial_tres.domain.graphs.narrative import NarrativeGraph
from editorial_tres.domain.graphs.dependency import DependencyGraph
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.reviews import (
    ContinuityReviewer,
    ContinuityRule,
    RepeatedPhraseReviewer,
    ReviewEngine,
    StructuralReviewer,
    VoiceDriftReviewer,
)
from editorial_tres.domain.work import Work
from editorial_tres.semantic_memory import MemoryRetriever, RetrievalRequest, WorkMemoryProjection


TEXT = '''A veces uno vuelve a un lugar sin saber bien por qué. Una especie de tirón invisible parecía llamarme desde la casa.

De repente, sentí una necesidad imperiosa de caminar hasta la orilla y comprender el peso del pasado.

Luego, tomé el reloj y lo dejé sobre la cómoda, junto al marco de plata. No me lo llevaría. Pertenecía a esa casa, a esa historia.

Arranqué y tomé el camino de tierra hacia la ruta. En el retrovisor, la casa se fue haciendo cada vez más pequeña, hasta desaparecer entre los árboles. Pero su imagen quedó grabada en mi mente, junto con el sonido del río, el olor a papel viejo y el peso del reloj en mi bolsillo. Un peso que, aunque ya no lo llevara conmigo, seguiría ahí, recordándome que algunas preguntas no tienen respuesta, y que algunas respuestas no valen la pena.

El tiempo pasó. Los años se acumularon. La casa del río siguió ahí, testigo mudo de una historia que nunca terminó de contarse. Y yo seguí viviendo, con la certeza de que, en algún lugar, entre el polvo y los recuerdos, quedaba la verdad. Una verdad que, tal vez, era mejor dejar donde estaba.
El tiempo pasó. Los años se acumularon. La casa del río siguió ahí, testigo mudo de una historia que nunca terminó de contarse. Y yo seguí viviendo, con la certeza de que, en algún lugar, entre el polvo y los recuerdos, quedaba la verdad. Una verdad que, tal vez, era mejor dejar donde estaba.
El tiempo pasó. Los años se acumularon. La casa del río siguió ahí, testigo mudo de una historia que nunca terminó de contarse. Y yo seguí viviendo, con la certeza de que, en algún lugar, entre el polvo y los recuerdos, quedaba la verdad. Una verdad que, tal vez, era mejor dejar donde estaba.
El tiempo pasó. Los años se acumularon. La casa del río siguió ahí, testigo mudo de una historia que nunca terminó de contarse. Y yo seguí viviendo, con la certeza de que, en algún lugar, entre el polvo y los recuerdos, quedaba la verdad. Una verdad que, tal vez, era mejor dejar donde estaba.'''


def _work():
    tenant_id = TenantId(value='tenant.demo')
    editorial_id = EditorialId(value='editorial.tres')
    work_id = WorkId(value='work.casa_rio')
    expression = ExpressionGraph(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id).add_block(
        ContentBlock(id='manuscript', block_type='paragraph', content=TEXT, position=1)
    )
    return Work(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title='La casa del río',
        language='es',
        knowledge_graph=KnowledgeGraph(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id),
        narrative_graph=NarrativeGraph(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id),
        expression_graph=expression,
        dependency_graph=DependencyGraph(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id),
    )


def test_pilot_reports_current_runtime_capability(capsys):
    work = _work()
    memory = WorkMemoryProjection.from_work(work)
    retriever = MemoryRetriever()
    reloj_refs = retriever.retrieve(work, memory, RetrievalRequest(query='reloj', max_results=10))

    repetition = RepeatedPhraseReviewer(
        reviewer_id='reviewer.pilot.repetition',
        phrase='El tiempo pasó.',
        minimum_occurrences=2,
        severity='warning',
    )
    voice = VoiceDriftReviewer(
        reviewer_id='reviewer.pilot.voice',
        drift_markers=('tirón invisible', 'necesidad imperiosa'),
        minimum_markers=2,
    )
    continuity = ContinuityReviewer(
        reviewer_id='reviewer.pilot.continuity',
        rules=(
            ContinuityRule(
                rule_id='clock-location',
                entity='reloj de bolsillo',
                established_markers=('dejé sobre la cómoda', 'no me lo llevaría'),
                conflicting_markers=('peso del reloj en mi bolsillo',),
            ),
        ),
    )
    structural = StructuralReviewer(
        reviewer_id='reviewer.pilot.structure',
        thematic_phrases=('El tiempo pasó.',),
        minimum_thematic_occurrences=3,
    )
    findings = ReviewEngine((repetition, voice, continuity, structural)).review(work)
    by_type = {finding.finding_type: finding for finding in findings}

    print('RETRIEVAL_RELOJ_REFS=', [(r.kind, r.target_id) for r in reloj_refs])
    print('FINDINGS=', [(f.finding_type, f.target_id, f.evidence, f.description) for f in findings])

    assert reloj_refs
    assert 'expression.repeated_phrase' in by_type
    assert 'expression.voice_drift' in by_type
    assert 'narrative.continuity_conflict' in by_type
    assert 'structure.duplicate_paragraph' in by_type
    assert 'structure.thematic_reiteration' in by_type
    assert 'dejé sobre la cómoda' in by_type['narrative.continuity_conflict'].evidence
    assert 'peso del reloj en mi bolsillo' in by_type['narrative.continuity_conflict'].evidence
