# Handoff

State on 2026-11-11 (second request done, see "Second request"). Read this before you change anything. `AGENTS.md` has the
working rules. `out/ODIGIES.md` is the guide the end user reads (Greek).

## Who it is for

An architect in Greece. She draws in model space with **1 unit = 1 metre**.
Her own drawings were last plotted from ZWCAD with `monochrome.ctb` and
lineweights set per layer. She asked that the kit works in AutoCAD 2024 and
later, AutoCAD LT, ZWCAD and BricsCAD, latest versions.

She does not program. She gets a zip: `KIT.dwg`, `KIT.dxf`, three `.ctb`
files, `KIT.lsp`, four fonts, `ODIGIES.md`, previews.

## What she asked for

The request came as a voice transcript. She showed the construction drawings of
another architecture office and said she likes how they look. In order:

| # | Request | State |
|---|---|---|
| 1 | All their legends, as CAD blocks | Done: 7 legend blocks |
| 2 | Sliding frame block in plan, "simpler than theirs", that she places at one wall corner and pulls to the length she wants. It keeps its shape and still reads as sliding | Done as a command (`KSYR`), not as a grip. See "Dynamic blocks" |
| 3 | The same for leaves gathered at one side, one behind the other (triple), and for leaves that slide into the wall | Done: `KSYRM`, `KSYRX` |
| 4 | A window block "like theirs" | Done: `KPAR` |
| 5 | The font they use, working in Greek and Latin | Answered: TT Norms Pro (paid). Kit ships Commissioner (free) |
| 6 | Which program they work in | Answered: AutoCAD LT 2024 |
| 7 | CTB with her colours, lineweights per scale 1:25 / 1:50 / 1:100, electrical blocks plot red, cut elements heavier | Done: 3 CTB files, one layer set |
| 8 | A suspended-ceiling drawing "with the mechanisms, like theirs, simple" | Done: `KPSEYD` (section) |
| 9 | Door blocks for interior elevations with the wood hatch and the handle, editable in width and height | Done: `KPORTA` |
| 10 | Title blocks ("πινακάκια") that fold to A4, for 1:100, 1:50, 1:25, as DWG | Done: `PINAKIDA`, `ANATHEORISEIS`, `SIMEIOSEIS`, `PLAISIO_A0..A3` |

Answers she gave to three questions:

1. Units: metres.
2. CAD: "compatible with everything from 2024 on; other CAD programs too, for
   example ZWCAD, BricsCAD, latest versions".
3. Lineweights: one CTB per scale, the same colours in all three. "Walls one
   colour; which CTB I pick decides the thickness."

Later she sent three of her own DWG files and said: take the colours from
these, maybe the other layer properties too; they are good, but improve them if
you have something better.

Not asked, but discussed at the start of the transcript: the "book" (the
specification booklet of the construction drawings). She compared two styles: a
plain table with one row per item that also carries a link to the product, and
a page-per-item layout with code, location, quantity, description. She likes
the look of the second and the link of the first. Nothing was built for this.

## What the reference drawings showed

The reference PDFs and her DWG files are private. They are **not** in this
repository and must not be added. Ask the owner if you need them. What was
measured from them:

Reference office PDFs (12 sheets: plans, flooring, lighting, sockets, bathroom
elevations):

- `Creator: AutoCAD LT 2024 - English`, `Producer: pdfplot16.hdi` (DWG To PDF),
  plotted from layouts. Plans on A0 at 1:25, elevations on A1 at 1:25.
- Fonts embedded: TT Norms Pro (Regular, Bold, Italic, Light, Medium) for all
  labels, legends and the title block; Arial and Arial Narrow for dimensions.
- Plotted pen widths found (600 dpi, so quantised): 0.05, 0.09, 0.18, 0.20,
  0.25, 0.30, 0.40, 0.50, 0.60, 0.70 mm. Cut walls 0.50 to 0.70, most linework
  0.18 to 0.25, hatches 0.09.
- Plotted colours: black for almost everything; grey 152 (black at 40 %
  screening) for the underlay; red (221,0,0 and darker reds) for lighting,
  sockets and their tags and dimensions; cyan 127,223,255 (ACI 141) for taps;
  true-colour fills for wood (tan) and insulation (248,246,176).
- Title block: a column 210 mm wide at the right edge of the sheet. Bottom
  panel about 210 x 297 mm (one A4), revision table above it, general notes
  above that, legends above those. Small letter-spaced field labels with a rule,
  bold right-aligned values, a big sheet-category letter and the sheet number.
