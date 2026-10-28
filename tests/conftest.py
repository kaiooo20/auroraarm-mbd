import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auroraarm.parametros import Parametros  # noqa: E402


@pytest.fixture(scope="session")
def p():
    return Parametros.carregar()
