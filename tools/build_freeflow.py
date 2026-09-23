#!/usr/bin/env python3
"""Estrae i tracciati A36 / A59 / A60 da OpenStreetMap, marca i tratti ambigui,
calcola le monitorRegions e verifica la regola di rilevamento free flow.

Uso:  python3 tools/build_freeflow.py

Cache Overpass in tools/.cache/. Se una verifica fallisce non scrive nulla.
Solo libreria standard.
"""
import json, math, sys, time, urllib.request, urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from freeflow_lib import (  # noqa: E402
    Chain, stitch, dist_m, project_on_seg, seg_bearing, bearing_delta_unoriented,
    detect, ambiguity_threshold_m, M_LON, M_LAT,
    TOLERANCE_M, MIN_CONSECUTIVE_POINTS, MIN_SPEED_KMH, MAX_BEARING_DELTA_DEG,
    MIN_PROGRESS_M, MIN_FAST_PROGRESS_M,
    AMBIGUOUS_MIN_PROGRESS_M, AMBIGUOUS_MIN_FAST_PROGRESS_M, AMBIGUOUS_MIN_SPEED_KMH,
)

AMBIGUITY_THRESHOLD_M = ambiguity_threshold_m()

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "tools" / ".cache"
OUT = ROOT / "rules"

BBOX = "45.55,8.60,45.95,9.35"
MIRRORS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
MAX_MONITOR_REGIONS = 12
MONITOR_MARGIN_M = 500.0
PRECISION = 6

ROADS = [
    ("a36", "36", "A36 Pedemontana"),
    ("a59", "59", "A59 Tangenziale di Como"),
    ("a60", "60", "A60 Tangenziale di Varese"),
]

ATTRIB = "(c) OpenStreetMap contributors - opendatacommons.org/licenses/odbl"
ORDINARY = "trunk|primary|secondary|tertiary|unclassified|residential|living_street|service"


# ------------------------------------------------------------------ overpass

def overpass(query, name, tries=6):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    last = None
    for attempt in range(tries):
        for host in MIRRORS:
            try:
                data = urllib.parse.urlencode({"data": query}).encode()
                req = urllib.request.Request(
                    host, data=data, headers={"User-Agent": "haipagato-build/1.0"})
                with urllib.request.urlopen(req, timeout=240) as r:
                    body = r.read()
                doc = json.loads(body)
                if doc.get("elements") is not None:
                    path.write_bytes(body)
                    return doc
            except Exception as e:      # noqa: BLE001 - qualunque errore -> prossimo mirror
                last = e
        time.sleep(20 * (attempt + 1))
    raise SystemExit(f"Overpass non raggiungibile per {name}: {last}")


def ways_of(ref):
    q = (f'[out:json][timeout:180];'
         f'way["highway"="motorway"]["ref"~"^A ?{ref}$"]({BBOX});out geom;')
    return overpass(q, f"osm_a{ref}.json")


def parallel_of(ref):
    q = (f'[out:json][timeout:180];'
         f'way["highway"="motorway"]["ref"~"^A ?{ref}$"]({BBOX})->.m;'
         f'way(around.m:{int(TOLERANCE_M)})["highway"~"^({ORDINARY})$"];out geom;')
    return overpass(q, f"osm_par{ref}.json")


# ------------------------------------------------------------------ indice

class Grid:
    """Indice a celle per non fare il prodotto cartesiano fra i segmenti."""

    CELL = 0.005  # ~400 m

    def __init__(self, segments):
        self.cells = {}
        for seg in segments:
            (a, b) = seg
            for key in self._keys(a, b):
                self.cells.setdefault(key, []).append(seg)

    def _keys(self, a, b):
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        out = set()
        i = int(math.floor(x0 / self.CELL))
        while i <= int(math.floor(x1 / self.CELL)):
            j = int(math.floor(y0 / self.CELL))
            while j <= int(math.floor(y1 / self.CELL)):
                out.add((i, j))
                j += 1
            i += 1
        return out

    def near(self, p):
        i0 = int(math.floor(p[0] / self.CELL))
        j0 = int(math.floor(p[1] / self.CELL))
        out = []
        for i in (i0 - 1, i0, i0 + 1):
            for j in (j0 - 1, j0, j0 + 1):
                out.extend(self.cells.get((i, j), ()))
        return out


# ------------------------------------------------------------------ verifiche

fails = []


