"""Builds the CAD kit: out/KIT.dxf, out/ctb/KIT-*.ctb.

Run from the project root:  python gen/build.py
Then gen/convert.sh turns the DXF into a DWG with the ODA File Converter.
"""
from __future__ import annotations

import io
import math
import pathlib
import struct
import zlib

import ezdxf
from ezdxf import bbox
from ezdxf.addons import acadctb

import furniture as F
import symbols as S
from draw import ALIGN, B, STYLES, text_width
from minilisp import Interp

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "out"

SCALES = {"25": 0.025, "50": 0.05, "100": 0.1}     # drawing units (m) per paper mm
PAPER = {"MM": 1.0}                                 # paper space drawn in mm

# ---------------------------------------------------------------- layers
# name, colour, lineweight (1/100 mm, -3 = default), linetype
# Her layers, as found in her three drawings.
HER_LAYERS = [
    ("Τομή Γραμμή", 243, 53, None),
    ("PROVOLH_FRONT", 242, 40, None),      # was colour 243: same colour as the 0.53 cut line
    ("PROVOLH", 21, 40, None),             # was colour 20: same colour as Σκάλες 0.25
    ("PROVOLH1", 152, 30, None),
    ("PROVOLH2", 143, 25, None),
    ("PROVOLH3", 147, 15, None),
    ("PROVOLH4", 185, 15, None),
    ("PROBOLH", 2, 25, None),
    ("WALLS", 6, 50, None),
    ("Πλάκα Στέγης", 22, 40, None),
    ("Πόρτες", 150, 15, None),
    ("Παράθυρα", 92, 15, None),
    ("Ανοίγματα", 172, 20, None),
    ("Σκάλες", 20, 25, None),
    ("Έπιπλα", 10, 15, None),
    ("Ερμάρια", 10, 15, None),
    ("FURNITUR", 11, 20, None),
    ("Τουαλέτα - Εξαρτήματα", 190, 20, None),
    ("KITBATH", 190, 20, None),            # was 0.18: same colour as Τουαλέτα 0.20
    ("Διαγραμμίσεις AEC", 252, 9, None),
    ("Γραμμές Διακεκομμένες 1-50 AEC", 253, 15, "HIDDEN2"),
    ("Διαστάσεις", 221, 18, None),
    ("DIM", 8, 18, None),
    ("STATHMES", 8, 18, None),
    ("Χώροι", 34, 30, None),
    ("Χώροι  - Σύμβολα", 131, 20, None),
    ("Σύμβολα Τομών", 191, 20, None),
    ("NOTES", 42, 20, None),
    ("SYMBOL", 72, 18, None),
    ("VLASTISI", 86, 25, None),
    ("TEXT", 7, -3, None),
    ("GRAMMATA", 5, -3, None),
    ("TITLOI_1", 7, -3, None),
]
# New layers of the kit. Colours that her drawings do not use.
KIT_LAYERS = [
    ("Ηλεκτρολογικά", 1, 25, None),
    ("Φωτισμός", 12, 25, None),
    ("Ψευδοροφή", 32, 30, None),
    ("Ετικέτες", 61, 18, None),
    ("Υπομνήματα", 61, 18, None),
    ("Πινακίδα", 61, 18, None),
    ("Υπόβαθρο Γκρι", 9, 18, None),
    ("Υδραυλικά", 141, 18, None),
    ("Γεμίσματα", 254, -3, None),
    ("Σοβατεπί TL-01", 30, 50, None),
    ("Σοβατεπί TL-07", 50, 50, None),
]
# layers that also carry a true colour: a line drawn on them, or given their
# properties with MATCHPROP, looks like the line in the floor legend
LAYER_RGB = {"Σοβατεπί TL-01": S.SKIRTING["TL-01"], "Σοβατεπί TL-07": S.SKIRTING["TL-07"]}
INFO_LAYER = "KIT-Οδηγίες"        # captions of the library sheet, does not plot

# ---------------------------------------------------------------- pens (ctb)
# colour -> lineweight in mm at 1:50, taken from her layers
ARCH_PENS = {
    243: 0.53, 6: 0.50, 113: 0.50, 242: 0.40, 21: 0.40, 22: 0.40,
    152: 0.30, 34: 0.30, 32: 0.30,
    143: 0.25, 2: 0.25, 20: 0.25, 86: 0.25, 106: 0.25,
    11: 0.20, 172: 0.20, 190: 0.20, 131: 0.20, 191: 0.20, 42: 0.20,
    145: 0.18, 72: 0.18,
    150: 0.15, 92: 0.15, 10: 0.15, 147: 0.15, 185: 0.15, 253: 0.15,
    252: 0.09,
}
# 1:50 width -> width at the other scales
STEP = {
    "25": {0.53: 0.70, 0.50: 0.70, 0.40: 0.50, 0.30: 0.40, 0.25: 0.30, 0.20: 0.25, 0.18: 0.20, 0.15: 0.18, 0.09: 0.09},
    "50": {},
    "100": {0.53: 0.35, 0.50: 0.35, 0.40: 0.30, 0.30: 0.20, 0.25: 0.18, 0.20: 0.13, 0.18: 0.13, 0.15: 0.09, 0.09: 0.05},
}
# annotation pens: the same width on paper at every scale
CONST_PENS = {8: 0.18, 221: 0.18, 60: 0.13, 61: 0.18, 62: 0.25, 64: 0.35, 65: 0.50}
RED_PENS = {1: 0.25, 12: 0.25}             # plot red
PLOT_RED = (220, 0, 0)
GRAY_PENS = {9: 0.18}                      # plot 40 % grey
OWN_COLOUR_PENS = {141: 0.18, 30: 0.50, 50: 0.50}   # plot in the object colour


