"""SQLite-backed infrastructure adapters."""

from editorial_tres.infrastructure.sqlite.event_store import SQLiteEventStore

__all__ = ["SQLiteEventStore"]
