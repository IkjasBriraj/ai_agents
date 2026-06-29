"""
Test File Operations in Workspace
Verify that agents can create, read, and write files
"""

import os
import sys
from agents.config import AGENT_WORKSPACE_DIR, get_workspace_path
from agents.tools import write_file_content, read_file_content, list_directory, create_project_structure


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
        print(f"\n✓ File created successfully at: {file_path}")
        return True
    else:
        print(f"\n✗ File was not created")
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
        print(f"\n✓ All project files created successfully!")
        print(f"\nProject location: {get_workspace_path('calculator')}")
        print(f"Open in browser: {get_workspace_path('calculator/index.html')}")
        return True
    else:
        print(f"\n✗ Some files were not created")
        return False


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
    }
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:.<40} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"\nWorkspace: {AGENT_WORKSPACE_DIR}")
    
    if passed == total:
        print("\n🎉 All tests passed! Agents can now create files in the workspace.")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
