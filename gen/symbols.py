"""Annotation symbols, legends, title block. All sizes in paper millimetres.

Every function draws into a draw.B helper. Lines are ByLayer unless a colour
is given: a block then takes the colour (and the plotted pen) of the layer it
is inserted on. Inside the legends the electrical symbols get colour 1 (red).
"""
from __future__ import annotations

import math

from draw import B, text_width

RED = 1          # electrical: plots red
THIN = 252       # thin lines: 0.09 at 1:50
RULE = 62        # title block rules: 0.25, same at every scale
WOOD = (205, 186, 165)
GRAIN = (150, 104, 64)
INSUL = (248, 246, 176)
SKIRTING = {"TL-01": (255, 127, 0), "TL-07": (255, 191, 0)}   # = ACI 30, 40: layer colours too
TXT = 1.7        # legend body text
D45 = math.sqrt(0.5)


# ------------------------------------------------------------------ tags

def tag(b: B, att=True, kod="PF", ar="02", k1="COUNTER", k2="TAP"):
    """Two-cell code box with a two-line label. Insertion: lower-left of the box."""
    b.rect(0, 0, 5.6, 5.4)
    b.line(0, 2.7, 5.6, 2.7)
    b.label("ΚΩΔΙΚΟΣ", kod, 2.8, 4.05, 1.5, align="MC", att=att)
    b.label("ΑΡΙΘΜΟΣ", ar, 2.8, 1.35, 1.5, align="MC", att=att)
    b.label("ΚΕΙΜΕΝΟ1", k1, 6.5, 3.3, 1.5, att=att)
    b.label("ΚΕΙΜΕΝΟ2", k2, 6.5, 0.6, 1.5, att=att)


def finishes(b: B, att=True):
    """Room finishes box: ceiling material / floor material."""
    b.rect(0, 0, 26, 10)
    b.line(5, 0, 5, 10)
    b.line(0, 5, 26, 5)
    b.text("Ο", 2.5, 7.5, 1.8, "KIT-B", "MC")
    b.text("Δ", 2.5, 2.5, 1.8, "KIT-B", "MC")
    b.label("ΟΡΟΦΗ", "ΥΛΙΚΟ ΟΡΟΦΗΣ", 6.4, 7.5, 1.6, align="ML", att=att)
    b.label("ΔΑΠΕΔΟ", "ΥΛΙΚΟ ΔΑΠΕΔΟΥ", 6.4, 2.5, 1.6, align="ML", att=att)


def opening_tag(b: B, att=True):
    """Exterior opening: number | width / sill | lintel."""
    b.rect(0, 0, 19.6, 7.8)
    b.line(7.4, 0, 7.4, 7.8)
    b.line(7.4, 3.9, 19.6, 3.9)
    b.line(13.5, 0, 13.5, 3.9)
    b.label("ΑΡΙΘΜΟΣ", "No" if not att else "W01", 3.7, 3.9, 1.9, "KIT-B", "MC", att=att)
    b.label("ΠΛΑΤΟΣ", "ΠΛΑΤΟΣ" if not att else "1.20", 13.5, 5.85, 1.5, align="MC", att=att)
    h = 1.5 if att else 1.1           # the words are wider than the numbers
    b.label("ΠΟΔΙΑ", "ΠΟΔΙΑ" if not att else "0.90", 10.45, 1.95, h, align="MC", att=att)
    b.label("ΠΡΕΚΙ", "ΠΡΕΚΙ" if not att else "2.20", 16.55, 1.95, h, align="MC", att=att)


def door_tag(b: B, att=True):
    """Interior door: number over a circle with width / lintel. Insertion: circle centre."""
    b.circle(0, 0, 4.1)
    b.line(-4.1, 0, 4.1, 0)
    b.label("ΑΡΙΘΜΟΣ", "No" if not att else "D01", 0, 5.2, 1.9, "KIT-B", "C", att=att)
    h = 1.5 if att else 1.05          # the words are wider than the numbers
    b.label("ΠΛΑΤΟΣ", "ΠΛΑΤΟΣ" if not att else "0.90", 0, 1.9, h, align="MC", att=att)
    b.label("ΠΡΕΚΙ", "ΠΡΕΚΙ" if not att else "2.20", 0, -1.9, h, align="MC", att=att)


LEVEL_LABELS = {
    "floor": (("ΔΑΠΕΔΟ", "ΣΤ. ΔΑΠ. = +0.00", "ΣΤΑΘΜΗ ΔΑΠΕΔΟΥ"), ("ΜΠΕΤΟΝ", "ΣΤ. ΜΠ. = -0.10", "ΣΤΑΘΜΗ ΜΠΕΤΟΥ")),
    "ground": (("ΔΙΑΜΟΡΦΩΜΕΝΟ", "ΣΤ. ΔΙΑΜ. ΕΔΑΦΟΥΣ = +0.00", "ΣΤ. ΔΙΑΜΟΡΦΩΜΕΝΟΥ ΕΔΑΦΟΥΣ"),
               ("ΦΥΣΙΚΟ", "ΣΤ. ΦΥΣ. ΕΔΑΦΟΥΣ = +0.00", "ΣΤ. ΦΥΣΙΚΟΥ ΕΔΑΦΟΥΣ")),
}


