import os
from pathlib import Path
from typing import Set

# Common directories and file extensions to ignore
DEFAULT_IGNORE_DIRS: Set[str] = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "eggs",
    "parts",
    "bin",
    "develop-eggs",
    "lib",
    "lib64",
    "parts",
    "sdist",
    "var",
    "share",
}

DEFAULT_IGNORE_EXTS: Set[str] = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".exe",
    ".bin",
    ".so",
    ".dll",
    ".dylib",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
}

def get_repo_structure(base_dir: Path | str, prefix: str = "") -> str:
    """
    Recursively walks base_dir and returns a string tree representation of the codebase.
    Avoids infinite recursion by following symlinks only selectively and ignoring common folders.
    """
    base_dir = Path(base_dir).resolve()
    if not base_dir.exists() or not base_dir.is_dir():
        return f"[Error: {base_dir} is not a valid directory]"
        
    tree = []
    
    try:
        items = sorted(base_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        return f"{prefix}[Permission Denied]\n"
        
    for i, item in enumerate(items):
        if item.name in DEFAULT_IGNORE_DIRS:
            continue
        if item.is_file() and item.suffix.lower() in DEFAULT_IGNORE_EXTS:
            continue
            
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        
        tree.append(f"{prefix}{connector}{item.name}")
        
        if item.is_dir():
            extension_prefix = "    " if is_last else "│   "
            # Limit depth or handle massive directory structures if needed
            subtree = get_repo_structure(item, prefix + extension_prefix)
            if subtree:
                tree.append(subtree)
                
    return "\n".join(tree)

def read_safe_text(file_path: Path | str, max_chars: int = 50000) -> str:
    """
    Safely reads a text file, handling different encodings and truncating if it exceeds max_chars.
    """
    file_path = Path(file_path).resolve()
    if not file_path.exists() or not file_path.is_file():
        return f"[Error: File {file_path.name} not found or is a directory]"
        
    # Check if file has binary extension
    if file_path.suffix.lower() in DEFAULT_IGNORE_EXTS:
        return f"[Skipped: Binary file {file_path.name}]"
        
    encodings = ["utf-8", "latin-1", "cp1252", "utf-16"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read(max_chars + 1)
                if len(content) > max_chars:
                    return content[:max_chars] + f"\n\n... [TRUNCATED - file exceeds {max_chars} characters] ..."
                return content
        except (UnicodeDecodeError, PermissionError):
            continue
            
    return f"[Error: Could not decode {file_path.name} (possibly binary or unsupported encoding)]"
