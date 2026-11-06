#!/usr/bin/env python3
"""Render SVG design previews for every face in CATALOGUE.md.

Each face gets two 466x466 SVGs (the OnePlus Watch 3 panel size):
  previews/<face>.svg      interactive mode
  previews/<face>-aod.svg  ambient / always-on mode

The previews show a fixed moment: Thu 06 Nov, 10:08:36.
They are design mockups, not the shipping Watch Face Format XML.

Usage:  python3 tools/render_previews.py
"""
import math
import random
from pathlib import Path

S = 466          # panel size in px
C = S / 2        # centre
OUT = Path(__file__).resolve().parent.parent / "previews"

# Sample moment shown on every face
HH, MM, SS = 10, 8, 36
DATE = "THU 06 NOV"
STEPS, BATT, HR, KCAL, TEMP = "8,421", 72, 68, 412, 18
MOON_PHASE = 0.884  # waning crescent on 2026-11-06

HOUR_ANG = (HH % 12 + MM / 60) * 30
MIN_ANG = (MM + SS / 60) * 6
SEC_ANG = SS * 6

F_COND = "Oswald, 'Arial Narrow', 'Roboto Condensed', sans-serif"
F_MONO = "'JetBrains Mono', 'DejaVu Sans Mono', Menlo, Consolas, monospace"
F_SERIF = "'Cormorant Garamond', Georgia, 'Times New Roman', serif"
F_THIN = "Outfit, 'Helvetica Neue', Arial, sans-serif"
F_UI = "Barlow, 'Helvetica Neue', Arial, sans-serif"


# ---------------------------------------------------------------- helpers
def pol(r, deg, cx=C, cy=C):
    a = math.radians(deg)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def arc(r, a0, a1, cx=C, cy=C):
    """Clockwise arc path from angle a0 to a1 (degrees, 0 = 12 o'clock)."""
    x0, y0 = pol(r, a0, cx, cy)
    x1, y1 = pol(r, a1, cx, cy)
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M{f(x0)} {f(y0)} A{f(r)} {f(r)} 0 {large} 1 {f(x1)} {f(y1)}"


def text(x, y, s, size, fill, family, weight=400, anchor="middle", extra=""):
    return (f'<text x="{f(x)}" y="{f(y)}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{s}</text>')