def pens(scale: str) -> dict[int, float]:
    out = {c: STEP[scale].get(w, w) for c, w in ARCH_PENS.items()}
    for group in (CONST_PENS, RED_PENS, GRAY_PENS, OWN_COLOUR_PENS):
        out.update(group)
    return out


def write_ctb(scale: str, path: pathlib.Path) -> None:
    ctb = acadctb.new_ctb()
    ctb.description = f"KIT 1:{scale} - same colours, pen widths for 1:{scale}"
    table = pens(scale)
    for aci in range(1, 256):
        style = ctb.new_style(aci)
        style.color = (0, 0, 0)                 # everything black ...
        style.set_lineweight(table.get(aci, 0.0))   # 0.0 = use the object lineweight
        style.screen = 100
        if aci in RED_PENS:
            style.color = PLOT_RED
        elif aci in GRAY_PENS:
            style.screen = 40
        elif aci in OWN_COLOUR_PENS:
            style.set_object_color()
    save_ctb(ctb, path)


def save_ctb(ctb, path: pathlib.Path) -> None:
    """Writes the plot style table.

    ezdxf's own save() packs the header with native C longs. On macOS and Linux
    that gives a 72-byte header and a file no CAD program reads. A file written
    by AutoCAD has 48 bytes of text, then three little-endian 32-bit numbers:
    Adler-32 of the compressed body, uncompressed size, compressed size.
    """
    text = io.StringIO()
    ctb.write_content(text)
    raw = text.getvalue().encode("utf-8") + b"\x00"
    body = zlib.compress(raw)
    header = b"PIAFILEVERSION_2.0,CTBVER1,compress\r\npmzlibcodec"
    path.write_bytes(header + struct.pack("<III", zlib.adler32(body), len(raw), len(body)) + body)


# ---------------------------------------------------------------- document

def new_doc():
    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = 0        # unitless: no automatic scaling on insert
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LTSCALE"] = 1.0
    doc.header["$LUNITS"] = 2
    doc.header["$LUPREC"] = 2
    doc.linetypes.add("HIDDEN2", [4.7625, 3.175, -1.5875], description="Hidden (.5x) _ _ _ _ _ _ _ _ _ _ _")
    doc.linetypes.add("KIT_DASH", [0.15, 0.10, -0.05], description="KIT dashed 10cm - 5cm")
    doc.linetypes.add("KIT_LED", [0.27, 0.15, -0.03, 0.0, -0.03, 0.0, -0.03, 0.0, -0.03],
                      description="KIT LED tape ___ . . . ___ . . .")
    doc.linetypes.add("KIT_SYND", [3.0, 2.0, -1.0], description="KIT connection 2mm - 1mm (ltscale = scale / 1000)")
    for name, (font, family, bold) in STYLES.items():
        style = doc.styles.add(name, font=font)
        style.set_extended_font_data(family, bold=bold)
    doc.styles.add(DIM_STYLE_FONT[0], font=DIM_STYLE_FONT[1])
    for name, color, lw, ltype in HER_LAYERS + KIT_LAYERS:
        layer = doc.layers.add(name, color=color, lineweight=lw, linetype=ltype or "Continuous")
        if name in LAYER_RGB:
            layer.rgb = LAYER_RGB[name]
    doc.layers.add(INFO_LAYER, color=140, plot=False)
    add_dimstyles(doc)
    return doc


# ---------------------------------------------------------------- dimensions

DIM_STYLE_FONT = ("KIT-DIM", "arial.ttf")     # the reference dimensions are in Arial
DIM_SCALES = {"25": 0.025, "50": 0.05}        # she asked for 1:25 and 1:50


def add_dimstyles(doc):
    """KIT_25, KIT_50: black, in centimetres, as on the flooring sheet.
    KIT_FOT_25, KIT_FOT_50: the same in red, for the lighting plans."""
    for suffix, k in DIM_SCALES.items():
        for prefix, colour in (("KIT_", 256), ("KIT_FOT_", 1)):
            doc.dimstyles.new(f"{prefix}{suffix}", dxfattribs={
                "dimscale": k, "dimlfac": 100.0, "dimdec": 0, "dimlunit": 2, "dimzin": 8,
                "dimtxsty": DIM_STYLE_FONT[0], "dimtxt": 2.0, "dimgap": 0.7, "dimtad": 1,
                "dimtih": 0, "dimtoh": 0, "dimtsz": 1.0, "dimasz": 1.0,
                "dimexe": 1.0, "dimexo": 1.0, "dimdle": 0.0,
                "dimclrd": colour, "dimclre": colour, "dimclrt": colour,
            })


def new_block(doc, name):
    blk = doc.blocks.new(name)
    blk.block_record.dxf.units = 0
    return blk


# ---------------------------------------------------------------- blocks from KIT.lsp

