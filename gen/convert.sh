#!/bin/sh
# DXF -> DWG (AutoCAD 2018 format) with the free ODA File Converter, then
# DWG -> DXF again into out/.roundtrip so that check_dwg.py can compare the two.
# Usage: ODA_CONVERTER=/path/to/ODAFileConverter gen/convert.sh
# Download: https://www.opendesign.com/guestfiles/oda_file_converter
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
: "${ODA_CONVERTER:?set ODA_CONVERTER to the ODAFileConverter binary}"
TMP=$(mktemp -d)
mkdir -p "$TMP/in" "$TMP/dwg" "$ROOT/out/.roundtrip"
cp "$ROOT/out/KIT.dxf" "$TMP/in/"
"$ODA_CONVERTER" "$TMP/in" "$TMP/dwg" ACAD2018 DWG 0 1 "*.dxf" >/dev/null 2>&1
test -s "$TMP/dwg/KIT.dwg" || { echo "conversion failed: no KIT.dwg" >&2; exit 1; }
cp "$TMP/dwg/KIT.dwg" "$ROOT/out/KIT.dwg"
"$ODA_CONVERTER" "$TMP/dwg" "$ROOT/out/.roundtrip" ACAD2018 DXF 0 1 "*.dwg" >/dev/null 2>&1
test -s "$ROOT/out/.roundtrip/KIT.dxf" || { echo "round trip failed" >&2; exit 1; }
ls "$TMP/dwg" | grep -i "\.err$" && { echo "the converter reported errors:" >&2; cat "$TMP"/dwg/*.err >&2; exit 1; } || true
rm -rf "$TMP"
echo "out/KIT.dwg written"
