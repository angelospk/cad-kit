"""Compares out/KIT.dxf with the DWG that the ODA converter made from it.

The DWG was converted back to DXF (out/.roundtrip/KIT.dxf). If blocks, layers,
styles, block contents and attribute values all survive the trip, the DWG holds
what the generator wrote.
"""
import collections
import pathlib
import sys
import warnings

warnings.simplefilter("ignore")
import ezdxf

ROOT = pathlib.Path(__file__).resolve().parent.parent


def summary(doc):
    blocks = {}
    for blk in doc.blocks:
        if blk.name.startswith("*"):
            continue
        blocks[blk.name] = dict(collections.Counter(e.dxftype() for e in blk))
    layers = {l.dxf.name: (l.color, l.dxf.lineweight, l.dxf.linetype, l.dxf.get("plot", 1)) for l in doc.layers}
    styles = {s.dxf.name: s.dxf.font.lower() for s in doc.styles if s.dxf.name.startswith("KIT")}
    ltypes = {l.dxf.name for l in doc.linetypes}
    inserts = collections.Counter()
    attribs = {}
    for ref in doc.modelspace().query("INSERT"):
        inserts[(ref.dxf.name, ref.dxf.layer)] += 1
        for a in ref.attribs:
            attribs[(ref.dxf.name, a.dxf.tag)] = a.dxf.text
    return blocks, layers, styles, ltypes, dict(inserts), attribs


if __name__ == "__main__":
    a = summary(ezdxf.readfile(ROOT / "out" / "KIT.dxf"))
    back = ezdxf.readfile(ROOT / "out" / ".roundtrip" / "KIT.dxf")
    b = summary(back)
    problems = []
    for label, x, y in zip(("blocks", "layers", "styles", "linetypes", "inserts", "attributes"), a, b):
        if label == "linetypes":
            missing = {n for n in x if n not in y}
            if missing:
                problems.append(f"linetypes missing: {missing}")
        elif label == "layers":
            diff = {k: (v, y.get(k)) for k, v in x.items() if y.get(k) != v}
            if diff:
                problems.append(f"layers differ: {diff}")
        elif x != y:
            keys = [k for k in x if x.get(k) != y.get(k)][:5]
            problems.append(f"{label} differ, e.g. {[(k, x.get(k), y.get(k)) for k in keys]}")
    audit = back.audit()
    if audit.errors:
        problems.append(f"audit errors: {[str(e.message) for e in audit.errors][:5]}")
    print(f"blocks {len(a[0])}  layers {len(a[1])}  inserts {sum(a[4].values())}  attributes {len(a[5])}")
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("DWG round trip: identical")
