from editorial_tres.domain.graphs.dependency import DependencyGraph
from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph
from editorial_tres.domain.graphs.narrative import NarrativeGraph
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.reviews import (
    ContinuityReviewer,
    ContinuityRule,
    ReviewEngine,
    StructuralReviewer,
    VoiceDriftReviewer,
)
from editorial_tres.domain.work import Work


TEXT = '''El campo alrededor de Chascomús tenía esa luz rasante de las tardes de otoño que Marina recordaba con una precisión casi dolorosa. La casa seguía en pie.

Pensó, no por primera vez, que las casas terminan por guardar aquello que las familias no logran decirse; se acumula en los rincones, en los cajones, en el fondo de los roperos, como si las palabras no dichas necesitaran igual un lugar físico donde depositarse.

La penumbra del pasillo se le pegaba a la piel como una tela fina. Corrió apenas la cortina y la penumbra retrocedió sin desaparecer del todo, replegada contra las paredes. Sobre la cómoda encontró una foto familiar que la penumbra del cuarto volvía casi ilegible. Tuvo que acercarla a la ventana para distinguir las caras, todavía envueltas en esa penumbra tibia.

Y en ese instante, ante el rostro detenido de Edgardo, el tiempo se irguió majestuoso como una ola inconmensurable que arrasaba con la fragilidad de los años, y la memoria familiar entera pareció desplegarse ante ella cual un tapiz inmenso, tejido de silencios ancestrales y verdades sepultadas bajo el peso inexorable del destino.

Volvió a pensar que las casas se quedan con lo que las familias no consiguen poner en palabras, que ese silencio se acomoda en los objetos y espera, paciente, a que alguien se anime a removerlo.

Ella había tenido una copia de la llave del cobertizo, pero la había perdido un verano entre los pastos altos y nunca volvió a aparecer. Con los años, el cobertizo quedó cerrado con un candado nuevo, más grande, que nadie en la familia pudo abrir después.

Cuando terminó de revisar la casa, ya había oscurecido por completo. Salió con la linterna del celular y cruzó el patio hacia el cobertizo.

La luz de la tarde entraba oblicua entre las tablas sueltas de la pared y le daba al aire quieto del interior un brillo dorado.

Sacó del bolsillo la llave del cobertizo y la hizo girar en el candado, que cedió con un chirrido seco.

Sintió que el pasado entero se precipitaba sobre ella como una marea inclemente, arrastrando consigo los años, las ausencias y los silencios acumulados de toda una estirpe, en una revelación tan vasta y tan honda que ninguna palabra alcanzaba para nombrarla del todo.

Era, en definitiva, un objeto profundamente significativo, cargado de una emotividad genuina y absolutamente indescriptible, que encapsulaba a la perfección la esencia misma de aquello que la familia nunca había sabido nombrar.

Cuando salió a la calle, pensó otra vez que las casas guardan lo que las familias no llegan a decirse, y que alguien, tarde o temprano, tiene que cargar con eso.'''


def _work() -> Work:
    tenant_id = TenantId(value="tenant.demo")
    editorial_id = EditorialId(value="editorial.tres")
    work_id = WorkId(value="work.aguja_quieta")
    expression = ExpressionGraph(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
    ).add_block(ContentBlock(id="manuscript", block_type="paragraph", content=TEXT, position=1))
    return Work(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title="La aguja quieta",
        language="es",
        knowledge_graph=KnowledgeGraph(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id),
        narrative_graph=NarrativeGraph(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id),
        expression_graph=expression,
        dependency_graph=DependencyGraph(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id),
    )


def test_second_pilot_reports_current_findings(capsys):
    work = _work()
    engine = ReviewEngine((
        VoiceDriftReviewer(
            reviewer_id="reviewer.voice",
            drift_markers=(
                "se irguió majestuoso",
                "ola inconmensurable",
                "silencios ancestrales",
                "peso inexorable del destino",
                "marea inclemente",
                "toda una estirpe",
                "profundamente significativo",
                "emotividad genuina",
                "absolutamente indescriptible",
                "encapsulaba a la perfección",
            ),
            minimum_markers=2,
        ),
        ContinuityReviewer(
            reviewer_id="reviewer.continuity",
            rules=(
                ContinuityRule(
                    rule_id="cobertizo-key",
                    entity="llave del cobertizo",
                    established_markers=("la había perdido", "nunca volvió a aparecer"),
                    conflicting_markers=("sacó del bolsillo la llave del cobertizo",),
                ),
                ContinuityRule(
                    rule_id="time-of-day",
                    entity="momento del día",
                    established_markers=("ya había oscurecido por completo",),
                    conflicting_markers=("la luz de la tarde entraba oblicua",),
                ),
            ),
        ),
        StructuralReviewer(
            reviewer_id="reviewer.structural",
            thematic_phrases=(
                "las casas guardan",
                "las familias no",
            ),
            minimum_thematic_occurrences=2,
        ),
    ))

    findings = engine.review(work)
    print("FINDINGS=", [
        (finding.finding_type, finding.evidence, finding.description)
        for finding in findings
    ])

    types = [finding.finding_type for finding in findings]
    assert "expression.voice_drift" in types
    assert types.count("narrative.continuity_conflict") == 2
    assert "structure.thematic_reiteration" in types
