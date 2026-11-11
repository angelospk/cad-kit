"""Furniture and sanitary fixtures in plan, real size: coordinates in metres.

Draw with draw.B(block, k=1.0). Insertion point: the middle of the wall the
item stands against, the item extends to -y (away from the wall).
Sanitary fixtures are colour 141, the light blue of the reference plans
(127, 223, 255); the KIT ctb files plot that colour as it is. Furniture is
ByLayer like the rest of the kit, with thin details in colour 252.
"""
from __future__ import annotations

from draw import B

CYAN = 141
THIN = 252
FILL = (250, 250, 250)      # light grey fill of the reference fixtures and beds
HALF = 1.0                  # bulge of a half circle


def wc(b: B):
    """Wall-hung WC 0.36 x 0.55, as measured on the reference plans."""
    r, front = 0.1735, 0.377
    outline = [(-r, 0, 0), (-r, -front, HALF), (r, -front, 0), (r, 0, 0)]
    b.bfill(outline, rgb=FILL)
    b.bpoly(outline, color=CYAN)
    b.line(-r, -0.15, r, -0.15, color=CYAN)
    b.line(-r, -0.165, r, -0.165, color=CYAN)


def tap(b: B, x=0.0, y=0.0):
    """Lever mixer: round body and a lever 18 cm long."""
    b.circle(x, y, 0.029, color=CYAN)
    b.rrect(x, y - 0.011, x + 0.18, y + 0.011, 0.011, color=CYAN)


def basin(b: B):
    """Wall-hung basin 0.60 x 0.45 with an oval bowl and a mixer."""
    b.rrect(-0.30, -0.45, 0.30, 0, 0.04, color=CYAN)
    b.bfill([(-0.20, -0.14, 0), (-0.20, -0.36, 0.414), (0.20, -0.36, 0), (0.20, -0.14, 0.414)], rgb=FILL)
    b.bpoly([(-0.20, -0.14, 0), (-0.20, -0.36, 0.414), (0.20, -0.36, 0), (0.20, -0.14, 0.414)], color=CYAN)
    b.circle(0, -0.25, 0.02, color=CYAN)
    b.circle(0, -0.07, 0.029, color=CYAN)
    b.rrect(-0.011, -0.07, 0.011, -0.02, 0.011, color=CYAN)


def shower_head(b: B):
    """Ceiling shower head, diameter 0.30. Insertion: centre."""
    b.disc(0, 0, 0.15, rgb=FILL)
    b.circle(0, 0, 0.15, color=CYAN)


def linear_drain(b: B):
    """Linear shower drain 0.80 m. Insertion: middle of the long side at the wall."""
    b.rect(-0.40, -0.08, 0.40, 0, color=CYAN)
    b.rect(-0.39, -0.07, 0.39, -0.01, color=CYAN)


def shower_tray(b: B, w=0.90, d=0.90):
    b.rect(-w / 2, -d, w / 2, 0, color=CYAN)
    b.rect(-w / 2 + 0.03, -d + 0.03, w / 2 - 0.03, -0.03, color=CYAN)
    b.circle(0, -d / 2, 0.045, color=CYAN)
    b.line(-w / 2 + 0.03, -d + 0.03, w / 2 - 0.03, -0.03, color=CYAN)
    b.line(-w / 2 + 0.03, -0.03, w / 2 - 0.03, -d + 0.03, color=CYAN)


def bathtub(b: B, w=1.70, d=0.75):
    """Bathtub along the wall. Insertion: middle of the long side at the wall."""
    b.rect(-w / 2, -d, w / 2, 0, color=CYAN)
    inner = [(-w / 2 + 0.07, -d + 0.07), (w / 2 - 0.07, -0.07)]
    (x1, y1), (x2, y2) = inner
    b.bfill([(x1 + 0.2, y1, 0), (x2 - 0.2, y1, 0.414), (x2, y1 + 0.2, 0), (x2, y2 - 0.2, 0.414),
             (x2 - 0.2, y2, 0), (x1 + 0.2, y2, 0.414), (x1, y2 - 0.2, 0), (x1, y1 + 0.2, 0.414)], rgb=FILL)
    b.rrect(x1, y1, x2, y2, 0.2, color=CYAN)
    b.circle(x1 + 0.15, (y1 + y2) / 2, 0.025, color=CYAN)
    tap(b.at(-w / 2 + 0.04, -d / 2))


def bidet(b: B):
    r, front = 0.1735, 0.377
    outline = [(-r, 0, 0), (-r, -front, HALF), (r, -front, 0), (r, 0, 0)]
    b.bfill(outline, rgb=FILL)
    b.bpoly(outline, color=CYAN)
    b.circle(0, -0.30, 0.02, color=CYAN)
    b.circle(0, -0.06, 0.029, color=CYAN)


def bed(b: B, w: float, pillows: int):
    """Bed w x 2.00 with a 6 cm headboard. Insertion: middle of the headboard at the wall."""
    L, hb = 2.00, 0.06
    b.fill([(-w / 2, 0), (w / 2, 0), (w / 2, -L - hb), (-w / 2, -L - hb)], rgb=FILL)
    b.rect(-w / 2, -L - hb, w / 2, 0)
    b.line(-w / 2, -hb, w / 2, -hb)
    pw = (w - 0.10 * (pillows + 1)) / pillows
    for i in range(pillows):
        x = -w / 2 + 0.10 + i * (pw + 0.10)
        b.rrect(x, -hb - 0.45, x + pw, -hb - 0.08, 0.04, color=THIN)
    top = -hb - 0.55
    b.line(-w / 2, top, w / 2, top)
    b.poly([(-w / 2, top), (-w / 2 + 0.23 * w, top - 0.25), (w / 2, top)], color=THIN)


def desk_chair(b: B):
    """Round chair seen from above (desk / armchair), diameter 0.55."""
    b.circle(0, 0, 0.275)
    b.circle(0, 0, 0.23, color=THIN)


SANITARY = [
    ("EY_WC", wc, "Λεκάνη WC κρεμαστή 36x55"),
    ("EY_BIDES", bidet, "Μπιντές κρεμαστός 36x55"),
    ("EY_NIPTIRAS", basin, "Νιπτήρας 60x45"),
    ("EY_BATARIA", lambda b: tap(b), "Μπαταρία"),
    ("EY_NTOUZ", shower_head, "Κεφαλή ντουζ Φ30"),
    ("EY_SIFONI_80", linear_drain, "Γραμμικό σιφώνι 80"),
    ("EY_NTOUZIERA_90", lambda b: shower_tray(b), "Ντουζιέρα 90x90"),
    ("EY_MPANIERA_170", lambda b: bathtub(b), "Μπανιέρα 170x75"),
]
FURNITURE = [
    ("KR_DIPLO_160", lambda b: bed(b, 1.60, 2), "Κρεβάτι διπλό 160x200"),
    ("KR_DIPLO_180", lambda b: bed(b, 1.80, 2), "Κρεβάτι διπλό 180x200"),
    ("KR_MONO_90", lambda b: bed(b, 0.90, 1), "Κρεβάτι μονό 90x200"),
    ("KR_MONO_120", lambda b: bed(b, 1.20, 1), "Κρεβάτι ημίδιπλο 120x200"),
    ("KAREKLA_GRAFEIOU", desk_chair, "Καρέκλα γραφείου Φ55"),
]
