"""Makes the four static Commissioner fonts in out/fonts from the variable font.

CAD programs handle a variable font badly, so the kit ships static weights.
Overlapping outlines are merged: a CAD program fills text itself and can show
holes where two outlines of one glyph overlap.

Usage: python gen/make_fonts.py <Commissioner variable .ttf>
Source: https://github.com/google/fonts/tree/main/ofl/commissioner (SIL OFL 1.1)
"""
import pathlib
import sys

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

OUT = pathlib.Path(__file__).resolve().parent.parent / "out" / "fonts"
WEIGHTS = {"Light": 300, "Regular": 400, "Medium": 500, "Bold": 700}

if __name__ == "__main__":
    src = sys.argv[1]
    OUT.mkdir(parents=True, exist_ok=True)
    for name, weight in WEIGHTS.items():
        font = TTFont(src)
        location = {axis.axisTag: axis.defaultValue for axis in font["fvar"].axes}
        location["wght"] = weight
        static = instancer.instantiateVariableFont(
            font, location, updateFontNames=True, overlap=instancer.OverlapMode.REMOVE)
        static.save(OUT / f"Commissioner-{name}.ttf")
        names = static["name"]
        print(name, "|", names.getDebugName(1), "|", names.getDebugName(2), "|", names.getDebugName(4))
