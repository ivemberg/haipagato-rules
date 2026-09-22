#!/usr/bin/env python3
"""Estrae il confine Area C e i varchi dagli open data del Comune di Milano,
e verifica che la geometria regga la regola di rilevamento transiti.

Solo libreria standard: nessuna dipendenza esterna.
"""
import json, math, sys

SRC_ZTL = "ztl.geojson"           # scaricare da ds51 (vedi SOURCES.md)
SRC_VARCHI = "varchi.geojson"     # scaricare da ds82 (vedi SOURCES.md)
OUT_POLY = "area-c.geojson"
OUT_GATES = "area-c-varchi.geojson"

INNER_BUFFER_M = 50.0
MONITOR_MARGIN_M = 500.0
PRECISION = 6

LAT0 = 45.466
M_LON = 111320.0 * math.cos(math.radians(LAT0))
M_LAT = 110540.0


def to_m(p, origin):
    return ((p[0] - origin[0]) * M_LON, (p[1] - origin[1]) * M_LAT)


def dist_point_seg(p, a, b):
    ax, ay = to_m(a, p)
    bx, by = to_m(b, p)
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    if L == 0:
        return math.hypot(ax, ay)
    t = max(0.0, min(1.0, -(ax * dx + ay * dy) / L))
    return math.hypot(ax + t * dx, ay + t * dy)


def dist_to_boundary(p, ring):
    return min(dist_point_seg(p, ring[i], ring[i + 1]) for i in range(len(ring) - 1))


def inside(p, ring):
    x, y = p[0], p[1]
    c = False
    n = len(ring) - 1
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        if (y1 > y) != (y2 > y):
            if x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                c = not c
    return c


def state(p, ring, buffer_m=INNER_BUFFER_M):
    """FUORI / BANDA / DENTRO."""
    if not inside(p, ring):
        return "FUORI"
    return "DENTRO" if dist_to_boundary(p, ring) > buffer_m else "BANDA"


# ---------------------------------------------------------------- estrazione

ztl = json.load(open(SRC_ZTL))
feat = [f for f in ztl["features"] if f["properties"].get("tipo") == "AREA_C"]
assert len(feat) == 1, f"attese 1 feature AREA_C, trovate {len(feat)}"
mp = feat[0]["geometry"]["coordinates"]
assert len(mp) == 1, f"MultiPolygon con {len(mp)} poligoni, atteso 1"
assert len(mp[0]) == 1, f"poligono con {len(mp[0])} anelli, atteso 1 (nessun buco)"

ring = [[round(c[0], PRECISION), round(c[1], PRECISION)] for c in mp[0][0]]
if ring[0] != ring[-1]:
    ring.append(ring[0])

varchi_src = json.load(open(SRC_VARCHI))
gates = []
for f in varchi_src["features"]:
    c = f["geometry"]["coordinates"][:2]
    gates.append({
        "type": "Feature",
        "geometry": {"type": "Point",
                     "coordinates": [round(c[0], PRECISION), round(c[1], PRECISION)]},
        "properties": {"id": f["properties"]["id_amat"],
                       "label": f["properties"]["label"].title()},
    })

ATTRIB = ("Contiene dati del Comune di Milano - dati.comune.milano.it, "
          "licenza CC BY 4.0")

poly_fc = {
    "type": "FeatureCollection",
    "attribution": ATTRIB,
    "source": "https://dati.comune.milano.it/dataset/ds51_trafficotrasporti_aree_pedonali_ztl",
    "features": [{
        "type": "Feature",
        "properties": {"id": "area-c", "name": "Area C - Cerchia dei Bastioni"},
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }],
}
gates_fc = {
    "type": "FeatureCollection",
    "attribution": ATTRIB,
    "source": "https://dati.comune.milano.it/dataset/ds82_infogeo_varchi_elettronici_localizzazione_",
    "note": "Usati solo per dare un nome alla notifica, mai per rilevare un transito.",
    "features": gates,
}

# ---------------------------------------------------------------- monitorRegion

xs = [c[0] for c in ring]
ys = [c[1] for c in ring]
bbox = (min(xs), min(ys), max(xs), max(ys))
cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
half_w = (bbox[2] - bbox[0]) / 2 * M_LON
half_h = (bbox[3] - bbox[1]) / 2 * M_LAT
radius = math.hypot(half_w, half_h) + MONITOR_MARGIN_M

