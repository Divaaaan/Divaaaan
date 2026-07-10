#!/usr/bin/env python3
"""Render assets/signals.svg — language distribution + contribution stats.

Pulls public data from the GitHub API and renders a spec-sheet style SVG
(FIG. 02, companion to the FIG. 01 banner). Stdlib only.

Env: GITHUB_TOKEN (optional locally, required in CI to avoid rate limits).
"""

import json
import os
import sys
import urllib.request
from datetime import date

LOGIN = "Divaaaan"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "signals.svg")

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

# canon palette: one orange signal, then a mono ladder
SEG_COLORS = ["#ff3d00", "#f4f4f0", "#8c8c88", "#5a5a57", "#3a3a3a"]
OTHER_COLOR = "#2a2a2a"
MAX_LANGS = 5


def api(path, payload=None):
    req = urllib.request.Request(API + path)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", LOGIN)
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    if payload is not None:
        req.data = json.dumps(payload).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_languages():
    repos = api(f"/users/{LOGIN}/repos?type=owner&per_page=100")
    totals = {}
    src_count = 0
    for repo in repos:
        if repo.get("fork"):
            continue
        src_count += 1
        langs = api(f"/repos/{LOGIN}/{repo['name']}/languages")
        for lang, size in langs.items():
            totals[lang] = totals.get(lang, 0) + size
    return totals, src_count


def fetch_contributions():
    query = {
        "query": (
            '{ user(login: "%s") { contributionsCollection '
            "{ contributionCalendar { totalContributions } } } }" % LOGIN
        )
    }
    data = api("/graphql", query)
    return data["data"]["user"]["contributionsCollection"][
        "contributionCalendar"
    ]["totalContributions"]


def build_svg(totals, src_count, contributions):
    grand = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    top = ranked[:MAX_LANGS]
    other = sum(size for _, size in ranked[MAX_LANGS:])

    segments = [
        (lang.upper(), size / grand, SEG_COLORS[i])
        for i, (lang, size) in enumerate(top)
    ]
    if other:
        segments.append(("OTHER", other / grand, OTHER_COLOR))

    bar_x, bar_w, bar_y, bar_h = 32, 816, 58, 12
    gap = 2.0

    bar_rects = []
    legend_items = []
    x = float(bar_x)
    free = bar_w - gap * (len(segments) - 1)
    for i, (name, share, color) in enumerate(segments):
        w = free * share
        bar_rects.append(
            f'  <rect x="{x:.1f}" y="{bar_y}" width="{max(w, 1.5):.1f}" '
            f'height="{bar_h}" fill="{color}"/>'
        )
        x += w + gap
        lx = 32 + (i % 3) * 272
        ly = 102 + (i // 3) * 24
        legend_items.append(
            f'  <rect x="{lx}" y="{ly - 8}" width="8" height="8" fill="{color}"/>\n'
            f'  <text x="{lx + 18}" y="{ly}" class="lname">{name}</text>\n'
            f'  <text x="{lx + 140}" y="{ly}" class="lval">'
            f"{share * 100:.1f}%</text>"
        )

    legend_rows = 1 if len(segments) <= 3 else 2
    footer_y = 132 + (legend_rows - 1) * 24
    height = footer_y + 28
    stamp = date.today().isoformat()

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 {height}" width="880" height="{height}" role="img" aria-label="Language distribution across public source repositories">
  <style>
    text {{ font-family: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace; }}
    .fig   {{ fill: #ff3d00; font-size: 12px; letter-spacing: 3px; }}
    .cap   {{ fill: #8c8c88; font-size: 12px; letter-spacing: 2px; }}
    .dim   {{ fill: #5a5a57; font-size: 11px; letter-spacing: 2px; }}
    .lname {{ fill: #8c8c88; font-size: 11px; letter-spacing: 1.5px; }}
    .lval  {{ fill: #f4f4f0; font-size: 11px; letter-spacing: 1px; }}
  </style>
  <rect x="0" y="0" width="880" height="{height}" fill="#0e0e0e"/>
  <rect x="0.5" y="0.5" width="879" height="{height - 1}" fill="none" stroke="#2a2a2a" stroke-width="1"/>

  <text x="32" y="36" class="fig">FIG. 02</text>
  <text x="112" y="36" class="cap">— LANGUAGE DISTRIBUTION · PUBLIC SRC</text>
  <text x="848" y="36" class="dim" text-anchor="end">{src_count} REPOS</text>

{chr(10).join(bar_rects)}

{chr(10).join(legend_items)}

  <line x1="32" y1="{footer_y - 20}" x2="848" y2="{footer_y - 20}" stroke="#2a2a2a" stroke-width="1"/>
  <text x="32" y="{footer_y}" class="dim">CONTRIBUTIONS · 365D — {contributions}</text>
  <text x="848" y="{footer_y}" class="dim" text-anchor="end">PLOTTED {stamp}</text>
</svg>
"""


def main():
    totals, src_count = fetch_languages()
    if not totals:
        print("no language data — refusing to overwrite", file=sys.stderr)
        return 1
    contributions = fetch_contributions()
    svg = build_svg(totals, src_count, contributions)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(svg)
    print(f"rendered {os.path.normpath(OUT)}: {src_count} repos, "
          f"{len(totals)} languages, {contributions} contributions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
