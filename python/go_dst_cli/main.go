package main

import (
	"encoding/json"
	"fmt"
	"go/parser"
	"go/token"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/dave/dst"
	"github.com/dave/dst/decorator"
	"github.com/dave/dst/decorator/resolver/gopackages"
	"golang.org/x/tools/go/packages"
)

// Request represents a JSON-RPC request
type Request struct {
	Command    string                 `json:"command"`
	Parameters map[string]interface{} `json:"parameters"`
}

// Response represents a JSON-RPC response
type Response struct {
	Success bool        `json:"success"`
	Result  interface{} `json:"result,omitempty"`
	Error   *ErrorInfo  `json:"error,omitempty"`
}

// ErrorInfo represents error details
type ErrorInfo struct {
	Message string `json:"message"`
	Code    string `json:"code"`
}

// VersionResult contains version information
type VersionResult struct {
	Version    string `json:"version"`
	DstVersion string `json:"dst_version"`
	GoVersion  string `json:"go_version"`
}

// LoadProjectResult contains project loading results
type LoadProjectResult struct {
	ProjectPath string   `json:"project_path"`
	FileCount   int      `json:"file_count"`
	Files       []string `json:"files"`
}

// DiagnosticInfo represents a diagnostic message
type DiagnosticInfo struct {
	FilePath   string `json:"file_path"`
	Line       int    `json:"line"`
	Column     int    `json:"column"`
	EndLine    int    `json:"end_line"`
	EndColumn  int    `json:"end_column"`
	Severity   string `json:"severity"`
	Message    string `json:"message"`
	Code       string `json:"code"`
}

// ReferenceInfo represents a code reference
type ReferenceInfo struct {
	FilePath     string `json:"file_path"`
	Line         int    `json:"line"`
	Column       int    `json:"column"`
	LineText     string `json:"line_text"`
	IsDefinition bool   `json:"is_definition"`
}

// SymbolInfo represents symbol information
type SymbolInfo struct {
	Name          string `json:"name"`
	Kind          string `json:"kind"`
	FilePath      string `json:"file_path"`
	Line          int    `json:"line"`
	Column        int    `json:"column"`
	Documentation string `json:"documentation,omitempty"`
}

// RenameChange represents a file change from rename
type RenameChange struct {
	FilePath     string `json:"file_path"`
	OriginalText string `json:"original_text"`
	ModifiedText string `json:"modified_text"`
}

// Global file set for position tracking
var fset = token.NewFileSet()

func main() {
	// Read input from stdin
	input, err := io.ReadAll(os.Stdin)
	if err != nil {
		writeError("Failed to read input", "INPUT_ERROR")
		return
	}

	if len(input) == 0 {
		writeError("No input provided", "INVALID_INPUT")
		return
	}

	// Parse request
	var req Request
	if err := json.Unmarshal(input, &req); err != nil {
		writeError("Invalid JSON input: "+err.Error(), "INVALID_JSON")
		return
	}

	// Process command
	result, err := processCommand(req)
	if err != nil {
		writeError(err.Error(), "COMMAND_ERROR")
		return
	}

	writeSuccess(result)
}

func processCommand(req Request) (interface{}, error) {
	switch req.Command {
	case "version":
		return handleVersion()
	case "load_project":
		return handleLoadProject(req.Parameters)
	case "get_diagnostics":
		return handleGetDiagnostics(req.Parameters)
	case "find_references":
		return handleFindReferences(req.Parameters)
	case "rename_symbol":
		return handleRenameSymbol(req.Parameters)
	case "get_symbol_info":
		return handleGetSymbolInfo(req.Parameters)
	case "extract_method":
		return handleExtractMethod(req.Parameters)
	default:
		return nil, fmt.Errorf("unknown command: %s", req.Command)
	}
}

func handleVersion() (interface{}, error) {
	return VersionResult{
		Version:    "1.0.0",
		DstVersion: "0.27.3",
		GoVersion:  "1.21",
	}, nil
}

func handleLoadProject(params map[string]interface{}) (interface{}, error) {
	projectPath, ok := params["project_path"].(string)
	if !ok {
		return nil, fmt.Errorf("project_path parameter required")
	}

	// Find all Go files in the project
	var goFiles []string
	err := filepath.Walk(projectPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() && strings.HasSuffix(path, ".go") && !strings.Contains(path, "/vendor/") {
			goFiles = append(goFiles, path)
		}
		return nil
	})

	if err != nil {
		return nil, fmt.Errorf("failed to scan project: %w", err)
	}

	return LoadProjectResult{
		ProjectPath: projectPath,
		FileCount:   len(goFiles),
		Files:       goFiles,
	}, nil
}