LISP_SAMPLES = [   # block name, lisp call, layer in the library
    ("SYR2_2000_250", '(kit:def-syr "SYR2_2000_250" 2.0 2 0.25 nil)', "Παράθυρα"),
    ("SYR2_3000_250", '(kit:def-syr "SYR2_3000_250" 3.0 2 0.25 nil)', "Παράθυρα"),
    ("SYR3_3600_250", '(kit:def-syr "SYR3_3600_250" 3.6 3 0.25 nil)', "Παράθυρα"),
    ("SYR4_4000_250", '(kit:def-syr "SYR4_4000_250" 4.0 4 0.25 nil)', "Παράθυρα"),
    ("SYR2_3000_350_M", '(kit:def-syr "SYR2_3000_350_M" 3.0 2 0.35 T)', "Παράθυρα"),
    ("SYRM3_3000_250", '(kit:def-syrm "SYRM3_3000_250" 3.0 3 0.25 nil nil)', "Παράθυρα"),
    ("SYRX1_1000_250", '(kit:def-syrm "SYRX1_1000_250" 1.0 1 0.25 T nil)', "Πόρτες"),
    ("SYRX2_2000_250", '(kit:def-syrm "SYRX2_2000_250" 2.0 2 0.25 T nil)', "Παράθυρα"),
    ("PAR_600_250", '(kit:def-par "PAR_600_250" 0.6 0.25 nil)', "Παράθυρα"),
    ("PAR_1200_250", '(kit:def-par "PAR_1200_250" 1.2 0.25 nil)', "Παράθυρα"),
    ("PAR_1200_350_M", '(kit:def-par "PAR_1200_350_M" 1.2 0.35 T)', "Παράθυρα"),
    ("POR_800_2200_A", '(kit:def-porta "POR_800_2200_A" 0.8 2.2 nil)', "Πόρτες"),
    ("POR_900_2200_D", '(kit:def-porta "POR_900_2200_D" 0.9 2.2 T)', "Πόρτες"),
    ("PSEYD_3000_300", '(kit:def-pseyd "PSEYD_3000_300" 3.0 0.3)', "Ψευδοροφή"),
    ("PK1_900_250_A", '(kit:def-portak "PK1_900_250_A" 0.9 0.25 1 nil nil)', "Πόρτες"),
    ("PK1_900_250_A_M", '(kit:def-portak "PK1_900_250_A_M" 0.9 0.25 1 nil T)', "Πόρτες"),
    ("PK2_1400_250_M", '(kit:def-portak "PK2_1400_250_M" 1.4 0.25 2 nil T)', "Πόρτες"),
    ("SK_1000_16_280", '(kit:def-skala "SK_1000_16_280" 1.0 16 0.28)', "Σκάλες"),
    ("TRAP_1800_900", '(kit:def-trap "TRAP_1800_900" 1.8 0.9 T)', "Έπιπλα"),
    ("TRAP_2400_1000", '(kit:def-trap "TRAP_2400_1000" 2.4 1.0 T)', "Έπιπλα"),
    ("TRAP_1200_800_X", '(kit:def-trap "TRAP_1200_800_X" 1.2 0.8 nil)', "Έπιπλα"),
    ("KAREKLA", '(kit:def-karekla "KAREKLA" "R")', "Έπιπλα"),
    ("KAREKLA_T", '(kit:def-karekla "KAREKLA_T" "T")', "Έπιπλα"),
    ("RAGA_2400_3", '(kit:def-raga "RAGA_2400_3" 2.4 3)', "Φωτισμός"),
    ("LED_2000_50", '(kit:def-led "LED_2000_50" 2.0 50)', "Φωτισμός"),
]
FRAME_SAMPLES = LISP_SAMPLES[:14]
PLAN_SAMPLES = LISP_SAMPLES[14:]


def lisp_blocks(doc) -> None:
    """Runs lisp/KIT.lsp and copies what its entmake calls produce into the DXF."""
    it = Interp()
    it.run((ROOT / "lisp" / "KIT.lsp").read_text(encoding="ascii"))
    for name, call, _ in LISP_SAMPLES:
        it.run(call)
        blk = new_block(doc, name)
        for ent in (e for e in it.entities if e.get("block") == name):
            codes = ent["codes"]
            first = {}
            for code, value in codes:
                first.setdefault(code, value)
            a = {"layer": first[8]}
            for code, key in ((62, "color"), (6, "linetype"), (370, "lineweight"), (420, "true_color")):
                if code in first:
                    a[key] = first[code]
            kind = ent["type"]
            if kind == "LINE":
                blk.add_line(first[10], first[11], dxfattribs=a)
            elif kind == "LWPOLYLINE":
                blk.add_lwpolyline([v for c, v in codes if c == 10], close=bool(first[70] & 1), dxfattribs=a)
            elif kind == "CIRCLE":
                blk.add_circle(first[10], first[40], dxfattribs=a)
            elif kind == "ARC":
                blk.add_arc(first[10], first[40], math.degrees(first[50]), math.degrees(first[51]), dxfattribs=a)
            elif kind == "SOLID":
                blk.add_solid([first[10], first[11], first[12], first[13]], dxfattribs=a)
            else:
                raise ValueError(f"{name}: entity {kind} is not copied")


# ---------------------------------------------------------------- annotation blocks

def simple(draw):
    return lambda b: draw(b)


