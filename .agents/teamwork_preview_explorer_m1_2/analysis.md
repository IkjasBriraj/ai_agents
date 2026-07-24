# Analysis Report: Incremental Code Modifiers & AST Validation (Milestone 1)

## Executive Summary
This analysis details the architectural design and exact code modifications required for Milestone 1 (R1). The objective is to expand `backend/agents/tools.py` to support surgical code modification via `operation: "patch"` in `file_operation`, integrate Python AST validation (`ast.parse`) prior to disk writes, and update `CodeAgent` system prompts in `backend/agents/specialized_agents.py` to prioritize localized patch operations over full file rewrites.

---

## 1. Codebase Baseline & Audit

### 1.1 `backend/agents/tools.py`
- **Location**: `backend/agents/tools.py` (1003 lines)
- **Existing `file_operation`**:
  - Defined at line 517: `file_operation(operation: str, path: str, content: str = "") -> str`
  - Current operations supported: `read` (calls `read_file_content`), `write` (calls `write_file_content`), `list` (calls `list_directory`).
  - Returns `Error: Unknown operation...` for unsupported operation strings.
- **Existing Validation in `write_file_content`**:
  - Defined at lines 383–442.
  - Extension check `.py` at line 402 runs `ast.parse(content)`.
  - Extension check `.json` at line 408 runs `json.loads(content)`.
  - Extension check `.js`/`.ts`/`.html`/`.jsx`/`.tsx` at line 414 performs bracket matching.
- **Tool Registrations**:
  - `get_code_agent_tools()` at line 830 registers `file_operation` with `StructuredTool.from_function(...)`.
  - Description lists operations `'read', 'write', 'list'`.

### 1.2 `backend/agents/specialized_agents.py`
- **Location**: `backend/agents/specialized_agents.py` (734 lines)
- **Existing `CodeAgent` Prompt**:
  - Defined at lines 408–483.
  - Rule 2 under CRITICAL RULES mandates: *"When asked to fix or update a file, FIRST read it with operation 'read', then write the corrected version with operation 'write'."*
  - `WORKFLOW FOR FIXING EXISTING FILES` (lines 469–474) explicitly directs: *"Step 3: Generate the COMPLETE corrected code (not just the changed parts)"* and *"Step 4: CALL file_operation with operation 'write' to overwrite the file with the fixed version"*.
- **Existing `CodeAgent.fix_file` Method**:
  - Defined at lines 515–538.
  - Prompt instructs: *"Write the COMPLETE corrected file back using: Action: file_operation with {"operation": "write", "path": "...", "content": "...fixed code..."}"*.

---

## 2. Component 1: AST Validation & `file_operation` Patch Integration

### 2.1 Design of `patch_file_content` Helper Function
A new helper function `patch_file_content(path: str, content: str)` will be added to `backend/agents/tools.py`.

#### Step-by-Step Logic Flow:
1. **JSON Payload Parsing**:
   - `content` can be delivered as a dict or a JSON string (due to LLM formatting variability or `safe_parse_input`).
   - Extract `target` (string to be replaced) and `replacement` (new string).
   - If `content` is a string, attempt `json.loads(content)`. If parsing fails, fall back to `extract_first_json(content)`.
   - If `target` is `None` or `replacement` is `None` or `target == ""`, return clear error:
     `"Error: 'patch' operation content must be a JSON string or dict containing non-empty 'target' and 'replacement' keys."`

2. **Path Resolution & Security Sandbox Checks**:
   - Normalize path to absolute workspace path via `get_workspace_path(path)`.
   - Execute permission check via `check_and_request_permission(path)`.
   - Check allowed extensions via `is_allowed_extension(path)`.
   - Verify file existence: If file does not exist, return `"Error: File not found: {path}"`.

3. **Target Match Verification & Error Context**:
   - Read current disk file content: `open(path, 'r', encoding='utf-8')`.
   - Check if `target` string is present in `existing_content`.
   - If `target` is missing, return detailed error string detailing line matching attempt:
     `f"Error: Target string not found in {path}. Target: {repr(target)}. Verify exact line text before patching."`

4. **Surgical Substitution**:
   - Perform exact string replacement of the **first occurrence** only:
     `updated_content = existing_content.replace(target, replacement, 1)`

5. **AST & Syntax Validation (Pre-disk Write Guard)**:
   - Check extension: `ext = os.path.splitext(path)[1].lower()`.
   - If `ext == '.py'`:
     ```python
     try:
         import ast
         ast.parse(updated_content)
     except SyntaxError as e:
         return f"Error: Syntax validation failed for Python file: {e}"
     ```
   - **Crucial Atomic Property**: `ast.parse` is executed **before** any `open(path, 'w')` call occurs. If `ast.parse` raises `SyntaxError`, the exception handler catches it and returns the error string immediately. The target file on disk remains completely untouched and unmodified.

