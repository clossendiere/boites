# Lecture simplifiée de dessins SVG pour le photophore.
# Convertit les formes d'un SVG (path, rect, circle, ellipse, line, polyline,
# polygon, use) en contours : segments droits et courbes de Bézier cubiques.
# Ajout au projet Boxes.py (GPL v3 ou ultérieure), sans dépendance externe.

import math
import re
import xml.etree.ElementTree as ET

NOMBRE = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
ESPACES = re.compile(r"[\s,]*")

IGNORES = {"defs", "clipPath", "mask", "symbol", "pattern", "marker", "metadata",
           "title", "desc", "style", "script", "filter", "linearGradient",
           "radialGradient", "namedview", "foreignObject"}
GEOMETRIES = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}


class ErreurChemin(Exception):
    pass


def _nombre(texte, defaut=0.0):
    """Valeur numérique au début d'un texte ('12.5mm' -> 12.5)."""
    if texte is None:
        return defaut
    m = NOMBRE.match(texte.strip())
    return float(m.group()) if m else defaut


# ---------------------------------------------------------------- matrices
IDENTITE = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _produit(m1, m2):
    """m1 · m2 (m2 est appliquée en premier)."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def _appliquer(m, p):
    a, b, c, d, e, f = m
    return (a * p[0] + c * p[1] + e, b * p[0] + d * p[1] + f)


def lire_transform(texte):
    m = IDENTITE
    if not texte:
        return m
    for nom, args in re.findall(r"(\w+)\s*\(([^)]*)\)", texte):
        v = [float(x) for x in NOMBRE.findall(args)]
        t = IDENTITE
        if nom == "matrix" and len(v) == 6:
            t = tuple(v)
        elif nom == "translate" and v:
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0.0)
        elif nom == "scale" and v:
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif nom == "rotate" and v:
            a = math.radians(v[0])
            ca, sa = math.cos(a), math.sin(a)
            t = (ca, sa, -sa, ca, 0, 0)
            if len(v) == 3:
                cx, cy = v[1], v[2]
                t = _produit((1, 0, 0, 1, cx, cy), _produit(t, (1, 0, 0, 1, -cx, -cy)))
        elif nom == "skewX" and v:
            t = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif nom == "skewY" and v:
            t = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        m = _produit(m, t)
    return m


# ------------------------------------------------------------------ chemins
class _Lecteur:
    def __init__(self, texte):
        self.t = texte
        self.i = 0

    def saute(self):
        self.i = ESPACES.match(self.t, self.i).end()

    def fin(self):
        self.saute()
        return self.i >= len(self.t)

    def commande(self):
        self.saute()
        if self.i < len(self.t) and self.t[self.i].isalpha():
            c = self.t[self.i]
            self.i += 1
            return c
        return None

    def nombre(self):
        self.saute()
        m = NOMBRE.match(self.t, self.i)
        if not m:
            raise ErreurChemin("nombre attendu")
        self.i = m.end()
        return float(m.group())

    def drapeau(self):
        self.saute()
        if self.i < len(self.t) and self.t[self.i] in "01":
            v = self.t[self.i] == "1"
            self.i += 1
            return v
        raise ErreurChemin("drapeau d'arc attendu")


def _arc_en_cubiques(x1, y1, rx, ry, phi, fa, fs, x2, y2):
    """Arc SVG -> liste de courbes cubiques (c1, c2, point). None si c'est un simple segment."""
    if x1 == x2 and y1 == y2:
        return []
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0:
        return None
    phi = math.radians(phi % 360.0)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2.0, (y1 - y2) / 2.0
    x1p = cp * dx + sp * dy
    y1p = -sp * dx + cp * dy
    lam = (x1p ** 2) / (rx ** 2) + (y1p ** 2) / (ry ** 2)
    if lam > 1:
        k = math.sqrt(lam)
        rx *= k
        ry *= k
    num = rx ** 2 * ry ** 2 - rx ** 2 * y1p ** 2 - ry ** 2 * x1p ** 2
    den = rx ** 2 * y1p ** 2 + ry ** 2 * x1p ** 2
    coef = math.sqrt(max(0.0, num / den)) if den else 0.0
    if fa == fs:
        coef = -coef
    cxp = coef * rx * y1p / ry
    cyp = -coef * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2.0
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2.0
    ux, uy = (x1p - cxp) / rx, (y1p - cyp) / ry
    vx, vy = (-x1p - cxp) / rx, (-y1p - cyp) / ry
    theta1 = math.atan2(uy, ux)
    dtheta = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
    if not fs and dtheta > 0:
        dtheta -= 2 * math.pi
    elif fs and dtheta < 0:
        dtheta += 2 * math.pi
    n = max(1, int(math.ceil(abs(dtheta) / (math.pi / 2) - 1e-9)))
    delta = dtheta / n
    t = 4.0 / 3.0 * math.tan(delta / 4.0)

    def vers_plan(px, py):
        return (cx + rx * px * cp - ry * py * sp, cy + rx * px * sp + ry * py * cp)

    segs = []
    for k in range(n):
        a1 = theta1 + k * delta
        a2 = a1 + delta
        c1 = vers_plan(math.cos(a1) - t * math.sin(a1), math.sin(a1) + t * math.cos(a1))
        c2 = vers_plan(math.cos(a2) + t * math.sin(a2), math.sin(a2) - t * math.cos(a2))
        p = vers_plan(math.cos(a2), math.sin(a2))
        segs.append((c1, c2, p))
    segs[-1] = (segs[-1][0], segs[-1][1], (x2, y2))
    return segs


