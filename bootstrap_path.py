import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def setup() -> Path:
    root_str = str(ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return ROOT
