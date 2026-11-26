"""Sprites pixel-art du chat (chaînes de caractères -> grilles de couleurs).

Chaque sprite est une liste de chaînes de même longueur. Un caractère = un pixel.
'.' = transparent. Les autres lettres renvoient à PALETTE.
"""

PALETTE = {
    "K": "#3b2a22",  # contour
    "O": "#f2a65a",  # pelage orange
    "D": "#d9823b",  # rayures
    "L": "#c46f2c",  # patte arrière (plus sombre)
    "W": "#fff1df",  # crème
    "P": "#f4a3b4",  # rose (oreilles, nez)
    "E": "#2b2b3a",  # yeux
    "S": "#ffffff",  # reflet
    "R": "#e8455a",  # coeur
    "r": "#ff99a8",  # reflet coeur
    "B": "#5aa9e6",  # eau
    "b": "#a8dcff",  # reflet eau
    "M": "#5b6fd6",  # bol
    "m": "#8797ee",  # bol clair
    "C": "#9b5a2b",  # croquettes
    "c": "#c98a4f",  # croquettes claires
    "Y": "#d65b9e",  # pelote
    "y": "#f08cc0",  # pelote clair
    "Z": "#7b8cff",  # Zzz
    "G": "#ffd84a",  # étoile / poisson
    "k": "#26262e",  # corps de mouche
    "F": "#cfe6f5",  # ailes de mouche
    "f": "#e8455a",  # yeux de mouche
}


def mirror_half(half_rows):
    """Construit une ligne symétrique à partir de la moitié gauche."""
    return [row + row[::-1] for row in half_rows]


def flip(rows):
    return [row[::-1] for row in rows]


def overlay(base, patch, ox, oy):
    """Retourne une copie de base avec patch collé en (ox, oy) ('.' ignorés)."""
    out = [list(r) for r in base]
    for y, row in enumerate(patch):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            yy, xx = oy + y, ox + x
            if 0 <= yy < len(out) and 0 <= xx < len(out[0]):
                out[yy][xx] = ch
    return ["".join(r) for r in out]


def points(base, pts):
    out = [list(r) for r in base]
    for x, y, ch in pts:
        out[y][x] = ch
    return ["".join(r) for r in out]


def pad(rows, width, height, ox=0, oy=0):
    canvas = ["." * width for _ in range(height)]
    return overlay(canvas, rows, ox, oy)


# ---------------------------------------------------------------- chat assis
SIT_HALF = [
    "............",
    "...K........",
    "..KOK.......",
    "..KPOK......",
    ".KPPOOK.....",
    ".KPPOOOKKKKK",
    ".KOOOOOOODOO",
    "KOOOOOOOOODO",
    "KOOOOOOOOOOO",
    "KOOOOOOOOOOO",
    "KOOOOOOOOOOO",
    "KOOOOOOOOOWW",
    ".KOOOOOOWWWW",
    "..KKOOOWWWWW",
    "...KOOOOWWWW",
    "..KOOOOOWWWW",
    "..KODOOOOWWW",
    ".KOOODOOOWWW",
    ".KOOOOOOOOWW",
    ".KODOOOOOOOW",
    ".KOODOOOOOOO",
    ".KOOOOOKWWWK",
    ".KOOOOKWWWWK",
    "..KKKKKKKKKK",
]
SIT_BODY = mirror_half(SIT_HALF)  # 24 x 24

# yeux / bouche (coordonnées dans le sprite assis)
FACE_NOSE = [(11, 10, "P"), (12, 10, "P")]
FACE_MOUTH = [(10, 11, "K"), (11, 12, "K"), (12, 12, "K"), (13, 11, "K")]
FACE_MOUTH_OPEN = [(10, 11, "K"), (13, 11, "K"), (11, 11, "K"), (12, 11, "K"),
                   (11, 12, "P"), (12, 12, "P"), (10, 12, "K"), (13, 12, "K"),
                   (11, 13, "K"), (12, 13, "K")]


