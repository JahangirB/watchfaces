#!/usr/bin/env python3
"""Render design previews for the flagship concept "Horizon" (see concepts/HORIZON.md).

Horizon wraps a 12-hour weather landscape around the dial: terrain height is
temperature, the sky above it is day or night, clouds and rain sit where the
forecast puts them, and the sun itself is the hour hand.

Writes (466 x 466, the OnePlus Watch 3 panel):
  previews/horizon.svg        active mode
  previews/horizon-scrub.svg  tilt-to-scrub state, cursor on 17:00
  previews/horizon-aod.svg    always-on mode
and previews/horizon-pins.json (anatomy pin positions for the concept page).

Sample moment: Thu 06 Nov, 10:08, with a made-up forecast.
"""
import json
import math
import random
from pathlib import Path

S, C = 466, 233
OUT = Path(__file__).resolve().parent.parent / "previews"
HH, MM = 10, 8
NOW_U = MM / 60                       # fractional offset of "now" inside hour 0
BASE_ANG = (HH % 12) * 30             # clock angle of offset 0

# offset n -> (hour, temp C, rain chance %, condition, feels-like, uv)
FORECAST = [
    (10, 12, 0, "clear", 11, 2), (11, 14, 0, "clear", 13, 3), (12, 15, 0, "clear", 15, 3),
    (13, 16, 5, "few", 16, 3), (14, 16, 10, "few", 15, 2), (15, 15, 30, "cloud", 14, 1),
    (16, 13, 60, "rain", 11, 0), (17, 11, 80, "rain", 8, 0), (18, 10, 70, "rain", 7, 0),
    (19, 9, 20, "cloud", 7, 0), (20, 8, 0, "clear", 6, 0), (21, 8, 0, "clear", 6, 0),
]
SUNSET_U = (17 * 60 + 2 - HH * 60) / 60   # offset where the sun sets (17:02)
TMIN, TMAX = 8, 16
STEPS, GOAL = 2840, 10000
PACE = ((HH - 7) * 60 + MM) / (15 * 60)
HR = 72
MOON_PHASE = 0.884

R_BASE = 176                 # terrain base (ground line)
R_TOP = (184, 221)           # terrain crest range, TMIN..TMAX
R_PACE = 124

F_UI = "Barlow, 'Helvetica Neue', Arial, sans-serif"
F_THIN = "Outfit, 'Helvetica Neue', Arial, sans-serif"


# ---------------------------------------------------------------- maths
def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def pol(r, deg, cx=C, cy=C):
    a = math.radians(deg)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def ang(u):
    return BASE_ANG + u * 30


def catmull(vals, u):
    i = math.floor(u)
    t = u - i
    g = lambda k: vals[max(0, min(len(vals) - 1, k))]
    p0, p1, p2, p3 = g(i - 1), g(i), g(i + 1), g(i + 2)
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)


TEMPS = [x[1] for x in FORECAST]


def temp_at(u):
    return catmull(TEMPS, u)


def crest(u):
    return lerp(R_TOP[0], R_TOP[1], (temp_at(u) - TMIN) / (TMAX - TMIN))


def night(u):
    return smooth(SUNSET_U - 0.5, SUNSET_U + 0.6, u)