6. **Disk Persistence & Return**:
   - If AST validation succeeds, write `updated_content` to `path`.
   - Return status string: `f"[SUCCESS] Patched: {rel_path}\n  Full path: {abs_path}\n  Size: {len(updated_content)} bytes"`.

### 2.2 Integration into `file_operation` Dispatcher
In `backend/agents/tools.py`:
```python
def file_operation(operation: str, path: str, content: str = "") -> str:
    """Perform file operations in workspace"""
    if operation == "read":
        return read_file_content(path)
    elif operation == "write":
        return write_file_content(path, content)
    elif operation == "patch":
        return patch_file_content(path, content)
    elif operation == "list":
        return list_directory(path)
    else:
        return f"Error: Unknown operation: {operation}. Use 'read', 'write', 'patch', or 'list'"
```

Also update the tool description in `get_code_agent_tools()` at line 830:
```python
description=f"Perform file operations in workspace ({AGENT_WORKSPACE_DIR}). Operations: 'read', 'write', 'patch', 'list'. For 'patch', content should be JSON string or dict with 'target' and 'replacement'. Input should be a dict with 'operation', 'path', and optional 'content' keys."
```

---

## 3. Component 2: `CodeAgent` System Prompt & Method Updates

### 3.1 Prompt Updates in `backend/agents/specialized_agents.py`

#### 1. CRITICAL RULES Section (Rule 2):
- **Original**:
  `2. When asked to fix or update a file, FIRST read it with operation "read", then write the corrected version with operation "write".`
- **Proposed Update**:
  `2. When asked to modify, fix, or update an existing file, FIRST read it with operation "read", then use operation "patch" with target and replacement JSON content for surgical updates instead of full file rewrites. Use operation "write" primarily for creating new files.`

#### 2. Tools YOU MUST USE Section (Tool 1):
- **Original**:
  `1. file_operation - READ, WRITE, or LIST files`
- **Proposed Update**:
  ```
  1. file_operation - READ, WRITE, PATCH, or LIST files
     To READ a file:  {"operation": "read", "path": "filename.py"}
     To WRITE a file: {"operation": "write", "path": "filename.py", "content": "file content here"}
     To PATCH a file: {"operation": "patch", "path": "filename.py", "content": "{\"target\": \"exact old code\", \"replacement\": \"new code\"}"}
     To LIST files:   {"operation": "list", "path": ""}
  ```

#### 3. WORKFLOW FOR FIXING EXISTING FILES Section:
- **Original**:
  ```
  WORKFLOW FOR FIXING EXISTING FILES:
  Step 1: CALL file_operation with operation "read" to read the existing file
  Step 2: Analyze the code and identify the errors/issues
  Step 3: Generate the COMPLETE corrected code (not just the changed parts)
  Step 4: CALL file_operation with operation "write" to overwrite the file with the fixed version
  Step 5: Confirm the fix was applied
  ```
- **Proposed Update**:
  ```
  WORKFLOW FOR FIXING / MODIFYING EXISTING FILES:
  Step 1: CALL file_operation with operation "read" to read the existing file
  Step 2: Identify the exact code block to modify and design the minimal target and replacement strings
  Step 3: CALL file_operation with operation "patch" supplying content JSON string {"target": "...", "replacement": "..."}
  Step 4: If patch fails (e.g. target string not found), re-verify target text against file reading and try again
  Step 5: Confirm the fix was applied successfully
  ```

#### 4. `CodeAgent.fix_file` Method Update (lines 515–538):
- **Proposed Step 3 Instruction**:
  `3. Write the patch using: Action: file_operation with {"operation": "patch", "path": "{filepath}", "content": "{\"target\": \"...old code...\", \"replacement\": \"...new code...\"}"}`

---

## 4. Proposed Code Diffs

