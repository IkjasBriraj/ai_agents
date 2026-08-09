import os
import sys
import tempfile
import json
import pytest
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.vector_store import BM25Index, HybridCodeStore

def test_bm25_tokenize():
    index = BM25Index()
    tokens = index.tokenize("Hello world! This is a TEST.")
    assert "hello" in tokens
    assert "world" in tokens
    assert "test" in tokens
    assert "this" not in tokens # stop word

def test_bm25_search():
    index = BM25Index()
    index.add_document("doc1", "The quick brown fox jumps over the lazy dog", {"path": "file1.txt"})
    index.add_document("doc2", "A fast brown fox", {"path": "file2.txt"})
    index.add_document("doc3", "Something completely different", {"path": "file3.txt"})
    
    results = index.search("brown fox")
    assert len(results) > 0
    # Both doc1 and doc2 have 'brown' and 'fox', but doc2 is shorter so might score higher
    doc_ids = [res[1]["id"] for res in results]
    assert "doc1" in doc_ids
    assert "doc2" in doc_ids

def test_hybrid_code_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "vector_store.json")
        store = HybridCodeStore(storage_path=storage_path)
        
        # Test add document with fake embedding
        store.add_document(
            text="def hello_world(): print('hello')",
            metadata={"path": "main.py", "chunk": 0},
            embedding=[0.1, 0.2, 0.3]
        )
        
        assert len(store.dense_store.data) == 1
        assert store.sparse_index.num_docs == 1
        
        # Test hybrid query
        # Since we just have 1 doc, it should return it
        store.dense_store.data[0]["embedding"] = [0.1, 0.2, 0.3] # ensure it's there
        # Create a mock embedder class for the test
        class MockEmbedder:
            def embed_text(self, text):
                return [0.1, 0.2, 0.3]
                
        store.embedder = MockEmbedder()
        
        results = store.hybrid_query("hello world", k=1)
        assert len(results) == 1
        assert results[0][1]["text"] == "def hello_world(): print('hello')"
        
        # Test file hashing
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")
            
        assert store.is_file_changed(test_file) == True
        assert store.is_file_changed(test_file) == False
        
        with open(test_file, "w") as f:
            f.write("new content")
            
        assert store.is_file_changed(test_file) == True

