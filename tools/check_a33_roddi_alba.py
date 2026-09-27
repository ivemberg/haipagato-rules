#!/usr/bin/env python3
"""Il lotto dell'A33 fra Roddi e Alba è comparso in OpenStreetMap come autostrada?

Da lanciare **prima di ogni release delle regole** (checklist, `docs/lancio-checklist.md` 0.4).

Il 2026-09-27 il lotto nuovo fra Roddi e Alba (circa 5 km) in OSM non c'è, né come autostrada né
come cantiere: nel buco ci sono solo la tangenziale di Alba (SP3bis/SS231, `trunk`) e la rotatoria di
Scaparoni (`highway=construction`, che col lotto non c'entra). `rules/a33.geojson` si ferma a Roddi
(7,9999 E, 44,6907 N) e riprende ad Alba (8,0485 E, 44,7213 N), e l'A33 in `rules/rules.json` porta
un `coverageNotice` che lo dice all'utente. Quando in OSM compare come `highway=motorway` (o come una
way qualsiasi con `ref=A33`), la geometria va rigenerata con
`tools/build_freeflow_astm.py` (con le sue verifiche e i replay dell'A33) e l'avviso va tolto,
nella stessa versione delle regole.

Lo script controlla che le tre cose dicano la stessa cosa:

- **OSM**: le `highway=motorway` e le way con `ref=A33` nel riquadro del buco, e quanti metri di queste stanno a più di
  `COVERED_M` da `a33.geojson`. Sopra `NEW_MOTORWAY_M` il lotto è comparso.
- **Geometria**: `a33.geojson` ha punti dentro il buco (cioè è già stata rigenerata)?
- **Avviso**: l'A33 in `rules.json` ha il `coverageNotice`?

Esce con 0 solo se sono coerenti: buco aperto in OSM, geometria senza il lotto, avviso presente;
oppure lotto coperto dalla geometria e avviso tolto. Con 1 dice che cosa fare. Con 2 se Overpass
non risponde: un controllo che non è riuscito a guardare non è un controllo passato.

`--self-test` prova la logica su dati finti, senza rete.
"""
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Nel repo dell'app le regole stanno in rules/, in haipagato-rules alla radice.
DATA = ROOT / "rules" if (ROOT / "rules" / "rules.json").exists() else ROOT
RULES = DATA / "rules.json"
GEOJSON = DATA / "a33.geojson"

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Il buco: fra la fine della geometria a Roddi e la ripresa ad Alba. Il riquadro per OSM è un po'
# più largo, perché il tracciato nuovo non è una retta; quello per la geometria è più stretto, per
# non contare i due capi che ci sono già.
OSM_BBOX = (44.684, 7.985, 44.728, 8.062)          # sud, ovest, nord, est
GAP_BOX = (44.693, 7.990, 44.719, 8.045)
# Una way di OSM è «già nella geometria» se il suo tratto sta entro questa distanza da a33.geojson.
COVERED_M = 60.0
# Sopra questi metri di autostrada nuova, il lotto è comparso. I raccordi fra una way e l'altra
# e le piccole correzioni di tracciato stanno sotto.
NEW_MOTORWAY_M = 300.0


def hav_m(a, b):
    """Distanza in metri fra due [lon, lat]."""
    la1, la2 = math.radians(a[1]), math.radians(b[1])
    dla, dlo = la2 - la1, math.radians(b[0] - a[0])
    h = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * 6371000.0 * math.asin(math.sqrt(min(1.0, h)))


def seg_dist_m(p, a, b):
    """Distanza in metri di p dal segmento a-b, in un piano locale (bastano poche centinaia di metri)."""
    kx = 111320.0 * math.cos(math.radians(p[1]))
    ky = 110540.0
    ax, ay = (a[0] - p[0]) * kx, (a[1] - p[1]) * ky
    bx, by = (b[0] - p[0]) * kx, (b[1] - p[1]) * ky
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / L))
    return math.hypot(ax + t * dx, ay + t * dy)


def near_lines(p, lines, limit):
    for line in lines:
        for a, b in zip(line, line[1:]):
            if seg_dist_m(p, a, b) <= limit:
                return True
    return False


def uncovered_m(ways, lines):
    """Metri delle way (liste di [lon, lat]) il cui punto medio di segmento sta lontano dalla geometria."""
    total = 0.0
    for w in ways:
        for a, b in zip(w, w[1:]):
            mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]
            if not near_lines(mid, lines, COVERED_M):
                total += hav_m(a, b)
    return total


def geometry_in_gap(lines):
    s, w, n, e = GAP_BOX
    return sum(1 for line in lines for p in line if s < p[1] < n and w < p[0] < e)


