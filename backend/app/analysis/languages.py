"""Language detection by extension and line counting.

Line counting uses radon's raw analyzer for Python (accurate blank/comment/code
splits) and a pragmatic per-language heuristic for everything else. The
heuristic handles the common single-line and block comment styles; it is not a
full parser, which is fine for a health overview.
"""
from __future__ import annotations

from dataclasses import dataclass

# Directories we never descend into.
IGNORED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".env",
        "dist",
        "build",
        ".next",
        ".vite",
        ".nuxt",
        "target",
        "vendor",
        ".idea",
        ".vscode",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        "coverage",
        ".coverage",
        "site-packages",
        "bower_components",
        ".gradle",
        ".terraform",
    }
)

# Extension -> language display name.
EXT_LANGUAGE: dict[str, str] = {
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".go": "Go",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C/C++ Header",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".cs": "C#",
    ".php": "PHP",
    ".swift": "Swift",
    ".scala": "Scala",
    ".m": "Objective-C",
    ".mm": "Objective-C++",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".ps1": "PowerShell",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SCSS",
    ".less": "Less",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".ini": "INI",
    ".xml": "XML",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".sql": "SQL",
    ".r": "R",
    ".dart": "Dart",
    ".lua": "Lua",
    ".pl": "Perl",
    ".pm": "Perl",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".clj": "Clojure",
    ".hs": "Haskell",
    ".ml": "OCaml",
    ".proto": "Protobuf",
    ".tf": "Terraform",
    ".dockerfile": "Dockerfile",
    ".gradle": "Gradle",
    ".groovy": "Groovy",
}

# Filenames (no extension) worth recognizing.
FILENAME_LANGUAGE: dict[str, str] = {
    "Dockerfile": "Dockerfile",
    "Makefile": "Makefile",
    "Rakefile": "Ruby",
    "Gemfile": "Ruby",
    "requirements.txt": "Pip Requirements",
    "go.mod": "Go Module",
}

# Single-line comment tokens per language.
_LINE_COMMENTS: dict[str, tuple[str, ...]] = {
    "JavaScript": ("//",),
    "TypeScript": ("//",),
    "Java": ("//",),
    "Kotlin": ("//",),
    "Go": ("//",),
    "Rust": ("//",),
    "C": ("//",),
    "C/C++ Header": ("//",),
    "C++": ("//",),
    "C#": ("//",),
    "PHP": ("//", "#"),
    "Swift": ("//",),
    "Scala": ("//",),
    "Objective-C": ("//",),
    "Objective-C++": ("//",),
    "Dart": ("//",),
    "Vue": ("//",),
    "Svelte": ("//",),
    "Shell": ("#",),
    "PowerShell": ("#",),
    "Ruby": ("#",),
    "Perl": ("#",),
    "R": ("#",),
    "YAML": ("#",),
    "TOML": ("#",),
    "INI": ("#", ";"),
    "SQL": ("--",),
    "Lua": ("--",),
    "Elixir": ("#",),
    "Terraform": ("#", "//"),
    "Makefile": ("#",),
    "Dockerfile": ("#",),
}

# Block comment delimiters (start, end) per language.
_BLOCK_COMMENTS: dict[str, tuple[str, str]] = {
    "JavaScript": ("/*", "*/"),
    "TypeScript": ("/*", "*/"),
    "Java": ("/*", "*/"),
    "Kotlin": ("/*", "*/"),
    "Go": ("/*", "*/"),
    "Rust": ("/*", "*/"),
    "C": ("/*", "*/"),
    "C/C++ Header": ("/*", "*/"),
    "C++": ("/*", "*/"),
    "C#": ("/*", "*/"),
    "Swift": ("/*", "*/"),
    "Scala": ("/*", "*/"),
    "CSS": ("/*", "*/"),
    "SCSS": ("/*", "*/"),
    "Less": ("/*", "*/"),
    "PHP": ("/*", "*/"),
    "Dart": ("/*", "*/"),
    "HTML": ("<!--", "-->"),
    "XML": ("<!--", "-->"),
    "Vue": ("<!--", "-->"),
}


@dataclass
class LineCounts:
    code: int = 0
    blank: int = 0
    comment: int = 0

    @property
    def total(self) -> int:
        return self.code + self.blank + self.comment


def detect_language(filename: str, ext: str) -> str | None:
    if filename in FILENAME_LANGUAGE:
        return FILENAME_LANGUAGE[filename]
    return EXT_LANGUAGE.get(ext.lower())


def count_lines_generic(text: str, language: str) -> LineCounts:
    """Heuristic blank/comment/code counting for non-Python languages."""
    line_tokens = _LINE_COMMENTS.get(language, ())
    block = _BLOCK_COMMENTS.get(language)
    counts = LineCounts()
    in_block = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            counts.blank += 1
            continue

        if in_block:
            counts.comment += 1
            if block and block[1] in line:
                in_block = False
            continue

        if block and line.startswith(block[0]):
            counts.comment += 1
            # Block that doesn't close on the same line opens a run.
            if block[1] not in line[len(block[0]):]:
                in_block = True
            continue

        if line_tokens and any(line.startswith(tok) for tok in line_tokens):
            counts.comment += 1
            continue

        counts.code += 1

    return counts
