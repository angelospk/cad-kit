"""Tests for lisp/KIT.lsp, run through the strict mini interpreter.

Run:  python -m unittest gen/test_lisp.py   (from the project root)
"""
import math
import pathlib
import unittest

from minilisp import Interp, LispError

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = (ROOT / "lisp" / "KIT.lsp").read_bytes()


def load():
    it = Interp()
    it.run(SRC.decode("ascii"))
    return it


def call(it, text):
    return it.run(text)


def ents(it, block):
    return [e for e in it.entities if e.get("block") == block]


def pts(e):
    return [v for c, v in e["codes"] if 10 <= c <= 13]


def bbox(entities):
    xs, ys = [], []
    for e in entities:
        r = dict(e["codes"]).get(40, 0.0) if e["type"] == "CIRCLE" else 0.0
        for p in pts(e):
            xs += [p[0] - r, p[0] + r]
            ys += [p[1] - r, p[1] + r]
    return min(xs), min(ys), max(xs), max(ys)


def leaves(entities):
    """x-range and track centre of every leaf outline (closed 4-point polyline 4 cm deep)."""
    out = []
    for e in entities:
        if e["type"] != "LWPOLYLINE":
            continue
        p = pts(e)
        xs, ys = [q[0] for q in p], [q[1] for q in p]
        if abs((max(ys) - min(ys)) - 0.04) < 1e-9:
            out.append((min(xs), max(xs), (min(ys) + max(ys)) / 2))
    return sorted(out)


class FileTests(unittest.TestCase):
    def test_ascii_only(self):
        SRC.decode("ascii")          # raises on any non-ASCII byte

    def test_loads_and_defines_commands(self):
        it = load()
        for name in ("C:KSYR", "C:KSYRM", "C:KSYRX", "C:KPAR", "C:KPORTA", "C:KPSEYD", "C:KITHELP",
                     "C:KPORTAK", "C:KSKALA", "C:KTRAP", "C:KRAGA", "C:KLED", "C:KSYND", "C:KKLIMAKA",
                     "C:KDAP", "C:KXYLO", "C:KOROFI"):
            self.assertIn(name, it.globals, name)

    def test_no_vl_or_command_calls(self):
        text = SRC.decode("ascii").lower()
        code = "\n".join(line.split(";")[0] for line in text.splitlines())
        for banned in ("(vl-", "(vla-", "(vlax-", "(command", "(vl-load-com"):
            self.assertNotIn(banned, code)


class SlidingTests(unittest.TestCase):
    def check_cover(self, n, length):
        it = load()
        call(it, f'(kit:def-syr "B" {length} {n} 0.25 nil)')
        es = ents(it, "B")
        lv = leaves(es)
        self.assertEqual(len(lv), n)
        self.assertAlmostEqual(lv[0][0], 0.05)
        self.assertAlmostEqual(max(l[1] for l in lv), length - 0.05)
        # all leaves have the same length
        lens = {round(b - a, 9) for a, b, _ in lv}
        self.assertEqual(len(lens), 1)
        # neighbours on different tracks overlap 6 cm; on the same track they touch
        for (a0, b0, y0), (a1, b1, y1) in zip(lv, lv[1:]):
            if abs(y0 - y1) > 1e-9:
                self.assertAlmostEqual(b0 - a1, 0.06)
            else:
                self.assertAlmostEqual(b0 - a1, 0.0)
        x0, y0, x1, y1 = bbox(es)
        self.assertAlmostEqual(x0, 0.0)
        self.assertAlmostEqual(x1, length)
        self.assertAlmostEqual(y0, 0.0)
        self.assertAlmostEqual(y1, 0.25)       # far wall face line
        return lv

    def test_two_leaves(self):
        lv = self.check_cover(2, 3.0)
        self.assertEqual(len({l[2] for l in lv}), 2)

    def test_three_leaves(self):
        lv = self.check_cover(3, 3.6)
        self.assertEqual(len({round(l[2], 9) for l in lv}), 3)

    def test_four_leaves_middle_pair_meets(self):
        lv = self.check_cover(4, 4.0)
        tracks = [round(l[2], 9) for l in lv]
        self.assertEqual(tracks[0], tracks[3])
        self.assertEqual(tracks[1], tracks[2])
        self.assertNotEqual(tracks[0], tracks[1])
        self.assertAlmostEqual(lv[1][1], 2.0)   # they meet in the middle of 4.00

    def test_no_far_line_when_wall_thinner_than_frame(self):
        it = load()
        call(it, '(kit:def-syr "B" 2.0 2 0.0 nil)')
        self.assertAlmostEqual(bbox(ents(it, "B"))[3], 0.10)

    def test_stacked_leaves_share_the_start(self):
        it = load()
        call(it, '(kit:def-syrm "B" 3.0 3 0.25 nil nil)')
        lv = leaves(ents(it, "B"))
        self.assertEqual(len(lv), 3)
        self.assertEqual({round(l[0], 9) for l in lv}, {0.05})
        self.assertEqual(len({round(l[2], 9) for l in lv}), 3)
        dashed = [e for e in ents(it, "B") if dict(e["codes"]).get(6) == "KIT_DASH"]
        self.assertGreaterEqual(len(dashed), 2)
        self.assertIn("KIT_DASH", it.tables["LTYPE"])

    def test_pocket_leaves_sit_inside_the_wall(self):
        it = load()
        call(it, '(kit:def-syrm "B" 1.0 1 0.25 T nil)')
        lv = leaves(ents(it, "B"))
        self.assertEqual(len(lv), 1)
        self.assertAlmostEqual(lv[0][1], 0.0)
        self.assertAlmostEqual(lv[0][0], -0.9)
        self.assertLess(bbox(ents(it, "B"))[0], -0.9)