def annotation_blocks() -> list[tuple[str, object, str, str]]:
    """base name, draw function, library layer, library group"""
    out = [
        ("ETIK", S.tag, "Ετικέτες", "tags"),
        ("TELEIOMATA", S.finishes, "Ετικέτες", "tags"),
        ("ANOIGMA", S.opening_tag, "Ετικέτες", "tags"),
        ("THYRA", S.door_tag, "Ετικέτες", "tags"),
        ("STATHMI", S.level, "Ετικέτες", "tags"),
        ("STATHMI1", lambda b: S.level(b, two=False), "Ετικέτες", "tags"),
        ("STATHMI_ED", lambda b: S.level(b, kind="ground"), "Ετικέτες", "tags"),
        ("ANAPT", S.elevation_ref, "Ετικέτες", "tags"),
        ("LEPT", S.detail_ref, "Ετικέτες", "tags"),
        ("ORIGIN", S.origin, "Ετικέτες", "tags"),
        ("HL_DIAK", S.el_switch, "Ηλεκτρολογικά", "power"),
        ("HL_DIAK_AR", lambda b: S.el_switch(b, True), "Ηλεκτρολογικά", "power"),
        ("HL_PRIZA", S.el_socket, "Ηλεκτρολογικά", "power"),
        ("HL_PRIZA_ST", lambda b: S.el_socket(b, True), "Ηλεκτρολογικά", "power"),
    ]
    for lab in S.EL_OUTLETS:
        out.append((f"HL_{lab}", (lambda lab: lambda b: S.el_outlet(b, lab))(lab), "Ηλεκτρολογικά", "power"))
    for d in S.DIRS:
        for n in ARROW_COUNTS:
            out.append((f"HL_YPSI{n}_{d}", (lambda d, n: lambda b: S.height_arrow(b, d, n))(d, n), "Ηλεκτρολογικά", "heights"))
    out += [
        ("HO_DIAK1", lambda b: S.pl_plate(b, "1"), "Ηλεκτρολογικά", "plates"),
        ("HO_DIAK2", lambda b: S.pl_plate(b, "2"), "Ηλεκτρολογικά", "plates"),
        ("HO_PRIZA", lambda b: S.pl_plate(b, "S"), "Ηλεκτρολογικά", "plates"),
        ("HO_TV", lambda b: S.pl_plate(b, "TV", "TV"), "Ηλεκτρολογικά", "plates"),
        ("HO_D", lambda b: S.pl_data(b, "D"), "Ηλεκτρολογικά", "plates"),
        ("HO_TL", lambda b: S.pl_data(b, "TL"), "Ηλεκτρολογικά", "plates"),
        ("HO_K", lambda b: S.pl_plate(b, "S", "K"), "Ηλεκτρολογικά", "plates"),
        ("HO_DW", lambda b: S.pl_plate(b, "S", "DW"), "Ηλεκτρολογικά", "plates"),
        ("HO_W", lambda b: S.pl_plate(b, "S", "W"), "Ηλεκτρολογικά", "plates"),
    ]
    out += [(name, draw, "Φωτισμός", "lights") for name, draw, _ in S.LIGHTS]
    out += [(name, draw, "Υπομνήματα", "legends") for name, draw in S.LEGENDS]
    out += [
        ("PINAKIDA", S.title_block, "Πινακίδα", "sheet"),
        ("ANATHEORISEIS", S.revisions, "Πινακίδα", "sheet"),
        ("SIMEIOSEIS", S.general_notes, "Πινακίδα", "sheet"),
    ]
    out += [(f"PLAISIO_{size}", (lambda size: lambda b: S.sheet_frame(b, size))(size), "Πινακίδα", "sheet")
            for size in S.SHEETS]
    return out


ARROW_COUNTS = (1, 2, 3, 4, 5, 6)


def build_furniture(doc) -> None:
    for name, draw, _ in F.SANITARY + F.FURNITURE:
        draw(B(new_block(doc, name), 1.0))


def build_annotation(doc) -> None:
    items = annotation_blocks()
    for suffix, k in SCALES.items():
        for base, draw, _, _ in items:
            draw(B(new_block(doc, f"{base}_{suffix}"), k))
    for suffix, k in PAPER.items():
        for base, draw, _, group in items:
            if group == "sheet":
                draw(B(new_block(doc, f"{base}_{suffix}"), k))


# ---------------------------------------------------------------- library sheet

class Flow:
    """Places block references in rows, left to right, with a caption under each."""

    def __init__(self, doc, x0, y0, k, max_w=None):
        self.doc, self.msp = doc, doc.modelspace()
        self.x0, self.y, self.k, self.max_w = x0, y0, k, max_w
        self.x, self.row_h = x0, 0.0
        self.width = 0.0

    def heading(self, text, h=6.0):
        self.newline()
        t = self.msp.add_text(text, height=h * self.k, dxfattribs={"layer": INFO_LAYER, "style": "KIT-B"})
        t.set_placement((self.x0, self.y - h * self.k))
        self.y -= (h + 8) * self.k

    def note(self, text, h=3.0):
        t = self.msp.add_text(text, height=h * self.k, dxfattribs={"layer": INFO_LAYER, "style": "KIT"})
        t.set_placement((self.x0, self.y - h * self.k))
        self.y -= (h + 4) * self.k

    def newline(self):
        if self.row_h:
            self.y -= self.row_h + 14 * self.k
        self.x, self.row_h = self.x0, 0.0

    def put(self, name, layer, gap=10.0, caption=True):
        blk = self.doc.blocks.get(name)
        ext = bbox.extents(blk, fast=True)
        w, h = ext.size.x, ext.size.y
        if self.max_w and self.x > self.x0 and self.x + w - self.x0 > self.max_w:
            self.newline()
        ins = (self.x - ext.extmin.x, self.y - h - ext.extmin.y)
        ref = self.msp.add_blockref(name, ins, dxfattribs={"layer": layer})
        if any(True for _ in blk.attdefs()):
            ref.add_auto_attribs({})
        if caption:
            t = self.msp.add_text(name, height=2.0 * self.k, dxfattribs={"layer": INFO_LAYER, "style": "KIT"})
            t.set_placement((self.x, self.y - h - 5.5 * self.k))
        self.x += max(w, len(name) * 1.5 * self.k) + gap * self.k
        self.row_h = max(self.row_h, h + 6 * self.k)
        self.width = max(self.width, self.x - self.x0)
        return ref, ins


