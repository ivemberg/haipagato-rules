#!/usr/bin/env python3
"""Estrae da OpenStreetMap le tratte free flow del gruppo ASTM (A33 Asti-Cuneo, tronco II, e
Corda Molle, raccordo Ospitaletto-Montichiari), le verifica come l'A36 e calcola le
monitorRegions.

Uso:  python3 tools/build_freeflow_astm.py

Stesse soglie e stesse verifiche di tools/build_freeflow.py (A36/A59/A60), che non si tocca:
i GeoJSON dell'APL restano quelli. Cache Overpass in tools/.cache/. Se una verifica fallisce
non scrive nulla. Solo libreria standard.

Scrive:
  rules/a33.geojson, rules/corda-molle.geojson        (ODbL, con attribuzione)
  tools/.cache/astm_regions.json                       (centri e raggi, per rules.json)
  tools/.cache/astm_parallels.json                     (la strada ordinaria parallela piu'
                                                        vicina, per il GPX: resta in cache,
                                                        non in rules/)
"""
import json, math, random, sys, time, urllib.request, urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from freeflow_lib import (  # noqa: E402
    Chain, stitch, dist_m, project_on_seg, seg_bearing, bearing_delta_unoriented,
    detect, ambiguity_threshold_m, M_LON, M_LAT,
    TOLERANCE_M, MIN_CONSECUTIVE_POINTS, MAX_BEARING_DELTA_DEG,
)

AMBIGUITY_THRESHOLD_M = ambiguity_threshold_m()

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "tools" / ".cache"
OUT = ROOT / "rules"

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
PRECISION = 6
ATTRIB = "(c) OpenStreetMap contributors - opendatacommons.org/licenses/odbl"
ORDINARY = "trunk|primary|secondary|tertiary|unclassified|residential|living_street|service"

# Lo stesso raggio di copertura dei cerchi dell'APL (2945 m il piu' grande, cioe' 2445 m di
# copertura piu' 500 m di margine): stessa granularita', stesso costo di batteria per km.
COVER_RADIUS_M = 2445.0
MONITOR_MARGIN_M = 500.0
# Per trovare la strada ordinaria parallela piu' vicina da percorrere nel GPX.
PARALLEL_SEARCH_M = 300

# (id, nome, filtro Overpass, bbox, catene da tenere)
ROADS = [
    ("a33", "A33 Asti-Cuneo",
     'way["highway"="motorway"]["ref"~"^A ?33$"]', "44.3,7.4,45.0,8.4",
     # Solo il tronco II (Marene sulla A6 - Rocca Schiavino sulla SS231), l'unico in free
     # flow. Il tronco I, Cuneo - Massimini, sta tutto a sud di 44,5 gradi.
     lambda pts: min(p[1] for p in pts) > 44.55),
    ("corda-molle", "Corda Molle",
     'way["highway"="motorway"]["ref"="A21racc"]', "45.35,10.0,45.62,10.45",
     lambda pts: True),
]


# ------------------------------------------------------------------ overpass

def overpass(query, name, tries=8):
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
                with urllib.request.urlopen(req, timeout=300) as r:
                    body = r.read()
                doc = json.loads(body)
                if doc.get("elements") is not None:
                    path.write_bytes(body)
                    return doc
            except Exception as e:      # noqa: BLE001 - qualunque errore -> prossimo mirror
                last = e
        time.sleep(20 * (attempt + 1))
    raise SystemExit(f"Overpass non raggiungibile per {name}: {last}")


def hav_m(a, b):
    """Distanza vera in metri fra due [lon, lat]. freeflow_lib proietta con la latitudine
    della Lombardia (45,7): all'A33, a 44,7, sbaglierebbe i raggi dei cerchi di qualche
    decina di metri, proprio il margine che deve tenere dentro le aree di servizio."""
    la1, la2 = math.radians(a[1]), math.radians(b[1])
    dla, dlo = la2 - la1, math.radians(b[0] - a[0])
    h = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * 6371000.0 * math.asin(math.sqrt(min(1.0, h)))


def split_returns(pts):
    """Divide una catena che torna indietro nel punto piu' lontano dall'inizio.

    `stitch` cuce le way agli estremi, e quando le due carreggiate si toccano ai capi del
    raccordo ne esce un anello: andata e ritorno in una catena sola. Lungo un anello un punto
    fermo si proietta ora su una carreggiata ora sull'altra, a ascisse lontanissime, e sembra
    avanzare di decine di km. Una catena per senso di marcia, come per l'APL.
    """
    if len(pts) < 3:
        return [pts]
    far = max(range(len(pts)), key=lambda i: dist_m(pts[0], pts[i]))
    if dist_m(pts[0], pts[-1]) < 0.5 * dist_m(pts[0], pts[far]) and 0 < far < len(pts) - 1:
        return split_returns(pts[:far + 1]) + split_returns(pts[far:])
    return [pts]


