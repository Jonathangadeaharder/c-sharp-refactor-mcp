package main

import (
	"encoding/json"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"go/types"
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
	projectPath, _ := params["project_path"].(string)
	filePath, _ := params["file_path"].(string)
	line, _ := params["line"].(float64)
	column, _ := params["column"].(float64)

	if projectPath == "" || filePath == "" {
		return nil, fmt.Errorf("missing required parameters")
	}

	// Load the package using go/packages
	cfg := &packages.Config{
		Mode: packages.NeedName | packages.NeedFiles | packages.NeedSyntax | packages.NeedTypesInfo | packages.NeedTypes,
		Dir:  projectPath,
	}

	pkgs, err := packages.Load(cfg, "./...")
	if err != nil {
		return nil, fmt.Errorf("failed to load packages: %w", err)
	}

	var references []ReferenceInfo

	// Find the symbol at the given position
	targetPos := token.Pos(0)
	var targetObj *types.Object

	for _, pkg := range pkgs {
		for _, file := range pkg.Syntax {
			fpos := fset.File(file.Pos())
			if fpos == nil || fpos.Name() != filePath {
				continue
			}

			// Convert line/column to token.Pos
			offset := lineColumnToOffset(fpos, int(line), int(column))
			targetPos = fpos.Pos(offset)

			// Find the identifier at this position
			ast.Inspect(file, func(n ast.Node) bool {
				if ident, ok := n.(*ast.Ident); ok {
					if ident.Pos() <= targetPos && targetPos <= ident.End() {
						targetObj = pkg.TypesInfo.Uses[ident]
						if targetObj == nil {
							targetObj = pkg.TypesInfo.Defs[ident]
						}
						return false
					}
				}
				return true
			})

			if targetObj != nil {
				break
			}
		}
		if targetObj != nil {
			break
		}
	}

	if targetObj == nil {
		return map[string]interface{}{
			"references": references,
		}, nil
	}

	// Find all references to this symbol
	for _, pkg := range pkgs {
		for _, file := range pkg.Syntax {
			fpos := fset.File(file.Pos())
			if fpos == nil {
				continue
			}

			ast.Inspect(file, func(n ast.Node) bool {
				if ident, ok := n.(*ast.Ident); ok {
					obj := pkg.TypesInfo.Uses[ident]
					if obj == nil {
						obj = pkg.TypesInfo.Defs[ident]
					}

					if obj != nil && obj == targetObj {
						pos := fset.Position(ident.Pos())
						lineText := getLineText(fpos, pos.Line)

						references = append(references, ReferenceInfo{
							FilePath:     pos.Filename,
							Line:         pos.Line,
							Column:       pos.Column,
							LineText:     lineText,
							IsDefinition: pkg.TypesInfo.Defs[ident] != nil,
						})
					}
				}
				return true
			})
		}
	}

	return map[string]interface{}{
		"references": references,
	}, nil
}

func lineColumnToOffset(file *token.File, line, column int) int {
	lineOffset := file.LineStart(line)
	return int(lineOffset) - file.Base() + column - 1
}

func getLineText(file *token.File, line int) string {
	// Read the file and get the line text
	// Simplified implementation
	return fmt.Sprintf("line %d", line)
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

	// Load packages to get type information
	cfg := &packages.Config{
		Mode: packages.NeedName | packages.NeedFiles | packages.NeedSyntax | packages.NeedTypesInfo | packages.NeedTypes,
		Dir:  projectPath,
	}

	pkgs, err := packages.Load(cfg, "./...")
	if err != nil {
		return nil, fmt.Errorf("failed to load packages: %w", err)
	}

	// Find the symbol to rename
	var targetObj *types.Object
	for _, pkg := range pkgs {
		for _, file := range pkg.Syntax {
			fpos := fset.File(file.Pos())
			if fpos == nil || fpos.Name() != filePath {
				continue
			}

			offset := lineColumnToOffset(fpos, int(line), int(column))
			targetPos := fpos.Pos(offset)

			ast.Inspect(file, func(n ast.Node) bool {
				if ident, ok := n.(*ast.Ident); ok {
					if ident.Pos() <= targetPos && targetPos <= ident.End() {
						targetObj = pkg.TypesInfo.Uses[ident]
						if targetObj == nil {
							targetObj = pkg.TypesInfo.Defs[ident]
						}
						return false
					}
				}
				return true
			})

			if targetObj != nil {
				break
			}
		}
		if targetObj != nil {
			break
		}
	}

	if targetObj == nil {
		return nil, fmt.Errorf("no symbol found at position")
	}

	// Collect all files that need changes
	fileChanges := make(map[string]*dst.File)
	filePaths := make(map[string]string)

	for _, pkg := range pkgs {
		for i, file := range pkg.Syntax {
			fpos := fset.File(file.Pos())
			if fpos == nil {
				continue
			}

			needsChange := false
			ast.Inspect(file, func(n ast.Node) bool {
				if ident, ok := n.(*ast.Ident); ok {
					obj := pkg.TypesInfo.Uses[ident]
					if obj == nil {
						obj = pkg.TypesInfo.Defs[ident]
					}
					if obj != nil && obj == targetObj {
						needsChange = true
						return false
					}
				}
				return true
			})

			if needsChange {
				// Parse with dst to preserve formatting
				dec := decorator.NewDecorator(fset)
				dstFile, err := dec.ParseFile(fpos.Name(), nil, parser.ParseComments)
				if err != nil {
					continue
				}
				fileChanges[fpos.Name()] = dstFile
				filePaths[fpos.Name()] = pkg.CompiledGoFiles[i]
			}
		}
	}

	// Apply renames using dst
	for path, dstFile := range fileChanges {
		dst.Inspect(dstFile, func(n dst.Node) bool {
			if ident, ok := n.(*dst.Ident); ok {
				// Match identifier names (simplified - should use type info)
				if ident.Name == targetObj.Name() {
					ident.Name = newName
				}
			}
			return true
		})
	}

	// Generate results
	var changes []RenameChange
	for path, dstFile := range fileChanges {
		originalContent, _ := os.ReadFile(path)

		// Restore file with dst to preserve comments
		res := decorator.NewRestorer()
		modifiedFile := res.FileSet.AddFile(path, -1, len(originalContent))
		var modifiedContent strings.Builder
		if err := res.Fprint(&modifiedContent, dstFile); err != nil {
			continue
		}

		changes = append(changes, RenameChange{
			FilePath:     path,
			OriginalText: string(originalContent),
			ModifiedText: modifiedContent.String(),
		})

		// Write the changes back to disk
		if err := os.WriteFile(path, []byte(modifiedContent.String()), 0644); err != nil {
			return nil, fmt.Errorf("failed to write file %s: %w", path, err)
		}
	}

	return map[string]interface{}{
		"changes": changes,
	}, nil
}