def level(b: B, att=True, two=True, kind="floor"):
    """Level mark. two=True: two levels (floor / concrete, or formed / natural ground)."""
    b.circle(0, 0, 1.3)
    b.sector(0, 0, 1.3, 90, 180)
    b.sector(0, 0, 1.3, 270, 360)
    if two:
        rows = LEVEL_LABELS[kind]
        texts = [r[1] if att else r[2] for r in rows]
        end = max(24.0, 2.4 + max(text_width(t, 1.7) for t in texts) + 1.5)
        b.line(-3.6, 0, end, 0)
        for (tag_, _, _), t, y in zip(rows, texts, (0.9, -2.7)):
            b.label(tag_, t, 2.4, y, 1.7, att=att)
    else:
        b.line(-3.6, 0, 14, 0)
        b.label("ΣΤΑΘΜΗ", "+0.00", 2.4, 0.9, 1.7, att=att)
    b.line(0, -3.8, 0, 3.8)


def elevation_ref(b: B, att=True):
    """Reference to the interior elevations: sheet number and views 01-04."""
    d = 2.9
    h = b._hatch({})
    h.dxf.hatch_style = 0
    h.paths.add_polyline_path([b.P(d, 0), b.P(0, d), b.P(-d, 0), b.P(0, -d)], is_closed=True, flags=1)
    (x1, y1), (x2, y2) = b.P(-1.9, 0), b.P(1.9, 0)
    h.paths.add_polyline_path([(x1, y1, 1), (x2, y2, 1)], is_closed=True, flags=16)
    b.poly([(d, 0), (0, d), (-d, 0), (0, -d)], close=True)
    b.circle(0, 0, 1.9)
    b.label("ΣΧΕΔΙΟ", "827", 0, 0, 1.1, align="MC", att=att)
    for s, x, y in (("01", 0, -4.3), ("02", 4.7, 0), ("03", 0, 4.3), ("04", -4.7, 0)):
        b.text(s, x, y, 0.95, align="MC")


def detail_ref(b: B, att=True):
    """Reference to a detail drawing."""
    b.circle(0, 0, 2.3)
    b.line(-2.3, 0, 2.3, 0)
    b.label("ΣΧΕΔΙΟ", "1305", 0, 1.0, 0.95, align="MC", att=att)
    b.text("DTL", 0, -1.0, 0.95, align="MC")
    b.line(2.3, 0, 5.2, 0)
    b.rrect(5.2, -3.3, 9.2, 3.3, 1.3)


def origin(b: B):
    """Tiling / setting-out origin point. Always red."""
    b = b.at(0, 0, color=RED)
    b.circle(0, 0, 1.7)
    b.line(-2.4, 0, 2.4, 0)
    b.line(0, -2.4, 0, 2.4)
    b.text("ORIGIN", 2.8, 4.4, 1.7)
    b.text("POINT", 2.8, 1.6, 1.7)


# ------------------------------------------------------------------ electrical, plan

def el_switch(b: B, two_way=False):
    """Switch. Insertion: centre of the circle."""
    r, e = 1.3, 1.3 * D45 + 2.6
    b.circle(0, 0, r)
    b.line(r * D45, r * D45, e, e)
    b.line(e, e, e + 0.9, e - 0.9)
    if two_way:
        b.line(-r * D45, -r * D45, -e, -e)
        b.line(-e, -e, -e - 0.9, -e + 0.9)


def el_socket(b: B, waterproof=False):
    """Socket. Insertion: the wall end of the stem. Points to +X."""
    b.line(0, 0, 5.6, 0)
    b.arc(8.0, 0, 2.4, 90, 270)
    if waterproof:
        b.sector(8.0, 0, 2.4, 90, 270)
        b.line(8.0, -2.4, 8.0, 2.4)


def el_outlet(b: B, label):
    """TV / data / phone / cooker / dishwasher / washing machine outlet."""
    b.line(0, 0, 3.6, 0)
    b.poly([(7.2, 2.7), (3.6, 2.7), (3.6, -2.7), (7.2, -2.7)])
    b.text(label, 9.4, 0, 2.2, align="MC", rot=-90)


EL_OUTLETS = {"TV": "Πρίζα TV", "D": "Πρίζα δικτύου", "TL": "Παροχή τηλεφώνου",
              "K": "Πρίζα ηλ. κουζίνας", "DW": "Πρίζα πλυντηρίου πιάτων",
              "W": "Πρίζα πλυντηρίου ρούχων"}


DIRS = {"R": (1, 0), "L": (-1, 0), "U": (0, 1), "D": (0, -1)}


def height_arrow(b: B, d: str, n: int):
    """Arrow to the wall with n points and their heights, as in the socket plans.

    Insertion: the arrow tip, on the wall. d = side of the wall: R, L, U, D.
    The line runs away from the wall. Heights are red attributes.
    """
    ux, uy = DIRS[d]
    px, py = -uy, ux                            # perpendicular
    first, pitch = 7.0, 6.0
    end = first + pitch * (n - 1) + 4.0
    b.line(0, 0, -ux * end, -uy * end, color=8)
    bx, by = -ux * 3.2, -uy * 3.2
    b.fill([(0, 0), (bx + px * 1.5, by + py * 1.5), (bx - px * 1.5, by - py * 1.5)], color=8)
    for i in range(n):
        cx, cy = -ux * (first + pitch * i), -uy * (first + pitch * i)
        b.disc(cx, cy, 0.45, color=8)
        if uy == 0:
            b.att(f"ΥΨΟΣ{i + 1}", "0.60", cx, cy + 1.3, 1.6, align="C", color=RED)
        else:
            b.att(f"ΥΨΟΣ{i + 1}", "0.60", cx - 1.3, cy, 1.6, align="MR", color=RED)


