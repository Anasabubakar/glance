"""
CLI for the grounding benchmark (see glance/shell/ai/grounding.py).

    python tools/grounding_bench.py [--trials 8] [--models a,b,c] [--refine]
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "glance" / "shell"))

from ai import grounding as g  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=8)
    ap.add_argument("--models", default="")
    ap.add_argument("--refine", action="store_true", help="two-step: coarse guess then zoomed re-aim")
    a = ap.parse_args()
    if a.models:
        asyncio.run(g.bench(a.models.split(","), a.trials, a.refine))
    else:
        asyncio.run(g.calibrate(a.trials, 8))
