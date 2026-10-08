import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.run_eval import run_eval

if __name__ == "__main__":
    run_eval(scan_only=True)