def check(name, ok, detail=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        fails.append(name)


def track_along(chain, s0, s1, speed_kmh, dt=2.0, offset_m=0.0, jitter=None):
    """Traccia GPS che segue la catena fra le ascisse s0 e s1 alla velocita' data."""
    step = speed_kmh / 3.6 * dt
    pts, s, t = [], s0, 0.0
    rnd = jitter
    while s <= s1:
        p = point_at(chain, s)
        if offset_m or rnd:
            brg = bearing_at(chain, s)
            nx = math.cos(math.radians(brg))
            ny = -math.sin(math.radians(brg))
            off = offset_m + (rnd() if rnd else 0.0)
            p = [p[0] + nx * off / M_LON, p[1] + ny * off / M_LAT]
        pts.append([p[0], p[1], t])
        s += step
        t += dt
    return pts


def point_at(chain, s):
    for i in range(len(chain.s) - 1):
        if chain.s[i] <= s <= chain.s[i + 1]:
            seg = chain.s[i + 1] - chain.s[i]
            f = 0.0 if seg == 0 else (s - chain.s[i]) / seg
            a, b = chain.pts[i], chain.pts[i + 1]
            return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]
    return chain.pts[-1]


def bearing_at(chain, s):
    for i in range(len(chain.s) - 1):
        if chain.s[i] <= s <= chain.s[i + 1]:
            return seg_bearing(chain.pts[i], chain.pts[i + 1])
    return seg_bearing(chain.pts[-2], chain.pts[-1])


# ------------------------------------------------------------------ main

print("== estrazione ==")
roads = {}
for rid, ref, name in ROADS:
    doc = ways_of(ref)
    els = doc["elements"]
    hw = {e["tags"].get("highway") for e in els}
    bad = [e for e in els if e["tags"].get("construction:ref") or e["tags"].get("proposed:ref")]
    ways = [[[round(n["lon"], PRECISION), round(n["lat"], PRECISION)] for n in e["geometry"]]
            for e in els]
    chains = [Chain(c) for c in stitch(ways)]
    chains = [c for c in chains if c.length_m > 50]
    roads[rid] = {"ref": ref, "name": name, "chains": chains, "ways": len(els)}
    print(f"  {rid}: {len(els)} way -> {len(chains)} catene, "
          f"{sum(c.length_m for c in chains) / 1000:.1f} km")
    check(f"{rid}: solo highway=motorway", hw == {"motorway"}, str(hw))
    check(f"{rid}: nessun construction/proposed", not bad, f"{len(bad)} residui")

print("\n== tratti ambigui (viabilita' ordinaria entro %.0f m e allineata) ==" % TOLERANCE_M)
for rid, ref, name in ROADS:
    doc = parallel_of(ref)
    segs = []
    for e in doc["elements"]:
        g = [[n["lon"], n["lat"]] for n in e["geometry"]]
        segs += [(g[i], g[i + 1]) for i in range(len(g) - 1)]
    grid = Grid(segs) if segs else None
    longest_overall = 0.0
    for ch in roads[rid]["chains"]:
        flags = []
        for i, p in enumerate(ch.pts):
            amb = False
            if grid:
                brg = seg_bearing(ch.pts[max(i - 1, 0)], ch.pts[min(i + 1, len(ch.pts) - 1)])
                for a, b in grid.near(p):
                    d, _, _ = project_on_seg(p, a, b)
                    if d <= TOLERANCE_M and \
                       bearing_delta_unoriented(seg_bearing(a, b), brg) <= MAX_BEARING_DELTA_DEG:
                        amb = True
                        break
            flags.append(amb)
        run = best = 0.0
        for i in range(1, len(ch.pts)):
            if flags[i] and flags[i - 1]:
                run += ch.s[i] - ch.s[i - 1]
                best = max(best, run)
            else:
                run = 0.0
        ch.ambiguous_run_m = best
        # Ambigua se il tratto parallelo e' lungo abbastanza da far scattare il ramo
        # piu' permissivo dei due. Il minimo fra ramo veloce e ramo lento, non il solo
        # ramo lento: basta che uno dei due sia soddisfatto perche' nasca il transito.
        ch.ambiguous = best > AMBIGUITY_THRESHOLD_M
        longest_overall = max(longest_overall, best)
    n_amb = sum(1 for c in roads[rid]["chains"] if c.ambiguous)
    roads[rid]["longest_parallel_m"] = longest_overall
    print(f"  {rid}: {len(segs)} segmenti ordinari vicini, "
          f"tratto parallelo piu' lungo {longest_overall:.0f} m, catene ambigue {n_amb}")

