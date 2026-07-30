"""
Excepciones específicas del dominio para Editorial TR.ES.
"""


class EditorialTresError(Exception):
    """Excepción base para todos los errores de Editorial TR.ES."""

    pass


class InvalidManifestError(EditorialTresError):
    """Lanzada cuando un manifiesto (de plugin o proyecto) no supera la validación."""

    pass


class PluginNotFoundError(EditorialTresError):
    """Lanzada cuando un plugin solicitado no se encuentra en el registro."""

    pass


class DuplicatePluginError(EditorialTresError):
    """Lanzada cuando se descubre un plugin con un ID ya registrado."""

    pass


class MissingDependencyError(EditorialTresError):
    """Lanzada cuando un plugin requiere otro plugin que no está presente en la composición."""

    pass


class InvalidPluginTypeError(EditorialTresError):
    """Lanzada cuando un plugin especifica un tipo no permitido."""

    pass


class IncompatibilityError(EditorialTresError):
    """Lanzada cuando dos plugins en una composición son incompatibles entre sí."""

    pass


class UnsafePathError(EditorialTresError):
    """Lanzada cuando una ruta viola los límites de seguridad (p. ej. path traversal o ruta absoluta)."""

    pass


# --- Excepciones del núcleo neoliterario ---


class InvalidIdentifierError(EditorialTresError):
    """Lanzada cuando un identificador tipado no cumple con el formato requerido."""

    pass


class EditorialNotFoundError(EditorialTresError):
    """Lanzada cuando una editorial solicitada no se encuentra."""

    pass


class WorkAlreadyExistsError(EditorialTresError):
    """Lanzada cuando se intenta crear una obra que ya existe."""

    pass


class WorkNotFoundError(EditorialTresError):
    """Lanzada cuando una obra solicitada no se encuentra."""

    pass


class DuplicateNodeError(EditorialTresError):
    """Lanzada cuando se intenta agregar un nodo con un ID ya existente en un grafo."""

    pass


class MissingParentNodeError(EditorialTresError):
    """Lanzada cuando un nodo referencia un padre que no existe en el grafo."""

    pass


class GraphCycleError(EditorialTresError):
    """Lanzada cuando se detecta un ciclo en la jerarquía de un grafo."""

    pass


class ConcurrencyError(EditorialTresError):
    """Lanzada cuando se detecta un conflicto de concurrencia (versión incorrecta)."""

    pass


class DuplicateEventError(EditorialTresError):
    """Lanzada cuando se intenta almacenar un evento con un event_id ya existente."""

    pass


class DuplicateCommitError(EditorialTresError):
    """Lanzada cuando se intenta almacenar un commit con un commit_id ya existente."""

    pass


class InvalidCommitParentError(EditorialTresError):
    """Lanzada cuando el parent_commit_id no coincide con el head actual."""

    pass


class IdempotencyConflictError(EditorialTresError):
    """Lanzada cuando se reutiliza una idempotency_key con datos distintos."""

    pass
