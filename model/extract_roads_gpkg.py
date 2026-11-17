"""Convert the HOT Vietnam roads GeoPackage into an Overpass-like JSON for the Điện Biên bbox.

Usage: python -E -P extract_roads_gpkg.py <zip or gpkg path>
Writes raw/gp_roads.json with synthetic node ids (shared vertices => shared nodes).
"""
import json
import sqlite3
import struct
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
src = Path(sys.argv[1])
if src.suffix == ".zip":
    with zipfile.ZipFile(src) as z:
        name = [n for n in z.namelist() if n.endswith(".gpkg")][0]
        out = src.parent / Path(name).name
        if not out.exists():
            with z.open(name) as f, open(out, "wb") as g:
                while True:
                    b = f.read(1 << 22)
                    if not b: break
                    g.write(b)
        src = out
print("gpkg:", src, src.stat().st_size // 1_000_000, "MB")
con = sqlite3.connect(src)
tabs = list(con.execute("select table_name, srs_id from gpkg_contents where data_type='features'"))
print("feature tables:", tabs)
table, srs = tabs[0]
cols = [r[1] for r in con.execute(f'pragma table_info("{table}")')]
print("columns:", cols[:30])
gcol = [r[0] for r in con.execute("select column_name from gpkg_geometry_columns where table_name=?", (table,))][0]
S, W, N, E = 20.89, 102.14, 22.55, 103.60
rt = f"rtree_{table}_{gcol}"
have_rt = con.execute("select count(*) from sqlite_master where name=?", (rt,)).fetchone()[0]
want = [c for c in ("osm_id", "highway", "name", "ref", "name:en") if c in cols]
sel = ", ".join(f't."{c}"' for c in want)
if have_rt:
    q = f'select t.fid, {sel}, t."{gcol}" from "{table}" t join "{rt}" r on t.fid = r.id where r.maxx >= ? and r.minx <= ? and r.maxy >= ? and r.miny <= ?'
    rows = con.execute(q, (W, E, S, N))
else:
    rows = con.execute(f'select t.fid, {sel}, t."{gcol}" from "{table}" t')
KEEP = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street", "track", "road",
        "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link", "service"}


def lines(g):
    flags = g[3]; env = (flags >> 1) & 7
    off = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[env]

    def read(p):
        bo = "<" if g[p] == 1 else ">"
        t = struct.unpack(bo + "I", g[p + 1:p + 5])[0] % 1000
        p += 5
        if t == 2:
            n = struct.unpack(bo + "I", g[p:p + 4])[0]; p += 4
            pts = [struct.unpack(bo + "dd", g[p + 16 * i:p + 16 * i + 16]) for i in range(n)]
            return [pts], p + 16 * n
        if t == 5:
            n = struct.unpack(bo + "I", g[p:p + 4])[0]; p += 4; acc = []
            for _ in range(n):
                ls, p = read(p); acc += ls
            return acc, p
        return [], p
    return read(off)[0]


nodes, elements, nid = {}, [], 0
nways = 0
for row in rows:
    fid = row[0]; vals = dict(zip(want, row[1:1 + len(want)])); g = row[-1]
    hw = vals.get("highway")
    if hw not in KEEP or g is None:
        continue
    for li, pts in enumerate(lines(g)):
        if not any(S <= y <= N and W <= x <= E for x, y in pts):
            continue
        ids = []
        for x, y in pts:
            k = (round(x, 7), round(y, 7))
            if k not in nodes:
                nid += 1; nodes[k] = nid
            ids.append(nodes[k])
        tags = {"highway": hw}
        for c in ("name", "ref"):
            if vals.get(c): tags[c] = vals[c]
        elements.append({"type": "way", "id": int(vals.get("osm_id") or fid) * 10 + li, "nodes": ids, "tags": tags})
        nways += 1
for (x, y), i in nodes.items():
    elements.append({"type": "node", "id": i, "lat": y, "lon": x})
(HERE / "raw" / "gp_roads.json").write_text(json.dumps({"elements": elements}, separators=(",", ":")), encoding="utf-8")
print("ways", nways, "nodes", len(nodes))