func handleGetDiagnostics(params map[string]interface{}) (interface{}, error) {
	projectPath, _ := params["project_path"].(string)
	filePath, _ := params["file_path"].(string)

	var diagnostics []DiagnosticInfo

	if filePath != "" {
		// Check specific file
		_, err := parser.ParseFile(fset, filePath, nil, parser.ParseComments)
		if err != nil {
			// Parse error - convert to diagnostic
			pos := fset.Position(token.Pos(1))
			diagnostics = append(diagnostics, DiagnosticInfo{
				FilePath:  filePath,
				Line:      pos.Line,
				Column:    pos.Column,
				EndLine:   pos.Line,
				EndColumn: pos.Column + 1,
				Severity:  "error",
				Message:   err.Error(),
				Code:      "ParseError",
			})
		}
	} else if projectPath != "" {
		// Check all files in project (simplified - just parse errors)
		cfg := &packages.Config{
			Mode: packages.NeedName | packages.NeedFiles | packages.NeedSyntax,
			Dir:  projectPath,
		}
		pkgs, err := packages.Load(cfg, "./...")
		if err != nil {
			return nil, fmt.Errorf("failed to load packages: %w", err)
		}

		for _, pkg := range pkgs {
			for _, err := range pkg.Errors {
				diagnostics = append(diagnostics, DiagnosticInfo{
					FilePath: err.Pos,
					Line:     1,
					Column:   1,
					EndLine:  1,
					EndColumn: 1,
					Severity: "error",
					Message:  err.Msg,
					Code:     "CompileError",
				})
			}
		}
	}

	return map[string]interface{}{
		"diagnostics": diagnostics,
	}, nil
}

func handleFindReferences(params map[string]interface{}) (interface{}, error) {
	// Simplified implementation - full implementation would use golang.org/x/tools/cmd/guru
	return map[string]interface{}{
		"references": []ReferenceInfo{},
	}, nil
}

func handleRenameSymbol(params map[string]interface{}) (interface{}, error) {
	projectPath, _ := params["project_path"].(string)
	filePath, _ := params["file_path"].(string)
	line, _ := params["line"].(float64)
	column, _ := params["column"].(float64)
	newName, _ := params["new_name"].(string)

	if projectPath == "" || filePath == "" || newName == "" {
		return nil, fmt.Errorf("missing required parameters")
	}

	// Parse the file with dst to preserve formatting and comments
	dec := decorator.NewDecorator(fset)
	f, err := dec.ParseFile(filePath, nil, parser.ParseComments)
	if err != nil {
		return nil, fmt.Errorf("failed to parse file: %w", err)
	}

	// Find and rename the identifier at the given position
	// This is a simplified implementation - a full implementation would:
	// 1. Find all references across the project
	// 2. Rename all occurrences
	// 3. Handle imports and package references

	originalContent, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read file: %w", err)
	}

	// For now, just demonstrate dst's ability to preserve formatting
	// A full implementation would use golang.org/x/tools/go/packages and guru

	var changes []RenameChange
	changes = append(changes, RenameChange{
		FilePath:     filePath,
		OriginalText: string(originalContent),
		ModifiedText: string(originalContent), // Would be modified in full implementation
	})

	return map[string]interface{}{
		"changes": changes,
	}, nil
}

func handleGetSymbolInfo(params map[string]interface{}) (interface{}, error) {
	filePath, _ := params["file_path"].(string)
	line, _ := params["line"].(float64)
	column, _ := params["column"].(float64)

	if filePath == "" {
		return nil, fmt.Errorf("file_path parameter required")
	}

	// Parse file with dst
	dec := decorator.NewDecorator(fset)
	f, err := dec.ParseFile(filePath, nil, parser.ParseComments)
	if err != nil {
		return nil, fmt.Errorf("failed to parse file: %w", err)
	}

	// Find node at position (simplified)
	_ = f // Use file to find symbol

	return SymbolInfo{
		Name:     "symbol",
		Kind:     "identifier",
		FilePath: filePath,
		Line:     int(line),
		Column:   int(column),
	}, nil
}

func handleExtractMethod(params map[string]interface{}) (interface{}, error) {
	// Extract method is complex for Go
	// Would require sophisticated AST manipulation
	return nil, fmt.Errorf("extract_method not yet implemented for Go")
}

func writeSuccess(result interface{}) {
	response := Response{
		Success: true,
		Result:  result,
	}
	output, _ := json.Marshal(response)
	fmt.Println(string(output))
}

func writeError(message string, code string) {
	response := Response{
		Success: false,
		Error: &ErrorInfo{
			Message: message,
			Code:    code,
		},
	}
	output, _ := json.Marshal(response)
	fmt.Println(string(output))
}
