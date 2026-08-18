"""
paths.py -- Project-relative filesystem paths.
"""

import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def project_path(*parts) -> str:
    """Absolute path to a location inside the project root."""
    return os.path.join(PROJECT_ROOT, *parts)


def ensure_dir(path: str) -> str:
    """Create the directory if missing and return it."""
    os.makedirs(path, exist_ok=True)
    return path
