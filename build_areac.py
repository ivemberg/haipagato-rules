#!/usr/bin/env python3
"""Estrae il confine Area C e i varchi dagli open data del Comune di Milano
e verifica che la geometria regga la regola di rilevamento transiti.

Uso:  python3 tools/build_areac.py

Scarica i dataset (cache in tools/.cache/), scrive rules/area-c.geojson e
rules/area-c-varchi.geojson, poi esegue le verifiche. Se una verifica fallisce
non scrive nulla.

Solo libreria standard: nessuna dipendenza esterna.
"""
import json, math, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "tools" / ".cache"
OUT = ROOT / "rules"

DS_ZTL = ("https://dati.comune.milano.it/dataset/d7d9179a-8228-427f-9c86-1e30154be4fe/"
          "resource/d788b26b-31b4-4e57-992d-276a1280c8c2/download/disciplina_aree.geojson")
DS_VARCHI = ("https://dati.comune.milano.it/dataset/4cad1605-8225-4ecd-9b82-868b3af453e5/"
             "resource/fa8fcc31-1722-4a50-a0ae-ce7b9c0d0361/download/ingressi_areac_varchi.geojson")

# Parametri di rilevamento. Devono restare allineati a rules.json -> geometry.
INNER_BUFFER_M = 50.0        # oltre questa distanza dal confine si e' DENTRO
PROBABLE_MIN_DEPTH_M = 15.0  # profondita' minima perche' un "probabile" sia credibile
PROBABLE_MIN_DWELL_S = 180.0 # permanenza minima DA FERMO dentro il poligono
STATIONARY_RADIUS_M = 25.0   # entro questo raggio il veicolo e' considerato fermo
MONITOR_MARGIN_M = 500.0
PRECISION = 6

LAT0 = 45.466
M_LON = 111320.0 * math.cos(math.radians(LAT0))
M_LAT = 110540.0

ATTRIB = ("Contiene dati del Comune di Milano - dati.comune.milano.it, "
          "licenza CC BY 4.0")


# ------------------------------------------------------------------ geometria

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
    for i in range(len(ring) - 1):
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


def crossing_time(a, b, ring):
    """Istante stimato di attraversamento del confine fra a (FUORI) e b (dentro).

    a e b sono (lon, lat, t). Bisezione sul segmento: il confine e' dove
    inside() cambia valore. Restituisce il tempo interpolato.
    """
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        p = [a[0] + (b[0] - a[0]) * mid, a[1] + (b[1] - a[1]) * mid]
        if inside(p, ring):
            hi = mid
        else:
            lo = mid
    return a[2] + (b[2] - a[2]) * (lo + hi) / 2


def classify_trip(track, ring, buffer_m=INNER_BUFFER_M,
                  min_depth=PROBABLE_MIN_DEPTH_M, min_dwell=PROBABLE_MIN_DWELL_S):
    """Macchina a stati FUORI -> BANDA -> DENTRO su un viaggio.

    track: lista di (lon, lat, t_secondi).
    Restituisce (esito, istante_attraversamento, motivo).
    """
    states = [state(p, ring, buffer_m) for p in track]
    if states[0] != "FUORI":
        return ("nessuno", None, "viaggio iniziato dentro il poligono")

    first_in = next((i for i, s in enumerate(states) if s != "FUORI"), None)
    if first_in is None:
        return ("nessuno", None, "mai entrato nel poligono")

    t_cross = crossing_time(track[first_in - 1], track[first_in], ring)

    if "DENTRO" in states[first_in:]:
        return ("confermato", t_cross, "raggiunto lo stato DENTRO")

    depth = max(dist_to_boundary(track[i], ring)
                for i in range(first_in, len(track)) if states[i] != "FUORI")
    if depth < min_depth:
        return ("nessuno", None, f"in BANDA ma profondita' {depth:.0f} m < {min_depth:.0f} m")

    # Permanenza DA FERMO in coda al viaggio, non tempo totale dentro il poligono.
    # E' la sola misura che distingue chi parcheggia da chi sta percorrendo la
    # Cerchia con l'errore GPS sbilanciato verso l'interno: il secondo non si
    # ferma mai, e il tempo totale dentro sarebbe alto per entrambi.
    last = track[-1]
    i = len(track) - 1
    while i > 0 and dist_point_seg(track[i - 1], last, last) <= STATIONARY_RADIUS_M:
        i -= 1
    dwell = last[2] - track[i][2]
    if state(last, ring, buffer_m) == "FUORI":
        return ("nessuno", None, "il viaggio finisce fuori dal poligono")
    if dwell < min_dwell:
        return ("nessuno", None, f"in BANDA ma fermo solo {dwell:.0f} s < {min_dwell:.0f} s")
    return ("probabile", t_cross, f"BANDA a {depth:.0f} m, fermo {dwell:.0f} s")


# ------------------------------------------------------------------ estrazione