longest_any = max(r["longest_parallel_m"] for r in roads.values())
check("la soglia di ambiguita' supera il tratto parallelo piu' lungo misurato",
      AMBIGUITY_THRESHOLD_M > longest_any,
      f"soglia {AMBIGUITY_THRESHOLD_M:.0f} m contro {longest_any:.0f} m misurati")

print("\n== monitorRegions (massimo %d) ==" % MAX_MONITOR_REGIONS)
all_pts = [p for r in roads.values() for c in r["chains"] for p in c.pts]


def cover(radius):
    circles = []
    for p in all_pts:
        if any(dist_m(p, c[0]) <= radius for c in circles):
            continue
        circles.append([list(p), 0.0])
    for c in circles:
        c[1] = max((dist_m(p, c[0]) for p in all_pts if dist_m(p, c[0]) <= radius), default=0.0)
    return circles


lo, hi = 300.0, 12000.0
for _ in range(24):
    mid = (lo + hi) / 2
    if len(cover(mid)) <= MAX_MONITOR_REGIONS:
        hi = mid
    else:
        lo = mid
circles = cover(hi)
regions = [{"lat": round(c[0][1], 6), "lon": round(c[0][0], 6),
            "radiusM": int(c[1] + MONITOR_MARGIN_M)} for c in circles]
print(f"  {len(regions)} cerchi, raggio max {max(r['radiusM'] for r in regions)} m")
check("monitorRegions entro il budget", len(regions) <= MAX_MONITOR_REGIONS, str(len(regions)))

print("\n== negativi: zero transiti ==")
main = max(roads["a36"]["chains"], key=lambda c: c.length_m)
allch = [c for r in roads.values() for c in r["chains"]]

esito, why = detect(track_along(main, 1000, 6000, 110), allch, in_vehicle=False)
check("filtro in-auto spento: nessun transito", esito == "nessuno", why)

# seg_bearing() misura da nord in senso orario: est = sin(b), nord = cos(b).
# Sbagliare questo vettore produce una traccia parallela invece che perpendicolare,
# e il test passerebbe o fallirebbe per la ragione sbagliata.
perp = []
road_b = bearing_at(main, 3000)
b = (road_b + 90.0) % 360.0
p0 = point_at(main, 3000)
for i in range(40):
    d = (i - 20) * 28.0
    perp.append([p0[0] + math.sin(math.radians(b)) * d / M_LON,
                 p0[1] + math.cos(math.radians(b)) * d / M_LAT, i * 2.0])
course = seg_bearing(perp[0][:2], perp[-1][:2])
check("la traccia del cavalcavia e' davvero perpendicolare",
      abs(bearing_delta_unoriented(course, road_b) - 90.0) < 5.0,
      f"delta {bearing_delta_unoriented(course, road_b):.1f} gradi")
check("il cavalcavia attraversa davvero la carreggiata",
      min(min(c.locate(p)[0] for c in allch) for p in perp) < TOLERANCE_M)
esito, why = detect(perp, allch)
check("cavalcavia perpendicolare a 50 km/h: nessun transito", esito == "nessuno", why)

def min_dist_to_network(tr):
    return min(min(c.locate(p)[0] for c in allch) for p in tr)


for off in (60.0, 45.0):
    # La carreggiata e' doppia: spostandosi dalla parte sbagliata si finisce
    # sull'altra carreggiata, a meno di 40 m. Scelgo il verso che allontana
    # davvero dalla rete e lo verifico, altrimenti il test non proverebbe nulla.
    cands = [track_along(main, 1000, 6000, 50, offset_m=s * off) for s in (1.0, -1.0)]
    tr = max(cands, key=min_dist_to_network)
    d = min_dist_to_network(tr)
    check(f"la traccia parallela a {off:.0f} m e' fuori tolleranza da tutta la rete",
          d > TOLERANCE_M, f"min {d:.1f} m")
    esito, why = detect(tr, allch)
    check(f"strada parallela a {off:.0f} m: nessun transito", esito == "nessuno", why)

# Il caso che il ramo veloce sbagliava prima della correzione: un tratto di strada
# parallela lungo quanto il piu' lungo misurato sul campo, percorso in fretta.
# Cinque punti veloci e allineati ci stanno comodamente, ma l'avanzamento no.
par_len = round(longest_any)
par = track_along(main, 2000, 2000 + par_len, 70, offset_m=20.0)
par_prog = max(main.locate(p)[1] for p in par) - min(main.locate(p)[1] for p in par)
check(f"la traccia parallela di {par_len} m e' dentro tolleranza e abbastanza veloce",
      min(min(c.locate(p)[0] for c in allch) for p in par) <= TOLERANCE_M
      and len(par) >= MIN_CONSECUTIVE_POINTS + 1,
      f"avanzamento {par_prog:.0f} m, {len(par)} punti")
