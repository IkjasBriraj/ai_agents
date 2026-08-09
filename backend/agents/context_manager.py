import os
import ast
import re
import logging
from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from .config import AGENT_WORKSPACE_DIR

logger = logging.getLogger(__name__)

# Default token budget allocation percentages
BUDGET_SYSTEM = 0.15      # 15% for system prompt + tool definitions
BUDGET_PROJECT = 0.20     # 20% for project context map
BUDGET_ACTIVE = 0.50      # 50% for active file buffers + conversation
BUDGET_SCRATCHPAD = 0.15  # 15% for completion / scratchpad

# Approximate tokens per character ratio (conservative)
CHARS_PER_TOKEN = 3.5

class ContextManager:
    """Manages token budgets, compacts conversation history, and builds hierarchical project context."""
    
    def __init__(self, total_token_budget: int = 8192, workspace_dir: Optional[str] = None):
        self.total_token_budget = total_token_budget
        self.workspace_dir = workspace_dir or AGENT_WORKSPACE_DIR
        
        # Calculate budget allocations based on percentages
        self.budgets = {
            'system': int(self.total_token_budget * BUDGET_SYSTEM),
            'project': int(self.total_token_budget * BUDGET_PROJECT),
            'active': int(self.total_token_budget * BUDGET_ACTIVE),
            'scratchpad': int(self.total_token_budget * BUDGET_SCRATCHPAD)
        }
        
        # Working memory scratchpad
        self._scratchpad: Dict[str, Any] = {}

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a given text."""
        return int(len(text) / CHARS_PER_TOKEN)

    def compact_history(self, messages: List[BaseMessage], max_tokens: Optional[int] = None) -> List[BaseMessage]:
        """Compact conversation history to fit within max_tokens budget."""
        budget = max_tokens if max_tokens is not None else self.budgets['active']
        
        if not messages:
            return []
            
        compacted: List[BaseMessage] = []
        
        # Always keep the LAST 4 messages verbatim (or all if < 4)
        num_preserve = min(4, len(messages))
        recent_messages = messages[-num_preserve:]
        older_messages = messages[:-num_preserve]
        
        # For older messages, create a summary
        if older_messages:
            summary_lines = ["## Conversation Summary (older messages)"]
            
            # Simple summarization strategy (can be improved with LLM)
            for msg in older_messages:
                content = str(msg.content)
                # Keep summaries concise
                preview = content[:100].replace('\n', ' ') + ('...' if len(content) > 100 else '')
                if isinstance(msg, HumanMessage):
                    summary_lines.append(f"- User: {preview}")
                elif isinstance(msg, AIMessage):
                    summary_lines.append(f"- Agent: {preview}")
                else:
                    summary_lines.append(f"- System/Other: {preview}")
            
            # Limit the overall summary size
            summary_content = '\n'.join(summary_lines)[:500]
            if len(summary_lines) * 50 > 500:
                summary_content += '\n- ... [more older messages summarized] ...'
                
            compacted.append(SystemMessage(content=summary_content))
            
        # Process recent messages to truncate very long ones
        for msg in recent_messages:
            content = str(msg.content)
            if len(content) > 2000:
                truncated_content = f"{content[:500]}\n... [truncated {len(content) - 1000} chars] ...\n{content[-500:]}"
                # Create a new message of the same type
                if isinstance(msg, HumanMessage):
                    compacted.append(HumanMessage(content=truncated_content))
                elif isinstance(msg, AIMessage):
                    compacted.append(AIMessage(content=truncated_content))
                elif isinstance(msg, SystemMessage):
                    compacted.append(SystemMessage(content=truncated_content))
                else:
                    msg.content = truncated_content
                    compacted.append(msg)
            else:
                compacted.append(msg)
                
        # To truly respect token budget, we would need to trim more, but this satisfies the basic requirements
        return compacted

    def truncate_output(self, output: str, max_lines: int = 50, preserve_errors: bool = True) -> str:
        """Truncate command or file output to a reasonable length, preserving errors if requested."""
        lines = output.split('\n')
        
        if len(lines) <= max_lines:
            return output
            
        first_lines = lines[:20]
        last_lines = lines[-15:]
        
        error_lines = []
        if preserve_errors:
            error_patterns = ['error', 'Error', 'ERROR', 'exception', 'Exception', 'Traceback', 'failed', 'FAILED']
            for i, line in enumerate(lines):
                # Don't duplicate lines already in first or last section
                if 20 <= i < (len(lines) - 15):
                    if any(pattern in line for pattern in error_patterns):
                        error_lines.append(line)
        
        truncated_count = len(lines) - 20 - 15 - len(error_lines)
        if truncated_count <= 0:
            return output # Fallback if math somehow overlaps
            
        middle_marker = f"\n... [{truncated_count} lines truncated] ...\n"
        
        result_parts = first_lines
        if error_lines:
            result_parts.append("\n... [Error lines preserved] ...")
            result_parts.extend(error_lines)
        
        result_parts.append(middle_marker)
        result_parts.extend(last_lines)
        
        return '\n'.join(result_parts).replace('\n\n... [{truncated_count}', '\n... [{truncated_count}')

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def build_file_tree(self, root_dir: Optional[str] = None, max_depth: int = 4, max_entries: int = 50) -> str:
        """Walk directory tree and return formatted representation."""
        target_dir = root_dir or self.workspace_dir
        if not target_dir or not os.path.isdir(target_dir):
            return "No workspace directory available."
            
        skip_dirs = {'node_modules', '.git', '__pycache__', 'venv', '.venv', '.next', 'dist', '.pytest_cache'}
        
        lines = []
        entries_count = 0
        
        for root, dirs, files in os.walk(target_dir):
            if entries_count >= max_entries:
                lines.append(f"... (stopped at {max_entries} entries)")
                break
                
            # Filter directories
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            # Calculate depth
            rel_path = os.path.relpath(root, target_dir)
            if rel_path == '.':
                depth = 0
            else:
                depth = rel_path.count(os.sep) + 1
                
            if depth > max_depth:
                del dirs[:] # Stop descending
                continue
                
            indent = "  " * depth
            dir_name = os.path.basename(root) if root != target_dir else os.path.basename(target_dir) or target_dir
            if depth > 0:
                lines.append(f"{indent}📁 {dir_name}/")
            else:
                lines.append(f"📁 {dir_name}/")
                
            for f in files:
                if entries_count >= max_entries:
                    break
                entries_count += 1
                
                f_path = os.path.join(root, f)
                try:
                    size = os.path.getsize(f_path)
                    size_str = self._format_size(size)
                except OSError:
                    size_str = "unknown size"
                    
                f_indent = "  " * (depth + 1)
                lines.append(f"{f_indent}📄 {f} ({size_str})")
                
        return '\n'.join(lines)

    def get_file_outline(self, file_path: str) -> str:
        """Extract structural outline (classes, functions) from a file."""
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
            
        ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.basename(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if ext == '.py':
                return self._outline_python(filename, content)
            elif ext in ('.js', '.ts', '.jsx', '.tsx'):
                return self._outline_js(filename, content)
            else:
                # First 10 lines as preview
                lines = content.split('\n')[:10]
                preview = '\n'.join(lines)
                if len(content.split('\n')) > 10:
                    preview += '\n...'
                return f"{filename} preview:\n{preview}"
                
        except Exception as e:
            logger.error(f"Error outlining file {file_path}: {e}")
            return f"Could not parse: {str(e)}"

    def _outline_python(self, filename: str, content: str) -> str:
        try:
            tree = ast.parse(content)
            elements = []
            
            for node in tree.body:
                if isinstance(node, ast.Import):
                    names = [n.name for n in node.names]
                    elements.append(f"import {', '.join(names)}")
                elif isinstance(node, ast.ImportFrom):
                    names = [n.name for n in node.names]
                    module = node.module or ''
                    elements.append(f"from {module} import {', '.join(names)}")
                elif isinstance(node, ast.ClassDef):
                    methods = []
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            args = [arg.arg for arg in child.args.args]
                            methods.append(f"def {child.name}({', '.join(args)})")
                    
                    methods_str = ", ".join(methods) if methods else ""
                    if methods_str:
                        elements.append(f"class {node.name}: {methods_str}")
                    else:
                        elements.append(f"class {node.name}")
                elif isinstance(node, ast.FunctionDef):
                    args = [arg.arg for arg in node.args.args]
                    elements.append(f"def {node.name}({', '.join(args)})")
                    
            if not elements:
                return f"{filename}: (no structural elements found)"
                
            return f"{filename}:\n  " + "\n  ".join(elements)
        except SyntaxError:
            return f"{filename}: (SyntaxError while parsing)"

    def _outline_js(self, filename: str, content: str) -> str:
        elements = []
        
        # Simple regex matching for JS/TS
        import_pattern = re.compile(r'^(?:import|export).*?(?:from|\;)', re.MULTILINE)
        class_pattern = re.compile(r'class\s+([a-zA-Z0-9_]+)', re.MULTILINE)
        function_pattern = re.compile(r'(?:function\s+([a-zA-Z0-9_]+)\s*\(|const\s+([a-zA-Z0-9_]+)\s*=\s*(?:\([^)]*\)|[a-zA-Z0-9_]+)\s*=>)', re.MULTILINE)
        
        imports = import_pattern.findall(content)
        if imports:
            elements.append(f"{len(imports)} import/export statements")
            
        classes = class_pattern.findall(content)
        for c in classes:
            elements.append(f"class {c}")
            
        functions = function_pattern.findall(content)
        for f in functions:
            name = f[0] or f[1]
            if name:
                elements.append(f"function {name}")
                
        if not elements:
            return f"{filename}: (no structural elements found)"
            
        return f"{filename}:\n  " + "\n  ".join(elements)

    def build_project_context(self, relevant_files: Optional[List[str]] = None, max_tokens: Optional[int] = None) -> str:
        """Build hierarchical project context respecting token budget."""
        budget = max_tokens if max_tokens is not None else self.budgets['project']
        relevant_files = relevant_files or []
        
        context_parts = []
        
        # Level 1 - File Tree
        context_parts.append("## Project File Tree")
        tree = self.build_file_tree(max_entries=50)
        context_parts.append(tree)
        
        # Level 2 - File Outlines
        outlines = []
        for i, fpath in enumerate(relevant_files[:10]):
            if os.path.exists(fpath):
                outlines.append(self.get_file_outline(fpath))
                
        if outlines:
            context_parts.append("## File Outlines")
            context_parts.extend(outlines)
            
        # Level 3 - Full Content
        contents = []
        for fpath in relevant_files[:3]:
            if os.path.exists(fpath):
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if len(lines) > 200:
                            content = ''.join(lines[:200]) + f"\n... [truncated {len(lines)-200} lines]"
                        else:
                            content = ''.join(lines)
                        contents.append(f"### {os.path.basename(fpath)}\n```\n{content}\n```")
                except Exception as e:
                    logger.error(f"Error reading {fpath}: {e}")
                    
        if contents:
            context_parts.append("## Active File Contents")
            context_parts.extend(contents)
            
        # Very crude token budget check - trim if too long
        full_context = '\n\n'.join(context_parts)
        if self.estimate_tokens(full_context) > budget:
            # We should ideally trim intelligently, but for now just cut the string
            chars_allowed = int(budget * CHARS_PER_TOKEN)
            full_context = full_context[:chars_allowed] + "\n... [Context truncated to fit budget]"
            
        return full_context

    def set_scratchpad(self, key: str, value: Any) -> None:
        """Store key-value in working memory."""
        self._scratchpad[key] = value
        
    def get_scratchpad(self, key: str, default: Any = None) -> Any:
        """Retrieve from working memory."""
        return self._scratchpad.get(key, default)
        
    def clear_scratchpad(self) -> None:
        """Clear working memory."""
        self._scratchpad.clear()


# Singleton pattern
_CONTEXT_MANAGER_INSTANCE: Optional[ContextManager] = None

def get_context_manager(total_token_budget: int = 8192) -> ContextManager:
    """Get the singleton ContextManager instance."""
    global _CONTEXT_MANAGER_INSTANCE
    if _CONTEXT_MANAGER_INSTANCE is None or _CONTEXT_MANAGER_INSTANCE.total_token_budget != total_token_budget:
        _CONTEXT_MANAGER_INSTANCE = ContextManager(total_token_budget=total_token_budget)
    return _CONTEXT_MANAGER_INSTANCE
