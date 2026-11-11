"""Drawing helper: coordinates in paper millimetres, written in drawing units.

k = drawing units per paper millimetre. With the metre as drawing unit:
1:25 -> 0.025, 1:50 -> 0.05, 1:100 -> 0.1, paper space in mm -> 1.0.
"""
from __future__ import annotations

import math
import pathlib

from ezdxf import colors
from ezdxf.enums import TextEntityAlignment as TA
from fontTools.ttLib import TTFont

FONT_DIR = pathlib.Path(__file__).resolve().parent.parent / "out" / "fonts"
STYLES = {            # text style -> (font file, family, bold)
    "KIT": ("Commissioner-Regular.ttf", "Commissioner", False),
    "KIT-B": ("Commissioner-Bold.ttf", "Commissioner", True),
    "KIT-L": ("Commissioner-Light.ttf", "Commissioner Light", False),
}
ALIGN = {
    "L": TA.LEFT, "C": TA.CENTER, "R": TA.RIGHT,
    "ML": TA.MIDDLE_LEFT, "MC": TA.MIDDLE_CENTER, "MR": TA.MIDDLE_RIGHT,
    "TL": TA.TOP_LEFT, "TC": TA.TOP_CENTER, "TR": TA.TOP_RIGHT,
}
BULGE90 = math.tan(math.radians(22.5))
_metrics: dict[str, tuple] = {}


def text_width(s: str, h: float, style: str = "KIT") -> float:
    """Width of s at cap height h. CAD programs scale a TTF so the capitals are h high."""
    if style not in _metrics:
        font = TTFont(FONT_DIR / STYLES[style][0])
        _metrics[style] = (font.getBestCmap(), font["hmtx"].metrics, font["OS/2"].sCapHeight)
    cmap, hmtx, cap = _metrics[style]
    missing = [ch for ch in s if ord(ch) not in cmap]
    if missing:
        raise ValueError(f"font {style} has no glyph for {missing!r}")
    return sum(hmtx[cmap[ord(ch)]][0] for ch in s) * h / cap


def attribs(a: dict) -> dict:
    """color / layer / linetype / lineweight / rgb / ltscale -> DXF attributes."""
    out = {"layer": a.get("layer", "0")}
    if a.get("color") is not None:
        out["color"] = a["color"]
    if a.get("rgb") is not None:
        out["true_color"] = colors.rgb2int(a["rgb"])
    if a.get("linetype"):
        out["linetype"] = a["linetype"]
    if a.get("ltscale"):
        out["ltscale"] = a["ltscale"]
    if a.get("lineweight") is not None:
        out["lineweight"] = a["lineweight"]
    return out