def mix(c0, c1, t):
    a = [int(c0[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(lerp(x, y, t)) for x, y in zip(a, b))


def temp_color(t):
    stops = [(8, "#3E8EF0"), (11, "#5FC7C0"), (13, "#F2C65C"), (16, "#FF7A3D")]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            return mix(c0, c1, max(0, (t - t0) / (t1 - t0)))
    return stops[-1][1]


def sky_color(u):
    day, dusk, nt = "#2D5F93", "#7A4A86", "#0B1430"
    n = night(u)
    d = smooth(SUNSET_U - 1.6, SUNSET_U - 0.2, u) * (1 - smooth(SUNSET_U + 0.2, SUNSET_U + 1.4, u))
    base = mix(day, nt, n)
    return mix(base, dusk, d * 0.85)


def sector(r0, r1, a0, a1):
    x0, y0 = pol(r1, a0)
    x1, y1 = pol(r1, a1)
    x2, y2 = pol(r0, a1)
    x3, y3 = pol(r0, a0)
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return (f"M{f(x0)} {f(y0)} A{f(r1)} {f(r1)} 0 {large} 1 {f(x1)} {f(y1)} "
            f"L{f(x2)} {f(y2)} A{f(r0)} {f(r0)} 0 {large} 0 {f(x3)} {f(y3)} Z")


def arc(r, a0, a1):
    x0, y0 = pol(r, a0)
    x1, y1 = pol(r, a1)
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M{f(x0)} {f(y0)} A{f(r)} {f(r)} 0 {large} 1 {f(x1)} {f(y1)}"


def text(x, y, s, size, fill, family=F_UI, weight=500, anchor="middle", extra=""):
    return (f'<text x="{f(x)}" y="{f(y)}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" {extra}>{s}</text>')


def moon_lit_path(cx, cy, r, ph):
    rx = r * abs(math.cos(2 * math.pi * ph))
    top, bot = f"{f(cx)} {f(cy-r)}", f"{f(cx)} {f(cy+r)}"
    if ph < 0.5:
        outer, sweep = f"M{top} A{r} {r} 0 0 1 {bot}", (0 if ph < 0.25 else 1)
    else:
        outer, sweep = f"M{top} A{r} {r} 0 0 0 {bot}", (1 if ph > 0.75 else 0)
    return f"{outer} A{f(rx)} {r} 0 0 {sweep} {top} Z"


U0, U1, DU = -0.47, 11.47, 0.04
SAMPLES = [U0 + i * DU for i in range(int((U1 - U0) / DU) + 1)]


# ---------------------------------------------------------------- layers
def landscape(p, dim_except=None):
    s = []
    # sky and terrain, sliced finely so colour can vary continuously
    for u in SAMPLES[:-1]:
        a0, a1 = ang(u), ang(u + DU) + 0.35
        um = u + DU / 2
        rc = crest(um)
        s.append(f'<path d="{sector(rc, 236, a0, a1)}" fill="{sky_color(um)}"/>')
        land = mix(temp_color(temp_at(um)), "#1A2235", 0.55 * night(um))
        s.append(f'<path d="{sector(R_BASE, rc + 0.3, a0, a1)}" fill="{land}"/>')
    # horizon glow over the sky, darker toward the bezel
    s.append(f'<circle cx="{C}" cy="{C}" r="236" fill="url(#{p}vign)"/>')
    # stars in the night sky
    rnd = random.Random(11)
    for _ in range(70):
        u = rnd.uniform(SUNSET_U + 0.6, U1 - 0.05)
        r = rnd.uniform(crest(u) + 5, 231)
        x, y = pol(r, ang(u))
        s.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rnd.uniform(.5, 1.2))}" fill="#FFFFFF" '
                 f'fill-opacity="{f(rnd.uniform(.35, .9))}"/>')
    # moon (real phase) in the night sky
    mx, my = pol(222, ang(9.6))
    s.append(f'<g transform="rotate({f(ang(9.6))} {f(mx)} {f(my)})"><circle cx="{f(mx)}" cy="{f(my)}" r="7.5" fill="#1E2A48"/>'
             f'<path d="{moon_lit_path(mx, my, 7.5, MOON_PHASE)}" fill="#F3EBCF"/></g>')
    # clouds sitting on the horizon where the forecast is cloudy
    rnd = random.Random(5)
    for n, (_, _, rain, cond, _, _) in enumerate(FORECAST):
        if cond not in ("cloud", "rain", "few"):
            continue
        puffs = {"few": 2, "cloud": 4, "rain": 5}[cond]
        col = "#E8EEF8" if cond != "rain" else "#9AA9C2"
        op = 0.55 if cond != "rain" else 0.75
        for k in range(puffs):
            u = n + rnd.uniform(-0.42, 0.42)
            r = crest(u) + rnd.uniform(5, 13)
            x, y = pol(r, ang(u))
            rr = rnd.uniform(6, 10)
            s.append(f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(rr*1.5)}" ry="{f(rr)}" fill="{col}" '
                     f'fill-opacity="{op}" filter="url(#{p}soft)" transform="rotate({f(ang(u))} {f(x)} {f(y)})"/>')
    # crest line
    pts = " ".join(f"{f(x)},{f(y)}" for x, y in (pol(crest(u), ang(u)) for u in SAMPLES))
    s.append(f'<polyline points="{pts}" fill="none" stroke="#FFFFFF" stroke-opacity="0.65" stroke-width="1.4" stroke-linejoin="round"/>')
    # ground line
    s.append(f'<path d="{arc(R_BASE, ang(U0), ang(U1))}" fill="none" stroke="#000000" stroke-opacity="0.35" stroke-width="2"/>')
    # seam where now meets +12 h
    seam = ang(-0.5)
    s.append(f'<path d="{sector(R_BASE - 2, 236, seam - 1.2, seam + 1.2)}" fill="#05080F"/>')
    # the sun is the hour hand
    su = NOW_U
    sx, sy = pol(crest(su) + 15, ang(su))
    s.append(f'<circle cx="{f(sx)}" cy="{f(sy)}" r="20" fill="url(#{p}sunglow)"/>')
    s.append(f'<circle cx="{f(sx)}" cy="{f(sy)}" r="8.5" fill="#FFE7A3"/>')
    tip = pol(R_BASE - 3, ang(su))
    bl = pol(R_BASE - 15, ang(su) - 3)
    br = pol(R_BASE - 15, ang(su) + 3)
    s.append(f'<path d="M{f(tip[0])} {f(tip[1])} L{f(bl[0])} {f(bl[1])} L{f(br[0])} {f(br[1])} Z" fill="#FFE7A3"/>')
    if dim_except is not None:
        a = ang(dim_except)
        s.append(f'<path d="{sector(R_BASE - 30, 236, a + 15, a + 345)}" fill="#000000" fill-opacity="0.55"/>')
        s.append(f'<path d="{sector(R_BASE - 30, 236, a - 15, a + 15)}" fill="none" stroke="#FFFFFF" stroke-width="2"/>')
    return "".join(s)


