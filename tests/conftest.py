import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def sample_urls():
    return [
        'https://example.com',
        'https://httpstat.us/404',
        'https://httpstat.us/301',
    ]