class WindowDoorCeilingTests(unittest.TestCase):
    def test_window(self):
        it = load()
        call(it, '(kit:def-par "B" 1.2 0.3 nil)')
        x0, y0, x1, y1 = bbox(ents(it, "B"))
        self.assertEqual((round(x0, 9), round(y0, 9), round(x1, 9), round(y1, 9)), (0.0, 0.0, 1.2, 0.3))

    def test_door_box_and_handle_side(self):
        for right, handle_x in ((None, 0.9 - 0.05 - 0.07), ("T", 0.05 + 0.07)):
            it = load()
            call(it, f'(kit:def-porta "B" 0.9 2.2 {right or "nil"})')
            es = ents(it, "B")
            x0, y0, x1, y1 = bbox(es)
            self.assertEqual((round(x0, 9), round(y0, 9), round(x1, 9), round(y1, 9)), (0.0, 0.0, 0.9, 2.2))
            self.assertEqual(es[0]["type"], "SOLID")            # the fill is drawn first, under the lines
            handle = [e for e in es if e["type"] == "CIRCLE" and dict(e["codes"])[40] == 0.025]
            self.assertEqual(len(handle), 1)
            self.assertAlmostEqual(pts(handle[0])[0][0], handle_x)
            self.assertAlmostEqual(pts(handle[0])[0][1], 1.0)
            grain = [e for e in es if e["type"] == "LINE" and dict(e["codes"]).get(420) == 9857088]
            self.assertGreater(len(grain), 10)
            for g in grain:
                (xa, ya, _), (xb, yb, _) = pts(g)
                self.assertGreater(xa, 0.05)
                self.assertLess(xa, 0.85)
                self.assertGreaterEqual(ya, 0.0)
                self.assertLessEqual(yb, 2.15)

    def test_ceiling_hangers(self):
        it = load()
        call(it, '(kit:def-pseyd "B" 3.0 0.3)')
        es = ents(it, "B")
        x0, y0, x1, y1 = bbox(es)
        self.assertEqual((round(x0, 9), round(y0, 9), round(x1, 9), round(y1, 9)), (0.0, 0.0, 3.0, 0.3))
        anchors = [e for e in es if e["type"] == "LWPOLYLINE" and abs(max(p[1] for p in pts(e)) - 0.3) < 1e-9]
        self.assertEqual(len(anchors), 5)                       # 3.00 m / 0.60 m

    def test_short_ceiling_still_gets_one_hanger(self):
        it = load()
        call(it, '(kit:def-pseyd "B" 0.25 0.3)')
        anchors = [e for e in ents(it, "B") if e["type"] == "LWPOLYLINE" and abs(max(p[1] for p in pts(e)) - 0.3) < 1e-9]
        self.assertEqual(len(anchors), 1)