def rain_layer(dim=False):
    s = []
    # rain falling inward from the ground line, under rainy hours
    rnd = random.Random(9)
    for n, (_, _, rain, _, _, _) in enumerate(FORECAST):
        for _ in range(int(rain / 5)):
            u = n + rnd.uniform(-0.45, 0.45)
            r0 = R_BASE - rnd.uniform(3, 10)
            ln = rnd.uniform(7, 14)
            x0, y0 = pol(r0, ang(u))
            x1, y1 = pol(r0 - ln, ang(u) + 2.2)
            s.append(f'<line x1="{f(x0)}" y1="{f(y0)}" x2="{f(x1)}" y2="{f(y1)}" stroke="#6CC0FF" '
                     f'stroke-opacity="{f(rnd.uniform(.45, .95))}" stroke-width="1.6" stroke-linecap="round"/>')
    out = "".join(s)
    return f'<g opacity="0.4">{out}</g>' if dim else out


def dial_centre(p):
    sun_a = ang(NOW_U)
    lx, ly = pol(60, sun_a)
    d = (f'<radialGradient id="{p}sheen" gradientUnits="userSpaceOnUse" cx="{f(lx)}" cy="{f(ly)}" r="200">'
         f'<stop offset="0" stop-color="#1D2C47"/><stop offset="1" stop-color="#070B14"/></radialGradient>')
    return d, f'<circle cx="{C}" cy="{C}" r="{R_BASE - 1}" fill="url(#{p}sheen)"/>'


def pace_ring(p, dim=False):
    s = []
    prog = STEPS / GOAL
    op = 0.35 if dim else 1
    s.append(f'<circle cx="{C}" cy="{C}" r="{R_PACE}" fill="none" stroke="#FFFFFF" stroke-opacity="0.08" stroke-width="5"/>')
    s.append(f'<path d="{arc(R_PACE, 0, 360*prog)}" fill="none" stroke="#7CE0A3" stroke-opacity="{op}" stroke-width="5" stroke-linecap="round"/>')
    gx, gy = pol(R_PACE, 360 * PACE)
    s.append(f'<circle cx="{f(gx)}" cy="{f(gy)}" r="5.5" fill="#0A1120" stroke="#FFFFFF" stroke-opacity="{op}" stroke-width="1.8"/>')
    return "".join(s)


