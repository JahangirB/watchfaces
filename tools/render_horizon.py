#!/usr/bin/env python3
"""Render design previews for the flagship concept "Horizon" (see concepts/HORIZON.md).

Writes previews/horizon.svg and previews/horizon-aod.svg at 466x466.
Sample moment: Thu 06 Nov, 10:08, with a made-up 12-hour forecast.
"""
import math
from pathlib import Path

S, C = 466, 233
OUT = Path(__file__).resolve().parent.parent / "previews"
HH, MM = 10, 8
HOUR_ANG = (HH % 12 + MM / 60) * 30

# hour, temp C, rain chance %, condition, is_day
FORECAST = [
    (10, 12, 0, "sun", 1), (11, 14, 0, "sun", 1), (12, 15, 0, "sun", 1), (13, 16, 5, "partly", 1),
    (14, 16, 10, "partly", 1), (15, 15, 30, "cloud", 1), (16, 13, 60, "rain", 1), (17, 11, 80, "rain", 0),
    (18, 10, 70, "rain", 0), (19, 9, 20, "cloud", 0), (20, 8, 0, "moon", 0), (21, 8, 0, "moon", 0),
]
TMIN, TMAX = 8, 16
STEPS, GOAL = 2840, 10000
PACE = ((HH - 7) * 60 + MM) / (15 * 60)   # expected share of goal, waking day 07:00-22:00
HR, BATT = 72, 64

F_UI = "Barlow, 'Helvetica Neue', Arial, sans-serif"
F_THIN = "Outfit, 'Helvetica Neue', Arial, sans-serif"
F_MONO = "'JetBrains Mono', Menlo, Consolas, monospace"


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def pol(r, deg, cx=C, cy=C):
    a = math.radians(deg)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def arc(r, a0, a1):
    x0, y0 = pol(r, a0)
    x1, y1 = pol(r, a1)
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M{f(x0)} {f(y0)} A{f(r)} {f(r)} 0 {large} 1 {f(x1)} {f(y1)}"


def sector(r0, r1, a0, a1):
    x0, y0 = pol(r1, a0)
    x1, y1 = pol(r1, a1)
    x2, y2 = pol(r0, a1)
    x3, y3 = pol(r0, a0)
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return (f"M{f(x0)} {f(y0)} A{r1} {r1} 0 {large} 1 {f(x1)} {f(y1)} "
            f"L{f(x2)} {f(y2)} A{r0} {r0} 0 {large} 0 {f(x3)} {f(y3)} Z")


def lerp(a, b, t):
    return a + (b - a) * t


def temp_color(t):
    stops = [(8, (79, 168, 255)), (12, (255, 209, 102)), (16, (255, 122, 61))]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            k = max(0, (t - t0) / (t1 - t0))
            return "#%02x%02x%02x" % tuple(round(lerp(a, b, k)) for a, b in zip(c0, c1))
    return "#%02x%02x%02x" % stops[-1][1]


def text(x, y, s, size, fill, family=F_UI, weight=500, anchor="middle", extra=""):
    return (f'<text x="{f(x)}" y="{f(y)}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" {extra}>{s}</text>')