def geom(e):
    return [[round(n["lon"], PRECISION), round(n["lat"], PRECISION)] for n in e["geometry"]]


# ------------------------------------------------------------------ verifiche

fails = []


def check(name, ok, detail=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        fails.append(name)


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


def track_along(chain, s0, s1, speed_kmh, dt=2.0, offset_m=0.0, jitter=None):
    step = speed_kmh / 3.6 * dt
    pts, s, t = [], s0, 0.0
    while s <= s1:
        p = point_at(chain, s)
        if offset_m or jitter:
            brg = bearing_at(chain, s)
            nx, ny = math.cos(math.radians(brg)), -math.sin(math.radians(brg))
            off = offset_m + (jitter() if jitter else 0.0)
            p = [p[0] + nx * off / M_LON, p[1] + ny * off / M_LAT]
        pts.append([p[0], p[1], t])
        s += step
        t += dt
    return pts


def near_chain(chains, p):
    return min(c.locate(p)[0] for c in chains)


# ------------------------------------------------------------------ estrazione

print("== estrazione ==")
roads = {}
for rid, name, flt, bbox, keep in ROADS:
    doc = overpass(f"[out:json][timeout:250];{flt}({bbox});out geom;", f"astm_{rid}.json")
    els = doc["elements"]
    hw = {e["tags"].get("highway") for e in els}
    pieces = [q for c in stitch([geom(e) for e in els]) for q in split_returns(c)]
    all_chains = [c for c in (Chain(q) for q in pieces) if c.length_m > 50]
    chains = [c for c in all_chains if keep(c.pts)]
    dropped = len(all_chains) - len(chains)
    roads[rid] = {"name": name, "chains": chains, "flt": flt, "bbox": bbox}
    km = sum(c.length_m for c in chains) / 1000
    print(f"  {rid}: {len(els)} way -> {len(chains)} catene tenute ({dropped} escluse), {km:.1f} km")
    check(f"{rid}: solo highway=motorway", hw == {"motorway"}, str(hw))
    check(f"{rid}: qualcosa da rilevare", km > 5.0, f"{km:.1f} km")

print("\n== tratti ambigui (viabilita' ordinaria entro %.0f m e allineata) ==" % TOLERANCE_M)
for rid, r in roads.items():
    doc = overpass(f'[out:json][timeout:250];{r["flt"]}({r["bbox"]})->.m;'
                   f'way(around.m:{int(TOLERANCE_M)})["highway"~"^({ORDINARY})$"];out geom;',
                   f"astm_{rid}_par40.json")
    segs = []
    for e in doc["elements"]:
        g = geom(e)
        segs += [(g[i], g[i + 1]) for i in range(len(g) - 1)]
    longest = 0.0
    for ch in r["chains"]:
        flags = []
        for i, p in enumerate(ch.pts):
            brg = seg_bearing(ch.pts[max(i - 1, 0)], ch.pts[min(i + 1, len(ch.pts) - 1)])
            flags.append(any(
                project_on_seg(p, a, b)[0] <= TOLERANCE_M
                and bearing_delta_unoriented(seg_bearing(a, b), brg) <= MAX_BEARING_DELTA_DEG
                for a, b in segs
                if abs(a[0] - p[0]) < 0.01 and abs(a[1] - p[1]) < 0.01))
        run = best = 0.0
        for i in range(1, len(ch.pts)):
            if flags[i] and flags[i - 1]:
                run += ch.s[i] - ch.s[i - 1]
                best = max(best, run)
            else:
                run = 0.0
        ch.ambiguous_run_m = best
        ch.ambiguous = best > AMBIGUITY_THRESHOLD_M
        longest = max(longest, best)
    r["longest_parallel_m"] = longest
    n_amb = sum(1 for c in r["chains"] if c.ambiguous)
    print(f"  {rid}: {len(segs)} segmenti ordinari entro {TOLERANCE_M:.0f} m, tratto parallelo "
          f"piu' lungo {longest:.0f} m (soglia {AMBIGUITY_THRESHOLD_M:.0f} m), catene ambigue {n_amb}")

print("\n== strada ordinaria parallela piu' vicina (per il GPX) ==")
parallels = {}
for rid, r in roads.items():
    doc = overpass(f'[out:json][timeout:250];{r["flt"]}({r["bbox"]})->.m;'
                   f'way(around.m:{PARALLEL_SEARCH_M})["highway"~"^({ORDINARY})$"];out geom;',
                   f"astm_{rid}_par{PARALLEL_SEARCH_M}.json")
    best = None
    for c in stitch([geom(e) for e in doc["elements"]]):
        ch = Chain(c)
        run, start, s_best = 0.0, 0, (0.0, 0, 0)
        dists = []
        for i in range(len(ch.pts) - 1):
            p = ch.pts[i]
            d = min(m.locate(p)[0] for m in r["chains"])
            brg = seg_bearing(ch.pts[i], ch.pts[i + 1])
            aligned = any(
                bearing_delta_unoriented(brg, bearing_at(m, m.locate(p)[1])) <= MAX_BEARING_DELTA_DEG
                for m in r["chains"] if m.locate(p)[0] <= PARALLEL_SEARCH_M)
            ok = d <= PARALLEL_SEARCH_M and d > TOLERANCE_M + 5 and aligned
            dists.append(d)
            if ok:
                if run == 0.0:
                    start = i
                run += ch.s[i + 1] - ch.s[i]
                if run > s_best[0]:
                    s_best = (run, start, i + 1)
            else:
                run = 0.0
        if s_best[0] > 0:
            seg_pts = ch.pts[s_best[1]:s_best[2] + 1]
            mean_d = sum(dists[s_best[1]:s_best[2]]) / max(1, s_best[2] - s_best[1])
            cand = (s_best[0], mean_d, seg_pts)
            # La piu' vicina fra quelle abbastanza lunghe da provare qualcosa (>= 1 km);
            # se nessuna lo e', la piu' lunga.
            if best is None or (cand[0] >= 1000 and (best[0] < 1000 or cand[1] < best[1])) \
                    or (best[0] < 1000 and cand[0] > best[0]):
                best = cand
    check(f"{rid}: trovata una strada ordinaria parallela", best is not None)
    if best:
        length, mean_d, pts = best
        # Al massimo 3 km: basta a superare le soglie di avanzamento se fosse l'autostrada.
        chain = Chain(pts)
        if chain.length_m > 3000:
            pts = [point_at(chain, s) for s in [i * 20.0 for i in range(int(3000 / 20) + 1)]]
        parallels[rid] = {"lengthM": int(min(length, 3000)), "meanDistanceM": round(mean_d),
                          "points": pts}
        print(f"  {rid}: {length:.0f} m allineati, distanza media {mean_d:.0f} m dall'autostrada")

print("\n== monitorRegions (raggio di copertura %.0f m, come l'APL) ==" % COVER_RADIUS_M)
regions = {}
for rid, r in roads.items():
    pts = [p for c in r["chains"] for p in c.pts]
    circles = []
    # Il centro nuovo non sta sul primo punto scoperto ma un raggio piu' avanti lungo la
    # catena: cosi' il cerchio copre il tratto prima e quello dopo, e ne servono la meta'.
    for ch in r["chains"]:
        for i, p in enumerate(ch.pts):
            if any(hav_m(p, c[0]) <= COVER_RADIUS_M for c in circles):
                continue
            centre = point_at(ch, min(ch.s[i] + COVER_RADIUS_M * 0.95, ch.s[-1]))
            circles.append([list(centre), 0.0])
    for c in circles:
        c[1] = max((hav_m(p, c[0]) for p in pts if hav_m(p, c[0]) <= COVER_RADIUS_M), default=0.0)
    uncovered = [p for p in pts if not any(hav_m(p, c[0]) <= c[1] + 1 for c in circles)]
    # Il margine vero: ogni punto almeno MONITOR_MARGIN_M dentro un cerchio, misurato come lo
    # misura il dominio (DoublePassageTest). Una sosta in area di servizio non esce dalla zona.
    worst = min(max(c[1] + MONITOR_MARGIN_M - hav_m(p, c[0]) for c in circles) for p in pts)
    check(f"{rid}: ogni punto almeno {MONITOR_MARGIN_M:.0f} m dentro un cerchio", worst >= MONITOR_MARGIN_M - 1,
          f"peggiore {worst:.0f} m")
    check(f"{rid}: ogni punto del tracciato dentro un cerchio", not uncovered, f"{len(uncovered)} fuori")
    # Per eccesso: arrotondare il raggio per difetto toglierebbe fino a un metro al margine.
    regions[rid] = [{"lat": round(c[0][1], 6), "lon": round(c[0][0], 6),
                     "radiusM": int(math.ceil(c[1] + MONITOR_MARGIN_M)) + 1} for c in circles]
    print(f"  {rid}: {len(regions[rid])} cerchi")
total_new = sum(len(v) for v in regions.values())
print(f"  totale nuove {total_new}; con le 13 di oggi (Area C 1, APL 12) fanno {13 + total_new}")

print("\n== negativi e positivi, come per l'A36 ==")
allch = [c for r in roads.values() for c in r["chains"]]
for rid, r in roads.items():
    main = max(r["chains"], key=lambda c: c.length_m)
    L = main.length_m
    a, b = min(1000.0, L * 0.1), min(9000.0, L * 0.9)
    esito, why = detect(track_along(main, a, b, 110), allch, in_vehicle=False)
    check(f"{rid}: filtro in-auto spento, nessun transito", esito == "nessuno", why)

    road_b = bearing_at(main, (a + b) / 2)
    bb = (road_b + 90.0) % 360.0
    p0 = point_at(main, (a + b) / 2)
    perp = [[p0[0] + math.sin(math.radians(bb)) * (i - 20) * 28.0 / M_LON,
             p0[1] + math.cos(math.radians(bb)) * (i - 20) * 28.0 / M_LAT, i * 2.0] for i in range(40)]
    check(f"{rid}: il cavalcavia attraversa davvero la carreggiata",
          min(near_chain(allch, p) for p in perp) < TOLERANCE_M)
    esito, why = detect(perp, allch)
    check(f"{rid}: cavalcavia perpendicolare, nessun transito", esito == "nessuno", why)

    for off in (60.0, 45.0):
        cands = [track_along(main, a, min(a + 5000, b), 50, offset_m=s * off) for s in (1.0, -1.0)]
        tr = max(cands, key=lambda t: min(near_chain(allch, p) for p in t))
        d = min(near_chain(allch, p) for p in tr)
        check(f"{rid}: la traccia parallela a {off:.0f} m e' fuori tolleranza", d > TOLERANCE_M, f"min {d:.1f} m")
        esito, why = detect(tr, allch)
        check(f"{rid}: strada parallela a {off:.0f} m, nessun transito", esito == "nessuno", why)

    random.seed(7)
    sp = point_at(main, (a + b) / 2)
    still = [[sp[0] + random.uniform(-20, 20) / M_LON, sp[1] + random.uniform(-20, 20) / M_LAT, i * 5.0]
             for i in range(240)]
    esito, why = detect(still, allch)
    check(f"{rid}: veicolo fermo con rumore GPS per 20 min, nessun transito", esito == "nessuno", why)

    esito, why = detect(track_along(main, a, b, 110), allch)
    check(f"{rid}: a 110 km/h, transito", esito == "confermato", why)
    esito, why = detect(track_along(main, a, min(a + 3500, b), 20), allch)
    check(f"{rid}: in coda a 20 km/h per 3,5 km, transito", esito == "confermato", why)
    random.seed(3)
    esito, why = detect(track_along(main, a, b, 110, jitter=lambda: random.uniform(-25, 25)), allch)
    check(f"{rid}: a 110 km/h con rumore GPS 25 m, transito", esito == "confermato", why)

    if rid in parallels:
        par = Chain(parallels[rid]["points"])
        tr = track_along(par, 0, par.length_m, 70)
        esito, why = detect(tr, allch)
        check(f"{rid}: strada ordinaria parallela piu' vicina a 70 km/h, nessun transito",
              esito == "nessuno", why)

# ------------------------------------------------------------------ scrittura

if fails:
    print(f"\n!! {len(fails)} verifiche fallite, non scrivo nulla: {fails}")
    sys.exit(1)

for rid, r in roads.items():
    fc = {
        "type": "FeatureCollection",
        "attribution": ATTRIB,
        "license": "ODbL-1.0",
        "source": f"OpenStreetMap via Overpass, {r['flt']}",
        "features": [{
            "type": "Feature",
            "properties": {"id": rid, "name": r["name"], "ambiguous": bool(c.ambiguous),
                           "ambiguousRunM": int(c.ambiguous_run_m), "lengthM": int(c.length_m)},
            "geometry": {"type": "LineString", "coordinates": c.pts},
        } for c in r["chains"]],
    }
    (OUT / f"{rid}.geojson").write_text(
        json.dumps(fc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
(CACHE / "astm_regions.json").write_text(json.dumps(regions, indent=2))
(CACHE / "astm_parallels.json").write_text(json.dumps(parallels))
print("\nscritti " + ", ".join(f"rules/{r}.geojson" for r in roads))
