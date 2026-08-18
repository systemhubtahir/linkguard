import os
import sys

import pytest

# Make both `import engine` and `from src.engine import ...` work in tests.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for path in (ROOT, os.path.join(ROOT, 'src')):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture
def sample_urls():
    return [
        'https://example.com',
        'https://httpstat.us/404',
        'https://httpstat.us/301',
    ]
