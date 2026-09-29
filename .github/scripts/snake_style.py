#!/usr/bin/env python3
"""Redesenha a cobra gerada pelo Platane/snk.

O snk desenha a cobra como 4 quadradinhos roxos. Este script mantém a
animação do grid (as contribuições sendo "comidas") e troca a cobra por
uma com cabeça, olhos, língua, corpo longo com escamas e cauda afinando.
A cabeça gira para acompanhar a direção do movimento.

Uso:
    python snake_style.py arquivo.svg [--theme light|dark] [--out saida.svg]
"""
import argparse
import math
import re
import sys

THEMES = {
    "light": {
        "body1": "#2da44e",
        "body2": "#4ac26b",
        "outline": "#116329",
        "spot": "#f2cc60",
        "head": "#218c43",
        "eye": "#ffffff",
        "pupil": "#0d1117",
        "tongue": "#e5484d",
    },
    "dark": {
        "body1": "#3fb950",
        "body2": "#56d364",
        "outline": "#0f5323",
        "spot": "#f2cc60",
        "head": "#2ea043",
        "eye": "#ffffff",
        "pupil": "#0d1117",
        "tongue": "#ff6b6b",
    },
}

N_BODY = 26          # segmentos do corpo (sem contar a cabeça)
SPACING_PX = 3.0     # distância entre segmentos, em px (1 célula = 16px)
HEAD_R = 5.6         # raio do corpo logo atrás da cabeça
TAIL_R = 1.9         # raio da ponta da cauda
OUTLINE = 1.1        # espessura do contorno
TURN_FRACTION = 0.5  # quanto de uma célula a cabeça leva para virar

KF_RE = r"@keyframes s0\{(.*?)\}\}"
STEP_RE = re.compile(r"([\d.,%]+)\{transform:translate\(([-\d.]+)px,([-\d.]+)px\)\}")


def parse_head(svg):
    m = re.search(KF_RE, svg)
    if not m:
        sys.exit("keyframes da cobra (s0) não encontrados no SVG")
    body = m.group(1) + "}"
    points = {}
    for sel, x, y in STEP_RE.findall(body):
        for t in sel.split(","):
            points[float(t.rstrip("%"))] = (float(x), float(y))
    base = re.search(r"\.s\.s0\{transform:translate\(([-\d.]+)px,([-\d.]+)px\)", svg)
    if 100.0 not in points:
        points[100.0] = (float(base.group(1)), float(base.group(2))) if base else points[0.0]
    if 0.0 not in points:
        points[0.0] = points[100.0]
    return sorted((t, xy[0], xy[1]) for t, xy in points.items())


def duration_ms(svg):
    m = re.search(r"\.s\{[^}]*?(\d+)ms", svg)
    return int(m.group(1)) if m else 20000


def make_path(pts):
    times = [p[0] for p in pts]

    def pos(t):
        t %= 100.0
        for i in range(len(pts) - 1):
            t0, x0, y0 = pts[i]
            t1, x1, y1 = pts[i + 1]
            if t0 <= t <= t1:
                if t1 == t0:
                    return x0, y0
                k = (t - t0) / (t1 - t0)
                return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        return pts[-1][1], pts[-1][2]

    return times, pos


