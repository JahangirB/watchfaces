#!/usr/bin/env python3
"""Audit the Almanac previews against concepts/almanac/ACCEPTANCE.md.

Measures every automatic (A) criterion on the rendered SVGs with headless
Chromium, combines them with the documented reviewer (R/D) scores below, and
writes concepts/almanac/AUDIT.md + audit.json.

Usage: python3 tools/almanac_audit.py   (needs Playwright + Chromium, PIL, numpy)
"""
import hashlib
import io
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PV = ROOT / "previews" / "almanac"
OUTDIR = ROOT / "concepts" / "almanac"
S, C = 466, 233
FONTS = ("https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300"
         "&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,500&display=swap")

PARTS = ["morning", "day", "evening", "night"]
STATES = PARTS + [f"{p}-aod" for p in PARTS] + ["nodata", "stale"]
EXTRA_STATES = ["error"]
COND = ["UNKNOWN", "CLEAR", "CLOUDY", "FOG", "HEAVY_RAIN", "HEAVY_SNOW", "RAIN", "SNOW", "SUNNY",
        "THUNDERSTORM", "SLEET", "LIGHT_SNOW", "LIGHT_RAIN", "MIST", "PARTLY_CLOUDY", "WINDY"]

# ---------------------------------------------------------------- browser measurement
JS = r"""
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [svgPath, fontsUrl] = process.argv.slice(2);
  const svg = fs.readFileSync(svgPath, 'utf8');
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 466, height: 466 }, deviceScaleFactor: 1 });
  await p.setContent(`<html><head><link rel="stylesheet" href="${fontsUrl}">
    <style>html,body{margin:0;background:#000}svg{display:block}</style></head><body>${svg}</body></html>`);
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(400);
  const texts = await p.evaluate(() => [...document.querySelectorAll('text[data-role]')].map(t => {
    const n = t.getNumberOfChars(); const chars = [];
    for (let i = 0; i < n; i++) { const e = t.getExtentOfChar(i); chars.push([e.x, e.y, e.width, e.height]); }
    const bb = t.getBBox(); const cs = getComputedStyle(t);
    return { role: t.dataset.role, size: parseFloat(t.getAttribute('font-size')),
             family: t.getAttribute('font-family'), fill: t.getAttribute('fill'), stroke: t.getAttribute('stroke'),
             text: t.textContent, bbox: [bb.x, bb.y, bb.width, bb.height], chars,
             usedFont: cs.fontFamily };
  }));
  const loaded = await p.evaluate(() => [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family + ' ' + f.style + ' ' + f.weight));
  const full = (await p.screenshot()).toString('base64');
  await p.addStyleTag({ content: 'text{visibility:hidden}' });
  const bg = (await p.screenshot()).toString('base64');
  await p.addStyleTag({ content: 'g *{visibility:hidden} text[data-role="time"]{visibility:visible}' });
  const timeOnly = (await p.screenshot()).toString('base64');
  console.log(JSON.stringify({ texts, loaded, full, bg, timeOnly }));
  await b.close();
})();
"""


def measure(svg_path):
    js = Path("/tmp") / "almanac_measure.js"
    js.write_text(JS)
    out = subprocess.run(["node", str(js), str(svg_path), FONTS], capture_output=True, text=True, check=True)
    d = json.loads(out.stdout)
    img = lambda k: np.asarray(Image.open(io.BytesIO(__import__("base64").b64decode(d[k]))).convert("RGB")).astype(float)
    return d, img("full"), img("bg"), img("timeOnly")


# ---------------------------------------------------------------- colour maths
def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def rel_lum(rgb):
    c = np.asarray(rgb, float) / 255
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722


def contrast(l1, l2):
    hi, lo = np.maximum(l1, l2), np.minimum(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def lab(rgb):
    c = np.asarray(rgb, float) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = m @ c / np.array([0.95047, 1.0, 1.08883])
    fx = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * fx[1] - 16, 500 * (fx[0] - fx[1]), 200 * (fx[1] - fx[2])])


