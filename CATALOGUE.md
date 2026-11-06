# Watch Face Catalogue: OnePlus Watch 3

These are the planned watch faces for this repository. Each one will be built
for the OnePlus Watch 3 and published as a free download on GitHub Releases.

## Target hardware and platform

| Item | Value |
|---|---|
| Display | 1.5" round LTPO AMOLED, **466 × 466 px** |
| OS | Wear OS 5 or later (OxygenOS Watch) |
| Face technology | **Watch Face Format (WFF)**: declarative XML, no app code |
| Packaging | Resource-only APK, one per face |
| Distribution | GitHub Releases. Users sideload with ADB over Wi-Fi, or with a phone app such as *Wear Installer* or *Bugjaeger* |

**Why WFF:** Google requires Watch Face Format for new watch faces on Wear OS 5
and later. The system renders a WFF face itself, so it uses less battery than
an old code-based face, and it has a proper ambient (always-on) mode. A WFF
APK contains no executable code, which also makes it safer for people to
sideload from GitHub.

**Battery rules for every face:**
- Use black backgrounds. On AMOLED, black pixels are switched off.
- Keep ambient (AOD) mode to about 15% of pixels lit or less, using only
  outlines and thin strokes.
- Don't animate anything while the watch is in ambient mode.

> Note: when the watch 3 is in its RTOS power-saver mode, it shows OnePlus's own
> built-in faces. Custom faces appear only while Wear OS is running.

---

## Catalogue at a glance

| # | Name | Style | Type | Complications | Difficulty | Release |
|---|---|---|---|---|---|---|
| 01 | **Monolith** | Bold minimal | Digital | 1 | ★☆☆ | v1.0 |
| 02 | **Meridian** | Clean classic | Analog | 4 | ★☆☆ | v1.0 |
| 03 | **Pulse** | Fitness | Digital + rings | 3 + steps goal | ★★☆ | v1.0 |
| 04 | **Tidal** | Ambient gradient | Digital | 2 | ★★☆ | v1.0 |
| 05 | **Field Line** | Tool watch | Analog | 3 | ★★☆ | v1.1 |
| 06 | **Terminal** | Retro CLI | Digital | 4 | ★★☆ | v1.1 |
| 07 | **Daylight** | Sun-arc | Hybrid | 2 | ★★☆ | v1.1 |
| 08 | **Dashboard** | Data-dense | Digital | 6 | ★★☆ | v1.1 |
| 09 | **Orbit** | Space / playful | Analog | 2 | ★★★ | v1.2 |
| 10 | **Lunar** | Moon phase | Analog | 2 | ★★★ | v1.2 |
| 11 | **Wordsmith** | Word clock | Text | 0–1 | ★★★ | v1.2 |
| 12 | **Bits** | Binary / dot-matrix | Digital | 1 | ★★★ | v1.2 |

Difficulty refers to how hard the face is to build in WFF. The release
column is a suggested order. v1.0 covers the core styles that most people want.

---

## Face details

### 01 · Monolith: bold minimal digital
- **Look:** Very large, condensed hour digits stacked over the minute digits,
  centered on a black background. The date sits in small caps under the minutes.
- **Complications:** 1 slot at the bottom, defaulting to battery.
- **Customization:** 8 accent colors, a 12/24h toggle, and a choice of filled
  or outline digits.
- **AOD:** Digits are drawn as 2px outlines and the complication is hidden.
- **Why it's first:** It's the simplest build, so we can use it to set up the
  repo, the build and the release pipeline from start to finish.

### 02 · Meridian: clean classic analog
- **Look:** Thin baton indices, a minute track, tapered hands and a red sweep
  seconds hand.
- **Complications:** 4 slots (top, bottom, left and right). Small circular
  ones work for battery, steps, heart rate and weather.
- **Customization:** Dial colors (black, navy, forest or sand), hand colors,
  and a choice of numerals at 12/3/6/9 or none.
- **AOD:** Hands and indices only, with no seconds hand.

### 03 · Pulse: fitness-first
- **Look:** Digital time in the center, with three concentric arc rings
  around the edge for steps, calories and active minutes, fitness-ring style.
- **Complications:** 3 ranged-value slots that feed the rings, plus heart
  rate as text.
- **Customization:** Ring color sets, and a choice of which metric each
  ring shows.
- **AOD:** Time only, with the rings dimmed to 30% opacity.

### 04 · Tidal: shifting gradient
- **Look:** A soft radial gradient whose colors change through the day:
  deep indigo at night, teal in the morning, amber in the evening. Thin
  digital time sits on top.
- **Complications:** 2 (date and weather).
- **Customization:** Gradient palettes (Ocean, Ember, Aurora or Mono).
- **AOD:** The gradient switches off and only the time is drawn, in the
  palette's accent color.

