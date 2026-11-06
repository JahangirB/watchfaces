# Almanac: build notes

Almanac is a Watch Face Format (v2) face, with no app code. To install it, see
[docs/INSTALL.md](../../docs/INSTALL.md). The design is described in
[concepts/almanac/ALMANAC.md](../../concepts/almanac/ALMANAC.md).

## Build

```bash
python3 faces/almanac/build.py
```

The script:

1. Cuts static font instances: Fraunces Light (time) and Newsreader Regular,
   Medium and Medium Italic (text). Both are under the SIL Open Font License;
   the licences are in `fonts/`.
2. Exports the engraved weather glyphs (16 conditions plus night versions), the
   29 moon phases, the light-scale hatch and the now marker as white PNGs. The
   face tints them per part of the day. The drawing code is shared with the
   design mockups in `tools/almanac_render.py`.
3. Generates `src/res/raw/watchface.xml` and the rest of the resources.
4. Packages the APK with `aapt2`, aligns it with `zipalign`, and signs it with
   `apksigner` into `dist/`.
5. Runs Google's validator,
   [`validator-push-cli`](https://maven.google.com/web/index.html#com.google.android.wearable.watchface.validator:validator-push-cli),
   on the APK. The output is in `build/validator.txt`.

**Requirements:**
- the Android SDK (build-tools 34.0.0, platform android-34) in `$ANDROID_HOME`;
- Python with `fonttools` and Pillow;
- Node with Playwright (to export PNGs from SVG);
- Java 17 or newer;
- the variable font files in `$FONT_SRC`, taken from the google/fonts repository;
- the validator jar in `$WFF_VALIDATOR`.

The generated `src/` folder is committed, so you can see exactly what goes into
the APK.

## Validation status (1.0.0)

| Check | Result |
|---|---|
| WFF v2 schema (Google validator) | Pass |
| Memory footprint (Google validator) | Pass |
| APK size, file contents, manifest, WFF version, minimum SDK, signature | Pass |
| Package-name rule for Watch Face Push | Fails, but this rule only applies to faces installed through a Watch Face Push app, not to sideloading |
| **Running on a real watch or emulator** | **Not done yet.** This build machine has no KVM, so the Wear OS emulator can't run here |

## Where the build differs from the concept, and why

| Concept | Build | Reason |
|---|---|---|
| 12 hours of forecast | **8 hours** | WFF only exposes `WEATHER.HOURS.1` to `.8` |
| Free wake and sleep times | **3 schedule presets** | Settings can choose between layouts, but a free value can't be read into the calculations |
| "Inks" setting | Dropped | It would have doubled the generated XML. The night red ink is always on |
| Always-on time as an outline | `PartText` with an `Outline` | `TimeText` fonts can't have decorations |

## Signing

The APK is signed with a key kept outside the repo (`.keys/`, which git
ignores). A build made with a different key can't update an installed copy, so
uninstall first; see the install guide.
