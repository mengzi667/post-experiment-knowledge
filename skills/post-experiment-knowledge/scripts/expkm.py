"""Self-contained installed skill, or source/plugin checkout launcher."""
import sys
from pathlib import Path

skill = Path(__file__).resolve().parents[1]
runtime = skill/'runtime'
source = skill.parents[1]/'src'
sys.path.insert(0, str(runtime if runtime.is_dir() else source))
from expkm.cli import main
raise SystemExit(main())