def circle_mask():
    yy, xx = np.mgrid[0:S, 0:S]
    return (xx + 0.5 - C) ** 2 + (yy + 0.5 - C) ** 2 <= C * C


MASK = circle_mask()


# ---------------------------------------------------------------- audit
def audit():
    results = {"states": {}, "gates": {}, "scores": {}}
    missing = [s for s in STATES if not (PV / f"{s}.svg").exists()]
    per = {}
    fonts_seen = set()
    for st in STATES + EXTRA_STATES:
        path = PV / f"{st}.svg"
        if not path.exists():
            continue
        d, full, bg, tonly = measure(path)
        fonts_seen.update(d["loaded"])
        texts = []
        for t in d["texts"]:
            col = t["fill"] if t["fill"] not in (None, "none") else t["stroke"]
            tl = rel_lum(hex_rgb(col))
            # per-text background: pixels under every character box
            xs, ys = [], []
            for x, y, w, h in t["chars"]:
                x0, y0 = max(0, int(math.floor(x))), max(0, int(math.floor(y)))
                x1, y1 = min(S, int(math.ceil(x + w))), min(S, int(math.ceil(y + h)))
                if x1 > x0 and y1 > y0:
                    yy, xx = np.mgrid[y0:y1, x0:x1]
                    xs.append(xx.ravel()); ys.append(yy.ravel())
            xs, ys = np.concatenate(xs), np.concatenate(ys)
            bl = rel_lum(bg[ys, xs])
            ratios = contrast(tl, bl)
            worst_r = 0.0
            for x, y, w, h in t["chars"]:
                for cx_, cy_ in ((x, y), (x + w, y), (x, y + h), (x + w, y + h)):
                    worst_r = max(worst_r, math.hypot(cx_ - C, cy_ - C))
            texts.append({"role": t["role"], "text": t["text"], "size": t["size"],
                          "family": t["family"].split(",")[0].strip().strip("'"),
                          "colour": col, "contrast_p5": round(float(np.percentile(ratios, 5)), 2),
                          "max_radius": round(worst_r, 1), "bbox": [round(v, 1) for v in t["bbox"]]})
        lit = full.max(axis=2) > 10
        rows = np.where(tonly.max(axis=2).max(axis=1) > 40)[0]
        time_ink_h = int(rows.max() - rows.min() + 1) if len(rows) else 0
        lum = rel_lum(full)[MASK]
        per[st] = {
            "texts": texts,
            "lit_pct": round(float(lit[MASK].mean() * 100), 2),
            "mean_lum_pct": round(float(lum.mean() * 100), 3),
            "time_ink_px": time_ink_h,
            "roles": sorted({t["role"] for t in texts} | ({"glyph"} if "data-role=\"glyph\"" in path.read_text() else set())),
            "colours": sorted(set(re.findall(r'(?:fill|stroke)="(#[0-9A-Fa-f]{6})"', path.read_text())) - {"#000000", "#000"}),
        }
    results["states"] = per

    interactive = [s for s in per if not s.endswith("-aod")]
    all_texts = [(s, t) for s in per for t in per[s]["texts"]]

    # ---- gates
    g = results["gates"]
    g["G1"] = {"pass": True, "evidence": "Data-source table in ALMANAC.md; every value maps to a documented WFF v2 source or a calculation on them."}
    t_h = {s: per[s]["time_ink_px"] for s in interactive}
    t_c = {s: min(t["contrast_p5"] for t in per[s]["texts"] if t["role"] == "time") for s in interactive}
    g["G2"] = {"pass": all(v >= 80 for v in t_h.values()) and all(v >= 7 for v in t_c.values()),
               "evidence": f"time ink height px {t_h}; time contrast p5 {t_c}"}
    aod = {s: per[s]["lit_pct"] for s in per if s.endswith("-aod")}
    g["G3"] = {"pass": len(aod) == 4 and all(v <= 15 for v in aod.values()), "evidence": f"lit % {aod}"}
    gl = {}
    for name in COND:
        fp = PV / f"glyph-{name.lower()}.svg"
        if fp.exists():
            body = re.sub(r'id="[^"]+"|url\(#[^)]+\)', "", fp.read_text())
            gl[name] = hashlib.sha1(body.encode()).hexdigest()
    g["G4"] = {"pass": len(gl) == 16 and len(set(gl.values())) == 16,
               "evidence": f"{len(gl)} glyph files, {len(set(gl.values()))} distinct"}
    g["G5"] = {"pass": not missing, "evidence": f"{len(STATES) - len(missing)}/{len(STATES)} required states present"
               + (f"; missing {missing}" if missing else "") + f"; extra: {[s for s in EXTRA_STATES if s in per]}"}
    worst = max(all_texts, key=lambda st: st[1]["max_radius"])
    g["G6"] = {"pass": worst[1]["max_radius"] <= 216,
               "evidence": f"outermost glyph corner {worst[1]['max_radius']} px ({worst[0]}: {worst[1]['text']!r})"}

    # ---- scored (A)
    sc = results["scores"]
    mins = min(t["size"] for _, t in all_texts)
    sc["S1"] = (1.0 if mins >= 24 else 0.0, f"smallest text {mins}px")
    lowc = sorted(((t["contrast_p5"], s, t["text"]) for s, t in all_texts))[:3]
    passc = sum(1 for _, t in all_texts if t["contrast_p5"] >= 4.5) / len(all_texts)
    sc["S2"] = (1.0 if passc == 1 else round(passc * 0.5, 3), f"{passc*100:.1f}% of text ≥4.5:1; lowest three {lowc}")
    ratio = min(min(t["size"] for t in per[s]["texts"] if t["role"] == "time") /
                max(t["size"] for t in per[s]["texts"] if t["role"] != "time") for s in interactive)
    sc["S3"] = (1.0 if ratio >= 2.5 else 0.0, f"time / largest other text = {ratio:.2f}")
    units = {s: len(set(per[s]["roles"]) - {"decor", "complication-box"}) for s in per}
    sc["S4"] = (1.0 if max(units.values()) <= 6 else 0.0, f"information units per state {units}")
    acc = {"morning": "#F4B77E", "day": "#8FC7FF", "evening": "#C6A8F5", "night": "#D9483B"}
    de = {f"{a}-{b}": round(float(np.linalg.norm(lab(hex_rgb(acc[a])) - lab(hex_rgb(acc[b])))), 1)
          for i, a in enumerate(acc) for b in list(acc)[i + 1:]}
    sc["S6"] = (1.0 if min(de.values()) >= 20 else 0.5, f"accent ΔE76 pairwise {de}; non-colour cues: part-of-day word, hatching pattern, marker shape")
    nt = per["night"]
    red_ok = all((lambda c: c[0] > c[1] and c[0] > c[2])(hex_rgb(t["colour"])) for t in nt["texts"])
    sc["S7"] = (1.0 if red_ok and nt["mean_lum_pct"] <= 2 else 0.0,
                f"night text red-dominant={red_ok}; mean luminance {nt['mean_lum_pct']}%")
    tb = {s: next(t["bbox"] for t in per[s]["texts"] if t["role"] == "time") for s in PARTS}
    cx = {s: b[0] + b[2] / 2 for s, b in tb.items()}
    spread = max(max(v[i] for v in tb.values()) - min(v[i] for v in tb.values()) for i in (1, 3))
    spread = max(spread, max(cx.values()) - min(cx.values()))
    sc["S8"] = (1.0 if spread <= 2 else 0.0, f"time box spread across parts of day {spread:.2f}px")
    fams = {t["family"] for _, t in all_texts}
    cols = {s: len(per[s]["colours"]) for s in PARTS}
    sc["S16"] = (1.0 if len(fams) <= 2 and max(cols.values()) <= 3 else 0.0, f"typefaces {sorted(fams)}; colours per part {cols}")

    # ---- reviewer / documented scores (justified in ALMANAC.md)
    sc["S5"] = (1.0, "R: each part of the day's glance questions (ALMANAC.md) are answered by visible content")
    sc["S9"] = (1.0, "R: no-data ('No forecast yet / Check connection'), stale ('Forecast 6 h old') and error ('Last update failed') states are drawn")
    sc["S10"] = (0.75, "D: unit, 12/24 h, condition, day and month names come from the system; the fixed phrases ('Rain from', 'High', 'Light at') are English-only until translations are added")
    sc["S11"] = (1.0, "D: 5 options — wake and sleep hours, inks, red night mode, 24 h scale, complication")
    sc["S12"] = (0.5, "D: every mechanism is mapped to a WFF element, but none is proven on the watch yet")
    sc["S13"] = (0.0, "Not run on a OnePlus Watch 3 yet")
    sc["S14"] = (0.0, "No comprehension test with people yet")
    sc["S15"] = (0.5, "R: no known face combines parts of the day with engraved almanac plates; novelty can't be proven exhaustively, so capped at 0.5")

    weights = {"S1": 10, "S2": 10, "S3": 6, "S4": 6, "S5": 6, "S6": 5, "S7": 5, "S8": 5, "S9": 5, "S10": 5,
               "S11": 5, "S12": 6, "S13": 8, "S14": 8, "S15": 5, "S16": 5}
    total = 10 * sum(weights[k] * sc[k][0] for k in weights) / sum(weights.values())
    paper_max = 10 * sum(w for k, w in weights.items() if k not in ("S13", "S14")) / 100 - 10 * (2.5 + 3) / 100
    results["weights"] = weights
    results["score"] = round(total, 4)
    results["gates_pass"] = all(v["pass"] for v in g.values())
    results["paper_ceiling"] = round(paper_max, 3)
    return results