def verdict(new_m, gap_points, has_notice):
    """(exit code, messaggio). La logica sta qui, separata dalla rete, per il self-test."""
    appeared = new_m > NEW_MOTORWAY_M
    covered = gap_points > 0
    if covered and not has_notice and not appeared:
        return 0, "a33.geojson copre già Roddi–Alba e l'avviso non c'è più: coerente."
    if covered and has_notice:
        return 1, ("a33.geojson copre già Roddi–Alba ma l'A33 ha ancora il coverageNotice: toglilo da "
                   "rules/rules.json nella stessa versione delle regole.")
    if appeared:
        return 1, (f"In OSM ci sono {new_m:.0f} m di highway=motorway nel buco Roddi–Alba che a33.geojson non ha: "
                   "il lotto è comparso. Rigenera con `python3 tools/build_freeflow_astm.py` (con le sue "
                   "verifiche), rifai i replay A33 su iOS e Android, togli il coverageNotice dell'A33 e "
                   "pubblica una versione nuova delle regole.")
    if not has_notice:
        return 1, ("Il buco Roddi–Alba c'è ancora (in OSM e in a33.geojson) ma l'A33 non ha il coverageNotice: "
                   "l'utente non saprebbe che quel tratto non è coperto. Rimettilo in rules/rules.json.")
    return 0, (f"Roddi–Alba non è ancora highway=motorway in OSM ({new_m:.0f} m nuovi, soglia "
               f"{NEW_MOTORWAY_M:.0f}): la geometria resta, l'avviso resta.")


def overpass(query, tries=3):
    last = None
    for attempt in range(tries):
        for host in MIRRORS:
            try:
                data = urllib.parse.urlencode({"data": query}).encode()
                req = urllib.request.Request(host, data=data, headers={"User-Agent": "haipagato-check/1.0"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    doc = json.loads(r.read())
                if doc.get("elements") is not None:
                    return doc, host
            except Exception as e:  # noqa: BLE001 - qualunque errore -> prossimo mirror
                last = e
        time.sleep(10 * (attempt + 1))
    print(f"Overpass non raggiungibile: {last}", file=sys.stderr)
    sys.exit(2)


def load_lines():
    g = json.loads(GEOJSON.read_text(encoding="utf-8"))
    return [f["geometry"]["coordinates"] for f in g["features"]]


def has_notice():
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    a33 = next((z for z in rules["zones"] if z["id"] == "a33"), None)
    if a33 is None:
        print("rules.json non ha la zona a33", file=sys.stderr)
        sys.exit(1)
    return bool(a33.get("coverageNotice"))


def main():
    s, w, n, e = OSM_BBOX
    # Autostrade e qualunque way con ref A33 (anche se la mappassero prima come trunk); i cantieri
    # solo per dirli, perché oggi nel buco c'è quello di una rotatoria che col lotto non c'entra.
    query = (f'[out:json][timeout:90];(way["highway"="motorway"]({s},{w},{n},{e});'
             f'way["ref"~"^A ?33$"]({s},{w},{n},{e});'
             f'way["highway"="construction"]({s},{w},{n},{e}););out tags geom;')
    doc, host = overpass(query)
    motorways, building = [], 0
    for el in doc["elements"]:
        pts = [[p["lon"], p["lat"]] for p in el.get("geometry", [])]
        tags = el["tags"]
        if tags.get("highway") == "motorway" or tags.get("ref", "").replace(" ", "") == "A33":
            motorways.append(pts)
        else:
            building += 1
    lines = load_lines()
    new_m = uncovered_m(motorways, lines)
    gap_points = geometry_in_gap(lines)
    notice = has_notice()
    print(f"Overpass: {host}")
    print(f"OSM: {len(motorways)} way motorway o ref=A33 nel riquadro, {new_m:.0f} m non in a33.geojson; "
          f"{building} way highway=construction")
    print(f"a33.geojson: {gap_points} punti dentro il buco")
    print(f"rules.json: coverageNotice dell'A33 {'presente' if notice else 'assente'}")
    code, message = verdict(new_m, gap_points, notice)
    print(("OK: " if code == 0 else "DA FARE: ") + message)
    return code


def self_test():
    # Una retta finta per la geometria e una way parallela a 20 m (coperta) o a 500 m (nuova).
    line = [[8.0, 44.70], [8.0, 44.71]]
    near = [[8.00025, 44.70], [8.00025, 44.71]]
    far = [[8.0063, 44.70], [8.0063, 44.71]]
    assert uncovered_m([near], [line]) == 0.0, "una way a 20 m è già nella geometria"
    assert abs(uncovered_m([far], [line]) - 1111) < 20, uncovered_m([far], [line])
    assert geometry_in_gap([[[8.02, 44.70]]]) == 1 and geometry_in_gap([[[7.95, 44.68]]]) == 0
    cases = [
        ((0, 0, True), 0),      # oggi: buco aperto, avviso presente
        ((0, 0, False), 1),     # buco aperto senza avviso
        ((1200, 0, True), 1),   # lotto comparso in OSM
        ((0, 40, True), 1),     # geometria rigenerata ma avviso rimasto
        ((0, 40, False), 0),    # dopo: tutto coerente
    ]
    for args, expected in cases:
        code, message = verdict(*args)
        assert code == expected, (args, code, message)
    print("self-test ok")
    return 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
