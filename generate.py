"""Generates dark_mode.svg and light_mode.svg for the GitHub profile README.

Run locally or from the GitHub Action. GitHub stats are fetched through the
GraphQL API when GITHUB_TOKEN (or GH_TOKEN) is set; otherwise the last known
values from stats.json are used.
"""
import datetime
import json
import os
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
USER = "knespii"
GITHUB_SINCE = datetime.date(2023, 7, 30)
WIDTH = 54  # characters per info line

THEMES = {
    "dark": {
        "bg": "#161b22", "text": "#c9d1d9", "key": "#ffa657", "value": "#a5d6ff",
        "cc": "#616e7f", "ink": "#f0f6fc",
    },
    "light": {
        "bg": "#f6f8fa", "text": "#24292f", "key": "#953800", "value": "#0a3069",
        "cc": "#c2cfde", "ink": "#1f2328",
    },
}

INFO = [
    ("header", "viktor@knespl"),
    ("row", ["Uptime"], "{uptime}"),
    ("row", ["Host"], "SSPŠ Praha"),
    ("row", ["Kernel"], "IT Student"),
    ("row", ["Location"], "Prague, Czech Republic"),
    ("blank",),
    ("row", ["Languages", "Programming"], "Python, C#, JS, TypeScript"),
    ("row", ["Languages", "Computer"], "HTML, CSS, Bash, Docker"),
    ("row", ["Languages", "Real"], "Czech, English"),
    ("blank",),
    ("row", ["Focus", "3D"], "3D Modeling in Fusion 360"),
    ("row", ["Focus", "Electronics"], "PCB Design in KiCad"),
    ("row", ["Currently", "Learning"], "KiCad, PCB Design"),
    ("blank",),
    ("row", ["Interests", "Tech"], "Linux, IoT, Raspberry Pi, E-ink"),
    ("row", ["Interests", "Software"], "GNOME extensions, AI tools"),
    ("row", ["Interests", "Making"], "3D Printing, Handwired Keyboards"),
    ("empty",),
    ("header", "- Contact"),
    ("row", ["LinkedIn"], "viktor-knespl"),
    ("row", ["GitHub"], "knespii"),
    ("empty",),
    ("header", "- GitHub Stats"),
    ("stats1",),
    ("stats2",),
]


def uptime(today):
    years = today.year - GITHUB_SINCE.year
    months = today.month - GITHUB_SINCE.month
    days = today.day - GITHUB_SINCE.day
    if days < 0:
        months -= 1
        prev_month_end = today.replace(day=1) - datetime.timedelta(days=1)
        days += prev_month_end.day
    if months < 0:
        years -= 1
        months += 12
    plural = lambda n, word: f"{n} {word}{'' if n == 1 else 's'}"
    return f"{plural(years, 'year')}, {plural(months, 'month')}, {plural(days, 'day')}"


def graphql(token, query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {token}"},
    )
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


def fetch_stats(token):
    data = graphql(token, f"""{{ user(login: "{USER}") {{
        followers {{ totalCount }}
        repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) {{ totalCount }}
        repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100) {{
            totalCount nodes {{ stargazerCount }} }}
        contributionsCollection {{ contributionYears }} }} }}""")["user"]
    years = data["contributionsCollection"]["contributionYears"]
    year_queries = " ".join(
        f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y}-12-31T23:59:59Z")'
        " { totalCommitContributions restrictedContributionsCount }"
        for y in years
    )
    per_year = graphql(token, f'{{ user(login: "{USER}") {{ {year_queries} }} }}')["user"]
    commits = sum(v["totalCommitContributions"] + v["restrictedContributionsCount"] for v in per_year.values())
    return {
        "repos": data["repositories"]["totalCount"],
        "contributed": data["repositoriesContributedTo"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in data["repositories"]["nodes"]),
        "commits": commits,
        "followers": data["followers"]["totalCount"],
    }


def dots(n):
    return f'<tspan class="cc"> {"." * max(n, 1)} </tspan>'


def row(keys, value):
    label = ".".join(keys)
    keys_svg = ".".join(f'<tspan class="key">{escape(k)}</tspan>' for k in keys)
    # ". " + label + ":" + " dots " + value
    fill = WIDTH - 2 - len(label) - 1 - 2 - len(value)
    return f'<tspan class="cc">. </tspan>{keys_svg}:{dots(fill)}<tspan class="value">{escape(value)}</tspan>'


