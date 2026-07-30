"""
Resolución de la composición de plugins para un proyecto editorial.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set
from pydantic import BaseModel, Field

from editorial_tres.application.handlers import (
    AddContentBlockHandler,
    ApplyApprovedPatchHandler,
    CreateBranchHandler,
    CreateWorkHandler,
    EditContentBlockHandler,
    RegisterDependencyHandler,
)
from editorial_tres.application.projections import CurrentWorkProjection
from editorial_tres.exceptions import (
    IncompatibilityError,
    MissingDependencyError,
    PluginNotFoundError,
)
from editorial_tres.infrastructure.sqlite.event_store import SQLiteEventStore
from editorial_tres.plugin_contract import PluginManifest
from editorial_tres.plugin_registry import PluginRegistry
from editorial_tres.project_manifest import ProjectManifest

CATEGORY_PRIORITY = [
    "genre",
    "voice",
    "narrator",
    "workflow",
    "style",
    "reviewer",
    "visual",
    "output",
]


def _get_category_rank(plugin_type: str) -> int:
    try:
        return CATEGORY_PRIORITY.index(plugin_type)
    except ValueError:
        return 999


class ProjectComposition(BaseModel):
    project: ProjectManifest
    resolved_plugins: List[PluginManifest] = Field(default_factory=list)
    plugins_by_type: Dict[str, List[PluginManifest]] = Field(default_factory=dict)
    composition_order: List[str] = Field(default_factory=list)


def compose_project(project_path: Path, plugins_root: Path) -> ProjectComposition:
    """
    Resuelve la composición completa de plugins para un proyecto.

    1. Carga el manifiesto de proyecto.
    2. Descubre los plugins disponibles en plugins_root.
    3. Resuelve los IDs de plugins solicitados.
    4. Comprueba que las dependencias de cada plugin estén presentes.
    5. Comprueba la compatibilidad entre plugins.
    6. Devuelve la composición ordenada y estructurada.
    """
    # 1. Cargar proyecto
    project = ProjectManifest.from_yaml(project_path)

    # 2. Descubrir plugins
    registry = PluginRegistry()
    registry.discover_plugins(plugins_root)

    # 3. Resolver identificadores
    requested_ids = project.plugins.get_all_plugin_ids()
    resolved_map: Dict[str, PluginManifest] = {}

    for pid in requested_ids:
        plugin = registry.get(pid)
        resolved_map[pid] = plugin

    # 4. Comprobar dependencias (requires)
    resolved_set = set(resolved_map.keys())
    for pid, plugin in resolved_map.items():
        for req in plugin.requires:
            if req not in resolved_set:
                raise MissingDependencyError(
                    f"El plugin '{pid}' requiere el plugin '{req}', pero este no está incluido en el proyecto."
                )

    # 5. Comprobar incompatibilidades (compatible_with)
    for pid, plugin in resolved_map.items():
        if plugin.compatible_with:
            allowed_targets = set(plugin.compatible_with)
            for other_id, other_plugin in resolved_map.items():
                if pid == other_id:
                    continue
                # Se permite si el ID del otro o su tipo están explicítamente en compatible_with
                if other_id not in allowed_targets and other_plugin.type not in allowed_targets:
                    raise IncompatibilityError(
                        f"El plugin '{pid}' declara compatibilidad restringida a {plugin.compatible_with}, "
                        f"lo cual es incompatible con el plugin incluido '{other_id}'."
                    )

    # 6. Ordenación estable y determinista de la composición
    # Ordenamiento base por tipo de categoría y luego por ID
    ordered_plugins = sorted(
        resolved_map.values(),
        key=lambda p: (_get_category_rank(p.type), p.id),
    )

    # Reordenar aplicando dependencias (Kahn's topological sort para mantener dependencias primero)
    deps_graph: Dict[str, Set[str]] = {p.id: set(p.requires) for p in ordered_plugins}
    composition_order: List[str] = []
    visited: Set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        for dep in sorted(deps_graph.get(node_id, set())):
            if dep in deps_graph:
                visit(dep)
        visited.add(node_id)
        composition_order.append(node_id)

    for p in ordered_plugins:
        visit(p.id)

    # Agrupar plugins por tipo
    plugins_by_type: Dict[str, List[PluginManifest]] = {}
    for p in ordered_plugins:
        plugins_by_type.setdefault(p.type, []).append(p)

    final_resolved_list = [resolved_map[pid] for pid in composition_order]

    return ProjectComposition(
        project=project,
        resolved_plugins=final_resolved_list,
        plugins_by_type=plugins_by_type,
        composition_order=composition_order,
    )


@dataclass
class EditorialApplication:
    """Runtime dependencies assembled around the persistent Event Store."""

    event_store: SQLiteEventStore
    current_work_projection: CurrentWorkProjection
    create_work: CreateWorkHandler
    add_content_block: AddContentBlockHandler
    apply_approved_patch: ApplyApprovedPatchHandler
    edit_content_block: EditContentBlockHandler
    register_dependency: RegisterDependencyHandler
    create_branch: CreateBranchHandler

    def rebuild_work(self, tenant_id, editorial_id, work_id, branch: str = "main") -> None:
        """Rebuild one current-work read model from its persisted event stream."""
        events = self.event_store.get_events(tenant_id, editorial_id, work_id, branch)
        self.current_work_projection.rebuild_work(events, branch=branch)

    def close(self) -> None:
        self.event_store.close()

    def __enter__(self) -> "EditorialApplication":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def compose_application(database_path: str | Path) -> EditorialApplication:
    """Assemble the application runtime with a SQLite-backed Event Store.

    Tests can continue wiring handlers with ``MemoryEventStore`` directly.  The
    production composition path always creates the persistent adapter.
    """
    event_store = SQLiteEventStore(database_path)
    projection = CurrentWorkProjection()
    return EditorialApplication(
        event_store=event_store,
        current_work_projection=projection,
        create_work=CreateWorkHandler(event_store, projection),
        add_content_block=AddContentBlockHandler(event_store, projection),
        apply_approved_patch=ApplyApprovedPatchHandler(event_store, projection),
        edit_content_block=EditContentBlockHandler(event_store, projection),
        register_dependency=RegisterDependencyHandler(event_store, projection),
        create_branch=CreateBranchHandler(event_store, projection),
    )
