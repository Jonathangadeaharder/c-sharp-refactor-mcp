"""
Data models for refactoring operations.

These models are used by the Roslyn, ts-morph, and LSP clients.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DiagnosticInfo(BaseModel):
    """A single diagnostic (error, warning, etc.)."""

    file_path: str = Field(description="File path")
    line: int = Field(description="Line number (1-based)")
    column: int = Field(description="Column number (1-based)")
    end_line: int = Field(description="End line number (1-based)")
    end_column: int = Field(description="End column number (1-based)")
    severity: str = Field(description="Diagnostic severity")
    message: str = Field(description="Diagnostic message")
    code: str = Field(description="Diagnostic code (e.g., CS0103, TS2322)")


class ReferenceInfo(BaseModel):
    """A reference location."""

    file_path: str = Field(description="File path")
    line: int = Field(description="Line number (1-based)")
    column: int = Field(description="Column number (1-based)")
    line_text: str = Field(description="Line text preview")
    is_definition: bool = Field(default=False, description="Whether this is the definition")


class ReferenceLocation(BaseModel):
    """A reference location (legacy format for Roslyn client)."""

    file_path: str = Field(description="File path")
    line: int = Field(description="Line number (1-based)")
    column: int = Field(description="Column number (1-based)")
    preview: str = Field(description="Code preview")


class ReferencesInfo(BaseModel):
    """Find references result."""

    symbol_name: str = Field(description="Symbol name")
    reference_count: int = Field(description="Number of references")
    references: List[ReferenceLocation] = Field(description="Reference locations")


class SymbolInfo(BaseModel):
    """Detailed symbol information."""

    name: str = Field(description="Symbol name")
    kind: str = Field(description="Symbol kind (class, method, etc.)")
    file_path: str = Field(description="File path")
    line: int = Field(description="Line number (1-based)")
    column: int = Field(description="Column number (1-based)")
    type: str = Field(default="unknown", description="Symbol type")
    containing_type: Optional[str] = Field(
        default=None, description="Containing type name"
    )
    containing_namespace: Optional[str] = Field(
        default=None, description="Containing namespace"
    )
    is_static: bool = Field(default=False, description="Is static")
    is_abstract: bool = Field(default=False, description="Is abstract")
    is_virtual: bool = Field(default=False, description="Is virtual")
    accessibility: str = Field(default="public", description="Accessibility (public, private, etc.)")
    documentation: Optional[str] = Field(
        default=None, description="Documentation"
    )
    definition_file: Optional[str] = Field(default=None, description="Definition file path")
    definition_line: Optional[int] = Field(default=None, description="Definition line")
    definition_column: Optional[int] = Field(default=None, description="Definition column")


class RenameResult(BaseModel):
    """Rename symbol result."""

    success: bool = Field(description="Whether rename succeeded")
    symbol_name: Optional[str] = Field(default=None, description="Original symbol name")
    new_name: Optional[str] = Field(default=None, description="New symbol name")
    files_modified: int = Field(default=0, description="Number of files modified")
    locations_modified: int = Field(default=0, description="Number of locations modified")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    changes: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of file changes"
    )
    extracted_method_name: Optional[str] = Field(
        default=None, description="Extracted method name (for extract_method)"
    )


class ExtractMethodResult(BaseModel):
    """Extract method result."""

    success: bool = Field(description="Whether extraction succeeded")
    method_name: str = Field(description="Extracted method name")
    files_modified: int = Field(description="Number of files modified")
    parameters: List[str] = Field(description="Method parameters")
    return_type: str = Field(description="Method return type")
    error: Optional[str] = Field(default=None, description="Error message if failed")