class CommandTests(unittest.TestCase):
    def inserts(self, it):
        return [e for e in it.entities if e["type"] == "INSERT"]

    def test_ksyr_defaults_and_insert(self):
        it = load()
        it.inputs = [None, None, None, (10.0, 5.0, 0.0), (10.0, 8.0, 0.0)]   # Enter x3, two picks
        call(it, "(c:KSYR)")
        ins = self.inserts(it)
        self.assertEqual(len(ins), 1)
        d = dict(ins[0]["codes"])
        self.assertEqual(d[2], "SYR2_3000_250")
        self.assertEqual(d[10], [10.0, 5.0, 0.0])
        self.assertAlmostEqual(d[50], math.pi / 2)
        self.assertEqual(d[41], 1.0)
        self.assertEqual(len(leaves(ents(it, "SYR2_3000_250"))), 2)

    def test_same_size_reuses_the_block(self):
        it = load()
        it.inputs = [3, 0.3, None, (0.0, 0.0, 0.0), (3.6, 0.0, 0.0), None, None, None, (0.0, 9.0, 0.0), (3.6, 9.0, 0.0)]
        call(it, "(c:KSYR)")
        n_def = len(ents(it, "SYR3_3600_300"))
        call(it, "(c:KSYR)")                 # Enter keeps 3 leaves and 0.30
        self.assertEqual(len(ents(it, "SYR3_3600_300")), n_def)
        self.assertEqual(len(self.inserts(it)), 2)

    def test_length_is_rounded_to_the_millimetre(self):
        it = load()
        it.inputs = [None, None, (0.0, 0.0, 0.0), (1.20049, 0.0, 0.0)]
        call(it, "(c:KPAR)")
        self.assertEqual(dict(self.inserts(it)[0]["codes"])[2], "PAR_1200_250")
        self.assertAlmostEqual(bbox(ents(it, "PAR_1200_250"))[2], 1.2)

    def test_cancel_and_tiny_opening_insert_nothing(self):
        it = load()
        it.inputs = [None, None, None, None]
        call(it, "(c:KSYR)")
        it.inputs = [None, None, None, (0.0, 0.0, 0.0), (0.1, 0.0, 0.0)]
        call(it, "(c:KSYRM)")
        self.assertEqual(self.inserts(it), [])

    def test_stacked_and_pocket_commands(self):
        it = load()
        it.inputs = [3, None, None, (0.0, 0.0, 0.0), (3.0, 0.0, 0.0)]
        call(it, "(c:KSYRM)")
        it.inputs = [1, None, None, (0.0, 4.0, 0.0), (1.0, 4.0, 0.0)]
        call(it, "(c:KSYRX)")
        names = [dict(e["codes"])[2] for e in self.inserts(it)]
        self.assertEqual(names, ["SYRM3_3000_250", "SYRX1_1000_250"])

    def test_door_command(self):
        it = load()
        it.inputs = [0.8, None, "D", (2.0, 0.0, 0.0)]
        call(it, "(c:KPORTA)")
        d = dict(self.inserts(it)[0]["codes"])
        self.assertEqual(d[2], "POR_800_2200_D")
        self.assertEqual(d[50], 0.0)
        it.inputs = [0.2, None, None]           # too narrow: message, no point asked
        call(it, "(c:KPORTA)")
        self.assertEqual(len(self.inserts(it)), 1)

    def test_ceiling_command(self):
        it = load()
        it.inputs = [0.45, (0.0, 0.0, 0.0), (4.2, 0.0, 0.0)]
        call(it, "(c:KPSEYD)")
        self.assertEqual(dict(self.inserts(it)[0]["codes"])[2], "PSEYD_4200_450")

    def test_other_drawing_unit_scales_the_insert(self):
        it = load()
        call(it, "(setq kit:u 100.0)")          # centimetres
        it.inputs = [None, 25.0, None, (0.0, 0.0, 0.0), (300.0, 0.0, 0.0)]
        call(it, "(c:KSYR)")
        d = dict(self.inserts(it)[0]["codes"])
        self.assertEqual(d[2], "SYR2_3000_250")
        self.assertEqual((d[41], d[42], d[43]), (100.0, 100.0, 100.0))

    def test_defaults_are_shown_in_drawing_units(self):
        it = load()
        call(it, "(setq kit:u 100.0)")          # centimetres
        it.inputs = [None, None, None]
        call(it, "(c:KPAR)")
        it.inputs = [None, None, None, None]
        call(it, "(c:KPORTA)")
        it.inputs = [None, None]
        call(it, "(c:KPSEYD)")
        shown = " ".join(it.prompts)
        for text in ("<25.00>", "<90.00>", "<220.00>", "<30.00>"):
            self.assertIn(text, shown)

    def test_defaults_in_metres(self):
        it = load()
        it.inputs = [None, None, None]
        call(it, "(c:KPAR)")
        self.assertIn("<0.25>", " ".join(it.prompts))


