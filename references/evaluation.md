# Voice Evaluation

Whether a generation matches the voice is a **measurement**, not an opinion —
and above all not the opinion of the conversation that produced the text.
LLM judges' dominant bias is style bias (0.76–0.92 across model families),
and models systematically prefer their own output. A self-scored "Style: 4/5"
is the generator grading its own homework; it has rated profile-based fakes
above the author's real writing in published tests.

## The Three Checks (in order of authority)

### 1. Stylometric compare — always, free

```bash
python3 <skill_dir>/scripts/stylometry.py compare \
  --author voices/<name>/samples/*.md --target generated.md
```

**Pass**: no flagged marker where the author is consistent (low sd). A flag
on a marker the author themselves varies wildly on is a shrug; a flag on a
measured-zero marker (they never use semicolons, the draft has three) is a
hard fail. Feed flagged metrics to the bounded refine loop in
`references/generation.md`.

**Base rate**: even a genuine same-author text flags a handful of markers
(measured ~10 on a real held-out newsletter essay) — authors vary between
their own pieces. Judge by the hard-fail rules and the largest |z| values,
never by flag count alone, and don't refine toward zero flags: that target
doesn't exist in the author's own writing.

### 2. Embedding voice-match — when the venv exists

```bash
python3 <skill_dir>/scripts/voice_match.py \
  --samples voices/<name>/samples/*.md --target generated.md
```

Reads out a normalized score on the author's own calibrated scale
(1.0 = within their self-similarity, 0.0 = stranger-level):

| Normalized score | Reading |
|---|---|
| ≥ 0.7 | Strongly in-voice — rare for pure prompting; verify it's not topic overlap |
| 0.4 – 0.7 | Recognizably in-voice — the realistic target band |
| < 0.4 | Closer to generic than to the author — fix conditioning, not wording |

Score < 0.4 means change the inputs (exemplar selection, ban list, sample
pool), not another polish pass.

**Two models, one rule**: `--both` runs Wegmann (content-independent style)
and LUAR (authorship representation). When they disagree, **trust the lower
score**. Measured behavior: LUAR rated an on-topic pastiche 0.933 while
Wegmann rated it 0.275 and a blind judge caught it — LUAR encodes topic
alongside authorship, so topic overlap between samples and generation
inflates it. Agreement between both models is meaningful evidence; a high
LUAR score alone is not.

### 3. Blind discrimination — for high-stakes output

Spawn a **fresh subagent** (never this conversation) with two unlabeled
texts in randomized order: the generation and a **held-out** real sample
(one excluded from the exemplars used in the prompt). Ask only:

> "One of these was written by a person, the other generated in their style.
> Which is generated, and what gave it away?"

- Judge picks wrong or reports guessing → strong pass.
- Judge picks right → its "what gave it away" list is your concrete fix list.
- No held-out sample available? Say so; skip the check rather than reusing
  an exemplar the generator already saw.

## Content and Fluency

Style is not the only axis. Check content preservation (facts, intent, no
inventions) against the task brief, and fluency by one read-aloud pass.
These two the generating conversation *may* self-check — the documented
biases are about style judgment.

## Disagreement Rule

When your impression ("this nails the voice") disagrees with the
measurements, **the measurements win**. Style-biased self-assessment is the
single most documented failure mode of this entire task. Report the scores,
not your confidence.

## Reporting Results

Report to the user:
- flagged stylometric deltas (or "none")
- normalized voice-match score with its band, or `calibration: none`
- blind-judge outcome if run
- the honest frame: "recognizably in-voice" is the achievable standard;
  indistinguishability is not on the table for prompting-based generation.

Never report a 1-5 style score you assigned yourself. If the user asks for
"a score," give the normalized voice-match number — it's the only one with
a defined scale behind it.
