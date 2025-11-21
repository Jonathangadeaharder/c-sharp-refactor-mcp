"""
Data models for refactor-mcp.

Exports commonly used models for easy import.
"""

# Export from refactoring models
from .refactoring import (
    DiagnosticInfo,
    ReferenceInfo,
    ReferenceLocation,
    ReferencesInfo,
    SymbolInfo,
    RenameResult,
    ExtractMethodResult,
)

__all__ = [
    "DiagnosticInfo",
    "ReferenceInfo",
    "ReferenceLocation",
    "ReferencesInfo",
    "SymbolInfo",
    "RenameResult",
    "ExtractMethodResult",
]