class ReviewTests(unittest.TestCase):
    """Cases found by the Codex review of KIT.lsp."""

    def inserts(self, it):
        return [e for e in it.entities if e["type"] == "INSERT"]

    def test_block_entities_do_not_inherit_current_properties(self):
        it = load()
        call(it, '(kit:def-syr "A" 3.0 2 0.25 nil)')
        call(it, '(kit:def-syrm "B" 3.0 3 0.25 T nil)')
        call(it, '(kit:def-par "C" 1.2 0.25 nil)')
        call(it, '(kit:def-porta "D" 0.9 2.2 nil)')
        call(it, '(kit:def-pseyd "E" 3.0 0.3)')
        call(it, '(kit:def-portak "F" 0.9 0.25 1 nil T)')
        call(it, '(kit:def-skala "G" 1.0 16 0.28)')
        call(it, '(kit:def-trap "H" 1.8 0.9 T)')
        call(it, '(kit:def-karekla "I" "T")')
        call(it, '(kit:def-raga "J" 2.0 2)')
        call(it, '(kit:def-led "K" 2.0 50)')
        for name in "ABCDEFGHIJK":
            for e in ents(it, name):
                d = dict(e["codes"])
                self.assertTrue(62 in d or 420 in d, f"{name} {e['type']}: no colour")
                self.assertIn(6, d, f"{name} {e['type']}: no linetype")

    def test_picks_with_different_z_use_the_plan_length(self):
        it = load()
        it.inputs = [None, None, None, (0.0, 0.0, 0.0), (3.0, 0.0, 2.5)]
        call(it, "(c:KSYR)")
        d = dict(self.inserts(it)[0]["codes"])
        self.assertEqual(d[2], "SYR2_3000_250")
        self.assertAlmostEqual(d[50], 0.0)

    def test_rotated_ucs(self):
        it = load()
        it.ucs_angle = math.radians(30)
        it.inputs = [None, None, None, (0.0, 0.0, 0.0), (3.0, 0.0, 0.0)]
        call(it, "(c:KSYR)")
        it.inputs = [None, None, None, (2.0, 0.0, 0.0)]
        call(it, "(c:KPORTA)")
        win, door = (dict(e["codes"]) for e in self.inserts(it))
        self.assertAlmostEqual(win[50], math.radians(30))
        self.assertAlmostEqual(door[50], math.radians(30))
        self.assertAlmostEqual(door[10][0], 2.0 * math.cos(math.radians(30)))
        self.assertAlmostEqual(door[10][1], 2.0 * math.sin(math.radians(30)))

    def test_sizes_are_rounded_before_the_block_is_drawn(self):
        it = load()
        it.inputs = [0.2504, None, (0.0, 0.0, 0.0), (1.2, 0.0, 0.0)]
        call(it, "(c:KPAR)")
        self.assertEqual(dict(self.inserts(it)[0]["codes"])[2], "PAR_1200_250")
        self.assertEqual(bbox(ents(it, "PAR_1200_250"))[3], 0.25)
        it.inputs = [0.9004, 2.1996, None, (0.0, 0.0, 0.0)]
        call(it, "(c:KPORTA)")
        x0, y0, x1, y1 = bbox(ents(it, "POR_900_2200_A"))
        self.assertEqual((x1, y1), (0.9, 2.2))
        it.inputs = [0.3004, (0.0, 0.0, 0.0), (3.0, 0.0, 0.0)]
        call(it, "(c:KPSEYD)")
        self.assertEqual(bbox(ents(it, "PSEYD_3000_300"))[3], 0.3)

    def test_ceiling_drop_below_10cm_is_refused(self):
        it = load()
        it.inputs = [0.05, (0.0, 0.0, 0.0), (3.0, 0.0, 0.0)]
        call(it, "(c:KPSEYD)")
        self.assertEqual(self.inserts(it), [])
        it.inputs = [0.1, (0.0, 0.0, 0.0), (3.0, 0.0, 0.0)]
        call(it, "(c:KPSEYD)")
        self.assertEqual(len(self.inserts(it)), 1)
        rods = [e for e in ents(it, "PSEYD_3000_100") if e["type"] == "LINE" and pts(e)[0][0] == pts(e)[1][0]
                and 0.0 < pts(e)[0][0] < 3.0]
        self.assertEqual(len(rods), 10)                      # 5 hangers, 2 lines each

    def test_opening_too_small_for_the_leaves_is_refused(self):
        it = load()
        it.inputs = [4, None, None, (0.0, 0.0, 0.0), (0.25, 0.0, 0.0)]   # leaves of 6.75 cm
        call(it, "(c:KSYR)")
        self.assertEqual(self.inserts(it), [])
        # a leaf only has to be longer than its two 5 cm stiles
        it.inputs = [2, None, None, (0.0, 0.0, 0.0), (0.32, 0.0, 0.0)]   # leaves of 14 cm
        call(it, "(c:KSYR)")
        self.assertEqual(dict(self.inserts(it)[0]["codes"])[2], "SYR2_320_250")
        for a, b, _ in leaves(ents(it, "SYR2_320_250")):
            self.assertGreater(round(b - a, 9), 0.10)

    def test_leaf_count_out_of_range_asks_again(self):
        it = load()
        it.inputs = [5, 3, None, None, (0.0, 0.0, 0.0), (3.6, 0.0, 0.0)]
        call(it, "(c:KSYR)")
        self.assertEqual(dict(self.inserts(it)[0]["codes"])[2], "SYR3_3600_250")
        self.assertEqual(it.inputs, [])

    def test_no_insert_when_the_block_was_not_created(self):
        it = load()
        it.fail_blocks = True
        it.inputs = [None, None, None, (0.0, 0.0, 0.0), (3.0, 0.0, 0.0)]
        call(it, "(c:KSYR)")
        self.assertEqual(self.inserts(it), [])
        self.assertIn("SYR2_3000_250", " ".join(it.output))