def library(doc) -> dict[str, tuple[float, float, float, float]]:
    """Lays every block out in model space. Returns zone -> (x0, y0, x1, y1) for the previews."""
    zones = {}
    items = annotation_blocks()

    f = Flow(doc, 0.0, 0.0, 0.05)
    f.heading("ΠΡΑΓΜΑΤΙΚΟ ΜΕΓΕΘΟΣ (1 μονάδα = 1 m)  -  ΚΟΥΦΩΜΑΤΑ, ΠΟΡΤΕΣ, ΨΕΥΔΟΡΟΦΗ")
    f.note("Δείγματα. Για άλλο μήκος: APPLOAD KIT.lsp και μετά KSYR, KSYRM, KSYRX, KPAR, KPORTA, KPSEYD.")
    f.note("Κύριες γραμμές ByLayer: το block παίρνει το χρώμα του layer όπου μπαίνει. Κατάληξη _M: κούφωμα στη μέση του τοίχου.")
    rows = [FRAME_SAMPLES[0:5], FRAME_SAMPLES[5:11], FRAME_SAMPLES[11:14]]
    for row in rows:
        f.newline()
        for name, _, layer in row:
            f.put(name, layer, gap=16)
    f.newline()
    zones["R"] = (-0.5, f.y, max(f.width, 14.0) + 0.5, 0.5)

    x = zones["R"][2] + 3.0
    for suffix, k in SCALES.items():
        f = Flow(doc, x, 0.0, k, max_w=840 * k)
        f.heading(f"ΚΛΙΜΑΚΑ 1:{suffix}  -  blocks με κατάληξη _{suffix}", 7.0)
        f.note("Μπαίνουν όπως είναι (scale 1) σε σχέδιο που τυπώνεται σε αυτή την κλίμακα.")
        for group, title in (("tags", "Ετικέτες και σύμβολα (layer Ετικέτες)"),
                             ("power", "Ρεύματα σε κάτοψη (layer Ηλεκτρολογικά, τυπώνεται κόκκινο)"),
                             ("plates", "Ρεύματα σε ανάπτυγμα (layer Ηλεκτρολογικά)"),
                             ("heights", "Ύψη πριζών: βελάκι προς τον τοίχο, 1 έως 6 σημεία (layer Ηλεκτρολογικά)"),
                             ("lights", "Φωτισμός (layer Φωτισμός, τυπώνεται κόκκινο)"),
                             ("legends", "Υπομνήματα (layer Υπομνήματα)")):
            f.newline()
            f.note(title, 3.2)
            for base, _, layer, g in items:
                if g == group:
                    f.put(f"{base}_{suffix}", layer, gap=12 if group != "legends" else 14)
        f.newline()
        f.note("Πινακίδα σε φύλλο A1 (layer Πινακίδα). Υπάρχουν και PLAISIO_A0, _A2, _A3.", 3.2)
        y_top = f.y
        frame, (fx, fy) = f.put(f"PLAISIO_A1_{suffix}", "Πινακίδα", caption=False)
        corner = (fx + (841 - S.MARGIN) * k, fy + S.MARGIN * k)
        msp = doc.modelspace()
        for name, dy in (("PINAKIDA", 0.0), ("ANATHEORISEIS", S.PANEL_H), ("SIMEIOSEIS", S.PANEL_H + 66)):
            ref = msp.add_blockref(f"{name}_{suffix}", (corner[0], corner[1] + dy * k), dxfattribs={"layer": "Πινακίδα"})
            ref.add_auto_attribs({})
        f.newline()
        zones[suffix] = (x - 10 * k, f.y, x + max(f.width, 860 * k) + 10 * k, 12 * k)
        zones[suffix + "_sheet"] = (fx, fy, fx + 841 * k, fy + 594 * k)
        x = zones[suffix][2] + 60 * k
    zones["F"] = furniture_zone(doc, x + 6.0, 0.0)
    zones["P"] = palette_zone(doc, zones["F"][2] + 6.0, 0.0)
    return zones


# ---------------------------------------------------------------- framed cells

def text(msp, s, x, y, h, style="KIT", layer=INFO_LAYER, align="L", color=None):
    a = {"layer": layer, "style": style}
    if color is not None:
        a["color"] = color
    t = msp.add_text(s, height=h, dxfattribs=a)
    t.set_placement((x, y), align=ALIGN[align])
    return t


class Grid:
    """Framed cells in rows. Each cell has a caption at the bottom. Frames and
    captions are on the layer that does not plot."""

    def __init__(self, doc, x0, y0, k):
        self.doc, self.msp, self.x0, self.y, self.k = doc, doc.modelspace(), x0, y0, k
        self.right = x0

    def heading(self, s, note=None):
        text(self.msp, s, self.x0, self.y - 5 * self.k, 5 * self.k, "KIT-B")
        self.y -= 9 * self.k
        if note:
            text(self.msp, note, self.x0, self.y - 3 * self.k, 3 * self.k)
            self.y -= 6 * self.k
        self.y -= 2 * self.k

    def row(self, cells, cw, ch):
        """cells: (caption, fill(x0, y0, x1, y1)). One row of framed cells."""
        x = self.x0
        cap = 2.2 * self.k
        for caption, fill in cells:
            self.msp.add_lwpolyline([(x, self.y), (x + cw, self.y), (x + cw, self.y - ch), (x, self.y - ch)],
                                    close=True, dxfattribs={"layer": INFO_LAYER, "color": 9})
            lines = caption.split("\n")
            for i, line in enumerate(reversed(lines)):
                text(self.msp, line, x + 0.5 * cw, self.y - ch + (1.6 + 3.4 * i) * self.k, cap,
                     "KIT-B" if i == len(lines) - 1 and len(lines) > 1 else "KIT", align="C")
            fill(x, self.y - ch + (2.5 + 3.4 * len(lines)) * self.k, x + cw, self.y)
            x += cw + 4 * self.k
        self.right = max(self.right, x)
        self.y -= ch + 4 * self.k

    def rows(self, cells, cw, ch, per_row):
        for i in range(0, len(cells), per_row):
            self.row(cells[i:i + per_row], cw, ch)
        self.y -= 6 * self.k