def glow(fid, std=4):
    return (f'<filter id="{fid}" x="-50%" y="-50%" width="200%" height="200%">'
            f'<feGaussianBlur stdDeviation="{std}" result="b"/>'
            f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')


def ticks(r_out, length, every, width, color, skip=(), count=60):
    out = []
    for i in range(count):
        if i in skip or i % every:
            continue
        a = i * 360 / count
        x0, y0 = pol(r_out, a)
        x1, y1 = pol(r_out - length, a)
        out.append(f'<line x1="{f(x0)}" y1="{f(y0)}" x2="{f(x1)}" y2="{f(y1)}" '
                   f'stroke="{color}" stroke-width="{width}"/>')
    return "".join(out)


def hand(angle, shape, fill="none", stroke="none", sw=0):
    return (f'<g transform="rotate({f(angle)} {f(C)} {f(C)})">'
            f'<path d="{shape}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            f'stroke-linejoin="round"/></g>')


def taper(length, base, tip, tail=0):
    """Tapered hand pointing at 12, centred on the panel."""
    return (f"M{f(C-base/2)} {f(C+tail)} L{f(C-tip/2)} {f(C-length)} "
            f"L{f(C+tip/2)} {f(C-length)} L{f(C+base/2)} {f(C+tail)} Z")


def cap(r, fill, stroke="none", sw=0):
    return f'<circle cx="{f(C)}" cy="{f(C)}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


# ---------------------------------------------------------------- faces
def monolith(p, aod):
    accent = "#FF7A45"
    if aod:
        digit = 'fill="none" stroke="#FFFFFF" stroke-width="2"'
        digit2 = f'fill="none" stroke="{accent}" stroke-width="2"'
    else:
        digit = 'fill="#F4F4F2"'
        digit2 = f'fill="{accent}"'
    s = [
        f'<text x="{C}" y="200" font-family="{F_COND}" font-size="172" font-weight="700" '
        f'text-anchor="middle" letter-spacing="-4" {digit}>{HH:02d}</text>',
        f'<text x="{C}" y="362" font-family="{F_COND}" font-size="172" font-weight="700" '
        f'text-anchor="middle" letter-spacing="-4" {digit2}>{MM:02d}</text>',
        text(C, 402, DATE, 20, "#8A8A8A" if not aod else "#5A5A5A", F_UI, 600,
             extra='letter-spacing="4"'),
    ]
    if not aod:
        s.append(f'<rect x="{C-30}" y="421" width="22" height="12" rx="2" fill="none" stroke="#8A8A8A" stroke-width="1.5"/>'
                 f'<rect x="{C-8}" y="424" width="2.5" height="6" fill="#8A8A8A"/>'
                 f'<rect x="{C-28}" y="423" width="{f(18*BATT/100)}" height="8" rx="1" fill="#8A8A8A"/>')
        s.append(text(C + 2, 433, f"{BATT}%", 15, "#BDBDBD", F_UI, 600, "start"))
    return "#000000", "".join(s)


def meridian(p, aod):
    ivory, red = "#EDEAE2", "#E5483C"
    s = []
    if not aod:
        s.append(f'<circle cx="{C}" cy="{C}" r="{C}" fill="url(#{p}dial)"/>')
        s.append(ticks(222, 8, 1, 1.4, "#6C7894"))
    for i in range(12):
        a = i * 30
        w, ln = (7, 34) if i % 3 == 0 else (4, 24)
        s.append(f'<g transform="rotate({a} {C} {C})"><rect x="{f(C-w/2)}" y="{C-216}" width="{w}" '
                 f'height="{ln}" rx="1.5" fill="{ivory if not aod else "none"}" '
                 f'stroke="{"none" if not aod else ivory}" stroke-width="1.5"/></g>')
    if not aod:
        comps = [  # (angle, label, value, progress)
            (0, "WEATHER", f"{TEMP}°", None),
            (90, "STEPS", "8.4k", 0.84),
            (180, "BATTERY", f"{BATT}", BATT / 100),
            (270, "BPM", f"{HR}", None),
        ]
        for a, lab, val, prog in comps:
            x, y = pol(102, a)
            s.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="36" fill="#0A1020" stroke="#2A3550" stroke-width="1.5"/>')
            if prog is not None:
                s.append(f'<path d="{arc(36, 0, 360*prog, x, y)}" fill="none" stroke="{ivory}" '
                         f'stroke-width="2.5" stroke-linecap="round"/>')
            s.append(text(x, y + 6, val, 20, ivory, F_UI, 600))
            s.append(text(x, y + 22, lab, 8, "#7D89A6", F_UI, 600, extra='letter-spacing="1"'))
    hf = ivory if not aod else "none"
    hs = "none" if not aod else ivory
    s.append(hand(HOUR_ANG, taper(118, 14, 6, 18), hf, hs if aod else "#0A1020", 1.5))
    s.append(hand(MIN_ANG, taper(178, 11, 4, 22), hf, hs if aod else "#0A1020", 1.5))
    if not aod:
        s.append(hand(SEC_ANG, taper(200, 2.5, 1.5, 40), red))
        s.append(cap(7, red))
        s.append(cap(2.5, "#0A1020"))
    else:
        s.append(cap(5, "#000", ivory, 1.5))
    defs = (f'<radialGradient id="{p}dial" cx="50%" cy="40%" r="65%">'
            f'<stop offset="0" stop-color="#1B2742"/><stop offset="1" stop-color="#0A1020"/></radialGradient>')
    return "#000000", defs + "".join(s)


def pulse(p, aod):
    rings = [(212, "#FF4D6D", 0.84), (186, "#C6F432", 0.62), (160, "#39D5FF", 0.45)]
    s = []
    for r, col, prog in rings:
        if aod:
            s.append(f'<path d="{arc(r, 0, 360*prog)}" fill="none" stroke="{col}" stroke-opacity="0.3" '
                     f'stroke-width="4" stroke-linecap="round"/>')
        else:
            s.append(f'<circle cx="{C}" cy="{C}" r="{r}" fill="none" stroke="{col}" stroke-opacity="0.18" stroke-width="18"/>')
            s.append(f'<path d="{arc(r, 0, 360*prog)}" fill="none" stroke="{col}" stroke-width="18" stroke-linecap="round"/>')
    s.append(text(C, 262, f"{HH:02d}:{MM:02d}", 92, "#FFFFFF" if not aod else "#BBBBBB", F_UI, 600 if not aod else 300,
                  extra='letter-spacing="-2"'))
    if not aod:
        s.append(text(C, 168, DATE, 16, "#9A9A9A", F_UI, 600, extra='letter-spacing="3"'))
        s.append(f'<path transform="translate({C-34} 292) scale(0.9)" d="M10 18 C-6 6 2 -4 10 3 C18 -4 26 6 10 18 Z" fill="#FF4D6D"/>')
        s.append(text(C - 8, 308, f"{HR}", 22, "#FFFFFF", F_UI, 600, "start"))
        s.append(text(C + 20, 308, "BPM", 11, "#9A9A9A", F_UI, 600, "start"))
        leg = [("#FF4D6D", STEPS), ("#C6F432", f"{KCAL}"), ("#39D5FF", "38m")]
        for i, (col, val) in enumerate(leg):
            x = C - 84 + i * 84
            s.append(f'<circle cx="{x-24}" cy="340" r="4" fill="{col}"/>')
            s.append(text(x - 15, 345, val, 15, "#DDDDDD", F_UI, 600, "start"))
    return "#000000", "".join(s)


def tidal(p, aod):
    if aod:
        s = [text(C, 268, f"{HH:02d}:{MM:02d}", 118, "#5FE0D6", F_THIN, 200, extra='letter-spacing="-3"')]
        return "#000000", "".join(s)
    defs = (f'<radialGradient id="{p}g" cx="30%" cy="22%" r="95%">'
            f'<stop offset="0" stop-color="#7CF2E2"/><stop offset="0.35" stop-color="#1A9AA8"/>'
            f'<stop offset="0.75" stop-color="#0B3B5C"/><stop offset="1" stop-color="#061423"/></radialGradient>')
    s = [defs, f'<rect width="{S}" height="{S}" fill="url(#{p}g)"/>']
    for k, (base, amp, ph, op) in enumerate([(360, 10, 0, .18), (385, 12, 1.4, .14), (410, 9, 2.6, .1)]):
        pts = " ".join(f"{x},{f(base + amp*math.sin(x/38 + ph))}" for x in range(0, S + 1, 6))
        s.append(f'<polyline points="{pts}" fill="none" stroke="#FFFFFF" stroke-opacity="{op}" stroke-width="2"/>')
    s.append(text(C, 150, "Thursday 6", 22, "#E9FFFC", F_THIN, 300, extra='letter-spacing="1"'))
    s.append(text(C, 268, f"{HH:02d}:{MM:02d}", 118, "#FFFFFF", F_THIN, 200, extra='letter-spacing="-3"'))
    s.append(text(C, 318, f"{TEMP}° · Clear", 20, "#E9FFFC", F_THIN, 300))
    return "#061423", "".join(s)


def field_line(p, aod):
    lume, edge = "#CFF5A8", "#0E0F0E"
    s = []
    if not aod:
        s.append(ticks(226, 10, 1, 1.5, "#5A5D58"))
        s.append(ticks(226, 18, 5, 3, "#C9CCC5"))
    for i in range(1, 12):
        x, y = pol(176, i * 30)
        s.append(text(x, y + 17, str(i), 48, lume if aod else "#F2F3EE", F_COND, 500))
    tri = f"M{C} {C-152} L{C-15} {C-192} L{C+15} {C-192} Z"
    s.append(f'<path d="{tri}" fill="{lume}"/>')
    if not aod:
        for i in range(12):
            x, y = pol(132, i * 30)
            s.append(text(x, y + 5, str(i + 13 if i else 24), 14, "#E0703A", F_UI, 600))
        for a, val, lab, prog in [(270, f"{BATT}", "BATT", BATT / 100), (90, "8.4k", "STEPS", .84)]:
            x, y = pol(74, a)
            s.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="32" fill="#171917" stroke="#3B3E39" stroke-width="1.5"/>')
            s.append(f'<path d="{arc(32, 0, 360*prog, x, y)}" fill="none" stroke="#E0703A" stroke-width="2.5"/>')
            s.append(text(x, y + 5, val, 17, "#F2F3EE", F_UI, 600))
            s.append(text(x, y + 19, lab, 8, "#8B8F86", F_UI, 600, extra='letter-spacing="1"'))
        s.append(f'<rect x="{C-24}" y="{C+70}" width="48" height="30" rx="3" fill="#F2F3EE"/>')
        s.append(text(C, C + 93, "06", 22, "#111", F_UI, 700))
    # sword hands
    hour = (f"M{C-9} {C+16} L{C-9} {C-70} L{C} {C-110} L{C+9} {C-70} L{C+9} {C+16} Z")
    minute = (f"M{C-7} {C+20} L{C-7} {C-130} L{C} {C-178} L{C+7} {C-130} L{C+7} {C+20} Z")
    if aod:
        s.append(hand(HOUR_ANG, hour, "none", lume, 2))
        s.append(hand(MIN_ANG, minute, "none", lume, 2))
        s.append(cap(6, "#000", lume, 2))
    else:
        s.append(hand(HOUR_ANG, hour, lume, edge, 2))
        s.append(hand(MIN_ANG, minute, lume, edge, 2))
        s.append(hand(SEC_ANG, taper(196, 2.5, 2, 36), "#E0703A"))
        s.append(cap(8, "#E0703A"))
    return "#0E0F0E", "".join(s)


def terminal(p, aod):
    g = "#3DFF7A"
    if aod:
        return "#000000", (text(70, 220, "$ time", 28, "#1F8A44", F_MONO, 500, "start")
                           + text(70, 288, f"{HH:02d}:{MM:02d}", 74, "#2BB45A", F_MONO, 500, "start"))
    defs = (glow(f"{p}glow", 3)
            + f'<pattern id="{p}scan" width="4" height="4" patternUnits="userSpaceOnUse">'
              f'<rect width="4" height="1.2" fill="#000" fill-opacity="0.45"/></pattern>')
    dim = "#1F8A44"
    rows = [
        (112, "watch3@oneplus:~", 18, dim),
        (172, "$ time", 26, g),
    ]
    s = [defs, f'<g filter="url(#{p}glow)">']
    for y, t, sz, col in rows:
        s.append(text(70, y, t, sz, col, F_MONO, 500, "start"))
    s.append(text(70, 236, f"{HH:02d}:{MM:02d}", 68, g, F_MONO, 600, "start"))
    for i, (k, v) in enumerate([("date", "THU 06 NOV"), ("steps", STEPS), ("batt", f"{BATT}%"), ("bpm", f"{HR}")]):
        y = 278 + i * 34
        s.append(text(70, y, f"$ {k}", 22, dim, F_MONO, 500, "start"))
        s.append(text(190, y, v, 22, g, F_MONO, 500, "start"))
    s.append(text(70, 414, "$", 22, g, F_MONO, 500, "start"))
    s.append(f'<rect x="90" y="397" width="13" height="22" fill="{g}"/>')
    s.append("</g>")
    s.append(f'<rect width="{S}" height="{S}" fill="url(#{p}scan)"/>')
    return "#020803", "".join(s)


def daylight(p, aod):
    hy, r = 250, 172
    rise, sset = 6 * 60 + 48, 17 * 60 + 2
    frac = (HH * 60 + MM - rise) / (sset - rise)
    sun_deg = -90 + 180 * frac          # -90 = left horizon, 90 = right horizon
    sx, sy = pol(r, sun_deg, C, hy)
    amber = "#FFB547"
    s = []
    if aod:
        s.append(f'<path d="{arc(r, -90, 90, C, hy)}" fill="none" stroke="{amber}" stroke-opacity="0.6" stroke-width="2"/>')
        s.append(f'<circle cx="{f(sx)}" cy="{f(sy)}" r="9" fill="none" stroke="{amber}" stroke-width="2"/>')
        s.append(text(C, 350, f"{HH:02d}:{MM:02d}", 88, "#C9C9C9", F_UI, 300, extra='letter-spacing="-1"'))
        return "#000000", "".join(s)
    defs = (f'<linearGradient id="{p}sky" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="#16233F"/><stop offset="1" stop-color="#2F3B58"/></linearGradient>'
            + glow(f"{p}glow", 8))
    s.append(defs)
    s.append(f'<rect width="{S}" height="{hy}" fill="url(#{p}sky)"/>')
    s.append(f'<rect y="{hy}" width="{S}" height="{S-hy}" fill="#0A0E18"/>')
    s.append(f'<path d="{arc(r, -90, 90, C, hy)}" fill="none" stroke="#FFFFFF" stroke-opacity="0.25" '
             f'stroke-width="2" stroke-dasharray="3 7"/>')
    s.append(f'<path d="{arc(r, -90, sun_deg, C, hy)}" fill="none" stroke="{amber}" stroke-width="5" stroke-linecap="round"/>')
    s.append(f'<line x1="0" y1="{hy}" x2="{S}" y2="{hy}" stroke="#FFFFFF" stroke-opacity="0.35" stroke-width="1.5"/>')
    s.append(f'<circle cx="{f(sx)}" cy="{f(sy)}" r="15" fill="{amber}" filter="url(#{p}glow)"/>')
    s.append(text(C - r, hy + 26, "↑ 06:48", 15, "#B9C0D0", F_UI, 600))
    s.append(text(C + r, hy + 26, "↓ 17:02", 15, "#B9C0D0", F_UI, 600))
    s.append(text(C, 150, "3h 20m of light used", 13, "#B9C0D0", F_UI, 500, extra='letter-spacing="1"'))
    s.append(text(C, 350, f"{HH:02d}:{MM:02d}", 88, "#FFFFFF", F_UI, 500, extra='letter-spacing="-1"'))
    s.append(text(C, 384, DATE, 16, "#8C93A6", F_UI, 600, extra='letter-spacing="3"'))
    s.append(text(C, 416, f"{STEPS} steps", 15, amber, F_UI, 600))
    return "#0A0E18", "".join(s)


def dashboard(p, aod):
    acc = "#7CC4FF"
    tiles = [
        ("STEPS", STEPS, 0.84), ("HEART", f"{HR}", None), ("BATTERY", f"{BATT}%", BATT / 100),
        ("WEATHER", f"{TEMP}°", None), ("CALORIES", f"{KCAL}", 0.62), ("SLEEP", "7h12", None),
    ]
    tw, th, gap, x0, y0 = 110, 82, 10, 58, 172
    s = [text(C, 120, f"{HH:02d}:{MM:02d}", 72, "#FFFFFF" if not aod else "#BBBBBB", F_UI, 600 if not aod else 300)]
    if not aod:
        s.append(text(C, 150, DATE, 14, "#8A93A3", F_UI, 600, extra='letter-spacing="3"'))
    show = tiles if not aod else tiles[:2]
    for i, (lab, val, prog) in enumerate(show):
        col, row = i % 3, i // 3
        if aod:
            col, row = i + 0.5, 0
        x, y = x0 + col * (tw + gap), y0 + row * (th + gap)
        stroke = "#2C3A4F" if not aod else "#3A3A3A"
        s.append(f'<rect x="{f(x)}" y="{y}" width="{tw}" height="{th}" rx="12" fill="{"#0D1520" if not aod else "none"}" '
                 f'stroke="{stroke}" stroke-width="1.5"/>')
        s.append(text(x + 12, y + 22, lab, 10, "#7D8797", F_UI, 700, "start", 'letter-spacing="1.2"'))
        s.append(text(x + 12, y + 54, val, 26, "#FFFFFF" if not aod else "#AAAAAA", F_UI, 600, "start"))
        if prog is not None and not aod:
            s.append(f'<rect x="{f(x+12)}" y="{y+64}" width="{tw-24}" height="5" rx="2.5" fill="#1F2B3B"/>')
            s.append(f'<rect x="{f(x+12)}" y="{y+64}" width="{f((tw-24)*prog)}" height="5" rx="2.5" fill="{acc}"/>')
    if not aod:
        s.append(f'<circle cx="{C-84}" cy="385" r="4" fill="{acc}"/>')
        s.append(text(C - 74, 390, "Standup · 10:30", 15, "#C7CFDB", F_UI, 600, "start"))
    return "#000000", "".join(s)


def orbit(p, aod):
    sun, hcol, mcol = "#FFC857", "#FF7B54", "#5BB8FF"
    rh, rm = 92, 166
    s = []
    if not aod:
        rnd = random.Random(7)
        for _ in range(90):
            x, y = rnd.uniform(0, S), rnd.uniform(0, S)
            s.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rnd.uniform(.4, 1.4))}" fill="#FFFFFF" '
                     f'fill-opacity="{f(rnd.uniform(.25, .8))}"/>')
        s.append(glow(f"{p}glow", 10))
    for i in range(12):
        x, y = pol(206, i * 30)
        s.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{3 if i % 3 == 0 else 1.8}" fill="#8E95B5"/>')
    for r in (rh, rm):
        s.append(f'<circle cx="{C}" cy="{C}" r="{r}" fill="none" stroke="#8E95B5" stroke-opacity="0.35" stroke-width="1"/>')
    hx, hy = pol(rh, HOUR_ANG)
    mx, my = pol(rm, MIN_ANG)
    if aod:
        s.append(cap(22, "none", sun, 2))
        s.append(f'<circle cx="{f(hx)}" cy="{f(hy)}" r="16" fill="none" stroke="{hcol}" stroke-width="2"/>')
        s.append(f'<circle cx="{f(mx)}" cy="{f(my)}" r="12" fill="none" stroke="{mcol}" stroke-width="2"/>')
        return "#000000", "".join(s)
    s.append(f'<circle cx="{C}" cy="{C}" r="26" fill="{sun}" filter="url(#{p}glow)"/>')
    s.append(f'<ellipse cx="{f(hx)}" cy="{f(hy)}" rx="28" ry="7" fill="none" stroke="#FFD2B8" stroke-width="2.5" '
             f'transform="rotate(-20 {f(hx)} {f(hy)})"/>')
    s.append(f'<circle cx="{f(hx)}" cy="{f(hy)}" r="16" fill="{hcol}"/>')
    s.append(f'<circle cx="{f(mx)}" cy="{f(my)}" r="28" fill="none" stroke="#8E95B5" stroke-opacity="0.35"/>')
    s.append(f'<circle cx="{f(mx)}" cy="{f(my)}" r="12" fill="{mcol}"/>')
    ox, oy = pol(28, SEC_ANG, mx, my)
    s.append(f'<circle cx="{f(ox)}" cy="{f(oy)}" r="4" fill="#E8E8F0"/>')
    s.append(text(128, 392, f"{BATT}%", 16, "#C5CAE0", F_UI, 600))
    s.append(text(338, 392, f"{TEMP}°", 16, "#C5CAE0", F_UI, 600))
    return "#05060F", "".join(s)


