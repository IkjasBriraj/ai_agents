# Technical Analysis: Expanding `file_operation` to Support `operation: "patch"`

## Executive Summary
This analysis details the architectural design and exact code modifications required in `backend/agents/tools.py` to add `operation: "patch"` support to `file_operation`. The patch operation enables surgical, exact-string substitution of target code blocks without requiring complete file rewrites, incorporating pre-write AST validation for Python files and diagnostic line search error reporting when target strings are not found.

---

## 1. Codebase Exploration & Line Range Mapping

### Target File: `backend/agents/tools.py`

| Component / Function | Line Range | Current Behavior | Required Modification |
|----------------------|------------|------------------|-----------------------|
| `FileOperationInput` | 59–63 | Pydantic schema listing `read`, `write`, `list`. | Update `operation` description to include `"patch"`; update `content` description for patch payload schema (`{"target": "...", "replacement": "..."}`). |
| `write_file_content` | 383–442 | Handles full file write with permission check, path resolution, size check, allowed extension check, and syntax validation. | Serves as structural blueprint for `patch_file_content`. |
| `patch_file_content` | New (~443) | Does not exist. | Create helper function implementing patch logic, JSON parsing, target substitution, diagnostic line search on failure, and Python `ast.parse` validation. |
| `file_operation` | 517–527 | Dispatches `"read"`, `"write"`, `"list"`. | Add `elif operation == "patch": return patch_file_content(path, content)`. |
| `get_code_agent_tools` | 829–837 | `StructuredTool` description lists `'read', 'write', 'list'`. | Update description string to include `'patch'`. |
| `get_analysis_agent_tools` | 897–905 | `StructuredTool` description lists `'read', 'write'`. | Update description string to include `'patch'`. |

---

## 2. Detailed Implementation Strategy for `operation == "patch"`

### 2.1 Content Payload Parsing
- Input: `content` argument passed to `file_operation`.
- Expected structure: JSON string encoding an object with `target` and `replacement` string keys. Example:
  ```json
  {"target": "def old_func():\n    pass", "replacement": "def old_func():\n    print(\"updated\")"}
  ```
- Robust Parsing Steps:
  1. If `isinstance(content, dict)`, use directly.
  2. If `isinstance(content, str)`, attempt `json.loads(content)`.
  3. On JSON parsing error, fallback to `json.loads(extract_first_json(content))`.
  4. Validate that `patch_data` is a dictionary containing string non-empty `"target"` and string `"replacement"`.
  5. Return descriptive error if JSON parsing or field validation fails.

### 2.2 Path Safety & Permission Checks
Consistent with `write_file_content` and `read_file_content`:
1. Resolve path relative to workspace if relative or root-relative: `get_workspace_path(rel_path)`.
2. Interactive permission check: `check_and_request_permission(path)`.
3. Existence check: `os.path.exists(path)`. Fails if file does not exist.
4. Allowed extension check: `is_allowed_extension(path)`.
5. Max file size check: `os.path.getsize(path) <= MAX_FILE_SIZE`.

### 2.3 Exact String Substitution Logic
1. Read existing file content: `with open(path, 'r', encoding='utf-8') as f: original_content = f.read()`.
2. Perform exact string search: `if target not in original_content:` -> trigger diagnostic error handling (Section 2.4).
3. Substitute the **first occurrence only**:
   ```python
   new_content = original_content.replace(target, replacement, 1)
   ```

### 2.4 Missing Target Diagnostic Line Search
When `target not in original_content`, construct a detailed diagnostic error detailing line numbers and line search results:
- Extract `file_lines = original_content.splitlines()` and `target_lines = target.splitlines()`.
- Identify line matches for the first line of `target` (`target_lines[0].strip()`):
  - **Exact line matches**: File line numbers where `line.strip() == target_lines[0].strip()`.
  - **Partial line matches**: File line numbers where `target_lines[0].strip() in line`.
- Construct descriptive error message detailing:
  - Total line count in file and line count of target.
  - First target line string.
  - Line numbers where the first line matched (or partial matched) and state why the overall multi-line match failed (e.g., mismatch in subsequent lines).

### 2.5 Pre-Write Syntax Validation (`ast.parse`)
Before modifying the file on disk:
- Extract file extension: `ext = os.path.splitext(path)[1].lower()`.
- For `.py` files:
  ```python
  if ext == '.py':
      try:
          import ast
          ast.parse(new_content)
      except SyntaxError as e:
          return f"Error: Syntax validation failed for Python file: {e}"
  ```
- If AST parsing raises `SyntaxError`, return the syntax error message immediately. **Do NOT write to disk.**

---

## 3. Proposed Code Additions (Diff / Code Snippet)

### 3.1 `patch_file_content` Implementation Blueprint (`backend/agents/tools.py`)

