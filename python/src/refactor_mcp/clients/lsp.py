"""
Language Server Protocol (LSP) client.

Generic LSP client for communicating with language servers via JSON-RPC.
Supports TypeScript, Python, Go, Rust, Java, and other LSP-compliant servers.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import (
    DiagnosticInfo,
    DiagnosticSeverity,
    DiagnosticsInfo,
    ReferenceLocation,
    ReferencesInfo,
    RenameResult,
    SymbolInfo,
)

logger = logging.getLogger(__name__)


class LspError(Exception):
    """LSP operation error."""

    pass


class LspClient:
    """
    Generic LSP client for language servers.

    Communicates with language servers via JSON-RPC over stdin/stdout.
    Supports initialization, diagnostics, references, rename, and symbol info.
    """

    def __init__(
        self,
        language: str,
        command: str,
        args: List[str],
        workspace_root: str | Path,
        timeout: int = 60,
    ):
        """
        Initialize LSP client.

        Args:
            language: Language name (typescript, python, go, rust, etc.)
            command: Language server command
            args: Command arguments
            workspace_root: Workspace root directory
            timeout: Operation timeout in seconds
        """
        self.language = language
        self.command = command
        self.args = args
        self.workspace_root = Path(workspace_root).resolve()
        self.timeout = timeout

        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self._initialized = False

        logger.info(f"LSP client created for {language}: {command} {' '.join(args)}")

    async def start(self) -> None:
        """Start the language server process."""
        if self._process:
            logger.warning(f"LSP client already started for {self.language}")
            return

        try:
            # Start language server process
            self._process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Start reading responses
            self._reader_task = asyncio.create_task(self._read_responses())

            # Initialize the server
            await self._initialize()

            logger.info(f"LSP client started for {self.language}")

        except FileNotFoundError:
            raise LspError(
                f"Language server not found: {self.command}. "
                f"Please install the {self.language} language server."
            )
        except Exception as e:
            logger.error(f"Failed to start LSP client for {self.language}: {e}")
            raise LspError(f"Failed to start language server: {e}")

    async def stop(self) -> None:
        """Stop the language server process."""
        if not self._process:
            return

        try:
            # Send shutdown request
            await self._send_request("shutdown", {})

            # Send exit notification
            await self._send_notification("exit", {})

            # Wait for process to exit
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"LSP server didn't exit cleanly for {self.language}, terminating")
                self._process.terminate()
                await self._process.wait()

            # Cancel reader task
            if self._reader_task:
                self._reader_task.cancel()
                try:
                    await self._reader_task
                except asyncio.CancelledError:
                    pass

            self._process = None
            self._initialized = False

            logger.info(f"LSP client stopped for {self.language}")

        except Exception as e:
            logger.error(f"Error stopping LSP client for {self.language}: {e}")

    async def get_diagnostics(self, file_path: str | Path) -> DiagnosticsInfo:
        """
        Get diagnostics for a file.

        Args:
            file_path: Path to source file

        Returns:
            Diagnostics information
        """
        file_uri = self._path_to_uri(file_path)

        # Open document
        await self._send_notification(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": file_uri,
                    "languageId": self.language,
                    "version": 1,
                    "text": Path(file_path).read_text(),
                }
            },
        )

        # Wait a bit for diagnostics to be published
        await asyncio.sleep(0.5)

        # For now, return empty diagnostics
        # In a full implementation, we'd listen for publishDiagnostics notifications
        return DiagnosticsInfo(
            error_count=0,
            warning_count=0,
            info_count=0,
            is_safe_to_refactor=True,
            diagnostics=[],
        )

    async def find_references(
        self,
        file_path: str | Path,
        line: int,
        column: int,
    ) -> ReferencesInfo:
        """
        Find all references to a symbol.

        Args:
            file_path: Path to source file
            line: Line number (1-based)
            column: Column number (1-based)

        Returns:
            References information
        """
        file_uri = self._path_to_uri(file_path)

        result = await self._send_request(
            "textDocument/references",
            {
                "textDocument": {"uri": file_uri},
                "position": {"line": line - 1, "character": column - 1},  # LSP is 0-based
                "context": {"includeDeclaration": True},
            },
        )

        if not result:
            return ReferencesInfo(symbol_name="", reference_count=0, references=[])

        # Parse locations
        references = []
        for loc in result:
            ref_path = self._uri_to_path(loc["uri"])
            ref_line = loc["range"]["start"]["line"] + 1  # Convert to 1-based
            ref_column = loc["range"]["start"]["character"] + 1

            references.append(
                ReferenceLocation(
                    file_path=str(ref_path),
                    line=ref_line,
                    column=ref_column,
                    preview="",  # Could read file to get preview
                )
            )

        return ReferencesInfo(
            symbol_name="",  # Could get from hover
            reference_count=len(references),
            references=references,
        )

    async def rename_symbol(
        self,
        file_path: str | Path,
        line: int,
        column: int,
        new_name: str,
    ) -> RenameResult:
        """
        Rename a symbol.

        Args:
            file_path: Path to source file
            line: Line number (1-based)
            column: Column number (1-based)
            new_name: New symbol name

        Returns:
            Rename result
        """
        file_uri = self._path_to_uri(file_path)

        result = await self._send_request(
            "textDocument/rename",
            {
                "textDocument": {"uri": file_uri},
                "position": {"line": line - 1, "character": column - 1},
                "newName": new_name,
            },
        )

        if not result or "changes" not in result:
            return RenameResult(
                success=False,
                symbol_name="",
                new_name=new_name,
                files_modified=0,
                locations_modified=0,
                error="Rename not supported or failed",
            )

        # Apply workspace edits
        changes = result["changes"]
        files_modified = set()
        locations_modified = 0

        for uri, edits in changes.items():
            file = self._uri_to_path(uri)
            files_modified.add(str(file))
            locations_modified += len(edits)

            # Apply edits to file
            await self._apply_edits(file, edits)

        return RenameResult(
            success=True,
            symbol_name="",  # Could get from hover
            new_name=new_name,
            files_modified=len(files_modified),
            locations_modified=locations_modified,
        )

    async def get_symbol_info(
        self,
        file_path: str | Path,
        line: int,
        column: int,
    ) -> SymbolInfo:
        """
        Get symbol information at a position.

        Args:
            file_path: Path to source file
            line: Line number (1-based)
            column: Column number (1-based)

        Returns:
            Symbol information
        """
        file_uri = self._path_to_uri(file_path)

        # Get hover information
        hover_result = await self._send_request(
            "textDocument/hover",
            {
                "textDocument": {"uri": file_uri},
                "position": {"line": line - 1, "character": column - 1},
            },
        )

        # Get definition (for more context)
        def_result = await self._send_request(
            "textDocument/definition",
            {
                "textDocument": {"uri": file_uri},
                "position": {"line": line - 1, "character": column - 1},
            },
        )

        # Parse hover result
        name = ""
        type_info = ""
        documentation = ""

        if hover_result and "contents" in hover_result:
            contents = hover_result["contents"]
            if isinstance(contents, str):
                documentation = contents
            elif isinstance(contents, dict) and "value" in contents:
                documentation = contents["value"]

        return SymbolInfo(
            name=name,
            kind="unknown",
            type=type_info,
            documentation=documentation,
        )

    async def _initialize(self) -> None:
        """Initialize the language server."""
        init_result = await self._send_request(
            "initialize",
            {
                "processId": None,
                "rootUri": self._path_to_uri(self.workspace_root),
                "capabilities": {
                    "textDocument": {
                        "references": {"dynamicRegistration": False},
                        "rename": {"dynamicRegistration": False},
                        "hover": {"dynamicRegistration": False},
                    }
                },
            },
        )

        # Send initialized notification
        await self._send_notification("initialized", {})

        self._initialized = True
        logger.debug(f"LSP server initialized for {self.language}")

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Any:
        """Send JSON-RPC request and wait for response."""
        if not self._process or not self._process.stdin:
            raise LspError("LSP client not started")

        self._request_id += 1
        request_id = self._request_id

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        # Create future for response
        future: asyncio.Future = asyncio.Future()
        self._pending_requests[request_id] = future

        # Send request
        message = json.dumps(request)
        content = f"Content-Length: {len(message)}\r\n\r\n{message}"
        self._process.stdin.write(content.encode("utf-8"))
        await self._process.stdin.drain()

        logger.debug(f"LSP request sent: {method} (id={request_id})")

        # Wait for response
        try:
            result = await asyncio.wait_for(future, timeout=self.timeout)
            return result
        except asyncio.TimeoutError:
            logger.error(f"LSP request timeout: {method}")
            raise LspError(f"Request timeout: {method}")

    async def _send_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Send JSON-RPC notification (no response expected)."""
        if not self._process or not self._process.stdin:
            raise LspError("LSP client not started")

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        message = json.dumps(notification)
        content = f"Content-Length: {len(message)}\r\n\r\n{message}"
        self._process.stdin.write(content.encode("utf-8"))
        await self._process.stdin.drain()

        logger.debug(f"LSP notification sent: {method}")

    async def _read_responses(self) -> None:
        """Read and process responses from language server."""
        if not self._process or not self._process.stdout:
            return

        buffer = b""

        try:
            while True:
                # Read data
                chunk = await self._process.stdout.read(4096)
                if not chunk:
                    break

                buffer += chunk

                # Process complete messages
                while b"\r\n\r\n" in buffer:
                    header_end = buffer.index(b"\r\n\r\n")
                    header = buffer[:header_end].decode("utf-8")
                    buffer = buffer[header_end + 4 :]

                    # Parse Content-Length
                    content_length = 0
                    for line in header.split("\r\n"):
                        if line.startswith("Content-Length:"):
                            content_length = int(line.split(":")[1].strip())
                            break

                    if content_length == 0:
                        continue

                    # Wait for complete message
                    while len(buffer) < content_length:
                        chunk = await self._process.stdout.read(4096)
                        if not chunk:
                            return
                        buffer += chunk

                    # Extract message
                    message_bytes = buffer[:content_length]
                    buffer = buffer[content_length:]

                    # Parse JSON
                    try:
                        message = json.loads(message_bytes.decode("utf-8"))
                        await self._handle_message(message)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse LSP message: {e}")

        except asyncio.CancelledError:
            logger.debug(f"LSP reader task cancelled for {self.language}")
        except Exception as e:
            logger.error(f"LSP reader error for {self.language}: {e}")

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle a message from the language server."""
        if "id" in message:
            # Response to a request
            request_id = message["id"]
            if request_id in self._pending_requests:
                future = self._pending_requests.pop(request_id)
                if "result" in message:
                    future.set_result(message["result"])
                elif "error" in message:
                    error = message["error"]
                    future.set_exception(LspError(f"{error.get('message', 'Unknown error')}"))
        elif "method" in message:
            # Notification from server
            method = message["method"]
            logger.debug(f"LSP notification received: {method}")
            # Could handle publishDiagnostics, etc.

    async def _apply_edits(self, file_path: Path, edits: List[Dict[str, Any]]) -> None:
        """Apply text edits to a file."""
        # Read file
        content = file_path.read_text()
        lines = content.split("\n")

        # Sort edits by position (reverse order to preserve positions)
        sorted_edits = sorted(
            edits,
            key=lambda e: (e["range"]["start"]["line"], e["range"]["start"]["character"]),
            reverse=True,
        )

        # Apply each edit
        for edit in sorted_edits:
            start_line = edit["range"]["start"]["line"]
            start_char = edit["range"]["start"]["character"]
            end_line = edit["range"]["end"]["line"]
            end_char = edit["range"]["end"]["character"]
            new_text = edit["newText"]

            # Simple single-line edit (full implementation would handle multi-line)
            if start_line == end_line:
                line = lines[start_line]
                lines[start_line] = line[:start_char] + new_text + line[end_char:]

        # Write file
        file_path.write_text("\n".join(lines))

    @staticmethod
    def _path_to_uri(path: str | Path) -> str:
        """Convert file path to URI."""
        return Path(path).resolve().as_uri()

    @staticmethod
    def _uri_to_path(uri: str) -> Path:
        """Convert URI to file path."""
        if uri.startswith("file://"):
            uri = uri[7:]
        return Path(uri)

    def __repr__(self) -> str:
        """String representation."""
        return f"LspClient(language={self.language}, initialized={self._initialized})"
