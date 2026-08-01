"""
Contrato y validación del manifiesto de plugins (plugin.yaml).
"""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field, field_validator

from editorial_tres.exceptions import (
    InvalidManifestError,
    InvalidPluginTypeError,
    UnsafePathError,
)

ALLOWED_PLUGIN_TYPES = {
    "editorial",
    "genre",
    "voice",
    "narrator",
    "style",
    "reviewer",
    "research_method",
    "visual",
    "visual_type",
    "visual_style",
    "workflow",
    "output",
}

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$")


def is_safe_relative_path(path_str: str) -> bool:
    """Verifica que la ruta sea relativa y no realice navegación insegura (sin .., sin raices / ni absolutas)."""
    if not path_str or not path_str.strip():
        return False
    path_str = path_str.strip()
    if path_str.startswith("/") or path_str.startswith("\\"):
        return False
    p = Path(path_str)
    if p.is_absolute() or p.drive != "" or p.anchor != "":
        return False
    parts = p.parts
    if ".." in parts:
        return False
    return True


class PluginManifest(BaseModel):
    id: str = Field(..., description="Identificador único del plugin (ej. genre.essay)")
    version: str = Field(..., description="Versión semántica (ej. 0.1.0)")
    type: str = Field(..., description="Tipo de plugin permitido")
    name: str = Field(..., description="Nombre del plugin")
    description: str = Field(..., description="Descripción breve")
    entrypoint: str = Field(..., description="Ruta relativa al archivo de entrada")
    language: List[str] = Field(default_factory=lambda: ["es"])
    compatible_with: List[str] = Field(default_factory=list)
    requires: List[str] = Field(default_factory=list)
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    rules: List[str] = Field(default_factory=list)
    schemas: List[str] = Field(default_factory=list)
    prompts: List[str] = Field(default_factory=list)
    reviewers: List[str] = Field(default_factory=list)
    passes: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    deterministic: Optional[bool] = None
    risks: List[str] = Field(default_factory=list)
    behavior: Dict[str, Any] = Field(default_factory=dict)
    manifest_path: Optional[Path] = None

    def __init__(self, **data):
        try:
            super().__init__(**data)
        except (InvalidPluginTypeError, UnsafePathError):
            raise
        except Exception as e:
            raise InvalidManifestError(f"Validación de manifiesto fallida: {e}") from e

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El ID del plugin no puede estar vacío.")
        val = v.strip()
        if not re.match(r"^[a-zA-Z0-9_-]+\.[a-zA-Z0-9_.-]+$", val):
            raise ValueError(f"El ID del plugin '{val}' debe tener el formato 'tipo.nombre'.")
        return val

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if not SEMVER_PATTERN.match(v):
            raise ValueError(f"La versión '{v}' no cumple con el formato semántico SemVer (ej. 0.1.0).")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ALLOWED_PLUGIN_TYPES:
            raise InvalidPluginTypeError(
                f"El tipo de plugin '{v}' no es válido. Tipos permitidos: {sorted(ALLOWED_PLUGIN_TYPES)}"
            )
        return v

    @field_validator("entrypoint")
    @classmethod
    def validate_entrypoint(cls, v: str) -> str:
        if not is_safe_relative_path(v):
            raise UnsafePathError(f"La ruta de entrypoint '{v}' es insegura o breaching de directorio.")
        return v

    @classmethod
    def from_yaml(cls, path: Path) -> "PluginManifest":
        """Carga y valida un PluginManifest desde un archivo YAML."""
        if not path.is_file():
            raise InvalidManifestError(f"Archivo de manifiesto de plugin no encontrado: '{path}'")
        try:
            content = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as e:
            raise InvalidManifestError(f"Error al parsear el YAML del plugin en '{path}': {e}") from e

        if not isinstance(content, dict):
            raise InvalidManifestError(f"El manifiesto en '{path}' debe ser un diccionario YAML.")

        manifest = cls(**content)
        manifest.manifest_path = path.resolve()
        return manifest