def moon_lit_path(cx, cy, r, ph):
    rx = r * abs(math.cos(2 * math.pi * ph))
    top, bot = f"{f(cx)} {f(cy-r)}", f"{f(cx)} {f(cy+r)}"
    if ph < 0.5:   # waxing, right side lit
        outer = f"M{top} A{r} {r} 0 0 1 {bot}"
        sweep = 0 if ph < 0.25 else 1
    else:          # waning, left side lit
        outer = f"M{top} A{r} {r} 0 0 0 {bot}"
        sweep = 1 if ph > 0.75 else 0
    return f"{outer} A{f(rx)} {r} 0 0 {sweep} {top} Z"


def lunar(p, aod):
    silver = "#E4E0D6"
    mcx, mcy, mr = C, 322, 36
    s = []
    if not aod:
        s.append(f'<circle cx="{C}" cy="{C}" r="{C}" fill="url(#{p}dial)"/>')
        s.append(ticks(224, 6, 1, 1, "#4A5578"))
        numerals = ["XII", "I", "II", "III", "IIII", "V", "", "VII", "VIII", "IX", "X", "XI"]
        for i, n in enumerate(numerals):
            if not n:
                continue
            x, y = pol(188, i * 30)
            s.append(f'<text x="{f(x)}" y="{f(y+10)}" font-family="{F_SERIF}" font-size="30" font-weight="500" '
                     f'fill="{silver}" text-anchor="middle" transform="rotate({i*30} {f(x)} {f(y)})">{n}</text>')
        # aperture
        s.append(f'<clipPath id="{p}win"><path d="M{mcx-70} {mcy+20} A70 70 0 0 1 {mcx+70} {mcy+20} Z"/></clipPath>')
        s.append(f'<path d="M{mcx-70} {mcy+20} A70 70 0 0 1 {mcx+70} {mcy+20} Z" fill="#0F1B3D" stroke="{silver}" stroke-width="1.5"/>')
        rnd = random.Random(3)
        st = "".join(f'<circle cx="{f(mcx+rnd.uniform(-65,65))}" cy="{f(mcy+rnd.uniform(-60,15))}" r="0.9" fill="#FFFFFF" fill-opacity="0.7"/>'
                     for _ in range(28))
        s.append(f'<g clip-path="url(#{p}win)">{st}'
                 f'<circle cx="{mcx}" cy="{mcy-14}" r="{mr}" fill="#26314F"/>'
                 f'<path d="{moon_lit_path(mcx, mcy-14, mr, MOON_PHASE)}" fill="#F3E9C6"/></g>')
        s.append(text(mcx, mcy + 40, "WANING CRESCENT", 9, "#8C95B3", F_UI, 600, extra='letter-spacing="2"'))
        s.append(f'<rect x="{C+92}" y="{C-14}" width="38" height="28" rx="2" fill="#0F1630" stroke="{silver}" stroke-width="1"/>')
        s.append(text(C + 111, C + 8, "06", 19, silver, F_SERIF, 600))
        s.append(text(C - 111, C + 7, f"{BATT}%", 17, silver, F_SERIF, 600))
    else:
        s.append(f'<circle cx="{mcx}" cy="{mcy-14}" r="{mr}" fill="none" stroke="{silver}" stroke-opacity="0.5" stroke-width="1.5"/>')
        s.append(f'<path d="{moon_lit_path(mcx, mcy-14, mr, MOON_PHASE)}" fill="none" stroke="{silver}" stroke-width="1.5"/>')
    def dauphine(length, w):
        return f"M{C} {C+14} L{C-w} {C-length*0.18} L{C} {C-length} L{C+w} {C-length*0.18} Z"
    hf, hs = (silver, "#2B3554") if not aod else ("none", silver)
    s.append(hand(HOUR_ANG, dauphine(116, 9), hf, hs, 1.2 if not aod else 1.6))
    s.append(hand(MIN_ANG, dauphine(176, 7), hf, hs, 1.2 if not aod else 1.6))
    s.append(cap(5, silver if not aod else "#000", silver, 1.5))
    defs = (f'<radialGradient id="{p}dial" cx="50%" cy="35%" r="70%">'
            f'<stop offset="0" stop-color="#1C2547"/><stop offset="1" stop-color="#080C1C"/></radialGradient>')
    return "#000000", defs + "".join(s)


