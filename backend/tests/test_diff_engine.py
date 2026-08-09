import sys
import os
import tempfile
import pytest
from pathlib import Path

# Add backend directory to sys.path so we can import agents module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.diff_engine import (
    SearchReplaceBlock,
    parse_search_replace_blocks,
    apply_search_replace,
    apply_blocks,
    generate_unified_diff,
    normalize_content
)

def test_normalize_content():
    content = "line1 \nline2\t\nline3\r\n\n"
    assert normalize_content(content) == "line1\nline2\nline3"

def test_parse_blocks_single():
    output = """
path/to/file.py
<<<<<<< SEARCH
def foo():
    pass
=======
def foo():
    return True
>>>>>>> REPLACE
"""
    blocks = parse_search_replace_blocks(output)
    assert len(blocks) == 1
    assert blocks[0].file_path == "path/to/file.py"
    assert blocks[0].search_content == "def foo():\n    pass"
    assert blocks[0].replace_content == "def foo():\n    return True"

def test_parse_blocks_multiple():
    output = """
file1.py
<<<<<<< SEARCH
a
=======
b
>>>>>>> REPLACE

<<<<<<< SEARCH
c
=======
d
>>>>>>> REPLACE
"""
    blocks = parse_search_replace_blocks(output)
    assert len(blocks) == 2
    assert blocks[0].file_path == "file1.py"
    assert blocks[0].search_content == "a"
    assert blocks[0].replace_content == "b"
    assert blocks[1].file_path == "" # no filepath for second block
    assert blocks[1].search_content == "c"

def test_parse_edge_cases():
    output = "random text without blocks"
    blocks = parse_search_replace_blocks(output)
    assert len(blocks) == 0

def test_apply_exact_match(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("def foo():\n    pass\n", encoding="utf-8")
    
    res = apply_search_replace(str(f), "def foo():\n    pass\n", "def bar():\n    pass\n")
    assert res.success is True
    assert res.confidence == 1.0
    assert f.read_text(encoding="utf-8") == "def bar():\n    pass\n"

def test_apply_fuzzy_match(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("def foo():\n    print('a')\n    print('b')\n", encoding="utf-8")
    
    # Trailing whitespace difference — should fuzzy match
    search = "def foo():\n    print('a')  \n    print('b')  "
    replace = "def foo():\n    print('c')"
    
    res = apply_search_replace(str(f), search, replace, similarity_threshold=0.6)
    assert res.success is True
    assert res.confidence >= 0.6
    assert "print('c')" in f.read_text(encoding="utf-8")

def test_apply_failed_match(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("def xyz():\n    pass\n", encoding="utf-8")
    
    # Completely unrelated content — should not match
    res = apply_search_replace(str(f), "class Widget:\n    def render(self):\n        return '<div>Hello</div>'", "class Gadget:\n    pass")
    assert res.success is False


def test_empty_replacement(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("a\nb\nc\n", encoding="utf-8")
    
    # Deletion scenario
    res = apply_search_replace(str(f), "b\n", "")
    assert res.success is True
    assert f.read_text(encoding="utf-8") == "a\nc\n"

def test_apply_blocks_multiple(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("line1\nline2\n", encoding="utf-8")
    
    b1 = SearchReplaceBlock("", "line1", "LINE1")
    b2 = SearchReplaceBlock("", "line2", "LINE2")
    
    res = apply_blocks([b1, b2], default_file_path=str(f))
    assert len(res) == 2
    assert res[0].success is True
    assert res[1].success is True
    assert f.read_text(encoding="utf-8") == "LINE1\nLINE2\n"

def test_generate_unified_diff():
    orig = "a\nb\nc\n"
    new = "a\nx\nc\n"
    diff = generate_unified_diff(orig, new, "test.py")
    assert "--- test.py" in diff
    assert "+++ test.py" in diff
    assert "-b\n" in diff
    assert "+x\n" in diff
