"""Genera los 3 SVG animados del README a partir de tu foto (en local).

Uso:  python tools/gen.py RUTA_FOTO
Salida: assets/terminal.svg, assets/scan.svg, assets/minimal.svg
La foto no se copia ni se incrusta: solo se guarda el texto ASCII.
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import face  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "assets")
MONO = "'JetBrains Mono','Fira Code',Consolas,'DejaVu Sans Mono',Menlo,monospace"
SANS = "'Segoe UI',Inter,'Helvetica Neue',Arial,sans-serif"
BG, BORDER, BAR = "#0d1117", "#30363d", "#161b22"
TXT, MUTED = "#c9d1d9", "#8b949e"
RED, CYAN, VIOLET, GREEN, YELLOW = "#ff4d4d", "#4ec9d4", "#a78bfa", "#3fb950", "#e5c07b"

NAME = "Jesús Peñaranda"
HOST = "jesus@fib-upc"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Anim:
    """Acumula @keyframes; todos comparten el mismo ciclo T (bucle infinito)."""

    def __init__(self, T):
        self.T, self.css, self.n = T, [], 0

    def p(self, t):
        return f"{max(0.0, min(100.0, t / self.T * 100)):.3f}%"

    def _add(self, frames):
        self.n += 1
        name = f"k{self.n}"
        body = " ".join(f"{k}{{{v}}}" for k, v in frames)
        self.css.append(f"@keyframes {name}{{{body}}}")
        self.css.append(f".{name}{{animation:{name} {self.T}s linear infinite}}")
        return name

    def show(self, t_on, t_off, fade=0.08):
        """Visible entre t_on y t_off."""
        return self._add([
            ("0%", "opacity:0"), (self.p(t_on), "opacity:0"),
            (self.p(t_on + fade), "opacity:1"), (self.p(t_off), "opacity:1"),
            (self.p(t_off + 0.3), "opacity:0"), ("100%", "opacity:0")])

    def hide(self, t_off, t_back):
        """Visible desde el inicio hasta t_off; vuelve en t_back."""
        return self._add([
            ("0%", "opacity:1"), (self.p(t_off), "opacity:1"),
            (self.p(t_off + 0.02), "opacity:0"), (self.p(t_back), "opacity:0"),
            (self.p(t_back + 0.3), "opacity:1"), ("100%", "opacity:1")])

    def slide(self, segs):
        """segs: [(t0, t1, x0, x1, nsteps)] -> translateX por tramos con steps()."""
        fr = [("0%", f"transform:translateX({segs[0][2]}px)")]
        for t0, t1, x0, x1, n in segs:
            fr.append((self.p(t0), f"transform:translateX({x0}px);animation-timing-function:steps({max(1, n)},end)"))
            fr.append((self.p(t1), f"transform:translateX({x1}px)"))
        fr.append(("100%", f"transform:translateX({segs[-1][3]}px)"))
        return self._add(fr)

    def type_cover(self, t0, dur, width, n, t_reset):
        """Rectángulo tapa que se desplaza a la derecha = efecto máquina de escribir."""
        return self.slide([(t0, t0 + dur, 0, width, n), (t_reset, t_reset + 0.01, width, 0, 1)])

    def style(self, extra=""):
        return "<style>" + extra + "".join(self.css) + "</style>"


def face_rows(lines, x, y, cw, lh, fs, fill, cls_for_row=None, extra=""):
    out = []
    W = len(lines[0]) * cw
    for i, ln in enumerate(lines):
        cls = f' class="{cls_for_row(i)}"' if cls_for_row else ""
        out.append(
            f'<text{cls} x="{x}" y="{y + i * lh:.1f}" textLength="{W:.1f}" lengthAdjust="spacing" '
            f'font-size="{fs}" fill="{fill}" xml:space="preserve"{extra}>{esc(ln)}</text>')
    return "\n".join(out)


def shaded_rows(levels, x, y, cw, lh, fs, cls_for_row=None, lo=(0x3a, 0x42, 0x4c), hi=(0xf3, 0xf8, 0xfd), steps=14, gamma=0.8):
    """Cara en bloques con tonos de gris por celda (más detalle que solo densidad)."""
    ramp = face.RAMP_BLOCK
    out = []
    W = len(levels[0]) * cw
    for i, row in enumerate(levels):
        runs = []  # (fill, text)
        for v in row:
            if v is None:
                key, ch = None, " "
            else:
                q = round((v ** gamma) * (steps - 1)) / (steps - 1)
                ch = ramp[max(1, min(4, round(0.6 + q * 3.6)))]
                c = tuple(round(a + (b - a) * q) for a, b in zip(lo, hi))
                key = "#%02x%02x%02x" % c
            if runs and runs[-1][0] == key:
                runs[-1][1] += ch
            else:
                runs.append([key, ch])
        spans = "".join(esc(t) if k is None else f'<tspan fill="{k}">{esc(t)}</tspan>' for k, t in runs)
        cls = f' class="{cls_for_row(i)}"' if cls_for_row else ""
        out.append(f'<text{cls} x="{x}" y="{y + i * lh:.1f}" textLength="{W:.1f}" lengthAdjust="spacing" '
                   f'font-size="{fs}" xml:space="preserve">{spans}</text>')
    return "\n".join(out)


def svg(w, h, body, title, frame=True):
    # recorta todo a la tarjeta para que los "tapadores" del tecleo no asomen por los bordes
    style, rest = body.split("</style>", 1)
    clip = (f'<clipPath id="card"><rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="11"/></clipPath>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>{style}</style>'
            f'<defs>{clip}</defs><g clip-path="url(#card)">{rest}</g>'
            + (f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="none" stroke="{BORDER}"/>'
               if frame else "") + "</svg>\n")


# ───────────────────────── A: terminal neofetch ─────────────────────────
FACE_COLS, FACE_FS, FACE_CW, FACE_LH = 76, 7, 4.2, 8.1


def face_levels_from_photo(photo):
    return face.load_levels(photo, FACE_COLS, row_factor=FACE_CW / FACE_LH, keep=0.86, detail=True)


def build_terminal(levels, st=None):
    """levels: rejilla de la cara (de la foto o de tools/face_levels.json). st: stats (opcional)."""
    fs, cw, lh = FACE_FS, FACE_CW, FACE_LH
    fx, fy = 30, 92
    W = 960
    T = 30.0 if st else 18.0
    A = Anim(T)
    END = T - 0.8
    b = []
    b.append(f'<defs><linearGradient id="fg" gradientUnits="userSpaceOnUse" x1="{fx}" y1="{fy}" '
             f'x2="{fx + 288}" y2="{fy + 330}"><stop offset="0" stop-color="{CYAN}"/>'
             f'<stop offset="1" stop-color="{VIOLET}"/></linearGradient>'
             f'<clipPath id="win"><rect x="11" y="11" width="{W - 22}" height="__H22__" rx="9"/></clipPath></defs>')
    b.append(f'<g clip-path="url(#win)"><rect x="10" y="10" width="{W - 20}" height="__H20__" fill="{BG}"/>')
    b.append(f'<rect x="10" y="10" width="{W - 20}" height="34" fill="{BAR}"/>')
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        b.append(f'<circle cx="{32 + i * 20}" cy="27" r="6" fill="{c}"/>')
    b.append(f'<text x="{W / 2}" y="32" text-anchor="middle" font-family="{MONO}" font-size="13" fill="{MUTED}">{HOST}: ~</text>')
    # logo de LinkedIn animado arriba a la derecha (toda la imagen es el enlace en el README)
    LI, ls = "#0A66C2", 22
    lx, ly = W - 10 - 16 - ls, 16
    b.append(f'<defs><clipPath id="lic"><rect x="{lx}" y="{ly}" width="{ls}" height="{ls}" rx="5"/></clipPath>'
             f'<linearGradient id="lish" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
             f'<stop offset="0.5" stop-color="#fff" stop-opacity="0.6"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
             f'</linearGradient></defs>')
    for extra in ("", " ring2"):
        b.append(f'<rect class="ring{extra}" x="{lx}" y="{ly}" width="{ls}" height="{ls}" rx="5" fill="none" stroke="{LI}" stroke-width="1.5"/>')
    b.append(f'<g class="logo"><rect x="{lx}" y="{ly}" width="{ls}" height="{ls}" rx="5" fill="{LI}"/>'
             f'<text x="{lx + ls / 2}" y="{ly + 16.5}" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" '
             f'font-size="15" font-weight="700" fill="#fff" letter-spacing="-0.5">in</text>'
             f'<g clip-path="url(#lic)"><rect class="shine" x="{lx}" y="{ly - 6}" width="14" height="{ls + 12}" '
             f'fill="url(#lish)" transform="skewX(-20)"/></g></g>')

    def prompt_line(x, y, cmd, t0, fs_=14):
        cwp = fs_ * 0.6
        pre = f"{HOST} ~> "
        s = (f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{fs_}" xml:space="preserve">'
             f'<tspan fill="{RED}">jesus</tspan><tspan fill="{MUTED}">@</tspan><tspan fill="{CYAN}">fib-upc</tspan>'
             f'<tspan fill="{MUTED}"> ~&gt; </tspan><tspan fill="{TXT}">{esc(cmd)}</tspan></text>')
        cx = x + len(pre) * cwp
        cwid = len(cmd) * cwp + 12
        dur = max(0.3, len(cmd) * 0.055)
        cover = A.type_cover(t0, dur, cwid, len(cmd), END)
        s += f'<rect class="{cover}" x="{cx}" y="{y - fs_}" width="{cwid}" height="{fs_ + 6}" fill="{BG}"/>'
        return s, t0 + dur

    s, t = prompt_line(30, 72, "neofetch --ascii face.txt", 0.4)
    b.append(f'<g class="{A.show(0.2, END)}">{s}</g>')

    t_face = t + 0.25
    b.append(f'<g font-family="{MONO}">')
    b.append(shaded_rows(levels, fx, fy, cw, lh, fs,
                         cls_for_row=lambda i: A.show(t_face + i * 0.04, END, 0.12)))
    b.append("</g>")

    # columna de información
    info = [
        ("title", HOST),
        ("rule", "─" * 15),
        ("kv", ("Name", NAME)),
        ("kv", ("Age", "21")),
        ("kv", ("Location", "Barcelona")),
        ("kv", ("Studies", "Computer Science @ FIB - UPC")),
        ("kv", ("Focus", "AI & Machine Learning")),
        ("kv", ("Goal", "Master algorithms for AI")),
        ("gap", None),
        ("kv", ("Languages", "C++ · Java · Python · C · Bash")),
        ("kv", ("ML / Data", "scikit-learn · NumPy · pandas · Gymnasium")),
        ("kv", ("Graphics", "OpenGL · GLSL")),
        ("kv", ("Tools", "Linux · Git · VS Code")),
    ]
    ix, iy, ilh, ifs = 390, 104, 23, 14
    icw = ifs * 0.6
    tt = t_face + 0.3
    b.append(f'<g font-family="{MONO}" font-size="{ifs}">')
    row = 0
    for kind, val in info:
        y = iy + row * ilh
        row += 1
        if kind == "gap":
            continue
        if kind == "title":
            txt = val
            el = (f'<text x="{ix}" y="{y}" font-weight="700"><tspan fill="{RED}">jesus</tspan>'
                  f'<tspan fill="{MUTED}">@</tspan><tspan fill="{CYAN}">fib-upc</tspan></text>')
        elif kind == "rule":
            txt = val
            el = f'<text x="{ix}" y="{y}" fill="{BORDER}">{val}</text>'
        else:
            k, v = val
            txt = f"{k}: {v}"
            el = (f'<text x="{ix}" y="{y}" xml:space="preserve"><tspan fill="{CYAN}" font-weight="700">{esc(k)}</tspan>'
                  f'<tspan fill="{MUTED}">: </tspan><tspan fill="{TXT}">{esc(v)}</tspan></text>')
        dur = max(0.15, len(txt) * 0.016)
        wid = len(txt) * icw + 14
        cover = A.type_cover(tt, dur, wid, max(4, len(txt) // 2), END)
        b.append(el + f'<rect class="{cover}" x="{ix - 2}" y="{y - ifs}" width="{wid}" height="{ifs + 7}" fill="{BG}"/>')
        tt += dur + 0.08
    b.append("</g>")

    # paleta estilo neofetch
    py = iy + row * ilh - 2
    pal = ["#21262d", RED, GREEN, YELLOW, "#58a6ff", VIOLET, CYAN, TXT]
    cls = A.show(tt + 0.1, END)
    b.append(f'<g class="{cls}">' + "".join(
        f'<rect x="{ix + i * 26}" y="{py}" width="24" height="14" rx="2" fill="{c}"/>' for i, c in enumerate(pal)) + "</g>")

    # (opcional) segundo comando: gh stats, dentro de la misma ventana
    t_last = tt + 0.5
    if st:
        import stats as stats_mod
        C = dict(MONO=MONO, BG=BG, TXT=TXT, MUTED=MUTED, RED=RED, CYAN=CYAN, VIOLET=VIOLET,
                 YELLOW=YELLOW, GREEN=GREEN, esc=esc)
        y0 = round(max(fy + len(levels) * lh, py + 14) + 40)
        yb, t_last = stats_mod.render(A, b, st, y0, t_last, END, W, C)
        px, fy2 = 30, yb + 6
    else:
        px, fy2 = ix, py + 44
    # prompt final con cursor parpadeante
    b.append(f'<g class="{A.show(t_last, END)}"><text x="{px}" y="{fy2}" font-family="{MONO}" font-size="{ifs}" xml:space="preserve">'
             f'<tspan fill="{RED}">jesus</tspan><tspan fill="{MUTED}">@</tspan><tspan fill="{CYAN}">fib-upc</tspan>'
             f'<tspan fill="{MUTED}"> ~&gt; </tspan></text>'
             f'<rect class="blink" x="{px + len(HOST + " ~> ") * icw}" y="{fy2 - ifs + 1}" width="{icw}" height="{ifs + 2}" fill="{TXT}"/></g>')
    b.append("</g>")
    H = max(470, round(fy + len(levels) * lh + 24), round(fy2 + 30))
    b.append(f'<rect x="10.5" y="10.5" width="{W - 21}" height="{H - 21}" rx="10" fill="none" stroke="{BORDER}"/>')
    css = ("@keyframes bl{0%,49%{opacity:1}50%,100%{opacity:0}}.blink{animation:bl 1s steps(1,end) infinite}"
           "@keyframes pulse{0%{transform:scale(1);opacity:.8}100%{transform:scale(1.7);opacity:0}}"
           ".ring{transform-box:fill-box;transform-origin:center;animation:pulse 2s ease-out infinite}"
           ".ring2{animation-delay:1s}"
           "@keyframes shine{0%,55%{transform:translateX(-40px)}85%,100%{transform:translateX(40px)}}"
           ".shine{animation:shine 3.2s ease-in-out infinite}"
           "@keyframes pop{0%,100%{transform:scale(1)}50%{transform:scale(1.08)}}"
           ".logo{transform-box:fill-box;transform-origin:center;animation:pop 2s ease-in-out infinite}"
           ".grow{transform-box:fill-box;transform-origin:left center}")
    body = "".join(b).replace("__H22__", str(H - 22)).replace("__H20__", str(H - 20))
    return svg(W, H, A.style(css) + body, f"{NAME} — terminal", frame=False)


# ───────────────────────── B: escaneo ─────────────────────────
def build_scan(photo):
    lines = face.to_chars(face.load_levels(photo, 60), face.RAMP_ASCII, invert=False)
    rows, cols = len(lines), len(lines[0])
    W, H, T = 500, 540, 14.0
    END = 13.2
    A = Anim(T)
    fs, cw, lh = 9, 5.4, 10
    fx, fy = (W - cols * cw) / 2, 78
    rnd = random.Random(7)
    charset = "01<>{}[]/\\*+=#$%&ABCDEF"
    b = []
    b.append(f'<defs><linearGradient id="sg" gradientUnits="userSpaceOnUse" x1="0" y1="{fy}" x2="0" y2="{fy + rows * lh}">'
             f'<stop offset="0" stop-color="#e6edf3"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>'
             f'<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CYAN}" stop-opacity="0"/>'
             f'<stop offset="0.85" stop-color="{CYAN}" stop-opacity="0.18"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0.9"/></linearGradient></defs>')
    b.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>')
    # cabecera HUD
    b.append(f'<text x="24" y="34" font-family="{MONO}" font-size="12" fill="{MUTED}">// IDENTITY SCAN</text>')
    t0, dt = 0.9, 0.1
    t_done = t0 + rows * dt
    b.append(f'<g class="{A.hide(t_done, END)}"><text class="blink" x="{W - 24}" y="34" text-anchor="end" font-family="{MONO}" '
             f'font-size="12" fill="{YELLOW}">● SCANNING</text></g>')
    b.append(f'<g class="{A.show(t_done, END)}"><text x="{W - 24}" y="34" text-anchor="end" font-family="{MONO}" '
             f'font-size="12" fill="{GREEN}">● VERIFIED</text></g>')
    # esquinas
    x0, y0, x1, y1 = fx - 18, fy - 22, fx + cols * cw + 18, fy + rows * lh + 4
    L = 22
    br = (f"M{x0},{y0 + L}V{y0}H{x0 + L} M{x1 - L},{y0}H{x1}V{y0 + L} "
          f"M{x1},{y1 - L}V{y1}H{x1 - L} M{x0 + L},{y1}H{x0}V{y1 - L}")
    b.append(f'<path d="{br}" fill="none" stroke="{CYAN}" stroke-width="2"/>')
    b.append(f'<path class="{A.show(t_done, t_done + 0.25, 0.02)}" d="{br}" fill="none" stroke="{GREEN}" stroke-width="3"/>')

    # ruido (3 capas que parpadean) + cara que se revela por filas
    b.append(f'<g font-family="{MONO}">')
    for layer in range(3):
        b.append(f'<g class="fl" style="animation-delay:-{layer * 0.15:.2f}s">')
        for i in range(rows):
            noise = "".join(rnd.choice(charset) if rnd.random() < 0.55 else " " for _ in range(cols))
            b.append(face_rows([noise], fx, fy + i * lh, cw, lh, fs, GREEN,
                               cls_for_row=lambda _i, i=i: A.hide(t0 + i * dt, END)))
        b.append("</g>")
    b.append(face_rows(lines, fx, fy, cw, lh, fs, "url(#sg)", cls_for_row=lambda i: A.show(t0 + i * dt, END, 0.05)))
    b.append("</g>")

    # haz de escaneo
    bh = 46
    mv = A.slide([(t0, t_done, 0, rows * lh, rows)])
    # slide() genera translateX; para el haz necesitamos translateY
    A.css[-2] = A.css[-2].replace("translateX", "translateY")
    b.append(f'<g class="{A.show(t0 - 0.05, t_done + 0.05, 0.02)}"><rect class="{mv}" x="{x0}" y="{fy - bh - 2}" '
             f'width="{x1 - x0}" height="{bh}" fill="url(#beam)"/></g>')

    # textos finales
    ty = y1 + 46
    msg1 = "> ACCESS GRANTED"
    msg2 = f"> {NAME} · AI & ML @ FIB-UPC"
    for txt, y, col, t_s, size, weight in [(msg1, ty, GREEN, t_done + 0.4, 18, 700),
                                           (msg2, ty + 30, TXT, t_done + 1.4, 14, 400)]:
        ccw = size * 0.6
        wid = len(txt) * ccw + 20
        tx = (W - len(txt) * ccw) / 2
        dur = len(txt) * 0.045
        b.append(f'<text x="{tx:.1f}" y="{y}" font-family="{MONO}" font-size="{size}" font-weight="{weight}" '
                 f'fill="{col}" xml:space="preserve">{esc(txt)}</text>')
        b.append(f'<rect class="{A.type_cover(t_s, dur, wid, len(txt), END)}" x="{tx - 4:.1f}" y="{y - size}" '
                 f'width="{wid:.1f}" height="{size + 8}" fill="{BG}"/>')
    css = ("@keyframes bl{0%,49%{opacity:1}50%,100%{opacity:0}}.blink{animation:bl 1s steps(1,end) infinite}"
           "@keyframes fl{0%{opacity:.45}33.3%{opacity:0}100%{opacity:0}}"
           ".fl{animation:fl .45s steps(1,end) infinite}")
    return svg(W, H, A.style(css) + "".join(b), f"{NAME} — identity scan")


# ───────────────────────── C: minimal ─────────────────────────
def build_minimal(photo):
    lines = face.to_chars(face.load_levels(photo, 44, row_factor=0.52), face.RAMP_BLOCK, invert=True)
    rows, cols = len(lines), len(lines[0])
    W, H = 900, 320
    fs, cw, lh = 9, 5.4, 10.4
    fx, fy = 40, (H - rows * lh) / 2 + 9
    roles = ["AI & Machine Learning", "Algorithms enthusiast", "CS student @ FIB-UPC", "Collector of segfaults"]
    sizes = 22
    ccw = sizes * 0.6
    sched, t = [], 0.4
    for r in roles:
        td, hold, te = len(r) * 0.06, 1.8, len(r) * 0.025
        sched.append((t, td, hold, te))
        t += td + hold + te + 0.35
    T = round(t + 0.2, 2)
    A = Anim(T)
    b = []
    fw = cols * cw
    b.append(f'<defs><linearGradient id="sh" gradientUnits="userSpaceOnUse" x1="{fx - fw}" y1="0" x2="{fx}" y2="0">'
             f'<stop offset="0" stop-color="#8b949e"/><stop offset="0.42" stop-color="#8b949e"/>'
             f'<stop offset="0.5" stop-color="#ffffff"/><stop offset="0.58" stop-color="#8b949e"/>'
             f'<stop offset="1" stop-color="#8b949e"/>'
             f'<animateTransform attributeName="gradientTransform" type="translate" values="0 0;{fw * 2.2:.0f} 0;{fw * 2.2:.0f} 0" '
             f'keyTimes="0;0.45;1" dur="5s" repeatCount="indefinite"/></linearGradient>'
             f'<linearGradient id="acc" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{RED}"/>'
             f'<stop offset="1" stop-color="{VIOLET}"/></linearGradient></defs>')
    b.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="{BG}" stroke="{BORDER}"/>')
    b.append(f'<g font-family="{MONO}">' + face_rows(lines, fx, fy, cw, lh, fs, "url(#sh)") + "</g>")
    rx = fx + fw + 50
    b.append(f'<line x1="{rx - 25}" y1="50" x2="{rx - 25}" y2="{H - 50}" stroke="{BORDER}"/>')
    b.append(f'<text x="{rx}" y="88" font-family="{MONO}" font-size="14" fill="{MUTED}">Hi there, I\'m</text>')
    b.append(f'<text x="{rx}" y="134" font-family="{SANS}" font-size="40" font-weight="700" fill="#e6edf3">{NAME}</text>')
    b.append(f'<rect x="{rx}" y="148" width="64" height="3" rx="1.5" fill="url(#acc)"/>')
    # roles rotativos
    ry = 192
    tx = rx + 2 * ccw
    b.append(f'<text x="{rx}" y="{ry}" font-family="{MONO}" font-size="{sizes}" fill="{RED}">&gt;</text>')
    cur = []
    for r, (ts, td, hold, te) in zip(roles, sched):
        wid = len(r) * ccw + 6
        n = len(r)
        segs = [(ts, ts + td, 0, wid - 6, n), (ts + td + hold, ts + td + hold + te, wid - 6, 0, n)]
        cur.extend(segs)
        grp = A.show(ts - 0.02, ts + td + hold + te, 0.01)
        cov = A.slide(segs)
        b.append(f'<g class="{grp}"><text x="{tx}" y="{ry}" font-family="{MONO}" font-size="{sizes}" fill="#e6edf3" '
                 f'xml:space="preserve">{esc(r)}</text><rect class="{cov}" x="{tx}" y="{ry - sizes}" width="{wid}" '
                 f'height="{sizes + 8}" fill="{BG}"/></g>')
    b.append(f'<g class="{A.slide(cur)}"><rect class="blink" x="{tx + 1}" y="{ry - sizes + 3}" width="2.5" '
             f'height="{sizes + 2}" fill="{RED}"/></g>')
    # chips
    chips = ["Barcelona", "FIB · UPC", "AI / ML", "C++ · Python"]
    cx = rx
    for c in chips:
        w = len(c) * 7.2 + 24
        b.append(f'<rect x="{cx}" y="{H - 92}" width="{w}" height="28" rx="14" fill="{BAR}" stroke="{BORDER}"/>'
                 f'<text x="{cx + w / 2}" y="{H - 73}" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{TXT}">{esc(c)}</text>')
        cx += w + 10
    css = "@keyframes bl{0%,49%{opacity:1}50%,100%{opacity:0}}.blink{animation:bl 1s steps(1,end) infinite}"
    return svg(W, H, A.style(css) + "".join(b), f"{NAME} — profile")


# ───────────────────────── botón LinkedIn animado ─────────────────────────
def build_linkedin():
    W, H = 300, 76
    LI = "#0A66C2"
    lx, ly, ls = 16, 16, 44
    css = (
        "@keyframes pulse{0%{transform:scale(1);opacity:.7}100%{transform:scale(1.55);opacity:0}}"
        ".ring{transform-box:fill-box;transform-origin:center;animation:pulse 2s ease-out infinite}"
        ".ring2{animation-delay:1s}"
        "@keyframes shine{0%,55%{transform:translateX(-70px)}85%,100%{transform:translateX(70px)}}"
        ".shine{animation:shine 3.2s ease-in-out infinite}"
        "@keyframes bob{0%,100%{transform:translateX(0)}50%{transform:translateX(5px)}}"
        ".arrow{animation:bob 1.2s ease-in-out infinite}"
        "@keyframes glow{0%,100%{stroke-opacity:.35}50%{stroke-opacity:1}}"
        ".edge{animation:glow 2.4s ease-in-out infinite}"
        "@keyframes pop{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}"
        ".logo{transform-box:fill-box;transform-origin:center;animation:pop 2s ease-in-out infinite}")
    b = [f'<defs><clipPath id="lc"><rect x="{lx}" y="{ly}" width="{ls}" height="{ls}" rx="9"/></clipPath>'
         f'<linearGradient id="sh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
         f'<stop offset="0.5" stop-color="#fff" stop-opacity="0.55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
         f'</linearGradient></defs>',
         f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="{BG}"/>',
         f'<rect class="edge" x="1" y="1" width="{W - 2}" height="{H - 2}" rx="13.5" fill="none" stroke="{LI}" stroke-width="1.5"/>']
    for extra in ("", " ring2"):
        b.append(f'<rect class="ring{extra}" x="{lx}" y="{ly}" width="{ls}" height="{ls}" rx="9" fill="none" stroke="{LI}" stroke-width="2"/>')
    b.append(f'<g class="logo"><rect x="{lx}" y="{ly}" width="{ls}" height="{ls}" rx="9" fill="{LI}"/>'
             f'<text x="{lx + ls / 2}" y="{ly + 33}" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" '
             f'font-size="29" font-weight="700" fill="#fff" letter-spacing="-1">in</text>'
             f'<g clip-path="url(#lc)"><rect class="shine" x="{lx}" y="{ly - 10}" width="28" height="{ls + 20}" '
             f'fill="url(#sh)" transform="skewX(-20)"/></g></g>')
    b.append(f'<text x="78" y="35" font-family="{SANS}" font-size="17" font-weight="700" fill="#e6edf3">Let&#8217;s connect</text>')
    b.append(f'<text x="78" y="56" font-family="{MONO}" font-size="12" fill="{MUTED}">{NAME} · LinkedIn</text>')
    b.append(f'<g class="arrow"><path d="M266 38h14m-6-6 6 6-6 6" fill="none" stroke="{LI}" stroke-width="2.4" '
             f'stroke-linecap="round" stroke-linejoin="round"/></g>')
    return svg(W, H, f"<style>{css}</style>" + "".join(b), f"{NAME} on LinkedIn", frame=False)


FACE_JSON = os.path.join(os.path.dirname(__file__), "face_levels.json")

if __name__ == "__main__":
    # Con foto: genera la cara y la guarda como texto (face_levels.json), sin guardar la foto.
    # Sin foto (p. ej. en la Action): reutiliza face_levels.json.
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    os.makedirs(OUT, exist_ok=True)
    if args:
        levels = face_levels_from_photo(args[0])
        with open(FACE_JSON, "w", encoding="utf-8") as f:
            json.dump([[None if v is None else round(v, 3) for v in row] for row in levels], f, separators=(",", ":"))
    else:
        with open(FACE_JSON, encoding="utf-8") as f:
            levels = json.load(f)
    st = None
    if "--no-stats" not in sys.argv:
        import stats as stats_mod
        st = stats_mod.collect()
    data = build_terminal(levels, st)
    with open(os.path.join(OUT, "terminal.svg"), "w", encoding="utf-8") as f:
        f.write(data)
    print("terminal.svg", f"{len(data.encode()) / 1024:.0f} KB", "with stats" if st else "")
    if "--all" in sys.argv and args:  # versiones B y C descartadas
        for fn, build in [("scan.svg", build_scan), ("minimal.svg", build_minimal)]:
            with open(os.path.join(OUT, fn), "w", encoding="utf-8") as f:
                f.write(build(args[0]))
