"""SQLite event store with the same stream contract as ``MemoryEventStore``."""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from editorial_tres.domain.commits import EditorialCommit
from editorial_tres.domain.events import (
    ContentBlockAdded,
    ContentBlockDeleted,
    ContentBlockEdited,
    ContentBlockMoved,
    DependencyRegistered,
    DerivedResourceInvalidated,
    DomainEvent,
    ReviewFindingDecided,
    ReviewFindingRecorded,
)
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.exceptions import (
    ConcurrencyError,
    DuplicateCommitError,
    DuplicateEventError,
    IdempotencyConflictError,
    InvalidCommitParentError,
)


_EVENT_MODELS = {
    "content_block.added": ContentBlockAdded,
    "content_block.deleted": ContentBlockDeleted,
    "content_block.edited": ContentBlockEdited,
    "content_block.moved": ContentBlockMoved,
    "dependency.registered": DependencyRegistered,
    "derived_resource.invalidated": DerivedResourceInvalidated,
    "review.finding_recorded": ReviewFindingRecorded,
    "review.finding_decided": ReviewFindingDecided,
}


class SQLiteEventStore:
    """Persist editorial streams in a single SQLite database.

    A stream is scoped by tenant, editorial, work, and branch.  ``BEGIN
    IMMEDIATE`` serializes appenders at the database boundary, so stream-head
    validation remains correct when separate store instances use the same file.
    """

    def __init__(self, database_path: str | Path) -> None:
        self._connection = sqlite3.connect(str(database_path))
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SQLiteEventStore":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _create_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS streams (
                tenant_id TEXT NOT NULL,
                editorial_id TEXT NOT NULL,
                work_id TEXT NOT NULL,
                branch TEXT NOT NULL,
                head_commit_id TEXT,
                head_version INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (tenant_id, editorial_id, work_id, branch)
            );

            CREATE TABLE IF NOT EXISTS commits (
                commit_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                editorial_id TEXT NOT NULL,
                work_id TEXT NOT NULL,
                branch TEXT NOT NULL,
                stream_position INTEGER NOT NULL,
                parent_commit_id TEXT,
                parent_branch TEXT,
                parent_branch_version INTEGER,
                message TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (tenant_id, editorial_id, work_id, branch, stream_position),
                FOREIGN KEY (tenant_id, editorial_id, work_id, branch)
                    REFERENCES streams (tenant_id, editorial_id, work_id, branch)
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                commit_id TEXT NOT NULL,
                event_position INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                editorial_id TEXT NOT NULL,
                work_id TEXT NOT NULL,
                aggregate_version INTEGER NOT NULL,
                occurred_at TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                origin_event_id TEXT,
                UNIQUE (commit_id, event_position),
                FOREIGN KEY (commit_id) REFERENCES commits (commit_id)
            );

            CREATE TABLE IF NOT EXISTS idempotency_keys (
                tenant_id TEXT NOT NULL,
                editorial_id TEXT NOT NULL,
                work_id TEXT NOT NULL,
                branch TEXT NOT NULL,
                command_type TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                commit_id TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                PRIMARY KEY (
                    tenant_id, editorial_id, work_id, branch,
                    command_type, idempotency_key
                ),
                FOREIGN KEY (commit_id) REFERENCES commits (commit_id)
            );

            CREATE INDEX IF NOT EXISTS idx_commits_stream
                ON commits (tenant_id, editorial_id, work_id, branch, stream_position);
            CREATE INDEX IF NOT EXISTS idx_events_commit
                ON events (commit_id, event_position);
            """
        )
        self._connection.commit()

    @staticmethod
    def _stream_values(tenant_id: TenantId, editorial_id: EditorialId, work_id: WorkId, branch: str) -> tuple[str, str, str, str]:
        return tenant_id.value, editorial_id.value, work_id.value, branch

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> DomainEvent:
        model = _EVENT_MODELS.get(row["event_type"], DomainEvent)
        return model.model_validate(
            {
                "event_id": row["event_id"],
                "event_type": row["event_type"],
                "tenant_id": TenantId(value=row["tenant_id"]),
                "editorial_id": EditorialId(value=row["editorial_id"]),
                "work_id": WorkId(value=row["work_id"]),
                "aggregate_version": row["aggregate_version"],
                "occurred_at": row["occurred_at"],
                "actor_id": ActorId(value=row["actor_id"]),
                "payload": json.loads(row["payload_json"]),
                "origin_event_id": row["origin_event_id"],
            }
        )

    def _events_for_commit(self, commit_id: str) -> tuple[DomainEvent, ...]:
        rows = self._connection.execute(
            "SELECT * FROM events WHERE commit_id = ? ORDER BY event_position", (commit_id,)
        ).fetchall()
        return tuple(self._event_from_row(row) for row in rows)

    def _commit_from_row(self, row: sqlite3.Row) -> EditorialCommit:
        return EditorialCommit(
            commit_id=row["commit_id"],
            tenant_id=TenantId(value=row["tenant_id"]),
            editorial_id=EditorialId(value=row["editorial_id"]),
            work_id=WorkId(value=row["work_id"]),
            branch=row["branch"],
            parent_commit_id=row["parent_commit_id"],
            parent_branch=row["parent_branch"],
            parent_branch_version=row["parent_branch_version"],
            events=self._events_for_commit(row["commit_id"]),
            message=row["message"],
            actor_id=ActorId(value=row["actor_id"]),
            created_at=row["created_at"],
        )

    def append_commit(
        self,
        commit: EditorialCommit,
        idempotency_key: Optional[str] = None,
        command_type: str = "legacy",
        payload_hash: Optional[str] = None,
    ) -> None:
        stream = self._stream_values(
            commit.tenant_id, commit.editorial_id, commit.work_id, commit.branch
        )
        event_ids = [event.event_id for event in commit.events]

        if any(
            (event.tenant_id, event.editorial_id, event.work_id)
            != (commit.tenant_id, commit.editorial_id, commit.work_id)
            for event in commit.events
        ):
            raise ValueError("Todos los eventos deben pertenecer al stream del commit.")
        if len(set(event_ids)) != len(event_ids):
            raise DuplicateEventError("Un event_id ya existe.")

        try:
            self._connection.execute("BEGIN IMMEDIATE")
            if self._connection.execute(
                "SELECT 1 FROM commits WHERE commit_id = ?", (commit.commit_id,)
            ).fetchone():
                raise DuplicateCommitError(
                    f"El commit con ID '{commit.commit_id}' ya existe."
                )
            if event_ids:
                placeholders = ", ".join("?" for _ in event_ids)
                if self._connection.execute(
                    f"SELECT 1 FROM events WHERE event_id IN ({placeholders}) LIMIT 1",
                    event_ids,
                ).fetchone():
                    raise DuplicateEventError("Un event_id ya existe.")

            head = self._connection.execute(
                "SELECT head_commit_id, head_version FROM streams "
                "WHERE tenant_id = ? AND editorial_id = ? AND work_id = ? AND branch = ?",
                stream,
            ).fetchone()
            if head is None:
                if commit.parent_commit_id is not None:
                    raise InvalidCommitParentError("El primer commit no tiene parent.")
                head_version = 0
                stream_position = 1
                self._connection.execute(
                    "INSERT INTO streams (tenant_id, editorial_id, work_id, branch) VALUES (?, ?, ?, ?)",
                    stream,
                )
            else:
                if commit.parent_commit_id != head["head_commit_id"]:
                    raise InvalidCommitParentError(
                        "El parent_commit_id debe coincidir con el head actual."
                    )
                head_version = head["head_version"]
                stream_position = self._connection.execute(
                    "SELECT COUNT(*) FROM commits WHERE tenant_id = ? AND editorial_id = ? "
                    "AND work_id = ? AND branch = ?",
                    stream,
                ).fetchone()[0] + 1

            expected_versions = list(
                range(head_version + 1, head_version + len(commit.events) + 1)
            )
            actual_versions = [event.aggregate_version for event in commit.events]
            if actual_versions != expected_versions:
                raise ConcurrencyError(
                    f"Versiones no consecutivas: se esperaba {expected_versions}, "
                    f"se recibió {actual_versions}."
                )

            if idempotency_key and self._connection.execute(
                "SELECT 1 FROM idempotency_keys WHERE tenant_id = ? AND editorial_id = ? "
                "AND work_id = ? AND branch = ? AND command_type = ? AND idempotency_key = ?",
                (*stream, command_type, idempotency_key),
            ).fetchone():
                raise IdempotencyConflictError(
                    f"La idempotency_key '{idempotency_key}' ya fue utilizada."
                )

            self._connection.execute(
                "INSERT INTO commits (commit_id, tenant_id, editorial_id, work_id, branch, "
                "stream_position, parent_commit_id, parent_branch, parent_branch_version, "
                "message, actor_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    commit.commit_id,
                    *stream,
                    stream_position,
                    commit.parent_commit_id,
                    commit.parent_branch,
                    commit.parent_branch_version,
                    commit.message,
                    commit.actor_id.value,
                    commit.created_at.isoformat(),
                ),
            )
            for position, event in enumerate(commit.events):
                payload = event.model_dump(mode="json")["payload"]
                self._connection.execute(
                    "INSERT INTO events (event_id, commit_id, event_position, event_type, "
                    "tenant_id, editorial_id, work_id, aggregate_version, occurred_at, actor_id, "
                    "payload_json, origin_event_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        event.event_id,
                        commit.commit_id,
                        position,
                        event.event_type,
                        event.tenant_id.value,
                        event.editorial_id.value,
                        event.work_id.value,
                        event.aggregate_version,
                        event.occurred_at.isoformat(),
                        event.actor_id.value,
                        json.dumps(payload, sort_keys=True, separators=(",", ":")),
                        event.origin_event_id,
                    ),
                )
            self._connection.execute(
                "UPDATE streams SET head_commit_id = ?, head_version = ? "
                "WHERE tenant_id = ? AND editorial_id = ? AND work_id = ? AND branch = ?",
                (commit.commit_id, actual_versions[-1], *stream),
            )
            if idempotency_key:
                self._connection.execute(
                    "INSERT INTO idempotency_keys (tenant_id, editorial_id, work_id, branch, "
                    "command_type, idempotency_key, commit_id, payload_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (*stream, command_type, idempotency_key, commit.commit_id, payload_hash or ""),
                )
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def get_commits(
        self, tenant_id: TenantId, editorial_id: EditorialId, work_id: WorkId, branch: str = "main"
    ) -> list[EditorialCommit]:
        rows = self._connection.execute(
            "SELECT * FROM commits WHERE tenant_id = ? AND editorial_id = ? "
            "AND work_id = ? AND branch = ? ORDER BY stream_position",
            self._stream_values(tenant_id, editorial_id, work_id, branch),
        ).fetchall()
        return [self._commit_from_row(row) for row in rows]

    def get_events(
        self, tenant_id: TenantId, editorial_id: EditorialId, work_id: WorkId, branch: str = "main"
    ) -> list[DomainEvent]:
        rows = self._connection.execute(
            "SELECT events.* FROM events JOIN commits ON commits.commit_id = events.commit_id "
            "WHERE commits.tenant_id = ? AND commits.editorial_id = ? "
            "AND commits.work_id = ? AND commits.branch = ? "
            "ORDER BY commits.stream_position, events.event_position",
            self._stream_values(tenant_id, editorial_id, work_id, branch),
        ).fetchall()
        return [self._event_from_row(row) for row in rows]

    def get_head_commit(
        self, tenant_id: TenantId, editorial_id: EditorialId, work_id: WorkId, branch: str = "main"
    ) -> Optional[EditorialCommit]:
        row = self._connection.execute(
            "SELECT commits.* FROM streams JOIN commits ON commits.commit_id = streams.head_commit_id "
            "WHERE streams.tenant_id = ? AND streams.editorial_id = ? "
            "AND streams.work_id = ? AND streams.branch = ?",
            self._stream_values(tenant_id, editorial_id, work_id, branch),
        ).fetchone()
        return self._commit_from_row(row) if row else None

    def get_idempotent_commit(
        self,
        tenant_id: TenantId,
        editorial_id: EditorialId,
        work_id: WorkId,
        branch: str,
        command_type: str,
        key: str,
        payload_hash: str,
    ) -> Optional[EditorialCommit]:
        row = self._connection.execute(
            "SELECT commit_id, payload_hash FROM idempotency_keys WHERE tenant_id = ? "
            "AND editorial_id = ? AND work_id = ? AND branch = ? "
            "AND command_type = ? AND idempotency_key = ?",
            (*self._stream_values(tenant_id, editorial_id, work_id, branch), command_type, key),
        ).fetchone()
        if row is None:
            return None
        if row["payload_hash"] != payload_hash:
            raise IdempotencyConflictError(
                "La idempotency_key fue reutilizada con un payload distinto."
            )
        commit_row = self._connection.execute(
            "SELECT * FROM commits WHERE commit_id = ?", (row["commit_id"],)
        ).fetchone()
        return self._commit_from_row(commit_row)

    def has_idempotency_key(self, key: str) -> bool:
        return bool(
            self._connection.execute(
                "SELECT 1 FROM idempotency_keys WHERE idempotency_key = ? LIMIT 1", (key,)
            ).fetchone()
        )

    def get_commits_by_idempotency_key(self, key: str) -> Optional[EditorialCommit]:
        row = self._connection.execute(
            "SELECT commits.* FROM idempotency_keys JOIN commits "
            "ON commits.commit_id = idempotency_keys.commit_id "
            "WHERE idempotency_keys.idempotency_key = ? LIMIT 1",
            (key,),
        ).fetchone()
        return self._commit_from_row(row) if row else None

    def branch_exists(
        self, tenant_id: TenantId, editorial_id: EditorialId, work_id: WorkId, branch: str
    ) -> bool:
        return bool(
            self._connection.execute(
                "SELECT 1 FROM streams WHERE tenant_id = ? AND editorial_id = ? "
                "AND work_id = ? AND branch = ?",
                self._stream_values(tenant_id, editorial_id, work_id, branch),
            ).fetchone()
        )