WORD_GRID = [
    "ITLISASAMPM",
    "ACQUARTERDC",
    "TWENTYFIVEX",
    "HALFSTENFTO",
    "PASTERUNINE",
    "ONESIXTHREE",
    "FOURFIVETWO",
    "EIGHTELEVEN",
    "SEVENTWELVE",
    "TENSEOCLOCK",
]
# "IT IS FIVE PAST TEN" (+3 minute dots)
WORD_LIT = {(0, 0), (0, 1), (0, 3), (0, 4),
            (2, 6), (2, 7), (2, 8), (2, 9),
            (4, 0), (4, 1), (4, 2), (4, 3),
            (9, 0), (9, 1), (9, 2)}


def wordsmith(p, aod):
    cell, cols, rows = 28, 11, 10
    gx, gy = C - cols * cell / 2, C - rows * cell / 2 + 6
    on = "#FFF1D6"
    s = [glow(f"{p}glow", 3)] if not aod else []
    for r, row in enumerate(WORD_GRID):
        for c, ch in enumerate(row):
            lit = (r, c) in WORD_LIT
            if aod and not lit:
                continue
            x, y = gx + c * cell + cell / 2, gy + r * cell + cell / 2 + 7
            col = on if lit else "#2A2A2E"
            extra = f'filter="url(#{p}glow)"' if lit and not aod else ""
            s.append(text(x, y, ch, 19, col if not aod else "#BFB6A4", F_MONO, 600 if lit else 500, extra=extra))
    for i in range(4):
        x = C - 33 + i * 22
        lit = i < MM % 5
        if aod and not lit:
            continue
        s.append(f'<circle cx="{x}" cy="{f(gy-18)}" r="4" fill="{on if lit else "#2A2A2E"}"/>')
    if not aod:
        s.append(text(C, gy + rows * cell + 34, DATE, 14, "#7A7468", F_UI, 600, extra='letter-spacing="3"'))
    return "#000000", "".join(s)


