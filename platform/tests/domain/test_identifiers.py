"""
Pruebas para identificadores tipados.
"""

import pytest

from editorial_tres.domain.identifiers import (
    ActorId,
    EditorialId,
    TenantId,
    WorkId,
)
from editorial_tres.exceptions import InvalidIdentifierError


def test_valid_tenant_id():
    tid = TenantId(value="tenant.almasana")
    assert tid.value == "tenant.almasana"
    assert str(tid) == "tenant.almasana"


def test_valid_editorial_id():
    eid = EditorialId(value="editorial.almasana")
    assert eid.value == "editorial.almasana"


def test_valid_work_id():
    wid = WorkId(value="work.yo-no-soy")
    assert wid.value == "work.yo-no-soy"


def test_valid_actor_id():
    aid = ActorId(value="actor.user-001")
    assert aid.value == "actor.user-001"


def test_invalid_tenant_id_wrong_prefix():
    with pytest.raises(InvalidIdentifierError):
        TenantId(value="wrong.almasana")


def test_invalid_editorial_id_wrong_prefix():
    with pytest.raises(InvalidIdentifierError):
        EditorialId(value="tenant.almasana")


def test_invalid_work_id_wrong_prefix():
    with pytest.raises(InvalidIdentifierError):
        WorkId(value="editorial.almasana")


def test_invalid_empty_id():
    with pytest.raises(InvalidIdentifierError):
        TenantId(value="")


def test_invalid_whitespace_id():
    with pytest.raises(InvalidIdentifierError):
        WorkId(value="   ")


def test_invalid_suffix_with_spaces():
    with pytest.raises(InvalidIdentifierError):
        TenantId(value="tenant.alma sana")


def test_immutability():
    tid = TenantId(value="tenant.almasana")
    with pytest.raises(Exception):
        tid.value = "tenant.otro"


def test_hash_equality():
    tid1 = TenantId(value="tenant.almasana")
    tid2 = TenantId(value="tenant.almasana")
    assert hash(tid1) == hash(tid2)
    assert tid1 == tid2