def shadowed_time(p, s_txt, y, size):
    # digits cast a soft shadow away from the sun's position on the dial
    sa = math.radians(ang(NOW_U))
    dx, dy = -math.sin(sa) * 6, math.cos(sa) * 6
    shadow = text(C + dx, y + dy, s_txt, size, "#000000", F_THIN, 300,
                  extra=f'fill-opacity="0.75" filter="url(#{p}shadow)" letter-spacing="-2"')
    return shadow + text(C, y, s_txt, size, "#FFFFFF", F_THIN, 300, extra='letter-spacing="-2"')


def common_defs(p):
    sx, sy = pol(crest(NOW_U) + 15, ang(NOW_U))
    return (f'<clipPath id="{p}round"><circle cx="{C}" cy="{C}" r="{C}"/></clipPath>'
            f'<radialGradient id="{p}vign" gradientUnits="userSpaceOnUse" cx="{C}" cy="{C}" r="236">'
            f'<stop offset="0.86" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.55"/></radialGradient>'
            f'<radialGradient id="{p}sunglow" gradientUnits="userSpaceOnUse" cx="{f(sx)}" cy="{f(sy)}" r="20">'
            f'<stop offset="0" stop-color="#FFD873" stop-opacity="0.9"/><stop offset="1" stop-color="#FFB547" stop-opacity="0"/></radialGradient>'
            f'<filter id="{p}soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2"/></filter>'
            f'<filter id="{p}shadow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3"/></filter>')


def rain_icon(x, y, s=0.7):
    g = (f'<g fill="#9FB3CC"><circle cx="{f(x-4*s)}" cy="{f(y+1*s)}" r="{f(4.5*s)}"/>'
         f'<circle cx="{f(x+2*s)}" cy="{f(y-2*s)}" r="{f(6*s)}"/>'
         f'<rect x="{f(x-8*s)}" y="{f(y)}" width="{f(16*s)}" height="{f(5.5*s)}" rx="{f(2.7*s)}"/></g>')
    for dx in (-5, 0, 5):
        g += (f'<line x1="{f(x+dx*s)}" y1="{f(y+8*s)}" x2="{f(x+(dx-2)*s)}" y2="{f(y+13*s)}" '
              f'stroke="#5AB4FF" stroke-width="{f(1.8*s)}" stroke-linecap="round"/>')
    return g


def heart(x, y, col, sc=0.72):
    return f'<path transform="translate({f(x)} {f(y)}) scale({sc})" d="M10 18 C-6 6 2 -4 10 3 C18 -4 26 6 10 18 Z" fill="{col}"/>'


# ---------------------------------------------------------------- states
def render_active():
    p = "hz_"
    d0, centre = dial_centre(p)
    s = [f'<rect width="{S}" height="{S}" fill="#05080F"/>', landscape(p), centre, rain_layer(), pace_ring(p)]
    # temperature labels on the ground, inside the terrain
    for n in (0, 3, 10):
        x, y = pol(R_BASE - 16, ang(n))
        s.append(text(x, y + 4.5, f"{TEMPS[n]}°", 12.5, temp_color(TEMPS[n]), weight=700))
    s.append(text(C, 170, "THU 06 NOV", 13.5, "#8FA3C4", weight=600, extra='letter-spacing="3"'))
    s.append(shadowed_time(p, f"{HH:02d}:{MM:02d}", 252, 82))
    s.append(rain_icon(C - 74, 274))
    s.append(text(C - 58, 287, "Rain at 16:00 · 60%", 16, "#6CC0FF", weight=600, anchor="start"))
    s.append(heart(C - 70, 304, "#7CE0A3"))
    s.append(text(C - 54, 318, f"{HR}", 16, "#E6ECF5", weight=600, anchor="start"))
    s.append(text(C - 4, 318, "2,840", 16, "#E6ECF5", weight=600, anchor="start"))
    s.append(text(C + 42, 318, "+640", 12, "#7CE0A3", weight=700, anchor="start"))
    return wrap(p, d0, s)