def inserts(it):
    return [e for e in it.entities if e["type"] == "INSERT"]


def hatches(it):
    return [e for e in it.entities if e["type"] == "HATCH"]


def codes(e, code):
    return [v for c, v in e["codes"] if c == code]


class MiddleOfWallTests(unittest.TestCase):
    def test_frame_centred_in_the_wall(self):
        it = load()
        call(it, '(kit:def-syr "B" 3.0 2 0.30 T)')
        lv = leaves(ents(it, "B"))
        # frame 10 cm deep in a 30 cm wall: tracks move up by 10 cm
        self.assertAlmostEqual(min(l[2] for l in lv), 0.10 + 0.025)
        x0, y0, x1, y1 = bbox(ents(it, "B"))
        self.assertAlmostEqual(y0, 0.10)
        self.assertAlmostEqual(y1, 0.30)        # far wall face stays where it is
        self.assertEqual(it.lookup("KIT:YO"), 0.0)

    def test_offset_is_local_to_the_definition(self):
        it = load()
        it.run('(defun kit:jambs (len d tw) (+ "x" 1))')  # fails after kit:yo is set
        with self.assertRaises(Exception):
            it.run('(kit:def-syr "B" 3.0 2 0.30 T)')
        self.assertEqual(it.lookup("KIT:YO"), 0.0)

    def test_command_names_the_middle_block(self):
        it = load()
        it.inputs = [None, "Mesi", (0.0, 0.0, 0.0), (1.2, 0.0, 0.0)]
        call(it, "(c:KPAR)")
        self.assertEqual(dict(inserts(it)[0]["codes"])[2], "PAR_1200_250_M")
        it.inputs = [None, None, (0.0, 0.0, 0.0), (1.2, 0.0, 0.0)]   # remembers Mesi
        call(it, "(c:KPAR)")
        self.assertEqual(dict(inserts(it)[1]["codes"])[2], "PAR_1200_250_M")