def centred_block(doc, name, layer):
    """fill() for a cell: the block centred in the free part of the cell."""
    def fill(x0, y0, x1, y1):
        blk = doc.blocks.get(name)
        ext = bbox.extents(blk, fast=True)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ins = (cx - (ext.extmin.x + ext.extmax.x) / 2, cy - (ext.extmin.y + ext.extmax.y) / 2)
        ref = doc.modelspace().add_blockref(name, ins, dxfattribs={"layer": layer})
        if any(True for _ in blk.attdefs()):
            ref.add_auto_attribs({})
    return fill


def furniture_zone(doc, x0, y0):
    """Real-size blocks: sanitary fixtures, furniture, plan doors, stair, table, lights."""
    g = Grid(doc, x0, y0, 0.04)
    g.heading("ΕΠΙΠΛΑ, ΕΙΔΗ ΥΓΙΕΙΝΗΣ, ΠΟΡΤΕΣ ΚΑΙ ΣΚΑΛΑ ΣΕ ΚΑΤΟΨΗ (1 μονάδα = 1 m)",
              "Blocks σε πραγματικό μέγεθος. Σημείο εισαγωγής: η μέση του τοίχου όπου ακουμπάνε.")
    g.heading("Είδη υγιεινής - τυπώνονται γαλάζια (χρώμα 141), όπως στις κατόψεις",
              "Layer: Τουαλέτα - Εξαρτήματα. Το χρώμα είναι μέσα στο block, δεν αλλάζει με το layer.")
    g.rows([(f"{n}\n{t}", centred_block(doc, n, "Τουαλέτα - Εξαρτήματα")) for n, _, t in F.SANITARY], 2.3, 1.6, 4)
    g.heading("Κρεβάτια και καρέκλες - layer Έπιπλα")
    chairs = [("KAREKLA\nΚαρέκλα τραπεζαρίας", centred_block(doc, "KAREKLA", "Έπιπλα")),
              ("KAREKLA_T\nΚαρέκλα τετράγωνη", centred_block(doc, "KAREKLA_T", "Έπιπλα"))]
    beds = [(f"{n}\n{t}", centred_block(doc, n, "Έπιπλα")) for n, _, t in F.FURNITURE]
    g.rows(beds[:4], 2.3, 2.6, 4)
    g.rows(beds[4:] + chairs, 2.3, 1.2, 4)
    g.heading("Τραπεζαρίες - εντολή KTRAP για άλλο μέγεθος (καρέκλες ανά 60 εκ.)")
    g.rows([(n, centred_block(doc, n, "Έπιπλα")) for n in ("TRAP_1800_900", "TRAP_2400_1000", "TRAP_1200_800_X")],
           3.0, 2.4, 3)
    g.heading("Πόρτες σε κάτοψη - εντολή KPORTAK. Σκάλα - εντολή KSKALA",
              "_M: η κάσα στη μέση του τοίχου, ο μεντεσές πιο μέσα από τη γωνία. PK2: δίφυλλη.")
    g.rows([(f"{n}\n{t}", centred_block(doc, n, "Πόρτες")) for n, t in (
        ("PK1_900_250_A", "κάσα στην άκρη"), ("PK1_900_250_A_M", "κάσα στη μέση"), ("PK2_1400_250_M", "δίφυλλη, στη μέση"))],
        2.3, 1.9, 3)
    g.rows([("SK_1000_16_280\n16 ρίχτια x 17.5, πάτημα 28, γραμμή ανάβασης",
             centred_block(doc, "SK_1000_16_280", "Σκάλες"))], 7.1, 1.7, 1)
    g.heading("Φωτισμός - εντολές KRAGA (ράγα με spot) και KLED (λεντοταινία)")
    g.rows([(n, centred_block(doc, n, "Φωτισμός")) for n in ("RAGA_2400_3", "LED_2000_50")], 3.5, 0.8, 2)
    return (x0 - 0.3, g.y, g.right + 0.3, y0 + 0.3)


ROOMS = ["ΚΑΘΙΣΤΙΚΟ", "ΣΑΛΟΝΙ", "ΚΟΥΖΙΝΑ", "ΤΡΑΠΕΖΑΡΙΑ", "ΥΠΝΟΔΩΜΑΤΙΟ", "ΚΥΡΙΟ ΥΠΝΟΔΩΜΑΤΙΟ",
         "ΠΑΙΔΙΚΟ ΔΩΜΑΤΙΟ", "ΜΠΑΝΙΟ", "WC", "ΝΤΟΥΣ", "ΧΟΛ", "ΕΙΣΟΔΟΣ", "ΔΙΑΔΡΟΜΟΣ", "ΓΡΑΦΕΙΟ",
         "ΑΠΟΘΗΚΗ", "ΠΛΥΝΤΗΡΙΟ", "ΙΜΑΤΙΟΘΗΚΗ", "ΚΛΙΜΑΚΟΣΤΑΣΙΟ", "ΒΕΡΑΝΤΑ", "ΑΥΛΗ", "ΣΤΑΘΜΕΥΣΗ",
         "ΛΕΒΗΤΟΣΤΑΣΙΟ"]
