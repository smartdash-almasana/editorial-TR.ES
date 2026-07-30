"""
Carga y validación del manifiesto de proyecto editorial (project.yaml).
"""

from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field

from editorial_tres.exceptions import InvalidManifestError


class ProjectPluginsSpec(BaseModel):
    genre: Optional[str] = None
    voice: Optional[str] = None
    narrator: Optional[str] = None
    workflow: Optional[str] = None
    styles: List[str] = Field(default_factory=list)
    reviewers: List[str] = Field(default_factory=list)
    visuals: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)

    def get_all_plugin_ids(self) -> List[str]:
        """Devuelve una lista ordenada determinista con todos los IDs de plugins solicitados."""
        ids: List[str] = []
        if self.genre:
            ids.append(self.genre)
        if self.voice:
            ids.append(self.voice)
        if self.narrator:
            ids.append(self.narrator)
        if self.workflow:
            ids.append(self.workflow)
        for s in self.styles:
            if s not in ids:
                ids.append(s)
        for r in self.reviewers:
            if r not in ids:
                ids.append(r)
        for v in self.visuals:
            if v not in ids:
                ids.append(v)
        for o in self.outputs:
            if o not in ids:
                ids.append(o)
        return ids


class ProjectManifest(BaseModel):
    id: str = Field(..., description="Identificador único del proyecto")
    title: str = Field(..., description="Título de la obra")
    language: str = Field(default="es-AR", description="Código de idioma principal")
    plugins: ProjectPluginsSpec = Field(default_factory=ProjectPluginsSpec)
    manifest_path: Optional[Path] = None

    @classmethod
    def from_yaml(cls, path: Path) -> "ProjectManifest":
        """Carga y valida un ProjectManifest desde un archivo YAML o carpeta conteniendo project.yaml."""
        target_file = path
        if path.is_dir():
            target_file = path / "project.yaml"

        if not target_file.is_file():
            raise InvalidManifestError(f"Archivo de proyecto no encontrado: '{target_file}'")

        try:
            content = yaml.safe_load(target_file.read_text(encoding="utf-8"))
        except Exception as e:
            raise InvalidManifestError(f"Error al parsear el YAML de proyecto en '{target_file}': {e}") from e

        if not isinstance(content, dict):
            raise InvalidManifestError(f"El manifiesto de proyecto en '{target_file}' debe ser un diccionario YAML.")

        try:
            manifest = cls(**content)
            manifest.manifest_path = target_file.resolve()
            return manifest
        except Exception as e:
            raise InvalidManifestError(f"Manifiesto de proyecto inválido en '{target_file}': {e}") from e
