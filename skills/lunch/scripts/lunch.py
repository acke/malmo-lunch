#!/usr/bin/env python3
"""Malmö lunch: today's menus from menydags.se + mylunch.se, fixed-menu places, per-user favorites. Stdlib only.

  lunch.py menu [--area NAME]   JSON: favorites first, then the rest by name
  lunch.py fav list|add|rm SLUG...
"""
import datetime
import gzip
import html
import http.client
import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE = "https://www.menydags.se/lunch/malmo"
MAX_PAGES = 6
MYLUNCH_BASE = "https://www.mylunch.se"
MYLUNCH = [("/vastr-hamnen/", "Hamnen"), ("/malmo/", "Malmö")]  # (page, area label)
TOO_FAR = {"Hyllie", "Limhamn", "Möllevången"}  # areas too far from the office
PREFS = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
                     "malmo-lunch", "prefs.json")

CARD = re.compile(r'<a [^>]*href="/restaurang/([^"]+)"[^>]*><h3[^>]*>(.*?)</h3>')
AREA = re.compile(r'<p[^>]*><span[^>]*>(?:\s|<!-- -->)*([^<]+)</span></p>')
DISH = re.compile(r'<li[^>]*>.*?<p[^>]*>(.*?)</p>(?:<p[^>]*>(.*?)</p>)?.*?<span[^>]*>([\d/]+)(?:<!-- -->)?:-</span>', re.S)
SUMMARY = re.compile(r'Lunch idag:</span>\s*(?:<!-- -->)?(.*?)(?:<!-- -->)?\s*m\.fl\.|Lunch idag:</span>\s*(?:<!-- -->)?([^<]*)')


def get(url):
    # pages are ~1MB chunked; gzip shrinks them and a retry covers dropped streams
    req = urllib.request.Request(url, headers={"User-Agent": "malmo-lunch/0.1", "Accept-Encoding": "gzip"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                body = r.read()
                return (gzip.decompress(body) if r.headers.get("Content-Encoding") == "gzip" else body).decode("utf-8")
        except http.client.IncompleteRead:
            if attempt == 2:
                raise


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>|<!-- -->", "", s or "")).strip()


def parse(page):
    page = re.sub(r"<script.*?</script>|<svg.*?</svg>", "", page, flags=re.S)
    cards = list(CARD.finditer(page))
    for i, m in enumerate(cards):
        end = cards[i + 1].start() if i + 1 < len(cards) else len(page)
        seg = page[m.end():end]
        area = AREA.search(seg)
        # "Gäller hela vecka" dishes are standing items, not today's lunch
        today = seg.split("Gäller hela vecka")[0]
        dishes = [{"name": clean(n), "desc": clean(d), "price": p}
                  for n, d, p in DISH.findall(today)] if "Dagens lunch</h3>" in today else []
        s = SUMMARY.search(seg)
        yield {
            "slug": m.group(1),
            "name": clean(m.group(2)),
            "area": clean(area.group(1)) if area else "",
            "dishes": dishes,
            "summary": clean(s.group(1) or s.group(2)) if s else "",
        }


def norm(name):
    return re.sub(r"[^a-z0-9åäö]", "", html.unescape(name).lower())


def parse_mylunch(page, area):
    """Today's dishes per restaurant card. Rows: [weekday heading, dishes..., '* * * * *', extras]."""
    days = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
    today = days[datetime.date.today().weekday()]
    for card in page.split('<div class="mi" ')[1:]:
        name = re.search(r'<h2 title="Öppna sidan[^"]*">(.*?)</h2>', card)
        rows = [(clean(t), clean(p)) for t, p in
                re.findall(r'<p class="mim-txt0?">(.*?)</p><p class="mim-prc">(.*?)</p>', card, re.S)]
        start = next((i for i, (t, _) in enumerate(rows) if t.startswith(today)), None)
        dishes = []
        for t, p in rows[start + 1:] if start is not None else []:
            if t.startswith("*") or t.startswith(tuple(days)):
                break
            dishes.append({"name": t, "desc": "", "price": p.removesuffix("Kr")})
        if name and dishes:
            n = clean(name.group(1))
            yield {"slug": "mylunch-" + norm(n), "name": n, "area": area, "dishes": dishes,
                   "summary": " · ".join(d["name"] for d in dishes)}


def standing():
    """Places with a fixed menu and no daily lunch; shipped in standing.json next to SKILL.md."""
    with open(os.path.join(os.path.dirname(__file__), "..", "standing.json")) as f:
        for s in json.load(f):
            yield {"slug": "standing-" + norm(s["name"]), "name": s["name"], "area": s["area"],
                   "dishes": [], "summary": s["note"], "standing": True}


def load_prefs():
    try:
        with open(PREFS) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"favorites": []}


def save_prefs(p):
    os.makedirs(os.path.dirname(PREFS), exist_ok=True)
    with open(PREFS, "w") as f:
        json.dump(p, f, indent=2, ensure_ascii=False)


def menu(area):
    seen = {}
    for n in range(1, MAX_PAGES + 1):
        try:
            found = {r["slug"]: r for r in parse(get(f"{BASE}?sida={n}"))}
        except urllib.error.HTTPError as e:
            if e.code == 404:  # past the last page
                break
            raise
        if not set(found) - set(seen):
            break
        seen.update(found)
    by_name = {norm(r["name"]): r for r in seen.values()}
    for path, label in MYLUNCH:
        try:
            extra = list(parse_mylunch(get(MYLUNCH_BASE + path), label))
        except (urllib.error.URLError, http.client.HTTPException) as e:
            print(f"mylunch {path} skipped: {e}", file=sys.stderr)
            continue
        for r in extra:
            have = by_name.get(norm(r["name"]))
            if have:  # mylunch lists the actual dishes; menydags often only a teaser
                have["dishes"] = have["dishes"] or r["dishes"]
            elif r["slug"] not in seen:
                seen[r["slug"]] = by_name[norm(r["name"])] = r
    for r in standing():
        if norm(r["name"]) not in by_name:
            seen[r["slug"]] = r
    favs = load_prefs()["favorites"]
    rows = [r for r in seen.values()
            if (r["dishes"] or r["summary"]) and r["area"] not in TOO_FAR]
    if area:
        rows = [r for r in rows if r["area"].lower() == area.lower()]
    for r in rows:
        r["fav"] = r["slug"] in favs
    rows.sort(key=lambda r: (not r["fav"], r["name"].lower()))
    print(json.dumps(rows, ensure_ascii=False, indent=1))


def fav(action, slugs):
    p = load_prefs()
    if action == "add":
        p["favorites"] += [s for s in slugs if s not in p["favorites"]]
    elif action == "rm":
        p["favorites"] = [s for s in p["favorites"] if s not in slugs]
    elif action != "list":
        sys.exit(__doc__)
    save_prefs(p)
    print(json.dumps(p["favorites"], ensure_ascii=False))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["menu"]:
        menu(a[2] if a[1:2] == ["--area"] and len(a) > 2 else None)
    elif a[:1] == ["fav"] and len(a) > 1:
        fav(a[1], a[2:])
    else:
        sys.exit(__doc__)
