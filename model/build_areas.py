"""Bản Đồ Cấp Cứu v3 – adds named settlement areas and routes (for the birth-plan card) on top of data2.json.

Reuses the graph/facility/hex setup of build_model.py, re-runs one Dijkstra per facility with predecessors,
groups population hexes by nearest named OSM place, and stores the route from each area's most populous hex
to its nearest facilities. Writes out/data3.json.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

HERE = Path(__file__).parent
_src = (HERE / "build_model.py").read_text(encoding="utf-8")
exec(_src.split("t0 = time.time()\nT_base")[0])  # graph, facilities, hexes (defines N, rows, cols, wts, SRC*, hk, HW, ...)

def simplify(pts, tol=0.0005):
    if len(pts) <= 2: return pts
    a, b = np.array(pts[0]), np.array(pts[-1]); ab = b - a; L = np.hypot(*ab)
    if L == 0:
        d = [np.hypot(*(np.array(p) - a)) for p in pts[1:-1]]
    else:
        d = [abs(ab[0] * (a[1] - p[1]) - ab[1] * (a[0] - p[0])) / L for p in map(np.array, pts[1:-1])]
    i = int(np.argmax(d)) + 1
    return simplify(pts[:i + 1], tol)[:-1] + simplify(pts[i:], tol) if d[i - 1] > tol else [pts[0], pts[-1]]


sys.setrecursionlimit(20000)
d2 = json.loads((OUT / "data2.json").read_text(encoding="utf-8"))
assert len(d2["hexes"]) == H

# ---------- per-facility shortest-path trees ----------
dists, preds = [], []
for f in range(F):
    sm = SRCF == f
    r = np.concatenate([rows, np.full(int(sm.sum()), N)]); c = np.concatenate([cols, SRC[sm]])
    w = np.concatenate([wts, SRCW[sm] + 1e-6])
    d, p = dijkstra(csr_matrix((w, (r, c)), shape=(N + 1, N + 1)), directed=True, indices=N, return_predecessors=True)
    dists.append(d[:N]); preds.append(p)
HT = np.vstack([(dists[f][hk] + HW).min(axis=1) for f in range(F)]).T  # H x F
chk = np.array([[np.inf if v is None else v for v in h["t"]] for h in d2["hexes"]])
fin = np.isfinite(chk)
print("max |diff| vs data2:", float(np.max(np.abs(np.round(HT[fin]) - chk[fin]))), "finite match:", bool(np.array_equal(np.isfinite(HT), fin)))

# ---------- settlement areas: k-means clusters of hexes, named after the nearest OSM place ----------
from sklearn.cluster import KMeans
LATIN = re.compile(r"^[0-9A-Za-zÀ-ỹĐđ .,'’()\-]+$")
KINDS = ("village", "hamlet", "town", "suburb", "neighbourhood", "isolated_dwelling", "locality", "quarter", "city")
PLACE_FILES = [RAW / "places.json"] + ([RAW / "places_hot.json"] if (RAW / "places_hot.json").exists() else [])
pl, seen = [], set()
for pf in PLACE_FILES:
    for e in json.loads(pf.read_text(encoding="utf-8"))["elements"]:
        nm = (e.get("tags") or {}).get("name") or ""
        if e["tags"].get("place", "locality") not in KINDS or not LATIN.match(nm or "@"): continue
        if not poly.contains_point((e["lon"], e["lat"])): continue
        key = (nm, round(e["lat"], 3), round(e["lon"], 3))
        if key in seen: continue
        seen.add(key); pl.append(e)
print("named places inside province:", len(pl))
PXY = np.array([[e["lon"] * KX, e["lat"] * KY] for e in pl]); ptree = cKDTree(PXY)
K = int(sys.argv[1]) if len(sys.argv) > 1 else 240
km = KMeans(n_clusters=K, n_init=4, random_state=7).fit(HXY, sample_weight=np.sqrt(np.maximum(POP, 1)))
lab_ = km.labels_
SHORT = ["BV Đa khoa tỉnh", "TTYT Điện Biên", "Điện Biên Đông", "Mường Ảng", "Tuần Giáo", "Tủa Chùa", "Mường Chà",
         "Mường Lay", "Nậm Pồ", "Mường Nhé"]
GROUP = ["TP. Điện Biên Phủ", "Điện Biên"] + SHORT[2:]
FXY = np.array([[f["lon"] * KX, f["lat"] * KY] for f in fac])
DIRS = ["Đông", "Đông Bắc", "Bắc", "Tây Bắc", "Tây", "Tây Nam", "Nam", "Đông Nam"]


def path_coords(f, i):
    """Route hex i -> facility f, delta-encoded ints of 1e-4 degree: [x0, y0, dx1, dy1, ...]."""
    cand = hk[i]; tot = dists[f][cand] + HW[i]
    if not np.isfinite(tot.min()):
        return None
    v = int(cand[int(np.argmin(tot))]); pts = [(hexes[i]["lon"], hexes[i]["lat"])]
    guard = 0
    while v != N and v >= 0 and guard < 200000:
        la, lo = nodes[int(inv[v])]; pts.append((lo, la)); v = int(preds[f][v]); guard += 1
    pts.append((fac[f]["lon"], fac[f]["lat"]))
    q = [(int(round(x * 1e4)), int(round(y * 1e4))) for x, y in simplify(pts, 0.002)]
    out = [q[0][0], q[0][1]]
    for (x0, y0), (x1, y1) in zip(q, q[1:]):
        out += [x1 - x0, y1 - y0]
    return out


areas, hex_area, used = [], np.full(H, -1), {}
cl_ids = [np.where(lab_ == k)[0] for k in range(K)]
cl_ids = [ids for ids in cl_ids if POP[ids].sum() > 0]
cl_ids.sort(key=lambda ids: -POP[ids].sum())
for ids in cl_ids:
    pop = POP[ids].sum()
    rep = int(ids[np.argmax(POP[ids])])
    cx = float((np.array([hexes[i]["lon"] for i in ids]) * POP[ids]).sum() / pop)
    cy = float((np.array([hexes[i]["lat"] for i in ids]) * POP[ids]).sum() / pop)
    dkm, pk = ptree.query([cx * KX, cy * KY])
    place = pl[pk]["tags"]["name"]; dkm = float(dkm)
    ang = np.degrees(np.arctan2(cy * KY - PXY[pk, 1], cx * KX - PXY[pk, 0])) % 360
    dr = DIRS[int(((ang + 22.5) % 360) // 45)]
    if dkm <= 2.5 and place not in used:
        lbl, dd = place, 0; used[place] = 1
    else:
        dd = max(1, int(round(dkm))); lbl = f"{place} · {dd} km hướng {dr}"
    g = int(np.argmin(np.hypot(FXY[:, 0] - cx * KX, FXY[:, 1] - cy * KY)))
    order = [int(f) for f in np.argsort(HT[rep]) if np.isfinite(HT[rep][f])][:3]
    if 0 not in order and np.isfinite(HT[rep][0]):
        order.append(0)
    routes = {}
    for f in order:
        pc = path_coords(f, rep)
        if pc: routes[str(f)] = pc
    hex_area[ids] = len(areas)
    areas.append({"n": lbl, "pl": place, "d": dd, "dir": dr if dd else "", "g": g, "c": [round(cx, 4), round(cy, 4)],
                  "p": int(round(pop)), "r": rep, "rt": routes})
print("areas:", len(areas), "pop range", min(a["p"] for a in areas), max(a["p"] for a in areas),
      "route ints:", sum(len(v) for a in areas for v in a["rt"].values()))
print("sample names:", [a["n"] for a in areas[:12]])

# ---------- export ----------
hx = []
for i, h in enumerate(d2["hexes"]):
    hx.append({"r": h["r"], "p": h["p"], "t": h["t"], "x": h["x"], "a": int(hex_area[i])})
roads = [{"c": r["c"], "p": r["p"]} for r in d2["roads"]]
facs = [dict(f, s=SHORT[i], g=GROUP[i]) for i, f in enumerate(d2["facilities"])]
data = {"cbr": d2["cbr"], "limit": d2["limit"], "pop": d2["pop"], "facilities": facs, "hexes": hx, "roads": roads,
        "closures": d2["closures"], "greedy": d2["greedy"], "boundary": d2["boundary"], "areas": areas}
(OUT / "data3.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("data3.json KB", (OUT / "data3.json").stat().st_size // 1024)
# quick look: biggest areas outside 2h when only the province hospital operates
tA = HT[:, 0]
rowsA = sorted(((float(POP[(hex_area == a) & (tA > LIMIT)].sum()), areas[a]["n"], GROUP[areas[a]["g"]]) for a in range(len(areas))), reverse=True)[:8]
print("top areas outside 2h (A):", [(round(p), n, g) for p, n, g in rowsA])
print("areas with any pop outside 2h (A):", sum(1 for a in range(len(areas)) if POP[(hex_area == a) & (tA > LIMIT)].sum() > 0))
