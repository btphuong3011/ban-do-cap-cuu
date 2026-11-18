"""HOT populated-places GeoJSON zip -> raw/places_hot.json (Overpass-like) for the Điện Biên bbox."""
import json, sys, zipfile
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
S, W, N, E = 20.89, 102.14, 22.55, 103.60
z = zipfile.ZipFile(sys.argv[1]); out = []
for nm in z.namelist():
    if not nm.endswith((".geojson", ".json")): continue
    gj = json.loads(z.read(nm).decode("utf-8"))
    for ft in gj.get("features", []):
        g = ft.get("geometry") or {}; pr = ft.get("properties") or {}
        if g.get("type") == "Point": x, y = g["coordinates"][:2]
        elif g.get("type") in ("Polygon", "MultiPolygon"):
            ring = g["coordinates"][0] if g["type"] == "Polygon" else g["coordinates"][0][0]
            x = sum(p[0] for p in ring) / len(ring); y = sum(p[1] for p in ring) / len(ring)
        else: continue
        if not (S <= y <= N and W <= x <= E): continue
        tags = {k: str(v) for k, v in pr.items() if k in ("name", "place", "name:vi") and v}
        out.append({"type": "node", "lat": y, "lon": x, "tags": tags})
    print(nm, "features in bbox so far:", len(out))
Path(sys.argv[2]).write_text(json.dumps({"elements": out}, ensure_ascii=False), encoding="utf-8")
import collections; print(collections.Counter(e["tags"].get("place") for e in out).most_common())