- Legends: a pill-shaped title frame with a bold underlined title, a plain
  frame under it, about 98 mm wide.
- Tags: a two-cell box (code over number) with a two-line label.

Her DWG files (AC1032, read with LibreDWG `dwg2dxf` and the ODA converter):

- `$INSUNITS = 4` (millimetres) although she draws in metres (dimension style
  `AEC Dim 1-50` has text height 0.1). This is why the kit is unitless: see
  "Decisions".
- No CTB in one file, `monochrome.ctb` in another. Plot device
  `ZWCAD Virtual Eps Plotter`.
- Her architectural layers, with colour and lineweight, are the table
  `HER_LAYERS` in `gen/build.py`. Layers of the structural program (`beam_*`,
  `column_*`, `slab_*`) and of the survey program (`Dcad_*`) were left out.
- Three pairs of layers share a colour but not a lineweight. A CTB sets the
  width per colour, so the kit changes one layer of each pair:
  `PROVOLH_FRONT` 243 -> 242, `PROVOLH` 20 -> 21, `KITBATH` 0.18 -> 0.20.
- `PROVOLH3` is colour 147 / 0.15 in one file and 145 / 0.18 in another. The
  CTB covers both colours. Not unified.
- Linetype `HIDDEN2` has the stock definition (dash 3.175) with `LTSCALE 1`,
  which is far too long for metres. The kit defines its own `KIT_DASH`
  (0.10 / 0.05 m) and `KIT_LED`.

Font search (Google Fonts metadata, 2026-11-09): free geometric sans families
**with** a Greek subset: Commissioner, Geologica, Google Sans, Manrope, Sofia
Sans, Geom, Inter. **Without** Greek: Montserrat, Jost, Outfit, Figtree,
Urbanist, Raleway, Mulish, Red Hat Display, Plus Jakarta Sans, Lexend. A
side-by-side render against the reference put Commissioner closest (round O and
Ω, light regular weight), Google Sans and Geologica next.

## Decisions and their trade-offs

**Dynamic blocks.** A block with a stretch grip is an AutoCAD dynamic block. It
can only be authored in the AutoCAD Block Editor on Windows. ezdxf cannot write
one, BricsCAD and ZWCAD cannot author one in the same format, and no CAD
program was available here. So the "pull it to length" request became commands:
two picks, and a block of that size is made and inserted. Cost: to change the
length she erases and runs the command again. A real dynamic block is the top
item of the backlog.

**One source for the parametric blocks.** `lisp/KIT.lsp` draws them with
`entmake`. `gen/minilisp.py` is a small strict AutoLISP interpreter. The build
runs the same file to make the sample blocks in the DXF, and the tests run it
too. Cost: the interpreter is one more thing to maintain, and it only models
what the file uses. Gain: the LISP is never untested text.

**ASCII-only LISP, Greeklish prompts, no layers created by LISP.** A `.lsp`
with Greek letters is read in a different code page by different CAD programs.
So the file has no Greek, creates no layers, and inserts on the current layer.
Inside a block the main lines are ByLayer on layer 0; thin lines use colour
252, dashed lines colour 253, fills a true colour. Cost: prompts are less
pretty.

**Annotation blocks per scale.** Tags, symbols, legends and title blocks have a
fixed size on paper, so each exists as `_25`, `_50`, `_100` (and the sheet
blocks as `_MM` for paper space). Annotative objects were not used: support
differs between CAD programs. Cost: 3 times the block count.

**Three CTB files, one layer set.** The 1:50 pens are her layer lineweights.
1:25 goes one step up, 1:100 one step down (`STEP` in `gen/build.py`).
Annotation, dimension and electrical pens keep their width at every scale.
Colours not in the table plot black with the object lineweight, as
`monochrome.ctb` did for her before. True-colour objects plot in their colour.

**Unitless file.** `$INSUNITS = 0` and every block record has units 0. With
units set to metres, a CAD program would scale a pasted block by 1000 in her
drawings, because they say millimetres.

**Fonts.** Static instances of Commissioner made with fontTools, with
overlapping contours merged (`gen/make_fonts.py`). Variable fonts and
overlapping contours both give trouble in CAD text rendering. Text styles `KIT`,
`KIT-B`, `KIT-L`; she can point them at TT Norms Pro if she buys it.

**Title block.** 190 x 277 mm, so with a 10 mm sheet margin it is what shows
after folding to A4. All fields are attributes. The logo is a placeholder box.

## What is verified, and what is not

Verified:

- 84 unit tests (`gen/test_lisp.py`, `gen/test_build.py`).
- KDAP, KXYLO and KOROFI refuse a polyline with a nonzero elevation (the hatch is made at elevation 0). HATCH angles (code 53) go to `entmake` in radians, as AutoLISP wants for codes 50-58.
- `KIT.lsp` loads and every command runs in the interpreter, including
  defaults, cancel, a UCS rotated about Z, another drawing unit.
- The DXF passes the ezdxf audit.
- DXF -> DWG -> DXF through the ODA File Converter (with audit) gives the same
  blocks, layers, styles, inserts and attribute values (`gen/check_dwg.py`).
- The CTB header has the layout of a file written by AutoCAD (compared with
  `tests/test_08_addons/ctbtest.ctb` from the ezdxf repository).
- Previews in `out/preview` were rendered and looked at.

Not verified:

- **Nothing was opened in AutoCAD, AutoCAD LT, ZWCAD or BricsCAD.** Not the
  DWG, not the CTB files, not the LISP.
- Text metrics: the layout assumes a CAD program scales a TrueType font so its
  capitals are as high as the text height.
- The six-step dynamic block recipe at the end of `ODIGIES.md`.

## Reviews so far

- CodeRabbit: 1 minor (defaults shown in metres when the unit is not the
  metre). Fixed.
- Codex round 1 on `KIT.lsp`: 8 important, 1 nit. Fixed 7. UCS: fixed for a UCS
  rotated about Z; a tilted 3D UCS was declined (2D kit, stated in the file
  header). The nit (check every `entmake` result) was declined except for one
  guard: no insert when the block was not created.
- Codex round 2: accepted all of that, and found one new point (the 15 cm
  minimum leaf was arbitrary). Changed to "longer than the two stiles". That
  last change was not reviewed again.

## Second request (2026-11-11)

A second voice transcript asked for improvements, with nothing removed. What
was asked, what was built, and the choice made where she was unsure:

| Request | Built |
|---|---|
| Sanitary fixtures in blue, as in the plans, printing light blue | `EY_*` blocks, real size. Colour 141 inside the block = (127, 223, 255), the exact cyan measured in the PDFs. Pen 141 plots the object colour. Shapes measured from the PDF vectors (WC 0.36 x 0.55, shower head 0.30, linear drain 0.80) |
| Nicer wood hatch on the elevation doors | `kit:def-porta` grain: columns 1.2-3.2 cm apart, two tones, broken pieces. Compared by eye with the bathroom elevation door |
| A wood "super hatch" for any outline | `KXYLO`: solid tan hatch + custom pattern `KIT_WOOD`, made with `entmake` |
| Room names in Greek, right size at 1:25 / 1:50 / 1:100 / 1:200 | Loose TEXT on layer `Χώροι`, 3 mm on paper, in the palette zone. Not blocks: she edits them with a double click. 1:200 has only these texts |
| General notes in English | `SIMEIOSEIS`: the reference text, oblique 12 for the italics |
| A level mark for formed / natural ground | `STATHMI_ED` |
| A stair she sizes with a command, with a walking line | `KSKALA`: straight flight only; risers = height / 0.175 rounded |
| Plan door with the hinge set in, and a double door | `KPORTAK`: frame at the wall face or in the middle (`Mesi`), 1 or 2 leaves |
| Bed, chairs, dining tables | `KR_*`, `KAREKLA*` blocks; `KTRAP` command plus 3 sample tables (she was unsure; both exist) |
| Existing frames: middle or edge of the wall | `Akri/Mesi` prompt in `KSYR`, `KSYRM`, `KSYRX`, `KPAR`, `KPORTAK`; `_M` suffix |
| Floor hatches from the legend, tile size of her choice, skirting | `KDAP` (Plakaki w x h, TL01-03, TL07, CN01, WD06) with origin point and direction. Skirting: layers `Σοβατεπί TL-01/TL-07` with the legend true colour, sample lines for MATCHPROP |
| Ready texts at 1:25: marble sills, square metres, rooms | Palette: ΜΑΡΜΑΡΟΠΟΔΙΑ, ΠΑΤΗΜΑ, `00.00 ΤΜ` |
| Dimension templates as on sheet 310, for 1:25 and 1:50 ("not 1:100") | Dim styles `KIT_25`, `KIT_50` (cm, Arial, ticks) and red `KIT_FOT_25/50` for lighting, with samples |
| Lighting: ceiling super hatch, rails with a length, LED as on sheet 311, red dashed connections | `KOROFI`, `KRAGA`, `KLED` (+ new legend symbol), `KSYND`. `KKLIMAKA` sets the plot scale these use |
| Socket arrows with heights, in four directions, as on sheet 312 | `HL_YPSI{1-6}_{R,L,U,D}` per scale, heights are red attributes |
| Red height templates `H=0.40m.` as on sheet 315 | Palette texts, 1:25 / 1:50 / 1:100 |
| "Notes with heights" | She withdrew it in the transcript. Not built |

