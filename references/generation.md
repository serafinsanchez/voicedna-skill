# Voice Generation Guidelines

The exemplars carry the voice; the profile steers and constrains. Showing the
model real samples beats describing the style — in head-to-head tests,
exemplar conditioning scored ~69% on authorship classifiers vs ~26% for
style descriptions alone. Build every generation prompt in this order:

## The Conditioning Stack (assemble in this order)

**1. Exemplars — verbatim, first, prominent.**
Select 5 sample files from the profile's pool:
- same register as the target output (newsletter profile → newsletter samples)
- prefer topic-adjacent samples when available
- fewer than 5 in-register? Backfill from the author's other registers and
  say so in the output caveats. Never pad with paraphrases or summaries —
  verbatim text only.

**2. Ban list — the profile's `never` block, stated as hard constraints.**
This is the anti-"AI-average" mechanism: the measured zeros (no semicolons,
no exclamation points), the avoided words, the forbidden tones. Constraints,
not suggestions.

**3. Compressed profile — tiebreaker guidance.**
2-3 sentences of summary plus the most distinctive `measured` targets
(sentence-length mean/sd, em-dash rate, contraction rate) and signature
phrases with dosing limits. Not the full YAML — the exemplars already carry
what the profile would describe.

**4. The task brief.** Content requirements last, so voice context frames them.

### Template

```
Here are 5 pieces [AUTHOR] wrote ([REGISTER]):

<sample>…verbatim…</sample>
<sample>…verbatim…</sample>
…

Write like these samples. Hard constraints — [AUTHOR] never uses:
- [ban list, one per line]

Style targets: sentences average [X] words with high variance ([style notes]).
Signature moves, max [N] uses each: [phrases].

Aphorism budget: the samples land a quotable ending in about [RATE] of
paragraphs. Hard limit: at most [K] of your [M] paragraphs may end on a
quotable/epigram line. The others must end plainly — on a detail, a number,
a hedge, or a sentence that simply completes the thought. After drafting,
classify every paragraph's ending (punchline or plain); if over budget,
rewrite those endings before finalizing.

Task: [content brief]
```

The aphorism-budget slot is REQUIRED, with [K] derived from the profile's
`hand_counted.aphoristic_paragraph_endings` rate (count it from the samples
during analysis if missing). The classify-then-rewrite step is part of the
slot — it is what makes the limit bind.

## Signature Phrase Dosing

Include naturally, never force: 1-3 placements per piece unless the samples
show more. If a phrase would need shoehorning, drop it — an absent signature
reads better than a forced one.

This applies to *every* recognizable device, not just phrases: tag questions,
callbacks, concession moves, ring composition. Dose each at the frequency the
samples actually show (count it), and vary the position — the same device in
the same structural slot twice is a tell.

## Why the Aphorism Budget Exists (micro-tested)

Punchline density is the most reliable tell blind judges catch in
profile-driven generation: every paragraph engineered to land a quotable
line. Advisory wording ("let a paragraph breathe") measurably fails — in a
5-rep head-to-head test, advice-worded prompts produced ~4 engineered
endings per 6 paragraphs in every rep, while the numbered budget with the
classify-then-rewrite step held every rep to 2-3. Use the budget slot; do
not soften it back into advice.

Known limitation (measured in a full-length verification run): the budget
binds paragraph *endings*, and the zingers migrate — a piece that passed the
ending budget (3/15) was still flagged by a blind judge for aphorisms opening
and mid-paragraph. If that tell dominates, apply the same numbered budget to
quotable lines *anywhere*, not just endings. Two further judge tells that no
ending budget fixes: too-symmetric structure (First/Second/Third/Fourth,
one even paragraph each — real authors are lumpier) and zero grammatical
looseness (every sentence groomed). Vary paragraph lengths deliberately and
let one construction stay slightly tangled.

One adjacent tell survives the budget: composition that is too tidy — an
opening image returning as a perfectly symmetric closing callback reads as
engineered. If the samples ring-compose, fine; if they don't, don't
gift-wrap the ending.

## The Refine Loop (bounded)

After drafting:

```bash
python3 <skill_dir>/scripts/stylometry.py compare \
  --author voices/<name>/samples/*.md --target draft.md
```

- Revise **only the flagged metrics**, touching the passages responsible —
  don't rewrite globally for a local drift.
- **Maximum 2 refine passes.** Repeated LLM revision measurably collapses
  stylistic variance toward generic AI voice; a third pass usually erases
  more voice than it fixes. If still failing after 2, the fix is upstream:
  different exemplars, tighter ban list, or more samples — not more polishing.
- Then evaluate per `references/evaluation.md` (never self-score).

## Edge Cases

**Topic mismatch** (profile built on other subject matter): exemplars still
lead — structure and tone transfer; adapt vocabulary to the new domain at the
same jargon level; keep signature phrases only where they fit.

**Formality mismatch** (formal deliverable, casual voice): keep sentence
rhythm and punctuation fingerprint; reduce, don't eliminate, casual markers.

**Emotional content, reserved voice**: let content carry the emotion; keep
their emphasis mechanics (short sentences, not exclamation points).

## Calibration Feedback Loop

| Feedback | Update |
|---|---|
| "I'd never say X" | Add to `never.words` immediately |
| "Too formal" / tone off | Adjust tone_position notes; swap in exemplars that show the register they mean |
| "Missing my usual [phrase]" | Add to signature_phrases with a dosing note |
| "Doesn't feel like me" | Ask for the offending passage; run `compare` on it; diagnose from flagged metrics rather than guessing |
| "Close but off" | Check flagged z-scores first — the drift is usually measurable |

Every correction is also a datum: if the user keeps correcting toward
something the samples don't show, the sample pool is stale or from the wrong
register — say so and ask for fresher samples.

## Honest Expectations

No prompting-based method reliably makes output *indistinguishable* from the
author — published evaluations put all inference-time methods below the
similarity that random humans have to each other. The deliverable is
"recognizably in-voice, no AI tells," verified by measurement. Don't promise
more, and don't self-certify success — that's `references/evaluation.md`'s job.
