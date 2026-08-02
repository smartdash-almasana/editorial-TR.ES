"""Traceable, immutable textual analysis for Spanish editorial manuscripts."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator, model_validator

from editorial_tres.domain.graphs.expression import ContentBlock
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.immutable_values import canonical_json

if TYPE_CHECKING:
    from editorial_tres.domain.work import Work


TEXT_ANALYSIS_SCHEMA_VERSION = "editorial.tres/text-analysis-snapshot-v1"
SPAN_KINDS = ("paragraph", "sentence", "token")
SpanKind = Literal["paragraph", "sentence", "token"]

_SPANISH_ABBREVIATIONS = frozenset(
    {
        "aprox",
        "atte",
        "cap",
        "cf",
        "cía",
        "d",
        "dña",
        "dr",
        "dra",
        "ej",
        "etc",
        "fig",
        "lic",
        "núm",
        "p",
        "pág",
        "págs",
        "prof",
        "s",
        "sra",
        "sras",
        "sr",
        "sres",
        "sta",
        "ud",
        "uds",
        "vol",
    }
)
_LEXICAL_TOKEN = re.compile(
    r"[^\W\d_]+(?:[-’'][^\W\d_]+)*|\d+(?:[.,]\d+)*",
    flags=re.UNICODE,
)
_PARAGRAPH_LINE = re.compile(r"[^\r\n]+")
_WORD_BEFORE = re.compile(r"([^\W\d_]+)$", flags=re.UNICODE)
_CLOSING_MARKS = frozenset("”’\"'»)]}")
_OPENING_MARKS = frozenset("“‘\"'«([{¿¡")


def _is_supported_spanish(language: str) -> bool:
    normalized = language.strip().lower().replace("_", "-")
    return normalized == "es" or normalized.startswith("es-")


def _required_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} es obligatorio.")
    return normalized


def _span_id(
    *,
    tenant_id: str,
    editorial_id: str,
    work_id: str,
    branch_id: str,
    manuscript_version: int,
    block_id: str,
    kind: SpanKind,
    start: int,
    end: int,
) -> str:
    payload = {
        "tenant_id": tenant_id,
        "editorial_id": editorial_id,
        "work_id": work_id,
        "branch_id": branch_id,
        "manuscript_version": manuscript_version,
        "block_id": block_id,
        "kind": kind,
        "start": start,
        "end": end,
    }
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"span.{digest[:32]}"


def _snapshot_id(
    *,
    tenant_id: str,
    editorial_id: str,
    work_id: str,
    branch_id: str,
    manuscript_version: int,
    language: str,
    blocks: Iterable["AnalyzedBlock"],
) -> str:
    block_fingerprints = [
        {
            "id": block.block_id,
            "block_type": block.block_type,
            "parent_block_id": block.parent_block_id,
            "position": block.position,
            "language": block.language,
            "content_sha256": hashlib.sha256(
                block.content.encode("utf-8")
            ).hexdigest(),
        }
        for block in blocks
    ]
    payload = {
        "schema_version": TEXT_ANALYSIS_SCHEMA_VERSION,
        "tenant_id": tenant_id,
        "editorial_id": editorial_id,
        "work_id": work_id,
        "branch_id": branch_id,
        "manuscript_version": manuscript_version,
        "language": language,
        "blocks": block_fingerprints,
    }
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"analysis.{digest}"


class TextSpan(BaseModel):
    """Exact half-open source interval inside one ContentBlock."""

    span_id: str
    kind: SpanKind
    block_id: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    evidence: str
    ordinal: int = Field(ge=0)
    parent_span_id: str | None = None

    model_config = {"frozen": True}

    @field_validator("span_id", "block_id")
    @classmethod
    def _required_identity(cls, value: str) -> str:
        return _required_text(value, field_name="La identidad del span")

    @model_validator(mode="after")
    def _valid_interval(self) -> "TextSpan":
        if self.start >= self.end:
            raise ValueError("Un span debe tener un intervalo no vacío.")
        if not self.evidence:
            raise ValueError("Un span debe conservar evidencia textual exacta.")
        if self.kind == "paragraph" and self.parent_span_id is not None:
            raise ValueError("Un párrafo no puede declarar un span padre.")
        if self.kind != "paragraph" and self.parent_span_id is None:
            raise ValueError("Oraciones y tokens deben declarar su span padre.")
        return self


class AnalyzedBlock(BaseModel):
    """Source block plus its immutable, nested textual coordinates."""

    block_id: str
    block_type: str
    parent_block_id: str | None = None
    position: int = Field(ge=0)
    language: str
    content: str
    paragraphs: tuple[TextSpan, ...] = ()
    sentences: tuple[TextSpan, ...] = ()
    tokens: tuple[TextSpan, ...] = ()

    model_config = {"frozen": True}

    @field_validator("block_id", "block_type")
    @classmethod
    def _required_identity(cls, value: str) -> str:
        return _required_text(value, field_name="La identidad del bloque analizado")

    @field_validator("language")
    @classmethod
    def _spanish_language(cls, value: str) -> str:
        normalized = value.strip().lower().replace("_", "-")
        if not _is_supported_spanish(normalized):
            raise ValueError(
                f"Idioma textual no soportado: '{value}'. PT-0 admite español."
            )
        return normalized

    @model_validator(mode="after")
    def _consistent_spans(self) -> "AnalyzedBlock":
        groups = (
            ("paragraph", self.paragraphs),
            ("sentence", self.sentences),
            ("token", self.tokens),
        )
        seen_ids: set[str] = set()
        for kind, spans in groups:
            previous_end = -1
            for ordinal, span in enumerate(spans):
                if span.kind != kind:
                    raise ValueError(
                        f"El grupo '{kind}' contiene un span de tipo '{span.kind}'."
                    )
                if span.block_id != self.block_id:
                    raise ValueError("Un span no pertenece al bloque que lo contiene.")
                if span.ordinal != ordinal:
                    raise ValueError(
                        f"Los spans '{kind}' deben tener ordinales consecutivos."
                    )
                if span.end > len(self.content):
                    raise ValueError("Un span excede los límites del bloque fuente.")
                if span.start < previous_end:
                    raise ValueError(
                        f"Los spans '{kind}' no pueden superponerse."
                    )
                if self.content[span.start : span.end] != span.evidence:
                    raise ValueError(
                        "La evidencia del span no coincide con el texto fuente."
                    )
                if span.span_id in seen_ids:
                    raise ValueError("Los IDs de span deben ser únicos.")
                seen_ids.add(span.span_id)
                previous_end = span.end

        paragraphs = {span.span_id: span for span in self.paragraphs}
        sentences = {span.span_id: span for span in self.sentences}
        for sentence in self.sentences:
            parent = paragraphs.get(sentence.parent_span_id or "")
            if parent is None or not (
                parent.start <= sentence.start < sentence.end <= parent.end
            ):
                raise ValueError(
                    "Cada oración debe estar contenida en su párrafo declarado."
                )
        for token in self.tokens:
            parent = sentences.get(token.parent_span_id or "")
            if parent is None or not (
                parent.start <= token.start < token.end <= parent.end
            ):
                raise ValueError(
                    "Cada token debe estar contenido en su oración declarada."
                )
        return self

    def span(self, span_id: str) -> TextSpan:
        for candidate in (*self.paragraphs, *self.sentences, *self.tokens):
            if candidate.span_id == span_id:
                return candidate
        raise KeyError(f"Span desconocido: {span_id}")


class TextAnalysisSnapshot(BaseModel):
    """Deterministic analysis bound to one exact manuscript scope."""

    schema_version: str = TEXT_ANALYSIS_SCHEMA_VERSION
    snapshot_id: str
    tenant_id: TenantId
    editorial_id: EditorialId
    work_id: WorkId
    branch_id: str
    source_work_version: int = Field(ge=1)
    source_manuscript_version: int = Field(ge=1)
    language: str
    blocks: tuple[AnalyzedBlock, ...]
    reading_order: tuple[str, ...]

    model_config = {"frozen": True}

    @field_validator("snapshot_id", "branch_id")
    @classmethod
    def _required_identity(cls, value: str) -> str:
        return _required_text(value, field_name="La identidad del análisis")

    @field_validator("language")
    @classmethod
    def _spanish_language(cls, value: str) -> str:
        normalized = value.strip().lower().replace("_", "-")
        if not _is_supported_spanish(normalized):
            raise ValueError(
                f"Idioma textual no soportado: '{value}'. PT-0 admite español."
            )
        return normalized

    @model_validator(mode="after")
    def _consistent_snapshot(self) -> "TextAnalysisSnapshot":
        if self.schema_version != TEXT_ANALYSIS_SCHEMA_VERSION:
            raise ValueError(
                f"Versión de análisis textual no soportada: {self.schema_version}."
            )
        block_ids = tuple(block.block_id for block in self.blocks)
        if len(set(block_ids)) != len(block_ids):
            raise ValueError("El análisis no puede contener bloques duplicados.")
        if self.reading_order != block_ids:
            raise ValueError(
                "El orden de lectura debe coincidir con los bloques analizados."
            )

        all_span_ids: set[str] = set()
        for block in self.blocks:
            for span in (*block.paragraphs, *block.sentences, *block.tokens):
                expected = _span_id(
                    tenant_id=self.tenant_id.value,
                    editorial_id=self.editorial_id.value,
                    work_id=self.work_id.value,
                    branch_id=self.branch_id,
                    manuscript_version=self.source_manuscript_version,
                    block_id=block.block_id,
                    kind=span.kind,
                    start=span.start,
                    end=span.end,
                )
                if span.span_id != expected:
                    raise ValueError(
                        f"El ID del span '{span.span_id}' no corresponde a su fuente."
                    )
                if span.span_id in all_span_ids:
                    raise ValueError("Un snapshot no puede repetir IDs de span.")
                all_span_ids.add(span.span_id)

        expected_snapshot_id = _snapshot_id(
            tenant_id=self.tenant_id.value,
            editorial_id=self.editorial_id.value,
            work_id=self.work_id.value,
            branch_id=self.branch_id,
            manuscript_version=self.source_manuscript_version,
            language=self.language,
            blocks=self.blocks,
        )
        if self.snapshot_id != expected_snapshot_id:
            raise ValueError("El ID del snapshot no corresponde a su fuente.")
        return self

    def span(self, span_id: str) -> TextSpan:
        for block in self.blocks:
            try:
                return block.span(span_id)
            except KeyError:
                continue
        raise KeyError(f"Span desconocido: {span_id}")

    def evidence_for(self, span_id: str) -> str:
        """Recover the exact source substring represented by one span."""

        return self.span(span_id).evidence

    def is_stale_for(self, work: "Work", *, branch_id: str) -> bool:
        """Detect material or scope divergence from the analyzed manuscript."""

        return (
            self.tenant_id != work.tenant_id
            or self.editorial_id != work.editorial_id
            or self.work_id != work.work_id
            or self.branch_id != branch_id
            or self.source_manuscript_version != work.manuscript_version
        )


class SpanishTextAnalyzer:
    """Dependency-free deterministic segmentation for Spanish manuscripts."""

    def analyze(
        self,
        work: "Work",
        *,
        branch_id: str,
    ) -> TextAnalysisSnapshot:
        normalized_branch = _required_text(
            branch_id, field_name="La rama editorial"
        )
        if not _is_supported_spanish(work.language):
            raise ValueError(
                f"Idioma textual no soportado: '{work.language}'. PT-0 admite español."
            )

        ordered = self._reading_order(work.expression_graph.blocks)
        analyzed = tuple(
            self._analyze_block(
                block,
                tenant_id=work.tenant_id.value,
                editorial_id=work.editorial_id.value,
                work_id=work.work_id.value,
                branch_id=normalized_branch,
                manuscript_version=work.manuscript_version,
            )
            for block in ordered
        )
        language = work.language.strip().lower().replace("_", "-")
        snapshot_id = _snapshot_id(
            tenant_id=work.tenant_id.value,
            editorial_id=work.editorial_id.value,
            work_id=work.work_id.value,
            branch_id=normalized_branch,
            manuscript_version=work.manuscript_version,
            language=language,
            blocks=analyzed,
        )
        return TextAnalysisSnapshot(
            snapshot_id=snapshot_id,
            tenant_id=work.tenant_id,
            editorial_id=work.editorial_id,
            work_id=work.work_id,
            branch_id=normalized_branch,
            source_work_version=work.version,
            source_manuscript_version=work.manuscript_version,
            language=language,
            blocks=analyzed,
            reading_order=tuple(block.block_id for block in analyzed),
        )

    @staticmethod
    def _reading_order(
        blocks: Mapping[str, ContentBlock],
    ) -> tuple[ContentBlock, ...]:
        children: dict[str | None, list[ContentBlock]] = {}
        for block in blocks.values():
            if block.parent_id is not None and block.parent_id not in blocks:
                raise ValueError(
                    f"El bloque '{block.id}' depende del padre inexistente "
                    f"'{block.parent_id}'."
                )
            children.setdefault(block.parent_id, []).append(block)
        for siblings in children.values():
            siblings.sort(key=lambda item: (item.position, item.id))

        ordered: list[ContentBlock] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(block: ContentBlock) -> None:
            if block.id in visiting:
                raise ValueError("El grafo de expresión contiene un ciclo parental.")
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
        if len(visited) != len(blocks):
            unresolved = ", ".join(sorted(set(blocks) - visited))
            raise ValueError(
                "El grafo de expresión no tiene un orden de lectura resoluble: "
                f"{unresolved}"
            )
        return tuple(ordered)

    def _analyze_block(
        self,
        block: ContentBlock,
        *,
        tenant_id: str,
        editorial_id: str,
        work_id: str,
        branch_id: str,
        manuscript_version: int,
    ) -> AnalyzedBlock:
        if not _is_supported_spanish(block.language):
            raise ValueError(
                f"El bloque '{block.id}' usa un idioma no soportado: "
                f"'{block.language}'."
            )

        paragraphs: list[TextSpan] = []
        sentences: list[TextSpan] = []
        tokens: list[TextSpan] = []

        for paragraph_start, paragraph_end in self._paragraph_ranges(block.content):
            paragraph = self._make_span(
                tenant_id=tenant_id,
                editorial_id=editorial_id,
                work_id=work_id,
                branch_id=branch_id,
                manuscript_version=manuscript_version,
                block=block,
                kind="paragraph",
                start=paragraph_start,
                end=paragraph_end,
                ordinal=len(paragraphs),
            )
            paragraphs.append(paragraph)

            for sentence_start, sentence_end in self._sentence_ranges(
                block.content, paragraph_start, paragraph_end
            ):
                sentence = self._make_span(
                    tenant_id=tenant_id,
                    editorial_id=editorial_id,
                    work_id=work_id,
                    branch_id=branch_id,
                    manuscript_version=manuscript_version,
                    block=block,
                    kind="sentence",
                    start=sentence_start,
                    end=sentence_end,
                    ordinal=len(sentences),
                    parent_span_id=paragraph.span_id,
                )
                sentences.append(sentence)
                for match in _LEXICAL_TOKEN.finditer(
                    block.content, sentence_start, sentence_end
                ):
                    tokens.append(
                        self._make_span(
                            tenant_id=tenant_id,
                            editorial_id=editorial_id,
                            work_id=work_id,
                            branch_id=branch_id,
                            manuscript_version=manuscript_version,
                            block=block,
                            kind="token",
                            start=match.start(),
                            end=match.end(),
                            ordinal=len(tokens),
                            parent_span_id=sentence.span_id,
                        )
                    )

        return AnalyzedBlock(
            block_id=block.id,
            block_type=block.block_type,
            parent_block_id=block.parent_id,
            position=block.position,
            language=block.language,
            content=block.content,
            paragraphs=tuple(paragraphs),
            sentences=tuple(sentences),
            tokens=tuple(tokens),
        )

    @staticmethod
    def _paragraph_ranges(content: str) -> tuple[tuple[int, int], ...]:
        ranges: list[tuple[int, int]] = []
        for match in _PARAGRAPH_LINE.finditer(content):
            start, end = match.span()
            while start < end and content[start].isspace():
                start += 1
            while end > start and content[end - 1].isspace():
                end -= 1
            if start < end:
                ranges.append((start, end))
        return tuple(ranges)

    @classmethod
    def _sentence_ranges(
        cls,
        content: str,
        paragraph_start: int,
        paragraph_end: int,
    ) -> tuple[tuple[int, int], ...]:
        ranges: list[tuple[int, int]] = []
        sentence_start = paragraph_start
        index = paragraph_start

        while index < paragraph_end:
            char = content[index]
            if char not in ".!?":
                index += 1
                continue
            if char == "." and cls._nonterminal_dot(
                content, index, paragraph_start, paragraph_end
            ):
                index += 1
                continue

            terminal_end = index + 1
            while (
                terminal_end < paragraph_end
                and content[terminal_end] in ".!?"
            ):
                terminal_end += 1
            close_end = terminal_end
            while (
                close_end < paragraph_end
                and content[close_end] in _CLOSING_MARKS
            ):
                close_end += 1

            if not cls._continues_after_terminal(
                content,
                terminal_start=index,
                terminal_end=terminal_end,
                close_end=close_end,
                paragraph_end=paragraph_end,
            ):
                start, end = cls._trim_interval(
                    content, sentence_start, close_end
                )
                if start < end:
                    ranges.append((start, end))
                sentence_start = close_end
                while (
                    sentence_start < paragraph_end
                    and content[sentence_start].isspace()
                ):
                    sentence_start += 1
                index = sentence_start
                continue
            index = terminal_end

        start, end = cls._trim_interval(
            content, sentence_start, paragraph_end
        )
        if start < end:
            ranges.append((start, end))
        return tuple(ranges)

    @staticmethod
    def _trim_interval(
        content: str, start: int, end: int
    ) -> tuple[int, int]:
        while start < end and content[start].isspace():
            start += 1
        while end > start and content[end - 1].isspace():
            end -= 1
        return start, end

    @staticmethod
    def _nonterminal_dot(
        content: str,
        index: int,
        paragraph_start: int,
        paragraph_end: int,
    ) -> bool:
        if (
            index > paragraph_start
            and index + 1 < paragraph_end
            and content[index - 1].isdigit()
            and content[index + 1].isdigit()
        ):
            return True

        before = content[paragraph_start:index]
        match = _WORD_BEFORE.search(before)
        if match is None:
            return False
        word = match.group(1)
        lowered = word.casefold()
        if lowered in _SPANISH_ABBREVIATIONS:
            return True
        if len(word) == 1 and word.isupper():
            return True
        return False

    @staticmethod
    def _continues_after_terminal(
        content: str,
        *,
        terminal_start: int,
        terminal_end: int,
        close_end: int,
        paragraph_end: int,
    ) -> bool:
        cursor = close_end
        while cursor < paragraph_end and content[cursor].isspace():
            cursor += 1
        if cursor >= paragraph_end:
            return False

        if content[cursor] in "—-":
            cursor += 1
            while cursor < paragraph_end and content[cursor].isspace():
                cursor += 1
            while cursor < paragraph_end and content[cursor] in _OPENING_MARKS:
                cursor += 1
            return cursor < paragraph_end and content[cursor].islower()

        terminal = content[terminal_start:terminal_end]
        if terminal.count(".") >= 2:
            probe = cursor
            while probe < paragraph_end and content[probe] in _OPENING_MARKS:
                probe += 1
            return probe < paragraph_end and content[probe].islower()
        return False

    @staticmethod
    def _make_span(
        *,
        tenant_id: str,
        editorial_id: str,
        work_id: str,
        branch_id: str,
        manuscript_version: int,
        block: ContentBlock,
        kind: SpanKind,
        start: int,
        end: int,
        ordinal: int,
        parent_span_id: str | None = None,
    ) -> TextSpan:
        return TextSpan(
            span_id=_span_id(
                tenant_id=tenant_id,
                editorial_id=editorial_id,
                work_id=work_id,
                branch_id=branch_id,
                manuscript_version=manuscript_version,
                block_id=block.id,
                kind=kind,
                start=start,
                end=end,
            ),
            kind=kind,
            block_id=block.id,
            start=start,
            end=end,
            evidence=block.content[start:end],
            ordinal=ordinal,
            parent_span_id=parent_span_id,
        )
