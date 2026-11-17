"""Bản Đồ Cấp Cứu v2 – road-graph model for Điện Biên, population-weighted (Kontur H3 hexagons).

Outputs out/data2.json (web map) and out/stats2.json (dossier).
"""
import glob
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MPath
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra, connected_components
from scipy.spatial import cKDTree

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
RAW, OUT = HERE / "raw", HERE / "out"
OUT.mkdir(exist_ok=True)
SPEED = {"motorway": 50, "motorway_link": 45, "trunk": 45, "trunk_link": 45, "primary": 40, "primary_link": 40,
         "secondary": 35, "secondary_link": 35, "tertiary": 28, "tertiary_link": 28, "unclassified": 22, "road": 22,
         "residential": 18, "living_street": 15, "service": 15, "track": 12}
CLS = {"motorway": 0, "motorway_link": 0, "trunk": 0, "trunk_link": 0, "primary": 0, "primary_link": 0,
       "secondary": 1, "secondary_link": 1, "tertiary": 2, "tertiary_link": 2,
       "unclassified": 3, "road": 3, "residential": 3, "living_street": 4, "service": 4, "track": 4}
WALK, LIMIT = 4.0, 120
FACILITIES = [
    (1204399183, "Bệnh viện Đa khoa tỉnh Điện Biên", "tinh"),
    (1204399213, "Trung tâm Y tế huyện Điện Biên", "khu_vuc"),
    (1204399212, "Trung tâm Y tế Điện Biên Đông", "khu_vuc"),
    (1204399209, "Trung tâm Y tế Mường Ảng", "khu_vuc"),
    (1204399208, "Trung tâm Y tế Tuần Giáo", "khu_vuc"),
    (1204399207, "Trung tâm Y tế Tủa Chùa", "khu_vuc"),
    (656686155, "Trung tâm Y tế Mường Chà", "khu_vuc"),
    (692586121, "Trung tâm Y tế Mường Lay", "khu_vuc"),
    (1204399206, "Trung tâm Y tế Nậm Pồ", "khu_vuc"),
    (532934088, "Trung tâm Y tế Mường Nhé", "khu_vuc"),
]
LAT0 = 21.7
KX, KY = 111.32 * math.cos(math.radians(LAT0)), 110.57


