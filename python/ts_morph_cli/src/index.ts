#!/usr/bin/env node

import { Project, SourceFile, Node, SyntaxKind, Diagnostic, FileSystemHost } from 'ts-morph';
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';

// Request/Response types matching Roslyn CLI protocol
interface Request {
  command: string;
  parameters: Record<string, any>;
}

interface Response {
  success: boolean;
  result?: any;
  error?: {
    message: string;
    code: string;
  };
}

interface DiagnosticInfo {
  file_path: string;
  line: number;
  column: number;
  end_line: number;
  end_column: number;
  severity: string;
  message: string;
  code: string;
}

interface SymbolInfo {
  name: string;
  kind: string;
  file_path: string;
  line: number;
  column: number;
  definition_file?: string;
  definition_line?: number;
  definition_column?: number;
  documentation?: string;
}

interface ReferenceInfo {
  file_path: string;
  line: number;
  column: number;
  line_text: string;
  is_definition: boolean;
}

interface RenameResult {
  changes: Array<{
    file_path: string;
    original_text: string;
    modified_text: string;
  }>;
}

// Global project cache
const projectCache = new Map<string, Project>();

function writeResponse(response: Response): void {
  console.log(JSON.stringify(response));
}

function writeSuccess(result: any): void {
  writeResponse({ success: true, result });
}

function writeError(message: string, code: string = 'UNKNOWN_ERROR'): void {
  writeResponse({
    success: false,
    error: { message, code }
  });
}

function getProject(projectPath: string): Project {
  const absolutePath = resolve(projectPath);

  if (!projectCache.has(absolutePath)) {
    // Create new project
    const project = new Project({
      tsConfigFilePath: resolve(absolutePath, 'tsconfig.json'),
      skipAddingFilesFromTsConfig: false,
    });
    projectCache.set(absolutePath, project);
  }

  return projectCache.get(absolutePath)!;
}

function getSourceFile(project: Project, filePath: string): SourceFile {
  const absolutePath = resolve(filePath);
  const sourceFile = project.getSourceFile(absolutePath);

  if (!sourceFile) {
    throw new Error(`Source file not found: ${filePath}`);
  }

  return sourceFile;
}

function getNodeAtPosition(sourceFile: SourceFile, line: number, column: number): Node | undefined {
  // ts-morph uses 0-based positions, convert from 1-based
  const pos = sourceFile.compilerNode.getPositionOfLineAndCharacter(line - 1, column - 1);
  return sourceFile.getDescendantAtPos(pos);
}

function severityToString(severity: number): string {
  switch (severity) {
    case 0: return 'warning';
    case 1: return 'error';
    case 2: return 'suggestion';
    case 3: return 'message';
    default: return 'info';
  }
}

function convertDiagnostic(diagnostic: Diagnostic<any>): DiagnosticInfo {
  const sourceFile = diagnostic.getSourceFile();
  const start = diagnostic.getStart();
  const length = diagnostic.getLength();

  if (!sourceFile || start === undefined || length === undefined) {
    return {
      file_path: '',
      line: 0,
      column: 0,
      end_line: 0,
      end_column: 0,
      severity: severityToString(diagnostic.getCategory()),
      message: diagnostic.getMessageText()?.toString() || '',
      code: diagnostic.getCode()?.toString() || ''
    };
  }

  const startLineAndChar = sourceFile.getLineAndColumnAtPos(start);
  const endLineAndChar = sourceFile.getLineAndColumnAtPos(start + length);

  return {
    file_path: sourceFile.getFilePath(),
    line: startLineAndChar.line,
    column: startLineAndChar.column,
    end_line: endLineAndChar.line,
    end_column: endLineAndChar.column,
    severity: severityToString(diagnostic.getCategory()),
    message: diagnostic.getMessageText()?.toString() || '',
    code: diagnostic.getCode()?.toString() || ''
  };
}

async function handleVersion(): Promise<any> {
  const packageJson = JSON.parse(
    readFileSync(new URL('../package.json', import.meta.url), 'utf-8')
  );

  return {
    version: packageJson.version,
    ts_morph_version: packageJson.dependencies['ts-morph'],
    typescript_version: packageJson.devDependencies['typescript']
  };
}

async function handleLoadProject(params: any): Promise<any> {
  const { project_path } = params;

  if (!project_path) {
    throw new Error('project_path is required');
  }

  const project = getProject(project_path);
  const sourceFiles = project.getSourceFiles();

  return {
    project_path: resolve(project_path),
    file_count: sourceFiles.length,
    files: sourceFiles.map(sf => sf.getFilePath())
  };
}

