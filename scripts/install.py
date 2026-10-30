"""Entry point executed only by the user's explicit installer action."""
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'src'))
from expkm.installer import main
raise SystemExit(main(root))
