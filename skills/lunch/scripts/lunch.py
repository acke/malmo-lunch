#!/usr/bin/env python3
"""Malmö lunch: today's menus from menydags.se + mylunch.se, fixed-menu places, per-user visit counts. Stdlib only.

  lunch.py list [--area NAME] [--sort distance]
                                today's list as ready-to-print text, fetched live (--json: raw rows)
  lunch.py go NAME              record a visit to NAME
  lunch.py undo NAME            remove one recorded visit to NAME
  lunch.py lang [eng|swe]       show or set the list language (default eng)
  lunch.py location             show the office location distances are measured from
  lunch.py location set TEXT    set it from an address, or "LAT,LON"
  lunch.py geocode              look up coordinates for places not yet in the cache (1 request/s)
"""
import datetime
import gzip
import html
import http.client
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
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
CONFIG = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "malmo-lunch")
PREFS = os.path.join(CONFIG, "prefs.json")
LOCATION = os.path.join(CONFIG, "location.json")  # office the distances are measured from
GEO = os.path.join(CONFIG, "geo.json")  # geocode cache {normalized name: [lat, lon] | null}
OFFICE = {"name": "Neo4j Malmö (Anckargripsgatan 3)", "lat": 55.6113, "lon": 12.9944}  # default until `location set`
NOMINATIM = "https://nominatim.openstreetmap.org/search"
MALMO_BOX = "12.85,55.65,13.15,55.50"  # left,top,right,bottom: bounds geocoding so a name can't match another city

LANGS = ("eng", "swe")
TEXT = {
    "eng": {"today": "Today is {day} {date}, {n} places.", "fav": "★ Most visited", "fixed": "fixed menu",
            "ask": "Which number (or name) are you going to?",
            "none": "No lunch places found today (weekend or holiday?).",
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]},
    "swe": {"today": "Idag är det {day} {date}, {n} ställen.", "fav": "★ Mest besökta", "fixed": "fast meny",
            "ask": "Vilket nummer (eller namn) går du till?",
            "none": "Inga lunchställen hittades idag (helg eller helgdag?).",
            "days": ["mån", "tis", "ons", "tor", "fre", "lör", "sön"]},
}

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


def nordrest(page):
    """Lunch buffet: the dishes in the first (current week) block under today's weekday heading."""
    today = DAYS[datetime.date.today().weekday()]
    for day in re.findall(r'<section class="castit-day[^"]*">(.*?)</section>', page, re.S):
        if 'data-sv="%s"' % today in day[:400]:
            return [clean(d) for d in re.findall(r'class="castit-dish__title" data-sv="([^"]*)"', day)]
    return []


def kalhuvet(page):
    """Today's two dishes under the weekday <h4>, only while the page's "V.NN" label is the current ISO week (the menu is replaced weekly)."""
    today = datetime.date.today()
    week = re.search(r"V\.\s*(\d+)", clean(page))
    if not week or int(week.group(1)) != today.isocalendar()[1]:
        return []
    m = re.search(r"<h4[^>]*>\s*%s\s*</h4>(.*?)(?:<h4|$)" % DAYS[today.weekday()], page, re.S | re.I)
    return [clean(d).lstrip("- ") for d in re.findall(r"<p[^>]*>(.*?)</p>", m.group(1))] if m else []


def twoforks(page):
    """Lunch bowls (No. 1-3, the same all week, changed seasonally): Mon-Fri only, Saturday has no bowls."""
    if datetime.date.today().weekday() > 4:
        return []
    return [clean(d) for d in re.findall(r"<h2[^>]*>No\. \d+</h2><p[^>]*>(.*?)</p>", page)]


def rotation(r):
    """Weekly menus that repeat in order: today's dishes from menu `first` in the week of `start`, the next menu each week after."""
    today = datetime.date.today()
    if today.weekday() > 4:
        return []
    weeks = (today - datetime.date.fromisoformat(r["start"])).days // 7
    return r["menus"][(r["first"] - 1 + weeks) % len(r["menus"])][DAYS[today.weekday()]]


MENUS = {"clemens": clemens, "holygreens": holygreens, "p2": p2, "nordrest": nordrest, "kalhuvet": kalhuvet, "twoforks": twoforks}  # standing.json `menu.kind` -> parser


def standing():
    """Places outside the aggregators, from standing.json next to SKILL.md.

    Dishes come from a scraped `menu` page, a hand-kept `rotation` of weekly menus, else a hand-kept `dishes` list. `fixed` marks places
    with no daily lunch, so the skill can say the dishes are their regular menu.
    """
    with open(os.path.join(os.path.dirname(__file__), "..", "standing.json")) as f:
        entries = json.load(f)
    for s in entries:
        names = list(s.get("dishes", []))
        if "rotation" in s:
            names = rotation(s["rotation"]) or names
        if "menu" in s:
            try:
                names = MENUS[s["menu"]["kind"]](get(s["menu"]["url"])) or names
            except (urllib.error.URLError, http.client.HTTPException) as e:
                print(f"{s['name']} menu skipped: {e}", file=sys.stderr)
        dishes = [{"name": n, "desc": "", "price": ""} for n in names]
        yield {"slug": "standing-" + norm(s["name"]), "name": s["name"], "area": s["area"], "dishes": dishes,
               "summary": summarize(dishes) or s.get("note", ""), "standing": s.get("fixed", False)}


def read_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_prefs():
    return read_json(PREFS, {"visits": {}})


def save_prefs(p):
    write_json(PREFS, p)


def lang():
    return load_prefs().get("lang", LANGS[0])


def set_lang(value):
    p = load_prefs()
    p["lang"] = value
    save_prefs(p)