async function handleGetDiagnostics(params: any): Promise<any> {
  const { project_path, file_path } = params;

  const project = getProject(project_path);

  if (file_path) {
    // Get diagnostics for specific file
    const sourceFile = getSourceFile(project, file_path);
    const preDiagnostics = project.getPreEmitDiagnostics().filter(d =>
      d.getSourceFile()?.getFilePath() === sourceFile.getFilePath()
    );

    return {
      diagnostics: preDiagnostics.map(convertDiagnostic)
    };
  } else {
    // Get diagnostics for entire project
    const diagnostics = project.getPreEmitDiagnostics();

    return {
      diagnostics: diagnostics.map(convertDiagnostic)
    };
  }
}

async function handleFindReferences(params: any): Promise<any> {
  const { project_path, file_path, line, column } = params;

  const project = getProject(project_path);
  const sourceFile = getSourceFile(project, file_path);
  const node = getNodeAtPosition(sourceFile, line, column);

  if (!node) {
    throw new Error(`No node found at ${file_path}:${line}:${column}`);
  }

  const referencedSymbols = node.findReferences();
  const references: ReferenceInfo[] = [];

  for (const referencedSymbol of referencedSymbols) {
    for (const reference of referencedSymbol.getReferences()) {
      const refSourceFile = reference.getSourceFile();
      const textSpan = reference.getTextSpan();
      const lineAndChar = refSourceFile.getLineAndColumnAtPos(textSpan.getStart());
      const lineText = refSourceFile.getFullText().split('\n')[lineAndChar.line - 1] || '';

      references.push({
        file_path: refSourceFile.getFilePath(),
        line: lineAndChar.line,
        column: lineAndChar.column,
        line_text: lineText.trim(),
        is_definition: reference.isDefinition()
      });
    }
  }

  return { references };
}

async function handleRenameSymbol(params: any): Promise<any> {
  const { project_path, file_path, line, column, new_name } = params;

  const project = getProject(project_path);
  const sourceFile = getSourceFile(project, file_path);
  const node = getNodeAtPosition(sourceFile, line, column);

  if (!node) {
    throw new Error(`No node found at ${file_path}:${line}:${column}`);
  }

  // Find renameable node
  let renameNode = node;
  while (renameNode && !Node.isReferenceFindable(renameNode)) {
    renameNode = renameNode.getParent();
  }

  if (!renameNode || !Node.isReferenceFindable(renameNode)) {
    throw new Error('Symbol at position is not renameable');
  }

  // Collect original content of all affected files
  const affectedFiles = new Map<string, string>();
  const referencedSymbols = renameNode.findReferences();

  for (const referencedSymbol of referencedSymbols) {
    for (const reference of referencedSymbol.getReferences()) {
      const refSourceFile = reference.getSourceFile();
      const filePath = refSourceFile.getFilePath();
      if (!affectedFiles.has(filePath)) {
        affectedFiles.set(filePath, refSourceFile.getFullText());
      }
    }
  }

  // Perform rename
  renameNode.rename(new_name);

  // Collect changes
  const changes: Array<{ file_path: string; original_text: string; modified_text: string }> = [];

  for (const [filePath, originalText] of affectedFiles.entries()) {
    const sourceFile = project.getSourceFile(filePath);
    if (sourceFile) {
      const modifiedText = sourceFile.getFullText();
      if (originalText !== modifiedText) {
        changes.push({
          file_path: filePath,
          original_text: originalText,
          modified_text: modifiedText
        });
      }
    }
  }

  // Save changes to disk
  await project.save();

  return { changes };
}

async function handleGetSymbolInfo(params: any): Promise<any> {
  const { project_path, file_path, line, column } = params;

  const project = getProject(project_path);
  const sourceFile = getSourceFile(project, file_path);
  const node = getNodeAtPosition(sourceFile, line, column);

  if (!node) {
    throw new Error(`No node found at ${file_path}:${line}:${column}`);
  }

  // Try to get symbol
  const symbol = node.getSymbol();
  if (!symbol) {
    throw new Error('No symbol found at position');
  }

  const declarations = symbol.getDeclarations();
  const firstDeclaration = declarations[0];

  let defFile: string | undefined;
  let defLine: number | undefined;
  let defColumn: number | undefined;

  if (firstDeclaration) {
    const declSourceFile = firstDeclaration.getSourceFile();
    const declStart = firstDeclaration.getStart();
    const lineAndChar = declSourceFile.getLineAndColumnAtPos(declStart);

    defFile = declSourceFile.getFilePath();
    defLine = lineAndChar.line;
    defColumn = lineAndChar.column;
  }

  const symbolInfo: SymbolInfo = {
    name: symbol.getName(),
    kind: node.getKindName(),
    file_path: sourceFile.getFilePath(),
    line: line,
    column: column,
    definition_file: defFile,
    definition_line: defLine,
    definition_column: defColumn,
    documentation: symbol.getDocumentationCommentText()
  };

  return symbolInfo;
}

