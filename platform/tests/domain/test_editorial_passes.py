"""Tests for the first creative boundary: Work -> EditorialPass -> Patch."""

import pytest
from pydantic import ValidationError

from editorial_tres.domain.editorial_passes import (
    DeterministicBlockEditPass,
    FindingDrivenBlockEditPass,
)
from editorial_tres.domain.finding_decisions import FindingDecision
from editorial_tres.domain.graphs.expression import ContentBlock
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.patches import PatchOperation
from editorial_tres.domain.reviews import ReviewFinding
from editorial_tres.domain.work import Work


def _work_with_block() -> Work:
    work = Work.create(
        tenant_id=TenantId(value="tenant.tres"),
        editorial_id=EditorialId(value="editorial.tres"),
        work_id=WorkId(value="work.first-pass"),
        title="Primera pasada",
        language="es",
        actor_id=ActorId(value="actor.editor"),
        event_id="evt-create",
    )
    expression_graph = work.expression_graph.add_block(
        ContentBlock(
            id="block-1",
            block_type="paragraph",
            content="Texto original.",
            position=0,
        )
    )
    return work.model_copy(update={"expression_graph": expression_graph})


def test_editorial_pass_proposes_patch_without_mutating_work() -> None:
    work = _work_with_block()
    before = work.model_dump(mode="json")

    editorial_pass = DeterministicBlockEditPass(
        pass_id="pass.copyedit",
        block_id="block-1",
        replacement_content="Texto propuesto.",
    )
    patch = editorial_pass.propose(work)

    assert work.model_dump(mode="json") == before
    assert work.expression_graph.get_block("block-1").content == "Texto original."
    assert patch.operations[0].after_content == "Texto propuesto."


def test_patch_is_traced_to_exact_work_scope_and_version() -> None:
    work = _work_with_block()
    patch = DeterministicBlockEditPass(
        pass_id="pass.copyedit",
        block_id="block-1",
        replacement_content="Texto propuesto.",
    ).propose(work, branch="experimental")

    assert patch.pass_id == "pass.copyedit"
    assert patch.tenant_id == work.tenant_id
    assert patch.editorial_id == work.editorial_id
    assert patch.work_id == work.work_id
    assert patch.branch == "experimental"
    assert patch.source_version == work.version
    assert patch.operations == (
        PatchOperation(
            block_id="block-1",
            before_content="Texto original.",
            after_content="Texto propuesto.",
        ),
    )


def test_same_pass_over_same_snapshot_produces_same_patch_identity() -> None:
    work = _work_with_block()
    editorial_pass = DeterministicBlockEditPass(
        pass_id="pass.copyedit",
        block_id="block-1",
        replacement_content="Texto propuesto.",
    )

    first = editorial_pass.propose(work)
    second = editorial_pass.propose(work)

    assert first == second
    assert first.patch_id == second.patch_id


def test_pass_rejects_missing_block_and_noop_change() -> None:
    work = _work_with_block()

    with pytest.raises(ValueError, match="no existe"):
        DeterministicBlockEditPass(
            pass_id="pass.copyedit",
            block_id="missing",
            replacement_content="Texto propuesto.",
        ).propose(work)

    with pytest.raises(ValueError, match="cambio real"):
        DeterministicBlockEditPass(
            pass_id="pass.copyedit",
            block_id="block-1",
            replacement_content="Texto original.",
        ).propose(work)


def test_patch_operation_and_pass_are_immutable() -> None:
    operation = PatchOperation(
        block_id="block-1",
        before_content="Antes",
        after_content="Después",
    )
    editorial_pass = DeterministicBlockEditPass(
        pass_id="pass.copyedit",
        block_id="block-1",
        replacement_content="Después",
    )

    with pytest.raises(ValidationError):
        operation.after_content = "Mutado"
    with pytest.raises(ValidationError):
        editorial_pass.replacement_content = "Mutado"


def test_multiblock_finding_cannot_feed_single_block_edit_pass() -> None:
    work = _work_with_block()
    work = work.model_copy(
        update={
            "expression_graph": work.expression_graph.add_block(
                ContentBlock(
                    id="block-2",
                    block_type="paragraph",
                    content="Otra aparición relacionada.",
                    position=1,
                )
            )
        }
    )
    finding = ReviewFinding(
        finding_id="finding-multiblock",
        reviewer_id="reviewer.llm",
        finding_type="structure.llm_cross_block_repetition",
        tenant_id=work.tenant_id,
        editorial_id=work.editorial_id,
        work_id=work.work_id,
        branch="main",
        source_version=work.manuscript_version,
        target_id="block-1",
        related_target_ids=("block-1", "block-2"),
        severity="warning",
        evidence="evidencia multibloque",
        description="Dos apariciones relacionadas.",
    )
    decision = FindingDecision.for_finding(
        finding,
        decision_id="decision-multiblock",
    ).accept(actor_id=ActorId(value="actor.editor"))

    with pytest.raises(ValueError, match="multibloque"):
        FindingDrivenBlockEditPass(
            pass_id="pass.invalid-multiblock",
            finding=finding,
            decision=decision,
            replacement_content="Cambio parcial indebido.",
        ).propose(work)
