"""Stats de GitHub dibujadas dentro de la terminal del README.

Solo lee datos públicos (API REST de GitHub + calendario público de contribuciones).
En la Action usa GITHUB_TOKEN para no toparse con el límite de la API.
"""
import collections
import datetime as dt
import json
import os
import re
import urllib.request

USER = "Jesus-Penaranda"
TOKEN = os.environ.get("GITHUB_TOKEN")


def get(url, api=True):
    h = {"User-Agent": "profile-stats"}
    if api and TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30).read().decode("utf-8", "ignore")


def collect(user=USER):
    u = json.loads(get(f"https://api.github.com/users/{user}"))
    repos = [r for r in json.loads(get(f"https://api.github.com/users/{user}/repos?per_page=100"))
             if not r["fork"] and r["name"] != user]
    # cada repo pesa lo mismo (los .ipynb inflan los bytes) y los notebooks cuentan como Python
    langs = collections.Counter()
    for r in repos:
        rl = collections.Counter()
        for k, v in json.loads(get(r["languages_url"])).items():
            rl["Python" if k == "Jupyter Notebook" else k] += v
        tot = sum(rl.values())
        for k, v in rl.items():
            langs[k] += v / tot if tot else 0
    html = get(f"https://github.com/users/{user}/contributions", api=False)
    total = int(re.search(r"([\d,]+)\s+contributions?\s+in the last year", html).group(1).replace(",", ""))
    days = {m.group(1): int(m.group(2)) for m in
            re.finditer(r'data-date="([\d-]+)" id="contribution-day-component-\d+-\d+" data-level="(\d)"', html)}
    dates = sorted(days)
    longest = run = 0
    for d in dates:
        run = run + 1 if days[d] else 0
        longest = max(longest, run)
    cur = 0
    for d in reversed(dates):
        if days[d]:
            cur += 1
        elif cur or d != dates[-1]:  # hoy sin contribuir todavía no rompe la racha
            break
    return dict(repos=len(repos), followers=u["followers"], stars=sum(r["stargazers_count"] for r in repos),
                total=total, longest=longest, current=cur, langs=langs.most_common(6),
                langsum=sum(langs.values()), days=days, dates=dates)


def plural(n, w):
    return f"{n} {w}" + ("" if n == 1 else "s")


STATS_HEIGHT = 380  # alto aproximado del bloque, para dimensionar la ventana


