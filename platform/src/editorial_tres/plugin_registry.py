"""
Registro y descubrimiento automático de plugins en el sistema.
"""

from pathlib import Path
from typing import Dict, List
from editorial_tres.exceptions import (
    DuplicatePluginError,
    PluginNotFoundError,
)
from editorial_tres.plugin_contract import PluginManifest


class PluginRegistry:
    """Mantiene el registro de todos los plugins disponibles descubiertos."""

    def __init__(self) -> None:
        self._plugins: Dict[str, PluginManifest] = {}

    def register(self, manifest: PluginManifest) -> None:
        """Registra un manifiesto de plugin. Falla si ya existe uno con el mismo ID."""
        if manifest.id in self._plugins:
            existing = self._plugins[manifest.id]
            existing_path = existing.manifest_path or "desconocido"
            new_path = manifest.manifest_path or "desconocido"
            raise DuplicatePluginError(
                f"Plugin duplicado detectado con ID '{manifest.id}'. "
                f"Existente en: '{existing_path}', Nuevo en: '{new_path}'"
            )
        self._plugins[manifest.id] = manifest

    def get(self, plugin_id: str) -> PluginManifest:
        """Obtiene un plugin por su ID o lanza PluginNotFoundError."""
        if plugin_id not in self._plugins:
            raise PluginNotFoundError(f"El plugin con ID '{plugin_id}' no fue encontrado en el registro.")
        return self._plugins[plugin_id]

    def contains(self, plugin_id: str) -> bool:
        """Indica si un ID de plugin está registrado."""
        return plugin_id in self._plugins

    def list_plugins(self) -> List[PluginManifest]:
        """Retorna una lista de todos los plugins registrados."""
        return list(self._plugins.values())

    def discover_plugins(self, root_path: Path) -> int:
        """
        Descubre recursivamente todos los archivos `plugin.yaml` bajo `root_path` y los registra.
        Retorna la cantidad de plugins descubiertos.
        """
        if not root_path.exists():
            return 0
        count = 0
        for yaml_file in root_path.rglob("plugin.yaml"):
            manifest = PluginManifest.from_yaml(yaml_file)
            self.register(manifest)
            count += 1
        return count