### Diff 1: `backend/agents/tools.py`
```diff
--- a/backend/agents/tools.py
+++ b/backend/agents/tools.py
@@ -442,6 +442,65 @@ def write_file_content(path: str, content: str) -> str:
     except Exception as e:
         return f"Error writing file: {str(e)}"
 
+
+def patch_file_content(path: str, content: Any) -> str:
+    """Patch file content by replacing exact target string with replacement string"""
+    try:
+        target = None
+        replacement = None
+        
+        if isinstance(content, dict):
+            target = content.get("target")
+            replacement = content.get("replacement")
+        elif isinstance(content, str):
+            try:
+                parsed = json.loads(content)
+                if isinstance(parsed, dict):
+                    target = parsed.get("target")
+                    replacement = parsed.get("replacement")
+            except Exception:
+                try:
+                    cleaned = extract_first_json(content)
+                    parsed = json.loads(cleaned)
+                    if isinstance(parsed, dict):
+                        target = parsed.get("target")
+                        replacement = parsed.get("replacement")
+                except Exception:
+                    pass
+                    
+        if target is None or replacement is None or not isinstance(target, str) or not target:
+            return "Error: 'patch' operation content must be a JSON string or dict containing non-empty 'target' and 'replacement' keys."
+            
+        if not os.path.isabs(path) or path.startswith('/') or path.startswith('\\'):
+            rel_path = path.lstrip('/\\')
+            path = get_workspace_path(rel_path)
+            
+        if not check_and_request_permission(path):
+            return f"Error: Access denied. Path must be whitelisted: {path}"
+            
+        if not is_allowed_extension(path):
+            return f"Error: File extension not allowed. File: {path}"
+            
+        if not os.path.exists(path):
+            return f"Error: File not found: {path}"
+            
+        with open(path, 'r', encoding='utf-8') as f:
+            existing_content = f.read()
+            
+        if target not in existing_content:
+            return f"Error: Target string not found in file: {path}. Target: {repr(target)}"
+            
+        updated_content = existing_content.replace(target, replacement, 1)
+        
+        ext = os.path.splitext(path)[1].lower()
+        if ext == '.py':
+            try:
+                import ast
+                ast.parse(updated_content)
+            except SyntaxError as e:
+                return f"Error: Syntax validation failed for Python file: {e}"
+        elif ext == '.json':
+            try:
+                json.loads(updated_content)
+            except json.JSONDecodeError as e:
+                return f"Error: Syntax validation failed for JSON file: {e}"
+                
+        with open(path, 'w', encoding='utf-8') as f:
+            f.write(updated_content)
+            
+        rel_path = os.path.relpath(path, AGENT_WORKSPACE_DIR)
+        abs_path = os.path.abspath(path)
+        return f"[SUCCESS] Patched: {rel_path}\n  Full path: {abs_path}\n  Size: {len(updated_content)} bytes"
+    except Exception as e:
+        return f"Error patching file: {str(e)}"
+
 
 def list_directory(path: str = "") -> str:
     ...
@@ -522,8 +581,10 @@ def file_operation(operation: str, path: str, content: str = "") -> str:
         return read_file_content(path)
     elif operation == "write":
         return write_file_content(path, content)
+    elif operation == "patch":
+        return patch_file_content(path, content)
     elif operation == "list":
         return list_directory(path)
     else:
-        return f"Error: Unknown operation: {operation}. Use 'read', 'write', or 'list'"
+        return f"Error: Unknown operation: {operation}. Use 'read', 'write', 'patch', or 'list'"
```

---

## 5. Verification Plan

### Test Scenarios:
1. **Valid Patch Operation**:
   - Create a test file `test_sample.py` with `def hello():\n    pass`.
   - Call `file_operation("patch", "test_sample.py", '{"target": "def hello():\\n    pass", "replacement": "def hello():\\n    print(\\"patched\\")"}')`.
   - Verify return message contains `[SUCCESS] Patched`. Read file to confirm replacement.

2. **Invalid Syntax Safeguard Verification**:
   - Call `file_operation("patch", "test_sample.py", '{"target": "print(\\"patched\\")", "replacement": "def invalid_syntax(:"}')`.
   - Verify return message starts with `Error: Syntax validation failed for Python file`.
   - Re-read `test_sample.py` and confirm file content remains unchanged (`print("patched")`).

3. **Missing Target Error Handling**:
   - Call `file_operation("patch", "test_sample.py", '{"target": "non_existent_function()", "replacement": "foo()"}')`.
   - Verify return message contains `Error: Target string not found in file`.

4. **Malformed JSON Payload**:
   - Call `file_operation("patch", "test_sample.py", 'invalid json')`.
   - Verify error message indicates missing target and replacement keys.

---

## 6. Risk Assessment & Mitigations

| Risk | Impact | Mitigation Strategy |
|---|---|---|
| Large file patch collision (multiple identical target strings) | Replaces wrong block | `replace(target, replacement, 1)` replaces only first match; system prompt instructs providing sufficient surrounding context in `target`. |
| LLM escapes in JSON strings | JSON parse failure | Multi-stage JSON parsing (`json.loads`, `extract_first_json`, and fallback dict checks). |
| File write during partial syntax error | Corrupted Python file | AST validation (`ast.parse`) executes BEFORE opening file handle for write (`'w'`). |

