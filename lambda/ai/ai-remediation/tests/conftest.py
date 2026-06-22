"""pytest 가 핸들러 모듈을 import 할 수 있도록 sys.path 설정."""
import sys
from pathlib import Path

# tests/ 의 상위 폴더 (handler.py, validator.py 가 있는 곳) 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
