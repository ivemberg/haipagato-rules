#!/usr/bin/env python3
"""Geometria e regola di rilevamento per le zone free flow.

Separato da build_freeflow.py per poter essere importato dai test senza
rieseguire il download. Solo libreria standard.
"""
import math

LAT0 = 45.75                       # baricentro fra Varese, Como e la Brianza
M_LON = 111320.0 * math.cos(math.radians(LAT0))
M_LAT = 110540.0

# Parametri di rilevamento. Devono restare allineati a rules.json -> geometry.
TOLERANCE_M = 40.0
MIN_CONSECUTIVE_POINTS = 5
MIN_SPEED_KMH = 50.0
MAX_BEARING_DELTA_DEG = 30.0
MIN_PROGRESS_M = 2000.0
# Anche il ramo veloce vuole un avanzamento minimo. Senza, bastano cinque punti
# su una strada parallela percorsa in fretta per fabbricare un transito: il tratto
# parallelo piu' lungo misurato e' 575 m, e a 70 km/h si copre in 30 secondi.
MIN_FAST_PROGRESS_M = 1000.0
# Soglie rinforzate sui tratti con viabilita' ordinaria entro TOLERANCE_M
AMBIGUOUS_MIN_PROGRESS_M = 3000.0
AMBIGUOUS_MIN_FAST_PROGRESS_M = 1500.0
AMBIGUOUS_MIN_SPEED_KMH = 80.0


def ambiguity_threshold_m(min_fast_progress=MIN_FAST_PROGRESS_M,
                          min_progress=MIN_PROGRESS_M):
    """Lunghezza oltre la quale un tratto parallelo puo' generare un falso positivo.

    E' il minimo fra i due rami: basta che il piu' permissivo scatti. Prima della
    correzione il ramo veloce non aveva soglia di avanzamento, quindi il minimo era
    zero e il criterio di ambiguita' guardava solo il ramo lento.
    """
    return min(min_fast_progress, min_progress)


def xy(p):
    """Da (lon, lat) a metri piani locali."""
    return (p[0] * M_LON, p[1] * M_LAT)


def dist_m(a, b):
    ax, ay = xy(a)
    bx, by = xy(b)
    return math.hypot(ax - bx, ay - by)


def project_on_seg(p, a, b):
    """Restituisce (distanza_m, t, punto_proiettato) di p sul segmento a-b."""
    px, py = xy(p)
    ax, ay = xy(a)
    bx, by = xy(b)
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    if L == 0:
        return math.hypot(px - ax, py - ay), 0.0, a
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy), t, [qx / M_LON, qy / M_LAT]


def seg_bearing(a, b):
    """Giacitura del segmento in gradi, 0-360."""
    ax, ay = xy(a)
    bx, by = xy(b)
    return math.degrees(math.atan2(bx - ax, by - ay)) % 360.0


def bearing_delta_unoriented(b1, b2):
    """Differenza di giacitura modulo 180.

    Una carreggiata doppia e' due way OSM con verso opposto: con un confronto
    orientato chi viaggia sulla carreggiata disegnata al contrario risulterebbe
    a 180 gradi e non verrebbe mai rilevato.
    """
    d = abs(b1 - b2) % 180.0
    return min(d, 180.0 - d)


class Chain:
    """Polilinea ordinata con ascissa curvilinea, per misurare l'avanzamento."""

    def __init__(self, pts, ambiguous=False):
        self.pts = pts
        self.ambiguous = ambiguous
        self.s = [0.0]
        for i in range(1, len(pts)):
            self.s.append(self.s[-1] + dist_m(pts[i - 1], pts[i]))

    @property
    def length_m(self):
        return self.s[-1]

    def locate(self, p):
        """(distanza_m, ascissa_curvilinea, giacitura_locale) del punto piu' vicino."""
        best = (float("inf"), 0.0, 0.0)
        for i in range(len(self.pts) - 1):
            d, t, _ = project_on_seg(p, self.pts[i], self.pts[i + 1])
            if d < best[0]:
                s = self.s[i] + t * (self.s[i + 1] - self.s[i])
                best = (d, s, seg_bearing(self.pts[i], self.pts[i + 1]))
        return best


