# Voice Analysis Methodology

Build a voice profile from writing samples using two instruments with a strict
division of labor:

- **Quantitative markers** — computed by `scripts/stylometry.py`. Never
  estimated from reading, never counted with a one-off script you write yourself.
- **Qualitative patterns** — read and judged by you: quirks, document flow,
  tone position, anti-patterns.

## Sample Requirements

**Quantity**: 3-5 samples minimum, 10+ for high fidelity
**Length**: 200+ words each
**Register**: analyze per register (newsletter ≠ email ≠ social post). An
author's style measurably shifts with genre and audience, so build one profile
per register rather than one global fingerprint. Samples from the target
register only; if the user has none, say so and profile the nearest register
with a caveat.
**Recency**: recent samples better capture current voice

## Step 1 — Store samples as files

One file per sample under `voices/<name>/samples/`, with YAML frontmatter:

```markdown
---
register: newsletter
topic: productivity tools
date: 2026-03-02
---

[verbatim sample text]
```

Verbatim means verbatim: no cleanup, no trimming "uhs" — the tics are the voice.

## Step 2 — Measure (run, don't count)

```bash
python3 <skill_dir>/scripts/stylometry.py analyze voices/<name>/samples/*.md
```

Copy the `aggregate` block (means + sd across samples) into the profile's
`measured` section unmodified. It covers: function-word rates, punctuation per
100 words, sentence-length distribution, paragraph shape, contraction rate,
type-token ratio / MATTR.

The script exists so that every number in a profile is (a) real and (b)
comparable — same tokenizer, same metric definitions — with the `compare` run
you'll do at generation time and with every other profile. A hand-rolled
counter breaks that comparability even when its counts are correct, and costs
far more to run.

| Temptation | Why it fails |
|---|---|
| "I'll just estimate — the example shows '3 per 100 words'" | Estimated precision is fabricated precision. Every number must come from the script's output. |
| "I'll write a quick counter myself" | Different tokenization → numbers that silently disagree with generation-time `compare`. Use the bundled instrument. |
| "The script missed something I want to count" | Fine — count it, but label it `hand_counted` in the profile, never mixed into `measured`. |

**Not computable, so do not report as numbers**: simple/compound/complex
sentence ratios (needs a parser; hand classification runs ±10 points),
"LIWC scores" (see below), any percentage the script doesn't emit.

## Step 3 — Calibrate the embedding scale (recommended)

```bash
python3 <skill_dir>/scripts/voice_match.py --samples voices/<name>/samples/*.md
```

Records the author's within-author ceiling and cross-author floor — the scale
every future generation is scored against (see `references/evaluation.md`).
Requires one-time `scripts/setup_env.sh`. If the environment isn't set up,
skip and note `calibration: none` in the profile; stylometric compare still works.

## Step 4 — Read for qualitative layers

These are judgment calls; make them from full readings, cite an example from
the samples for each claim, and label them as judgments — never dress them as
measurements.

**Document flow** — how pieces open, develop, and close; transition moves
between paragraphs; where the punchlines land.

**Tone position** (qualitative spectrums, adapted from Nielsen Norman):
formal↔casual, serious↔funny, respectful↔irreverent, matter-of-fact↔enthusiastic.
State position in words with an example, not as a fake score.

**Distinctive quirks** — signature phrases, how they address the reader,
rhetorical habits (questions, analogies, story-vs-data leads), vocabulary
fingerprint, favorite and avoided words.

**Anti-patterns** — what they never do. This list does double duty at
generation time as the ban list that pulls output away from generic
"AI-average" style, so be concrete: words, constructions, tones, punctuation
they don't use (the `measured` block's zeros are a good source: a 0.0
semicolon rate is an anti-pattern, verified).

## What happened to the LIWC layer

Earlier versions asked for 1-5 "LIWC" scores (Analytic/Clout/Authentic/Tone).
Those are proprietary percentile composites; a model assigning 1-5 by feel is
producing Likert guesses wearing LIWC's name, so the layer is gone. If
psychological dimensions are useful for the profile, compute them:

```bash
python3 <skill_dir>/scripts/psycho_profile.py voices/<name>/samples/*.md
```

This emits analytic/clout/tone **proxies** from open lexicons (Empath + CDI-style
word-category rates), labeled LIWC-adjacent. Paste the aggregate into the
profile's optional `psycho_adjacent` block with its disclaimer intact. Never
report these as LIWC scores, and never estimate them by feel.

## A note on "unconscious" markers

Function words and punctuation habits are high-signal because they're rarely
consciously monitored — not because they're uncontrollable. Imitation studies
show writers can deliberately shift them toward a target, which is exactly
what generation does with the measured profile. Treat them as the most
*reliable* markers, not magic ones.

## Output

Assemble into the profile format in `references/schema.md`: measured block
(verbatim script output), calibration, qualitative layers, anti-patterns, and
pointers to the sample files themselves — the samples are the primary asset;
the profile is the index.