def write_report(r):
    (OUTDIR / "audit.json").write_text(json.dumps(r, indent=1, ensure_ascii=False))
    L = ["# Almanac: audit report", "",
         "Generated by `tools/almanac_audit.py` against [ACCEPTANCE.md](ACCEPTANCE.md). "
         "A = measured on the render, R = reviewer judgement, D = documented mapping.", "",
         f"**Gates: {'all pass' if r['gates_pass'] else 'FAILED'}**  ·  **Score: {r['score']:.2f} / 10**  ·  "
         f"Highest score a paper concept can reach under these rules: {r['paper_ceiling']:.2f}", "",
         "## Gates", "", "| Gate | Result | Evidence |", "|---|---|---|"]
    for k, v in r["gates"].items():
        L.append(f"| {k} | {'PASS' if v['pass'] else 'FAIL'} | {v['evidence']} |")
    L += ["", "## Scored criteria", "", "| ID | Weight | Score | Evidence |", "|---|---|---|---|"]
    for k in r["weights"]:
        s, ev = r["scores"][k]
        L.append(f"| {k} | {r['weights'][k]} | {s:g} | {ev} |")
    L += ["", "## Per-state measurements", "", "| State | Lit pixels | Mean luminance | Time ink height | Smallest text | Lowest contrast |",
          "|---|---|---|---|---|---|"]
    for s, v in r["states"].items():
        L.append(f"| {s} | {v['lit_pct']}% | {v['mean_lum_pct']}% | {v['time_ink_px']} px | "
                 f"{min(t['size'] for t in v['texts']):g} px | {min(t['contrast_p5'] for t in v['texts']):.2f}:1 |")
    (OUTDIR / "AUDIT.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    res = audit()
    write_report(res)
    print(json.dumps({"gates": {k: v["pass"] for k, v in res["gates"].items()}, "score": res["score"],
                      "ceiling": res["paper_ceiling"]}, indent=1))
    for k, (s, ev) in res["scores"].items():
        print(k, s, ev[:160])
    for k, v in res["gates"].items():
        print(k, v["evidence"][:200])
    sys.exit(0)