# ------------------------------------------------------------------ electrical, elevation

def pl_plate(b: B, kind, label=None):
    """Wall plate in an interior elevation. Insertion: centre."""
    b.rect(-2.9, -2.9, 2.9, 2.9)
    b.rect(-2.3, -2.3, 2.3, 2.3)
    if kind == "2":
        b.line(0, -2.3, 0, 2.3)
    elif kind == "S":
        b.circle(0, 0, 1.4)
    elif kind == "TV":
        b.circle(0, 0, 0.5)
    if label:
        b.text(label, 0, -4.6, 1.9, align="MC")


def pl_data(b: B, label):
    b.rect(-1.3, -2.5, 1.3, 2.5)
    b.rect(-0.8, -0.3, 0.8, 0.9)
    b.text(label, 0, -4.2, 1.9, align="MC")


# ------------------------------------------------------------------ lighting

def lt_spot(b: B, small=False):
    r1, r2, r3 = (1.0, 0.7, 0.42) if small else (1.9, 1.5, 1.0)
    b.circle(0, 0, r1)
    b.circle(0, 0, r2)
    b.disc(0, 0, r3)


def lt_cross(b: B, r):
    d = r * 0.52
    b.line(-d, -d, d, d)
    b.line(-d, d, d, -d)


def lt_floor(b: B):
    b.circle(0, 0, 3.0)
    lt_cross(b, 3.0)


def lt_table(b: B):
    b.circle(0, 0, 3.0, linetype="KIT_DASH", ltscale=12 * b.k)
    lt_cross(b, 3.0)


def lt_wall(b: B):
    """Wall light. Insertion: on the wall line."""
    b.line(-3.8, 0, 3.8, 0)
    b.arc(0, 0, 3.0, 0, 180)
    b.arc(0, 0, 2.1, 0, 180)
    b.line(0, 0, 0, 3.9)


def lt_ceiling(b: B):
    b.circle(0, 0, 2.2)
    b.circle(0, 0, 1.4)
    b.line(-3.0, 0, 3.0, 0)
    b.line(0, -3.0, 0, 3.0)


def lt_supply(b: B):
    """Provision for a supply point on a wall."""
    b.line(-2.1, -2.1, 2.1, 2.1)
    b.line(-2.1, 2.1, 2.1, -2.1)
    b.line(0, 0, 0, 2.9)


def lt_led(b: B):
    """LED tape as in the reference legend: thick dash, three thin ticks. Same as KLED."""
    x = -8.0
    while x < 8.0:
        xe = min(x + 4.0, 8.0)
        b.fill([(x, -0.3), (xe, -0.3), (xe, 0.3), (x, 0.3)])
        for k in (1, 2, 3):
            if xe + 0.75 * k < 8.0:
                b.line(xe + 0.75 * k, -0.21, xe + 0.75 * k, 0.21, lineweight=9)
        x = xe + 3.0


def lt_panel(b: B):
    b.rect(-8, -2.2, 8, 2.2)
    b.rect(-7.3, -1.5, 7.3, 1.5)
    b.fill([(-7.3, -1.5), (7.3, -1.5), (7.3, 1.5)])


def lt_track(b: B):
    b.fill([(-8.5, -0.4), (8.5, -0.4), (8.5, 0.4), (-8.5, 0.4)])
    lt_spot(b.at(-4.5, 0))
    lt_spot(b.at(4.5, 0), small=True)


LIGHTS = [
    ("FO_SPOT", lt_spot, "ΧΩΝΕΥΤΟ SPOT ΟΡΟΦΗΣ"),
    ("FO_SPOT_M", lambda b: lt_spot(b, small=True), "ΧΩΝΕΥΤΟ SPOT ΟΡΟΦΗΣ ΜΙΚΡΟ"),
    ("FO_EPIDAP", lt_floor, "ΕΠΙΔΑΠΕΔΙΟ ΦΩΤΙΣΤΙΚΟ"),
    ("FO_EPITOIX", lt_wall, "ΕΠΙΤΟΙΧΙΟ ΦΩΤΙΣΤΙΚΟ"),
    ("FO_EPITRAP", lt_table, "ΕΠΙΤΡΑΠΕΖΙΟ ΦΩΤΙΣΤΙΚΟ"),
    ("FO_OROFIS", lt_ceiling, "ΦΩΤΙΣΤΙΚΟ ΟΡΟΦΗΣ"),
    ("FO_PAROXI", lt_supply, "ΠΡΟΒΛΕΨΗ ΠΑΡΟΧΗΣ ΣΕ ΤΟΙΧΟ"),
    ("FO_LED", lt_led, "ΛΕΝΤΟΤΑΙΝΙΑ (εντολή KLED)"),
    ("FO_PINAKAS", lt_panel, "ΗΛΕΚΤΡΟΛΟΓΙΚΟΣ ΠΙΝΑΚΑΣ"),
    ("FO_RAGA", lt_track, "ΡΑΓΑ ΜΕ ΧΩΝΕΥΤΑ ΚΑΙ ΕΞΩΤΕΡΙΚΑ SPOT (KRAGA)"),
]