def stitch(ways, tol_m=1.0):
    """Unisce i frammenti OSM in catene ordinate.

    Necessario perche' l'ascissa curvilinea, e quindi l'avanzamento, non e'
    definita su una MultiLineString di frammenti sconnessi.
    """
    segs = [list(w) for w in ways if len(w) >= 2]
    chains = []
    while segs:
        cur = segs.pop(0)
        changed = True
        while changed:
            changed = False
            for i, s in enumerate(segs):
                if dist_m(cur[-1], s[0]) <= tol_m:
                    cur = cur + s[1:]
                elif dist_m(cur[-1], s[-1]) <= tol_m:
                    cur = cur + s[::-1][1:]
                elif dist_m(cur[0], s[-1]) <= tol_m:
                    cur = s[:-1] + cur
                elif dist_m(cur[0], s[0]) <= tol_m:
                    cur = s[::-1][:-1] + cur
                else:
                    continue
                segs.pop(i)
                changed = True
                break
        chains.append(cur)
    return chains


def speed_kmh(p0, p1):
    dt = p1[2] - p0[2]
    if dt <= 0:
        return 0.0
    return dist_m(p0, p1) / dt * 3.6


def detect(track, chains,
           tolerance_m=TOLERANCE_M,
           min_points=MIN_CONSECUTIVE_POINTS,
           min_speed=MIN_SPEED_KMH,
           max_bearing=MAX_BEARING_DELTA_DEG,
           min_progress=MIN_PROGRESS_M,
           min_fast_progress=MIN_FAST_PROGRESS_M,
           amb_progress=AMBIGUOUS_MIN_PROGRESS_M,
           amb_fast_progress=AMBIGUOUS_MIN_FAST_PROGRESS_M,
           amb_speed=AMBIGUOUS_MIN_SPEED_KMH,
           in_vehicle=True):
    """Rileva un transito free flow su una traccia.

    track: lista di (lon, lat, t_secondi).
    Restituisce (esito, motivo) con esito in confermato / probabile / nessuno.

    Due vie indipendenti, come da piano:
      1. N punti consecutivi vicini, veloci e allineati;
      2. avanzamento della proiezione oltre soglia, che copre le code.
    Su catene marcate ambiguous valgono le soglie rinforzate.
    """
    if not in_vehicle:
        return ("nessuno", "filtro in-auto non soddisfatto")
    if len(track) < 2:
        return ("nessuno", "traccia troppo corta")

    best = ("nessuno", "nessuna catena soddisfa le condizioni")
    for ch in chains:
        amb = ch.ambiguous
        need_speed = amb_speed if amb else min_speed
        need_prog = amb_progress if amb else min_progress
        need_fast_prog = amb_fast_progress if amb else min_fast_progress

        loc = [ch.locate(p) for p in track]
        near = [i for i, (d, _, _) in enumerate(loc) if d <= tolerance_m]
        if not near:
            continue

        # via 1: N punti consecutivi vicini, veloci e allineati
        run = 0
        hit_run = False
        for i in range(1, len(track)):
            d, _, brg = loc[i]
            if d > tolerance_m:
                run = 0
                continue
            v = speed_kmh(track[i - 1], track[i])
            course = seg_bearing(track[i - 1], track[i])
            aligned = bearing_delta_unoriented(course, brg) <= max_bearing
            if v > need_speed and aligned:
                run += 1
                if run >= min_points:
                    hit_run = True
                    break
            else:
                run = 0

        # via 2: avanzamento della proiezione, robusto al rumore da fermo
        ss = [loc[i][1] for i in near]
        progress = max(ss) - min(ss)

        # Il ramo veloce vuole anche un avanzamento minimo: cinque punti veloci e
        # allineati si ottengono anche su una strada parallela di poche centinaia
        # di metri, e da soli non provano di essere in autostrada.
        if hit_run and progress > need_fast_prog:
            return ("confermato",
                    f"{min_points} punti sopra {need_speed:.0f} km/h allineati, "
                    f"avanzamento {progress:.0f} m oltre {need_fast_prog:.0f} m")
        if progress > need_prog:
            return ("confermato", f"avanzamento {progress:.0f} m oltre {need_prog:.0f} m")
        # Nel dubbio probabile invece che mancato, ma non sotto la soglia di
        # ambiguita': li' un tratto di strada parallela e un pezzo di autostrada
        # sono indistinguibili, e un "probabile" sarebbe comunque un falso positivo
        # da far confermare all'utente ogni volta che costeggia l'autostrada.
        floor = ambiguity_threshold_m(need_fast_prog, need_prog)
        if progress > floor:
            best = ("probabile", f"avanzamento {progress:.0f} m sotto soglia"
                                 + (" (tratto ambiguo)" if amb else ""))
    return best