def _eye_pts(kind):
    pts = []
    for ex, mirror in ((5, False), (17, True)):
        if kind == "open":
            sx = ex if mirror else ex + 1
            pts += [(ex, 7, "E"), (ex + 1, 7, "E"), (ex, 8, "E"), (ex + 1, 8, "E"),
                    (ex, 9, "E"), (ex + 1, 9, "E"), (sx, 7, "S")]
        elif kind == "closed":
            pts += [(ex - 1, 9, "K"), (ex, 9, "K"), (ex + 1, 9, "K"), (ex + 2, 9, "K")]
        elif kind == "happy":
            pts += [(ex - 1, 9, "K"), (ex, 8, "K"), (ex + 1, 8, "K"), (ex + 2, 9, "K")]
        elif kind == "cross":  # yeux qui louchent (mode FOU)
            px = ex + 1 if not mirror else ex
            pts += [(ex, 7, "S"), (ex + 1, 7, "S"), (ex, 8, "S"), (ex + 1, 8, "S"),
                    (ex, 9, "S"), (ex + 1, 9, "S"), (px, 8, "E"), (px, 9, "E")]
        elif kind == "sad":
            pts += [(ex, 8, "E"), (ex + 1, 8, "E"), (ex, 9, "E"), (ex + 1, 9, "E")]
            if mirror:
                pts += [(ex - 1, 7, "K"), (ex, 6, "K")]
            else:
                pts += [(ex + 2, 7, "K"), (ex + 1, 6, "K")]
    return pts


BLUSH = [(2, 11, "P"), (3, 11, "P"), (20, 11, "P"), (21, 11, "P")]

TAIL_UP = [
    "....KK..",
    "...KOOK.",
    "...KODK.",
    "....KOK.",
    "....KOK.",
    "...KOOK.",
    "..KODK..",
    ".KOOK...",
    "KODK....",
    "KOOK....",
    "KOK.....",
    "KK......",
]
TAIL_SIDE = [
    "........",
    "........",
    "......KK",
    ".....KOK",
    ".....KDK",
    "....KOOK",
    "....KOK.",
    "...KOOK.",
    "..KODK..",
    ".KOOK...",
    "KOOK....",
    "KKK.....",
]


def make_sit(eyes="open", mouth="normal", tail="up", blush=False):
    tail_rows = TAIL_UP if tail == "up" else TAIL_SIDE
    canvas = pad([], 31, 24)
    canvas = overlay(canvas, tail_rows, 21, 12)
    canvas = overlay(canvas, SIT_BODY, 0, 0)
    pts = _eye_pts(eyes) + FACE_NOSE
    pts += FACE_MOUTH_OPEN if mouth == "open" else FACE_MOUTH
    if blush:
        pts += BLUSH
    return points(canvas, pts)


# ---------------------------------------------------------------- chat couché
LOAF_BODY_HALF = [
    "KOOOOOOOOOOO",
    "KODOOOOOOOOO",
    "KOODOOOOOOOO",
    "KOOOOOOOOOOO",
    "KOOOOKWWWKKK",
    ".KKKKKKKKKKK",
]


def make_sleep(eyes="closed"):
    head = SIT_BODY[1:13]
    body = mirror_half(LOAF_BODY_HALF)
    rows = head + body  # 18 lignes
    tail = [
        "KKKKKKKK..",
        "OOOOOOOOKK",
        "OODOOOOOOK",
        "KKKKKKKKKK",
    ]
    canvas = pad([], 31, 24)
    canvas = overlay(canvas, rows, 0, 6)
    canvas = overlay(canvas, tail, 20, 19)
    pts = [(x, y + 5, c) for x, y, c in _eye_pts(eyes) + FACE_NOSE + FACE_MOUTH]
    return points(canvas, pts)


# ---------------------------------------------------------------- chat qui marche (profil, vers la droite)
WALK_BODY = [
    "...................K....K.....",
    "..................KPK..KPK....",
    "..................KOOKKOOOK...",
    ".................KOOOOOOOOOK..",
    "..KK.............KOODOOOOOOK..",
    ".KOOK............KOOOOOOEEOOK.",
    ".KOK.............KOOOOOOESOOK.",
    ".KOK.............KOOOOOOOOOOPK",
    "..KOK............KWWOOOOOWWWK.",
    "..KOK.......KKKKKKWWWOOOWWWK..",
    "...KOKKKKKKKOOOOODDKWWWWWKK...",
    "....KOOOOOODOOOODOOOKKKKK.....",
    "....KOOOODOOOODOOOOOOOOK......",
    "....KOOOOOOOOOOOOOOOWWWK......",
    "....KOOOOOOOOOOOOOOWWWWK......",
    "....KKKKKKKKKKKKKKKKKKKK......",
]
LEG_NEAR = ["KOK", "KOK", "KOK", "KWK", "KKK"]
LEG_FAR = ["KLK", "KLK", "KLK", "KWK", "KKK"]


