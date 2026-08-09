import ast
import os
import re
import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

@dataclass
class SymbolLocation:
    file_path: str
    line_number: int
    symbol_type: str  # 'class' | 'function' | 'method' | 'import' | 'export' | 'reference'
    name: str
    signature: str

class PythonSymbolVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.symbols: List[SymbolLocation] = []
        self._class_context: List[str] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        sig = f"class {node.name}"
        if node.bases:
            bases = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    bases.append(b.id)
                elif isinstance(b, ast.Attribute):
                    bases.append(b.attr)
            if bases:
                sig += f"({', '.join(bases)})"
        
        self.symbols.append(SymbolLocation(
            file_path=self.file_path,
            line_number=node.lineno,
            symbol_type='class',
            name=node.name,
            signature=sig
        ))
        
        self._class_context.append(node.name)
        self.generic_visit(node)
        self._class_context.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_func(node)
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_func(node, is_async=True)
        
    def _visit_func(self, node, is_async: bool = False):
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        
        arg_str = ", ".join(args)
        prefix = "async def" if is_async else "def"
        sig = f"{prefix} {node.name}({arg_str})"
        
        if node.returns:
            if isinstance(node.returns, ast.Name):
                sig += f" -> {node.returns.id}"
            elif isinstance(node.returns, ast.Constant):
                sig += f" -> {node.returns.value}"
                
        is_method = len(self._class_context) > 0
        sym_type = 'method' if is_method else 'function'
        
        self.symbols.append(SymbolLocation(
            file_path=self.file_path,
            line_number=node.lineno,
            symbol_type=sym_type,
            name=node.name,
            signature=sig
        ))
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.symbols.append(SymbolLocation(
                file_path=self.file_path,
                line_number=node.lineno,
                symbol_type='import',
                name=alias.name,
                signature=f"import {alias.name}"
            ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ''
        for alias in node.names:
            name = alias.name
            self.symbols.append(SymbolLocation(
                file_path=self.file_path,
                line_number=node.lineno,
                symbol_type='import',
                name=name,
                signature=f"from {module} import {name}"
            ))
        self.generic_visit(node)


class CodeMapper:
    """
    Code Mapper class to parse and navigate symbols in code files.
    """
    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = workspace_dir

    def parse_python_symbols(self, file_path: str, content: str) -> List[SymbolLocation]:
        """Parse Python files using AST to extract symbols."""
        try:
            tree = ast.parse(content, filename=file_path)
            visitor = PythonSymbolVisitor(file_path)
            visitor.visit(tree)
            return visitor.symbols
        except Exception as e:
            logger.error(f"Failed to parse python file {file_path}: {e}")
            return []

    def parse_js_ts_symbols(self, file_path: str, content: str) -> List[SymbolLocation]:
        """Parse JavaScript and TypeScript files using Regex to extract symbols."""
        symbols = []
        lines = content.split('\n')
        for i, line in enumerate(lines):
            lineno = i + 1
            
            # import
            m_import = re.match(r'^\s*import\s+.*?\s+from', line)
            if m_import:
                m_name = re.search(r'import\s+(.*?)\s+from', line)
                name = m_name.group(1).strip() if m_name else "import"
                symbols.append(SymbolLocation(file_path, lineno, 'import', name, line.strip()))
                continue
                
            # class
            m_class = re.search(r'\bclass\s+([a-zA-Z_$][0-9a-zA-Z_$]*)', line)
            if m_class:
                is_export = 'export' in line
                sym_type = 'export' if is_export else 'class'
                symbols.append(SymbolLocation(file_path, lineno, sym_type, m_class.group(1), line.strip()))
                continue
                
            # function
            m_func = re.search(r'\bfunction\s+([a-zA-Z_$][0-9a-zA-Z_$]*)\s*\(', line)
            if m_func:
                is_export = 'export' in line
                sym_type = 'export' if is_export else 'function'
                symbols.append(SymbolLocation(file_path, lineno, sym_type, m_func.group(1), line.strip()))
                continue
                
            # export const / let / var
            m_const = re.search(r'\bexport\s+(?:const|let|var)\s+([a-zA-Z_$][0-9a-zA-Z_$]*)', line)
            if m_const:
                symbols.append(SymbolLocation(file_path, lineno, 'export', m_const.group(1), line.strip()))
                continue

        return symbols

    def build_repo_map(self, max_files: int = 100) -> str:
        """Walk the workspace directory and build a string representation of the repository symbols."""
        if not self.workspace_dir or not os.path.isdir(self.workspace_dir):
            return ""
            
        ignore_dirs = {'node_modules', '.git', 'venv', '__pycache__', 'dist', '.next'}
        code_exts = {'.py', '.js', '.jsx', '.ts', '.tsx'}
        
        result = []
        files_processed = 0
        
        for root, dirs, files in os.walk(self.workspace_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                if files_processed >= max_files:
                    break
                    
                ext = os.path.splitext(file)[1]
                if ext not in code_exts:
                    continue
                    
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    if ext == '.py':
                        symbols = self.parse_python_symbols(full_path, content)
                    else:
                        symbols = self.parse_js_ts_symbols(full_path, content)
                        
                    if symbols:
                        rel_path = os.path.relpath(full_path, self.workspace_dir).replace('\\', '/')
                        result.append(f"{rel_path}:")
                        defs = [s for s in symbols if s.symbol_type != 'import']
                        for s in defs:
                            result.append(f"  L{s.line_number} {s.signature}")
                            
                    files_processed += 1
                except Exception as e:
                    logger.debug(f"Failed to process {full_path}: {e}")
                    
            if files_processed >= max_files:
                break
                
        return "\n".join(result)

    def find_definition(self, symbol_name: str) -> List[SymbolLocation]:
        """Find definitions of a specific symbol across the workspace."""
        if not self.workspace_dir or not os.path.isdir(self.workspace_dir):
            return []
            
        ignore_dirs = {'node_modules', '.git', 'venv', '__pycache__', 'dist', '.next'}
        code_exts = {'.py', '.js', '.jsx', '.ts', '.tsx'}
        
        results = []
        for root, dirs, files in os.walk(self.workspace_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext not in code_exts:
                    continue
                    
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    if ext == '.py':
                        symbols = self.parse_python_symbols(full_path, content)
                    else:
                        symbols = self.parse_js_ts_symbols(full_path, content)
                        
                    for s in symbols:
                        if s.name == symbol_name and s.symbol_type != 'import':
                            results.append(s)
                except Exception:
                    pass
        return results

    def find_references(self, symbol_name: str) -> List[SymbolLocation]:
        """Find occurrences/references of a specific symbol across the workspace."""
        if not self.workspace_dir or not os.path.isdir(self.workspace_dir):
            return []
            
        ignore_dirs = {'node_modules', '.git', 'venv', '__pycache__', 'dist', '.next'}
        code_exts = {'.py', '.js', '.jsx', '.ts', '.tsx'}
        
        results = []
        for root, dirs, files in os.walk(self.workspace_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext not in code_exts:
                    continue
                    
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        
                    ref_pattern = re.compile(rf'\b{re.escape(symbol_name)}\b')
                    for i, line in enumerate(lines):
                        if ref_pattern.search(line):
                            results.append(SymbolLocation(
                                file_path=full_path,
                                line_number=i + 1,
                                symbol_type='reference',
                                name=symbol_name,
                                signature=line.strip()
                            ))
                except Exception:
                    pass
        return results

    def get_file_outline(self, file_path: str) -> str:
        """Get formatted outline of symbols for a specific file."""
        if not os.path.isfile(file_path):
            return ""
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            ext = os.path.splitext(file_path)[1]
            if ext == '.py':
                symbols = self.parse_python_symbols(file_path, content)
            elif ext in {'.js', '.jsx', '.ts', '.tsx'}:
                symbols = self.parse_js_ts_symbols(file_path, content)
            else:
                return ""
                
            if not symbols:
                return f"{file_path}:\n  (no symbols found)"
                
            result = [f"{file_path}:"]
            for s in symbols:
                result.append(f"  L{s.line_number} [{s.symbol_type}] {s.signature}")
            return "\n".join(result)
        except Exception as e:
            logger.error(f"Failed to get outline for {file_path}: {e}")
            return ""


_code_mapper: Optional[CodeMapper] = None

def get_code_mapper(workspace_dir: Optional[str] = None) -> CodeMapper:
    """Singleton helper to get the CodeMapper instance."""
    global _code_mapper
    if _code_mapper is None:
        _code_mapper = CodeMapper(workspace_dir)
    elif workspace_dir is not None and _code_mapper.workspace_dir != workspace_dir:
        _code_mapper = CodeMapper(workspace_dir)
    return _code_mapper
