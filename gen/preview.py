"""Renders preview PNGs of the kit into out/preview. Run after build.py."""
from __future__ import annotations

import pathlib
import sys
import warnings

warnings.simplefilter("ignore")
import ezdxf

import build
import render

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main(only=None):
    render.setup_fonts()
    doc, zones = build.build()
    out = ROOT / "out" / "preview"
    out.mkdir(exist_ok=True)
    ctb = ROOT / "out" / "ctb" / "KIT-50.ctb"
    jobs = {"01-pragmatiko-megethos": (zones["R"], None, 3000)}
    x0, y0, x1, y1 = zones["50"]
    sx0, sy0, sx1, sy1 = zones["50_sheet"]
    jobs["02-etiketes-symvola-1-50"] = ((x0, sy1 + 9.0, x1, y1), ctb, 4400)
    jobs["03-ypomnimata-1-50"] = ((x0, sy1 + 0.3, x1, sy1 + 9.2), ctb, 4200)
    jobs["04-fyllo-A1-1-50"] = ((sx0 - 0.5, sy0 - 0.5, sx1 + 0.5, sy1 + 0.5), ctb, 3400)
    jobs["05-pinakida-1-50"] = ((sx1 - 10.6, sy0 + 0.2, sx1 - 0.2, sy0 + 19.6), ctb, 2200)
    jobs["06-epipla-ygieinis"] = (zones["F"], ctb, 3000)
    px0, py0, px1, py1 = zones["P"]
    jobs["07-protypa-matchprop"] = (zones["P"], ctb, 4000)
    jobs["08-hatch-diastaseis"] = ((px0, py0, px0 + 21.0, py0 + 9.5), ctb, 3400)
    for name, (window, c, px) in jobs.items():
        if only and only not in name:
            continue
        render.render(doc, window, out / f"{name}.png", c, px)
        print(name, tuple(round(v, 2) for v in window))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