```python
def patch_file_content(path: str, content: str) -> str:
    """Patch file content by replacing the first exact occurrence of target string with replacement"""
    try:
        print("Patch file content: ", path)
        # 1. Path resolution
        if not os.path.isabs(path) or path.startswith('/') or path.startswith('\\'):
            rel_path = path.lstrip('/\\')
            path = get_workspace_path(rel_path)

        # 2. Permission check
        if not check_and_request_permission(path):
            return f"Error: Access denied. Path must be whitelisted: {path}"

        # 3. File existence check
        if not os.path.exists(path):
            return f"Error: File not found: {path}"

        # 4. File extension check
        if not is_allowed_extension(path):
            return f"Error: File extension not allowed. File: {path}"

        # 5. File size check
        file_size = os.path.getsize(path)
        if file_size > MAX_FILE_SIZE:
            return f"Error: File too large ({file_size} bytes). Maximum size: {MAX_FILE_SIZE} bytes"

        # 6. Parse content JSON
        patch_data = None
        if isinstance(content, dict):
            patch_data = content
        elif isinstance(content, str):
            try:
                patch_data = json.loads(content)
            except Exception:
                try:
                    patch_data = json.loads(extract_first_json(content))
                except Exception:
                    pass

        if not isinstance(patch_data, dict) or "target" not in patch_data or "replacement" not in patch_data:
            return "Error: Invalid content payload for patch operation. Must be a JSON object containing 'target' and 'replacement' keys."

        target = patch_data["target"]
        replacement = patch_data["replacement"]

        if not isinstance(target, str) or not isinstance(replacement, str):
            return "Error: 'target' and 'replacement' must both be string values."

        if not target:
            return "Error: 'target' string cannot be empty for patch operation."

        # 7. Read existing file
        with open(path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # 8. Check target existence & build line details if missing
        if target not in original_content:
            file_lines = original_content.splitlines()
            target_lines = target.splitlines()
            total_file_lines = len(file_lines)
            total_target_lines = len(target_lines)

            first_target_line = target_lines[0].strip() if target_lines else ""

            exact_matches = [
                idx + 1 for idx, line in enumerate(file_lines)
                if first_target_line and first_target_line == line.strip()
            ]
            partial_matches = [
                idx + 1 for idx, line in enumerate(file_lines)
                if first_target_line and first_target_line in line and idx + 1 not in exact_matches
            ]

            diag = f"Error: Target string not found in file '{path}' (total lines: {total_file_lines}). Target length: {total_target_lines} line(s)."
            if exact_matches:
                diag += f" First target line '{first_target_line}' matched file line(s) {exact_matches}, but full consecutive block match failed."
            elif partial_matches:
                diag += f" First target line '{first_target_line}' partially matched file line(s) {partial_matches}, but exact block match failed."
            else:
                diag += f" First target line '{first_target_line}' was not found in any line of the file."

            return diag

        # 9. Perform exact string replacement (first occurrence only)
        new_content = original_content.replace(target, replacement, 1)

        # 10. Syntax validation (AST check for .py)
        ext = os.path.splitext(path)[1].lower()
        if ext == '.py':
            try:
                import ast
                ast.parse(new_content)
            except SyntaxError as e:
                return f"Error: Syntax validation failed for Python file: {e}"
        elif ext == '.json':
            try:
                json.loads(new_content)
            except json.JSONDecodeError as e:
                return f"Error: Syntax validation failed for JSON file: {e}"

        # 11. Write back patched content
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        rel_path = os.path.relpath(path, AGENT_WORKSPACE_DIR)
        abs_path = os.path.abspath(path)
        return f"[SUCCESS] Patched: {rel_path}\n  Full path: {abs_path}\n  Original size: {len(original_content)} bytes, New size: {len(new_content)} bytes"

    except Exception as e:
        return f"Error patching file: {str(e)}"
```

---

## 4. Edge Cases & Risk Assessment

1. **Escaped Newlines in JSON String**:
   - `safe_parse_input` in `tools.py` (lines 265-275) automatically unescapes string fields. In addition, Python's native `json.loads` handles standard JSON string escape sequences (`\n`, `\"`, `\t`).

2. **Multiple Target Occurrences**:
   - The requirement explicitly states to replace the first occurrence. Using `original_content.replace(target, replacement, 1)` guarantees only the first match is replaced.

3. **Empty File or Non-Existent File**:
   - Non-existent files return `Error: File not found: {path}` prior to reading.

4. **AST Validation Failure**:
   - If `ast.parse` fails, the function returns `Error: Syntax validation failed for Python file: <details>` BEFORE opening the file in write mode (`'w'`), protecting the disk copy from syntax corruption.

5. **Non-Python Files**:
   - AST validation is skipped for non-Python text files (e.g. `.txt`, `.md`, `.html`), while basic JSON syntax checks are applied if extension is `.json`.
