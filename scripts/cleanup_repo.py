#!/usr/bin/env python3
"""
Repository Cleanup Script
========================
Prepares the repository for professional submission by:
1. Removing __pycache__ and .pyc files
2. Scanning for accidentally committed secrets
3. Formatting Python files with black and isort
4. Generating a clean .gitignore if missing entries
5. Checking for common issues

Usage:
    python cleanup_repo.py           # Dry run (show what would be done)
    python cleanup_repo.py --apply   # Actually perform cleanup
    python cleanup_repo.py --check   # Just check for issues, exit 1 if found
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Repository root (script should be run from project root)
REPO_ROOT = Path(__file__).parent.parent if Path(__file__).parent.name == "scripts" else Path(__file__).parent

# Patterns that might indicate leaked secrets
SECRET_PATTERNS = [
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key'),
    (r'sk-[a-zA-Z0-9]{32,}', 'OpenAI API Key'),
    (r'AIza[0-9A-Za-z\-_]{35}', 'Google API Key'),
    (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Personal Token'),
    (r'gho_[a-zA-Z0-9]{36}', 'GitHub OAuth Token'),
    (r'sk_live_[a-zA-Z0-9]{24,}', 'Stripe Live Key'),
    (r'sk_test_[a-zA-Z0-9]{24,}', 'Stripe Test Key'),
    (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', 'JWT Token'),
    (r'xox[baprs]-[a-zA-Z0-9]{10,}', 'Slack Token'),
    (r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', 'Private Key'),
    (r'mongodb\+srv://[^:]+:[^@]+@', 'MongoDB Connection String'),
    (r'postgres://[^:]+:[^@]+@', 'PostgreSQL Connection String'),
    (r'redis://[^:]+:[^@]+@', 'Redis Connection String'),
]

# Directories to skip when scanning
SKIP_DIRS = {
    '.git', 'node_modules', 'venv', '.venv', '__pycache__',
    'dist', 'build', '.eggs', '*.egg-info', '.tox', '.mypy_cache',
    '.pytest_cache', 'htmlcov', '.coverage', 'data', 'lance_data',
    '.lancedb'
}

# File extensions to skip
SKIP_EXTENSIONS = {
    '.pyc', '.pyo', '.exe', '.dll', '.so', '.dylib',
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg',
    '.woff', '.woff2', '.ttf', '.eot',
    '.zip', '.tar', '.gz', '.rar',
    '.pdf', '.doc', '.docx',
    '.db', '.sqlite', '.sqlite3',
    '.lance', '.idx'
}

# Files to always skip
SKIP_FILES = {
    '.env', '.env.local', '.env.production', '.env.example',
    'package-lock.json', 'yarn.lock', 'poetry.lock'
}


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print('='*60)


def print_issue(severity: str, message: str, file: str = None):
    """Print an issue with severity color."""
    colors = {
        'error': '\033[91m',    # Red
        'warning': '\033[93m',  # Yellow
        'info': '\033[94m',     # Blue
        'success': '\033[92m',  # Green
    }
    reset = '\033[0m'
    
    prefix = f"{colors.get(severity, '')}{severity.upper()}{reset}"
    if file:
        print(f"  [{prefix}] {file}: {message}")
    else:
        print(f"  [{prefix}] {message}")


def should_skip_path(path: Path) -> bool:
    """Check if a path should be skipped."""
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
        for pattern in SKIP_DIRS:
            if '*' in pattern and Path(part).match(pattern):
                return True
    return False


def should_skip_file(path: Path) -> bool:
    """Check if a file should be skipped."""
    if path.name in SKIP_FILES:
        return True
    if path.suffix.lower() in SKIP_EXTENSIONS:
        return True
    return False


def find_pycache_dirs() -> List[Path]:
    """Find all __pycache__ directories."""
    pycache_dirs = []
    for root, dirs, _ in os.walk(REPO_ROOT):
        if '__pycache__' in dirs:
            pycache_dirs.append(Path(root) / '__pycache__')
        # Don't descend into skip dirs
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    return pycache_dirs


def find_pyc_files() -> List[Path]:
    """Find all .pyc files outside __pycache__."""
    pyc_files = []
    for root, dirs, files in os.walk(REPO_ROOT):
        if should_skip_path(Path(root)):
            continue
        for f in files:
            if f.endswith('.pyc'):
                pyc_files.append(Path(root) / f)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    return pyc_files


def scan_for_secrets() -> List[Tuple[Path, str, str, int]]:
    """Scan repository for potential secrets."""
    findings = []
    
    for root, dirs, files in os.walk(REPO_ROOT):
        path = Path(root)
        if should_skip_path(path):
            dirs[:] = []
            continue
        
        for f in files:
            file_path = path / f
            if should_skip_file(file_path):
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                for pattern, secret_type in SECRET_PATTERNS:
                    for line_num, line in enumerate(content.splitlines(), 1):
                        if re.search(pattern, line):
                            # Skip if it's in a comment or example
                            if 'example' in line.lower() or 'xxx' in line.lower():
                                continue
                            findings.append((file_path, secret_type, line.strip()[:50], line_num))
            except Exception:
                continue
        
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    
    return findings


def check_gitignore() -> List[str]:
    """Check .gitignore for recommended entries."""
    recommended = [
        '.env',
        '.env.local',
        '.env.production',
        '__pycache__/',
        '*.pyc',
        '.venv/',
        'venv/',
        'node_modules/',
        '.lancedb/',
        'lance_data/',
        '*.log',
        '.DS_Store',
        'Thumbs.db',
        '.idea/',
        '.vscode/',
        '*.sqlite3',
        'htmlcov/',
        '.coverage',
        '.pytest_cache/',
    ]
    
    gitignore_path = REPO_ROOT / '.gitignore'
    missing = []
    
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        for entry in recommended:
            # Check if entry or similar pattern exists
            base = entry.rstrip('/')
            if base not in content and f'{base}/' not in content:
                missing.append(entry)
    else:
        missing = recommended
    
    return missing


def run_black(apply: bool = False) -> Tuple[bool, str]:
    """Run black formatter."""
    try:
        cmd = ['black', '--check', '--diff', '.'] if not apply else ['black', '.']
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout + result.stderr
    except FileNotFoundError:
        return True, "black not installed (pip install black)"


def run_isort(apply: bool = False) -> Tuple[bool, str]:
    """Run isort import sorter."""
    try:
        cmd = ['isort', '--check-only', '--diff', '.'] if not apply else ['isort', '.']
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout + result.stderr
    except FileNotFoundError:
        return True, "isort not installed (pip install isort)"


def check_python_files() -> List[Tuple[Path, str]]:
    """Check Python files for common issues."""
    issues = []
    
    for root, dirs, files in os.walk(REPO_ROOT):
        path = Path(root)
        if should_skip_path(path):
            dirs[:] = []
            continue
        
        for f in files:
            if not f.endswith('.py'):
                continue
            
            file_path = path / f
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Check for debug prints
                if 'print(' in content and 'DEBUG' not in file_path.name.upper():
                    # Count prints not in comments
                    for line_num, line in enumerate(content.splitlines(), 1):
                        stripped = line.strip()
                        if stripped.startswith('print(') and not stripped.startswith('#'):
                            issues.append((file_path, f"Debug print on line {line_num}"))
                            break
                
                # Check for TODO/FIXME
                for line_num, line in enumerate(content.splitlines(), 1):
                    if 'TODO' in line or 'FIXME' in line or 'XXX' in line:
                        issues.append((file_path, f"TODO/FIXME on line {line_num}"))
                        break
                        
            except Exception:
                continue
        
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    
    return issues


def main():
    parser = argparse.ArgumentParser(description='Repository cleanup script')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry run)')
    parser.add_argument('--check', action='store_true', help='Check only, exit 1 if issues found')
    args = parser.parse_args()
    
    issues_found = False
    
    # 1. Find __pycache__ directories
    print_header("Scanning for __pycache__ directories")
    pycache_dirs = find_pycache_dirs()
    if pycache_dirs:
        for d in pycache_dirs:
            print_issue('warning', f"Found {d.relative_to(REPO_ROOT)}")
            if args.apply:
                shutil.rmtree(d)
                print_issue('success', f"Removed {d.relative_to(REPO_ROOT)}")
        issues_found = True
    else:
        print_issue('success', "No __pycache__ directories found")
    
    # 2. Find .pyc files
    print_header("Scanning for .pyc files")
    pyc_files = find_pyc_files()
    if pyc_files:
        for f in pyc_files:
            print_issue('warning', f"Found {f.relative_to(REPO_ROOT)}")
            if args.apply:
                f.unlink()
                print_issue('success', f"Removed {f.relative_to(REPO_ROOT)}")
        issues_found = True
    else:
        print_issue('success', "No stray .pyc files found")
    
    # 3. Scan for secrets
    print_header("Scanning for potential secrets")
    secrets = scan_for_secrets()
    if secrets:
        for path, secret_type, preview, line_num in secrets:
            print_issue('error', f"{secret_type} on line {line_num}: {preview}...", 
                       str(path.relative_to(REPO_ROOT)))
        issues_found = True
    else:
        print_issue('success', "No potential secrets found")
    
    # 4. Check .gitignore
    print_header("Checking .gitignore")
    missing_ignores = check_gitignore()
    if missing_ignores:
        print_issue('warning', f"Missing recommended entries: {', '.join(missing_ignores[:5])}")
        if len(missing_ignores) > 5:
            print_issue('info', f"...and {len(missing_ignores) - 5} more")
        
        if args.apply:
            gitignore_path = REPO_ROOT / '.gitignore'
            with open(gitignore_path, 'a') as f:
                f.write('\n# Added by cleanup_repo.py\n')
                for entry in missing_ignores:
                    f.write(f'{entry}\n')
            print_issue('success', f"Added {len(missing_ignores)} entries to .gitignore")
    else:
        print_issue('success', ".gitignore has all recommended entries")
    
    # 5. Check Python formatting (black)
    print_header("Checking Python formatting (black)")
    black_ok, black_output = run_black(apply=args.apply)
    if not black_ok:
        if "not installed" in black_output:
            print_issue('info', black_output)
        else:
            print_issue('warning', "Some files need formatting")
            if args.apply:
                print_issue('success', "Formatted with black")
            issues_found = True
    else:
        print_issue('success', "All Python files are properly formatted")
    
    # 6. Check import sorting (isort)
    print_header("Checking import sorting (isort)")
    isort_ok, isort_output = run_isort(apply=args.apply)
    if not isort_ok:
        if "not installed" in isort_output:
            print_issue('info', isort_output)
        else:
            print_issue('warning', "Some imports need sorting")
            if args.apply:
                print_issue('success', "Sorted with isort")
            issues_found = True
    else:
        print_issue('success', "All imports are properly sorted")
    
    # 7. Check for common issues
    print_header("Checking for common issues")
    code_issues = check_python_files()
    if code_issues:
        for path, issue in code_issues[:10]:  # Limit output
            print_issue('info', issue, str(path.relative_to(REPO_ROOT)))
        if len(code_issues) > 10:
            print_issue('info', f"...and {len(code_issues) - 10} more issues")
    else:
        print_issue('success', "No common issues found")
    
    # Summary
    print_header("Summary")
    if args.apply:
        print_issue('success', "Cleanup complete!")
    elif args.check:
        if issues_found:
            print_issue('error', "Issues found. Run with --apply to fix.")
            sys.exit(1)
        else:
            print_issue('success', "No issues found!")
    else:
        if issues_found:
            print_issue('warning', "Issues found. Run with --apply to fix.")
        else:
            print_issue('success', "Repository is clean!")
    
    print()


if __name__ == '__main__':
    main()
