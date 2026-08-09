import os
import sys
import tempfile
from typing import List

import pytest
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Setup import path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock config
sys.modules['agents.config'] = type('MockConfig', (), {'AGENT_WORKSPACE_DIR': '/tmp'})()

from agents.context_manager import (
    ContextManager, 
    get_context_manager,
    CHARS_PER_TOKEN
)

def test_estimate_tokens():
    cm = ContextManager()
    text = "Hello world" * 10
    expected_tokens = int(len(text) / CHARS_PER_TOKEN)
    assert cm.estimate_tokens(text) == expected_tokens

def test_compact_history_preserves_last_4():
    cm = ContextManager()
    messages = [
        HumanMessage(content=f"Message {i}") for i in range(10)
    ]
    compacted = cm.compact_history(messages)
    
    # Should have a summary message + 4 recent messages
    assert len(compacted) == 5
    assert isinstance(compacted[0], SystemMessage)
    assert "Conversation Summary" in str(compacted[0].content)
    
    # Check last 4 are preserved verbatim
    for i in range(4):
        assert compacted[i+1].content == f"Message {i+6}"

def test_compact_history_truncates_long_messages():
    cm = ContextManager()
    long_content = "A" * 3000
    messages = [HumanMessage(content=long_content)]
    
    compacted = cm.compact_history(messages)
    assert len(compacted) == 1
    content = str(compacted[0].content)
    assert "truncated 2000 chars" in content
    assert content.startswith("A" * 500)
    assert content.endswith("A" * 500)
    assert len(content) < 3000

def test_truncate_output_short():
    cm = ContextManager()
    short_output = "Line 1\nLine 2\nLine 3"
    result = cm.truncate_output(short_output, max_lines=10)
    assert result == short_output

def test_truncate_output_keeps_errors():
    cm = ContextManager()
    lines = [f"Line {i}" for i in range(100)]
    lines[50] = "This is a critical Error in the middle"
    output = '\n'.join(lines)
    
    result = cm.truncate_output(output, max_lines=50)
    
    assert "Line 0" in result
    assert "Line 19" in result
    assert "This is a critical Error in the middle" in result
    assert "Line 85" in result
    assert "Line 99" in result

def test_build_file_tree():
    cm = ContextManager()
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some files
        os.makedirs(os.path.join(temp_dir, "src"))
        with open(os.path.join(temp_dir, "src", "main.py"), "w") as f:
            f.write("print('hello')")
            
        tree = cm.build_file_tree(root_dir=temp_dir)
        assert "src/" in tree
        assert "main.py" in tree

def test_get_file_outline_python():
    cm = ContextManager()
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "test.py")
        with open(file_path, "w") as f:
            f.write("import os\nclass MyClass:\n  def my_method(self, arg):\n    pass\ndef my_func():\n  pass\n")
            
        outline = cm.get_file_outline(file_path)
        assert "import os" in outline
        assert "class MyClass: def my_method(self, arg)" in outline
        assert "def my_func()" in outline

def test_scratchpad_operations():
    cm = ContextManager()
    cm.set_scratchpad("test_key", "test_value")
    assert cm.get_scratchpad("test_key") == "test_value"
    assert cm.get_scratchpad("missing", "default") == "default"
    
    cm.clear_scratchpad()
    assert cm.get_scratchpad("test_key") is None

def test_singleton():
    cm1 = get_context_manager(1000)
    cm2 = get_context_manager(1000)
    assert cm1 is cm2
    
    cm3 = get_context_manager(2000)
    assert cm3 is not cm1
