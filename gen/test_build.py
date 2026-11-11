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
import furniture as F
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
            self.assertIsNone(ctb[30].color)                     # skirting TL-01: its true colour
            self.assertIsNone(ctb[50].color)                     # TL-07
            self.assertAlmostEqual(ctb[30].get_lineweight(), 0.50)


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


class AdditionsTests(unittest.TestCase):
    """Second request: furniture, sanitary, texts, dimensions, skirting, hatches."""

    @classmethod
    def setUpClass(cls):
        cls.doc, cls.zones = build.build()
        cls.reloaded = ezdxf.readfile(build.OUT / "KIT.dxf")
        cls.msp = cls.reloaded.modelspace()

    def test_sanitary_blocks_plot_light_blue(self):
        for name, _, _ in F.SANITARY:
            blk = self.reloaded.blocks.get(name)
            lines = [e for e in blk if e.dxftype() != "HATCH"]
            self.assertTrue(lines, name)
            for e in lines:
                self.assertEqual(e.dxf.color, 141, f"{name} {e.dxftype()}")
        self.assertEqual(ezdxf.colors.aci2rgb(141), (127, 223, 255))   # the cyan of the reference

    def test_furniture_is_not_blue(self):
        for name, _, _ in F.FURNITURE:
            for e in self.reloaded.blocks.get(name):
                self.assertNotEqual(e.dxf.get("color", 256), 141, name)

    def test_bed_size(self):
        ext = ezdxf.bbox.extents(self.reloaded.blocks.get("KR_DIPLO_160"), fast=True)
        self.assertAlmostEqual(ext.size.x, 1.60)
        self.assertAlmostEqual(ext.size.y, 2.06)

    def test_new_annotation_blocks(self):
        names = {b.name for b in self.reloaded.blocks}
        for suffix in build.SCALES:
            self.assertIn(f"STATHMI_ED_{suffix}", names)
            for d in "RLUD":
                for n in build.ARROW_COUNTS:
                    self.assertIn(f"HL_YPSI{n}_{d}_{suffix}", names)
        blk = self.reloaded.blocks.get("HL_YPSI3_D_50")
        self.assertEqual([a.dxf.tag for a in blk.attdefs()], ["ΥΨΟΣ1", "ΥΨΟΣ2", "ΥΨΟΣ3"])
        self.assertTrue(all(a.dxf.color == 1 for a in blk.attdefs()))
        ed = [a.dxf.text for a in self.reloaded.blocks.get("STATHMI_ED_50").attdefs()]
        self.assertEqual(ed, ["ΣΤ. ΔΙΑΜ. ΕΔΑΦΟΥΣ = +0.00", "ΣΤ. ΦΥΣ. ΕΔΑΦΟΥΣ = +0.00"])

    def test_height_arrow_points_to_the_wall(self):
        for d, (ux, uy) in S.DIRS.items():
            ext = ezdxf.bbox.extents([e for e in self.reloaded.blocks.get(f"HL_YPSI2_{d}_50") if e.dxftype() == "LINE"])
            # the line runs from the tip (0, 0) away from the wall
            far = (ext.extmin.x if ux > 0 else ext.extmax.x) if ux else (ext.extmin.y if uy > 0 else ext.extmax.y)
            near = (ext.extmax.x if ux > 0 else ext.extmin.x) if ux else (ext.extmax.y if uy > 0 else ext.extmin.y)
            self.assertAlmostEqual(near, 0.0, msg=d)
            self.assertGreater(abs(far), 0.5, d)

    def test_general_notes_in_english(self):
        texts = [e.dxf.text for e in self.reloaded.blocks.get("SIMEIOSEIS_50") if e.dxftype() == "TEXT"]
        self.assertIn("GENERAL NOTES", texts)
        self.assertTrue(any("DO NOT SCALE FROM DOCUMENT" in t for t in texts))

    def test_skirting_layers_carry_the_legend_colour(self):
        for code in ("TL-01", "TL-07"):
            layer = self.reloaded.layers.get(f"Σοβατεπί {code}")
            self.assertEqual(layer.rgb, S.SKIRTING[code])
            self.assertEqual(layer.dxf.lineweight, 50)
            lines = self.msp.query(f'LWPOLYLINE[layer=="Σοβατεπί {code}"]')
            self.assertEqual(len(lines), 1)                 # sample for MATCHPROP, loose, not a block

    def test_dimension_styles_in_centimetres(self):
        for name, k, red in (("KIT_25", 0.025, False), ("KIT_50", 0.05, False), ("KIT_FOT_25", 0.025, True)):
            st = self.reloaded.dimstyles.get(name)
            self.assertAlmostEqual(st.dxf.dimscale, k)
            self.assertAlmostEqual(st.dxf.dimlfac, 100.0)
            self.assertEqual(st.dxf.dimdec, 0)
            self.assertEqual(st.dxf.dimclrt, 1 if red else 256)
        self.assertEqual(len(self.msp.query("DIMENSION")), 4)

    def test_room_texts_at_every_scale_including_200(self):
        rooms = [t for t in self.msp.query('TEXT[layer=="Χώροι"]') if t.dxf.text == "ΚΑΘΙΣΤΙΚΟ"]
        heights = sorted(round(t.dxf.height, 6) for t in rooms)
        self.assertEqual(heights, [round(build.ROOM_H * k, 6) for k in sorted(build.TEXT_SCALES.values())])

    def test_red_height_templates_not_at_200(self):
        t = [e for e in self.msp.query("TEXT") if e.dxf.text == "H=0.40m."]
        self.assertEqual(len(t), 3)
        self.assertTrue(all(e.dxf.color == 1 for e in t))

    def test_hatch_samples_come_from_the_lisp(self):
        names = sorted(h.dxf.pattern_name for h in self.msp.query("HATCH"))
        for name in ("KIT_TILE", "KIT_DECK", "KIT_WOOD", "KIT_DIAG", "SOLID"):
            self.assertIn(name, names)
        self.assertEqual(names.count("KIT_DIAG"), 6)


if __name__ == "__main__":
    unittest.main()