### 05 · Field Line: legible tool watch
- **Look:** Large Arabic numerals with an inner 13–24 hour ring, high-contrast
  luminous-style hands and an arrow at 12.
- **Complications:** 3 subdials (date, battery, steps).
- **Customization:** Lume color (green, blue or white), a toggle for the
  24h ring, and dial texture (matte or grained).
- **AOD:** Hands and numerals in the lume color only.

### 06 · Terminal: retro command line
- **Look:** Monospace green-phosphor text in the style of a shell session:
  ```
  $ time   14:32
  $ date   THU 06 NOV
  $ steps  8,421
  $ batt   72%
  ```
  It also has a blinking block cursor.
- **Complications:** 4 text slots.
- **Customization:** Phosphor color (green, amber or white), and optional
  scanlines.
- **AOD:** Only the `$ time` line, with no cursor.

### 07 · Daylight: sun-arc hybrid
- **Look:** A half-circle arc across the top showing today's daylight. A sun
  marker moves along it, and below the horizon line the moon marks the night.
  Digital time sits underneath.
- **Complications:** Sunrise/sunset in the arc ends, plus 1 free slot.
- **Customization:** Arc style (thin line or filled band), and an accent color.
- **AOD:** The arc outline and time only.

### 08 · Dashboard: data-dense grid
- **Look:** Compact time at the top, with a 2 × 3 grid of complication tiles
  below it. It's built for people who want everything visible at once.
- **Complications:** 6 slots of mixed types (short text, ranged, small image).
- **Customization:** Tile style (outlined or filled), accent color.
- **AOD:** Time and the top two tiles.

### 09 · Orbit: planetary hands
- **Look:** The hour and minute "hands" are two planets orbiting a central
  sun along faint orbit lines. A small moon orbits the minute planet to
  mark the seconds.
- **Complications:** 2 small slots in the corners.
- **Customization:** Planet color sets, and a toggle for showing orbit lines.
- **AOD:** Static orbit lines and planets with no moon. Both are drawn as
  outlines.

### 10 · Lunar: moon-phase dress watch
- **Look:** An elegant analog dial with a large moon-phase window at 6
  o'clock, driven by WFF's built-in moon-phase data. Fine Roman numerals.
- **Complications:** 2 (date and 1 free slot).
- **Customization:** Dial colors (midnight, ivory-on-black or slate),
  numeral style.
- **AOD:** Hands and the moon outline.

### 11 · Wordsmith: word clock
- **Look:** The time is written out in words, for example *"IT IS TWENTY PAST
  TEN"*. The active words are lit and the others are dimmed, letter-grid style.
- **Complications:** An optional date line.
- **Customization:** Text color, and a toggle between rounding to 5 minutes
  and exact time.
- **AOD:** Only the lit words, with the dimmed grid hidden.
- **Note:** This face needs many WFF `Condition` blocks for the
  hour and minute logic, so it's best built after the pipeline is stable.

### 12 · Bits: binary / dot matrix
- **Look:** BCD binary clock columns of glowing dots, with a small
  human-readable time below for anyone who doesn't read binary.
- **Complications:** 1 (battery).
- **Customization:** Dot color, a toggle for the readable time, and dot
  shape (round or square).
- **AOD:** Lit dots only, with no readable time.

---

## Features shared by every face

- **Native customization** through WFF `UserConfigurations`, so users change
  colors and options in the watch's own long-press **Customize** menu or in
  the OnePlus Health app.
- **12h/24h support** that follows the system setting.
- **Localized date strings** from the system locale.
- **Preview image**, a 466 × 466 PNG for the watch-face picker and the
  README gallery.
- **Every face is an original design.** No brand logos or copies of
  commercial watch dials.

## Proposed repository layout

```
watchfaces/
├── CATALOGUE.md            ← this file
├── README.md               ← gallery, install guide
├── faces/
│   ├── monolith/
│   │   ├── AndroidManifest.xml
│   │   ├── build.gradle.kts
│   │   └── res/
│   │       ├── raw/watchface.xml
│   │       ├── drawable/   (previews, assets)
│   │       ├── font/
│   │       └── xml/watch_face_info.xml
│   ├── meridian/
│   └── ...
├── docs/
│   └── INSTALL.md          ← step-by-step sideload guide
└── .github/workflows/
    └── release.yml         ← builds + validates every face, attaches APKs to a release
```

- **CI:** A GitHub Actions workflow builds each face, runs Google's WFF XML
  validator and memory-footprint checker, and attaches signed APKs to a
  GitHub Release whenever a tag is pushed.
- **Install guide:** Covers ADB over Wi-Fi from a computer and a phone-only
  route.

## Suggested next step

Build **01 Monolith** first. It sets up the Gradle project, the WFF schema,
validation, CI and the install guide. The other faces reuse that setup, so
each later face mostly comes down to writing one XML file and adding some
artwork.
