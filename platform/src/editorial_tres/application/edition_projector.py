"""Projection of approved Work content into a neutral master edition."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from editorial_tres.domain.edition import EditionBlock, EditionSnapshot
from editorial_tres.domain.graphs.expression import ContentBlock
from editorial_tres.domain.work import Work


class EditionProjector:
    """Select and order public content without copying the production history."""

    def project(
        self,
        work: Work,
        *,
        edition_id: str | None = None,
        edition_version: int = 1,
        public_metadata: Mapping[str, Any] | None = None,
    ) -> EditionSnapshot:
        if work.status not in {"approved", "published"}:
            raise ValueError(
                "Sólo una Work aprobada o publicada puede proyectarse como edición."
            )

        approved = {
            block.id: block
            for block in work.expression_graph.blocks.values()
            if block.status == "approved"
        }
        if not approved:
            raise ValueError("La Work no contiene bloques aprobados publicables.")

        for block in approved.values():
            if not block.content.strip():
                raise ValueError(
                    f"El bloque aprobado '{block.id}' no tiene contenido publicable."
                )
            if block.parent_id is not None and block.parent_id not in approved:
                raise ValueError(
                    f"El bloque aprobado '{block.id}' depende del padre no aprobado "
                    f"'{block.parent_id}'."
                )

        ordered = self._reading_order(approved)
        final_edition_id = edition_id or (
            f"{work.work_id.value}.edition-{edition_version}"
        )
        blocks = tuple(
            EditionBlock(
                id=block.id,
                block_type=block.block_type,
                content=block.content,
                parent_id=block.parent_id,
                position=block.position,
                language=block.language,
                metadata=block.metadata,
            )
            for block in ordered
        )

        return EditionSnapshot(
            edition_id=final_edition_id,
            edition_version=edition_version,
            tenant_id=work.tenant_id.value,
            editorial_id=work.editorial_id.value,
            work_id=work.work_id.value,
            source_work_version=work.version,
            source_manuscript_version=work.manuscript_version,
            title=work.title,
            language=work.language,
            blocks=blocks,
            reading_order=tuple(block.id for block in blocks),
            public_metadata=public_metadata or {},
        )

    @staticmethod
    def _reading_order(
        approved: Mapping[str, ContentBlock],
    ) -> tuple[ContentBlock, ...]:
        children: dict[str | None, list[ContentBlock]] = {}
        for block in approved.values():
            children.setdefault(block.parent_id, []).append(block)
        for siblings in children.values():
            siblings.sort(key=lambda item: (item.position, item.id))

        ordered: list[ContentBlock] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(block: ContentBlock) -> None:
            if block.id in visiting:
                raise ValueError("La estructura aprobada contiene un ciclo parental.")
            if block.id in visited:
                return
            visiting.add(block.id)
            ordered.append(block)
            for child in children.get(block.id, ()):
                visit(child)
            visiting.remove(block.id)
            visited.add(block.id)

        for root in children.get(None, ()):
            visit(root)

        if len(visited) != len(approved):
            missing = sorted(set(approved) - visited)
            raise ValueError(
                "La estructura aprobada no tiene un orden de lectura resoluble: "
                + ", ".join(missing)
            )
        return tuple(ordered)