def icon(kind, x, y, s=1.0):
    g = []
    if kind in ("sun", "partly"):
        sx, sy = (x - 4 * s, y - 3 * s) if kind == "partly" else (x, y)
        g.append(f'<circle cx="{f(sx)}" cy="{f(sy)}" r="{f(5*s)}" fill="#FFD166"/>')
        for k in range(8):
            a = k * 45
            x0, y0 = pol(7.5 * s, a, sx, sy)
            x1, y1 = pol(10 * s, a, sx, sy)
            g.append(f'<line x1="{f(x0)}" y1="{f(y0)}" x2="{f(x1)}" y2="{f(y1)}" stroke="#FFD166" stroke-width="{f(1.6*s)}" stroke-linecap="round"/>')
    if kind in ("cloud", "partly", "rain"):
        cy = y + (2 * s if kind == "partly" else 0)
        cx = x + (2 * s if kind == "partly" else 0)
        col = "#C9D3E3" if kind != "rain" else "#9FB3CC"
        g.append(f'<g fill="{col}"><circle cx="{f(cx-4*s)}" cy="{f(cy+1*s)}" r="{f(4.5*s)}"/>'
                 f'<circle cx="{f(cx+2*s)}" cy="{f(cy-2*s)}" r="{f(6*s)}"/>'
                 f'<rect x="{f(cx-8*s)}" y="{f(cy)}" width="{f(16*s)}" height="{f(5.5*s)}" rx="{f(2.7*s)}"/></g>')
    if kind == "rain":
        for dx in (-5, 0, 5):
            g.append(f'<line x1="{f(x+dx*s)}" y1="{f(y+8*s)}" x2="{f(x+(dx-2)*s)}" y2="{f(y+13*s)}" '
                     f'stroke="#5AB4FF" stroke-width="{f(1.8*s)}" stroke-linecap="round"/>')
    if kind == "moon":
        g.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(6.5*s)}" fill="#DCE3F2"/>'
                 f'<circle cx="{f(x+3.5*s)}" cy="{f(y-2.5*s)}" r="{f(5.5*s)}" fill="#0A1326"/>')
    return "".join(g)


R_IN = 190          # forecast band base radius
R_SPAN = (200, 226)  # outer radius range mapped from TMIN..TMAX
R_PACE = 124


def band_r(t):
    return lerp(R_SPAN[0], R_SPAN[1], (t - TMIN) / (TMAX - TMIN))


