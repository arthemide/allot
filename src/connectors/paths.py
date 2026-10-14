"""Where the connectors keep their local state.

All under one directory so a deployment can move it to a mounted volume with a
single setting. In the container that is /data/connectors, on the volume that
already holds the app's database; by default it is data/connectors/ in the
tree, which git ignores.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent

DATA_DIR = Path(os.getenv("ALLOT_CONNECTORS_DIR", ROOT / "data" / "connectors"))
