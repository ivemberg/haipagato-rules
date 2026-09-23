"""Geometria e macchina a stati per le zone a poligono (Area C).

Estratto da build_areac.py per non averne due copie: build_gpx.py verifica i percorsi
generati con la stessa identica logica con cui sono stati tarati i parametri.

Solo libreria standard.
"""
import math

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