def make_walk(frame, facing="right", crazy=False):
    canvas = pad([], 31, 24)
    canvas = overlay(canvas, WALK_BODY, 0, 4)
    if crazy:  # grand oeil blanc, petite pupille, bouche ouverte
        canvas = points(canvas, [(23, 9, "S"), (24, 9, "S"), (25, 9, "S"),
                                 (23, 10, "S"), (24, 10, "S"), (25, 10, "E"),
                                 (27, 12, "K"), (28, 12, "P"), (27, 13, "K")])
    if frame == 0:
        legs = [(8, LEG_FAR), (20, LEG_FAR), (5, LEG_NEAR), (17, LEG_NEAR)]
    else:
        legs = [(4, LEG_FAR), (16, LEG_FAR), (9, LEG_NEAR), (21, LEG_NEAR)]
    for x, leg in legs:
        canvas = overlay(canvas, leg, x, 19)
    return canvas if facing == "right" else flip(canvas)


# ---------------------------------------------------------------- réactions
# bouche grande ouverte (bâillement), sous le nez
FACE_YAWN = [(10, 11, "K"), (11, 11, "K"), (12, 11, "K"), (13, 11, "K"),
             (9, 12, "K"), (10, 12, "P"), (11, 12, "P"), (12, 12, "P"), (13, 12, "P"), (14, 12, "K"),
             (9, 13, "K"), (10, 13, "P"), (11, 13, "R"), (12, 13, "R"), (13, 13, "P"), (14, 13, "K"),
             (10, 14, "K"), (11, 14, "K"), (12, 14, "K"), (13, 14, "K")]
# patte avant levée jusqu'à la bouche (toilette)
GROOM_PAW = [
    "..KKKK..",
    ".KWWWWK.",
    ".KWWWWK.",
    ".KOOOOK.",
    "..KOOOK.",
    "..KOOOK.",
    "..KODK..",
    "..KOOK..",
]


def _sit_face(rows, eyes, mouth_pts, dy=0):
    return points(rows, [(x, y + dy, c) for x, y, c in _eye_pts(eyes) + FACE_NOSE + mouth_pts])


def make_yawn():
    """Assis, yeux fermés, bouche grande ouverte."""
    canvas = pad([], 31, 24)
    canvas = overlay(canvas, TAIL_UP, 21, 12)
    canvas = overlay(canvas, SIT_BODY, 0, 0)
    return _sit_face(canvas, "closed", FACE_YAWN)


def make_groom(frame):
    """Fait sa toilette : patte levée et petite langue rose ; frame 0/1 = patte haute/basse."""
    canvas = make_sit("closed", "normal", "side")
    if frame == 0:
        canvas = overlay(canvas, GROOM_PAW, 5, 10)
        return points(canvas, [(13, 12, "P"), (13, 13, "P")])
    canvas = overlay(canvas, GROOM_PAW, 5, 13)
    return points(canvas, [(11, 12, "P"), (12, 12, "P"), (12, 13, "P")])


def _wide_eyes(look):
    """Grands yeux blancs (3 x 3) et pupilles de 1 x 2 pixels.
    look : "center" (regarde devant), "in" (louche), "down" (louche sur le bout du nez)."""
    pts = []
    for left, right in ((4, 6), (17, 19)):           # colonnes de chaque oeil
        pts += [(x, y, "S") for x in range(left, right + 1) for y in (7, 8, 9)]
        inner = right if left == 4 else left           # côté du nez
        if look == "center":
            px, rows = left + 1, (7, 8)
        elif look == "in":
            px, rows = inner, (7, 8)
        else:
            px, rows = inner, (8, 9)
        pts += [(px, y, "E") for y in rows]
    return pts


