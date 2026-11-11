#!/usr/bin/env python3
"""Malmö lunch: today's menus from menydags.se + mylunch.se, fixed-menu places, per-user visit counts. Stdlib only.

  lunch.py list [--area NAME]   today's list as ready-to-print text, fetched live (--json: raw rows)
  lunch.py go NAME              record a visit to NAME
  lunch.py undo NAME            remove one recorded visit to NAME
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
LABELS = {"idag", "green", "local", "world wide", "asia", "dagens", "vegetariskt", "vegan", "veg"}  # mylunch headings
# mylunch rows that describe a dish rather than name one: 'Serveras med ...', English translations, tag lists
NOT_DISH = re.compile(r"^(?:serveras|serverad|severas|served)\b|\b(?:with|and|stew|served)\b|^vi erbjuder|^\S+(?: - \S+)+$", re.I)
TOO_FAR = {"Hyllie", "Limhamn", "Möllevången"}  # areas too far from the office
TOP_N = 5  # this many most-visited places are listed first
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
    """Match key across sources: 'Brasserie Sture 1912' == 'Sture', 'Varv Malmö' == 'Varv'."""
    name = re.sub(r"\b(kvartersrestaurang|restaurang|restaurant|brasserie|hotel|malmö|1912)\b", "", html.unescape(name).lower())
    return re.sub(r"[^a-z0-9åäö]", "", name)


def tidy(dish):
    """Strip source noise from a dish row: 'Onsdag: ' prefix, allergen codes, trailing à-la-carte price."""
    dish = re.sub(r"^[A-ZÅÄÖ][\wåäö ]{0,20}:\s+", "", dish)  # 'Onsdag: ', 'Husman: ' category prefixes
    dish = re.sub(r"\s*\([A-ZÅÄÖ](?:,\s*[A-ZÅÄÖ])*\)", "", dish)
    return dish.strip()


def short(dish, cap=45):
    """Dish name without the ingredient list: 'Kyckling med potatispuré, ärtor' -> 'Kyckling'."""
    dish = re.split(r"\s+(?:med|serveras|serverad|serverade|samt)\s+", dish)[0].strip(" -–")  # 'Daal makahni - med linser' -> 'Daal makahni'
    head, _, _ = dish.partition(",")
    if " " in head.strip():  # 'Bakad lax, sås, potatis' -> 'Bakad lax'; one-word heads are list items, keep the line
        dish = head.strip()
    return dish if len(dish) <= cap else dish[:cap - 1].rstrip() + "…"


def summarize(dishes, limit=6):
    names = []
    for d in dishes:
        n = short(d["name"])
        if n and n not in names:
            names.append(n)
    return " · ".join(names[:limit])


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
            t = tidy(t)
            # drop section labels ("Idag", "Green") and à-la-carte rows ("Beef tartare 190")
            if (t.lower() in LABELS or re.search(r"\s\d{3}$", t) or NOT_DISH.search(t)
                    or any(d["name"] == t for d in dishes)):
                continue
            dishes.append({"name": t, "desc": "", "price": p.removesuffix("Kr")})
        if name and dishes:
            n = clean(name.group(1))
            yield {"slug": "mylunch-" + norm(n), "name": n, "area": area, "dishes": dishes,
                   "summary": summarize(dishes)}


DAYS = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]


def clemens(page):
    """Veckans Lunchmeny: today's weekday block."""
    today = DAYS[datetime.date.today().weekday()]
    return [clean(d) for day, d in re.findall(r'<div class="acme[^"]*">(\w+)</div><div class="italic">(.*?)</div>', page)
            if day == today]


def holygreens(page):
    """First 5 dishes on the menu page (chain-wide menu, not Saluhall-specific)."""
    names = [clean(n).capitalize() for n in re.findall(r'<div class="content-wrap"><h3>(.*?)</h3>', page)]
    return [n for n in names if not n.endswith(" vegansk")][:5]  # vegan variants would use up the slots


def p2(page):
    """Veckans meny: the dishes (Green/Local/World Wide) under today's weekday heading."""
    m = re.search(r"<h3[^>]*>%s</h3>(.*?)(?:<h3|$)" % DAYS[datetime.date.today().weekday()], page, re.S)
    return [clean(d) for d in re.findall(r'<div class="lunch_desc">(.*?)</div>', m.group(1))] if m else []


MENUS = {"clemens": clemens, "holygreens": holygreens, "p2": p2}  # standing.json `menu.kind` -> parser


