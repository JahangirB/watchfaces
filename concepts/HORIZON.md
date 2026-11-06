# Horizon: flagship concept

> **The next 12 hours of weather, drawn on the clock itself.**
> Look at 4 o'clock to see the weather at 4 pm.

| Active | Always-on |
|---|---|
| <img src="../previews/horizon.svg" width="300" alt="Horizon active"> | <img src="../previews/horizon-aod.svg" width="300" alt="Horizon always-on"> |

*Mockup shows Thu 06 Nov, 10:08, with sample forecast data.*

## The idea

On a normal face, the 12 hour positions only tell you the time. Horizon also puts
a forecast at each one. Each hour position carries a segment for the **next time
that hour comes around**. The segment at 2 o'clock shows 2 pm, and the one at
8 o'clock shows 8 pm. The ring rolls forward every hour, so it always covers
the next 12 hours, starting from now.

You can plan your day at a glance. If the hatching starts at 4 o'clock, rain
starts at 4. The shortest, bluest segment is the coldest hour, which is when
you'll want a jacket.

## Anatomy

| # | Element | What it tells you |
|---|---|---|
| 1 | **Forecast band** | 12 segments, one per hour position. The segment's **height** shows the temperature: taller means warmer. Its **colour** runs from blue for cold to amber and orange for warm. |
| 2 | **Now pointer** | The hour hand. It's a small arrow that points into the current hour's segment, and that segment is outlined. |
| 3 | **Seam** | A dashed line where "now" meets "+12 h", so you know where the forecast ends. |
| 4 | **Rain hatching** | Diagonal blue hatching on a segment, getting denser as the rain chance goes up. |
| 5 | **Daylight track** | A thin line under the band, gold during daylight hours and indigo at night. A condition icon (sun, cloud, rain or moon) sits at each hour. |
| 6 | **Pace ring** | The step-goal progress arc, plus a **ghost marker** showing where you *should* be by now to reach your goal by the end of your day. If the green end is past the ghost, you're ahead. |
| 7 | **Rain countdown** | One line of text, worked out from the hourly forecast: "Rain at 16:00 · 60%", or "Dry for the next 12 h". |
| 8 | **Vitals line** | Heart rate, with the heart icon coloured by HR zone. Then today's steps, with how far ahead of or behind pace you are (`+640`). |

## Features

- **Forecast on the dial.** The forecast lines up with real clock positions. I haven't seen another Wear OS face do this.
- **Rain countdown.** The face finds the first hour in the next 12 where the
  rain chance is 50% or more, and shows when it starts and how likely it is.
- **Step pace ghost.** Compares your steps against an even pace across your
  waking day, so it's "am I on track?" rather than just a percentage. You set
  your wake and sleep hours in Customize.
- **HR zones.** The heart icon and its value change colour across 5 zones
  based on your max HR, which you set in Customize.
- **Depth parallax.** The forecast band and the centre sit on separate layers
  that shift slightly as you tilt your wrist, using WFF's gyro support.
- **Sky that follows the day.** The background glow changes from dawn blue to
  day to dusk violet to night.
- **Works without weather data.** If there's no weather data yet, the band
  becomes a plain 12-hour dial with hour ticks and step pace, and shows a small
  "No forecast" note. It never shows an empty ring.
- **Purpose-built always-on mode.** Only the temperature curve's outline, the
  rain dashes, the pointer and the time are lit, at about 6% of pixels. It
  shifts a few pixels every minute to prevent burn-in.

### Customize menu

| Option | Values |
|---|---|
| Band shows | Temperature · Rain chance · UV index |
| Units | °C · °F |
| Colour scale | Thermal (default) · Mono · Colour-blind safe (blue–yellow) |
| Wake / sleep hours | Used by the pace ghost (default 07:00–22:00) |
| Max HR | Used for zone colours (default 190) |
| Parallax | On · Off |
| Slot left / right | 2 complication slots replacing the vitals line, e.g. calendar or battery |

## How it's built (Watch Face Format, no app code)

The whole face is written as declarative WFF XML, with no Kotlin or Java code.
That's what makes it hard to build:

| Problem | Approach |
|---|---|
| The ring has to roll each hour | Build the 12 segments by **offset** (now, +1 h … +11 h) instead of by clock position, and rotate the whole group by `HOUR_0_23 × 30°`. Each segment then reads one fixed data source, `WEATHER.HOURS.<n>`. |
| Segment height and colour per hour | Each segment is an arc whose radius and colour come from expressions on that hour's temperature, normalised against the 12-hour min and max. |
| Rain countdown text | A chain of 12 `Condition` blocks evaluated in order; the first hour that matches wins. |
| Pace ghost position | `(minutes since wake ÷ waking minutes) × 360°` as a `Transform` angle, clamped to the waking window. |
| Too much hand-written XML | A Python generator writes `watchface.xml` from one geometry spec. It's the same idea as `tools/render_horizon.py`, which drew these mockups. |

### Data sources needed

| Data | WFF source |
|---|---|
| Hourly temperature and condition | `WEATHER.HOURS.<n>.*` (WFF v2, Wear OS 5) |
| Rain chance | Hourly rain chance if the watch exposes it. If not, fall back to the hourly condition (rain or showers) |
| Weather available or stale | `WEATHER.IS_AVAILABLE`, `WEATHER.IS_ERROR` |
| Steps / goal | `STEP_COUNT`, `STEP_GOAL` |
| Heart rate | `HEART_RATE` |
| Tilt | `Gyro` element |

### Risks to check on day 1

1. **Which weather fields the Watch 3 actually exposes**, and how many hours
   ahead. Everything else depends on this, so it's the first thing to test on
   the real watch.
2. **Arc radius driven by an expression.** If WFF won't animate the radius, I
   can use the same trick as an equaliser instead: a stack of thin arcs per
   segment, each shown or hidden by a threshold.
3. **Render cost.** Google's memory-footprint tool will measure the layered
   band, which has about 60 elements. Always-on mode has its own lighter tree.

## Development plan (about 6 working days)

| Day | Work |
|---|---|
| 1 | Set up the project, Gradle and CI. Test the weather fields on the watch or emulator. Get Google's validator and memory checker running. |
| 2 | Python XML generator, and the rolling forecast band with temperature height and colour. |
| 3 | Rain hatching, condition icons, daylight track, now pointer and seam. Rain countdown logic. |
| 4 | Centre layout, pace ring and ghost, HR zones, complication slots. |
| 5 | Customize options, the no-weather fallback, parallax, always-on mode and burn-in shift. |
| 6 | Testing on the watch (morning, evening, night, rain and no data), measuring battery and memory, release APK, install guide. |

## Why this one

- **It's useful.** Seeing which hour is when, and its weather, in the same
  place answers "will it rain on my way home?" without opening an app.
- **It's unique.** The forecast sits on the clock positions rather than in a
  separate widget.
- **It's demanding.** It pushes WFF expressions, conditions, transforms and
  gyro, with a generator to keep the XML manageable. It's a real engineering
  project rather than a skin.