def make_cross_eyed(look, mouth="normal"):
    """Assis, grands yeux qui suivent quelque chose jusqu'à son nez (et louchent dessus)."""
    canvas = pad([], 31, 24)
    canvas = overlay(canvas, TAIL_UP, 21, 12)
    canvas = overlay(canvas, SIT_BODY, 0, 0)
    pts = _wide_eyes(look) + FACE_NOSE
    pts += FACE_MOUTH_OPEN if mouth == "open" else FACE_MOUTH
    return points(canvas, pts)


# coccinelle (vue de dessus) qui vient se poser sur son nez
LADYBUG = [
    "..k.k..",
    "...k...",
    "..kkk..",
    ".RrkRR.",
    "RkRkRkR",
    "RRRkRRR",
    ".RkRkR.",
    "..RRR..",
]
LADYBUG_FLY = [                     # ailes ouvertes
    "..k.k..",
    "FF.k.FF",
    "FFkkkFF",
    ".RrkRR.",
    "RkR.RkR",
    "RRR.RRR",
    ".RkRkR.",
    "..R.R..",
]


def make_stretch(extra, yawn=False):
    """S'étire vers le haut : buste allongé de `extra` lignes (sprite plus haut que 24)."""
    torso = SIT_BODY[15:17]       # lignes du buste sans encoche : on peut les répéter
    body = SIT_BODY[:14] + [torso[i % len(torso)] for i in range(extra)] + SIT_BODY[14:]
    canvas = pad([], 31, 24 + extra)
    canvas = overlay(canvas, TAIL_UP, 21, 12 + extra)
    canvas = overlay(canvas, body, 0, 0)
    return _sit_face(canvas, "closed", FACE_YAWN if yawn else FACE_MOUTH)


# ---------------------------------------------------------------- accessoires
HEART = [
    ".KK.KK.",
    "KRrKRRK",
    "KRRRRRK",
    ".KRRRK.",
    "..KRK..",
    "...K...",
]

ZZZ = [
    "ZZZZ",
    "..Z.",
    ".Z..",
    "ZZZZ",
]

BOWL_FOOD = [
    "..cCcCcCcC..",
    ".CcCcCcCcCc.",
    "KMMMMMMMMMMK",
    "KMmmmmmmmmMK",
    ".KMMMMMMMMK.",
    "..KKKKKKKK..",
]
BOWL_FOOD_EMPTY = [
    "............",
    "............",
    "KMMMMMMMMMMK",
    "KMmmmmmmmmMK",
    ".KMMMMMMMMK.",
    "..KKKKKKKK..",
]
BOWL_WATER = [
    "............",
    ".BbBBBbBBBB.",
    "KMMMMMMMMMMK",
    "KMmmmmmmmmMK",
    ".KMMMMMMMMK.",
    "..KKKKKKKK..",
]

YARN = [
    "..KKKK..",
    ".KYyYYK.",
    "KYYyYyYK",
    "KyYYyYYK",
    "KYyYYyYK",
    ".KYYyYK.",
    "..KKKKYY",
]

def add_outline(rows, ch, around="kf"):
    """Entoure (1 px) les pixels de `around` avec `ch`, en agrandissant le sprite."""
    w, h = len(rows[0]) + 2, len(rows) + 2
    grid = [list("." * w) for _ in range(h)]
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c in around:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if grid[y + 1 + dy][x + 1 + dx] == ".":
                            grid[y + 1 + dy][x + 1 + dx] = ch
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c != ".":
                grid[y + 1][x + 1] = c
    return ["".join(r) for r in grid]


PALETTE["w"] = "#f4f6f8"  # contour clair (visible sur fond sombre)
FLY = [add_outline(f, "w") for f in (
    [   # ailes en haut
        "FF...FF",
        ".FF.FF.",
        "..kkf..",
        ".kkkkk.",
        "..k.k..",
    ],
    [   # ailes en bas
        ".......",
        "..kkf..",
        "FFkkkFF",
        "FF.k.FF",
        ".......",
    ],
)]

DUST = [
    ".WW.",
    "WWWW",
    ".WW.",
]

SPARKLE = [
    "..G..",
    ".GGG.",
    "GGGGG",
    ".GGG.",
    "..G..",
]


def sprite_size(rows):
    return len(rows[0]), len(rows)
