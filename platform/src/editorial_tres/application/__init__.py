"""
Application package — capa de aplicación del núcleo neoliterario.
"""

from editorial_tres.application.commands import CreateWorkCommand, CreateBranchCommand
from editorial_tres.application.handlers import CreateWorkHandler, CreateWorkResult, CreateBranchHandler, CommandResult
from editorial_tres.application.projections import CurrentWorkProjection

CreateBranchResult = CommandResult

__all__ = [
    "CreateWorkCommand",
    "CreateWorkHandler",
    "CreateWorkResult",
    "CreateBranchCommand",
    "CreateBranchHandler",
    "CreateBranchResult",
    "CurrentWorkProjection",
]