# ------------------------------------------------------------------ legends

def panel(b: B, title: str, w: float, h: float) -> B:
    """Legend frame. Insertion: top-left. Returns the body origin (top-left of the body)."""
    b.rrect(0, -10.6, w, 0, 4.6)
    b.underlined(title, w / 2, -6.5, 2.6)
    b.rect(0, -14.2 - h, w, -14.2)
    body = b.at(0, -14.2)
    body.w = w
    return body


def say(b: B, lines, x, y, h=TXT, style="KIT", pitch=None):
    """Lines of text, first baseline at y. Fails when a line leaves the frame."""
    pitch = pitch or h * 1.6
    for i, s in enumerate(lines):
        if x + text_width(s, h, style) > b.w - 2.5:
            raise ValueError(f"legend text too long: {s!r}")
        b.text(s, x, y - i * pitch, h, style)


def notes(b: B, y, lines):
    b.line(0, y, b.w, y)
    say(b, ["Σημειώσεις:"], 6, y - 5.4, 2.3, "KIT-B")
    say(b, lines, 9, y - 10.4, 1.5, "KIT")


def legend_symbols(b: B):
    p = panel(b, "ΥΠΟΜΝΗΜΑ ΣΥΜΒΟΛΩΝ", 98, 88)
    x = 38
    finishes(p.at(8, -13), att=False)
    say(p, ["ΠΙΝΑΚΑΣ ΤΕΛΕΙΩΜΑΤΩΝ"], x, -8.9)
    opening_tag(p.at(11, -27.5), att=False)
    say(p, ["ΠΙΝΑΚΑΣ ΕΞΩΤΕΡΙΚΩΝ ΑΝΟΙΓΜΑΤΩΝ"], x, -19.6)
    say(p, ["(Ποδιά και πρέκι μετρώνται από το τελικό", "διαμορφωμένο δάπεδο του χώρου", "στον οποίο ανήκουν)"],
        x, -22.6, 1.5)
    door_tag(p.at(21, -42.5), att=False)
    say(p, ["ΠΙΝΑΚΑΣ ΕΣΩΤΕΡΙΚΩΝ ΘΥΡΩΝ"], x, -42.0)
    level(p.at(9, -56), att=False)
    say(p, ["ΣΥΜΒΟΛΟ ΣΤΑΘΜΗΣ"], x, -56.9)
    elevation_ref(p.at(21, -68), att=False)
    say(p, ["ΚΩΔΙΚΟΣ ΑΝΑΦΟΡΑΣ ΓΙΑ ΤΑ ΑΝΑΠΤΥΓΜΑΤΑ", "ΤΩΝ ΕΣΩΤΕΡΙΚΩΝ ΧΩΡΩΝ"], x, -67.4)
    detail_ref(p.at(16, -80), att=False)
    say(p, ["ΚΩΔΙΚΟΣ ΑΝΑΦΟΡΑΣ ΓΙΑ ΤΑ ΣΧΕΔΙΑ", "ΤΩΝ ΛΕΠΤΟΜΕΡΕΙΩΝ"], x, -79.4)


def swatch_concrete(b: B, w, h):
    box = [(0, 0), (w, 0), (w, h), (0, h)]
    b.pattern(box, "ANSI31", 1.0, color=THIN)
    b.pattern(box, "DOTS", 2.2, color=THIN)
    b.rect(0, 0, w, h)


def swatch_brick(b: B, w, h):
    ins = h * 0.28
    box = [(0, 0), (w, 0), (w, ins), (0, ins)]
    b.fill(box, rgb=INSUL)
    b.pattern(box, "ANSI37", 0.8, color=THIN)
    b.line(0, ins, w, ins)
    mid = ins + (h - ins) / 2
    b.line(0, mid, w, mid, color=THIN)
    for f in (0.33, 0.66):
        b.line(w * f, mid, w * f, h, color=THIN)
    b.line(w * 0.5, ins, w * 0.5, mid, color=THIN)
    b.rect(0, 0, w, h)


def swatch_stone(b: B, w, h):
    for pts in ([(0, h * 0.45), (w * 0.4, h * 0.5), (w, h * 0.42)],
                [(w * 0.4, h * 0.5), (w * 0.46, h)],
                [(w * 0.62, 0), (w * 0.58, h * 0.44)],
                [(0, h * 0.16), (w * 0.3, h * 0.2), (w * 0.6, h * 0.12)],
                [(w * 0.78, h * 0.43), (w * 0.82, h)]):
        b.poly(pts, color=THIN)
    b.rect(0, 0, w, h)


def swatch_fill(b: B, w, h):
    b.pattern([(0, 0), (w, 0), (w, h), (0, h)], "ANSI31", 0.55, color=THIN)
    b.rect(0, 0, w, h)


def swatch_drywall(b: B, w, h):
    b.rect(0, 0, w, h)
    for f in (0.14, 0.28, 0.72, 0.86):
        b.line(0, h * f, w, h * f, color=THIN)


