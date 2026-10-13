import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

# data/scripts is a folder of standalone scripts, not a package.
sys.path.insert(0, str(ROOT / "data" / "scripts"))
sys.path.insert(0, str(ROOT))

# Importing the agent must never need real credentials or network access.
os.environ.setdefault("ES_URL", "http://localhost:9200")
os.environ.setdefault("ES_API_KEY", "test-key")
