"""
Work Projection en memoria para el núcleo neoliterario.
"""

from editorial_tres.application.projections import CurrentWorkProjection

# La implementación en memoria usa directamente CurrentWorkProjection
# ya que esta ya es una implementación en memoria.
MemoryWorkProjection = CurrentWorkProjection