def swatch_wood(b: B, w, h):
    b.fill([(0, 0), (w, 0), (w, h), (0, h)], rgb=WOOD)
    for f, a, c in ((0.08, 0.1, 0.9), (0.14, 0.0, 0.6), (0.33, 0.3, 1.0), (0.37, 0.0, 0.7),
                    (0.7, 0.2, 1.0), (0.74, 0.0, 0.5), (0.9, 0.4, 1.0)):
        b.line(w * f, h * a, w * f, h * c, rgb=GRAIN, lineweight=5)
    b.rect(0, 0, w, h, color=THIN)


def swatch_dots(b: B, w, h):
    b.pattern([(0, 0), (w, 0), (w, h), (0, h)], "DOTS", 2.8, color=THIN)
    b.rect(0, 0, w, h, color=THIN)


def legend_materials(b: B):
    p = panel(b, "ΥΠΟΜΝΗΜΑ ΥΛΙΚΩΝ", 98, 92)
    sx, tx, w, h = 7, 21, 9.5, 5.0
    say(p, ["Εξωτερικές Τοιχοποιίες και Στοιχεία"], 6, -7.2, 2.3, "KIT-B")
    swatch_concrete(p.at(sx, -17.5), w, h)
    say(p, ["Τοιχεία οπλισμένου σκυροδέματος με εξωτερική", "μόνωση και υγρομόνωση"], tx, -14.0)
    swatch_brick(p.at(sx, -28.5), w, h)
    say(p, ["Τοιχοποιία πλινθοδομής 25εκ", "και εξωτερική μόνωση 10εκ, πάχος 35εκ"], tx, -25.0)
    swatch_stone(p.at(sx, -39.5), w, h)
    say(p, ["Τοιχοποιία από ανεπίχριστη τοπική πέτρα,", "πάχος 50εκ"], tx, -36.0)
    swatch_fill(p.at(sx, -49.5), w, h)
    say(p, ["Πλήρωση εξωτερικής τοιχοποιίας"], tx, -47.9)
    say(p, ["Εσωτερικές Τοιχοποιίες"], 6, -58.2, 2.3, "KIT-B")
    swatch_drywall(p.at(sx, -67.5), w, 2.6)
    say(p, ["Τοιχοποιία ξηράς δόμησης: μονός μεταλλικός", "σκελετός, μόνωση πετροβάμβακα, δύο", "γυψοσανίδες σε κάθε πλευρά, πάχος 10εκ"],
        tx, -63.6)
    notes(p, -75, ["*ΚΑΘΑΡΟ ΥΨΟΣ ΜΕΤΑΞΥ ΠΛΑΚΩΝ ΙΣΟΓΕΙΟΥ: 2,55 μ.", "*ΚΑΘΑΡΟ ΥΨΟΣ ΜΕΤΑΞΥ ΠΛΑΚΩΝ ΟΡΟΦΩΝ: 2,50 μ."])


def swatch_tiles(b: B, w, h):
    b.rect(0, 0, w, h)
    b.line(0, h / 2, w, h / 2, color=THIN)
    for i in range(1, 4):
        b.line(w * i / 4, 0, w * i / 4, h, color=THIN)


def legend_floors(b: B):
    p = panel(b, "ΥΠΟΜΝΗΜΑ ΥΛΙΚΩΝ ΔΑΠΕΔΟΣΤΡΩΣΗΣ", 98, 124)
    sx, tx, w, h = 7, 30, 17, 7

    def row(i, code, lines, draw):
        y = -6 - i * 11.0
        draw(p.at(sx, y - h))
        if code:
            say(p, [code], tx, y - 2.6, 2.3, "KIT-B")
            say(p, lines, tx, y - 5.9, 1.7)
        else:
            say(p, lines, tx, y - 4.2, 1.7)

    def band(rgb):
        def f(q):
            q.rect(0, 0, w, h)
            q.fill([(0, h / 2 - 0.25), (w, h / 2 - 0.25), (w, h / 2 + 0.25), (0, h / 2 + 0.25)], rgb=rgb)
        return f

    def gray(q):
        q.fill([(0, 0), (w, 0), (w, h), (0, h)], rgb=(200, 200, 203))
        q.rect(0, 0, w, h)

    def deck(q):
        q.rect(0, 0, w, h)
        for i in range(1, 10):
            q.line(w * i / 10, 0, w * i / 10, h, color=THIN)

    def drain(q):
        q.rect(0, 0, w, h)
        q.rect(1, h / 2 - 0.9, w - 1, h / 2 + 0.9, color=THIN)
        q.rect(1.4, h / 2 - 0.5, w - 1.4, h / 2 + 0.5, color=THIN)

    tiles = lambda q: swatch_tiles(q, w, h)
    row(0, "TL-01", ["Πλακάκι 120x120, πάχους 0.9cm"], tiles)
    row(1, "TL-02", ["Πλακάκι 120x120, 0.9cm, R10, υγροί χώροι"], tiles)
    row(2, "TL-03", ["Πλακάκι 120x120, πάχους 2cm, R11 antislip"], tiles)
    row(3, "CN-01", ["Τσιμεντοκονία"], gray)
    row(4, "TL-01", ["ΣΟΒΑΤΕΠΙ από το πλακάκι δαπέδου, H=7cm"], band(SKIRTING["TL-01"]))
    row(5, "TL-07", ["Επένδυση τοίχων WC με πλακίδια 150x75cm"], band(SKIRTING["TL-07"]))
    row(6, "MB-02", ["ΜΑΡΜΑΡΟΠΟΔΙΕΣ"], lambda q: q.rect(0, 0, w, h))
    row(7, "WD-06", ["ΔΑΠΕΔΟ DECK ΕΞΩΤΕΡΙΚΟΥ ΧΩΡΟΥ"], deck)
    row(8, None, ["ΓΡΑΜΜΙΚΟ ΣΙΦΩΝΙ ΝΤΟΥΖΙΕΡΑΣ 95εκ."], drain)
    notes(p, -107, ["1. ΣΟΒΑΤΕΠΙ ΜΠΑΙΝΕΙ ΣΕ ΟΛΟΥΣ ΤΟΥΣ ΤΟΙΧΟΥΣ ΕΚΤΟΣ ΑΠΟ ΤΟΥΣ", "    ΤΟΙΧΟΥΣ ΜΕ ΕΠΕΝΔΥΣΗ ΑΔΡΗΣ ΤΕΧΝΟΤΡΟΠΙΑΣ ΣΟΒΑ."])


