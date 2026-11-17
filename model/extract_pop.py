"""Extract Kontur population hexagons inside the Điện Biên boundary -> raw/pop_dienbien.json.

Usage: python -E -P -I extract_pop.py <path to kontur_vn.gpkg>
"""
import json
import math
import sqlite3
import struct
import sys
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MPath

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
GPKG = sys.argv[1]
R = 6378137.0


def merc2ll(x, y):
    return math.degrees(math.atan(math.sinh(y / R))), math.degrees(x / R)


rel = json.load(open(HERE / "raw" / "boundary.json", encoding="utf-8"))["elements"][0]
segs = [[(p["lon"], p["lat"]) for p in m["geometry"]] for m in rel["members"] if m["type"] == "way" and m["role"] in ("outer", "")]
ring = segs.pop(0)
while segs and ring[0] != ring[-1]:
    for i, w in enumerate(segs):
        if w[0] == ring[-1]: ring += w[1:]
        elif w[-1] == ring[-1]: ring += w[::-1][1:]
        else: continue
        segs.pop(i); break
    else:
        break
poly = MPath(np.array(ring))
lons = [p[0] for p in ring]; lats = [p[1] for p in ring]
# bbox in mercator for a quick SQL prefilter via the rtree index if present
def ll2merc(lat, lon):
    return R * math.radians(lon), R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
x0, y0 = ll2merc(min(lats), min(lons)); x1, y1 = ll2merc(max(lats), max(lons))

con = sqlite3.connect(GPKG)
tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
rt = [t for t in tables if t.startswith("rtree_population")]
if rt:
    q = f"select p.h3, p.population, p.geom from population p join {rt[0]} r on p.fid = r.id where r.maxx >= ? and r.minx <= ? and r.maxy >= ? and r.miny <= ?"
    rows = con.execute(q, (x0, x1, y0, y1))
else:
    rows = con.execute("select h3, population, geom from population")
out = []
for h3, pop, g in rows:
    flags = g[3]; env = (flags >> 1) & 7
    envlen = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[env]
    off = 8 + envlen
    bo = "<" if g[off] == 1 else ">"
    gtype = struct.unpack(bo + "I", g[off + 1:off + 5])[0] % 1000
    p = off + 5
    if gtype == 6:  # multipolygon -> first polygon
        p += 4; bo = "<" if g[p] == 1 else ">"; p += 5
    nrings = struct.unpack(bo + "I", g[p:p + 4])[0]; p += 4
    npts = struct.unpack(bo + "I", g[p:p + 4])[0]; p += 4
    pts = [struct.unpack(bo + "dd", g[p + 16 * i:p + 16 * i + 16]) for i in range(npts)]
    ll = [merc2ll(x, y) for x, y in pts]
    clat = sum(a for a, _ in ll[:-1]) / (len(ll) - 1); clon = sum(b for _, b in ll[:-1]) / (len(ll) - 1)
    if not poly.contains_point((clon, clat)):
        continue
    out.append({"h3": h3, "pop": float(pop), "lat": clat, "lon": clon, "ring": [[round(b, 5), round(a, 5)] for a, b in ll[:-1]]})
(HERE / "raw" / "pop_dienbien.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
print("hexes inside:", len(out), "population:", round(sum(o["pop"] for o in out)))
