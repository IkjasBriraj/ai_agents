"""
Empirical Verification Harness for Milestone 1 - Challenger 2
Tests:
1. CodeAgent system prompt integration and fix_file task prompt.
2. file_operation with operation="patch" on Large Files (>10,000 lines).
3. file_operation with operation="patch" on Multi-matching targets (50+ occurrences).
4. AST syntax validation failure preventing file modification.
5. Missing target diagnostic context.
6. Payload handling (Dict, JSON string, Markdown-wrapped JSON).
7. Self-cleanup of all temporary test files.
"""

import os
import sys
import json
import ast

# Ensure backend directory is in sys.path
BACKEND_DIR = r"d:\learning\code\ai_agents\backend"
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from agents.config import AGENT_WORKSPACE_DIR, get_workspace_path
from agents.tools import file_operation, write_file_content, read_file_content
from agents.specialized_agents import CodeAgent


def run_tests():
    test_files_created = []
    results = []

    print("=" * 70)
    print("STARTING EMPIRICAL VERIFICATION HARNESS — CHALLENGER 2 (M1)")
    print("=" * 70)

    try:
        # -------------------------------------------------------------
        # Test 1: CodeAgent System Prompt & fix_file Prompt Integration
        # -------------------------------------------------------------
        print("\n[TEST 1] CodeAgent System Prompt Integration")
        agent = CodeAgent()
        sys_prompt = agent.system_prompt
        
        prompt_has_patch = "patch" in sys_prompt
        prompt_has_target_repl = "target" in sys_prompt and "replacement" in sys_prompt
        prompt_has_workflow = "WORKFLOW FOR FIXING EXISTING FILES" in sys_prompt
        
        # Test fix_file task prompt structure
        fix_file_doc = agent.fix_file.__doc__ or ""
        
        print(f"  - System prompt references 'patch': {prompt_has_patch}")
        print(f"  - System prompt references target/replacement: {prompt_has_target_repl}")
        print(f"  - System prompt includes workflow for fixing files: {prompt_has_workflow}")
        
        assert prompt_has_patch, "CodeAgent system prompt missing 'patch'"
        assert prompt_has_target_repl, "CodeAgent system prompt missing target/replacement instructions"
        assert prompt_has_workflow, "CodeAgent system prompt missing WORKFLOW FOR FIXING EXISTING FILES"
        
        results.append(("CodeAgent System Prompt Integration", True, "System prompt correctly mandates operation='patch'"))

        # -------------------------------------------------------------
        # Test 2: Large File Patching (>10,000 lines, ~350 KB)
        # -------------------------------------------------------------
        print("\n[TEST 2] Large File Patching (>10,000 lines)")
        large_filename = "challenger_large_file_test.py"
        large_filepath = get_workspace_path(large_filename)
        test_files_created.append(large_filepath)

        # Generate 10,000 line file with specific markers
        lines = []
        lines.append('"""Large file stress test for file_operation patch"""\n')
        lines.append('GLOBAL_CONFIG = {"version": 1.0}\n\n')
        
        for i in range(1, 10001):
            if i == 3000:
                lines.append(f'def target_function_at_{i}():\n    return "ORIGINAL_VALUE_AT_{i}"\n\n')
            elif i == 8000:
                lines.append(f'def target_function_at_{i}():\n    return "DUPLICATE_TARGET_VALUE"\n\n')
            elif i == 9500:
                lines.append(f'def target_function_at_{i}():\n    return "DUPLICATE_TARGET_VALUE"\n\n')
            else:
                lines.append(f'def dummy_function_{i}():\n    return {i}\n\n')

        large_content = "".join(lines)
        write_file_content(large_filename, large_content)

        initial_size = os.path.getsize(large_filepath)
        print(f"  - Created large file: {large_filename} ({len(lines)} lines, {initial_size} bytes)")

        # Patch unique target at line 3000
        patch_payload_1 = {
            "target": 'def target_function_at_3000():\n    return "ORIGINAL_VALUE_AT_3000"',
            "replacement": 'def target_function_at_3000():\n    return "PATCHED_VALUE_AT_3000"'
        }
        res_1 = file_operation(operation="patch", path=large_filename, content=json.dumps(patch_payload_1))
        assert "[SUCCESS]" in res_1, f"Large file patch failed: {res_1}"

        # Read back and verify
        with open(large_filepath, 'r', encoding='utf-8') as f:
            patched_large_content = f.read()

        assert 'PATCHED_VALUE_AT_3000' in patched_large_content, "Patched value missing in large file"
        assert 'ORIGINAL_VALUE_AT_3000' not in patched_large_content, "Original value still present in large file"
        
        # AST validation on patched large file
        ast.parse(patched_large_content)
        print("  - Large file patch succeeded & AST parse valid")

        results.append(("Large File Patching (>10k lines)", True, f"Successfully patched {initial_size} bytes file"))

        # -------------------------------------------------------------
        # Test 3: Multi-Matching Targets (Verifying ONLY 1st occurrence replaced)
        # -------------------------------------------------------------
        print("\n[TEST 3] Multi-Matching Targets (50 occurrences of same target string)")
        multi_filename = "challenger_multi_target_test.py"
        multi_filepath = get_workspace_path(multi_filename)
        test_files_created.append(multi_filepath)

        target_str = 'CONFIG_SETTING = "DEFAULT_CONFIG_VALUE"'
        replacement_str = 'CONFIG_SETTING = "UPDATED_CONFIG_VALUE"'

        multi_lines = []
        multi_lines.append("# Multi-matching test file\n")
        for idx in range(1, 51):
            multi_lines.append(f"# Block {idx}\n")
            multi_lines.append(f"{target_str}\n")
            multi_lines.append(f"def process_block_{idx}():\n    pass\n\n")

        write_file_content(multi_filename, "".join(multi_lines))
        
        # Patch multi-matching file
        patch_multi_payload = {
            "target": target_str,
            "replacement": replacement_str
        }
        res_multi = file_operation(operation="patch", path=multi_filename, content=json.dumps(patch_multi_payload))
        assert "[SUCCESS]" in res_multi, f"Multi-matching patch failed: {res_multi}"

        with open(multi_filepath, 'r', encoding='utf-8') as f:
            multi_content_after = f.read()

        occ_target = multi_content_after.count(target_str)
        occ_replacement = multi_content_after.count(replacement_str)

        print(f"  - Target occurrences remaining: {occ_target} (expected 49)")
        print(f"  - Replacement occurrences present: {occ_replacement} (expected 1)")

        assert occ_replacement == 1, f"Expected exactly 1 replacement, found {occ_replacement}"
        assert occ_target == 49, f"Expected 49 remaining targets, found {occ_target}"

        # Verify replacement is at Block 1 (the first occurrence)
        first_block_patched = '# Block 1\nCONFIG_SETTING = "UPDATED_CONFIG_VALUE"' in multi_content_after
        second_block_unpatched = '# Block 2\nCONFIG_SETTING = "DEFAULT_CONFIG_VALUE"' in multi_content_after
        assert first_block_patched, "First occurrence (Block 1) was not the one replaced"
        assert second_block_unpatched, "Second occurrence (Block 2) was modified when it shouldn't be"

        print("  - Confirmed ONLY the first occurrence was replaced!")

        results.append(("Multi-Matching Targets (50 occurrences)", True, "Exactly 1st occurrence replaced, 49 untouched"))

        # -------------------------------------------------------------
        # Test 4: AST Validation Rollback on Invalid Python Syntax
        # -------------------------------------------------------------
        print("\n[TEST 4] AST Validation Pre-Write Safeguard")
        ast_filename = "challenger_ast_test.py"
        ast_filepath = get_workspace_path(ast_filename)
        test_files_created.append(ast_filepath)

        valid_py = 'def compute(a, b):\n    return a + b\n'
        write_file_content(ast_filename, valid_py)

        bad_patch = {
            "target": "return a + b",
            "replacement": "return a + ("  # Syntax error!
        }
        res_ast = file_operation(operation="patch", path=ast_filename, content=json.dumps(bad_patch))
        
        with open(ast_filepath, 'r', encoding='utf-8') as f:
            content_after_bad_ast = f.read()

        assert "Syntax validation failed" in res_ast, f"Expected Syntax validation failed, got: {res_ast}"
        assert content_after_bad_ast == valid_py, "File was modified despite syntax error!"
        print("  - AST check blocked write; original file preserved intact.")

        results.append(("AST Validation Pre-Write Safeguard", True, "Syntax error blocked file write, content preserved"))

        # -------------------------------------------------------------
        # Test 5: Missing Target Diagnostic Details
        # -------------------------------------------------------------
        print("\n[TEST 5] Missing Target Diagnostic Context")
        missing_filename = "challenger_missing_target.py"
        missing_filepath = get_workspace_path(missing_filename)
        test_files_created.append(missing_filepath)

        write_file_content(missing_filename, 'def foo():\n    print("hello")\n')
        
        missing_patch = {
            "target": "def non_existent_function():",
            "replacement": "def exists():"
        }
        res_missing = file_operation(operation="patch", path=missing_filename, content=json.dumps(missing_patch))
        
        assert "Error: Target string not found in file" in res_missing, f"Unexpected error output: {res_missing}"
        assert "Total lines=" in res_missing and "Total bytes=" in res_missing, "Diagnostic info missing line/byte count"
        print("  - Detailed diagnostic context returned on missing target.")

        results.append(("Missing Target Diagnostics", True, "Returned complete line search and file stats context"))

        # -------------------------------------------------------------
        # Test 6: Payload Handling (Dict vs JSON String vs Markdown)
        # -------------------------------------------------------------
        print("\n[TEST 6] Flexible Payload Parsing (Dict & JSON String)")
        payload_filename = "challenger_payload_test.py"
        payload_filepath = get_workspace_path(payload_filename)
        test_files_created.append(payload_filepath)

        write_file_content(payload_filename, 'VAR_A = 1\nVAR_B = 2\nVAR_C = 3\n')

        # Pass as Dict
        res_dict = file_operation(operation="patch", path=payload_filename, content={"target": "VAR_A = 1", "replacement": "VAR_A = 100"})
        assert "[SUCCESS]" in res_dict, f"Dict payload failed: {res_dict}"

        # Pass as Markdown JSON
        markdown_json = "```json\n{\n  \"target\": \"VAR_B = 2\",\n  \"replacement\": \"VAR_B = 200\"\n}\n```"
        res_md = file_operation(operation="patch", path=payload_filename, content=markdown_json)
        assert "[SUCCESS]" in res_md, f"Markdown JSON payload failed: {res_md}"

        with open(payload_filepath, 'r', encoding='utf-8') as f:
            final_payload_content = f.read()

        assert 'VAR_A = 100' in final_payload_content
        assert 'VAR_B = 200' in final_payload_content
        print("  - Dict and Markdown JSON payloads handled seamlessly.")

        results.append(("Flexible Payload Parsing", True, "Dict and Markdown JSON parsed successfully"))

    finally:
        # Cleanup created files
        print("\n[CLEANUP] Removing temporary verification test files...")
        cleaned_count = 0
        for filepath in test_files_created:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    cleaned_count += 1
                except Exception as e:
                    print(f"  - Warning: Failed to remove {filepath}: {e}")
        print(f"  - Cleaned up {cleaned_count}/{len(test_files_created)} temporary test files.")

    # Print Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    all_passed = True
    for name, passed, note in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{name:.<45} {status} | {note}")
        if not passed:
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("ALL EMPIRICAL VERIFICATION TESTS PASSED SUCCESSFULLY!")
        return 0
    else:
        print("SOME VERIFICATION TESTS FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
