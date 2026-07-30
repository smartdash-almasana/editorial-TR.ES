"""
Graphs package — grafos especializados del dominio.
"""

from editorial_tres.domain.graphs.dependency import DependencyGraph, ResourceDependency
from editorial_tres.domain.graphs.base import BaseGraph, GraphNode
from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph, KnowledgeNode
from editorial_tres.domain.graphs.narrative import NarrativeGraph, NarrativeNode

__all__ = [
    "BaseGraph",
    "ContentBlock",
    "DependencyGraph",
    "ExpressionGraph",
    "GraphNode",
    "KnowledgeGraph",
    "KnowledgeNode",
    "NarrativeGraph",
    "ResourceDependency",
    "NarrativeNode",
]

