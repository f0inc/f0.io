#!/usr/bin/env python3
"""Builds overtones from news.txt: index.html (latest day) and one page per day in YYYY-MM-DD/."""
import datetime, hashlib, html, os, re, shutil, sys
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
PALETTE = ['#b5446e', '#d9773a', '#dcb043', '#6f9f52', '#1f8a86', '#33509e', '#5a3f93']
FIXED = {'models': 5, 'funding': 3, 'research': 6, 'tools': 4, 'product': 1, 'pricing': 2, 'policy': 0}

def parse(path):
    days, cur = {}, None
    for n, raw in enumerate(open(path, encoding='utf-8'), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', line):
            cur = days.setdefault(datetime.date.fromisoformat(line), [])
            continue
        parts = [p.strip() for p in line.split('|')]
        if cur is None or len(parts) != 3 or not re.match(r'https?://', parts[2]):
            sys.exit(f'news.txt line {n}: expected "category | headline | https://link" under a date line')
        cur.append(parts)
    return sorted(days.items(), reverse=True)

def _lum(rgb):
    lin = [((v / 255 + 0.055) / 1.055) ** 2.4 if v > 10 else v / 255 / 12.92 for v in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

def colour(cat):
    """(logo colour, text colour, a thin veil over the paint that guarantees the text reads, palette index)

    Light colours take black text and a faint white veil. Mid and dark colours take white text, and are
    deepened just enough for white to reach a contrast of 5.5: the hue stays the logo's, only a shade darker."""
    k = cat.lower()
    c = PALETTE[FIXED[k] if k in FIXED else int(hashlib.sha1(k.encode()).hexdigest(), 16) % len(PALETTE)]
    rgb = bytes.fromhex(c[1:])
    if (_lum(rgb) + 0.05) / 0.05 >= 8:
        return c, '#000000', 'rgba(255,255,255,.14)', PALETTE.index(c)
    a = 0.0
    while 1.05 / (_lum([v * (1 - a) for v in rgb]) + 0.05) < 5.5:
        a += 0.02
    return c, '#ffffff', f'rgba(0,0,0,{a + 0.06:.2f})', PALETTE.index(c)

def short(d):
    return f'{d.day} {d:%B %Y}'

def nice(d):
    return f'{d:%A}, {d.day} {d:%B %Y}'

def page(day, items, days, root, archive=False):
    e = html.escape
    rows = '\n'.join(
        f'    <li><span class="cat" style="--c: {colour(c)[0]}; --t: {colour(c)[1]}; --o: {colour(c)[2]}; --paint: var(--paint-{colour(c)[3]}); --pos: {20 + n * 37 % 60}% {20 + n * 53 % 60}%">{e(c.lower())}</span>'
        f'<span class="story"><a href="{e(u, quote=True)}" rel="noopener">{e(t)}</a> <span class="src">{e(urlparse(u).netloc.removeprefix("www."))}</span></span></li>'
        for n, (c, t, u) in enumerate(items))
    link = lambda d: f'      <li><a href="{root}{d}/">{nice(d)}</a></li>'
    if archive:
        title = 'f0 overtones · archive'
        section = ('  <section class="day">\n    <h1><a href="https://f0.io">f0</a> <span class="name">overtones</span> <span aria-hidden="true">·</span> archive</h1>\n    <ul class="days">\n'
                   + '\n'.join(link(d) for d, _ in days) + '\n    </ul>\n  </section>\n')
        nav = ''
    else:
        title = f'f0 overtones · {nice(day)}'
        section = (f'  <section class="day">\n    <h1><a href="https://f0.io">f0</a> <span class="name">overtones</span> <span class="when"><span aria-hidden="true">·</span> Daily breakdown of what happened in voice AI</span></h1>\n    <p class="tag"><time datetime="{day}">{short(day)}</time></p>\n'
                   f'    <ol>\n{rows}\n    </ol>\n  </section>\n')
        past = [d for d, _ in days if d < day][:5]          # the five days before this one
        nav = ('\n  <nav aria-labelledby="prev">\n    <h2 id="prev">Previous days</h2>\n    <ul class="days">\n' + ''.join(link(d) + '\n' for d in past)
               + f'      <li class="arch"><a href="{root}archive/">Archive<svg class="arr" viewBox="0 0 10 10" aria-hidden="true"><path d="M2.5 7.5 7.5 2.5M3.5 2.5h4v4" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg></a></li>\n    </ul>\n  </nav>\n')
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="Daily breakdown of what happened in voice AI, by f0.">
<link rel="icon" type="image/png" href="{root}favicon.png">
<meta name="theme-color" content="#f6f6f6" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#161616" media="(prefers-color-scheme: dark)">
<!-- the brush paintings, baked in as images by ../paint/make.py: loaded before the page is drawn, so nothing flickers -->
<link rel="stylesheet" href="{root}paint.css">
<style>
  @font-face {{ font-family: "GT Alpina"; src: url("{root}fonts/GT-Alpina-Standard-Medium.woff2") format("woff2"); font-weight: 500; font-display: swap; }}
  @font-face {{ font-family: "GT America"; src: url("{root}fonts/GT-America-Standard-Regular.woff2") format("woff2"); font-weight: 400; font-display: swap; }}
  @font-face {{ font-family: "GT America"; src: url("{root}fonts/GT-America-Standard-Medium.woff2") format("woff2"); font-weight: 500; font-display: swap; }}
  /* same page as f0.io: one left-anchored column, light grey or soft near-black from the system */
  :root {{ color-scheme: light dark; --bg: #f6f6f6; --ink: #121212; --muted: #5e5e5e; --rule: #dadada; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg: #161616; --ink: #f2f2f2; --muted: #9b9b9b; --rule: #303030; }} }}
  * {{ box-sizing: border-box; }}
  html {{ -webkit-text-size-adjust: 100%; }}
  body {{ margin: 0; background: var(--bg); color: var(--ink); font-family: "GT America", "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 19px; line-height: 1.5; -webkit-font-smoothing: antialiased; }}
  main {{ box-sizing: content-box; max-width: 760px; margin: 0; padding: 24px 24px 64px; display: flex; flex-direction: column; gap: 28px; }}
  a {{ color: var(--ink); text-decoration: none; }}
  a:hover {{ color: var(--muted); }}
  a:focus-visible {{ outline: 2px solid var(--ink); outline-offset: 3px; }}
  h1 {{ margin: 0; font-size: 19px; font-weight: 500; line-height: 1.3; display: flex; flex-wrap: wrap; align-items: center; column-gap: 0.4em; }}
  h1 .when, h1 .when span {{ color: var(--muted); font-weight: 400; }}
  h1 .name {{ color: var(--ink); }}
  /* the date belongs to the list: more room above it, little below */
  .tag {{ margin: 6px 0 -10px; color: var(--muted); font-size: 16px; }}
  /* f0 as on the favicon: white letters on a tile of the brush painting (the painting comes from paint.css; the gradient is the fallback) */
  h1 a {{ display: block; padding: 0.16em 0.34em 0.18em 0.3em; border-radius: 5px; color: #fff; font-family: "GT Alpina", Georgia, serif; font-size: 1.12em; line-height: 1; text-decoration: none;
    background: linear-gradient(rgba(0,0,0,.2), rgba(0,0,0,.2)), var(--paint-tile, conic-gradient(from 40deg, #1f8a86, #33509e, #5a3f93, #b5446e, #d9773a, #dcb043, #6f9f52, #1f8a86)) center / cover no-repeat; }}
  h1 a:hover {{ color: #fff; filter: brightness(1.1); }}
  /* section label: plain sentence case at the size of the dates, set apart by weight and colour, not capitals */
  h2 {{ margin: 0; font-size: 16px; font-weight: 500; color: var(--ink); }}
  /* the day's list: category, headline, most important first */
  .day {{ display: flex; flex-direction: column; gap: 14px; }}
  ol {{ list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: auto minmax(0, 1fr); column-gap: 14px; row-gap: 12px; }}
  ol li {{ grid-column: 1 / -1; display: grid; grid-template-columns: subgrid; align-items: baseline; }}
  /* category badge: the exact logo colour for its category, with quiet strokes of the logo's brush laid over it
     (the strokes come from paint.css; without it the badge is the flat colour) */
  .cat {{ justify-self: start; padding: 2px 8px; border-radius: 5px; background: linear-gradient(var(--o), var(--o)), var(--c) var(--paint, none) var(--pos, 50% 50%) / 200px auto; color: var(--t); font-size: 13px; font-weight: 500; line-height: 1.5; white-space: nowrap; position: relative; top: -1px; }}
  .src {{ color: var(--muted); font-size: 14px; white-space: nowrap; margin-left: 4px; }}
  .days {{ list-style: none; margin: 4px 0 0; padding: 0; display: flex; flex-direction: column; gap: 2px; font-size: 16px; }}
  /* earlier days look like today's date line: same size, same grey */
  .days a {{ color: var(--muted); }}
  /* drawn, not a font character, so it is the same small size in every browser */
  .arr {{ width: 0.55em; height: 0.55em; margin-left: 0.3em; vertical-align: 0.08em; }}
  .days a:hover {{ color: var(--ink); }}
  @media (max-width: 520px) {{
    main {{ padding: 16px 16px 48px; }} body {{ font-size: 17px; }}
    ol {{ column-gap: 10px; row-gap: 14px; }}
    /* the tagline drops to its own line here, so it loses its leading dot */
    h1 .when {{ flex-basis: 100%; margin-top: 4px; font-size: 16px; }} h1 .when span {{ display: none; }}
  }}
</style>
</head>
<body>
<main>
{section}{nav}</main>
</body>
</html>
'''

def main():
    days = parse(os.path.join(HERE, 'news.txt'))
    if not days:
        sys.exit('news.txt has no days')
    open(os.path.join(HERE, 'index.html'), 'w', encoding='utf-8').write(page(days[0][0], days[0][1], days, ''))
    for d, items in days:
        os.makedirs(os.path.join(HERE, str(d)), exist_ok=True)
        open(os.path.join(HERE, str(d), 'index.html'), 'w', encoding='utf-8').write(page(d, items, days, '../'))
    os.makedirs(os.path.join(HERE, 'archive'), exist_ok=True)
    open(os.path.join(HERE, 'archive', 'index.html'), 'w', encoding='utf-8').write(page(days[0][0], [], days, '../', archive=True))
    # shared assets from the main site, so this folder can be deployed on its own
    site = os.path.dirname(HERE)
    for f in ('favicon.png',):
        if os.path.exists(os.path.join(site, f)):
            shutil.copy(os.path.join(site, f), os.path.join(HERE, f))
    if os.path.isdir(os.path.join(site, 'fonts')):
        shutil.copytree(os.path.join(site, 'fonts'), os.path.join(HERE, 'fonts'), dirs_exist_ok=True)
    print(f'built {len(days)} day(s); latest {days[0][0]} with {len(days[0][1])} stories')

if __name__ == '__main__':
    main()
