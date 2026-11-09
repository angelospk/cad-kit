# Rules for agents

Read `docs/HANDOFF.md` first: who the kit is for, what was asked, what was
decided and why, what is not verified, and the backlog.

## Build and test

```sh
python -m venv .venv && .venv/bin/pip install ezdxf fonttools matplotlib skia-pathops
.venv/bin/python gen/build.py          # out/KIT.dxf, out/ctb/*.ctb
.venv/bin/python gen/docs.py           # out/ODIGIES.md
.venv/bin/python gen/preview.py        # out/preview/*.png
cd gen && ../.venv/bin/python -m unittest test_lisp test_build
```

DWG (needs the free ODA File Converter):

```sh
ODA_CONVERTER=/path/to/ODAFileConverter gen/convert.sh
.venv/bin/python gen/check_dwg.py
```

## Rules

- Everything in `out/` is generated. Change the generator, then rebuild. Do not
  edit `out/` by hand. `out/ODIGIES.md` comes from `gen/docs.py`.
- `lisp/KIT.lsp` stays ASCII only, uses no `vl-*` functions and no
  `(command ...)`, and creates no layers. A test enforces the first two.
- A new AutoLISP function used in `KIT.lsp` must be added to `gen/minilisp.py`
  with the real AutoLISP behaviour (integer division, nil, types). The
  interpreter must stay strict: unknown function or wrong `entmake` type is an
  error.
- Write the failing test first. Tests for the LISP go in `gen/test_lisp.py`,
  for the DXF and CTB in `gen/test_build.py`.
- Entities inside blocks are on layer `0`. Main lines ByLayer, thin lines
  colour 252, dashed lines colour 253 with linetype `KIT_DASH`, fills in a true
  colour. Every entity made by the LISP writes colour, linetype and lineweight.
- Sizes in `gen/symbols.py` are paper millimetres. Sizes in `lisp/KIT.lsp` are
  metres.
- The file and all block records stay unitless (`$INSUNITS = 0`).
- One lineweight per colour across all layers. A test enforces it.
- After a change, render the previews and look at them. Tests do not see a
  label that overlaps a symbol.
- User-facing text (`ODIGIES.md`, captions in the library sheet) is Greek.
  Code, comments and commit messages are English.
- Do not add the reference PDFs, anyone's DWG drawings, real names of clients
  or offices, or `out/KIT.dwg` (the converter stamps the local user name in
  it).
- Say plainly what was not run in a real CAD program. So far nothing was.