def pair(k1, v1, k2, v2, contributed=None):
    v1, v2 = f"{v1:,}", f"{v2:,}"
    extra_svg, extra_len = "", 0
    if contributed is not None:
        extra_svg = f' {{<tspan class="key">Contributed</tspan>: <tspan class="value">{contributed}</tspan>}}'
        extra_len = len(f" {{Contributed: {contributed}}}")
    left_width = 31
    fill1 = left_width - 2 - len(k1) - 1 - 2 - len(v1) - extra_len
    fill2 = WIDTH - left_width - 3 - len(k2) - 1 - 2 - len(v2)
    return (f'<tspan class="cc">. </tspan><tspan class="key">{k1}</tspan>:{dots(fill1)}'
            f'<tspan class="value">{v1}</tspan>{extra_svg} | <tspan class="key">{k2}</tspan>:{dots(fill2)}'
            f'<tspan class="value">{v2}</tspan>')


def info_lines(stats, today):
    lines = []
    for item in INFO:
        kind = item[0]
        if kind == "header":
            title = item[1]
            lines.append(f'{escape(title)} -{"—" * (WIDTH - len(title) - 5)}-—-')
        elif kind == "row":
            lines.append(row(item[1], item[2].format(uptime=uptime(today))))
        elif kind == "blank":
            lines.append('<tspan class="cc">. </tspan>')
        elif kind == "empty":
            lines.append("")
        elif kind == "stats1":
            lines.append(pair("Repos", stats["repos"], "Stars", stats["stars"], stats["contributed"]))
        elif kind == "stats2":
            lines.append(pair("Commits", stats["commits"], "Followers", stats["followers"]))
    return lines


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def art_row(glyphs, levels):
    """Groups runs of equal brightness into tspans with a level class."""
    out, i = [], 0
    while i < len(glyphs):
        j = i
        while j < len(glyphs) and levels[j] == levels[i]:
            j += 1
        out.append(f'<tspan class="l{levels[i]}">{escape(glyphs[i:j])}</tspan>')
        i = j
    return "".join(out)


def render(theme, stats, today):
    t = THEMES[theme]
    art = json.loads((ROOT / "art.json").read_text())
    levels_css = "\n".join(
        f".l{k} {{fill: {mix(t['bg'], t['ink'], 0.12 + 0.88 * (k if theme == 'dark' else 9 - k) / 9)};}}"
        for k in range(10)
    )
    art_svg = "\n".join(
        f'<tspan x="15" y="{24 + i * 8}" textLength="400" lengthAdjust="spacingAndGlyphs">'
        f'{art_row(glyphs, levels)}</tspan>'
        for i, (glyphs, levels) in enumerate(zip(art[theme], art["level"]))
    )
    info_svg = "\n".join(
        f'<tspan x="430" y="{30 + i * 20}">{line}</tspan>'
        for i, line in enumerate(info_lines(stats, today)) if line
    )
    return f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="985px" height="530px" font-size="16px">
<style>
@font-face {{
src: local('Consolas'), local('Consolas Bold');
font-family: 'ConsolasFallback';
font-display: swap;
-webkit-size-adjust: 109%;
size-adjust: 109%;
}}
.key {{fill: {t["key"]};}}
.value {{fill: {t["value"]};}}
.cc {{fill: {t["cc"]};}}
.ascii {{font-size: 7px;}}
{levels_css}
text, tspan {{white-space: pre;}}
</style>
<rect width="985px" height="530px" fill="{t["bg"]}" rx="15"/>
<text x="15" y="30" fill="{t["text"]}" class="ascii">
{art_svg}
</text>
<text x="430" y="30" fill="{t["text"]}">
{info_svg}
</text>
</svg>
"""


def main():
    stats_file = ROOT / "stats.json"
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        stats = fetch_stats(token)
        stats_file.write_text(json.dumps(stats, indent=2) + "\n")
    else:
        stats = json.loads(stats_file.read_text())
    today = datetime.date.today()
    for theme in THEMES:
        (ROOT / f"{theme}_mode.svg").write_text(render(theme, stats, today))


if __name__ == "__main__":
    main()
