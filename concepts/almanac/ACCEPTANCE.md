# Almanac: acceptance criteria

I wrote these **before** drawing anything, and I don't change them after seeing
results. Anything a script can measure is measured by `tools/almanac_audit.py`
on the rendered previews. I've only used judgement where no measurement is
possible, and those items are marked **R** (reviewer).

Device constants: OnePlus Watch 3, 466 × 466 px round AMOLED, 1.5″, which is
about 311 ppi and roughly density 2.0. So **1 dp ≈ 2 px** and **12 sp ≈ 24 px**.

## Gates

If any gate fails, the concept is rejected, whatever its score.

| ID | Criterion | Threshold | Method |
|---|---|---|---|
| G1 | **Data honesty.** Every value shown comes from a documented WFF data source, or from a calculation on documented sources. | 0 values without a source | Data-source table in the concept doc, checked against developer.android.com/reference/wear-os/wff/common/attributes/source-type |
| G2 | **Time legibility.** The time digits are tall enough and stand out from the background in every interactive state. | Digits at least 80 px tall; contrast of at least 7:1 | A — measured on the render |
| G3 | **Always-on power.** Lit pixels in each always-on state. | 15% or less (Google's rule) | A — share of pixels with any colour channel above 10, inside the round display |
| G4 | **Weather coverage.** Every one of the 16 `WEATHER.CONDITION` values has its own drawn glyph. | 16 / 16 | A — the glyph files exist and are all different |
| G5 | **State coverage.** All 4 parts of the day are designed in active mode and in always-on mode, plus no-data and stale-data. | 10 / 10 | A — the files exist |
| G6 | **Inside the bezel.** No text is clipped by the round edge. | Every text box within 216 px of the centre (93% radius) | A |

## Scored criteria

Each item scores between 0 and 1. The total score is
**10 × Σ(weight × score) / Σ weight.**

| ID | Weight | Criterion | Full marks when | Method |
|---|---|---|---|---|
| S1 | 10 | Smallest text size, in every state | All text is at least 24 px (12 sp) | A |
| S2 | 10 | Text contrast against the actual pixels behind it | At least 4.5:1 for every text element, measured against the 5th-percentile background pixel | A |
| S3 | 6 | The time clearly dominates | Time font size is at least 2.5 × the largest other text | A |
| S4 | 6 | Not overloaded (Miller, Hick, Nielsen H8) | No more than 6 pieces of information per state | A — counted from `data-role` tags |
| S5 | 6 | Each part of the day answers its glance questions with no interaction | Every question in the concept doc is answered by visible content | R |
| S6 | 5 | No information carried by colour alone, and the parts of the day are easy to tell apart | Every coloured element also has a text or shape cue, and accent colours differ by ΔE76 ≥ 20 pairwise | A for ΔE, R for the cue |
| S7 | 5 | Night mode protects night vision | Night text and accents are red-dominant, and average brightness is 2% or less | A |
| S8 | 5 | Consistency (H4): the time doesn't move between parts of the day | Time position and size are the same in all 4 within 2 px | A |
| S9 | 5 | System status is visible (H1) | No-data, error and stale-data states have their own wording that tells the user what to do | R + render |
| S10 | 5 | Respects system settings | Temperature unit, 12/24 h, and localised condition and day names all come from the system | D — mapping in the doc |
| S11 | 5 | Customisation | At least 3 meaningful options in Customize | D |
| S12 | 6 | Buildable in WFF | Each mechanism is mapped to a named WFF element. A mapping not yet proven on the watch scores 0.5 | D |
| S13 | 8 | **Verified on a real OnePlus Watch 3** | It runs on the watch, and every state has been seen there | Device test. **Scores 0 until done** |
| S14 | 8 | **Comprehension test** | At least 5 people answer each part of the day's glance questions in 3 s or less, with at least 90% correct | User test. **Scores 0 until done** |
| S15 | 5 | Originality | Not a recreation of an existing face. Novelty can't be proven exhaustively, so the maximum is 0.5 | R |
| S16 | 5 | Visual consistency | At most 2 typefaces, and at most 3 colours per part of the day | A |

## What a score above 9.999985 would require

The weights add up to 100. A score of 9.999985 or more leaves room for a
shortfall of only 0.00015%, so **every criterion would need full marks**.
S13 and S14 can't score anything until the face runs on a real watch and real
people have tried it. S15 is capped at 0.5. That means **the highest score a
paper concept can reach is 10 × (100 − 8 − 8 − 2.5 − partial S12) / 100 ≈ 8.0**.
I'm stating that ceiling up front rather than inflating the score.
