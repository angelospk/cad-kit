"""Tests for the generated DXF and CTB files.

Run:  python -m unittest test_build   (inside gen/)
"""
import pathlib
import struct
import tempfile
import unittest
import warnings
import zlib

warnings.simplefilter("ignore")
import ezdxf
from ezdxf.addons import acadctb

import build
import symbols as S


class CtbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = pathlib.Path(tempfile.mkdtemp())
        for scale in build.SCALES:
            build.write_ctb(scale, cls.dir / f"KIT-{scale}.ctb")
        cls.ctb = {s: acadctb.load(cls.dir / f"KIT-{s}.ctb") for s in build.SCALES}

    def test_header_matches_the_layout_autocad_writes(self):
        data = (self.dir / "KIT-50.ctb").read_bytes()
        self.assertEqual(data[:48], b"PIAFILEVERSION_2.0,CTBVER1,compress\r\npmzlibcodec")
        checksum, size, packed = struct.unpack("<III", data[48:60])
        body = data[60:]
        self.assertEqual(packed, len(body))
        self.assertEqual(checksum, zlib.adler32(body))
        raw = zlib.decompress(body)
        self.assertEqual(size, len(raw))
        self.assertTrue(raw.endswith(b"\x00"))

    def test_same_colours_thicker_at_25_thinner_at_100(self):
        for aci in build.ARCH_PENS:
            w25, w50, w100 = (self.ctb[s][aci].get_lineweight() for s in ("25", "50", "100"))
            self.assertAlmostEqual(w50, build.ARCH_PENS[aci])
            self.assertGreaterEqual(w25, w50)
            self.assertLessEqual(w100, w50)
            self.assertLess(w100, w25)

    def test_her_layer_widths_are_the_1_50_pens(self):
        for name, color, lw, _ in build.HER_LAYERS:
            if lw > 0:
                self.assertAlmostEqual(self.ctb["50"][color].get_lineweight(), lw / 100.0, msg=name)

    def test_one_width_per_colour(self):
        seen = {}
        for name, color, lw, _ in build.HER_LAYERS + build.KIT_LAYERS:
            if lw > 0:
                self.assertEqual(seen.setdefault(color, lw), lw, f"{name}: colour {color} has two widths")

    def test_annotation_pens_do_not_change_with_scale(self):
        for aci in list(build.CONST_PENS) + list(build.RED_PENS):
            widths = {self.ctb[s][aci].get_lineweight() for s in build.SCALES}
            self.assertEqual(len(widths), 1, aci)

    def test_plot_colours(self):
        for s in build.SCALES:
            ctb = self.ctb[s]
            self.assertEqual(ctb[1].color, build.PLOT_RED)
            self.assertEqual(ctb[12].color, build.PLOT_RED)
            self.assertEqual(ctb[243].color, (0, 0, 0))
            self.assertEqual(ctb[7].color, (0, 0, 0))
            self.assertEqual(ctb[9].screen, 40)
            self.assertIsNone(ctb[141].color)                    # object colour
            self.assertEqual(ctb[7].get_lineweight(), 0.0)       # object lineweight
            self.assertEqual(ctb[200].get_lineweight(), 0.0)


class DxfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc, cls.zones = build.build()
        cls.reloaded = ezdxf.readfile(build.OUT / "KIT.dxf")

    def test_file_passes_the_audit(self):
        auditor = self.reloaded.audit()
        self.assertEqual([str(e.message) for e in auditor.errors], [])

    def test_no_automatic_unit_scaling(self):
        self.assertEqual(self.reloaded.header["$INSUNITS"], 0)
        for blk in self.reloaded.blocks:
            self.assertEqual(blk.block_record.dxf.get("units", 0), 0, blk.name)

    def test_every_block_exists_at_every_scale(self):
        names = {b.name for b in self.reloaded.blocks}
        for base, _, _, group in build.annotation_blocks():
            for suffix in build.SCALES:
                self.assertIn(f"{base}_{suffix}", names)
            if group == "sheet":
                self.assertIn(f"{base}_MM", names)
        for name, _, _ in build.LISP_SAMPLES:
            self.assertIn(name, names)

    def test_scaled_blocks_have_the_right_size(self):
        for suffix, k in {**build.SCALES, **build.PAPER}.items():
            ext = ezdxf.bbox.extents(self.reloaded.blocks.get(f"PLAISIO_A1_{suffix}"), fast=True)
            self.assertAlmostEqual(ext.size.x, 841 * k)
            self.assertAlmostEqual(ext.size.y, 594 * k)
            ext = ezdxf.bbox.extents(
                [e for e in self.reloaded.blocks.get(f"PINAKIDA_{suffix}") if e.dxftype() == "LWPOLYLINE"], fast=True)
            self.assertAlmostEqual(ext.size.x, S.PANEL_W * k)
            self.assertAlmostEqual(ext.size.y, S.PANEL_H * k)

    def test_title_block_folds_to_a4(self):
        self.assertLessEqual(S.PANEL_W + 2 * S.MARGIN, 210)
        self.assertLessEqual(S.PANEL_H + 2 * S.MARGIN, 297)

    def test_blocks_use_only_layer_0_and_known_styles(self):
        for blk in self.reloaded.blocks:
            if blk.name.startswith("*"):
                continue
            for e in blk:
                self.assertEqual(e.dxf.layer, "0", f"{blk.name}: {e.dxftype()} on {e.dxf.layer}")
                if e.dxftype() in ("TEXT", "ATTDEF"):
                    self.assertIn(e.dxf.style, ("KIT", "KIT-B", "KIT-L"))

    def test_attribute_tags_are_unique_inside_a_block(self):
        for blk in self.reloaded.blocks:
            tags = [a.dxf.tag for a in blk.attdefs()]
            self.assertEqual(len(tags), len(set(tags)), blk.name)
            for tag in tags:
                self.assertNotIn(" ", tag)

    def test_layers(self):
        layers = {l.dxf.name: l for l in self.reloaded.layers}
        for name, color, lw, ltype in build.HER_LAYERS + build.KIT_LAYERS:
            self.assertEqual(layers[name].color, color, name)
            self.assertEqual(layers[name].dxf.lineweight, lw, name)
        self.assertEqual(layers[build.INFO_LAYER].dxf.plot, 0)

    def test_library_zones_do_not_overlap(self):
        main = [self.zones[k] for k in ("R", "25", "50", "100")]
        for a, b in zip(main, main[1:]):
            self.assertLess(a[2], b[0])

    def test_inserts_carry_their_attributes(self):
        msp = self.reloaded.modelspace()
        for ref in msp.query("INSERT"):
            blk = self.reloaded.blocks.get(ref.dxf.name)
            want = sorted(a.dxf.tag for a in blk.attdefs())
            self.assertEqual(sorted(a.dxf.tag for a in ref.attribs), want, ref.dxf.name)


if __name__ == "__main__":
    unittest.main()
