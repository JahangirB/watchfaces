#!/usr/bin/env python3
"""Render design previews for the Almanac concept (concepts/almanac/ALMANAC.md).

Almanac is a pocket almanac for the day: one fixed time and frame, plus a
"plate" that changes with the part of the day (morning brief, daytime next
change, evening tomorrow, night moon and first light), drawn as line engravings.

Writes previews/almanac/*.svg (466x466, OnePlus Watch 3 panel) and
previews/almanac/pins.json. Every text node carries data-role so
tools/almanac_audit.py can measure it.
"""
import itertools
import json
import math
from pathlib import Path

S, C = 466, 233
OUT = Path(__file__).resolve().parent.parent / "previews" / "almanac"

F_TIME = "Fraunces, Georgia, 'Times New Roman', serif"
F_TEXT = "Newsreader, Georgia, 'Times New Roman', serif"

PALETTE = {  # ink (text), accent; one tick colour for the scale
    "morning": {"ink": "#EFE7DA", "accent": "#F4B77E", "tick": "#6E675E"},
    "day":     {"ink": "#ECF0F4", "accent": "#8FC7FF", "tick": "#5E6670"},
    "evening": {"ink": "#ECE6F3", "accent": "#C6A8F5", "tick": "#665E72"},
    "night":   {"ink": "#D9483B", "accent": "#D9483B", "tick": "#5A1D18", "time": "#FF6B57"},
}

COND = ["UNKNOWN", "CLEAR", "CLOUDY", "FOG", "HEAVY_RAIN", "HEAVY_SNOW", "RAIN", "SNOW", "SUNNY",
        "THUNDERSTORM", "SLEET", "LIGHT_SNOW", "LIGHT_RAIN", "MIST", "PARTLY_CLOUDY", "WINDY"]

_ids = itertools.count()


def uid(p):
    return f"{p}{next(_ids)}"


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def pol(r, deg, cx=C, cy=C):
    a = math.radians(deg)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def text(x, y, s, size, fill, role, family=F_TEXT, weight=400, anchor="middle", extra=""):
    return (f'<text data-role="{role}" x="{f(x)}" y="{f(y)}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{s}</text>')


# ------------------------------------------------------------------ engraving primitives
SW = 1.7


def hatch(clip_id, x0, y0, x1, y1, gap, ink, angle=0, sw=1.1, op=1):
    lines = []
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    span = max(x1 - x0, y1 - y0) * 1.5
    k = -span
    while k <= span:
        lines.append(f'<line x1="{f(cx-span)}" y1="{f(cy+k)}" x2="{f(cx+span)}" y2="{f(cy+k)}"/>')
        k += gap
    return (f'<g clip-path="url(#{clip_id})"><g transform="rotate({angle} {f(cx)} {f(cy)})" stroke="{ink}" '
            f'stroke-width="{sw}" stroke-opacity="{op}">{"".join(lines)}</g></g>')


def sun(cx, cy, r, ink, p, hatched=True, rays=16):
    cid = uid(p + "c")
    g = [f'<clipPath id="{cid}"><circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}"/></clipPath>']
    if hatched:
        g.append(hatch(cid, cx - r, cy - r, cx + r, cy + r, 3.2, ink, angle=-30))
    g.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="none" stroke="{ink}" stroke-width="{SW}"/>')
    for i in range(rays):
        a = i * 360 / rays
        l = 10 if i % 2 == 0 else 6
        x0, y0 = pol(r + 4, a, cx, cy)
        x1, y1 = pol(r + 4 + l, a, cx, cy)
        g.append(f'<line x1="{f(x0)}" y1="{f(y0)}" x2="{f(x1)}" y2="{f(y1)}" stroke="{ink}" stroke-width="{SW}" stroke-linecap="round"/>')
    return "".join(g)


def moon_lit_path(cx, cy, r, ph):
    rx = r * abs(math.cos(2 * math.pi * ph))
    top, bot = f"{f(cx)} {f(cy-r)}", f"{f(cx)} {f(cy+r)}"
    if ph < 0.5:
        outer, sweep = f"M{top} A{f(r)} {f(r)} 0 0 1 {bot}", (0 if ph < 0.25 else 1)
    else:
        outer, sweep = f"M{top} A{f(r)} {f(r)} 0 0 0 {bot}", (1 if ph > 0.75 else 0)
    return f"{outer} A{f(rx)} {f(r)} 0 0 {sweep} {top} Z"


