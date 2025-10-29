"""Legacy router tests kept to avoid breaking imports.

The canonical API coverage now lives in tests/test_api_endpoints.py,
so we skip this module to prevent duplicate runs.
"""

import pytest


pytestmark = pytest.mark.skip(reason="See tests/test_api_endpoints.py for API coverage.")
