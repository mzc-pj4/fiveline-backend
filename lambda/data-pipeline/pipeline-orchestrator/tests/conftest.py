"""pytest sys.path + handler 캐시 충돌 방지."""
import sys
from pathlib import Path

PARENT = str(Path(__file__).parent.parent)
if PARENT in sys.path:
    sys.path.remove(PARENT)
sys.path.insert(0, PARENT)
sys.modules.pop("handler", None)
