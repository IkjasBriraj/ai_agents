"""
Test File Operations in Workspace
Verify that agents can create, read, and write files
"""

import os
import sys
from agents.config import AGENT_WORKSPACE_DIR, get_workspace_path
from agents.tools import write_file_content, read_file_content, list_directory, create_project_structure, file_operation
from agents.specialized_agents import CodeAgent


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def test_workspace_setup():
    """Test workspace directory setup"""
    print_section("Testing Workspace Setup")
    
    print(f"Workspace Directory: {AGENT_WORKSPACE_DIR}")
    print(f"Exists: {os.path.exists(AGENT_WORKSPACE_DIR)}")
    print(f"Is Directory: {os.path.isdir(AGENT_WORKSPACE_DIR)}")
    print(f"Writable: {os.access(AGENT_WORKSPACE_DIR, os.W_OK)}")
    
    return os.path.exists(AGENT_WORKSPACE_DIR) and os.path.isdir(AGENT_WORKSPACE_DIR)


def test_write_file():
    """Test writing a file"""
    print_section("Testing File Write")
    
    test_content = """<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Hello from AI Agent!</h1>
    <p>This file was created by the Code Agent.</p>
</body>
</html>"""
    
    result = write_file_content("test.html", test_content)
    print(result)
    
    # Check if file exists
    file_path = get_workspace_path("test.html")
    if os.path.exists(file_path):
        print(f"\n[OK] File created successfully at: {file_path}")
        return True
    else:
        print(f"\n[FAIL] File was not created")
        return False


def test_read_file():
    """Test reading a file"""
    print_section("Testing File Read")
    
    result = read_file_content("test.html")
    print(result)
    
    return "Error" not in result


def test_list_directory():
    """Test listing directory"""
    print_section("Testing Directory Listing")
    
    result = list_directory("")
    print(result)
    
    return "Error" not in result