def bits(p, aod):
    on, off = "#4FD1FF", "#18222E"
    digits = [HH // 10, HH % 10, MM // 10, MM % 10, SS // 10, SS % 10]
    maxbits = [2, 4, 3, 4, 3, 4]
    xs = [118, 166, 233 - 24, 233 + 24, 300, 348]
    ys = {8: 108, 4: 158, 2: 208, 1: 258}
    s = [glow(f"{p}glow", 5)] if not aod else []
    for d, mb, x in zip(digits, maxbits, xs):
        for b in (8, 4, 2, 1):
            if b >= 2 ** mb:
                continue
            lit = bool(d & b)
            if aod and not lit:
                continue
            y = ys[b]
            if lit:
                extra = f' filter="url(#{p}glow)"' if not aod else ""
                s.append(f'<circle cx="{x}" cy="{y}" r="15" fill="{on if not aod else "#2C7FA0"}"{extra}/>')
            else:
                s.append(f'<circle cx="{x}" cy="{y}" r="15" fill="{off}"/>')
    if not aod:
        for b, y in ys.items():
            s.append(text(80, y + 5, str(b), 13, "#4A5A6C", F_MONO, 500))
        for lab, x in [("H", 142), ("M", 233), ("S", 324)]:
            s.append(text(x, 298, lab, 13, "#4A5A6C", F_MONO, 600, extra='letter-spacing="2"'))
        s.append(text(C, 352, f"{HH:02d}:{MM:02d}:{SS:02d}", 34, "#DCEFF7", F_MONO, 500))
        s.append(text(C, 392, f"BATT {BATT}%", 15, "#6E8396", F_MONO, 500, extra='letter-spacing="2"'))
    return "#000000", "".join(s)


FACES = [
    ("monolith", monolith), ("meridian", meridian), ("pulse", pulse), ("tidal", tidal),
    ("field-line", field_line), ("terminal", terminal), ("daylight", daylight), ("dashboard", dashboard),
    ("orbit", orbit), ("lunar", lunar), ("wordsmith", wordsmith), ("bits", bits),
]


def render(key, fn, aod):
    p = key.replace("-", "") + ("aod" if aod else "") + "_"
    bg, body = fn(p, aod)
    if aod:
        bg = "#000000"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}" height="{S}">'
            f'<defs><clipPath id="{p}round"><circle cx="{C}" cy="{C}" r="{C}"/></clipPath></defs>'
            f'<g clip-path="url(#{p}round)"><rect width="{S}" height="{S}" fill="{bg}"/>{body}</g></svg>\n')


def main():
    OUT.mkdir(exist_ok=True)
    for key, fn in FACES:
        (OUT / f"{key}.svg").write_text(render(key, fn, False))
        (OUT / f"{key}-aod.svg").write_text(render(key, fn, True))
    print(f"wrote {len(FACES) * 2} previews to {OUT}")


if __name__ == "__main__":
    main()