ROOM_H = 3.0                 # cap height on paper, mm, at every scale
TEXT_SCALES = {"25": 0.025, "50": 0.05, "100": 0.1, "200": 0.2}
FLOOR_TEXTS = ["ΜΑΡΜΑΡΟΠΟΔΙΑ", "ΜΑΡΜΑΡΟΠΟΔΙΕΣ", "ΠΑΤΗΜΑ", "ΣΚΑΛΟΠΑΤΙ", "00.00 ΤΜ"]
HEIGHT_TEXTS = ["H=0.30m.", "H=0.40m.", "H=0.60m.", "H=1.10m.", "H=1.20m.", "H=1.80m.", "H=2.10m.", "H=2.20m."]


def lisp_hatches(doc, jobs):
    """Runs the KIT.lsp hatch commands on rectangles and copies the result.
    jobs: (x, y, w, h, command, answers before the pick, answers after)."""
    it = Interp()
    it.run((ROOT / "lisp" / "KIT.lsp").read_text(encoding="ascii"))
    msp = doc.modelspace()
    for x, y, w, h, cmd, before, after in jobs:
        start = len(it.entities)
        pl = it.add_pline([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
        it.inputs = list(before) + [pl, None] + list(after)
        it.run(f"(c:{cmd})")
        for ent in it.entities[start:]:
            copy_entity(msp, ent, "Γεμίσματα")
        if cmd != "KOROFI":            # KOROFI draws its own coloured outline
            msp.add_lwpolyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], close=True,
                               dxfattribs={"layer": "Γεμίσματα", "color": 252})


def copy_entity(msp, ent, layer):
    codes = ent["codes"]
    first = {}
    for c, v in codes:
        first.setdefault(c, v)
    if ent["type"] == "LWPOLYLINE":
        pts = [v for c, v in codes if c == 10]
        a = {"layer": layer, "color": first[62], "lineweight": first[370]}
        pl = msp.add_lwpolyline(pts, close=bool(first[70] & 1), dxfattribs=a)
        if 420 in first:
            pl.dxf.true_color = first[420]
        return
    if ent["type"] != "HATCH":
        raise ValueError(f"palette: entity {ent['type']} is not copied")
    seq = list(codes)
    i93 = next(i for i, (c, _) in enumerate(seq) if c == 93)
    i97 = next(i for i, (c, _) in enumerate(seq) if c == 97)
    verts = []
    for c, v in seq[i93 + 1:i97]:
        if c == 10:
            verts.append([v[0], v[1], 0.0])
        elif c == 42:
            verts[-1][2] = v
    h = msp.add_hatch(color=first[62], dxfattribs={"layer": layer})
    h.paths.add_polyline_path([tuple(v) for v in verts], is_closed=True)
    if first[70] == 1:
        h.set_solid_fill(color=first[62])
    else:
        lines, cur = [], None
        for c, v in seq[i97:]:
            if c == 53:                             # radians in AutoLISP, degrees in ezdxf
                cur = [math.degrees(v), [0, 0], [0, 0], []]
                lines.append(cur)
            elif cur is not None and c == 43:
                cur[1][0] = v
            elif cur is not None and c == 44:
                cur[1][1] = v
            elif cur is not None and c == 45:
                cur[2][0] = v
            elif cur is not None and c == 46:
                cur[2][1] = v
            elif cur is not None and c == 49:
                cur[3].append(v)
            elif c == 98:
                break
        h.set_pattern_fill(first[2], color=first[62], pattern_type=2, definition=lines)
    if 420 in first:
        h.dxf.true_color = first[420]


