"""PNG previews of out/KIT.dxf (or any DXF) for checking the drawing by eye.

Usage: python gen/render.py <dxf> <outdir> [ctb]
With a ctb file the preview shows the plotted colours and pen widths.
"""
from __future__ import annotations

import pathlib
import sys

import ezdxf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from ezdxf import bbox, options
from ezdxf.addons import acadctb
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.config import BackgroundPolicy, ColorPolicy, Configuration, LineweightPolicy
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.fonts import fonts

ROOT = pathlib.Path(__file__).resolve().parent.parent


def setup_fonts():
    options.support_dirs = [str(ROOT / "out" / "fonts")]
    fonts.font_manager.build([str(ROOT / "out" / "fonts")], support_dirs=False)


def render(doc, window, path, ctb=None, px=2600, entities=None):
    x0, y0, x1, y1 = window
    w, h = x1 - x0, y1 - y0
    fig = plt.figure(figsize=(px / 200, px / 200 * h / w), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc, ctb=str(ctb) if ctb else acadctb.new_ctb())
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE,
                        color_policy=ColorPolicy.COLOR,
                        lineweight_policy=LineweightPolicy.ABSOLUTE,
                        lineweight_scaling=1.0)
    front = Frontend(ctx, MatplotlibBackend(ax), config=cfg)
    if entities is None:
        front.draw_layout(doc.modelspace(), finalize=False)
    else:
        front.draw_entities(entities)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(path, dpi=200)
    plt.close(fig)


def block_window(doc, name, pad=0.08):
    ext = bbox.extents(doc.blocks.get(name), fast=True)
    dx, dy = ext.size.x * pad + 1e-6, ext.size.y * pad + 1e-6
    return ext.extmin.x - dx, ext.extmin.y - dy, ext.extmax.x + dx, ext.extmax.y + dy


if __name__ == "__main__":
    setup_fonts()
    doc = ezdxf.readfile(sys.argv[1])
    out = pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    ctb = sys.argv[3] if len(sys.argv) > 3 else None
    ext = bbox.extents(doc.modelspace(), fast=True)
    render(doc, (ext.extmin.x, ext.extmin.y, ext.extmax.x, ext.extmax.y), out / "all.png", ctb)
    print("extents", ext.extmin, ext.extmax)