def standing():
    """Places outside the aggregators, from standing.json next to SKILL.md.

    Dishes come from a scraped `menu` page, else a hand-kept `dishes` list. `fixed` marks places
    with no daily lunch, so the skill can say the dishes are their regular menu.
    """
    with open(os.path.join(os.path.dirname(__file__), "..", "standing.json")) as f:
        entries = json.load(f)
    for s in entries:
        names = list(s.get("dishes", []))
        if "menu" in s:
            try:
                names = MENUS[s["menu"]["kind"]](get(s["menu"]["url"])) or names
            except (urllib.error.URLError, http.client.HTTPException) as e:
                print(f"{s['name']} menu skipped: {e}", file=sys.stderr)
        dishes = [{"name": n, "desc": "", "price": ""} for n in names]
        yield {"slug": "standing-" + norm(s["name"]), "name": s["name"], "area": s["area"], "dishes": dishes,
               "summary": summarize(dishes) or s.get("note", ""), "standing": s.get("fixed", False)}


def load_prefs():
    try:
        with open(PREFS) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"visits": {}}


def save_prefs(p):
    os.makedirs(os.path.dirname(PREFS), exist_ok=True)
    with open(PREFS, "w") as f:
        json.dump(p, f, indent=2, ensure_ascii=False)


def places(area):
    """Fetch every source live, merge, and return today's rows, most-visited first. Nothing is cached."""
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
    for r in standing():  # standing.json wins over scraped rows of the same place
        seen = {s: v for s, v in seen.items() if norm(v["name"]) != norm(r["name"])}
        seen[r["slug"]] = r
    for r in seen.values():  # show whichever of the teaser / dish rows names more dishes, ingredients cut
        teaser = [{"name": s} for s in r["summary"].split(" · ") if s] if not r.get("standing") else []
        r["summary"] = max(summarize(r["dishes"]), summarize(teaser), key=lambda s: s.count(" · ")) or r["summary"]
    visits = load_prefs().get("visits", {})
    rows = [r for r in seen.values()
            if (r["dishes"] or r["summary"]) and r["area"] not in TOO_FAR]
    if area:
        rows = [r for r in rows if r["area"].lower() == area.lower()]
    for r in rows:
        r["visits"] = visits.get(norm(r["name"]), 0)
    top = sorted((r for r in rows if r["visits"]), key=lambda r: (-r["visits"], r["name"].lower()))[:TOP_N]
    for r in rows:
        r["fav"] = r in top
    rows.sort(key=lambda r: (top.index(r) if r["fav"] else TOP_N, r["name"].lower()))
    return rows


def render(rows):
    """The finished list, ready to paste: most-visited group, then one group per area, continuous numbers."""
    if not rows:
        return "No lunch places found today (weekend or holiday?)."
    out, n = [f"Today is {datetime.date.today():%a %Y-%m-%d}, {len(rows)} places."], 0

    def group(title, group_rows, counts=False):
        nonlocal n
        out.extend(["", f"**{title}**"])
        for r in group_rows:
            n += 1
            summary = r["summary"] if len(r["summary"]) <= 100 else r["summary"][:99] + "…"
            tag = (" (fast meny)" if r.get("standing") else "") + (f" ({r['visits']}×)" if counts else "")
            out.append(f"{n}. {r['name']}{tag}: {summary}")

    if any(r["fav"] for r in rows):
        group("★ Most visited", [r for r in rows if r["fav"]], counts=True)
    rest = [r for r in rows if not r["fav"]]
    for area in sorted({r["area"] for r in rest}):
        group(area, [r for r in rest if r["area"] == area])
    return "\n".join(out + ["", "Which number (or name) are you going to?"])


def visit(name, delta):
    p = load_prefs()
    visits = p.setdefault("visits", {})
    key = norm(name)
    visits[key] = max(visits.get(key, 0) + delta, 0)
    if not visits[key]:
        del visits[key]
    save_prefs(p)
    print(json.dumps({name: visits.get(key, 0)}, ensure_ascii=False))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["list"]:
        flags = a[1:]
        as_json = "--json" in flags
        flags = [f for f in flags if f != "--json"]
        try:
            rows = places(flags[1] if flags[:1] == ["--area"] and len(flags) > 1 else None)
        except (urllib.error.URLError, http.client.HTTPException) as e:
            sys.exit(f"ERROR: could not fetch menus: {e}")
        print(json.dumps(rows, ensure_ascii=False, indent=1) if as_json else render(rows))
    elif a[:1] in (["go"], ["undo"]) and len(a) > 1:
        visit(" ".join(a[1:]), 1 if a[0] == "go" else -1)
    else:
        sys.exit(__doc__)