def lire_chemin(d):
    """Texte d'un attribut 'd' -> liste de sous-chemins.

    Un sous-chemin est {"debut": (x, y), "segs": [("L", p) | ("C", c1, c2, p)], "ferme": bool}.
    """
    lec = _Lecteur(d or "")
    sous = []
    cur = None
    x = y = sx = sy = 0.0
    cmd = None
    derniere_c2 = None  # point de contrôle précédent pour S
    derniere_q = None   # point de contrôle précédent pour T
    avert = None

    def nouveau(px, py):
        nonlocal cur
        cur = {"debut": (px, py), "segs": [], "ferme": False}
        sous.append(cur)

    try:
        while not lec.fin():
            c = lec.commande()
            if c:
                cmd = c
                if c in "Zz":
                    if cur is not None:
                        cur["ferme"] = True
                    x, y = sx, sy
                    cur = None
                    derniere_c2 = derniere_q = None
                    continue
            elif cmd is None or cmd in "Zz":
                raise ErreurChemin("commande attendue")
            if cmd not in "MmLlHhVvCcSsQqTtAa":
                raise ErreurChemin("commande inconnue " + cmd)
            rel = cmd.islower()
            C = cmd.upper()
            ox, oy = (x, y) if rel else (0.0, 0.0)

            if C == "M":
                x, y = lec.nombre() + ox, lec.nombre() + oy
                sx, sy = x, y
                nouveau(x, y)
                cmd = "l" if rel else "L"   # paires suivantes = segments
                derniere_c2 = derniere_q = None
                continue

            if cur is None:
                nouveau(x, y)
                sx, sy = x, y

            if C == "L":
                x, y = lec.nombre() + ox, lec.nombre() + oy
                cur["segs"].append(("L", (x, y)))
                derniere_c2 = derniere_q = None
            elif C == "H":
                x = lec.nombre() + ox
                cur["segs"].append(("L", (x, y)))
                derniere_c2 = derniere_q = None
            elif C == "V":
                y = lec.nombre() + oy
                cur["segs"].append(("L", (x, y)))
                derniere_c2 = derniere_q = None
            elif C == "C":
                c1 = (lec.nombre() + ox, lec.nombre() + oy)
                c2 = (lec.nombre() + ox, lec.nombre() + oy)
                p = (lec.nombre() + ox, lec.nombre() + oy)
                cur["segs"].append(("C", c1, c2, p))
                derniere_c2, derniere_q = c2, None
                x, y = p
            elif C == "S":
                c1 = (2 * x - derniere_c2[0], 2 * y - derniere_c2[1]) if derniere_c2 else (x, y)
                c2 = (lec.nombre() + ox, lec.nombre() + oy)
                p = (lec.nombre() + ox, lec.nombre() + oy)
                cur["segs"].append(("C", c1, c2, p))
                derniere_c2, derniere_q = c2, None
                x, y = p
            elif C in "QT":
                if C == "Q":
                    q = (lec.nombre() + ox, lec.nombre() + oy)
                else:
                    q = (2 * x - derniere_q[0], 2 * y - derniere_q[1]) if derniere_q else (x, y)
                p = (lec.nombre() + ox, lec.nombre() + oy)
                c1 = (x + 2.0 / 3.0 * (q[0] - x), y + 2.0 / 3.0 * (q[1] - y))
                c2 = (p[0] + 2.0 / 3.0 * (q[0] - p[0]), p[1] + 2.0 / 3.0 * (q[1] - p[1]))
                cur["segs"].append(("C", c1, c2, p))
                derniere_q, derniere_c2 = q, None
                x, y = p
            elif C == "A":
                rx, ry, rot = lec.nombre(), lec.nombre(), lec.nombre()
                fa, fs = lec.drapeau(), lec.drapeau()
                p = (lec.nombre() + ox, lec.nombre() + oy)
                cubiques = _arc_en_cubiques(x, y, rx, ry, rot, fa, fs, p[0], p[1])
                if cubiques is None:
                    cur["segs"].append(("L", p))
                else:
                    for c1, c2, q in cubiques:
                        cur["segs"].append(("C", c1, c2, q))
                derniere_c2 = derniere_q = None
                x, y = p
    except ErreurChemin:
        avert = "chemin mal formé, lu jusqu'à l'erreur"
    return sous, avert


