"""Convierte una foto en una rejilla de caracteres (solo se ejecuta en local).

La foto NO se guarda en el repo: solo se usa para generar el texto.
"""
from collections import deque
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

RAMP_ASCII = " .'`:-=+*cox#%@"
RAMP_BLOCK = " ░▒▓█"


def load_levels(path, cols, row_factor=0.5, keep=1.0, detail=False):
    """Devuelve (rows x cols) de valores 0..1 (1 = claro) o None para fondo."""
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    g = Image.alpha_composite(bg, im).convert("L")
    w, h = g.size
    px = g.load()

    # Fondo = fuera del círculo de la foto, o blanco conectado con el borde del círculo
    cx, cy, r = w / 2, h / 2, min(w, h) / 2 - 2
    bgmask = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
                bgmask[y][x] = True
    q = deque()
    for y in range(h):
        for x in range(w):
            if bgmask[y][x]:
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not bgmask[ny][nx] and px[nx, ny] > 228:
                bgmask[ny][nx] = True
                q.append((nx, ny))

    g = ImageOps.autocontrast(g, cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(1.25)
    m = Image.new("L", (w, h))
    mp = m.load()
    for y in range(h):
        for x in range(w):
            mp[x, y] = 255 if bgmask[y][x] else 0

    # recorta a la caja del sujeto
    bbox = Image.eval(m, lambda v: 255 - v).getbbox()
    if keep < 1.0:  # recorta parte del jersey para dar más celdas a la cara
        bbox = (bbox[0], bbox[1], bbox[2], bbox[1] + int((bbox[3] - bbox[1]) * keep))
    g, m = g.crop(bbox), m.crop(bbox)
    w, h = g.size
    if detail:
        # sube resolución, contraste local y enfoque: resalta ojos y gafas
        g = g.resize((w * 4, h * 4), Image.LANCZOS)
        m = m.resize((w * 4, h * 4), Image.NEAREST)
        g = g.filter(ImageFilter.UnsharpMask(radius=6, percent=160, threshold=2))
        w, h = g.size
    rows = round(h / w * cols * row_factor)
    g = g.resize((cols, rows), Image.LANCZOS)
    m = m.resize((cols, rows), Image.BOX)
    gp, mp = g.load(), m.load()
    out = []
    for y in range(rows):
        row = []
        for x in range(cols):
            row.append(None if mp[x, y] > 140 else gp[x, y] / 255)
        out.append(row)
    return out


def to_chars(levels, ramp, invert=True, floor=1):
    """invert=True: lo claro se dibuja denso (para fondo oscuro)."""
    n = len(ramp) - 1
    lines = []
    for row in levels:
        s = ""
        for v in row:
            if v is None:
                s += " "
                continue
            t = v if invert else 1 - v
            s += ramp[max(floor, min(n, round(t * n)))]
        lines.append(s)
    return lines


if __name__ == "__main__":
    import sys
    lv = load_levels(sys.argv[1], int(sys.argv[2]))
    ramp = RAMP_BLOCK if len(sys.argv) > 3 else RAMP_ASCII
    print("\n".join(to_chars(lv, ramp)))
