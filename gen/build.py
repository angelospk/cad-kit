"""Builds the CAD kit: out/KIT.dxf, out/ctb/KIT-*.ctb.

Run from the project root:  python gen/build.py
Then gen/convert.sh turns the DXF into a DWG with the ODA File Converter.
"""
from __future__ import annotations

import io
import pathlib
import struct
import zlib

import ezdxf
from ezdxf import bbox
from ezdxf.addons import acadctb

import symbols as S
from draw import B, STYLES
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
]
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
OWN_COLOUR_PENS = {141: 0.18}              # plot in the object colour


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
    for name, (font, family, bold) in STYLES.items():
        style = doc.styles.add(name, font=font)
        style.set_extended_font_data(family, bold=bold)
    for name, color, lw, ltype in HER_LAYERS + KIT_LAYERS:
        doc.layers.add(name, color=color, lineweight=lw, linetype=ltype or "Continuous")
    doc.layers.add(INFO_LAYER, color=140, plot=False)
    return doc


def new_block(doc, name):
    blk = doc.blocks.new(name)
    blk.block_record.dxf.units = 0
    return blk


# ---------------------------------------------------------------- blocks from KIT.lsp

LISP_SAMPLES = [   # block name, lisp call, layer in the library
    ("SYR2_2000_250", '(kit:def-syr "SYR2_2000_250" 2.0 2 0.25)', "Παράθυρα"),
    ("SYR2_3000_250", '(kit:def-syr "SYR2_3000_250" 3.0 2 0.25)', "Παράθυρα"),
    ("SYR3_3600_250", '(kit:def-syr "SYR3_3600_250" 3.6 3 0.25)', "Παράθυρα"),
    ("SYR4_4000_250", '(kit:def-syr "SYR4_4000_250" 4.0 4 0.25)', "Παράθυρα"),
    ("SYRM3_3000_250", '(kit:def-syrm "SYRM3_3000_250" 3.0 3 0.25 nil)', "Παράθυρα"),
    ("SYRX1_1000_250", '(kit:def-syrm "SYRX1_1000_250" 1.0 1 0.25 T)', "Πόρτες"),
    ("SYRX2_2000_250", '(kit:def-syrm "SYRX2_2000_250" 2.0 2 0.25 T)', "Παράθυρα"),
    ("PAR_600_250", '(kit:def-par "PAR_600_250" 0.6 0.25)', "Παράθυρα"),
    ("PAR_1200_250", '(kit:def-par "PAR_1200_250" 1.2 0.25)', "Παράθυρα"),
    ("POR_800_2200_A", '(kit:def-porta "POR_800_2200_A" 0.8 2.2 nil)', "Πόρτες"),
    ("POR_900_2200_D", '(kit:def-porta "POR_900_2200_D" 0.9 2.2 T)', "Πόρτες"),
    ("PSEYD_3000_300", '(kit:def-pseyd "PSEYD_3000_300" 3.0 0.3)', "Ψευδοροφή"),
]


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

    def __init__(self, doc, x0, y0, k):
        self.doc, self.msp = doc, doc.modelspace()
        self.x0, self.y, self.k = x0, y0, k
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
    f.note("Κύριες γραμμές ByLayer: το block παίρνει το χρώμα του layer όπου μπαίνει.")
    rows = [LISP_SAMPLES[0:4], LISP_SAMPLES[4:9], LISP_SAMPLES[9:12]]
    for row in rows:
        f.newline()
        for name, _, layer in row:
            f.put(name, layer, gap=16)
    f.newline()
    zones["R"] = (-0.5, f.y, max(f.width, 14.0) + 0.5, 0.5)

    x = zones["R"][2] + 3.0
    for suffix, k in SCALES.items():
        f = Flow(doc, x, 0.0, k)
        f.heading(f"ΚΛΙΜΑΚΑ 1:{suffix}  -  blocks με κατάληξη _{suffix}", 7.0)
        f.note("Μπαίνουν όπως είναι (scale 1) σε σχέδιο που τυπώνεται σε αυτή την κλίμακα.")
        for group, title in (("tags", "Ετικέτες και σύμβολα (layer Ετικέτες)"),
                             ("power", "Ρεύματα σε κάτοψη (layer Ηλεκτρολογικά, τυπώνεται κόκκινο)"),
                             ("plates", "Ρεύματα σε ανάπτυγμα (layer Ηλεκτρολογικά)"),
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
    return zones


def build():
    OUT.mkdir(exist_ok=True)
    (OUT / "ctb").mkdir(exist_ok=True)
    doc = new_doc()
    lisp_blocks(doc)
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