esito, why = detect(par, allch)
check(f"strada parallela di {par_len} m a 70 km/h: nessun transito", esito == "nessuno", why)
# Senza la soglia sul ramo veloce lo stesso percorso deve produrre un transito:
# altrimenti il test passerebbe per conto suo e non proverebbe la correzione.
regressione, _ = detect(par, allch, min_fast_progress=0.0)
check("senza minFastProgressM lo stesso percorso darebbe un falso positivo",
      regressione == "confermato", f"con soglia a zero: {regressione}")

import random
random.seed(7)
still_p = point_at(main, 3000)
still = [[still_p[0] + random.uniform(-20, 20) / M_LON,
          still_p[1] + random.uniform(-20, 20) / M_LAT, i * 5.0] for i in range(240)]
esito, why = detect(still, allch)
check("veicolo fermo con rumore GPS per 20 min: nessun transito", esito == "nessuno", why)

print("\n== positivi ==")
esito, why = detect(track_along(main, 1000, 9000, 110), allch)
check("A36 a 110 km/h: transito", esito == "confermato", why)

esito, why = detect(track_along(main, 1000, 9000, 20), allch)
check("A36 in coda a 20 km/h: transito", esito == "confermato", why)

random.seed(3)
esito, why = detect(track_along(main, 1000, 9000, 110, jitter=lambda: random.uniform(-25, 25)),
                    allch)
check("A36 a 110 km/h con rumore GPS 25 m: transito", esito == "confermato", why)

short = min((c for c in roads["a59"]["chains"]), key=lambda c: -c.length_m)
esito, why = detect(track_along(short, 0, min(short.length_m, 2600), 90), allch)
check("A59 percorsa per intero: transito", esito in ("confermato", "probabile"), why)

print("\n== soglie rinforzate sui tratti ambigui ==")
# Nessuna catena reale risulta ambigua (il tratto parallelo piu' lungo e' 575 m,
# sotto minProgressM), quindi senza questi casi sintetici il ramo resterebbe
# codice non provato.
amb = Chain(main.pts)
amb.ambiguous = True
amb.ambiguous_run_m = 0

esito, why = detect(track_along(amb, 1000, 3500, 60), [amb])
check("ambiguo, 60 km/h e avanzamento 2500 m: probabile, non confermato",
      esito == "probabile", why)

esito, why = detect(track_along(amb, 1000, 5000, 110), [amb])
check("ambiguo, 110 km/h sopra la soglia rinforzata: confermato",
      esito == "confermato", why)

esito, why = detect(track_along(amb, 1000, 5500, 60), [amb])
check("ambiguo, 60 km/h e avanzamento 4500 m: confermato",
      esito == "confermato", why)

esito, why = detect(track_along(amb, 1000, 1600, 60), [amb])
check("ambiguo, tratto breve a 60 km/h: nessun transito", esito == "nessuno", why)

# ------------------------------------------------------------------ scrittura

if fails:
    print(f"\n!! {len(fails)} verifiche fallite, non scrivo nulla: {fails}")
    sys.exit(1)

for rid, ref, name in ROADS:
    r = roads[rid]
    fc = {
        "type": "FeatureCollection",
        "attribution": ATTRIB,
        "license": "ODbL-1.0",
        "source": f"OpenStreetMap via Overpass, way[highway=motorway][ref~^A ?{ref}$]",
        "features": [{
            "type": "Feature",
            "properties": {
                "id": rid,
                "name": name,
                "ambiguous": bool(c.ambiguous),
                "ambiguousRunM": int(c.ambiguous_run_m),
                "lengthM": int(c.length_m),
            },
            "geometry": {"type": "LineString", "coordinates": c.pts},
        } for c in r["chains"]],
    }
    (OUT / f"{rid}.geojson").write_text(
        json.dumps(fc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

(CACHE / "monitor_regions.json").write_text(json.dumps(regions, indent=2))
print("\nscritti " + ", ".join(f"rules/{r}.geojson" for r, _, _ in ROADS))
print("monitorRegions:")
for r in regions:
    print(f"  {{ lat {r['lat']}, lon {r['lon']}, radiusM {r['radiusM']} }}")