# ------------------------------------------------------------------- formes
def _chemin_depuis(forme, attrs):
    """Retourne (sous-chemins, avertissement) pour un élément géométrique."""
    if forme == "path":
        return lire_chemin(attrs.get("d"))
    if forme == "rect":
        x, y = _nombre(attrs.get("x")), _nombre(attrs.get("y"))
        w, h = _nombre(attrs.get("width")), _nombre(attrs.get("height"))
        if w <= 0 or h <= 0:
            return [], None
        rx = _nombre(attrs.get("rx"), -1)
        ry = _nombre(attrs.get("ry"), -1)
        if rx < 0 and ry < 0:
            rx = ry = 0.0
        elif rx < 0:
            rx = ry
        elif ry < 0:
            ry = rx
        rx, ry = min(rx, w / 2.0), min(ry, h / 2.0)
        if rx <= 0 or ry <= 0:
            d = "M%r %r H%r V%r H%r Z" % (x, y, x + w, y + h, x)
        else:
            d = ("M%r %r H%r A%r %r 0 0 1 %r %r V%r A%r %r 0 0 1 %r %r "
                 "H%r A%r %r 0 0 1 %r %r V%r A%r %r 0 0 1 %r %r Z") % (
                x + rx, y, x + w - rx,
                rx, ry, x + w, y + ry, y + h - ry,
                rx, ry, x + w - rx, y + h,
                x + rx, rx, ry, x, y + h - ry, y + ry,
                rx, ry, x + rx, y)
        return lire_chemin(d)
    if forme in ("circle", "ellipse"):
        cx, cy = _nombre(attrs.get("cx")), _nombre(attrs.get("cy"))
        if forme == "circle":
            rx = ry = _nombre(attrs.get("r"))
        else:
            rx, ry = _nombre(attrs.get("rx")), _nombre(attrs.get("ry"))
        if rx <= 0 or ry <= 0:
            return [], None
        d = "M%r %r A%r %r 0 1 0 %r %r A%r %r 0 1 0 %r %r Z" % (
            cx + rx, cy, rx, ry, cx - rx, cy, rx, ry, cx + rx, cy)
        return lire_chemin(d)
    if forme == "line":
        d = "M%r %r L%r %r" % (_nombre(attrs.get("x1")), _nombre(attrs.get("y1")),
                               _nombre(attrs.get("x2")), _nombre(attrs.get("y2")))
        return lire_chemin(d)
    if forme in ("polyline", "polygon"):
        v = [float(n) for n in NOMBRE.findall(attrs.get("points", ""))]
        if len(v) < 4:
            return [], None
        pts = [(v[i], v[i + 1]) for i in range(0, len(v) - 1, 2)]
        sp = {"debut": pts[0], "segs": [("L", p) for p in pts[1:]], "ferme": forme == "polygon"}
        return [sp], None
    return [], None