def fetch(url, name):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "haipagato-build/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as fh:
            fh.write(r.read())
    return json.loads(path.read_text(encoding="utf-8"))


ztl = fetch(DS_ZTL, "disciplina_aree.geojson")
varchi_src = fetch(DS_VARCHI, "ingressi_areac_varchi.geojson")

feat = [f for f in ztl["features"] if f["properties"].get("tipo") == "AREA_C"]
assert len(feat) == 1, f"attese 1 feature AREA_C, trovate {len(feat)}"
mp = feat[0]["geometry"]["coordinates"]
assert len(mp) == 1, f"MultiPolygon con {len(mp)} poligoni, atteso 1"
assert len(mp[0]) == 1, f"poligono con {len(mp[0])} anelli, atteso 1 (nessun buco)"

ring = [[round(c[0], PRECISION), round(c[1], PRECISION)] for c in mp[0][0]]
if ring[0] != ring[-1]:
    ring.append(ring[0])

gates = [{
    "type": "Feature",
    "geometry": {"type": "Point",
                 "coordinates": [round(f["geometry"]["coordinates"][0], PRECISION),
                                 round(f["geometry"]["coordinates"][1], PRECISION)]},
    "properties": {"id": f["properties"]["id_amat"],
                   "label": f["properties"]["label"].title()},
} for f in varchi_src["features"]]

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

xs = [c[0] for c in ring]
ys = [c[1] for c in ring]
bbox = (min(xs), min(ys), max(xs), max(ys))
cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
radius = math.hypot((bbox[2] - bbox[0]) / 2 * M_LON,
                    (bbox[3] - bbox[1]) / 2 * M_LAT) + MONITOR_MARGIN_M


# ------------------------------------------------------------------ tracce di prova

DUOMO = [9.191926, 45.464211]
CENTRALE = [9.204289, 45.487003]
NORD = [9.19, 45.492]        # ben fuori, a nord del bbox


def lerp(a, b, t):
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]


def signed_depth(p):
    """Positiva dentro il poligono, negativa fuori."""
    d = dist_to_boundary(p, ring)
    return d if inside(p, ring) else -d


def sample_line(a, b, n=120, dt=2.0, t0=0.0):
    return [[*lerp(a, b, i / (n - 1)), t0 + i * dt] for i in range(n)]


def truncate_at_depth(pts, target):
    """Taglia la traccia al primo punto che raggiunge `target` metri di profondita'.

    Nessuna assunzione di monotonia: il confine e' concavo e una corda puo'
    entrare, uscire e rientrare.
    """
    for i, p in enumerate(pts):
        if signed_depth(p) >= target:
            return pts[:i + 1]
    raise AssertionError(f"la traccia non raggiunge mai {target} m di profondita'")


def nudge_outward(p, meters):
    """Sposta p di `meters` verso il punto piu' vicino del confine, e oltre.

    Simula l'errore GPS nella direzione che fa sottostimare la profondita'.
    """
    best, bd = None, float("inf")
    for i in range(len(ring) - 1):
        a, b = ring[i], ring[i + 1]
        ax, ay = to_m(a, p)
        bx, by = to_m(b, p)
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / L))
        qx, qy = ax + t * dx, ay + t * dy
        d = math.hypot(qx, qy)
        if d < bd:
            bd, best = d, (qx, qy)
    if bd == 0:
        return list(p)
    ux, uy = best[0] / bd, best[1] / bd
    return [p[0] + ux * meters / M_LON, p[1] + uy * meters / M_LAT] + list(p[2:])


def dwell(at, seconds, t0, step=10.0):
    """Punti fermi nello stesso posto, per simulare un parcheggio."""
    n = int(seconds / step) + 1
    return [[at[0], at[1], t0 + i * step] for i in range(n)]


# ------------------------------------------------------------------ verifiche

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
      f"max {max(gd)[0]:.1f} m, mediana {sorted(gd)[len(gd) // 2][0]:.1f} m")

print("\n== punti noti ==")
check("Duomo DENTRO", state(DUOMO, ring) == "DENTRO", state(DUOMO, ring))
check("Stazione Centrale FUORI", state(CENTRALE, ring) == "FUORI", state(CENTRALE, ring))

print("\n== negativi: nessun transito ==")
start = len(ring) // 4
route = ring[start:start + 260]
bast = [[p[0], p[1], i * 2.0] for i, p in enumerate(route)]
near = {g["properties"]["label"] for p in route for g in gates
        if dist_point_seg(g["geometry"]["coordinates"], p, p) < 80}
check("il percorso sui Bastioni sfiora almeno 3 varchi", len(near) >= 3,
      f"{len(near)} varchi: {', '.join(sorted(near)[:5])}")
esito, _, why = classify_trip(bast, ring)
check("giro dei Bastioni: nessun transito", esito == "nessuno", why)