def palette_zone(doc, x0, y0):
    """Loose objects to copy or to take with MATCHPROP: room names per scale,
    texts of the flooring sheet, heights, dimensions, skirting lines, hatches."""
    msp = doc.modelspace()
    g = Grid(doc, x0, y0, 0.05)
    g.heading("ΠΡΟΤΥΠΑ: ΚΕΙΜΕΝΑ, ΔΙΑΣΤΑΣΕΙΣ, ΣΟΒΑΤΕΠΙΑ, HATCH",
              "Χαλαρά αντικείμενα, όχι blocks: Ctrl+C / Ctrl+V, ή MATCHPROP από εδώ πάνω στα δικά σου.")
    for suffix, k in TEXT_SCALES.items():
        text(msp, f"Χώροι 1:{suffix}  (layer Χώροι, γράμματα {ROOM_H:g} mm στο χαρτί)", x0, g.y - 3 * 0.05, 3 * 0.05, "KIT-B")
        g.y -= 8 * 0.05
        cw, ch, cols = 52 * k, 14 * k, 6
        for i, room in enumerate(ROOMS):
            cx = x0 + (i % cols) * cw + cw / 2
            cy = g.y - (i // cols) * ch
            text(msp, room, cx, cy - ROOM_H * k, ROOM_H * k, layer="Χώροι", align="C")
            text(msp, "H = 2.50m", cx, cy - (2 * ROOM_H + 2.0) * k, ROOM_H * k, layer="Χώροι", align="C")
        g.right = max(g.right, x0 + cols * cw)
        g.y -= ((len(ROOMS) + cols - 1) // cols) * ch + 4 * k
        if suffix in ("25", "50"):
            x = x0
            for s in FLOOR_TEXTS:
                text(msp, s, x, g.y - 2.4 * k, 2.4 * k, layer="Χώροι")
                x += text_width(s, 2.4) * k + 10 * k
            g.y -= 10 * k
        if suffix != "200":
            x = x0
            for s in HEIGHT_TEXTS:
                text(msp, s, x, g.y - 1.7 * k, 1.7 * k, "KIT-B", layer="Ετικέτες", color=1)
                x += text_width(s, 1.7, "KIT-B") * k + 8 * k
            g.y -= 10 * k
        g.y -= 1.0
    # dimensions
    text(msp, "Διαστάσεις σε εκατοστά, όπως στο σχέδιο δαπεδόστρωσης. Dimension styles KIT_25, KIT_50, "
              "και κόκκινες για τον φωτισμό KIT_FOT_25, KIT_FOT_50.", x0, g.y - 0.15, 0.15, "KIT-B")
    g.y -= 0.8
    x = x0
    for suffix, k in DIM_SCALES.items():
        for prefix, layer in (("KIT_", "Διαστάσεις"), ("KIT_FOT_", "Φωτισμός")):
            name = f"{prefix}{suffix}"
            text(msp, name, x, g.y - 0.12, 0.12)
            dim = msp.add_linear_dim(base=(x, g.y - 0.5), p1=(x, g.y - 1.0), p2=(x + 2.0, g.y - 1.0),
                                     dimstyle=name, dxfattribs={"layer": layer})
            dim.render()
            x += 3.0
    g.y -= 1.8
    # skirting and connection lines
    text(msp, "Σοβατεπί: σχεδίασε γραμμή στο layer Σοβατεπί TL-01 ή TL-07, ή MATCHPROP από εδώ.  "
              "Σύνδεση φωτιστικών: εντολή KSYND.", x0, g.y - 0.15, 0.15, "KIT-B")
    g.y -= 0.7
    for i, (layer, label) in enumerate((("Σοβατεπί TL-01", "TL-01 ΣΟΒΑΤΕΠΙ"), ("Σοβατεπί TL-07", "TL-07 ΕΠΕΝΔΥΣΗ WC"))):
        x = x0 + i * 4.0
        msp.add_lwpolyline([(x, g.y - 0.3), (x + 3.0, g.y - 0.3)], dxfattribs={"layer": layer})
        text(msp, label, x, g.y - 0.65, 0.12)
    x = x0 + 8.0
    syn = msp.add_lwpolyline([(x, g.y - 0.3), (x + 3.0, g.y - 0.3)],
                             dxfattribs={"layer": "Φωτισμός", "color": 1, "linetype": "KIT_SYND"})
    syn.dxf.ltscale = 0.05
    text(msp, "ΣΥΝΔΕΣΗ ΦΩΤΙΣΤΙΚΩΝ (1:50)", x, g.y - 0.65, 0.12)
    g.y -= 1.4
    # hatches
    text(msp, "Hatch: εντολές KDAP (δάπεδα), KXYLO (ξύλο), KOROFI (ανόψεις). Εδώ δείγματα, και για MATCHPROP.",
         x0, g.y - 0.15, 0.15, "KIT-B")
    g.y -= 0.6
    jobs, labels = [], []
    floor = [("Plakaki", [None, 1.0, 1.0], "ΠΛΑΚΑΚΙ 100x100 (KDAP)"), ("TL01", ["TL01"], "TL-01 120x120"),
             ("TL07", ["TL07"], "TL-07 150x75"), ("CN01", ["CN01"], "CN-01 ΤΣΙΜΕΝΤΟΚΟΝΙΑ"),
             ("WD06", ["WD06"], "WD-06 DECK")]
    y = g.y - 2.6
    for i, (_, before, label) in enumerate(floor):
        jobs.append((x0 + i * 3.4, y, 3.0, 2.4, "KDAP", before, [None]))
        labels.append((x0 + i * 3.4, y - 0.25, label))
    jobs.append((x0 + 5 * 3.4, y, 1.2, 2.4, "KXYLO", [], [None]))
    labels.append((x0 + 5 * 3.4, y - 0.25, "ΞΥΛΟ (KXYLO)"))
    y2 = y - 3.2
    for i, key in enumerate(["H220", "H225", "H240", "H245", "EPIKL", "H275"]):
        jobs.append((x0 + i * 3.4, y2, 3.0, 2.0, "KOROFI", [key], []))
        labels.append((x0 + i * 3.4, y2 - 0.25, f"ΑΝΟΨΗ {key}"))
    lisp_hatches(doc, jobs)
    for x, yy, s in labels:
        text(msp, s, x, yy, 0.12)
    g.y = y2 - 0.8
    g.right = max(g.right, x0 + 6 * 3.4)
    return (x0 - 0.3, g.y, g.right + 0.3, y0 + 0.3)


def build():
    OUT.mkdir(exist_ok=True)
    (OUT / "ctb").mkdir(exist_ok=True)
    doc = new_doc()
    lisp_blocks(doc)
    build_furniture(doc)
    build_annotation(doc)
    zones = library(doc)
    doc.set_modelspace_vport(height=40, center=(20, -15))
    doc.saveas(OUT / "KIT.dxf")
    for scale in SCALES:
        write_ctb(scale, OUT / "ctb" / f"KIT-{scale}.ctb")
    return doc, zones


if __name__ == "__main__":
    doc, zones = build()
    names = [b.name for b in doc.blocks if not b.name.startswith("*")]
    print(f"blocks: {len(names)}  layers: {len(doc.layers)}  zones: { {k: tuple(round(v, 1) for v in z) for k, z in zones.items()} }")
