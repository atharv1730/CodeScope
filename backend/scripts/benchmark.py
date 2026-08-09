"""Benchmark the analysis passes against an already-cloned repository.

Times the compute-heavy part of each pass (the DB writes are negligible by
comparison) so you get representative per-pass timings and totals.

Usage:
    python scripts/benchmark.py /path/to/cloned/repo [more/repos ...]
"""
from __future__ import annotations

import os
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.analysis.complexity import _analyze_python_file  # noqa: E402
from app.analysis.filereader import count_file  # noqa: E402
from app.analysis.git import MAX_FILES_FOR_COCHANGE, _week_start  # noqa: E402
from app.analysis.gitlog import parse_git_log, run_git_log  # noqa: E402
from app.analysis.imports import resolve_edges  # noqa: E402
from app.analysis.structure import _walk_code_files  # noqa: E402


def _time(fn):
    start = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - start


def benchmark(path: str) -> dict:
    # --- structure ---
    def structure():
        files = []
        loc = 0
        py = {}
        for ap, rel in _walk_code_files(path):
            r = count_file(ap, rel)
            if r is None:
                continue
            files.append((ap, rel, r))
            loc += r.counts.code
            if r.language == "Python":
                py[rel] = ap
        return files, loc, py

    (files, loc, py_files), t_structure = _time(structure)

    # --- git ---
    def git():
        commits = parse_git_log(run_git_log(path))
        file_changes = Counter()
        authors = defaultdict(Counter)
        co = Counter()
        weekly = Counter()
        for c in commits:
            for p in c.files:
                file_changes[p] += 1
                authors[p][c.author_email] += 1
            if 2 <= len(c.files) <= MAX_FILES_FOR_COCHANGE:
                for a, b in combinations(sorted(set(c.files)), 2):
                    co[(a, b)] += 1
            if c.date:
                weekly[(_week_start(c.date.date()), c.author_email)] += 1
        return commits
    commits, t_git = _time(git)

    # --- complexity (python only) ---
    def complexity():
        scored = 0
        for rel, ap in py_files.items():
            if _analyze_python_file(ap) is not None:
                scored += 1
        return scored
    scored, t_complexity = _time(complexity)

    # --- import graph ---
    def imports():
        sources = {}
        for rel, ap in py_files.items():
            try:
                sources[rel] = open(ap, encoding="utf-8", errors="replace").read()
            except OSError:
                pass
        return resolve_edges(list(py_files.keys()), sources)
    edges, t_imports = _time(imports)

    total = t_structure + t_git + t_complexity + t_imports
    return {
        "repo": os.path.basename(path.rstrip("/")),
        "files": len(files),
        "loc": loc,
        "python_files": len(py_files),
        "commits": len(commits),
        "import_edges": len(edges),
        "t_structure": t_structure,
        "t_git": t_git,
        "t_complexity": t_complexity,
        "t_imports": t_imports,
        "t_total": total,
    }


def main(paths: list[str]) -> None:
    rows = [benchmark(p) for p in paths]
    header = f"{'repo':16} {'files':>6} {'LOC':>8} {'py':>5} {'commits':>8} {'edges':>6} {'struct':>7} {'git':>7} {'cx':>7} {'imp':>7} {'TOTAL':>7}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['repo']:16} {r['files']:>6} {r['loc']:>8} {r['python_files']:>5} "
            f"{r['commits']:>8} {r['import_edges']:>6} "
            f"{r['t_structure']:>7.2f} {r['t_git']:>7.2f} {r['t_complexity']:>7.2f} "
            f"{r['t_imports']:>7.2f} {r['t_total']:>7.2f}"
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])