# ---------------------------------------------------------------- verifiche

fails = []
def check(name, ok, detail=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        fails.append(name)

print("\n== struttura ==")
check("poligono chiuso", ring[0] == ring[-1])
check("anello singolo, nessun buco", True, f"{len(ring)} vertici")
check("varchi estratti", len(gates) == 42, f"{len(gates)} punti")

print("\n== varchi vs confine ==")
gd = [(dist_to_boundary(g["geometry"]["coordinates"], ring), g["properties"]["label"])
      for g in gates]
check("tutti i varchi entro 40 m dal confine", max(d for d, _ in gd) <= 40.0,
      f"max {max(gd)[0]:.1f} m, mediana {sorted(gd)[len(gd)//2][0]:.1f} m")

print("\n== punti noti ==")
DUOMO = [9.191926, 45.464211]
CENTRALE = [9.204289, 45.487003]
check("Duomo DENTRO", state(DUOMO, ring) == "DENTRO", state(DUOMO, ring))
check("Stazione Centrale FUORI", state(CENTRALE, ring) == "FUORI", state(CENTRALE, ring))

print("\n== percorso simulato lungo la Cerchia dei Bastioni ==")
# Il confine coincide con la carreggiata dei Bastioni: uso un tratto dell'anello
# come traccia GPS di chi percorre la circonvallazione senza entrare.
start = len(ring) // 4
route = ring[start:start + 260]
states = [state(p, ring) for p in route]
n_dentro = sum(1 for s in states if s == "DENTRO")

# quanti varchi vengono sfiorati lungo il tratto
near = set()
for p in route:
    for g in gates:
        if dist_point_seg(g["geometry"]["coordinates"], p, p) < 80:
            near.add(g["properties"]["label"])

check("il percorso sfiora almeno 3 varchi", len(near) >= 3,
      f"{len(near)} varchi: {', '.join(sorted(near)[:6])}")
check("zero punti in stato DENTRO lungo i Bastioni", n_dentro == 0,
      f"{n_dentro} su {len(route)} punti")

# Caso peggiore: lo stesso percorso con errore GPS di 10-25 m spinto
# deliberatamente verso l'interno, che e' la direzione che genera falsi positivi.
import random
random.seed(1)
jitter = []
for i, p in enumerate(route):
    a = ring[i + start]
    b = ring[min(i + start + 1, len(ring) - 1)]
    dx = (b[0] - a[0]) * M_LON
    dy = (b[1] - a[1]) * M_LAT
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L          # normale unitaria, in metri
    off = random.uniform(10, 25)
    cands = [[p[0] + nx * off / M_LON, p[1] + ny * off / M_LAT],
             [p[0] - nx * off / M_LON, p[1] - ny * off / M_LAT]]
    # tengo lo spostamento che va verso l'interno, cioe' il caso sfavorevole
    cands.sort(key=lambda q: (not inside(q, ring), -dist_to_boundary(q, ring)))
    jitter.append(cands[0])

depth = max((dist_to_boundary(q, ring) if inside(q, ring) else 0.0) for q in jitter)
jd = sum(1 for q in jitter if state(q, ring) == "DENTRO")
check("il rumore spinge davvero verso l'interno", depth > 15.0,
      f"profondita max raggiunta {depth:.1f} m")
check("zero DENTRO con errore GPS 25 m verso l'interno", jd == 0,
      f"{jd} su {len(jitter)} punti, buffer {INNER_BUFFER_M:.0f} m")

# ---------------------------------------------------------------- scrittura

if fails:
    print(f"\n!! {len(fails)} verifiche fallite, non scrivo nulla: {fails}")
    sys.exit(1)

for path, data in ((OUT_POLY, poly_fc), (OUT_GATES, gates_fc)):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")

print("\n== monitorRegion (margine 500 m oltre il bbox) ==")
print(f"  centro  {cy:.6f}, {cx:.6f}")
print(f"  raggio  {radius:.0f} m")
print(f"  bbox    {bbox[0]:.6f},{bbox[1]:.6f} .. {bbox[2]:.6f},{bbox[3]:.6f}")
print(f"\nscritti {OUT_POLY} e {OUT_GATES}")