def legend_lighting(b: B):
    p = panel(b, "ΥΠΟΜΝΗΜΑ ΦΩΤΙΣΜΟΥ", 98, 102)
    for i, (_, draw, text) in enumerate(LIGHTS):
        y = -7.5 - i * 8.6
        draw(p.at(18, y - (1.6 if draw is lt_wall else 0), color=RED))
        say(p, [text], 34, y - 0.95)
    y = -7.5 - len(LIGHTS) * 8.6
    tag(p.at(15.2, y - 2.7, color=RED), att=False, kod="LG", ar="XX", k1="", k2="")
    say(p, ["ΠΙΝΑΚΑΣ ΦΩΤΙΣΤΙΚΟΥ ΣΩΜΑΤΟΣ"], 34, y - 0.95)


def legend_power(b: B):
    p = panel(b, "ΥΠΟΜΝΗΜΑ ΙΣΧ. & ΑΣΘ. ΡΕΥΜΑΤΩΝ", 98, 106)
    say(p, ["ΚΑΤΟΨΗ"], 5, -5.2, 1.5, "KIT-B")
    say(p, ["ΑΝΑΠΤΥΓΜΑ"], 53, -5.2, 1.5, "KIT-B")
    left = [(lambda q: el_switch(q), "Διακόπτης μονός", 4),
            (lambda q: el_switch(q, True), "Διακόπτης αλέ ρετούρ", 4),
            (lambda q: el_socket(q), "Πρίζα", 0),
            (lambda q: el_socket(q, True), "Πρίζα στεγανή", 0)]
    left += [((lambda lab: (lambda q: el_outlet(q, lab)))(lab), text, 0) for lab, text in EL_OUTLETS.items()]
    for i, (draw, text, dx) in enumerate(left):
        y = -13 - i * 9.4
        draw(p.at(5 + dx, y, color=RED))
        say(p, [text], 19, y - 0.9, 1.7)
    right = [(lambda q: pl_plate(q, "1"), "Διακόπτης μονός"),
             (lambda q: pl_plate(q, "2"), "Διακόπτης διπλός"),
             (lambda q: pl_plate(q, "S"), "Πρίζα"),
             (lambda q: pl_plate(q, "TV", "TV"), "Πρίζα TV"),
             (lambda q: pl_data(q, "D"), "Πρίζα δικτύου"),
             (lambda q: pl_data(q, "TL"), "Παροχή τηλεφώνου"),
             (lambda q: pl_plate(q, "S", "K"), "Πρίζα ηλ. κουζίνας"),
             (lambda q: pl_plate(q, "S", "DW"), "Πρίζα πλυντηρίου πιάτων"),
             (lambda q: pl_plate(q, "S", "W"), "Πρίζα πλυντηρίου ρούχων")]
    for i, (draw, text) in enumerate(right):
        y = -13 - i * 10.4
        draw(p.at(57, y, color=RED))
        say(p, [text], 63, y - 0.9, 1.7)


CEILINGS = [((122, 175, 223), "H=2.20m"), ((147, 39, 143), "H=2.25m"), ((242, 103, 34), "H=2.40m"),
            ((0, 82, 163), "H=2.45m"), ((20, 138, 255), "ΕΠΙΚΛΙΝΗΣ ΟΡΟΦΗ H=2.97-4.60m"), ((255, 196, 20), "H=2.75m")]


def legend_ceilings(b: B):
    p = panel(b, "ΥΠΟΜΝΗΜΑ ΥΛΙΚΩΝ ΑΝΟΨΕΩΝ", 98, 84)
    for i, (rgb, text) in enumerate(CEILINGS):
        y = -6 - i * 9.6
        box = [(8, y - 6.4), (26, y - 6.4), (26, y), (8, y)]
        p.pattern(box, "ANSI31", 2.6, rgb=rgb)
        p.poly(box, close=True, rgb=rgb, lineweight=50)
        say(p, ["PT01 - ΒΑΦΗ", text], 32, y - 2.6, 1.8, "KIT-B", pitch=3.2)
    notes(p, -66, ["1. ΤΟ ΥΨΟΣ ΤΗΣ ΚΑΘΕ ΨΕΥΔΟΡΟΦΗΣ ΜΕΤΡΙΕΤΑΙ ΑΠΟ ΤΟ ΤΕΛΙΚΟ", "    ΔΙΑΜΟΡΦΩΜΕΝΟ ΔΑΠΕΔΟ."])