def render_scrub():
    p = "hzs_"
    n = 7
    hour, t, rain, cond, feels, uv = FORECAST[n]
    d0, centre = dial_centre(p)
    s = [f'<rect width="{S}" height="{S}" fill="#05080F"/>', landscape(p, dim_except=n), centre, rain_layer(dim=True), pace_ring(p, dim=True)]
    # tilt glyph + selected hour
    s.append(f'<g fill="none" stroke="#8FA3C4" stroke-width="1.6" stroke-linecap="round">'
             f'<path d="M{C-62} 160 q-6 6 0 12"/><path d="M{C-68} 156 q-10 10 0 20"/></g>')
    s.append(text(C - 48, 172, f"{hour}:00", 15, "#FFFFFF", weight=700, anchor="start", extra='letter-spacing="1"'))
    s.append(text(C + 4, 172, "· in 7 h", 15, "#8FA3C4", weight=600, anchor="start"))
    s.append(text(C, 252, f"{t}°", 82, "#FFFFFF", F_THIN, 300, extra='letter-spacing="-2"'))
    s.append(rain_icon(C - 70, 274))
    s.append(text(C - 54, 287, f"Heavy rain · {rain}%", 16, "#6CC0FF", weight=600, anchor="start"))
    s.append(text(C, 318, f"Feels {feels}° · UV {uv} · After sunset", 13.5, "#B9C4D8", weight=600))
    s.append(text(C, 344, "Now 10:08", 12, "#6C7A93", weight=600, extra='letter-spacing="1"'))
    return wrap(p, d0, s)


def render_aod():
    p = "hza_"
    s = [f'<rect width="{S}" height="{S}" fill="#000"/>']
    prev = None
    for u in SAMPLES:
        pt = pol(crest(u), ang(u))
        if prev:
            col = temp_color(temp_at(u))
            s.append(f'<line x1="{f(prev[0])}" y1="{f(prev[1])}" x2="{f(pt[0])}" y2="{f(pt[1])}" '
                     f'stroke="{col}" stroke-opacity="0.75" stroke-width="2" stroke-linecap="round"/>')
        prev = pt
    for n, (_, _, rain, _, _, _) in enumerate(FORECAST):
        if rain >= 50:
            s.append(f'<path d="{arc(R_BASE - 6, ang(n) - 14, ang(n) + 14)}" fill="none" stroke="#5AB4FF" '
                     f'stroke-opacity="0.75" stroke-width="2" stroke-dasharray="2 4"/>')
    sx, sy = pol(crest(NOW_U) + 15, ang(NOW_U))
    s.append(f'<circle cx="{f(sx)}" cy="{f(sy)}" r="7" fill="none" stroke="#FFE7A3" stroke-width="2"/>')
    s.append(text(C, 252, f"{HH:02d}:{MM:02d}", 82, "none", F_THIN, 200,
                  extra='letter-spacing="-2" stroke="#D0D0D0" stroke-width="1.5"'))
    s.append(text(C, 287, "Rain at 16:00 · 60%", 16, "#3F7FB5", weight=600))
    return wrap(p, "", s)


def wrap(p, extra_defs, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}" height="{S}">'
            f'<defs>{common_defs(p)}{extra_defs}</defs><g clip-path="url(#{p}round)">{"".join(body)}</g></svg>\n')


def pins():
    def pct(x, y):
        return [round(x / S * 100, 1), round(y / S * 100, 1)]
    out = {
        "1": pct(*pol((R_BASE + crest(2.5)) / 2, ang(2.5))),
        "2": pct(*pol(crest(NOW_U) + 15 + 22, ang(NOW_U) + 3)),
        "3": pct(*pol(229, ang(7.2))),
        "4": pct(*pol(R_BASE - 20, ang(7.6))),
        "5": pct(*pol(222, ang(-0.5))),
        "6": pct(C + 122, 222),
        "7": pct(*pol(R_PACE, 360 * PACE + 14)),
        "8": pct(C + 116, 282),
        "9": pct(C - 92, 313),
    }
    return out


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "horizon.svg").write_text(render_active())
    (OUT / "horizon-scrub.svg").write_text(render_scrub())
    (OUT / "horizon-aod.svg").write_text(render_aod())
    (OUT / "horizon-pins.json").write_text(json.dumps(pins(), indent=1) + "\n")
    print("wrote horizon previews")


if __name__ == "__main__":
    main()