def test_create_project():
    """Test creating a complete project"""
    print_section("Testing Project Creation")
    
    project_structure = {
        "calculator/index.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple Calculator</title>
    <link rel="stylesheet" href="styles/main.css">
</head>
<body>
    <div class="calculator">
        <h1>Calculator</h1>
        <input type="text" id="display" readonly>
        <div class="buttons">
            <button onclick="appendNumber('7')">7</button>
            <button onclick="appendNumber('8')">8</button>
            <button onclick="appendNumber('9')">9</button>
            <button onclick="setOperation('+')">+</button>
        </div>
    </div>
    <script src="scripts/calculator.js"></script>
</body>
</html>""",
        
        "calculator/styles/main.css": """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.calculator {
    background: white;
    padding: 2rem;
    border-radius: 10px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

h1 {
    text-align: center;
    margin-bottom: 1rem;
    color: #333;
}

#display {
    width: 100%;
    padding: 1rem;
    font-size: 1.5rem;
    border: 2px solid #ddd;
    border-radius: 5px;
    margin-bottom: 1rem;
}

.buttons {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.5rem;
}

button {
    padding: 1rem;
    font-size: 1.2rem;
    border: none;
    background: #667eea;
    color: white;
    border-radius: 5px;
    cursor: pointer;
    transition: background 0.3s;
}

button:hover {
    background: #764ba2;
}""",
        
        "calculator/scripts/calculator.js": """let display = document.getElementById('display');
let currentValue = '';
let operation = null;
let previousValue = '';

function appendNumber(num) {
    currentValue += num;
    display.value = currentValue;
}

function setOperation(op) {
    if (currentValue === '') return;
    if (previousValue !== '') {
        calculate();
    }
    operation = op;
    previousValue = currentValue;
    currentValue = '';
}

function calculate() {
    let result;
    const prev = parseFloat(previousValue);
    const current = parseFloat(currentValue);
    
    if (isNaN(prev) || isNaN(current)) return;
    
    switch (operation) {
        case '+':
            result = prev + current;
            break;
        case '-':
            result = prev - current;
            break;
        case '*':
            result = prev * current;
            break;
        case '/':
            result = prev / current;
            break;
        default:
            return;
    }
    
    currentValue = result.toString();
    operation = null;
    previousValue = '';
    display.value = currentValue;
}

function clearDisplay() {
    currentValue = '';
    previousValue = '';
    operation = null;
    display.value = '';
}""",
        
        "calculator/README.md": """# Simple Calculator

A beautiful, responsive calculator web application.

## Features
- Basic arithmetic operations (+, -, *, /)
- Clean, modern UI
- Responsive design

## How to Use
1. Open `index.html` in your web browser
2. Click the number buttons to enter numbers
3. Click operation buttons to perform calculations

## Files
- `index.html` - Main HTML structure
- `styles/main.css` - Styling
- `scripts/calculator.js` - Calculator logic

Created by AI Code Agent
"""
    }
    
    result = create_project_structure(project_structure)
    print(result)
    
    # Verify files were created
    all_created = all(
        os.path.exists(get_workspace_path(path))
        for path in project_structure.keys()
    )
    
    if all_created:
        print(f"\n[OK] All project files created successfully!")
        print(f"\nProject location: {get_workspace_path('calculator')}")
        print(f"Open in browser: {get_workspace_path('calculator/index.html')}")
        return True
    else:
        print(f"\n[FAIL] Some files were not created")
        return False


def test_patch_file_success():
    """Test patching a file with valid target and replacement"""
    print_section("Testing Patch File Success")
    
    test_filename = "test_patch_success.py"
    initial_content = 'def add(a, b):\n    return a - b  # bug here\n'
    write_file_content(test_filename, initial_content)
    
    patch_payload = '{"target": "return a - b  # bug here", "replacement": "return a + b  # fixed"}'
    result = file_operation(operation="patch", path=test_filename, content=patch_payload)
    print(f"Result: {result}")
    
    with open(get_workspace_path(test_filename), 'r', encoding='utf-8') as f:
        patched_content = f.read()
    print(f"Patched Content:\n{patched_content}")
    
    assert "[SUCCESS]" in result, f"Expected SUCCESS, got: {result}"
    assert "return a + b  # fixed" in patched_content, "Replacement string missing from file content"
    assert "return a - b" not in patched_content, "Target string still present in file content"
    
    # Verify replacing ONLY first occurrence
    dup_filename = "test_patch_first_occ.py"
    dup_initial = 'value = 10\nvalue = 10\n'
    write_file_content(dup_filename, dup_initial)
    dup_patch = '{"target": "value = 10", "replacement": "value = 20"}'
    file_operation(operation="patch", path=dup_filename, content=dup_patch)
    with open(get_workspace_path(dup_filename), 'r', encoding='utf-8') as f:
        dup_content = f.read()
    assert dup_content == 'value = 20\nvalue = 10\n', f"Expected only first occurrence replaced, got: {dup_content}"
    
    print("\n[OK] test_patch_file_success passed")
    return True


def test_patch_file_missing_target():
    """Test patch operation when target string is not found in the file"""
    print_section("Testing Patch File Missing Target")
    
    test_filename = "test_patch_missing.py"
    initial_content = 'def multiply(x, y):\n    return x * y\n'
    write_file_content(test_filename, initial_content)
    
    patch_payload = '{"target": "def divide(x, y):", "replacement": "def divide(x, y):\\n    return x / y"}'
    result = file_operation(operation="patch", path=test_filename, content=patch_payload)
    print(f"Result: {result}")
    
    with open(get_workspace_path(test_filename), 'r', encoding='utf-8') as f:
        current_content = f.read()
    
    assert "Error: Target string not found in file" in result or "Target string not found" in result, f"Expected target missing error, got: {result}"
    assert "File context:" in result or "Search details" in result or "Total lines" in result, "Error message should contain line search context"
    assert current_content == initial_content, "File content should remain unchanged when target is missing"
    
    print("\n[OK] test_patch_file_missing_target passed")
    return True


def test_patch_file_invalid_ast():
    """Test AST validation prevents writing syntactically invalid Python code to disk"""
    print_section("Testing Patch File Invalid AST")
    
    test_filename = "test_patch_invalid_ast.py"
    initial_content = 'def calculate():\n    return 42\n'
    write_file_content(test_filename, initial_content)
    
    # Invalid Python syntax replacement
    patch_payload = '{"target": "return 42", "replacement": "return ("}'
    result = file_operation(operation="patch", path=test_filename, content=patch_payload)
    print(f"Result: {result}")
    
    with open(get_workspace_path(test_filename), 'r', encoding='utf-8') as f:
        current_content = f.read()
    
    assert "Syntax validation failed" in result, f"Expected Syntax validation failed error, got: {result}"
    assert current_content == initial_content, f"File content should NOT be modified on AST error. Got: {current_content}"
    
    print("\n[OK] test_patch_file_invalid_ast passed")
    return True


def test_code_agent_prompt_patch_instruction():
    """Test that CodeAgent system prompt includes patch operation instructions"""
    print_section("Testing CodeAgent Prompt Patch Instruction")
    
    agent = CodeAgent()
    prompt = agent.system_prompt
    
    assert "patch" in prompt, "CodeAgent system prompt must reference 'patch' operation"
    assert "target" in prompt and "replacement" in prompt, "CodeAgent system prompt must instruct using target and replacement"
    
    print("\n[OK] test_code_agent_prompt_patch_instruction passed")
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  FILE OPERATIONS TEST SUITE")
    print("=" * 60)
    
    results = {
        "Workspace Setup": test_workspace_setup(),
        "Write File": test_write_file(),
        "Read File": test_read_file(),
        "List Directory": test_list_directory(),
        "Create Project": test_create_project(),
        "Patch File Success": test_patch_file_success(),
        "Patch File Missing Target": test_patch_file_missing_target(),
        "Patch File Invalid AST": test_patch_file_invalid_ast(),
        "CodeAgent Prompt Patch Instruction": test_code_agent_prompt_patch_instruction(),
    }
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[OK] PASSED" if result else "[FAIL] FAILED"
        print(f"{test_name:.<40} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"\nWorkspace: {AGENT_WORKSPACE_DIR}")
    
    if passed == total:
        print("\nAll tests passed! Agents can now create files in the workspace.")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