def legend_codes(b: B):
    p = panel(b, "ΥΠΟΜΝΗΜΑ ΚΩΔΙΚΩΝ", 98, 96)
    rows = [("PL_01", None, ["Λείο σπατουλαριστό στοκάρισμα και βαφή τοίχου,", "υπόλευκο RAL 9010 (κατόπιν δειγματισμού)"]),
            ("PL_02", None, ["Αδρός rustic σοβάς και βαφή τοίχου,", "υπόλευκο RAL 9010 (κατόπιν δειγματισμού)"]),
            ("PT_01", None, ["Βαφή, RAL 9010"]),
            ("PT_02", None, ["Βαφή λάκας, RAL 9010"]),
            ("ST_01", swatch_stone, ["Αδρή ανεπίχριστη λιθοδομή, πάχους 50-60εκ"]),
            ("WD_01", swatch_wood, ["Ξύλο σκούρας δρύινης απόχρωσης"]),
            ("TL_07", swatch_dots, ["Πλακίδια τοίχων WC, αντιολισθηρά (R10)"]),
            ("BLT", None, ["Σταθερή επίπλωση - ειδικές κατασκευές"]),
            ("FR", None, ["Κινητή επίπλωση"]),
            ("DR", None, ["Πόρτες / Μπαλκονόπορτες"]),
            ("W", None, ["Παράθυρα"])]
    for i, (code, swatch, lines) in enumerate(rows):
        y = -5 - i * 8.2
        if swatch:
            swatch(p.at(6, y - 5.0), 13, 5.0)
            say(p, [code], 22, y - 3.6, 2.1, "KIT-B")
            say(p, lines, 34, y - 3.4, 1.6)
        else:
            p.rect(6, y - 5.0, 19, y)
            p.text(code, 12.5, y - 2.5, 2.1, "KIT-B", "MC")
            say(p, lines, 23, y - (1.9 if len(lines) == 2 else 3.4), 1.6, pitch=2.9)


LEGENDS = [("YP_SYMVOLA", legend_symbols), ("YP_YLIKA", legend_materials), ("YP_DAPEDA", legend_floors),
           ("YP_FOTISMOS", legend_lighting), ("YP_REYMATA", legend_power), ("YP_ANOPSEIS", legend_ceilings),
           ("YP_KODIKOI", legend_codes)]


# ------------------------------------------------------------------ title block

PANEL_W, PANEL_H = 190.0, 277.0
SHEETS = {"A0": (1189, 841), "A1": (841, 594), "A2": (594, 420), "A3": (420, 297)}
MARGIN = 10.0


def spaced(s):
    return " ".join(s)


def field(b: B, name, x0, x1, y):
    """Small spaced label on the left with a rule running to x1."""
    label = spaced(name)
    b.text(label, x0, y - 0.75, 1.5, "KIT-L")
    b.line(x0 + text_width(label, 1.5, "KIT-L") + 1.5, y, x1, y, color=RULE)


