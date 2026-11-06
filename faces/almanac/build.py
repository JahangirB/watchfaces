#!/usr/bin/env python3
"""Build the Almanac watch face (Watch Face Format v2) into an installable APK.

Steps:
  1. fonts   - cut static Fraunces / Newsreader instances (OFL) into res/font
  2. images  - export engraved glyphs, moon phases, scale hatch and marker as PNG
  3. xml     - generate res/raw/watchface.xml, watch_face_info.xml, strings.xml
  4. check   - validate watchface.xml against the official WFF v2 XSD
  5. apk     - aapt2 compile/link, zipalign, apksigner  ->  dist/almanac-<ver>.apk

Requirements: Android SDK (build-tools 34, platform android-34) at $ANDROID_HOME
or /opt/android-sdk; Python fonttools + Pillow; Node Playwright (for PNG export);
xmllint; a WFF v2 XSD folder ($WFF_XSD or /tmp/wffxsd).

Usage: python3 faces/almanac/build.py [--skip-images] [--skip-fonts]
"""
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import almanac_render as AR  # noqa: E402  (design source of truth for glyph drawing)

VERSION_NAME, VERSION_CODE = "1.0.0", 1
PACKAGE = "io.github.jahangirb.watchface.almanac"
SRC = HERE / "src"
RES = SRC / "res"
DIST = ROOT / "dist"
SDK = Path(os.environ.get("ANDROID_HOME", "/opt/android-sdk"))
BT = SDK / "build-tools" / "34.0.0"
ANDROID_JAR = SDK / "platforms" / "android-34" / "android.jar"
XSD = Path(os.environ.get("WFF_XSD", "/tmp/wffxsd")) / "watchface.xsd"
FONT_SRC = Path(os.environ.get("FONT_SRC", "/tmp/fonts"))
KEYSTORE = Path(os.environ.get("ALMANAC_KEYSTORE", ROOT / ".keys" / "almanac.jks"))

W = 466
C = W / 2

# ------------------------------------------------------------------ palettes (from the concept)
PAL = {
    "morning": dict(ink="#ECE6DA", accent="#F4B77E", tick="#6E675E", time="#EFE7DA"),
    "day":     dict(ink="#ECF0F4", accent="#8FC7FF", tick="#5E6670", time="#ECF0F4"),
    "evening": dict(ink="#ECE6F3", accent="#C6A8F5", tick="#665E72", time="#ECE6F3"),
    "night":   dict(ink="#D9483B", accent="#D9483B", tick="#5A1D18", time="#FF6B57"),
}
SCHEDULES = [  # id, label, wake, sleep
    ("early", "Early 06–21", 6, 21),
    ("standard", "Standard 07–22", 7, 22),
    ("late", "Late 08–23", 8, 23),
]
PRECIP = [4, 5, 6, 7, 9, 10, 11, 12]
HOURS = range(1, 9)  # WFF exposes WEATHER.HOURS.1 .. 8


# ================================================================== 1. fonts
def build_fonts():
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    from fontTools import subset
    out = RES / "font"
    out.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("fraunces_Fraunces.ttf", "almanac_time", dict(opsz=144, wght=300, SOFT=0, WONK=0)),
        ("newsreader_Newsreader.ttf", "almanac_text", dict(opsz=16, wght=400)),
        ("newsreader_Newsreader.ttf", "almanac_text_medium", dict(opsz=16, wght=500)),
        ("newsreader_Newsreader-Italic.ttf", "almanac_text_italic", dict(opsz=16, wght=500)),
    ]
    for src, name, loc in jobs:
        f = TTFont(FONT_SRC / src)
        axes = {a.axisTag for a in f["fvar"].axes}
        inst = instancer.instantiateVariableFont(f, {k: v for k, v in loc.items() if k in axes})
        opts = subset.Options()
        opts.layout_features = ["kern", "liga", "tnum", "lnum"]
        opts.name_IDs = ["*"]
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=list(range(0x20, 0x7F)) + list(range(0xA0, 0x180)) + [0x2013, 0x2014, 0x2019, 0x2026, 0xB0, 0xB7])
        sub.subset(inst)
        inst.save(out / f"{name}.ttf")
    lic = HERE / "fonts"
    lic.mkdir(exist_ok=True)
    shutil.copy(FONT_SRC / "fraunces_OFL.txt", lic / "Fraunces-OFL.txt")
    shutil.copy(FONT_SRC / "newsreader_OFL.txt", lic / "Newsreader-OFL.txt")
    print("fonts:", sorted(p.name for p in out.iterdir()))