def office():
    return read_json(LOCATION, OFFICE)


def geocode_text(text, bounded):
    """First Nominatim hit for `text` as [lat, lon], or None. `bounded` limits it to the Malmö box."""
    q = {"format": "jsonv2", "limit": 1, "countrycodes": "se", "q": text}
    if bounded:
        q.update(viewbox=MALMO_BOX, bounded=1)
    hits = json.loads(get(f"{NOMINATIM}?{urllib.parse.urlencode(q)}"))
    return [float(hits[0]["lat"]), float(hits[0]["lon"])] if hits else None


def set_location(text):
    """Store the office as `LAT,LON`, or geocode `text` as an address."""
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*", text)
    point = [float(m.group(1)), float(m.group(2))] if m else geocode_text(text, bounded=False)
    if not point:
        sys.exit(f"ERROR: no match for {text!r}")
    loc = {"name": text, "lat": point[0], "lon": point[1]}
    write_json(LOCATION, loc)
    return loc


def metres(a, b):
    """Straight-line distance between two [lat, lon] points (haversine)."""
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def geocode_missing(rows):
    """Look up places absent from the cache, 1 request/s (Nominatim's limit). A miss is cached as null."""
    cache = read_json(GEO, {})
    todo = [r for r in rows if norm(r["name"]) not in cache]
    for i, r in enumerate(todo):
        if i:
            time.sleep(1.1)
        try:
            cache[norm(r["name"])] = geocode_text(f"{r['name']}, Malmö", bounded=True)
        except (urllib.error.URLError, http.client.HTTPException, ValueError) as e:
            print(f"geocode {r['name']} skipped: {e}", file=sys.stderr)
            continue
        write_json(GEO, cache)
    return len(todo), sum(1 for r in rows if cache.get(norm(r["name"])))


def short_distance(m):
    return f"{round(m, -1):.0f} m" if m < 1000 else f"{m / 1000:.1f} km"


def places(area, by_distance=False):
    """Fetch every source live, merge, and return today's rows, most-visited first. Menus are never cached.

    `distance_m` is the straight-line distance from the office, from coordinates cached by `geocode`; None if unknown.
    """
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
    cache, here = read_json(GEO, {}), office()
    for r in rows:
        r["visits"] = visits.get(norm(r["name"]), 0)
        point = cache.get(norm(r["name"]))
        r["distance_m"] = round(metres([here["lat"], here["lon"]], point)) if point else None
    top = sorted((r for r in rows if r["visits"]), key=lambda r: (-r["visits"], r["name"].lower()))[:TOP_N]
    for r in rows:
        r["fav"] = r in top
    far = float("inf")  # places without coordinates sort last
    rows.sort(key=lambda r: (top.index(r) if r["fav"] else TOP_N,
                             (r["distance_m"] if r["distance_m"] is not None else far) if by_distance else 0,
                             r["name"].lower()))
    return rows


def render(rows):
    """The finished list, ready to paste: most-visited group, then one group per area, continuous numbers."""
    t = TEXT[lang()]
    if not rows:
        return t["none"]
    today = datetime.date.today()
    out, n = [t["today"].format(day=t["days"][today.weekday()], date=today.isoformat(), n=len(rows))], 0

    def group(title, group_rows, counts=False):
        nonlocal n
        out.extend(["", f"**{title}**"])
        for r in group_rows:
            n += 1
            summary = r["summary"] if len(r["summary"]) <= 100 else r["summary"][:99] + "…"
            tag = (f" ({t['fixed']})" if r.get("standing") else "") + (f" ({r['visits']}×)" if counts else "")
            dist = f" · {short_distance(r['distance_m'])}" if r["distance_m"] is not None else ""
            out.append(f"{n}. {r['name']}{tag}{dist}: {summary}")

    if any(r["fav"] for r in rows):
        group(t["fav"], [r for r in rows if r["fav"]], counts=True)
    rest = [r for r in rows if not r["fav"]]
    for area in sorted({r["area"] for r in rest}):
        group(area, [r for r in rest if r["area"] == area])
    return "\n".join(out + ["", t["ask"]])


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
        by_distance = "--sort" in flags and flags[flags.index("--sort") + 1:][:1] == ["distance"]
        area = flags[flags.index("--area") + 1] if "--area" in flags[:-1] else None
        try:
            rows = places(area, by_distance)
        except (urllib.error.URLError, http.client.HTTPException) as e:
            sys.exit(f"ERROR: could not fetch menus: {e}")
        print(json.dumps(rows, ensure_ascii=False, indent=1) if as_json else render(rows))
    elif a[:1] in (["go"], ["undo"]) and len(a) > 1:
        visit(" ".join(a[1:]), 1 if a[0] == "go" else -1)
    elif a[:1] == ["lang"] and len(a) <= 2:
        if len(a) == 2:
            if a[1] not in LANGS:
                sys.exit(f"ERROR: language must be one of {', '.join(LANGS)}")
            set_lang(a[1])
        print(lang())
    elif a[:1] == ["location"] and (len(a) == 1 or a[1] == "set" and len(a) > 2):
        try:
            print(json.dumps(set_location(" ".join(a[2:])) if len(a) > 1 else office(), ensure_ascii=False))
        except (urllib.error.URLError, http.client.HTTPException, ValueError) as e:
            sys.exit(f"ERROR: could not look up location: {e}")
    elif a == ["geocode"]:
        try:
            asked, known = geocode_missing(places(None))
        except (urllib.error.URLError, http.client.HTTPException) as e:
            sys.exit(f"ERROR: could not fetch menus: {e}")
        print(json.dumps({"looked_up": asked, "with_coordinates": known}))
    else:
        sys.exit(__doc__)