def render(aod):
    p = "hzaod_" if aod else "hz_"
    d = [f'<clipPath id="{p}round"><circle cx="{C}" cy="{C}" r="{C}"/></clipPath>']
    s = []
    if not aod:
        d.append(f'<radialGradient id="{p}sky" cx="50%" cy="100%" r="100%">'
                 f'<stop offset="0" stop-color="#16345C"/><stop offset="0.55" stop-color="#0A1326"/>'
                 f'<stop offset="1" stop-color="#05080F"/></radialGradient>')
        d.append(f'<pattern id="{p}rain" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(30)">'
                 f'<rect width="2.2" height="6" fill="#5AB4FF"/></pattern>')
        d.append(f'<filter id="{p}glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/>'
                 f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
        s.append(f'<rect width="{S}" height="{S}" fill="url(#{p}sky)"/>')
    else:
        s.append(f'<rect width="{S}" height="{S}" fill="#000"/>')

    # ---- forecast band: one segment per hour, sitting at that hour's clock position
    for h, t, rain, cond, day in FORECAST:
        a = (h % 12) * 30
        a0, a1 = a - 14, a + 14
        ro = band_r(t)
        col = temp_color(t)
        if aod:
            s.append(f'<path d="{arc(ro, a0, a1)}" fill="none" stroke="{col}" stroke-opacity="0.75" stroke-width="2.5" stroke-linecap="round"/>')
            if rain >= 50:
                s.append(f'<path d="{arc(R_IN - 6, a0, a1)}" fill="none" stroke="#5AB4FF" stroke-opacity="0.7" '
                         f'stroke-width="2" stroke-dasharray="2 4"/>')
            continue
        s.append(f'<path d="{sector(R_IN, ro, a0, a1)}" fill="{col}" fill-opacity="{0.95 if day else 0.6}"/>')
        if rain:
            s.append(f'<path d="{sector(R_IN, ro, a0, a1)}" fill="url(#{p}rain)" fill-opacity="{f(min(1, rain/80))}"/>')
        # daylight track under each segment
        s.append(f'<path d="{arc(R_IN - 6, a0, a1)}" fill="none" stroke="{"#FFD166" if day else "#3D4E7A"}" '
                 f'stroke-width="2.5" stroke-linecap="round"/>')
        if h == HH:  # current hour: outlined, and the pointer takes the icon's place
            s.append(f'<path d="{sector(R_IN, ro, a0, a1)}" fill="none" stroke="#FFFFFF" stroke-width="2"/>')
            continue
        ix, iy = pol(167, a)
        s.append(icon(cond, ix, iy, 0.95))

    # temperature labels at high / now / low
    if not aod:
        for h, label in [(10, "12°"), (13, "16°"), (17, "11°"), (20, "8°")]:
            t = next(x[1] for x in FORECAST if x[0] == h)
            x, y = pol(144, (h % 12) * 30)
            s.append(text(x, y + 5, label, 13, temp_color(t), weight=700))

    # seam where "now" meets "+12h"
    seam = (HH % 12) * 30 - 15
    x0, y0 = pol(R_IN - 10, seam)
    x1, y1 = pol(232, seam)
    s.append(f'<line x1="{f(x0)}" y1="{f(y0)}" x2="{f(x1)}" y2="{f(y1)}" stroke="#FFFFFF" '
             f'stroke-opacity="{0.5 if not aod else 0.35}" stroke-width="1.5" stroke-dasharray="3 3"/>')

    # now pointer (the hour hand), tip touching the band
    tip = pol(R_IN - 9, HOUR_ANG)  # sits where the current-hour icon would be
    bl = pol(R_IN - 24, HOUR_ANG - 3.2)
    br = pol(R_IN - 24, HOUR_ANG + 3.2)
    ptr = f"M{f(tip[0])} {f(tip[1])} L{f(bl[0])} {f(bl[1])} L{f(br[0])} {f(br[1])} Z"
    s.append(f'<path d="{ptr}" fill="{"#FFFFFF" if not aod else "none"}" stroke="#FFFFFF" stroke-width="1.5" stroke-linejoin="round"/>')

    # ---- step pace ring with ghost marker
    prog = STEPS / GOAL
    if not aod:
        s.append(f'<circle cx="{C}" cy="{C}" r="{R_PACE}" fill="none" stroke="#FFFFFF" stroke-opacity="0.1" stroke-width="6"/>')
        s.append(f'<path d="{arc(R_PACE, 0, 360*prog)}" fill="none" stroke="#7CE0A3" stroke-width="6" stroke-linecap="round"/>')
        gx, gy = pol(R_PACE, 360 * PACE)
        s.append(f'<circle cx="{f(gx)}" cy="{f(gy)}" r="6" fill="#0A1326" stroke="#FFFFFF" stroke-width="2"/>')
        ex, ey = pol(R_PACE, 360 * prog)
        s.append(f'<circle cx="{f(ex)}" cy="{f(ey)}" r="5" fill="#7CE0A3" filter="url(#{p}glow)"/>')

    # ---- centre
    tc = "#FFFFFF" if not aod else "#D0D0D0"
    if not aod:
        s.append(text(C, 172, "THU 06 NOV", 14, "#8FA3C4", weight=600, extra='letter-spacing="3"'))
    s.append(text(C, 252, f"{HH:02d}:{MM:02d}", 82, tc if not aod else "none", F_THIN, 300 if not aod else 200,
                  extra='letter-spacing="-2"' + ('' if not aod else ' stroke="#D0D0D0" stroke-width="1.5"')))
    # rain countdown line (computed from the hourly forecast)
    rc = "#5AB4FF" if not aod else "#3F7FB5"
    s.append(icon("rain", C - 74, 274, 0.75) if not aod else "")
    s.append(text(C - 58 if not aod else C, 287, "Rain at 16:00 · 60%", 16, rc, weight=600,
                  anchor="start" if not aod else "middle"))
    if not aod:
        hrcol = "#7CE0A3"  # zone 1 colour
        s.append(f'<path transform="translate({C-70} 304) scale(0.75)" d="M10 18 C-6 6 2 -4 10 3 C18 -4 26 6 10 18 Z" fill="{hrcol}"/>')
        s.append(text(C - 54, 318, f"{HR}", 16, "#E6ECF5", weight=600, anchor="start"))
        s.append(text(C - 4, 318, "2,840", 16, "#E6ECF5", weight=600, anchor="start"))
        s.append(text(C + 42, 318, "+640", 12, "#7CE0A3", weight=700, anchor="start"))

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}" height="{S}">'
            f'<defs>{"".join(d)}</defs><g clip-path="url(#{p}round)">{"".join(s)}</g></svg>\n')


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "horizon.svg").write_text(render(False))
    (OUT / "horizon-aod.svg").write_text(render(True))
    print("wrote horizon previews")


if __name__ == "__main__":
    main()
