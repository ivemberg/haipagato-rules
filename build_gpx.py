#!/usr/bin/env python3
"""Genera i percorsi GPX per il simulatore di Xcode, dai GeoJSON veri.

Uso:  python3 tools/build_gpx.py

I percorsi sono gli stessi su cui girano i test: se il simulatore usasse tracce
inventate a mano, il verde dei test non direbbe nulla sul comportamento reale.

Ogni file viene **riletto e fatto passare dal rilevatore**, con la stessa logica
di build_areac.py e build_freeflow.py. Un GPX che non produce il transito che
promette, in M2 farebbe sospettare del codice invece che del file.

Solo libreria standard.
"""
import json, math, sys, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import areac_lib as ac  # noqa: E402
from freeflow_lib import (  # noqa: E402
    Chain, stitch, detect, dist_m, M_LON as FF_M_LON, M_LAT as FF_M_LAT,
    TOLERANCE_M, MIN_PROGRESS_M, MIN_FAST_PROGRESS_M,
)

OUT = ROOT / "tools" / "gpx"
RULES = ROOT / "rules"

# Istante di partenza fisso: un file che cambia a ogni generazione sporca il diff
# senza motivo. Lunedi 28 settembre 2026, ore 10:00 a Roma, quando Area C e' attiva.
T0 = "2026-09-28T08:00:00Z"

DUOMO = [9.191926, 45.464211]
NORD = [9.19, 45.492]

# Velocita' realistiche: il simulatore le ricava dai <time>, e per le free flow
# la velocita' e' parte della regola.
V_CITTA = 30.0
V_AUTOSTRADA = 110.0
V_CODA = 20.0
V_PARALLELA = 70.0


def epoch(iso):
    y, mo, rest = iso[:4], iso[5:7], iso[8:]
    d, hh, mm, ss = rest[:2], rest[3:5], rest[6:8], rest[9:11]
    days = (int(y) - 1970) * 365 + (int(y) - 1969) // 4
    cum = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    leap = 1 if (int(y) % 4 == 0 and int(mo) > 2) else 0
    days += cum[int(mo) - 1] + int(d) - 1 + leap
    return days * 86400 + int(hh) * 3600 + int(mm) * 60 + int(ss)


T0_EPOCH = epoch(T0)


def iso(seconds):
    s = int(seconds)
    days, rem = divmod(s, 86400)
    hh, rem = divmod(rem, 3600)
    mm, ss = divmod(rem, 60)
    y = 1970
    while True:
        n = 366 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 365
        if days < n:
            break
        days -= n
        y += 1
    leap = 1 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 0
    lengths = [31, 28 + leap, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    mo = 1
    for L in lengths:
        if days < L:
            break
        days -= L
        mo += 1
    return f"{y:04d}-{mo:02d}-{days + 1:02d}T{hh:02d}:{mm:02d}:{ss:02d}Z"


# ------------------------------------------------------------------ geometrie

def load_ring():
    fc = json.loads((RULES / "area-c.geojson").read_text(encoding="utf-8"))
    return fc["features"][0]["geometry"]["coordinates"][0]


def load_chains(name):
    fc = json.loads((RULES / name).read_text(encoding="utf-8"))
    ways = [f["geometry"]["coordinates"] for f in fc["features"]]
    return [Chain(c) for c in stitch(ways) if len(c) >= 2]


RING = load_ring()
A36 = load_chains("a36.geojson")
A36_MAIN = max(A36, key=lambda c: c.length_m)


DT = 2.0  # secondi fra un punto e l'altro


def walk(points, speed_kmh, t0=0.0, dt=DT):
    """Ricampiona il percorso a passo di TEMPO costante, non di distanza.

    I <time> del GPX sono a secondi interi, e il simulatore ricava la velocita' da li'.
    Campionando a distanza costante il dt viene frazionario e la troncatura lo falsa:
    passi da 40 m a 110 km/h danno dt 1,31 s che diventa 1 s, cioe' 144 km/h letti.
    A passo di tempo il dt e' intero per costruzione e la velocita' e' esatta.
    """
    step = speed_kmh / 3.6 * dt
    out = [[points[0][0], points[0][1], t0]]
    t = t0
    i = 0
    carry = 0.0
    while i < len(points) - 1:
        a, b = points[i], points[i + 1]
        seg = ac.dist_point_seg(b, a, a)
        if seg <= 0:
            i += 1
            continue
        pos = carry
        while pos + step <= seg:
            pos += step
            f = pos / seg
            t += dt
            out.append([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, t])
        carry = pos - seg
        i += 1
    return out


def line(a, b, n):
    return [[a[0] + (b[0] - a[0]) * i / (n - 1), a[1] + (b[1] - a[1]) * i / (n - 1)]
            for i in range(n)]


def chain_point(chain, s):
    for i in range(len(chain.pts) - 1):
        if chain.s[i] <= s <= chain.s[i + 1]:
            span = chain.s[i + 1] - chain.s[i]
            f = 0.0 if span == 0 else (s - chain.s[i]) / span
            a, b = chain.pts[i], chain.pts[i + 1]
            return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]
    return list(chain.pts[-1])


def along(chain, s0, s1, step_m=20.0):
    """Punti fitti lungo la catena: il ricampionamento a tempo li assottiglia."""
    pts, s = [], s0
    while s <= s1:
        pts.append(chain_point(chain, s))
        s += step_m
    return pts


# ------------------------------------------------------------------ percorsi

def bastioni():
    start = len(RING) // 4
    return walk([list(p) for p in RING[start:start + 260]], V_CITTA)


def ingresso_duomo():
    return walk(line(NORD, DUOMO, 120), V_CITTA)


