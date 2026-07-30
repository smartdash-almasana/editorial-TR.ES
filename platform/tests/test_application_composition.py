"""End-to-end tests for the persistent application composition."""

from editorial_tres.application.commands import CreateWorkCommand
from editorial_tres.composition import compose_application
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId


def test_application_rebuilds_work_from_sqlite_after_restart(tmp_path) -> None:
    database_path = tmp_path / "editorial.sqlite"
    tenant_id = TenantId(value="tenant.tres")
    editorial_id = EditorialId(value="editorial.tres")
    work_id = WorkId(value="work.persisted")
    command = CreateWorkCommand(
        command_id="cmd-create-work",
        idempotency_key="create-work",
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        actor_id=ActorId(value="actor.editor"),
        title="Obra persistida",
        language="es",
    )

    with compose_application(database_path) as application:
        application.create_work.handle(command)
        assert application.current_work_projection.get_work(
            tenant_id, editorial_id, work_id
        ).version == 1

    with compose_application(database_path) as restarted_application:
        restarted_application.rebuild_work(tenant_id, editorial_id, work_id)

        rebuilt = restarted_application.current_work_projection.get_work(
            tenant_id, editorial_id, work_id
        )
        assert rebuilt.title == "Obra persistida"
        assert rebuilt.version == 1
