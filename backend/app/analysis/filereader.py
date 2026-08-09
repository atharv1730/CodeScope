"""Safe file reading + per-file line counting.

Returns None for files we should skip (binary, too large, or an unrecognized
type). Python files get accurate counts from radon's raw analyzer; other
recognized languages use the heuristic counter.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from radon.raw import analyze as radon_raw_analyze

from app.analysis.languages import LineCounts, count_lines_generic, detect_language

# Skip files larger than this to avoid pathological inputs (generated bundles,
# vendored blobs). Size in bytes.
MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB


@dataclass
class FileCount:
    language: str
    counts: LineCounts


def _looks_binary(chunk: bytes) -> bool:
    if b"\x00" in chunk:
        return True
    # High proportion of non-text bytes -> treat as binary.
    if not chunk:
        return False
    text_chars = bytes(range(0x20, 0x7F)) + b"\n\r\t\f\b"
    nontext = sum(1 for b in chunk if b not in text_chars)
    return nontext / len(chunk) > 0.30


def count_file(abs_path: str, rel_path: str) -> FileCount | None:
    filename = os.path.basename(rel_path)
    _, ext = os.path.splitext(filename)
    language = detect_language(filename, ext)
    if language is None:
        return None

    try:
        size = os.path.getsize(abs_path)
    except OSError:
        return None
    if size > MAX_FILE_BYTES:
        return None

    try:
        with open(abs_path, "rb") as fh:
            head = fh.read(2048)
            if _looks_binary(head):
                return None
            rest = fh.read()
        text = (head + rest).decode("utf-8", errors="replace")
    except OSError:
        return None

    if language == "Python":
        counts = _count_python(text)
    else:
        counts = count_lines_generic(text, language)
    return FileCount(language=language, counts=counts)


def _count_python(text: str) -> LineCounts:
    try:
        raw = radon_raw_analyze(text)
        # radon: sloc = source lines of code, comments = single-line comments,
        # multi = lines in multiline strings/docstrings (count as comments),
        # blank = blank lines.
        return LineCounts(
            code=raw.sloc,
            blank=raw.blank,
            comment=raw.comments + raw.multi,
        )
    except (SyntaxError, Exception):  # noqa: BLE001 - fall back on any parse issue
        # Broken/Py2 file: fall back to a plain blank/comment/code split.
        return count_lines_generic(text, "Shell")  # '#' comment style