def _transformer(sp, m):
    def f(p):
        return _appliquer(m, p)
    segs = []
    for s in sp["segs"]:
        if s[0] == "L":
            segs.append(("L", f(s[1])))
        else:
            segs.append(("C", f(s[1]), f(s[2]), f(s[3])))
    return {"debut": f(sp["debut"]), "segs": segs, "ferme": sp["ferme"]}


# --------------------------------------------------------------- aplatissement
def _aplatir_sous_chemin(sp, n_cubique=24):
    """Points d'un sous-chemin avec un nombre fixe de pas par courbe (sert aux cadres)."""
    pts = [sp["debut"]]
    for s in sp["segs"]:
        p0 = pts[-1]
        if s[0] == "L":
            pts.append(s[1])
        else:
            _, c1, c2, p3 = s
            for k in range(1, n_cubique + 1):
                pts.append(_bezier(p0, c1, c2, p3, k / n_cubique))
    return pts


def _bezier(p0, p1, p2, p3, t):
    u = 1.0 - t
    a, b, c, d = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
    return (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
            a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])


def aplatir(sp, echelle, tolerance=0.02):
    """Points d'un sous-chemin ; la flèche de chaque courbe reste sous `tolerance` mm
    une fois le dessin multiplié par `echelle`."""
    pts = [sp["debut"]]
    for s in sp["segs"]:
        p0 = pts[-1]
        if s[0] == "L":
            pts.append(s[1])
            continue
        _, c1, c2, p3 = s
        dd = max(math.hypot(p0[0] - 2 * c1[0] + c2[0], p0[1] - 2 * c1[1] + c2[1]),
                 math.hypot(c1[0] - 2 * c2[0] + p3[0], c1[1] - 2 * c2[1] + p3[1])) * echelle
        n = max(1, min(400, int(math.ceil(math.sqrt(0.75 * dd / tolerance)))))
        for k in range(1, n + 1):
            pts.append(_bezier(p0, c1, c2, p3, k / n) if k < n else p3)
    return pts


# ------------------------------------------------------------------ dessin
class Dessin:
    def __init__(self):
        self.formes = []          # {"nom": str, "sous": [sous-chemins]}
        self.largeur = 0.0
        self.hauteur = 0.0
        self.avertissements = []

    @property
    def sous_chemins(self):
        return [sp for f in self.formes for sp in f["sous"]]


def _est_rectangle(sous):
    """Vrai pour une forme formée d'un seul rectangle droit (fond éventuel)."""
    if len(sous) != 1 or any(s[0] != "L" for s in sous[0]["segs"]):
        return False
    pts = _aplatir_sous_chemin(sous[0])
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    e = 1e-6 * max(1.0, x1 - x0, y1 - y0)
    return all((abs(p[0] - x0) < e or abs(p[0] - x1) < e) and
               (abs(p[1] - y0) < e or abs(p[1] - y1) < e) for p in pts) and len(set(
                   (round(p[0], 6), round(p[1], 6)) for p in pts)) == 4