func handleGetSymbolInfo(params map[string]interface{}) (interface{}, error) {
	projectPath, _ := params["project_path"].(string)
	filePath, _ := params["file_path"].(string)
	line, _ := params["line"].(float64)
	column, _ := params["column"].(float64)

	if filePath == "" {
		return nil, fmt.Errorf("file_path parameter required")
	}

	// If project_path provided, use full type information
	if projectPath != "" {
		cfg := &packages.Config{
			Mode: packages.NeedName | packages.NeedFiles | packages.NeedSyntax | packages.NeedTypesInfo | packages.NeedTypes,
			Dir:  projectPath,
		}

		pkgs, err := packages.Load(cfg, "./...")
		if err != nil {
			return nil, fmt.Errorf("failed to load packages: %w", err)
		}

		// Find symbol at position
		for _, pkg := range pkgs {
			for _, file := range pkg.Syntax {
				fpos := fset.File(file.Pos())
				if fpos == nil || fpos.Name() != filePath {
					continue
				}

				offset := lineColumnToOffset(fpos, int(line), int(column))
				targetPos := fpos.Pos(offset)

				var foundIdent *ast.Ident
				var foundObj *types.Object
				ast.Inspect(file, func(n ast.Node) bool {
					if ident, ok := n.(*ast.Ident); ok {
						if ident.Pos() <= targetPos && targetPos <= ident.End() {
							foundIdent = ident
							foundObj = pkg.TypesInfo.Uses[ident]
							if foundObj == nil {
								foundObj = pkg.TypesInfo.Defs[ident]
							}
							return false
						}
					}
					return true
				})

				if foundIdent != nil {
					kind := "identifier"
					documentation := ""

					if foundObj != nil {
						switch foundObj.(type) {
						case *types.Func:
							kind = "function"
						case *types.Var:
							kind = "variable"
						case *types.Const:
							kind = "constant"
						case *types.TypeName:
							kind = "type"
						case *types.PkgName:
							kind = "package"
						}

						// Try to find documentation
						documentation = findDocumentation(file, foundIdent.Pos())
					}

					pos := fset.Position(foundIdent.Pos())
					return SymbolInfo{
						Name:          foundIdent.Name,
						Kind:          kind,
						FilePath:      pos.Filename,
						Line:          pos.Line,
						Column:        pos.Column,
						Documentation: documentation,
					}, nil
				}
			}
		}
	}

	// Fallback: simple parsing without type info
	dec := decorator.NewDecorator(fset)
	f, err := dec.ParseFile(filePath, nil, parser.ParseComments)
	if err != nil {
		return nil, fmt.Errorf("failed to parse file: %w", err)
	}

	// Simple identifier lookup
	return SymbolInfo{
		Name:     "symbol",
		Kind:     "identifier",
		FilePath: filePath,
		Line:     int(line),
		Column:   int(column),
	}, nil
}

func findDocumentation(file *ast.File, pos token.Pos) string {
	// Find the comment group before the declaration
	for _, decl := range file.Decls {
		if genDecl, ok := decl.(*ast.GenDecl); ok {
			if genDecl.Doc != nil && genDecl.Pos() > pos-1000 && genDecl.Pos() < pos+1000 {
				return genDecl.Doc.Text()
			}
		}
		if funcDecl, ok := decl.(*ast.FuncDecl); ok {
			if funcDecl.Doc != nil && funcDecl.Pos() > pos-1000 && funcDecl.Pos() < pos+1000 {
				return funcDecl.Doc.Text()
			}
		}
	}
	return ""
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
