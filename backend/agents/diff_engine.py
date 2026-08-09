import logging
import os
import re
import difflib
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

@dataclass
class SearchReplaceBlock:
    file_path: str
    search_content: str
    replace_content: str

@dataclass
class SearchReplaceResult:
    success: bool
    file_path: str
    message: str
    confidence: float
    matched_line_range: Optional[Tuple[int, int]]

def normalize_content(content: str) -> str:
    """Normalize content by stripping trailing whitespace per line and converting to \n."""
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    normalized_lines = [line.rstrip() for line in lines]
    joined = "\n".join(normalized_lines)
    return joined.rstrip("\n")

def parse_search_replace_blocks(llm_output: str) -> List[SearchReplaceBlock]:
    """Parse Aider-style search/replace blocks from LLM output text."""
    blocks = []
    
    # Pattern to match optional file path header, SEARCH and REPLACE blocks
    pattern = re.compile(
        r'(?:(?P<filepath>[^\n]*?)\n)?<<<<<<< SEARCH\n(?P<search>.*?)\n=======\n(?P<replace>.*?)\n>>>>>>> REPLACE',
        re.DOTALL
    )
    
    for match in pattern.finditer(llm_output):
        filepath = match.group('filepath') or ""
        filepath = filepath.strip()
        search_content = match.group('search')
        replace_content = match.group('replace')
        
        # Clean up any potential markdown ticks or extra formatting in the path
        if filepath.startswith("```"):
            filepath = filepath.strip("` \n\t")
            
        blocks.append(SearchReplaceBlock(
            file_path=filepath,
            search_content=search_content,
            replace_content=replace_content
        ))
        
    return blocks

def apply_search_replace(file_path: str, search_content: str, replace_content: str, similarity_threshold: float = 0.6) -> SearchReplaceResult:
    """Apply a search/replace block to a file."""
    if not os.path.exists(file_path):
        return SearchReplaceResult(
            success=False,
            file_path=file_path,
            message=f"File not found: {file_path}",
            confidence=0.0,
            matched_line_range=None
        )
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
    except Exception as e:
        return SearchReplaceResult(
            success=False,
            file_path=file_path,
            message=f"Failed to read file: {e}",
            confidence=0.0,
            matched_line_range=None
        )
        
    # Attempt exact match first
    if search_content in file_content:
        new_content = file_content.replace(search_content, replace_content)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return SearchReplaceResult(
                success=True,
                file_path=file_path,
                message="Exact match found and replaced.",
                confidence=1.0,
                matched_line_range=None 
            )
        except Exception as e:
            return SearchReplaceResult(
                success=False,
                file_path=file_path,
                message=f"Failed to write file: {e}",
                confidence=1.0,
                matched_line_range=None
            )

    # Fuzzy matching line-by-line fallback
    norm_search = normalize_content(search_content)
    file_lines_raw = file_content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    search_lines_norm = [line.rstrip() for line in norm_search.split("\n")]
    file_lines_norm = [line.rstrip() for line in file_lines_raw]
    
    best_ratio = 0.0
    best_window = None
    
    search_len = len(search_lines_norm)
    if search_len == 0:
        return SearchReplaceResult(
            success=False,
            file_path=file_path,
            message="Search content is empty.",
            confidence=0.0,
            matched_line_range=None
        )

    # Sliding window to find best match
    for i in range(len(file_lines_norm)):
        for w_size in range(max(1, search_len - 3), search_len + 4):
            if i + w_size > len(file_lines_norm):
                break
                
            window_lines = file_lines_norm[i:i+w_size]
            matcher = difflib.SequenceMatcher(None, window_lines, search_lines_norm)
            ratio = matcher.ratio()
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_window = (i, i + w_size)
                
    if best_ratio >= similarity_threshold and best_window is not None:
        start_idx, end_idx = best_window
        replace_lines = replace_content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        
        # Replace the best matching window with the replacement content
        new_file_lines = file_lines_raw[:start_idx] + replace_lines + file_lines_raw[end_idx:]
        new_content = "\n".join(new_file_lines)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return SearchReplaceResult(
                success=True,
                file_path=file_path,
                message=f"Fuzzy match replaced with {best_ratio:.2f} confidence.",
                confidence=best_ratio,
                matched_line_range=(start_idx + 1, end_idx) # 1-indexed for line ranges
            )
        except Exception as e:
            return SearchReplaceResult(
                success=False,
                file_path=file_path,
                message=f"Failed to write file after fuzzy match: {e}",
                confidence=best_ratio,
                matched_line_range=(start_idx + 1, end_idx)
            )
            
    # Failed to find a matching window
    preview = "\n".join(search_lines_norm[:3])
    return SearchReplaceResult(
        success=False,
        file_path=file_path,
        message=f"No match found. Preview of search content:\n{preview}",
        confidence=best_ratio,
        matched_line_range=None
    )


def apply_blocks(blocks: List[SearchReplaceBlock], default_file_path: Optional[str] = None) -> List[SearchReplaceResult]:
    """Apply multiple blocks sequentially."""
    results = []
    for block in blocks:
        path = block.file_path if block.file_path else default_file_path
        if not path:
            results.append(SearchReplaceResult(
                success=False,
                file_path="",
                message="No file path provided for block.",
                confidence=0.0,
                matched_line_range=None
            ))
            continue
            
        res = apply_search_replace(path, block.search_content, block.replace_content)
        results.append(res)
    return results


def generate_unified_diff(original: str, modified: str, file_path: str = 'file') -> str:
    """Generate a standard unified diff string."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=file_path,
        tofile=file_path,
        n=3
    )
    return "".join(diff)