def lire_svg(texte, ignorer_fond=True):
    """Lit un SVG et retourne un Dessin dont le cadre englobant démarre en (0, 0)."""
    try:
        racine = ET.fromstring(texte.encode("utf-8") if isinstance(texte, str) else texte)
    except ET.ParseError as e:
        raise ValueError("fichier SVG illisible (%s)" % e)

    dessin = Dessin()
    ids = {}
    for el in racine.iter():
        if el.get("id"):
            ids[el.get("id")] = el
    ignores = {"texte": 0, "image": 0, "use": 0}

    def visite(el, m, profondeur=0):
        if profondeur > 60:
            return
        nom = el.tag.split("}")[-1] if isinstance(el.tag, str) else ""
        if nom in IGNORES:
            return
        style = (el.get("style") or "").replace(" ", "")
        if el.get("display") == "none" or "display:none" in style:
            return
        m = _produit(m, lire_transform(el.get("transform")))
        if nom in GEOMETRIES:
            sous, avert = _chemin_depuis(nom, el.attrib)
            if avert:
                dessin.avertissements.append(avert)
            sous = [_transformer(sp, m) for sp in sous if sp["segs"]]
            if sous:
                dessin.formes.append({"nom": nom, "sous": sous})
            return
        if nom == "text":
            ignores["texte"] += 1
            return
        if nom == "image":
            ignores["image"] += 1
            return
        if nom == "use":
            href = el.get("{http://www.w3.org/1999/xlink}href") or el.get("href") or ""
            cible = ids.get(href.lstrip("#"))
            if cible is None:
                ignores["use"] += 1
                return
            dec = (1, 0, 0, 1, _nombre(el.get("x")), _nombre(el.get("y")))
            visite(cible, _produit(m, dec), profondeur + 1)
            return
        for enfant in el:
            visite(enfant, m, profondeur + 1)

    visite(racine, IDENTITE)

    if ignores["texte"]:
        dessin.avertissements.append(
            "%d texte(s) ignoré(s) : convertissez-les en chemins (Inkscape : Chemin > Objet en chemin)"
            % ignores["texte"])
    if ignores["image"]:
        dessin.avertissements.append("%d image(s) ignorée(s)" % ignores["image"])
    if ignores["use"]:
        dessin.avertissements.append("%d clone(s) <use> introuvable(s)" % ignores["use"])

    if not dessin.formes:
        raise ValueError("aucune forme (chemin, rectangle, cercle…) trouvée dans le SVG")

    def cadre(formes):
        pts = [p for f in formes for sp in f["sous"] for p in _aplatir_sous_chemin(sp)]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    if ignorer_fond and len(dessin.formes) > 1:
        x0, y0, x1, y1 = cadre(dessin.formes)
        w, h = x1 - x0, y1 - y0
        gardees = []
        for f in dessin.formes:
            fx0, fy0, fx1, fy1 = cadre([f])
            fond = (f["nom"] in ("rect", "path", "polygon") and w > 0 and h > 0 and
                    (fx1 - fx0) >= 0.98 * w and (fy1 - fy0) >= 0.98 * h and _est_rectangle(f["sous"]))
            if not fond:
                gardees.append(f)
        if gardees and len(gardees) < len(dessin.formes):
            dessin.avertissements.append("rectangle de fond ignoré")
            dessin.formes = gardees

    x0, y0, x1, y1 = cadre(dessin.formes)
    dessin.largeur, dessin.hauteur = x1 - x0, y1 - y0
    decal = (1, 0, 0, 1, -x0, -y0)
    for f in dessin.formes:
        f["sous"] = [_transformer(sp, decal) for sp in f["sous"]]
    if dessin.largeur <= 0 and dessin.hauteur <= 0:
        raise ValueError("le dessin est réduit à un point")
    return dessin