def parcheggio_30m():
    full = line(NORD, DUOMO, 400)
    trip = []
    for p in full:
        trip.append(p)
        d = ac.dist_to_boundary(p, RING)
        if ac.inside(p, RING) and d >= 30.0:
            break
    timed = walk(trip, V_CITTA)
    last = timed[-1]
    # cinque minuti fermi: sopra probableMinDwellS
    timed += [[last[0], last[1], last[2] + 10.0 * i] for i in range(1, 31)]
    return timed


def a36(speed):
    return walk(along(A36_MAIN, 1000.0, 9000.0), speed)


def a36_parallela():
    pts = along(A36_MAIN, 2000.0, 2575.0, step_m=10.0)
    off = []
    for i, p in enumerate(pts):
        q = pts[min(i + 1, len(pts) - 1)]
        dx = (q[0] - p[0]) * FF_M_LON
        dy = (q[1] - p[1]) * FF_M_LAT
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        off.append([p[0] + nx * 20.0 / FF_M_LON, p[1] + ny * 20.0 / FF_M_LAT])
    return walk(off, V_PARALLELA)


# ------------------------------------------------------------------ scrittura

def write_gpx(path, name, description, track):
    gpx = ET.Element("gpx", {
        "version": "1.1",
        "creator": "haipagato tools/build_gpx.py",
        "xmlns": "http://www.topografix.com/GPX/1/1",
    })
    meta = ET.SubElement(gpx, "metadata")
    ET.SubElement(meta, "name").text = name
    ET.SubElement(meta, "desc").text = description
    trk = ET.SubElement(gpx, "trk")
    ET.SubElement(trk, "name").text = name
    seg = ET.SubElement(trk, "trkseg")
    for lon, lat, t in track:
        pt = ET.SubElement(seg, "trkpt", {"lat": f"{lat:.6f}", "lon": f"{lon:.6f}"})
        ET.SubElement(pt, "time").text = iso(T0_EPOCH + t)
    ET.indent(gpx, space="  ")
    path.write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(gpx, encoding="utf-8"))


def read_gpx(path):
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    root = ET.parse(path).getroot()
    out = []
    for pt in root.findall(".//g:trkpt", ns):
        t = pt.find("g:time", ns)
        if t is None or t.text is None:
            raise AssertionError(f"{path.name}: trkpt senza <time>")
        out.append([float(pt.get("lon")), float(pt.get("lat")), float(epoch(t.text) - T0_EPOCH)])
    return out


def measured_speed_kmh(track):
    """Velocita' mediana ricavata dai <time>, come fa il simulatore."""
    speeds = []
    for i in range(1, len(track)):
        dt = track[i][2] - track[i - 1][2]
        if dt <= 0:
            continue
        d = dist_m(track[i - 1][:2], track[i][:2])
        if d > 0.5:
            speeds.append(d / dt * 3.6)
    speeds.sort()
    return speeds[len(speeds) // 2] if speeds else 0.0


# ------------------------------------------------------------------ verifiche

fails = []


def check(name, ok, detail=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        fails.append(name)


PERCORSI = [
    ("bastioni-senza-entrare.gpx", "Cerchia dei Bastioni senza entrare",
     "Giro sulla circonvallazione: non deve nascere alcun transito.",
     bastioni, "poligono", "nessuno", V_CITTA),
    ("ingresso-duomo.gpx", "Ingresso in Area C fino al Duomo",
     "Ingresso da nord: transito confermato.",
     ingresso_duomo, "poligono", "confermato", V_CITTA),
    ("parcheggio-30m.gpx", "Ingresso e sosta a 30 m dal confine",
     "Entra in banda e parcheggia cinque minuti: transito probabile.",
     parcheggio_30m, "poligono", "probabile", V_CITTA),
    ("a36-percorrenza.gpx", "A36 Pedemontana a 110 km/h",
     "Percorrenza normale: transito confermato.",
     lambda: a36(V_AUTOSTRADA), "polilinea", "confermato", V_AUTOSTRADA),
    ("a36-coda.gpx", "A36 Pedemontana in coda a 20 km/h",
     "In coda non si superano i 50 km/h ma il pedaggio e' dovuto: confermato via avanzamento.",
     lambda: a36(V_CODA), "polilinea", "confermato", V_CODA),
    ("a36-parallela-575m.gpx", "Strada parallela all'A36, 575 m",
     "Costeggia l'autostrada per il tratto parallelo piu' lungo misurato: nessun transito.",
     a36_parallela, "polilinea", "nessuno", V_PARALLELA),
]

OUT.mkdir(parents=True, exist_ok=True)
print("== generazione ==")
for filename, name, desc, build, kind, atteso, velocita in PERCORSI:
    track = build()
    write_gpx(OUT / filename, name, desc, track)
    print(f"  {filename}: {len(track)} punti")

print("\n== rilettura e verifica ==")
for filename, name, desc, build, kind, atteso, velocita in PERCORSI:
    track = read_gpx(OUT / filename)
    check(f"{filename}: tutti i punti hanno un orario", len(track) > 1, f"{len(track)} punti")

    v = measured_speed_kmh(track)
    tolleranza = 0.05 * velocita
    check(f"{filename}: velocita' letta {v:.0f} km/h vicino a {velocita:.0f}",
          abs(v - velocita) <= tolleranza, f"scarto {abs(v - velocita):.1f} km/h")

    if kind == "poligono":
        esito, _, why = ac.classify_trip(track, RING)
    else:
        esito, why = detect(track, A36)
    check(f"{filename}: esito {esito}", esito == atteso, f"atteso {atteso} - {why}")

if fails:
    print(f"\n!! {len(fails)} verifiche fallite: {fails}")
    sys.exit(1)
print(f"\n{len(PERCORSI)} percorsi scritti in tools/gpx/")