def speed(pts):
    """px por % de tempo; a cobra do snk anda em velocidade constante."""
    vals = []
    for (t0, x0, y0), (t1, x1, y1) in zip(pts, pts[1:]):
        d = math.hypot(x1 - x0, y1 - y0)
        if t1 > t0 and d > 0:
            vals.append(d / (t1 - t0))
    vals.sort()
    return vals[len(vals) // 2]


def fmt(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def body_keyframes(name, times, pos, delay):
    stops = {0.0, 100.0}
    for t in times:
        stops.add(round((t + delay) % 100.0, 4))
    frames = []
    for t in sorted(stops):
        x, y = pos(t - delay)
        frames.append(f"{fmt(t)}%{{transform:translate({fmt(x)}px,{fmt(y)}px)}}")
    return f"@keyframes {name}{{{''.join(frames)}}}"


def head_keyframes(name, pts, pos, turn):
    # direção de cada trecho do caminho
    segs = []
    for (t0, x0, y0), (t1, x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        ang = math.degrees(math.atan2(dy, dx)) if (dx or dy) else None
        segs.append((t0, t1, ang))
    # preenche trechos parados com o ângulo anterior e "desembrulha"
    first = next(a for _, _, a in segs if a is not None)
    prev = first
    angles = []
    for _, _, a in segs:
        if a is None:
            a = prev
        while a - prev > 180:
            a -= 360
        while a - prev < -180:
            a += 360
        angles.append(a)
        prev = a

    frames = []

    def add(t, a):
        x, y = pos(t)
        frames.append((t, f"transform:translate({fmt(x)}px,{fmt(y)}px) rotate({fmt(a)}deg)"))

    for i, (t0, t1, _) in enumerate(segs):
        a = angles[i]
        add(t0, a)
        nxt = angles[i + 1] if i + 1 < len(segs) else None
        if nxt is not None and nxt != a and t1 - t0 > turn * 1.2:
            add(t1 - turn, a)
    # fecha o loop no mesmo ângulo (mod 360) do início
    end = angles[-1]
    loop = first
    while loop - end > 180:
        loop -= 360
    while loop - end < -180:
        loop += 360
    add(100.0, loop)

    frames.sort(key=lambda f: f[0])
    body = "".join(f"{fmt(t)}%{{{css}}}" for t, css in frames)
    return f"@keyframes {name}{{{body}}}"


def build(svg, theme):
    c = THEMES[theme]
    pts = parse_head(svg)
    times, pos = make_path(pts)
    v = speed(pts)
    step = SPACING_PX / v              # atraso (em %) entre segmentos
    turn = 16.0 * TURN_FRACTION / v    # tempo da virada da cabeça
    dur = duration_ms(svg)

    css = [
        f":root{{--sb1:{c['body1']};--sb2:{c['body2']};--so:{c['outline']};--ss:{c['spot']};"
        f"--sh:{c['head']};--se:{c['eye']};--sp:{c['pupil']};--st:{c['tongue']}}}",
        f".sn{{animation:none linear {dur}ms infinite;shape-rendering:geometricPrecision}}",
        ".bo{fill:var(--so)}.b1{fill:var(--sb1)}",
        ".sd{fill:var(--sh)}.sp{fill:var(--ss)}",
        ".snh{transform-origin:8px 8px}",
        ".snh .hd{fill:var(--sh);stroke:var(--so);stroke-width:1.1}",
        ".snh .ey{fill:var(--se)}.snh .pu{fill:var(--sp)}",
        ".snh .no{fill:var(--so)}.snh .hs{fill:var(--sb1);opacity:.55}",
        ".tg{fill:none;stroke:var(--st);stroke-width:1.2;stroke-linecap:round;stroke-linejoin:round;"
        "transform-origin:15px 8px;animation:tg 1.4s ease-in-out infinite}",
        "@keyframes tg{0%,55%,100%{transform:scaleX(0)}65%,85%{transform:scaleX(1)}}",
        head_keyframes("snh", pts, pos, turn),
        f".snh{{animation-name:snh;transform:translate({fmt(pts[0][1])}px,{fmt(pts[0][2])}px)}}",
    ]

    outline, fill, marks = [], [], []
    for i in range(N_BODY, 0, -1):  # cauda primeiro, cabeça por cima
        k = (i - 1) / (N_BODY - 1)
        r = HEAD_R + (TAIL_R - HEAD_R) * (k ** 1.15)
        name = f"sb{i}"
        css.append(body_keyframes(name, times, pos, step * i))
        x0, y0 = pos(-step * i)
        css.append(f".{name}{{animation-name:{name};transform:translate({fmt(x0)}px,{fmt(y0)}px)}}")
        outline.append(f'<circle class="sn {name} bo" cx="8" cy="8" r="{fmt(r + OUTLINE)}"/>')
        fill.append(f'<circle class="sn {name} b1" cx="8" cy="8" r="{fmt(r)}"/>')
        if i % 4 == 2 and i < N_BODY - 2:  # manchas no dorso
            marks.append(f'<circle class="sn {name} sd" cx="8" cy="8" r="{fmt(r * 0.62)}"/>')
            marks.append(f'<circle class="sn {name} sp" cx="8" cy="8" r="{fmt(r * 0.28)}"/>')

    # cabeça desenhada olhando para a direita (+x); a rotação cuida do resto
    head = (
        '<g class="sn snh">'
        '<path class="tg" d="M16.8 8H21M21 8L23.2 6.3M21 8L23.2 9.7"/>'
        '<path class="hd" d="M-0.5 8C-0.5 2.2 4.6 -0.6 9.4 0.6C13.6 1.7 17.4 4.8 17.4 8'
        'C17.4 11.2 13.6 14.3 9.4 15.4C4.6 16.6 -0.5 13.8 -0.5 8Z"/>'
        '<path class="hs" d="M3 8C3 5.6 5.4 4.4 7.6 5.2L9.4 8L7.6 10.8C5.4 11.6 3 10.4 3 8Z"/>'
        '<circle class="ey" cx="10.2" cy="3.9" r="2.2"/>'
        '<circle class="ey" cx="10.2" cy="12.1" r="2.2"/>'
        '<ellipse class="pu" cx="10.6" cy="3.9" rx="0.65" ry="1.55"/>'
        '<ellipse class="pu" cx="10.6" cy="12.1" rx="0.65" ry="1.55"/>'
        '<circle class="no" cx="16" cy="6.8" r="0.45"/>'
        '<circle class="no" cx="16" cy="9.2" r="0.45"/>'
        "</g>"
    )
    shapes = outline + fill + marks + [head]

    # remove a cobra original do snk
    svg = re.sub(r'<rect class="s s\d+"[^>]*/>', "", svg)
    style = "<style>" + "".join(css) + "</style>"
    return svg.replace("</svg>", style + "".join(shapes) + "</svg>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("svg")
    ap.add_argument("--theme", choices=THEMES, default="light")
    ap.add_argument("--out")
    a = ap.parse_args()
    with open(a.svg, encoding="utf-8") as f:
        src = f.read()
    out = build(src, a.theme)
    with open(a.out or a.svg, "w", encoding="utf-8") as f:
        f.write(out)


if __name__ == "__main__":
    main()
