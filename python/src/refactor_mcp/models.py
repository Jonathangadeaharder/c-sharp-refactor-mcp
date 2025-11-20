"""
Data models for the refactor-mcp server.

Uses Pydantic for validation and schema generation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Enums
# ============================================================================


class Language(str, Enum):
    """Supported programming languages."""

    CSHARP = "csharp"
    VBNET = "vbnet"
    TYPESCRIPT = "typescript"
    PYTHON = "python"
    GO = "go"
    CPP = "cpp"
    JAVA = "java"
    RUST = "rust"


class DiagnosticSeverity(str, Enum):
    """Diagnostic severity levels."""

    ERROR = "Error"
    WARNING = "Warning"
    INFO = "Info"
    HINT = "Hint"


class SymbolKind(str, Enum):
    """Code symbol kinds."""

    CLASS = "class"
    INTERFACE = "interface"
    STRUCT = "struct"
    ENUM = "enum"
    METHOD = "method"
    PROPERTY = "property"
    FIELD = "field"
    VARIABLE = "variable"
    PARAMETER = "parameter"
    NAMESPACE = "namespace"


# ============================================================================
# Request/Response Models
# ============================================================================


class ProjectInfo(BaseModel):
    """Information about a loaded project."""

    project_path: str = Field(description="Absolute path to project file")
    project_name: str = Field(description="Project name")
    language: Language = Field(description="Programming language")
    file_count: int = Field(description="Number of source files")
    sub_projects: list[str] | None = Field(
        default=None, description="Sub-projects (for solutions)"
    )

    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "project_path": "/home/user/projects/MyApp/MyApp.sln",
                "project_name": "MyApp",
                "language": "csharp",
                "file_count": 150,
                "sub_projects": ["MyApp.Core", "MyApp.Web", "MyApp.Tests"],
            }
        ]
    })


class DiagnosticInfo(BaseModel):
    """A single diagnostic (error, warning, etc.)."""

    severity: DiagnosticSeverity = Field(description="Diagnostic severity")
    message: str = Field(description="Diagnostic message")
    file_path: str = Field(description="File path")
    line: int = Field(description="Line number (1-based)")
    column: int = Field(description="Column number (1-based)")
    diagnostic_id: str | None = Field(default=None, description="Diagnostic ID (e.g., CS0103)")


class DiagnosticsInfo(BaseModel):
    """Project diagnostics summary."""

    error_count: int = Field(description="Number of errors")
    warning_count: int = Field(description="Number of warnings")
    info_count: int = Field(default=0, description="Number of info messages")
    is_safe_to_refactor: bool = Field(
        description="True if no compilation errors exist"
    )
    diagnostics: list[DiagnosticInfo] = Field(
        description="List of diagnostics"
    )

    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "error_count": 0,
                "warning_count": 5,
                "info_count": 10,
                "is_safe_to_refactor": True,
                "diagnostics": [
                    {
                        "severity": "Warning",
                        "message": "Variable 'x' is never used",
                        "file_path": "/home/user/MyApp/Program.cs",
                        "line": 10,
                        "column": 13,
                        "diagnostic_id": "CS0168",
                    }
                ],
            }
        ]
    })


class ReferenceLocation(BaseModel):
    """A reference location."""

    file_path: str = Field(description="File path")
    line: int = Field(description="Line number (1-based)")
    column: int = Field(description="Column number (1-based)")
    preview: str = Field(description="Code preview")


class ReferencesInfo(BaseModel):
    """Find references result."""

    symbol_name: str = Field(description="Symbol name")
    reference_count: int = Field(description="Number of references")
    references: list[ReferenceLocation] = Field(description="Reference locations")


class SymbolInfo(BaseModel):
    """Detailed symbol information."""

    name: str = Field(description="Symbol name")
    kind: str = Field(description="Symbol kind (class, method, etc.)")
    type: str = Field(description="Symbol type")
    containing_type: str | None = Field(
        default=None, description="Containing type name"
    )
    containing_namespace: str | None = Field(
        default=None, description="Containing namespace"
    )
    is_static: bool = Field(default=False, description="Is static")
    is_abstract: bool = Field(default=False, description="Is abstract")
    is_virtual: bool = Field(default=False, description="Is virtual")
    accessibility: str = Field(description="Accessibility (public, private, etc.)")
    documentation: str | None = Field(
        default=None, description="XML documentation"
    )


class RenameResult(BaseModel):
    """Rename symbol result."""

    success: bool = Field(description="Whether rename succeeded")
    symbol_name: str = Field(description="Original symbol name")
    new_name: str = Field(description="New symbol name")
    files_modified: int = Field(description="Number of files modified")
    locations_modified: int = Field(description="Number of locations modified")
    error: str | None = Field(default=None, description="Error message if failed")


class ExtractMethodResult(BaseModel):
    """Extract method result."""

    success: bool = Field(description="Whether extraction succeeded")
    method_name: str = Field(description="Extracted method name")
    files_modified: int = Field(description="Number of files modified")
    parameters: list[str] = Field(description="Method parameters")
    return_type: str = Field(description="Method return type")
    error: str | None = Field(default=None, description="Error message if failed")


# ============================================================================
# Application Context (passed to tools via FastMCP context injection)
# ============================================================================


@dataclass
class AppContext:
    """
    Application context passed to all tools.

    FastMCP automatically injects this into tool handlers.
    """

    config: "Config"  # Forward reference
    cache: "CacheManager"  # Forward reference
    security: "PathSecurityService"  # Forward reference
    lsp_pool: "LspClientPool"  # Forward reference
    roslyn_client: "RoslynClient | None"  # Forward reference
    ts_morph_client: "TsMorphClient | None"  # Forward reference
    rope_client: "RopeClient | None"  # Forward reference


# Forward references for type hints (actual imports avoided for circular dependencies)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config
    from .utils.cache import CacheManager
    from .utils.security import PathSecurityService
    from .clients.lsp import LspClientPool
    from .clients.roslyn import RoslynClient
    from .clients.ts_morph import TsMorphClient
    from .clients.rope_client import RopeClient
