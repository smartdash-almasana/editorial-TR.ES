"""
Pruebas para EditorialProfile.
"""

import pytest

from editorial_tres.domain.editorial_profile import EditorialProfile
from editorial_tres.domain.identifiers import EditorialId, TenantId


def test_valid_editorial_profile():
    tenant_id = TenantId(value="tenant.almasana")
    editorial_id = EditorialId(value="editorial.almasana")
    profile = EditorialProfile(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        name="Almasana Editorial",
        description="Editorial de obras literarias",
        default_language="es",
    )
    assert profile.name == "Almasana Editorial"
    assert profile.default_language == "es"
    assert profile.tenant_id == tenant_id
    assert profile.editorial_id == editorial_id


def test_editorial_profile_without_description():
    profile = EditorialProfile(
        tenant_id=TenantId(value="tenant.almasana"),
        editorial_id=EditorialId(value="editorial.almasana"),
        name="Editorial Test",
        default_language="es",
    )
    assert profile.description == ""


def test_editorial_profile_mandatory_name():
    with pytest.raises(Exception):
        EditorialProfile(
            tenant_id=TenantId(value="tenant.almasana"),
            editorial_id=EditorialId(value="editorial.almasana"),
            name="",
            default_language="es",
        )


def test_editorial_profile_mandatory_language():
    with pytest.raises(Exception):
        EditorialProfile(
            tenant_id=TenantId(value="tenant.almasana"),
            editorial_id=EditorialId(value="editorial.almasana"),
            name="Editorial Test",
            default_language="",
        )


def test_editorial_profile_immutability():
    profile = EditorialProfile(
        tenant_id=TenantId(value="tenant.almasana"),
        editorial_id=EditorialId(value="editorial.almasana"),
        name="Editorial Test",
        default_language="es",
    )
    with pytest.raises(Exception):
        profile.name = "Otro nombre"


def test_editorial_profile_serialization():
    profile = EditorialProfile(
        tenant_id=TenantId(value="tenant.almasana"),
        editorial_id=EditorialId(value="editorial.almasana"),
        name="Editorial Test",
        description="Descripción",
        default_language="es",
    )
    data = profile.model_dump()
    restored = EditorialProfile.model_validate(data)
    assert restored.name == profile.name
    assert restored.tenant_id == profile.tenant_id
    assert restored.editorial_id == profile.editorial_id