class B:
    def __init__(self, layout, k: float, ox: float = 0.0, oy: float = 0.0, defaults: dict | None = None):
        self.layout, self.k, self.ox, self.oy = layout, k, ox, oy
        self.defaults = defaults or {}

    def at(self, dx: float, dy: float, **defaults) -> "B":
        return B(self.layout, self.k, self.ox + dx, self.oy + dy, {**self.defaults, **defaults})

    def P(self, x, y):
        return ((self.ox + x) * self.k, (self.oy + y) * self.k)

    def A(self, a):
        return attribs({**self.defaults, **a})

    # ------------------------------------------------------------ geometry
    def line(self, x1, y1, x2, y2, **a):
        return self.layout.add_line(self.P(x1, y1), self.P(x2, y2), dxfattribs=self.A(a))

    def poly(self, pts, close=False, **a):
        return self.layout.add_lwpolyline([self.P(x, y) for x, y in pts], close=close, dxfattribs=self.A(a))

    def rect(self, x1, y1, x2, y2, **a):
        return self.poly([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], close=True, **a)

    def rrect(self, x1, y1, x2, y2, r, **a):
        b = BULGE90
        pts = [(x1 + r, y1, 0), (x2 - r, y1, b), (x2, y1 + r, 0), (x2, y2 - r, b),
               (x2 - r, y2, 0), (x1 + r, y2, b), (x1, y2 - r, 0), (x1, y1 + r, b)]
        return self.layout.add_lwpolyline([(*self.P(x, y), bulge) for x, y, bulge in pts],
                                          format="xyb", close=True, dxfattribs=self.A(a))

    def bpoly(self, pts, close=True, **a):
        """Polyline with bulges: pts = (x, y, bulge)."""
        return self.layout.add_lwpolyline([(*self.P(x, y), bulge) for x, y, bulge in pts],
                                          format="xyb", close=close, dxfattribs=self.A(a))

    def bfill(self, pts, **a):
        h = self._hatch(a)
        h.paths.add_polyline_path([(*self.P(x, y), bulge) for x, y, bulge in pts], is_closed=True)
        return h

    def circle(self, x, y, r, **a):
        return self.layout.add_circle(self.P(x, y), r * self.k, dxfattribs=self.A(a))

    def arc(self, x, y, r, a0, a1, **a):
        return self.layout.add_arc(self.P(x, y), r * self.k, a0, a1, dxfattribs=self.A(a))

    # ------------------------------------------------------------ fills
    def _hatch(self, a):
        h = self.layout.add_hatch(color=a.get("color", self.defaults.get("color", 256)) or 256,
                                  dxfattribs={"layer": a.get("layer", self.defaults.get("layer", "0"))})
        rgb = a.get("rgb", self.defaults.get("rgb"))
        if rgb is not None:
            h.rgb = rgb
        return h

    def fill(self, pts, **a):
        h = self._hatch(a)
        h.paths.add_polyline_path([self.P(x, y) for x, y in pts], is_closed=True)
        return h

    def disc(self, x, y, r, **a):
        h = self._hatch(a)
        (x1, y1), (x2, y2) = self.P(x - r, y), self.P(x + r, y)
        h.paths.add_polyline_path([(x1, y1, 1), (x2, y2, 1)], is_closed=True)
        return h

    def sector(self, x, y, r, a0, a1, **a):
        """Filled pie slice from angle a0 to a1 (degrees, counter-clockwise)."""
        h = self._hatch(a)
        c = self.P(x, y)
        p0 = self.P(x + r * math.cos(math.radians(a0)), y + r * math.sin(math.radians(a0)))
        p1 = self.P(x + r * math.cos(math.radians(a1)), y + r * math.sin(math.radians(a1)))
        bulge = math.tan(math.radians(a1 - a0) / 4)
        h.paths.add_polyline_path([(*c, 0), (*p0, bulge), (*p1, 0)], is_closed=True)
        return h

    def pattern(self, pts, name, spacing, angle=0.0, **a):
        """Pattern hatch. spacing = wanted line spacing in paper mm for the
        ANSI31-type patterns (their definition spacing is 3.175)."""
        h = self._hatch(a)
        h.paths.add_polyline_path([self.P(x, y) for x, y in pts], is_closed=True)
        h.set_pattern_fill(name, color=h.dxf.color, angle=angle, scale=spacing * self.k / 3.175)
        rgb = a.get("rgb", self.defaults.get("rgb"))
        if rgb is not None:
            h.rgb = rgb
        return h

    # ------------------------------------------------------------ text
    def text(self, s, x, y, h, style="KIT", align="L", rot=0.0, **a):
        text_width(s, h, style)            # fails early when a glyph is missing
        t = self.layout.add_text(s, height=h * self.k, rotation=rot,
                                 dxfattribs={**self.A(a), "style": style})
        t.set_placement(self.P(x, y), align=ALIGN[align])
        return t

    def att(self, tag, default, x, y, h, style="KIT", align="L", prompt="", rot=0.0, **a):
        text_width(default, h, style)
        t = self.layout.add_attdef(tag, self.P(x, y), default, height=h * self.k, rotation=rot,
                                   dxfattribs={**self.A(a), "style": style, "prompt": prompt or tag})
        t.set_placement(self.P(x, y), align=ALIGN[align])
        return t

    def label(self, tag, default, x, y, h, style="KIT", align="L", att=True, **a):
        """Attribute in a usable block, plain text inside a legend."""
        if att:
            return self.att(tag, default, x, y, h, style, align, **a)
        if default == "":
            return None
        return self.text(default, x, y, h, style, align, **a)

    def underlined(self, s, x, y, h, style="KIT-B", **a):
        """Centred text with a rule under it."""
        w = text_width(s, h, style)
        self.text(s, x, y, h, style, "C", **a)
        self.line(x - w / 2, y - 0.38 * h, x + w / 2, y - 0.38 * h, **a)
