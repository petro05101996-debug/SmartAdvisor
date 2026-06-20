#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release gate for SmartAdvisor v8.6.64.
Fails if a release tree/archive contains runtime databases, screenshots, caches,
or old generated audit artifacts that previously leaked into ZIP archives.
"""
from __future__ import annotations
import fnmatch
import sys
import zipfile
from pathlib import Path

FORBIDDEN_PARTS = {'__pycache__', '.pytest_cache'}
FORBIDDEN_PREFIXES = ('appdb', 'audit_v', 'LIVE_CORE_AUDIT', 'ui_audit', 'REAL_COMPLEX_REPORTS')
FORBIDDEN_SUFFIXES = ('.pyc', '.pyo', '.sqlite3', '.sqlite', '.db', '.png', '.jpg', '.jpeg', '.webp')
FORBIDDEN_GLOBS = (
    'SAAS_UI_VERIFY_*.json', 'UI_BROWSER_SMOKE_*.json', 'COMPLETE_UIUX_VERIFY_*.json', 'TRAINER_MAX_UX_VERIFY_*.json', 'COMPLEX_CASE_*.json', 'AUDIT_REPORT*.md', 'LANGUAGE_STYLE_*',
    'REPORT_CORE_v8_6_*.md', 'USER_ACCEPTANCE_*.md', 'USER_ACCEPTANCE_VERIFY_*.json',
    'REFERENCE_INTERVIEW_VERIFY_*.json', 'ALL_TECH_REPORT*.md', 'COMPLEX_E2E_*.md',
    'CONTEXTUAL_CLARIFICATIONS_*.md', 'DEEP_SCHEMA_VALIDATION_*.md', 'LAYOUT_NO_OVERLAP_*.md',
    'REAL_USER_FLOW_*.md', 'SCHEMA_VALIDATION_*.md', 'USER_REPORT_*.md', 'real_user_*.txt',
)
REQUIRED_FILES = {'app.py', 'engine.py', 'report.py', 'learning.py', 'ui.py', 'README.md'}


def bad_path(path: str) -> str | None:
    parts = [p for p in path.replace('\\', '/').split('/') if p]
    name = parts[-1] if parts else path
    if any(part in FORBIDDEN_PARTS for part in parts):
        return 'cache directory'
    if any(name.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        return 'generated runtime/audit directory'
    if name.lower().endswith(FORBIDDEN_SUFFIXES):
        return 'generated binary/runtime file'
    if any(fnmatch.fnmatch(name, pat) for pat in FORBIDDEN_GLOBS):
        return 'generated audit artifact'
    return None


def iter_tree(root: Path):
    for p in root.rglob('*'):
        if '.git' in p.parts:
            continue
        if p == root:
            continue
        rel = p.relative_to(root).as_posix()
        yield rel, p.is_dir()


def check_paths(paths):
    bad = []
    files = set()
    for rel, is_dir in paths:
        if not is_dir:
            files.add(Path(rel).name)
        reason = bad_path(rel)
        if reason:
            bad.append((rel, reason))
    missing = sorted(REQUIRED_FILES - files)
    if missing:
        bad.extend((f'<missing:{m}>', 'required file missing') for m in missing)
    return bad


def main(argv: list[str]) -> int:
    target = Path(argv[1]) if len(argv) > 1 else Path('.')
    if target.is_file() and target.suffix == '.zip':
        with zipfile.ZipFile(target) as zf:
            infos = []
            for n in zf.namelist():
                if n.endswith('/'):
                    infos.append((n.rstrip('/'), True))
                else:
                    infos.append((n, False))
            # Strip single top-level folder for required-file check.
            roots = {Path(n).parts[0] for n, _ in infos if Path(n).parts}
            if len(roots) == 1:
                root = next(iter(roots))
                normalized = []
                for n, d in infos:
                    parts = Path(n).parts
                    normalized.append(('/'.join(parts[1:]), d) if len(parts) > 1 else ('', True))
                infos = [(n, d) for n, d in normalized if n]
            bad = check_paths(infos)
    else:
        bad = check_paths(iter_tree(target))
    if bad:
        print('RELEASE_GATE_FAIL')
        for rel, reason in bad[:200]:
            print(f'- {rel}: {reason}')
        if len(bad) > 200:
            print(f'... and {len(bad)-200} more')
        return 1
    print('RELEASE_GATE_OK')
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