class PlanDoorTests(unittest.TestCase):
    def test_single_leaf_hinge_in_the_middle_of_the_wall(self):
        it = load()
        call(it, '(kit:def-portak "B" 0.9 0.30 1 nil T)')
        es = ents(it, "B")
        arcs = [e for e in es if e["type"] == "ARC"]
        self.assertEqual(len(arcs), 1)
        c = dict(arcs[0]["codes"])
        self.assertAlmostEqual(c[10][0], 0.05)
        self.assertAlmostEqual(c[10][1], 0.10)     # (0.30 - 0.10) / 2: not at the wall corner
        self.assertAlmostEqual(c[40], 0.80)

    def test_double_door_two_leaves(self):
        it = load()
        call(it, '(kit:def-portak "B" 1.6 0.25 2 nil nil)')
        arcs = [dict(e["codes"]) for e in ents(it, "B") if e["type"] == "ARC"]
        self.assertEqual(len(arcs), 2)
        self.assertEqual({round(a[40], 9) for a in arcs}, {0.75})
        self.assertEqual(sorted(round(a[10][0], 9) for a in arcs), [0.05, 1.55])

    def test_command(self):
        it = load()
        it.inputs = ["2", None, None, (0.0, 0.0, 0.0), (1.4, 0.0, 0.0)]
        call(it, "(c:KPORTAK)")
        self.assertEqual(dict(inserts(it)[0]["codes"])[2], "PK2_1400_250")
        it.inputs = [None, None, "Mesi", "D", (0.0, 0.0, 0.0), (0.9, 0.0, 0.0)]
        call(it, "(c:KPORTAK)")
        self.assertEqual(dict(inserts(it)[1]["codes"])[2], "PK1_900_250_D_M")


class StairTests(unittest.TestCase):
    def test_stair_risers_treads_and_walking_line(self):
        it = load()
        it.inputs = [1.0, 2.8, 0.28, (0.0, 0.0, 0.0), (5.0, 0.0, 0.0)]
        call(it, "(c:KSKALA)")
        name = dict(inserts(it)[0]["codes"])[2]
        self.assertEqual(name, "SK_1000_16_280")             # 2.80 / 0.175 = 16 risers
        es = ents(it, name)
        x0, y0, x1, y1 = bbox(es)
        self.assertAlmostEqual(x1, 15 * 0.28)
        self.assertAlmostEqual(y1, 1.0)
        treads = [e for e in es if e["type"] == "LINE" and abs(pts(e)[0][0] - pts(e)[1][0]) < 1e-9]
        self.assertEqual(len(treads), 14)
        self.assertEqual(len([e for e in es if e["type"] == "SOLID"]), 1)   # arrow
        self.assertEqual(len([e for e in es if e["type"] == "CIRCLE"]), 1)  # start of the walking line
        self.assertIn("16 riktes x 17.5 cm", " ".join(it.output))


class TableTests(unittest.TestCase):
    def test_chairs_around_the_table(self):
        it = load()
        call(it, '(kit:def-trap "B" 1.8 0.9 T)')
        seats = [e for e in ents(it, "B") if e["type"] == "CIRCLE"]
        self.assertEqual(len(seats), 8)                       # 3 + 3 + 2 ends
        self.assertEqual(it.run("(kit:trap-chairs 1.8 T)"), 8)
        self.assertEqual(it.run("(kit:trap-chairs 2.4 nil)"), 8)

    def test_command_and_square_chair(self):
        it = load()
        it.inputs = [2.4, 1.0, "Oxi", (0.0, 0.0, 0.0)]
        call(it, "(c:KTRAP)")
        self.assertEqual(dict(inserts(it)[0]["codes"])[2], "TRAP_2400_1000_X")
        call(it, '(kit:def-karekla "K" "T")')
        polys = [e for e in ents(it, "K") if e["type"] == "LWPOLYLINE"]
        self.assertEqual(len(polys), 2)