def hav(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


# ---------- boundary ----------
rel = json.load(open(RAW / "boundary.json", encoding="utf-8"))["elements"][0]
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

# ---------- roads ----------
nodes, ways = {}, {}
FILES = [str(RAW / "gp_roads.json")] if (RAW / "gp_roads.json").exists() else sorted(glob.glob(str(RAW / "rp_*.json")) + glob.glob(str(RAW / "rq_*.json")))
print("road files:", [Path(f).name for f in FILES])
for f in FILES:
    for e in json.load(open(f, encoding="utf-8"))["elements"]:
        if e["type"] == "node": nodes[e["id"]] = (e["lat"], e["lon"])
        elif e["type"] == "way": ways[e["id"]] = e
nid_arr = np.array(list(nodes.keys())); ll = np.array([nodes[n] for n in nid_arr])
ins = poly.contains_points(ll[:, ::-1])
keep = set(nid_arr[ins].tolist())
print("osm nodes", len(nodes), "inside", len(keep), "ways", len(ways))
idx, rows, cols, wts, eway = {}, [], [], [], []
way_nodes = {}
for wid, w in ways.items():
    sp = SPEED.get(w["tags"].get("highway"))
    if not sp: continue
    ns = [n for n in w["nodes"] if n in keep]
    if len(ns) < 2: continue
    way_nodes[wid] = ns
    for a, b in zip(w["nodes"], w["nodes"][1:]):
        if a in keep and b in keep:
            ia = idx.setdefault(a, len(idx)); ib = idx.setdefault(b, len(idx))
            t = hav(nodes[a], nodes[b]) / sp * 60
            rows += [ia, ib]; cols += [ib, ia]; wts += [t, t]; eway += [wid, wid]
N = len(idx)
rows, cols, wts, eway = (np.array(v) for v in (rows, cols, wts, eway))
G0 = csr_matrix((wts, (rows, cols)), shape=(N, N))
ncomp, lab = connected_components(G0, directed=False)
big = np.bincount(lab).argmax()
print("graph nodes", N, "edges", len(rows) // 2, "components", ncomp, "largest", int(np.sum(lab == big)))
inv = np.empty(N, dtype=np.int64)
for k, i in idx.items(): inv[i] = k
XY = np.array([[nodes[k][1] * KX, nodes[k][0] * KY] for k in inv])
main = np.where(lab == big)[0]
tree_main = cKDTree(XY[main]); tree_all = cKDTree(XY)

# ---------- facilities (snap to nearest node of the main component) ----------
hosp = {e["id"]: e for e in json.load(open(RAW / "hosp.json", encoding="utf-8"))["elements"]}
fac = []
for wid, name, kind in FACILITIES:
    c = hosp[wid]["center"]
    d, k = tree_main.query([c["lon"] * KX, c["lat"] * KY], k=8)
    sel = [(int(main[kk]), float(dd)) for dd, kk in zip(d, k) if dd <= max(1.5, d[0] + 0.3)][:8]
    fac.append({"name": name, "kind": kind, "lat": c["lat"], "lon": c["lon"], "node": sel[0][0],
                "snaps": [n for n, _ in sel], "walks": [dd / WALK * 60 for _, dd in sel]})
F = len(fac)
SRC = np.array([n for f in fac for n in f["snaps"]]); SRCW = np.array([w for f in fac for w in f["walks"]])
SRCF = np.array([i for i, f in enumerate(fac) for _ in f["snaps"]])
print("facility snap nodes:", [len(f["snaps"]) for f in fac])

# ---------- population hexes ----------
hexes = json.load(open(RAW / "pop_dienbien.json", encoding="utf-8"))
H = len(hexes); POP = np.array([h["pop"] for h in hexes]); TOT = POP.sum()
HXY = np.array([[h["lon"] * KX, h["lat"] * KY] for h in hexes])
hd, hk = tree_all.query(HXY, k=8)
HW = hd / WALK * 60
print("hexes", H, "population", round(TOT))


def fac_times(G):
    D = dijkstra(G, directed=False, indices=SRC) + SRCW[:, None]  # (snaps) x N
    return np.vstack([D[SRCF == f].min(axis=0) for f in range(F)])


def hex_times(T):  # T: F x N -> H x F
    out = np.empty((H, F))
    for f in range(F):
        out[:, f] = (T[f][hk] + HW).min(axis=1)
    return out


def cov(HT, enabled, limit=LIMIT):
    t = HT[:, enabled].min(axis=1)
    return float(POP[t <= limit].sum() / TOT), t


t0 = time.time()
T_base = fac_times(G0); HT = hex_times(T_base)
print("base %.1fs" % (time.time() - t0))
ALL, PROV = list(range(F)), [0]
cA, tA = cov(HT, PROV); cB, tB = cov(HT, ALL)


def wmedian(t):
    o = np.argsort(t); c = np.cumsum(POP[o]); return float(t[o][np.searchsorted(c, TOT / 2)])


print(f"pop coverage A {cA:.1%}  B {cB:.1%}  medianA {wmedian(tA):.0f}  medianB {wmedian(tB):.0f}")
# sanity: Mường Nhé TTYT -> province hospital
print("sanity Muong Nhe -> BV tinh (min):", round(float(T_base[0][fac[9]["node"]]), 1))

# ---------- greedy upgrade order ----------
chosen, rem, order = [0], list(range(1, F)), []
while rem:
    b = max(rem, key=lambda i: cov(HT, chosen + [i])[0]); chosen.append(b); rem.remove(b)
    order.append({"facility": fac[b]["name"], "coverage": round(cov(HT, chosen)[0] * 100, 1)})
print("greedy", order[:4])

# ---------- critical segments (one super-source Dijkstra per closure, scenario B and A) ----------
def super_times(mask, srcs):
    sm = np.isin(SRCF, srcs)
    r = np.concatenate([rows[mask], np.full(int(sm.sum()), N)]); c = np.concatenate([cols[mask], SRC[sm]])
    w = np.concatenate([wts[mask], SRCW[sm] + 1e-6])
    G = csr_matrix((w, (r, c)), shape=(N + 1, N + 1))
    d = dijkstra(G, directed=True, indices=N)[:N]
    return (d[hk] + HW).min(axis=1)


base_A = super_times(np.ones(len(rows), bool), PROV)
# flow-based candidate selection: population routed over each major road on the shortest-path tree (scenario B)
r_ = np.concatenate([rows, np.full(len(SRC), N)]); c_ = np.concatenate([cols, SRC]); w_ = np.concatenate([wts, SRCW + 1e-6])
dS, pred = dijkstra(csr_matrix((w_, (r_, c_)), shape=(N + 1, N + 1)), directed=True, indices=N, return_predecessors=True)
dS = dS[:N]
tot = dS[hk] + HW
bk = np.argmin(tot, axis=1); hn = hk[np.arange(H), bk]
base_B = tot[np.arange(H), bk]
load = np.zeros(N + 1); np.add.at(load, hn, POP)
fin = np.where(np.isfinite(dS))[0]
for v in fin[np.argsort(-dS[fin])]:
    p = pred[v]
    if p >= 0 and p != N: load[p] += load[v]
flow = {}
for e in np.where(pred[cols] == rows)[0]:
    w = int(eway[e]); f = load[cols[e]]
    if f > flow.get(w, 0): flow[w] = f
MAJOR = ("trunk", "primary", "secondary", "tertiary", "trunk_link", "primary_link", "secondary_link", "tertiary_link")
FXY = np.array([[f["lon"] * KX, f["lat"] * KY] for f in fac])
def far_from_facilities(w):
    ns = way_nodes[w]; la, lo = nodes[ns[len(ns) // 2]]
    return np.min(np.hypot(FXY[:, 0] - lo * KX, FXY[:, 1] - la * KY)) > 2.0
cand = [w for w in flow if ways[w]["tags"].get("highway") in MAJOR and far_from_facilities(w)]
seg_km = {w: sum(hav(nodes[a], nodes[b]) for a, b in zip(way_nodes[w], way_nodes[w][1:])) for w in cand}
cand = sorted([w for w in cand if seg_km[w] >= 0.1], key=lambda w: -flow[w])[:int(sys.argv[1]) if len(sys.argv) > 1 else 150]
print("closure candidates (by routed population)", len(cand)); t0 = time.time()
res = []
for k, w in enumerate(cand):
    m = eway != w
    tb = super_times(m, ALL)
    lostB = float(POP[(base_B <= LIMIT) & (tb > LIMIT)].sum())
    extra = float((np.minimum(tb, 900) - np.minimum(base_B, 900)) @ POP)
    res.append((lostB, extra, w))
    if k % 200 == 0: print("  ..", k, "%.0fs" % (time.time() - t0), flush=True)
res.sort(reverse=True)
_pl = [e for e in json.load(open(RAW / "places.json", encoding="utf-8"))["elements"] if e["tags"].get("name") and e["tags"].get("place") in ("village", "hamlet", "town", "suburb", "neighbourhood", "isolated_dwelling")]
_pt = cKDTree(np.array([[e["lon"] * KX, e["lat"] * KY] for e in _pl]))
def near_name(lat, lon):
    return _pl[_pt.query([lon * KX, lat * KY])[1]]["tags"]["name"]
top = []
seen_refs = set()
for lostB, extra, w in res:
    tg = ways[w]["tags"]; ns = way_nodes[w]; mid = nodes[ns[len(ns) // 2]]
    key = (tg.get("ref") or tg.get("name") or str(w), round(mid[0], 1), round(mid[1], 1))
    if key in seen_refs: continue
    seen_refs.add(key)
    top.append({"way": w, "ref": tg.get("ref", ""), "name": tg.get("name", ""), "near": near_name(*mid), "highway": tg.get("highway"), "km": round(seg_km[w], 1),
                "lost_pop": int(round(lostB)), "extra_person_min": int(round(extra)), "lat": round(mid[0], 4), "lon": round(mid[1], 4),
                "line": [[round(nodes[n][1], 5), round(nodes[n][0], 5)] for n in ns]})
    if len(top) >= 5: break
for t in top: print("  closure", t["ref"], t["name"], t["km"], "km lost pop", t["lost_pop"])

# per-facility times for the top-3 closures (for the web toggle)
variants = []
for t in top[:3]:
    Tv = fac_times(csr_matrix((wts[eway != t["way"]], (rows[eway != t["way"]], cols[eway != t["way"]])), shape=(N, N)))
    variants.append((Tv, hex_times(Tv)))
cov_closure = [round(cov(v[1], ALL)[0] * 100, 1) for v in variants]

# sensitivity on drive speeds
sens = {}
for fct in (0.8, 1.25):
    HTs = np.empty((H, F))
    for f in range(F):
        HTs[:, f] = (((T_base[f] - SRCW[f]) / fct + SRCW[f])[hk] + HW).min(axis=1)
    sens[str(fct)] = {"A": round(cov(HTs, PROV)[0] * 100, 1), "B": round(cov(HTs, ALL)[0] * 100, 1)}
print("sensitivity", sens)

# ---------- export ----------
def rr(v): return None if not np.isfinite(v) else int(round(v))
def simplify(pts, tol=0.0005):
    if len(pts) <= 2: return pts
    a, b = np.array(pts[0]), np.array(pts[-1]); ab = b - a; L = np.hypot(*ab)
    if L == 0: return [pts[0], pts[-1]]
    d = [abs(ab[0] * (a[1] - p[1]) - ab[1] * (a[0] - p[0])) / L for p in map(np.array, pts[1:-1])]
    i = int(np.argmax(d)) + 1
    return simplify(pts[:i + 1], tol)[:-1] + simplify(pts[i:], tol) if d[i - 1] > tol else [pts[0], pts[-1]]
roads = []
for w, ns in way_nodes.items():
    hwy = ways[w]["tags"]["highway"]
    c = CLS.get(hwy, 4)
    if c > 3 or hwy in ("residential", "living_street"): continue
    mid = idx.get(ns[len(ns) // 2])
    if mid is None: continue
    rd = {"c": c, "p": simplify([(round(nodes[n][1], 4), round(nodes[n][0], 4)) for n in ns]), "t": [rr(T_base[f, mid]) for f in range(F)]}
    xs = []
    for Tv, _ in variants:
        tv = [rr(Tv[f, mid]) for f in range(F)]
        xs.append(0 if tv == rd["t"] else tv)
    rd["x"] = xs
    roads.append(rd)
hx = []
for i, h in enumerate(hexes):
    e = {"r": h["ring"], "p": int(round(h["pop"])), "t": [rr(v) for v in HT[i]]}
    e["x"] = [[rr(v) for v in var[1][i]] if not np.allclose(np.nan_to_num(var[1][i], posinf=1e9), np.nan_to_num(HT[i], posinf=1e9)) else 0 for var in variants]
    hx.append(e)
CBR = 18.72  # births per 1000 population, Điện Biên, NSO mid-term population survey 1/4/2024 (Biểu 16)
data = {"cbr": CBR, "facilities": [{k: f[k] for k in ("name", "kind", "lat", "lon")} for f in fac], "limit": LIMIT, "pop": int(round(TOT)),
        "hexes": hx, "roads": roads, "closures": [{k: v for k, v in t.items() if k != "way"} for t in top[:3]],
        "closure_cov": cov_closure, "greedy": order,
        "boundary": [[round(x, 4), round(y, 4)] for x, y in ring[::5]]}
(OUT / "data2.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
over_A = float(POP[tA > LIMIT].sum()); over_B = float(POP[tB > LIMIT].sum())
stats = {"method": "graph", "hexes": H, "population": int(round(TOT)), "graph_nodes": N, "ways": len(way_nodes),
         "coverage_A": round(cA * 100, 1), "coverage_B": round(cB * 100, 1), "pop_over2h_A": int(round(over_A)), "pop_over2h_B": int(round(over_B)),
         "median_A": round(wmedian(tA)), "median_B": round(wmedian(tB)), "births_over2h_A": round(over_A * CBR / 1000), "births_over2h_B": round(over_B * CBR / 1000),
         "sanity_muongnhe_to_province_min": round(float(T_base[0][fac[9]["node"]])), "greedy": order,
         "closures": [{k: v for k, v in t.items() if k not in ("line", "way")} for t in top], "closure_cov_B": cov_closure, "sensitivity": sens}
(OUT / "stats2.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in stats.items() if k not in ("greedy", "closures")}, ensure_ascii=False))
print("data2.json KB", (OUT / "data2.json").stat().st_size // 1024)