def moon(cx, cy, r, ink, p, phase=0.87):
    cid = uid(p + "m")
    return (f'<clipPath id="{cid}"><path d="{moon_lit_path(cx, cy, r, phase)}"/></clipPath>'
            + hatch(cid, cx - r, cy - r, cx + r, cy + r, 2.4, ink, angle=-20, sw=1.2)
            + f'<path d="{moon_lit_path(cx, cy, r, phase)}" fill="none" stroke="{ink}" stroke-width="{SW}"/>'
            + f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="none" stroke="{ink}" stroke-width="1" stroke-dasharray="1.5 3"/>')


def star(x, y, s, ink):
    return (f'<path d="M{f(x)} {f(y-s)} L{f(x+s*.25)} {f(y-s*.25)} L{f(x+s)} {f(y)} L{f(x+s*.25)} {f(y+s*.25)} '
            f'L{f(x)} {f(y+s)} L{f(x-s*.25)} {f(y+s*.25)} L{f(x-s)} {f(y)} L{f(x-s*.25)} {f(y-s*.25)} Z" fill="{ink}"/>')


def cloud(cx, cy, w, ink, p, dark=False):
    """Outline of a union of circles, with engraved hatching under the belly."""
    k = w / 60
    parts = [(-16, 4, 13), (2, -6, 18), (19, 3, 13)]
    circles = [(cx + dx * k, cy + dy * k, r * k) for dx, dy, r in parts]
    base = (cx - 29 * k, cy + 4 * k, 58 * k, 13 * k)
    cid = uid(p + "k")
    shapes = "".join(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}"/>' for x, y, r in circles)
    rect = f'<rect x="{f(base[0])}" y="{f(base[1])}" width="{f(base[2])}" height="{f(base[3])}" rx="{f(6*k)}"/>'
    g = [f'<clipPath id="{cid}">{shapes}{rect}</clipPath>']
    # outline trick: thick ink stroke, then black fill on top leaves only the outer edge
    g.append(f'<g fill="none" stroke="{ink}" stroke-width="{SW*2}">{shapes}{rect}</g>')
    g.append(f'<g fill="#000">{shapes}{rect}</g>')
    top = cy - (12 if dark else 1) * k
    g.append(f'<g clip-path="url(#{cid})">' + hatch(cid, cx - 32 * k, top, cx + 32 * k, cy + 18 * k,
                                                     2.4 if dark else 3.4, ink, angle=0).replace(f'clip-path="url(#{cid})"', "", 1)
             .replace(f'<g ><g', '<g><g') + "</g>")
    # mask hatching to the lower part only
    return "".join(g)


def drops(cx, y0, n, ink, length=10, spread=50, seed=0):
    out = []
    for i in range(n):
        x = cx - spread / 2 + (i + 0.5) * spread / n
        yy = y0 + (6 if (i + seed) % 2 else 0)
        out.append(f'<line x1="{f(x)}" y1="{f(yy)}" x2="{f(x-3)}" y2="{f(yy+length)}" stroke="{ink}" stroke-width="{SW}" stroke-linecap="round"/>')
    return "".join(out)


def flakes(cx, y0, n, ink, spread=50, seed=0, size=3.6):
    out = []
    for i in range(n):
        x = cx - spread / 2 + (i + 0.5) * spread / n
        yy = y0 + (8 if (i + seed) % 2 else 0) + (i % 3) * 2
        for a in (0, 60, 120):
            x0, y0_ = pol(size, a, x, yy)
            x1, y1 = pol(size, a + 180, x, yy)
            out.append(f'<line x1="{f(x0)}" y1="{f(y0_)}" x2="{f(x1)}" y2="{f(y1)}" stroke="{ink}" stroke-width="1.3" stroke-linecap="round"/>')
    return "".join(out)


def waves(cx, cy, w, n, ink, dashed=False, gap=9):
    out = []
    for i in range(n):
        y = cy + i * gap
        off = 6 if i % 2 else 0
        x0, x1 = cx - w / 2 + off, cx + w / 2 - (6 - off)
        segs = 4
        d = f"M{f(x0)} {f(y)}"
        step = (x1 - x0) / segs
        for s in range(segs):
            d += f" q{f(step/2)} {-3 if s % 2 else 3} {f(step)} 0"
        dash = ' stroke-dasharray="2 5"' if dashed else ""
        out.append(f'<path d="{d}" fill="none" stroke="{ink}" stroke-width="{SW}" stroke-linecap="round"{dash}/>')
    return "".join(out)


def wind(cx, cy, ink):
    out = []
    for i, (w, dy) in enumerate([(54, -14), (64, 0), (44, 14)]):
        x0 = cx - 32
        y = cy + dy
        r = 6
        d = f"M{f(x0)} {f(y)} L{f(x0+w)} {f(y)} a{r} {r} 0 1 0 {-r} {-r}"
        out.append(f'<path d="{d}" fill="none" stroke="{ink}" stroke-width="{SW}" stroke-linecap="round"/>')
    return "".join(out)


def bolt(cx, cy, ink, p):
    d = (f"M{f(cx+4)} {f(cy)} L{f(cx-8)} {f(cy+16)} L{f(cx)} {f(cy+16)} L{f(cx-5)} {f(cy+30)} "
         f"L{f(cx+10)} {f(cy+11)} L{f(cx+2)} {f(cy+11)} L{f(cx+8)} {f(cy)} Z")
    cid = uid(p + "b")
    return (f'<clipPath id="{cid}"><path d="{d}"/></clipPath>' + hatch(cid, cx - 10, cy, cx + 12, cy + 30, 2.2, ink, angle=40)
            + f'<path d="{d}" fill="none" stroke="{ink}" stroke-width="{SW}" stroke-linejoin="round"/>')


def glyph(code, x, y, ink, p, night=False, box=80):
    """Engraved weather glyph for WEATHER.CONDITION `code`, inside a box at (x, y)."""
    cx, cy = x + box / 2, y + box / 2
    name = COND[code]
    g = []
    if name == "UNKNOWN":
        g.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="22" fill="none" stroke="{ink}" stroke-width="{SW}" stroke-dasharray="3 5"/>')
        g.append(f'<line x1="{f(cx-8)}" y1="{f(cy)}" x2="{f(cx+8)}" y2="{f(cy)}" stroke="{ink}" stroke-width="{SW}" stroke-linecap="round"/>')
    elif name in ("SUNNY", "CLEAR"):
        if night:
            g.append(moon(cx - 4, cy, 18, ink, p))
            g.append(star(cx + 22, cy - 18, 5, ink) + star(cx + 26, cy + 10, 3.5, ink) + star(cx - 26, cy - 22, 3, ink))
        elif name == "SUNNY":
            g.append(sun(cx, cy, 15, ink, p, hatched=True))
        else:
            g.append(sun(cx, cy, 15, ink, p, hatched=False, rays=8))
    elif name == "PARTLY_CLOUDY":
        if night:
            g.append(moon(cx - 10, cy - 10, 13, ink, p))
        else:
            g.append(sun(cx - 10, cy - 12, 11, ink, p, hatched=True, rays=12))
        g.append(cloud(cx + 6, cy + 8, 52, ink, p))
    elif name == "CLOUDY":
        g.append(cloud(cx - 10, cy - 10, 40, ink, p))
        g.append(cloud(cx + 6, cy + 6, 58, ink, p))
    elif name in ("LIGHT_RAIN", "RAIN", "HEAVY_RAIN", "THUNDERSTORM", "SLEET",
                  "LIGHT_SNOW", "SNOW", "HEAVY_SNOW"):
        heavy = name in ("HEAVY_RAIN", "THUNDERSTORM", "HEAVY_SNOW")
        g.append(cloud(cx, cy - 12, 62, ink, p, dark=heavy))
        top = cy + 10
        if name == "LIGHT_RAIN":
            g.append(drops(cx, top, 3, ink, 9))
        elif name == "RAIN":
            g.append(drops(cx, top, 5, ink, 12))
        elif name == "HEAVY_RAIN":
            g.append(drops(cx, top, 8, ink, 16, spread=58))
        elif name == "THUNDERSTORM":
            g.append(drops(cx - 14, top, 3, ink, 12, spread=24))
            g.append(bolt(cx + 10, top - 2, ink, p))
        elif name == "SLEET":
            g.append(drops(cx - 12, top, 3, ink, 12, spread=30))
            g.append(flakes(cx + 15, top + 4, 2, ink, spread=22))
        elif name == "LIGHT_SNOW":
            g.append(flakes(cx, top + 4, 3, ink))
        elif name == "SNOW":
            g.append(flakes(cx, top + 4, 5, ink, spread=56))
        elif name == "HEAVY_SNOW":
            g.append(flakes(cx, top + 4, 7, ink, spread=60))
            g.append(f'<path d="M{f(cx-34)} {f(cy+38)} q17 -7 34 -2 t34 -2" fill="none" stroke="{ink}" stroke-width="{SW}" stroke-linecap="round"/>')
    elif name == "FOG":
        g.append(waves(cx, cy - 13, 64, 4, ink))
    elif name == "MIST":
        g.append(waves(cx, cy - 9, 60, 3, ink, dashed=True, gap=10))
    elif name == "WINDY":
        g.append(wind(cx, cy, ink))
    return f'<g data-role="glyph" data-cond="{name}">{"".join(g)}</g>'


# ------------------------------------------------------------------ face
def scale_ring(pal, hh, mm, is_day, p, stale=False, unknown=False):
    """24 h almanac scale: noon at top, midnight at bottom. Night hours in the
    next 12 h are engraved with radial hatching; past hours are left plain."""
    g = []
    now = hh + mm / 60
    ang = lambda h: (h - 12) * 15
    tick = pal["tick"]
    for h in range(24):
        a = ang(h)
        major = h % 6 == 0
        x0, y0 = pol(226, a)
        x1, y1 = pol(226 - (10 if major else 5), a)
        g.append(f'<line x1="{f(x0)}" y1="{f(y0)}" x2="{f(x1)}" y2="{f(y1)}" stroke="{tick}" '
                 f'stroke-width="{2 if major else 1.2}" stroke-linecap="round"/>')
    if not unknown:
        op = 0.35 if stale else 0.85
        for n, d in enumerate(is_day):
            if d:
                continue
            h0 = max(now, math.floor(now) + n)
            h1 = math.floor(now) + n + 1
            a = ang(h0)
            while a < ang(h1) - 0.01:
                x0, y0 = pol(213, a)
                x1, y1 = pol(219, a)
                g.append(f'<line x1="{f(x0)}" y1="{f(y0)}" x2="{f(x1)}" y2="{f(y1)}" stroke="{pal["accent"]}" '
                         f'stroke-opacity="{op}" stroke-width="1.1"/>')
                a += 2.2
    # now marker
    a = ang(now)
    tip = pol(221, a)
    bl, br = pol(208, a - 3), pol(208, a + 3)
    g.append(f'<path d="M{f(tip[0])} {f(tip[1])} L{f(bl[0])} {f(bl[1])} L{f(br[0])} {f(br[1])} Z" fill="{pal["accent"]}"/>')
    return f'<g data-role="decor">{"".join(g)}</g>'


def label_arc(s, pal, p):
    pid = uid(p + "arc")
    r = 176
    x0, y0 = pol(r, -80)
    x1, y1 = pol(r, 80)
    return (f'<path id="{pid}" d="M{f(x0)} {f(y0)} A{r} {r} 0 0 1 {f(x1)} {f(y1)}" fill="none"/>'
            f'<text data-role="label" font-family="{F_TEXT}" font-size="24" font-weight="500" fill="{pal["ink"]}" '
            f'letter-spacing="2"><textPath href="#{pid}" startOffset="50%" text-anchor="middle">{s}</textPath></text>')


TIME_Y, TIME_SIZE = 210, 120
GX, GY = 82, 250       # glyph box
TX = 178               # text column
LA_Y, LB_Y = 279, 317
COMP = (233, 386, 48)


def time_text(s, pal, outline=False):
    style = 'style="font-variant-numeric: tabular-nums"'
    if outline:
        return text(C, TIME_Y, s, TIME_SIZE, "none", "time", F_TIME, 300,
                    extra=f'{style} stroke="{pal["ink"]}" stroke-width="1.6" letter-spacing="-2"')
    return text(C, TIME_Y, s, TIME_SIZE, pal.get("time", pal["ink"]), "time", F_TIME, 300, extra=f'{style} letter-spacing="-2"')


def complication(kind, value, pal):
    cx, cy, r = COMP
    ink = pal["ink"]
    g = [f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#000" stroke="{pal["tick"]}" stroke-width="1.5"/>']
    iy = cy - 20
    if kind == "steps":
        # two footprints: sole + heel + toe dots, staggered
        fp = ""
        for dx, dy, flip in ((-7, 3, -1), (7, -3, 1)):
            x, y = cx + dx, iy + dy
            fp += (f'<path d="M{x-3.2} {y-1} q0 -6 3.2 -6 q3.2 0 3.2 6 q0 4 -3.2 4 q-3.2 0 -3.2 -4 z"/>'
                   f'<path d="M{x-2.6} {y+5} h5.2 v1.5 q0 2.6 -2.6 2.6 q-2.6 0 -2.6 -2.6 z"/>')
        g.append(f'<g fill="{ink}" transform="translate({cx} {iy}) scale(1.45) translate({-cx} {-iy}) rotate(-8 {cx} {iy})">{fp}</g>')
    elif kind == "alarm":
        g.append(f'<g fill="none" stroke="{ink}" stroke-width="1.6" stroke-linecap="round">'
                 f'<path d="M{cx-8} {iy+6} q0 -14 8 -14 q8 0 8 14 l3 3 h-22 z"/><line x1="{cx-2}" y1="{iy+12}" x2="{cx+2}" y2="{iy+12}"/></g>')
    g.append(text(cx, cy + 22, value, 24, ink, "complication", F_TEXT, 500))
    return f'<g data-role="complication-box">{"".join(g)}</g>'


def face(sc, aod=False):
    pal = PALETTE[sc["part"]]
    p = sc["key"] + ("a" if aod else "") + "_"
    night = sc["part"] == "night"
    body = [f'<rect width="{S}" height="{S}" fill="#000"/>']
    if aod:
        body.append(time_text(sc["time"], pal, outline=True))
        body.append(f'<g opacity="0.7">{glyph(sc["glyph"], GX, GY, pal["accent"], p, night=sc.get("glyph_night", False))}</g>'
                    if sc["glyph"] is not None else "")
        if sc.get("moon"):
            body.append(f'<g data-role="glyph" opacity="0.7">{moon(GX+40, GY+40, 26, pal["accent"], p, sc["moon"])}</g>')
        body.append(text(TX, LA_Y, sc["a"], 24, pal["accent"], "line-a", F_TEXT, 500, "start", 'font-style="italic"'))
    else:
        body.append(scale_ring(pal, sc["hh"], sc["mm"], sc["is_day"], p, stale=sc.get("stale", False),
                               unknown=sc.get("unknown", False)))
        body.append(label_arc(sc["label"], pal, p))
        body.append(time_text(sc["time"], pal))
        if sc.get("moon"):
            body.append(f'<g data-role="glyph">{moon(GX+40, GY+40, 26, pal["accent"], p, sc["moon"])}</g>')
        else:
            body.append(glyph(sc["glyph"], GX, GY, pal["accent"], p, night=sc.get("glyph_night", False)))
        body.append(text(TX, LA_Y, sc["a"], 24, pal["accent"], "line-a", F_TEXT, 500, "start", 'font-style="italic"'))
        body.append(text(TX, LB_Y, sc["b"], 24, pal["ink"], "line-b", F_TEXT, 400, "start"))
        body.append(complication(*sc["comp"], pal))
    clip = uid(p + "round")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}" height="{S}" data-state="{sc["key"]}{"-aod" if aod else ""}">'
            f'<defs><clipPath id="{clip}"><circle cx="{C}" cy="{C}" r="{C}"/></clipPath></defs>'
            f'<g clip-path="url(#{clip})">{"".join(body)}</g></svg>\n')