async function handleExtractMethod(params: any): Promise<any> {
  const { project_path, file_path, start_line, start_column, end_line, end_column, method_name } = params;

  const project = getProject(project_path);
  const sourceFile = getSourceFile(project, file_path);

  // Get start and end positions
  const startPos = sourceFile.compilerNode.getPositionOfLineAndCharacter(start_line - 1, start_column - 1);
  const endPos = sourceFile.compilerNode.getPositionOfLineAndCharacter(end_line - 1, end_column - 1);

  // Get the selected text
  const selectedText = sourceFile.getFullText().substring(startPos, endPos);

  // Find the containing function/method
  const startNode = sourceFile.getDescendantAtPos(startPos);
  if (!startNode) {
    throw new Error('No node found at start position');
  }

  // Find containing function, method, or arrow function
  let containingFunction = startNode.getFirstAncestorByKind(SyntaxKind.FunctionDeclaration)
    || startNode.getFirstAncestorByKind(SyntaxKind.MethodDeclaration)
    || startNode.getFirstAncestorByKind(SyntaxKind.ArrowFunction)
    || startNode.getFirstAncestorByKind(SyntaxKind.FunctionExpression);

  if (!containingFunction) {
    throw new Error('Selected code is not within a function or method');
  }

  // This is a simplified implementation
  // A full implementation would:
  // 1. Analyze variables used in selected code
  // 2. Determine which are defined outside (need to be parameters)
  // 3. Determine which are modified (need to be returned)
  // 4. Generate proper method signature with parameters and return type
  // 5. Insert method call at original location
  // 6. Insert new method definition

  const originalText = sourceFile.getFullText();

  // For now, create a simple extracted method
  const extractedMethod = `
  function ${method_name}() {
    ${selectedText}
  }
`;

  // Replace selected text with method call
  const beforeSelection = originalText.substring(0, startPos);
  const afterSelection = originalText.substring(endPos);
  const methodCall = `${method_name}();`;

  const modifiedText = beforeSelection + methodCall + afterSelection;

  // Find a good place to insert the new method (after containing function)
  const containingFunctionEnd = containingFunction.getEnd();
  const finalText = modifiedText.substring(0, containingFunctionEnd)
    + extractedMethod
    + modifiedText.substring(containingFunctionEnd);

  sourceFile.replaceWithText(finalText);
  await project.save();

  return {
    changes: [{
      file_path: sourceFile.getFilePath(),
      original_text: originalText,
      modified_text: finalText
    }],
    extracted_method_name: method_name
  };
}

async function processCommand(request: Request): Promise<any> {
  switch (request.command) {
    case 'version':
      return await handleVersion();

    case 'load_project':
      return await handleLoadProject(request.parameters);

    case 'get_diagnostics':
      return await handleGetDiagnostics(request.parameters);

    case 'find_references':
      return await handleFindReferences(request.parameters);

    case 'rename_symbol':
      return await handleRenameSymbol(request.parameters);

    case 'get_symbol_info':
      return await handleGetSymbolInfo(request.parameters);

    case 'extract_method':
      return await handleExtractMethod(request.parameters);

    default:
      throw new Error(`Unknown command: ${request.command}`);
  }
}

async function main(): Promise<void> {
  try {
    // Read input from stdin
    const input = readFileSync(0, 'utf-8');

    if (!input.trim()) {
      writeError('No input provided', 'INVALID_INPUT');
      return;
    }

    // Parse request
    let request: Request;
    try {
      request = JSON.parse(input);
    } catch (e) {
      writeError('Invalid JSON input', 'INVALID_JSON');
      return;
    }

    // Process command
    const result = await processCommand(request);
    writeSuccess(result);

  } catch (error: any) {
    writeError(error.message || 'Unknown error occurred', error.code || 'UNKNOWN_ERROR');
  }
}

// Run main
main();
