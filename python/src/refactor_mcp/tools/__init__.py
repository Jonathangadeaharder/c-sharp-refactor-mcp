"""MCP tools for refactoring, analysis, and diagnostics."""

from .analysis import register_analysis_tools
from .diagnostics import register_diagnostic_tools
from .refactoring import register_refactoring_tools

__all__ = [
    "register_refactoring_tools",
    "register_analysis_tools",
    "register_diagnostic_tools",
]