class LightingTests(unittest.TestCase):
    def test_rail_with_spots(self):
        it = load()
        it.inputs = [3, (0.0, 0.0, 0.0), (2.4, 0.0, 0.0)]
        call(it, "(c:KRAGA)")
        self.assertEqual(dict(inserts(it)[0]["codes"])[2], "RAGA_2400_3")
        centres = sorted({round(pts(e)[0][0], 9) for e in ents(it, "RAGA_2400_3") if e["type"] == "CIRCLE"})
        self.assertEqual(centres, [0.4, 1.2, 2.0])

    def test_led_tape_pattern(self):
        it = load()
        call(it, '(setq kit:sc 25)')
        it.inputs = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
        call(it, "(c:KLED)")
        name = dict(inserts(it)[0]["codes"])[2]
        self.assertEqual(name, "LED_1000_25")
        es = ents(it, name)
        dashes = [e for e in es if e["type"] == "SOLID"]
        ticks = [e for e in es if e["type"] == "LINE"]
        # 7 mm period at 1:25 = 0.175 m: 1.0 / 0.175 -> 6 dashes
        self.assertEqual(len(dashes), 6)
        self.assertGreaterEqual(len(ticks), 15)
        self.assertLessEqual(max(p[0] for e in es for p in pts(e)), 1.0 + 1e-9)
        for e in es:
            self.assertEqual(dict(e["codes"])[62], 1)        # plots red

    def test_connection_line(self):
        it = load()
        it.inputs = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 2.0, 0.0), None]
        call(it, "(c:KSYND)")
        pl = [e for e in it.entities if e["type"] == "LWPOLYLINE"]
        self.assertEqual(len(pl), 1)
        d = dict(pl[0]["codes"])
        self.assertEqual((d[62], d[6], d[90]), (1, "KIT_SYND", 3))
        self.assertAlmostEqual(d[48], 0.05)
        self.assertIn("KIT_SYND", it.tables["LTYPE"])

    def test_scale_command(self):
        it = load()
        it.inputs = [30, 100]
        call(it, "(c:KKLIMAKA)")
        self.assertEqual(it.lookup("KIT:SC"), 100)