import random
random.seed(1)
# la traccia deve partire FUORI, altrimenti il test passerebbe per la ragione
# sbagliata (viaggio iniziato dentro) invece che per la banda di isteresi
jit = [[NORD[0], NORD[1], -20.0], [NORD[0], NORD[1], -10.0]]
for i, p in enumerate(route):
    a, b = ring[i + start], ring[min(i + start + 1, len(ring) - 1)]
    dx, dy = (b[0] - a[0]) * M_LON, (b[1] - a[1]) * M_LAT
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    off = random.uniform(10, 25)
    cands = [[p[0] + nx * off / M_LON, p[1] + ny * off / M_LAT, i * 2.0],
             [p[0] - nx * off / M_LON, p[1] - ny * off / M_LAT, i * 2.0]]
    cands.sort(key=lambda q: (not inside(q, ring), -dist_to_boundary(q, ring)))
    jit.append(cands[0])
depth_in = max((dist_to_boundary(q, ring) if inside(q, ring) else 0.0) for q in jit)
check("il rumore sui Bastioni spinge davvero verso l'interno", depth_in > 15.0,
      f"profondita' max {depth_in:.1f} m")
check("la traccia dei Bastioni parte FUORI", state(jit[0], ring) == "FUORI")
esito, _, why = classify_trip(jit, ring)
check("Bastioni con GPS 25 m verso l'interno: nessun transito", esito == "nessuno", why)

# sosta al semaforo sulla corsia interna: dentro il poligono ma di pochi metri.
# E' il caso che probableMinDepthM deve scartare.
line = sample_line(NORD, DUOMO, n=400)
shallow = truncate_at_depth(line, 6.0)
shallow += dwell(shallow[-1][:2], 600, shallow[-1][2])
esito, _, why = classify_trip(shallow, ring)
check("sosta a 6 m dal confine per 10 min: nessun transito", esito == "nessuno", why)

# passaggio veloce in banda senza fermarsi: lo scarta probableMinDwellS
quick = truncate_at_depth(line, 30.0)
esito, _, why = classify_trip(quick, ring)
check("passaggio in banda a 30 m senza sosta: nessun transito", esito == "nessuno", why)

print("\n== positivi ==")
# 1) ingresso fino al Duomo
full = sample_line(NORD, DUOMO, n=120)
esito, t_cross, why = classify_trip(full, ring)
states_full = [state(p, ring) for p in full]
first_in = next(i for i, s in enumerate(states_full) if s != "FUORI")
ok_t = full[first_in - 1][2] <= t_cross <= full[first_in][2]
check("ingresso fino al Duomo: confermato", esito == "confermato", why)
check("orario interpolato fra ultimo FUORI e primo punto dentro", ok_t,
      f"t={t_cross:.1f}s in [{full[first_in - 1][2]:.0f}, {full[first_in][2]:.0f}]")

# 2) entra e parcheggia a 30 m dal confine
park = truncate_at_depth(line, 30.0)
pdepth = max(signed_depth(p) for p in park)
check("il parcheggio resta in banda, non tocca DENTRO", pdepth <= INNER_BUFFER_M,
      f"profondita' max {pdepth:.0f} m")
park = park + dwell(park[-1][:2], 300, park[-1][2])
esito, t_cross, why = classify_trip(park, ring)
check("parcheggio a 30 m dal confine: probabile", esito == "probabile", why)

# 3) ingresso vero a 70 m con rumore GPS di 25 m verso l'esterno: la profondita'
#    letta scende sotto la soglia DENTRO, ma l'esito non deve essere "nessuno"
deep = truncate_at_depth(line, 70.0)
noisy = [nudge_outward(p, 25.0) for p in deep]
noisy += dwell(noisy[-1][:2], 300, noisy[-1][2])
d_true = max(signed_depth(p) for p in deep)
d_read = max(signed_depth(p) for p in noisy)
check("il rumore verso l'esterno fa sottostimare la profondita'",
      d_read < d_true - 20.0, f"reale {d_true:.0f} m, letta {d_read:.0f} m")
esito, t_cross, why = classify_trip(noisy, ring)
check("rumore verso l'esterno: almeno probabile",
      esito in ("probabile", "confermato"), f"{esito} - {why}")

# ------------------------------------------------------------------ scrittura

if fails:
    print(f"\n!! {len(fails)} verifiche fallite, non scrivo nulla: {fails}")
    sys.exit(1)

for path, data in ((OUT / "area-c.geojson", poly_fc),
                   (OUT / "area-c-varchi.geojson", gates_fc)):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")

print("\n== monitorRegion (margine 500 m oltre il bbox) ==")
print(f"  centro  {cy:.6f}, {cx:.6f}")
print(f"  raggio  {radius:.0f} m")
print(f"\nscritti {OUT / 'area-c.geojson'} e {OUT / 'area-c-varchi.geojson'}")
