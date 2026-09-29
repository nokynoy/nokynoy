#!/usr/bin/env python3
"""Gera o cartão de estatísticas do perfil usando só dados públicos da API do GitHub.

Substitui o cartão "stats" do github-readme-stats, que precisa de um token
pessoal para funcionar dentro do GitHub Actions.

Uso:
    GITHUB_TOKEN=... python stats_card.py nokynoy dist/stats.svg
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from html import escape

API = "https://api.github.com"

# tema tokyonight (mesmo do cartão de linguagens)
BG = "#1a1b27"
TITLE = "#70a5fd"
TEXT = "#38bdae"
ICON = "#bf91f3"
MUTED = "#a9b1d6"


def get(path):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-stats-card",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def safe(fn, default=None):
    try:
        return fn()
    except Exception as e:  # um número faltando não deve derrubar o cartão
        print(f"aviso: {e}", file=sys.stderr)
        return default


def search_count(kind, query):
    q = urllib.parse.quote(query, safe=":+")
    return get(f"/search/{kind}?q={q}&per_page=1")["total_count"]


def collect(user):
    info = get(f"/users/{user}")
    repos, page = [], 1
    while True:
        batch = get(f"/users/{user}/repos?per_page=100&type=owner&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    own = [r for r in repos if not r.get("fork")]
    return {
        "name": (info.get("name") or user).split()[0],
        "stars": sum(r.get("stargazers_count", 0) for r in own),
        "commits": safe(lambda: search_count("commits", f"author:{user}")),
        "prs": safe(lambda: search_count("issues", f"author:{user} type:pr")),
        "issues": safe(lambda: search_count("issues", f"author:{user} type:issue")),
        "repos": len(own),
        "followers": info.get("followers", 0),
    }


# ícones simples desenhados em uma caixa 16x16
ICONS = {
    "stars": '<path d="M8 1.3l2 4.2 4.6.6-3.4 3.2.9 4.6L8 11.7l-4.1 2.2.9-4.6L1.4 6.1 6 5.5z" '
             'fill="none" stroke-width="1.4" stroke-linejoin="round"/>',
    "commits": '<circle cx="8" cy="8" r="3" fill="none" stroke-width="1.5"/>'
               '<path d="M0.5 8H5M11 8h4.5" stroke-width="1.5" stroke-linecap="round"/>',
    "prs": '<circle cx="4" cy="3.5" r="1.8" fill="none" stroke-width="1.4"/>'
           '<circle cx="4" cy="12.5" r="1.8" fill="none" stroke-width="1.4"/>'
           '<circle cx="12" cy="12.5" r="1.8" fill="none" stroke-width="1.4"/>'
           '<path d="M4 5.3v5.4M12 10.7V6.5a2 2 0 0 0-2-2H7.5M9 3l-1.5 1.5L9 6" fill="none" '
           'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>',
    "issues": '<circle cx="8" cy="8" r="6.3" fill="none" stroke-width="1.4"/>'
              '<circle cx="8" cy="8" r="1.4" stroke="none"/>',
    "repos": '<path d="M3 2.5A1.5 1.5 0 0 1 4.5 1H13v11H4.5A1.5 1.5 0 0 0 3 13.5zM3 13.5A1.5 1.5 0 0 0 4.5 15H13v-3" '
             'fill="none" stroke-width="1.4" stroke-linejoin="round"/>',
    "followers": '<circle cx="6" cy="5" r="2.6" fill="none" stroke-width="1.4"/>'
                 '<path d="M1.5 14c0-2.6 2-4.4 4.5-4.4s4.5 1.8 4.5 4.4M11 3a2.4 2.4 0 0 1 0 4.4M12.3 9.8c1.3.6 2.2 2 2.2 4.2" '
                 'fill="none" stroke-width="1.4" stroke-linecap="round"/>',
}

ROWS = [
    ("stars", "Estrelas recebidas"),
    ("commits", "Commits"),
    ("prs", "Pull requests"),
    ("issues", "Issues abertas"),
    ("repos", "Repositórios"),
    ("followers", "Seguidores"),
]


def fmt_num(v):
    if v is None:
        return "–"
    if v >= 1000:
        return f"{v / 1000:.1f}k".replace(".0k", "k")
    return str(v)


def render(d):
    w, h = 467, 195
    rows = []
    for i, (key, label) in enumerate(ROWS):
        y = 58 + i * 23
        delay = 150 + i * 120
        rows.append(
            f'<g class="row" style="animation-delay:{delay}ms" transform="translate(25,{y})">'
            f'<g class="ic" transform="translate(0,-12)">{ICONS[key]}</g>'
            f'<text x="26" class="lb">{escape(label)}:</text>'
            f'<text x="200" class="vl">{fmt_num(d[key])}</text></g>'
        )
    total = sum(v or 0 for k, v in d.items() if k in ("stars", "commits", "prs", "issues"))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t">
<title id="t">Estatísticas do GitHub de {escape(d["name"])}</title>
<style>
.tt{{font:600 18px 'Segoe UI',Ubuntu,Sans-Serif;fill:{TITLE}}}
.lb{{font:600 14px 'Segoe UI',Ubuntu,Sans-Serif;fill:{TEXT}}}
.vl{{font:700 14px 'Segoe UI',Ubuntu,Sans-Serif;fill:{TEXT}}}
.ic{{stroke:{ICON};fill:{ICON}}}
.row{{opacity:0;animation:fade .4s ease-out forwards}}
.big{{font:800 26px 'Segoe UI',Ubuntu,Sans-Serif;fill:{TITLE}}}
.cap{{font:600 11px 'Segoe UI',Ubuntu,Sans-Serif;fill:{MUTED}}}
.ring{{fill:none;stroke:{TITLE};stroke-width:6;stroke-linecap:round;stroke-dasharray:251;stroke-dashoffset:251;
transform:rotate(-90deg);transform-origin:390px 108px;animation:ring 1.2s ease-out .3s forwards}}
@keyframes fade{{to{{opacity:1}}}}
@keyframes ring{{to{{stroke-dashoffset:40}}}}
</style>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="4.5" fill="{BG}"/>
<text x="25" y="33" class="tt">Estatísticas de {escape(d["name"])}</text>
{"".join(rows)}
<circle cx="390" cy="108" r="40" fill="none" stroke="{TITLE}" stroke-opacity=".2" stroke-width="6"/>
<circle class="ring" cx="390" cy="108" r="40"/>
<text x="390" y="112" text-anchor="middle" class="big">{fmt_num(total)}</text>
<text x="390" y="128" text-anchor="middle" class="cap">no total</text>
</svg>'''


def main():
    user, out = sys.argv[1], sys.argv[2]
    data = json.loads(os.environ["STATS_MOCK"]) if os.environ.get("STATS_MOCK") else collect(user)
    print(data)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(data))


if __name__ == "__main__":
    main()