C_ = {n: i for i, n in enumerate(COND)}
SCENES = [
    dict(key="morning", part="morning", hh=7, mm=42, time="07:42", label="MORNING · THU 6 NOV",
         is_day=[1] * 10 + [0, 0], glyph=C_["PARTLY_CLOUDY"], a="Rain from 16:00", b="High 16° · low 8°",
         comp=("steps", "320")),
    dict(key="day", part="day", hh=13, mm=20, time="13:20", label="DAY · THU 6 NOV",
         is_day=[1] * 4 + [0] * 8, glyph=C_["RAIN"], a="Rain from 16:00", b="+640 steps ahead",
         comp=("steps", "2,840")),
    dict(key="evening", part="evening", hh=19, mm=5, time="19:05", label="EVENING · THU 6 NOV",
         is_day=[0] * 12, glyph=C_["WINDY"], a="Tomorrow: Windy", b="High 13° · rain 20%",
         comp=("steps", "9,412")),
    dict(key="night", part="night", hh=23, mm=30, time="23:30", label="NIGHT · THU 6 NOV",
         is_day=[0] * 8 + [1] * 4, glyph=None, moon=0.884, a="Morning crescent", b="Light at 07:00",
         comp=("alarm", "06:45")),
    dict(key="nodata", part="day", hh=13, mm=20, time="13:20", label="DAY · THU 6 NOV",
         is_day=[1] * 12, unknown=True, glyph=C_["UNKNOWN"], a="No forecast yet", b="Check connection",
         comp=("steps", "2,840")),
    dict(key="stale", part="day", hh=13, mm=20, time="13:20", label="DAY · THU 6 NOV",
         is_day=[1] * 4 + [0] * 8, stale=True, glyph=C_["RAIN"], a="Rain from 16:00", b="Forecast 6 h old",
         comp=("steps", "2,840")),
    dict(key="error", part="day", hh=13, mm=20, time="13:20", label="DAY · THU 6 NOV",
         is_day=[1] * 4 + [0] * 8, stale=True, glyph=C_["RAIN"], a="Rain from 16:00", b="Last update failed",
         comp=("steps", "2,840")),
]
AOD_FOR = ["morning", "day", "evening", "night"]