Decisions:

- **MATCHPROP palette.** MATCHPROP cannot pick an entity inside a block, so
  everything meant for MATCHPROP (texts, dimensions, skirting lines, hatches)
  is loose in model space, in the zone `P`. Hatch samples are made by running
  the LISP hatch commands in the interpreter: one source.
- **Hatch with entmake.** `kit:hatch` writes the HATCH group codes directly.
  Pattern offsets are in WCS, already rotated by the line angle: that is what
  ezdxf writes when it compiles a PAT pattern (`ezdxf/tools/pattern.py`). The
  interpreter checks the counts (`93`, `78`, `79`, `98`). Not run in a real CAD:
  this is the riskiest new part. The hatches are not associative.
- **Paper-sized LISP output** (LED pattern, connection linetype, ceiling hatch
  spacing) uses `kit:sc`, set by `KKLIMAKA` (default 50).
- **Skirting colour.** Layers on ACI 30 and 40, with a true colour equal to the
  ACI colour exactly: (255, 127, 0) and (255, 191, 0). The CTB plots pens 30
  and 40 in the object colour at 0.50. The PDF colours were (221, 55, 0) and
  (255, 196, 20), but DWG keeps only the nearest ACI of a true colour: the ODA
  converter turned the first into ACI 22 (her "Πλάκα Στέγης" pen, black 0.40).
  Every free ACI near that red is taken, so Άγγελος chose orange ACI 30. The
  floor legend uses the same colours.

Not verified this round:

- `out/KIT.dwg` was **not** rebuilt: the ODA File Converter is not installed on
  either host any more. The file in `out/` is from 2026-11-10 and is stale.
  Build it again with `gen/convert.sh` before sending the kit.
- Italic (oblique) text and the Arial dimension font do not show in the
  ezdxf previews; only in a CAD program.

## Backlog, most useful first

1. Open `KIT.dwg` in a real CAD program, load `KIT.lsp`, run each command, plot
   with each CTB. Record what breaks. Everything else depends on this.
2. Real dynamic blocks for the sliding frames, window and door, authored in
   AutoCAD and saved into the kit. They cannot be generated here.
3. Sliding frames: choose where the frame sits in the wall thickness (now flush
   with the picked line), a mirror option, optional opening arrows.
4. A command that changes the size of an existing kit block in place.
5. Dimension styles per scale, and a `.dwt` template with layouts, viewports
   and page setups that already point at the CTB files.
6. More blocks in the same style: window and sliding door in elevation,
   L-shaped and U-shaped stairs, step numbers on `KSKALA`, kitchen.
7. Legends she can edit without the Block Editor (attributes or tables).
8. `KIT_LED` and `KIT_DASH` as a `.lin` file, hatch patterns as a `.pat` file.
9. The "book": a generator for specification sheets with code, location,
   quantity, description, dimensions, finish, maker, link. She has no InDesign;
   HTML to PDF would do.
10. Fold marks on the sheet frames. A PDF catalogue of all blocks.

## Traps met on the way

- `ezdxf.addons.acadctb` saves a CTB with `struct.pack("LLL")`. On 64-bit macOS
  and Linux that makes a 72-byte header and a file nothing can read, ezdxf
  included. `build.save_ctb` writes the correct 60-byte header.
- `RenderContext(doc, ctb=None)` crashes in ezdxf 1.4.5. Pass a
  `acadctb.new_ctb()` object instead (`gen/render.py`).
- The ODA File Converter writes the operating-system user name into the DWG as
  "last saved by". That is why `out/KIT.dwg` is not in the repository: build it
  with `gen/convert.sh`.
- The ODA converter is a GUI program but runs headless from the command line:
  `ODAFileConverter <in dir> <out dir> ACAD2018 DWG 0 1 "*.dxf"`.
- Every build writes new timestamps and GUIDs into `out/KIT.dxf`, and
  `test_build.py` runs the build. So `git status` shows the DXF as modified
  after the tests. Run `git checkout out/KIT.dxf` when you did not change the
  generator.
- `grep -v` as the last command in a pipe returns 1 when it filters every line.
  Do not read that as a failed build.