class HatchTests(unittest.TestCase):
    SQUARE = [(0, 0), (4, 0), (4, 3), (0, 3)]

    def test_tile_grid_size_and_origin(self):
        it = load()
        pl = it.add_pline(self.SQUARE)
        it.inputs = [None, 1.0, 0.5, pl, None, (0.3, 0.2, 0.0), None]
        call(it, "(c:KDAP)")
        hs = hatches(it)
        self.assertEqual(len(hs), 1)
        h = hs[0]
        self.assertEqual(codes(h, 93), [4])
        self.assertEqual(codes(h, 78), [2])
        self.assertEqual(codes(h, 53), [0.0, math.pi / 2])            # radians
        self.assertEqual(codes(h, 43), [0.3, 0.3])
        self.assertEqual(codes(h, 44), [0.2, 0.2])
        offsets = list(zip(codes(h, 45), codes(h, 46)))
        self.assertAlmostEqual(offsets[0][1], 0.5)            # rows 0.50 apart
        self.assertAlmostEqual(abs(offsets[1][0]), 1.0)       # columns 1.00 apart
        self.assertAlmostEqual(offsets[1][1], 0.0)

    def test_rotation_past_180_degrees(self):
        it = load()
        pl = it.add_pline(self.SQUARE)
        it.inputs = [None, 1.0, 1.0, pl, None, (0.0, 0.0, 0.0), (1.0, -1.0, 0.0)]
        call(it, "(c:KDAP)")
        self.assertEqual(len(hatches(it)), 1)

    def test_polyline_with_elevation_is_refused(self):
        it = load()
        pl = it.add_pline(self.SQUARE)
        pl["codes"].insert(6, (38, 1.5))
        it.inputs = [None, 1.0, 1.0, pl, None, (0.0, 0.0, 0.0), None]
        try:
            call(it, "(c:KDAP)")
        except LispError:
            pass
        self.assertEqual(hatches(it), [])

    def test_preset_and_rotation(self):
        it = load()
        pl = it.add_pline(self.SQUARE)
        it.inputs = ["TL07", pl, None, (0.0, 0.0, 0.0), (1.0, 1.0, 0.0)]
        call(it, "(c:KDAP)")
        h = hatches(it)[0]
        self.assertAlmostEqual(codes(h, 53)[0], math.pi / 4)
        ox, oy = codes(h, 45)[0], codes(h, 46)[0]
        self.assertAlmostEqual(math.hypot(ox, oy), 0.75)

    def test_wood_is_fill_plus_grain_and_open_polyline_is_refused(self):
        it = load()
        open_pl = it.add_pline(self.SQUARE, closed=False)
        pl = it.add_pline(self.SQUARE, bulges={1: 0.4})
        it.inputs = [open_pl, pl, None, None]
        call(it, "(c:KXYLO)")
        hs = hatches(it)
        self.assertEqual(len(hs), 2)
        self.assertEqual(codes(hs[0], 2), ["SOLID"])
        self.assertEqual(codes(hs[1], 2), ["KIT_WOOD"])
        self.assertEqual(codes(hs[1], 72), [1])
        self.assertIn(0.4, codes(hs[1], 42))
        self.assertIn("kleisti", " ".join(it.output))

    def test_ceiling_hatch_colour_and_outline(self):
        import symbols
        it = load()
        pl = it.add_pline(self.SQUARE)
        it.inputs = ["H240", pl, None]
        call(it, "(c:KOROFI)")
        r, g, b = symbols.CEILINGS[2][0]
        h = hatches(it)[0]
        self.assertEqual(codes(h, 420), [r * 65536 + g * 256 + b])
        self.assertAlmostEqual(math.hypot(codes(h, 45)[0], codes(h, 46)[0]), 0.13)  # 2.6 mm at 1:50
        outline = [e for e in it.entities if e["type"] == "LWPOLYLINE"]
        self.assertEqual(dict(outline[0]["codes"])[370], 50)

    def test_every_ceiling_colour_matches_the_legend(self):
        import symbols
        it = load()
        for key, (rgb, _) in zip(["H220", "H225", "H240", "H245", "EPIKL", "H275"], symbols.CEILINGS):
            self.assertEqual(it.run(f'(kit:ceiling-rgb "{key}")'), rgb[0] * 65536 + rgb[1] * 256 + rgb[2], key)

    def test_hatch_checker_wants_subclass_markers_and_radians(self):
        it = load()
        good = it.run("(length (kit:pat-tiles 1.0 1.0 (list 0.0 0.0) 0.0))")
        self.assertEqual(good, 2)
        bad = """(entmake (list '(0 . "HATCH") '(62 . 7)
              '(10 0.0 0.0 0.0) '(210 0.0 0.0 1.0) '(2 . "SOLID") '(70 . 1) '(71 . 0)
              '(91 . 1) '(92 . 3) '(72 . 0) '(73 . 1) '(93 . 3) '(10 0.0 0.0) '(10 1.0 0.0) '(10 1.0 1.0)
              '(97 . 0) '(75 . 0) '(76 . 1) '(98 . 1) '(10 0.0 0.0)))"""
        with self.assertRaises(LispError):
            it.run(bad)

    def test_hatch_checker_catches_a_wrong_count(self):
        it = load()
        with self.assertRaises(LispError):
            it.run("""(entmake (list '(0 . "HATCH") '(100 . "AcDbEntity") '(62 . 7)
              '(100 . "AcDbHatch") '(10 0.0 0.0 0.0) '(210 0.0 0.0 1.0) '(2 . "SOLID") '(70 . 1) '(71 . 0)
              '(91 . 1) '(92 . 3) '(72 . 0) '(73 . 1) '(93 . 4) '(10 0.0 0.0) '(10 1.0 0.0) '(10 1.0 1.0)
              '(97 . 0) '(75 . 0) '(76 . 1) '(98 . 1) '(10 0.0 0.0)))""")


class InterpreterTests(unittest.TestCase):
    def test_integer_division_truncates(self):
        self.assertEqual(Interp().run("(/ 7 2)"), 3)
        self.assertEqual(Interp().run("(/ 7 2.0)"), 3.5)

    def test_unknown_function_is_an_error(self):
        with self.assertRaises(LispError):
            Interp().run("(vl-string-search \"a\" \"b\")")

    def test_entmake_rejects_integer_coordinates(self):
        with self.assertRaises(LispError):
            Interp().run("(entmake (list '(0 . \"LINE\") '(8 . \"0\") (list 10 0 0 0) (list 11 1.0 1.0 0.0)))")

    def test_unbalanced_parens(self):
        with self.assertRaises(LispError):
            Interp().run("(setq a (+ 1 2)")


if __name__ == "__main__":
    unittest.main()