def title_block(b: B):
    """Title block panel 190 x 277 mm. Insertion: lower-right corner.

    With a 10 mm sheet margin the panel is what stays visible after the sheet
    is folded to A4.
    """
    L, M, R, R0 = -184.0, -86.0, -12.0, -80.0
    b.rect(-PANEL_W, 0, 0, PANEL_H)
    b.line(L, 263, M, 263, color=RULE)
    b.rect(R0, 251, R, 269, color=THIN)
    b.text("ΛΟΓΟΤΥΠΟ", (R0 + R) / 2, 260, 2.6, "KIT-L", "MC", color=THIN)
    b.line(R0, 236, R, 236, color=RULE)

    def values(tags, y, h=3.3, pitch=6.0, x=M, style="KIT-B"):
        for i, (tag_, default) in enumerate(tags):
            b.att(tag_, default, x, y - i * pitch, h, style, "R")

    field(b, "ΙΔΙΟΚΤΗΤΗΣ", L, M, 236)
    values([("ΙΔΙΟΚΤΗΤΗΣ1", "ΟΝΟΜΑΤΕΠΩΝΥΜΟ ΙΔΙΟΚΤΗΤΗ"), ("ΙΔΙΟΚΤΗΤΗΣ2", "")], 227.5)
    field(b, "ΤΙΤΛΟΣ ΕΡΓΟΥ", L, M, 210)
    values([("ΤΙΤΛΟΣ1", "ΤΙΤΛΟΣ ΕΡΓΟΥ"), ("ΤΙΤΛΟΣ2", "ΔΕΥΤΕΡΗ ΓΡΑΜΜΗ"), ("ΤΙΤΛΟΣ3", ""), ("ΤΙΤΛΟΣ4", "")], 201.5)
    field(b, "ΘΕΣΗ ΕΡΓΟΥ", L, M, 172)
    values([("ΘΕΣΗ1", "ΟΔΟΣ ΚΑΙ ΑΡΙΘΜΟΣ"), ("ΘΕΣΗ2", "ΔΗΜΟΣ")], 163.5)
    field(b, "ΘΕΜΑ ΣΧΕΔΙΟΥ", L, M, 147)
    values([("ΘΕΜΑ1", "ΚΑΤΟΨΗ"), ("ΘΕΜΑ2", "ΙΣΟΓΕΙΟ"), ("ΘΕΜΑ3", "")], 138.5)
    field(b, "ΚΛΙΜΑΚΑ", L, M, 116)
    values([("ΚΛΙΜΑΚΑ", "1:50")], 107.5)
    field(b, "ΗΜΕΡΟΜΗΝΙΑ", L, M, 96)
    values([("ΗΜΕΡΟΜΗΝΙΑ", "ΜΗΝΑΣ 2026")], 87.5)

    b.att("ΚΑΤΗΓΟΡΙΑ", "Α", (R0 + R) / 2, 150, 46, "KIT-B", "C")
    b.att("ΑΡΙΘΜΟΣ", "101", (R0 + R) / 2, 126, 13, "KIT-B", "C")

    field(b, "ΣΦΡΑΓΙΔΑ - ΥΠΟΓΡΑΦΗ", L, M, 64)
    field(b, "ΜΕΛΕΤΗ", R0, R, 64)
    values([("ΜΕΛΕΤΗ1", "ΟΝΟΜΑ ΓΡΑΦΕΙΟΥ"), ("ΜΕΛΕΤΗ2", "ΟΝΟΜΑ, αρχιτέκτων μηχανικός")], 56.5, 2.7, 5.2, R)
    field(b, "ΟΜΑΔΑ ΜΕΛΕΤΗΣ", R0, R, 44.5)
    values([("ΟΜΑΔΑ1", "ΟΝΟΜΑ, αρχιτέκτων μηχανικός"), ("ΟΜΑΔΑ2", ""), ("ΟΜΑΔΑ3", ""), ("ΟΜΑΔΑ4", "")],
           37.5, 2.7, 5.2, R)
    b.line(L, 10, M, 10, color=RULE)
    b.line(R0, 10, -48, 10, color=RULE)
    b.att("ΑΡΧΕΙΟ", "ΚΩΔΙΚΟΣ_ΑΡΧΕΙΟΥ", R, 9.3, 1.4, "KIT", "R")


def revisions(b: B):
    """Revision table 190 x 66 mm. Insertion: lower-right corner."""
    b.rect(-PANEL_W, 0, 0, 66)
    b.line(-95, 0, -95, 66)
    for i in range(1, 8):
        b.line(-PANEL_W, i * 8, 0, i * 8)
    b.underlined("ΑΝΑΘΕΩΡΗΣΕΙΣ", -142.5, 59.8, 2.2)
    b.underlined("ΗΜΕΡΟΜΗΝΙΑ", -47.5, 59.8, 2.2)
    for i in range(7):
        y = 52 - i * 8
        b.att(f"ΑΝΑΘ{i + 1}", "101-01" if i == 0 else "", -142.5, y, 2.6, "KIT-L", "MC")
        b.att(f"ΗΜΕΡ{i + 1}", "2026-01-01" if i == 0 else "", -47.5, y, 2.6, "KIT-L", "MC")


GENERAL_NOTES = [
    "-     DO NOT SCALE FROM DOCUMENT. USE PROVIDED DIMENSIONS OR ASK.",
    "-     ANY DISCREPANCY TO BE BROUGHT TO THE NOTICE OF CONSULTANT PRIOR TO COMMENCEMENT OF WORK.",
    "-     DRAWINGS TO BE READ IN CONJUNCTION WITH RELEVANT ARCHITECTURAL, STRUCTURAL, INTERIOR,",
    "       LIGHTING, MEP AND LANDSCAPE CONSULTANTS' PACKAGES.",
    "-     ALL FINISHES IN WET AREAS WILL HAVE WATERPROOF OR ANTISLIP TREATMENT.",
]
ITALIC = 12.0      # oblique angle: the reference notes are in italics


def general_notes(b: B):
    """General notes 190 x 30 mm, in English as in the reference. Insertion: lower-right corner."""
    b.rect(-PANEL_W, 0, 0, 30)
    w = text_width("GENERAL NOTES", 1.6, "KIT-B")
    b.text("GENERAL NOTES", -186, 25.0, 1.6, "KIT-B")
    b.line(-186, 24.3, -186 + w, 24.3)
    for i, s in enumerate(GENERAL_NOTES):
        if text_width(s, 1.4, "KIT") > PANEL_W - 8:
            raise ValueError(f"note too long: {s!r}")
        t = b.text(s, -186, 19.0 - i * 3.6, 1.4, "KIT")
        t.dxf.oblique = ITALIC


def sheet_frame(b: B, size):
    """Sheet outline and 10 mm border. Insertion: lower-left corner of the sheet."""
    w, h = SHEETS[size]
    b.rect(0, 0, w, h, color=THIN)
    b.rect(MARGIN, MARGIN, w - MARGIN, h - MARGIN, color=RULE)
