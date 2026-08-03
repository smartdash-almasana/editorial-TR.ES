"""Carga y validación del manifiesto de proyecto editorial (project.yaml)."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from editorial_tres.exceptions import InvalidManifestError


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ProjectPluginsSpec(BaseModel):
    editorial: Optional[str] = None
    genre: Optional[str] = None
    voice: Optional[str] = None
    narrator: Optional[str] = None
    research_method: Optional[str] = None
    workflow: Optional[str] = None
    styles: List[str] = Field(default_factory=list)
    reviewers: List[str] = Field(default_factory=list)
    visuals: List[str] = Field(default_factory=list)
    visual_types: List[str] = Field(default_factory=list)
    visual_styles: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)

    def get_all_plugin_ids(self) -> List[str]:
        """Devuelve una lista ordenada determinista con todos los IDs solicitados."""

        ids: List[str] = []
        for plugin_id in (
            self.editorial,
            self.genre,
            self.voice,
            self.narrator,
            self.research_method,
            self.workflow,
        ):
            if plugin_id:
                ids.append(plugin_id)
        for group in (
            self.styles,
            self.reviewers,
            self.visuals,
            self.visual_types,
            self.visual_styles,
            self.outputs,
        ):
            for plugin_id in group:
                if plugin_id not in ids:
                    ids.append(plugin_id)
        return ids


class ProjectManifest(BaseModel):
    """Canonical project manifest used by composition and executable factories."""

    id: str = Field(..., description="Identificador único del proyecto")
    title: str = Field(..., description="Título de la obra")
    language: str = Field(default="es-AR", description="Código de idioma principal")
    plugins: ProjectPluginsSpec = Field(default_factory=ProjectPluginsSpec)

    publisher: Optional[str] = None
    author: Optional[str] = None
    source_file: Optional[str] = None
    source_sha256: Optional[str] = None
    expected_word_count: Optional[int] = Field(default=None, ge=1)
    expected_chapter_count: Optional[int] = Field(default=None, ge=1)
    workflow: Optional[str] = None
    tenant_id: str = "tenant.tres-private"
    editorial_id: str = "editorial.tres"
    manifest_path: Optional[Path] = None

    @model_validator(mode="before")
    @classmethod
    def _accept_project_id(cls, value):
        if isinstance(value, dict) and "id" not in value and "project_id" in value:
            value = {**value, "id": value["project_id"]}
        return value

    @field_validator("id", "title", "language", "tenant_id", "editorial_id")
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La identidad, el título y el idioma del proyecto son obligatorios.")
        return normalized

    @field_validator("source_sha256")
    @classmethod
    def _valid_source_sha256(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not _SHA256.fullmatch(normalized):
            raise ValueError("source_sha256 debe ser un SHA-256 hexadecimal.")
        return normalized

    @field_validator("source_file")
    @classmethod
    def _safe_source_file(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.replace("\\", "/").strip()
        path = PurePosixPath(normalized)
        if not normalized or path.is_absolute() or ".." in path.parts:
            raise ValueError("source_file debe ser una ruta relativa segura.")
        return path.as_posix()

    @property
    def project_id(self) -> str:
        """Stable alias used by private-factory project manifests."""

        return self.id

    @property
    def work_id(self) -> str:
        return f"work.{self.id}"

    @property
    def output_slug(self) -> str:
        return self.id

    def resolve_source_path(self) -> Path:
        if self.manifest_path is None:
            raise InvalidManifestError("El manifiesto no conserva su ubicación de origen.")
        if self.source_file is None:
            raise InvalidManifestError("El proyecto no declara source_file.")
        return self.manifest_path.parent / self.source_file

    @classmethod
    def from_yaml(cls, path: Path) -> "ProjectManifest":
        """Carga y valida un manifiesto desde un archivo o una carpeta."""

        target_file = path / "project.yaml" if path.is_dir() else path
        if not target_file.is_file():
            raise InvalidManifestError(
                f"Archivo de proyecto no encontrado: '{target_file}'"
            )

        try:
            content = yaml.safe_load(target_file.read_text(encoding="utf-8"))
        except Exception as exc:
            raise InvalidManifestError(
                f"Error al parsear el YAML de proyecto en '{target_file}': {exc}"
            ) from exc
        if not isinstance(content, dict):
            raise InvalidManifestError(
                f"El manifiesto de proyecto en '{target_file}' debe ser un diccionario YAML."
            )

        try:
            manifest = cls(**content)
            manifest.manifest_path = target_file.resolve()
            return manifest
        except Exception as exc:
            raise InvalidManifestError(
                f"Manifiesto de proyecto inválido en '{target_file}': {exc}"
            ) from exc