def glyph_sheet():
    """One SVG per condition (plus night variants), for coverage checks and the gallery."""
    out = {}
    for code, name in enumerate(COND):
        variants = [("day", False)] + ([("night", True)] if name in ("CLEAR", "PARTLY_CLOUDY", "SUNNY") else [])
        for tag, night in variants:
            if name == "SUNNY" and night:
                continue
            p = f"g{code}{tag[0]}_"
            ink = PALETTE["night" if night else "day"]["accent"] if not night else "#C6A8F5"
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" width="96" height="96">'
                   f'<rect width="96" height="96" fill="#000"/>{glyph(code, 8, 8, ink, p, night=night)}</svg>\n')
            out[f"glyph-{name.lower()}{'-night' if night else ''}.svg"] = svg
    return out


def pins():
    pct = lambda x, y: [round(x / S * 100, 1), round(y / S * 100, 1)]
    return {
        "1": pct(*pol(190, 52)),            # daypart label
        "2": pct(C + 168, 160),             # time
        "3": pct(*pol(216, 112)),           # 24h scale, night hatching
        "4": pct(*pol(196, (7.7 - 12) * 15 - 9)),  # now marker
        "5": pct(GX - 6, GY + 6),           # glyph
        "6": pct(415, LA_Y - 8),            # line A
        "7": pct(415, LB_Y - 8),            # line B
        "8": pct(COMP[0] + 52, COMP[1] + 30),  # complication
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    for sc in SCENES:
        (OUT / f"{sc['key']}.svg").write_text(face(sc))
        if sc["key"] in AOD_FOR:
            (OUT / f"{sc['key']}-aod.svg").write_text(face(sc, aod=True))
    for name, svg in glyph_sheet().items():
        (OUT / name).write_text(svg)
    (OUT / "pins.json").write_text(json.dumps(pins(), indent=1) + "\n")
    print(f"wrote {len(list(OUT.glob('*.svg')))} svgs to {OUT}")


if __name__ == "__main__":
    main()