def render(A, b, d, y0, t, END, W, C):
    """Dibuja `gh stats` a partir de y0 / tiempo t. Devuelve (y_final, t_final).
    C: dict con colores/fuentes/helpers de gen.py."""
    MONO, BG, TXT, MUTED, RED, CYAN = C["MONO"], C["BG"], C["TXT"], C["MUTED"], C["RED"], C["CYAN"]
    esc = C["esc"]
    ifs, icw, ilh = 14, 8.4, 23

    def typed(x, y, inner, plain, t0, speed=0.016, n=None):
        dur = max(0.15, len(plain) * speed)
        wid = len(plain) * icw + 14
        cov = A.type_cover(t0, dur, wid, n or max(4, len(plain) // 2), END)
        b.append(f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{ifs}" xml:space="preserve">{inner}</text>'
                 f'<rect class="{cov}" x="{x - 2}" y="{y - ifs}" width="{wid}" height="{ifs + 7}" fill="{BG}"/>')
        return t0 + dur

    # prompt + comando
    cmd = "gh stats"
    b.append(f'<g class="{A.show(t, END)}"><text x="30" y="{y0}" font-family="{MONO}" font-size="{ifs}" xml:space="preserve">'
             f'<tspan fill="{RED}">jesus</tspan><tspan fill="{MUTED}">@</tspan><tspan fill="{CYAN}">fib-upc</tspan>'
             f'<tspan fill="{MUTED}"> ~&gt; </tspan></text></g>')
    t = typed(30 + len("jesus@fib-upc ~> ") * icw, y0, f'<tspan fill="{TXT}">{cmd}</tspan>', cmd, t + 0.2, 0.06, len(cmd)) + 0.3

    # números
    kv = [("Contributions", f'{d["total"]} (last year)'), ("Current streak", plural(d["current"], "day")),
          ("Longest streak", plural(d["longest"], "day")), ("Public repos", str(d["repos"])),
          ("Stars", str(d["stars"])), ("Followers", str(d["followers"]))]
    ly = y0 + 40
    for i, (k, v) in enumerate(kv):
        inner = (f'<tspan fill="{CYAN}" font-weight="700">{esc(k)}</tspan><tspan fill="{MUTED}">: </tspan>'
                 f'<tspan fill="{TXT}">{esc(v)}</tspan>')
        t = typed(30, ly + i * ilh, inner, f"{k}: {v}", t) + 0.06

    # lenguajes con barras
    rx = 390
    b.append(f'<g class="{A.show(t, END)}"><text x="{rx}" y="{ly}" font-family="{MONO}" font-size="{ifs}" '
             f'font-weight="700" fill="{RED}">Top languages</text></g>')
    pal = [CYAN, C["VIOLET"], RED, C["YELLOW"], C["GREEN"], "#58a6ff"]
    bar_x, bar_w = rx + 130, 300
    for i, (lang, v) in enumerate(d["langs"][:5]):
        y = ly + 23 + i * ilh
        pct = v / d["langsum"] * 100
        t0 = t + 0.15 + i * 0.12
        grow = A._add([("0%", "transform:scaleX(0)"), (A.p(t0), "transform:scaleX(0)"),
                       (A.p(t0 + 0.7), "transform:scaleX(1)"), (A.p(END), "transform:scaleX(1)"),
                       (A.p(END + 0.3), "transform:scaleX(0)"), ("100%", "transform:scaleX(0)")])
        b.append(f'<g class="{A.show(t0, END)}"><text x="{rx}" y="{y}" font-family="{MONO}" font-size="13" fill="{TXT}">{esc(lang)}</text>'
                 f'<rect x="{bar_x}" y="{y - 10}" width="{bar_w}" height="10" rx="2" fill="#21262d"/>'
                 f'<text x="{bar_x + bar_w + 10}" y="{y}" font-family="{MONO}" font-size="12" fill="{MUTED}">{pct:.1f}%</text></g>'
                 f'<rect class="{grow} grow" x="{bar_x}" y="{y - 10}" width="{max(3, bar_w * pct / 100):.1f}" height="10" rx="2" fill="{pal[i]}"/>')
    t += 1.1

    # calendario de contribuciones (domingo arriba, como GitHub)
    first = dt.date.fromisoformat(d["dates"][0])
    weeks = (dt.date.fromisoformat(d["dates"][-1]) - first).days // 7 + 1
    cs, cg = 11, 3
    cal_w = weeks * (cs + cg)
    cal_x = (W - cal_w) / 2
    cal_y = ly + 6 * ilh + 30
    b.append(f'<g class="{A.show(t, END)}"><text x="{cal_x}" y="{cal_y - 12}" font-family="{MONO}" font-size="12" '
             f'fill="{MUTED}">contributions · last 12 months</text></g>')
    shades = ["#161b22", "#3b1c22", "#7a2a33", "#c23a45", RED]
    # una clase por semana (no por día) para que el SVG pese poco
    week_cls = [A.show(t + w * 0.025, END, 0.1) for w in range(weeks)]
    for date, lvl in d["days"].items():
        day = dt.date.fromisoformat(date)
        wk = (day - first).days // 7
        row = (day.weekday() + 1) % 7
        b.append(f'<rect class="{week_cls[wk]}" x="{cal_x + wk * (cs + cg):.0f}" y="{cal_y + row * (cs + cg)}" '
                 f'width="{cs}" height="{cs}" rx="2" fill="{shades[lvl]}"/>')
    t += weeks * 0.025
    lg_y = cal_y + 7 * (cs + cg) + 8
    b.append(f'<g class="{A.show(t, END)}"><text x="{cal_x + cal_w - 150}" y="{lg_y + 9}" font-family="{MONO}" '
             f'font-size="11" fill="{MUTED}">less</text>' + "".join(
                 f'<rect x="{cal_x + cal_w - 116 + i * 15}" y="{lg_y}" width="{cs}" height="{cs}" rx="2" fill="{c}"/>'
                 for i, c in enumerate(shades)) +
             f'<text x="{cal_x + cal_w - 36}" y="{lg_y + 9}" font-family="{MONO}" font-size="11" fill="{MUTED}">more</text>'
             f'<text x="{cal_x}" y="{lg_y + 9}" font-family="{MONO}" font-size="11" fill="{MUTED}">'
             f'updated {dt.date.today().isoformat()}</text></g>')
    return lg_y + 30, t + 0.3