# ================================================================== 2. images
NODE_RENDER = r"""
const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const b = await chromium.launch(); const p = await b.newPage();
  for (const j of jobs) {
    await p.setViewportSize({ width: j.w, height: j.h });
    await p.setContent(`<html><body style="margin:0;background:#000">${j.svg}</body></html>`);
    await p.screenshot({ path: j.out, omitBackground: false });
  }
  await b.close();
})();
"""


def _render(jobs):
    with tempfile.TemporaryDirectory() as td:
        js, jf = Path(td) / "r.js", Path(td) / "jobs.json"
        js.write_text(NODE_RENDER)
        jf.write_text(json.dumps(jobs))
        env = dict(os.environ)
        env.setdefault("NODE_PATH", subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip())
        subprocess.run(["node", str(js), str(jf)], check=True, env=env)


def _to_mask(path, crop=None):
    """White-on-black render -> white glyph with luminance as alpha (tintable)."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if crop:
        im = im.crop(crop)
    a = im.convert("L")
    out = Image.new("RGBA", im.size, (255, 255, 255, 0))
    out.putalpha(a)
    out.save(path, optimize=True)
    return out.size


def build_images():
    d = RES / "drawable-nodpi"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("*.png"):
        old.unlink()
    jobs = []
    box = 96
    white = "#FFFFFF"

    def svg(inner, w=box, h=box):
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="{w}" height="{h}" fill="#000"/>{inner}</svg>'

    # weather glyphs: code 0-15 day, 16-31 night variants (only clear / sunny / partly differ)
    for code in range(16):
        for night in (False, True):
            p = f"g{code}{'n' if night else 'd'}_"
            jobs.append(dict(svg=svg(AR.glyph(code, 8, 8, white, p, night=night)), w=box, h=box,
                             out=str(d / f"glyph_{code + (16 if night else 0)}.png")))
    # moon phases for MOON_PHASE_POSITION 0..28
    for pos in range(29):
        ph = pos / 29.53
        inner = AR.moon(48, 48, 30, white, f"m{pos}_", phase=max(0.001, ph))
        jobs.append(dict(svg=svg(inner), w=box, h=box, out=str(d / f"moon_{pos}.png")))
    # 24 h scale: one hour of night hatching (15 degrees at the top) and the now marker
    hatch = []
    a = -7.5 + 1.1
    while a < 7.5:
        x0, y0 = AR.pol(213, a)
        x1, y1 = AR.pol(219, a)
        hatch.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="#fff" stroke-width="1.1"/>')
        a += 2.2
    jobs.append(dict(svg=svg("".join(hatch), W, W), w=W, h=W, out=str(d / "scale_hatch.png")))
    tip, bl, br = AR.pol(221, 0), AR.pol(208, -3), AR.pol(208, 3)
    tri = f'<path d="M{tip[0]:.2f} {tip[1]:.2f} L{bl[0]:.2f} {bl[1]:.2f} L{br[0]:.2f} {br[1]:.2f} Z" fill="#fff"/>'
    jobs.append(dict(svg=svg(tri, W, W), w=W, h=W, out=str(d / "now_marker.png")))
    # steps icon used when the complication has no image
    _render(jobs)
    crops = {}
    for j in jobs:
        name = Path(j["out"]).name
        if name in ("scale_hatch.png", "now_marker.png"):
            from PIL import Image
            bb = Image.open(j["out"]).convert("L").getbbox()
            bb = (bb[0] - 1, bb[1] - 1, bb[2] + 1, bb[3] + 1)
            crops[name] = bb
            _to_mask(j["out"], bb)
        else:
            _to_mask(j["out"])
    # preview for the watch face picker: the morning mockup
    prev = ROOT / "previews" / "almanac" / "morning.svg"
    _render([dict(svg=prev.read_text(), w=W, h=W, out=str(d / "preview.png"))])
    (HERE / "build" ).mkdir(exist_ok=True)
    (HERE / "build" / "crops.json").write_text(json.dumps(crops))
    print("images:", len(list(d.glob("*.png"))), "png; crops", crops)


# ================================================================== 3. xml
def q(expr):
    """Escape an expression for use inside an XML attribute."""
    return escape(expr, {'"': "&quot;"})


def cdata(expr):
    return f"<![CDATA[{expr}]]>"


def is_precip(n):
    c = f"[WEATHER.HOURS.{n}.CONDITION]"
    return f"([WEATHER.HOURS.{n}.IS_AVAILABLE] && (" + " || ".join(f"{c} == {k}" for k in PRECIP) + "))"


def precip_now():
    c = "[WEATHER.CONDITION]"
    return "(" + " || ".join(f"{c} == {k}" for k in PRECIP) + ")"


def first(pred, val, fallback):
    """Nested ternary: value for the first hour n in 1..8 where pred(n) holds."""
    e = fallback
    for n in reversed(HOURS):
        e = f"({pred(n)} ? {val(n)} : {e})"
    return e


def any_of(pred):
    return "(" + " || ".join(pred(n) for n in HOURS) + ")"


HOUR_N = lambda n: f"(([HOUR_0_23] + {n}) % 24)"
H12 = lambda h: f"(({h}) % 12 == 0 ? 12 : ({h}) % 12)"
AMPM = lambda h: f'(({h}) < 12 ? "am" : "pm")'
IS_DAY_N = lambda n: f"([WEATHER.HOURS.{n}.IS_AVAILABLE] && [WEATHER.HOURS.{n}.IS_DAY])"


def glyph_code(cond, isday):
    return f"(({cond}) <= 15 ? ({cond}) : 0) + (({isday}) ? 0 : 16)"


def text_part(name, x, y, w, h, font, size, color, template, params=(), align="START", slant=None, extra=""):
    ps = "".join(f'<Parameter expression="{q(p)}"/>' for p in params)
    sl = f' slant="{slant}"' if slant else ""
    # a Template needs at least one Parameter; static text goes straight into Font
    body = f"<Template>{cdata(template)}{ps}</Template>" if params else escape(template.replace("%%", "%"))
    return (f'<PartText name="{name}" x="{x}" y="{y}" width="{w}" height="{h}">{extra}'
            f'<Text align="{align}" ellipsis="TRUE"><Font family="{font}" size="{size}" color="{color}"{sl}>'
            f'{body}</Font></Text></PartText>')


def condition(name, branches, default=None):
    """branches: list of (expression, xml). First true wins."""
    exprs = "".join(f'<Expression name="{name}_{i}">{cdata(e)}</Expression>' for i, (e, _) in enumerate(branches))
    comps = "".join(f'<Compare expression="{name}_{i}">{x}</Compare>' for i, (_, x) in enumerate(branches))
    dflt = f"<Default>{default}</Default>" if default else ""
    return f"<Condition><Expressions>{exprs}</Expressions>{comps}{dflt}</Condition>"


def group(name, inner, x=0, y=0, w=W, h=W, attrs="", pre=""):
    return f'<Group name="{name}" x="{x}" y="{y}" width="{w}" height="{h}"{attrs}>{pre}{inner}</Group>'


AMBIENT_HIDE = '<Variant mode="AMBIENT" target="alpha" value="0"/>'
TX, LA_Y, LB_Y, LINE_H, LINE_W = 178, 258, 296, 34, 250
GX, GY, GS = 82, 250, 80


def line_a(part, P, uid):
    acc, font = P["accent"], "almanac_text_italic"
    T = lambda tmpl, params=(): text_part(f"{uid}_a", TX, LA_Y, LINE_W, LINE_H, font, 24, acc, tmpl, params)
    nodata = T("No forecast yet")
    if part in ("morning", "day"):
        name_first = first(is_precip, lambda n: f"[WEATHER.HOURS.{n}.CONDITION_NAME]", '""')
        hour_first = first(is_precip, HOUR_N, "0")
        return condition(f"{uid}_a", [
            ("![WEATHER.IS_AVAILABLE]", nodata),
            (precip_now(), T("%s now", ["[WEATHER.CONDITION_NAME]"])),
            (f"{any_of(is_precip)} && [IS_24_HOUR_MODE]", T("%s from %s:00", [name_first, f'numberFormat("00", {hour_first})'])),
            (any_of(is_precip), T("%s from %s %s", [name_first, H12(hour_first), AMPM(hour_first)])),
        ], T("No rain expected"))
    if part == "evening":
        return condition(f"{uid}_a", [
            ("[WEATHER.IS_AVAILABLE] && [WEATHER.DAYS.1.IS_AVAILABLE]",
             T("Tomorrow: %s", ["[WEATHER.DAYS.1.CONDITION_DAY_NAME]"])),
        ], nodata)
    return T("%s", ["[MOON_PHASE_TYPE_STRING]"])  # night


def line_b(part, P, uid, wake, sleep):
    ink = P["ink"]
    T = lambda tmpl, params=(): text_part(f"{uid}_b", TX, LB_Y, LINE_W, LINE_H, "almanac_text", 24, ink, tmpl, params)
    status = [
        ("![WEATHER.IS_AVAILABLE]", T("Check connection")),
        ("[WEATHER.IS_ERROR]", T("Last update failed")),
        ("([UTC_TIMESTAMP] - [WEATHER.LAST_UPDATED]) > 10800000",
         T("Forecast %s h old", ["floor(([UTC_TIMESTAMP] - [WEATHER.LAST_UPDATED]) / 3600000)"])),
    ]
    if part == "morning":
        body = T("High %s° · low %s°", ["[WEATHER.DAY_TEMPERATURE_HIGH]", "[WEATHER.DAY_TEMPERATURE_LOW]"])
        return condition(f"{uid}_b", status, body)
    if part == "day":
        diff = f"([STEP_COUNT] - [STEP_GOAL] * clamp(([HOUR_0_23_MINUTE] - {wake}) / {sleep - wake}, 0, 1))"
        pace = condition(f"{uid}_p", [
            ("[STEP_COUNT] >= [STEP_GOAL]", T("Step goal reached")),
            (f"{diff} >= 0", T("+%s steps ahead", [f'numberFormat("#,##0", round({diff}))'])),
        ], T("%s steps behind", [f'numberFormat("#,##0", round(0 - {diff}))']))
        return condition(f"{uid}_b", status, pace)
    if part == "evening":
        body = condition(f"{uid}_e", [
            ("[WEATHER.DAYS.1.IS_AVAILABLE]", T("High %s° · rain %s%%",
                                                ["[WEATHER.DAYS.1.TEMPERATURE_HIGH]", "[WEATHER.DAYS.1.CHANCE_OF_PRECIPITATION]"])),
        ], T("Tomorrow unknown"))
        return condition(f"{uid}_b", status, body)
    # night: first daylight hour within the forecast
    hour_light = first(IS_DAY_N, HOUR_N, "0")
    after = HOUR_N(8)
    return condition(f"{uid}_b", [
        ("![WEATHER.IS_AVAILABLE]", T("Check connection")),
        (f"{any_of(IS_DAY_N)} && [IS_24_HOUR_MODE]", T("Light at %s:00", [f'numberFormat("00", {hour_light})'])),
        (any_of(IS_DAY_N), T("Light at %s %s", [H12(hour_light), AMPM(hour_light)])),
        ("[IS_24_HOUR_MODE]", T("Light after %s:00", [f'numberFormat("00", {after})'])),
    ], T("Light after %s %s", [H12(after), AMPM(after)]))


def plate_glyph(part, P, uid):
    tint = P["accent"]
    def bm(family, expr):
        return (f'<PartText name="{uid}_g" x="{GX}" y="{GY}" width="{GS}" height="{GS}" tintColor="{tint}">'
                f'<Text align="CENTER"><BitmapFont family="{family}" size="{GS}">'
                f'<Template>%s<Parameter expression="{q(expr)}"/></Template></BitmapFont></Text></PartText>')
    if part == "night":
        return bm("almanac_moon", "clamp([MOON_PHASE_POSITION], 0, 28)")
    now = glyph_code("[WEATHER.CONDITION]", "[WEATHER.IS_DAY]")
    if part == "morning":
        expr = f"([WEATHER.IS_AVAILABLE] ? {now} : 0)"
    elif part == "day":
        nxt = first(is_precip, lambda n: f"({glyph_code(f'[WEATHER.HOURS.{n}.CONDITION]', f'[WEATHER.HOURS.{n}.IS_DAY]')})", now)
        expr = f"([WEATHER.IS_AVAILABLE] ? ({precip_now()} ? {now} : {nxt}) : 0)"
    else:
        expr = "([WEATHER.DAYS.1.IS_AVAILABLE] ? (([WEATHER.DAYS.1.CONDITION_DAY] <= 15) ? [WEATHER.DAYS.1.CONDITION_DAY] : 0) : 0)"
    return bm("almanac_glyph", expr)


def scale(part, P, uid, crops):
    ticks = []
    for h in range(24):
        a = (h - 12) * 15
        major = h % 6 == 0
        x0, y0 = AR.pol(226, a)
        x1, y1 = AR.pol(226 - (10 if major else 5), a)
        ticks.append(f'<Line startX="{x0:.2f}" startY="{y0:.2f}" endX="{x1:.2f}" endY="{y1:.2f}">'
                     f'<Stroke color="{P["tick"]}" thickness="{2 if major else 1.2}" cap="ROUND"/></Line>')
    out = [f'<PartDraw name="{uid}_ticks" x="0" y="0" width="{W}" height="{W}">{"".join(ticks)}</PartDraw>']
    hx0, hy0, hx1, hy1 = crops["scale_hatch.png"]
    hatches = []
    for n in range(0, 9):
        if n == 0:
            cond = "[WEATHER.IS_AVAILABLE] && ![WEATHER.IS_DAY]"
        else:
            cond = f"[WEATHER.IS_AVAILABLE] && [WEATHER.HOURS.{n}.IS_AVAILABLE] && ![WEATHER.HOURS.{n}.IS_DAY]"
        ang = f"({HOUR_N(n)} - 12) * 15 + 7.5"
        img = (f'<PartImage name="{uid}_h{n}_img" x="{hx0}" y="{hy0}" width="{hx1 - hx0}" height="{hy1 - hy0}" tintColor="{P["accent"]}">'
               f'<Image resource="scale_hatch"/></PartImage>')
        rot = group(f"{uid}_h{n}", img, attrs=' pivotX="0.5" pivotY="0.5"',
                    pre=f'<Transform target="angle" value="{q(ang)}"/>'
                        f'<Transform target="alpha" value="{q("([UTC_TIMESTAMP] - [WEATHER.LAST_UPDATED]) > 10800000 ? 90 : 220")}"/>')
        hatches.append(condition(f"{uid}_h{n}c", [(cond, rot)]))
    out.append(f'<BooleanConfiguration id="scale"><BooleanOption id="TRUE">{group(f"{uid}_hatches", "".join(hatches))}</BooleanOption></BooleanConfiguration>')
    mx0, my0, mx1, my1 = crops["now_marker.png"]
    marker = (f'<PartImage name="{uid}_mk_img" x="{mx0}" y="{my0}" width="{mx1 - mx0}" height="{my1 - my0}" tintColor="{P["accent"]}">'
              f'<Image resource="now_marker"/></PartImage>')
    out.append(group(f"{uid}_mk", marker, attrs=' pivotX="0.5" pivotY="0.5"',
                     pre=f'<Transform target="angle" value="{q("([HOUR_0_23_MINUTE] - 12) * 15")}"/>'))
    return group(f"{uid}_scale", "".join(out), pre=AMBIENT_HIDE)


def label(part, P, uid):
    word = part.upper()
    return (f'<Group name="{uid}_label" x="0" y="0" width="{W}" height="{W}">{AMBIENT_HIDE}'
            f'<PartText name="{uid}_label_t" x="0" y="0" width="{W}" height="{W}">'
            f'<TextCircular centerX="{C}" centerY="{C}" width="352" height="352" startAngle="-80" endAngle="80" align="CENTER" direction="CLOCKWISE">'
            f'<Font family="almanac_text_medium" size="24" color="{P["ink"]}" letterSpacing="0.08"><Upper><Template>'
            f'{cdata(word + " · %s %s %s")}<Parameter expression="[DAY_OF_WEEK_S]"/><Parameter expression="[DAY]"/>'
            f'<Parameter expression="[MONTH_S]"/></Template></Upper></Font></TextCircular></PartText></Group>')


def clock(P, uid):
    tt = lambda color, deco="": (f'<TimeText format="hh:mm" hourFormat="SYNC_TO_DEVICE" align="CENTER" x="0" y="0" width="{W}" height="130">'
                                 f'<Font family="almanac_time" size="120" color="{color}">{deco}</Font></TimeText>')
    active = f'<DigitalClock x="0" y="100" width="{W}" height="130">{AMBIENT_HIDE}{tt(P["time"])}</DigitalClock>'
    # TimeText fonts can't take an Outline, so the always-on time is a PartText
    # built from the time sources, following the 12/24 h setting.
    def outlined(hour_src):
        return (f'<PartText name="{uid}_aod_t" x="0" y="0" width="{W}" height="130"><Text align="CENTER">'
                f'<Font family="almanac_time" size="120" color="#00000000"><Outline color="{P["time"]}" width="1.6"/>'
                f'<Template>%s:%s<Parameter expression="{hour_src}"/><Parameter expression="[MINUTE_Z]"/></Template>'
                f'</Font></Text></PartText>')
    ambient = group(f"{uid}_aod", condition(f"{uid}_aodc", [("[IS_24_HOUR_MODE]", outlined("[HOUR_0_23_Z]"))],
                                            outlined("[HOUR_1_12_Z]")),
                    y=100, h=130, attrs=' alpha="0"', pre='<Variant mode="AMBIENT" target="alpha" value="255"/>')
    return active + ambient


def part_face(part, uid, wake, sleep, crops):
    P = PAL[part]
    inner = [
        scale(part, P, uid, crops),
        label(part, P, uid),
        clock(P, uid),
        group(f"{uid}_glyph", plate_glyph(part, P, uid), pre='<Variant mode="AMBIENT" target="alpha" value="178"/>'),
        line_a(part, P, uid),
        group(f"{uid}_lb", line_b(part, P, uid, wake, sleep), pre=AMBIENT_HIDE),
    ]
    return group(f"{uid}", "".join(inner))


def part_switch(prefix, wake, sleep, body):
    """Choose the part of the day from the clock and the schedule preset."""
    m_end = wake + 4
    h = "[HOUR_0_23_MINUTE]"
    return condition(f"{prefix}_part", [
        (f"{h} >= {wake} && {h} < {m_end}", body("morning")),
        (f"{h} >= {m_end} && {h} < 18", body("day")),
        (f"{h} >= 18 && {h} < {sleep}", body("evening")),
    ], body("night"))


def complication_body(prefix, wake, sleep):
    def colored(part):
        P = PAL[part]
        uid = f"{prefix}_{part[0]}"
        ring = (f'<PartDraw name="{uid}_ring" x="0" y="0" width="96" height="96"><Ellipse x="1" y="1" width="94" height="94">'
                f'<Fill color="#000000"/><Stroke color="{P["tick"]}" thickness="1.5"/></Ellipse></PartDraw>')
        icon = (f'<PartImage name="{uid}_icon" x="35" y="14" width="26" height="26" tintColor="{P["ink"]}">'
                f'<Image resource="[COMPLICATION.MONOCHROMATIC_IMAGE]"/></PartImage>')
        txt = text_part(f"{uid}_txt", 4, 44, 88, 34, "almanac_text_medium", 24, P["ink"], "%s", ["[COMPLICATION.TEXT]"], align="CENTER")
        return group(uid, ring + icon + txt, w=96, h=96)
    return part_switch(prefix, wake, sleep, colored)


def build_xml(crops):
    raw = RES / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    glyph_chars = "".join(
        (f'<Character name="{i}" resource="glyph_{i}" width="96" height="96"/>' if i < 10 else
         f'<Word name="{i}" resource="glyph_{i}" width="96" height="96"/>') for i in range(32))
    moon_chars = "".join(
        (f'<Character name="{i}" resource="moon_{i}" width="96" height="96"/>' if i < 10 else
         f'<Word name="{i}" resource="moon_{i}" width="96" height="96"/>') for i in range(29))
    configs = ('<UserConfigurations>'
               '<ListConfiguration id="schedule" displayName="@string/cfg_schedule" defaultValue="standard">'
               + "".join(f'<ListOption id="{sid}" displayName="@string/sched_{sid}"/>' for sid, _, _, _ in SCHEDULES)
               + '</ListConfiguration>'
               '<BooleanConfiguration id="scale" displayName="@string/cfg_scale" defaultValue="TRUE"/>'
               '</UserConfigurations>')
    options = []
    for sid, _, wake, sleep in SCHEDULES:
        body = lambda part, sid=sid, wake=wake, sleep=sleep: part_face(part, f"{sid}_{part}", wake, sleep, crops)
        options.append(f'<ListOption id="{sid}">{group(f"face_{sid}", part_switch(sid, wake, sleep, body))}</ListOption>')
    comp_opts = "".join(
        f'<ListOption id="{sid}">{group(f"comp_{sid}", complication_body(f"c_{sid}", wake, sleep), w=96, h=96)}</ListOption>'
        for sid, _, wake, sleep in SCHEDULES)
    complication = (
        '<ComplicationSlot slotId="0" x="185" y="338" width="96" height="96" displayName="@string/slot_bottom" '
        'supportedTypes="SHORT_TEXT RANGED_VALUE EMPTY" isCustomizable="TRUE">'
        '<DefaultProviderPolicy defaultSystemProvider="STEP_COUNT" defaultSystemProviderType="SHORT_TEXT"/>'
        '<BoundingOval x="0" y="0" width="96" height="96"/>'
        f'{AMBIENT_HIDE}'
        f'<Complication type="SHORT_TEXT">{group("comp_st", f"<ListConfiguration id=\"schedule\">{comp_opts}</ListConfiguration>", w=96, h=96)}</Complication>'
        f'<Complication type="RANGED_VALUE">{group("comp_rv", f"<ListConfiguration id=\"schedule\">{comp_opts}</ListConfiguration>", w=96, h=96)}</Complication>'
        '</ComplicationSlot>')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<!-- Generated by faces/almanac/build.py ({VERSION_NAME}). Do not edit by hand. -->\n'
           f'<WatchFace width="{W}" height="{W}">'
           '<Metadata key="CLOCK_TYPE" value="DIGITAL"/>'
           '<Metadata key="PREVIEW_TIME" value="07:42:00"/>'
           f'{configs}'
           f'<BitmapFonts><BitmapFont name="almanac_glyph">{glyph_chars}</BitmapFont>'
           f'<BitmapFont name="almanac_moon">{moon_chars}</BitmapFont></BitmapFonts>'
           '<Scene backgroundColor="#FF000000">'
           f'{group("root", "<ListConfiguration id=\"schedule\">" + "".join(options) + "</ListConfiguration>")}'
           f'{complication}'
           '</Scene></WatchFace>\n')
    (raw / "watchface.xml").write_text(xml)
    (RES / "xml").mkdir(exist_ok=True)
    (RES / "xml" / "watch_face_info.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<WatchFaceInfo>\n'
        '  <Preview value="@drawable/preview" />\n  <Category value="CATEGORY_EMPTY" />\n'
        '  <AvailableInRetail value="false" />\n  <MultipleInstancesAllowed value="true" />\n'
        '  <Editable value="true" />\n</WatchFaceInfo>\n')
    (RES / "values").mkdir(exist_ok=True)
    strings = {"app_name": "Almanac", "cfg_schedule": "Day schedule", "cfg_scale": "Light scale",
               "slot_bottom": "Bottom", **{f"sched_{sid}": lab for sid, lab, _, _ in SCHEDULES}}
    (RES / "values" / "strings.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
        + "".join(f'    <string name="{k}">{escape(v)}</string>\n' for k, v in strings.items()) + '</resources>\n')
    (SRC / "AndroidManifest.xml").write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{PACKAGE}">
    <uses-feature android:name="android.hardware.type.watch" />
    <application android:label="@string/app_name" android:hasCode="false">
        <meta-data android:name="com.google.android.wearable.standalone" android:value="true" />
        <property android:name="com.google.wear.watchface.format.version" android:value="2" />
        <property android:name="com.google.wear.watchface.format.publisher" android:value="almanac-build.py-{VERSION_NAME}" />
    </application>
</manifest>
''')
    print("xml:", round(len(xml) / 1024), "KB")


# ================================================================== 4. check
VALIDATOR = Path(os.environ.get("WFF_VALIDATOR", "/tmp/vpc.jar"))


def check(apk):
    """Run Google's Watch Face validator (validator-push-cli) on the built APK.

    It checks the WFF XML against the official schema, the memory footprint and
    the Watch Face Push packaging rules. The push-only rules (package name
    prefix, etc.) do not apply to a sideloaded face and are reported but ignored."""
    if not VALIDATOR.exists():
        print("validator: skipped (set WFF_VALIDATOR to validator-push-cli.jar)")
        return
    r = subprocess.run(["java", "-jar", str(VALIDATOR), "--apk_path", str(apk),
                        "--package_name", PACKAGE.rsplit(".", 1)[0]], capture_output=True, text=True)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if "JAVA_TOOL_OPTIONS" not in l)
    (HERE / "build" / "validator.txt").write_text(out)
    print(out[-4000:])


# ================================================================== 5. apk
def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit(f"failed: {cmd[0]}")
    return r.stdout


def build_apk():
    work = HERE / "build"
    shutil.rmtree(work / "compiled", ignore_errors=True)
    (work / "compiled").mkdir(parents=True)
    run([BT / "aapt2", "compile", "--dir", RES, "-o", work / "compiled" / "res.zip"])
    unsigned = work / "almanac-unsigned.apk"
    run([BT / "aapt2", "link", "-o", unsigned, "-I", ANDROID_JAR, "--manifest", SRC / "AndroidManifest.xml",
         "--min-sdk-version", "34", "--target-sdk-version", "34", "--version-code", VERSION_CODE,
         "--version-name", VERSION_NAME, "--rename-manifest-package", PACKAGE,
         "-R", work / "compiled" / "res.zip", "--auto-add-overlay"])
    aligned = work / "almanac-aligned.apk"
    run([BT / "zipalign", "-p", "-f", "4", unsigned, aligned])
    if not KEYSTORE.exists():
        KEYSTORE.parent.mkdir(parents=True, exist_ok=True)
        run(["keytool", "-genkeypair", "-keystore", KEYSTORE, "-storepass", "almanac", "-keypass", "almanac",
             "-alias", "almanac", "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
             "-dname", "CN=Almanac watch face, O=JahangirB watchfaces"])
    DIST.mkdir(exist_ok=True)
    out = DIST / f"almanac-{VERSION_NAME}.apk"
    run([BT / "apksigner", "sign", "--v2-signing-enabled", "true", "--v3-signing-enabled", "true", "--ks", KEYSTORE, "--ks-pass", "pass:almanac", "--key-pass", "pass:almanac",
         "--ks-key-alias", "almanac", "--out", out, aligned])
    print(run([BT / "apksigner", "verify", "--verbose", out]).strip().splitlines()[:4])
    print("apk:", out, round(out.stat().st_size / 1024), "KB")
    return out


if __name__ == "__main__":
    if "--skip-fonts" not in sys.argv:
        build_fonts()
    if "--skip-images" not in sys.argv:
        build_images()
    crops = json.loads((HERE / "build" / "crops.json").read_text())
    build_xml(crops)
    check(build_apk())
