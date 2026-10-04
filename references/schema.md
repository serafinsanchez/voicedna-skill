# Voice Profile Schema

The samples are the primary asset; the profile is an index over them. A
profile with no sample files behind it is a downgrade, not a deliverable.

## Storage Layout

```
voices/<name>/
  samples/
    01-reflect-review.md      # one file per sample, YAML frontmatter
    02-email-deletion.md      #   register / topic / date
    ...
  newsletter.profile.yaml     # one profile per register
  email.profile.yaml
```

## Profile Template (per register)

```yaml
voice_profile:
  meta:
    author: "[name]"
    register: "[newsletter/email/social/...]"
    created: "[date]"
    samples: ["samples/01-....md", "samples/02-....md"]   # the exemplar pool
    sample_word_count: [total]

  # ── MEASURED ─ verbatim `aggregate` output of stylometry.py analyze.
  # Never hand-edited, never estimated. Regenerate when samples change.
  measured:
    sentence_length.mean: {mean: 8.40, sd: 0.38}
    punctuation.em_dash: {mean: 1.76, sd: 0.39}
    punctuation.semicolon: {mean: 0.0, sd: 0.0}
    contraction_rate: {mean: 4.54, sd: 1.22}
    # ... full aggregate block

  # ── CALIBRATION ─ from voice_match.py (omit with `calibration: none`)
  calibration:
    model: "AnnaWegmann/Style-Embedding"
    ceiling_within_author: 0.71   # author's self-similarity
    floor_cross_author: 0.38      # what a stranger scores

  # ── JUDGMENT ─ qualitative, each claim backed by a sample citation
  summary: |
    [2-3 sentences: what this voice sounds like]
  document_flow:
    opening: "[how pieces start — cite an example]"
    development: "[how arguments build]"
    closing: "[how pieces end]"
    transitions: "[characteristic pivot moves]"
  tone_position:  # words + evidence, not scores
    formality: "[e.g. casual — contracts everything, sentence fragments for emphasis]"
    humor: "[e.g. dry asides, never jokes at reader's expense]"
    stance: "[e.g. confident but self-deprecating about past mistakes]"
    energy: "[e.g. warm, restrained — emphasis via short sentences, not exclamation]"
  quirks:
    signature_phrases: ["[verbatim recurring phrases]"]
    reader_address: "[how they talk to the reader]"
    rhetorical_habits: "[questions/analogies/story-vs-data patterns]"
    favorite_words: ["..."]

  # ── BAN LIST ─ hard constraints at generation time. Include both the
  # author's verified zeros (measured 0.0 rates) and their avoided
  # words/tones. This is the primary defense against generic AI voice.
  never:
    punctuation: ["semicolons (measured 0.0)", "exclamation points (measured 0.0)"]
    words: ["utilize", "leverage", "..."]
    structures: ["..."]
    tones: ["..."]

  # optional: LIWC-adjacent proxies from scripts/psycho_profile.py —
  # open-lexicon, direction-preserving; NOT LIWC percentiles
  psycho_adjacent:
    analytic_proxy: {mean: 20.27, sd: 3.14}
    clout_proxy: {mean: 0.0, sd: 1.96}
    tone_proxy: {mean: -0.26, sd: 0.33}

  # optional: things you counted manually beyond the script's metrics —
  # kept separate from `measured` so provenance stays honest
  hand_counted:
    sentence_initial_conjunctions: "10 of 81 sentences"
    aphoristic_paragraph_endings: "~1 in 3 paragraphs"  # feeds the generation budget
```

## Minimal Profile (quick capture, <3 samples)

```yaml
voice_profile_minimal:
  register: "[context]"
  samples: ["path1", "path2"]        # still store the raw samples!
  summary: "[2-3 sentences]"
  signature_elements: ["trait 1", "trait 2", "trait 3"]
  never: ["thing 1", "thing 2"]
```

No `measured` block below 3 samples — the sd column would be noise. Say so
rather than faking one.

## Practices

1. **One profile per register.** Voice shifts with genre/audience; a global
   profile averages away the signal. Share the `never` list across registers
   if it genuinely holds in all of them.
2. **Regenerate, don't patch, `measured`** — when samples are added, rerun
   `stylometry.py analyze`. Hand-tuning measured numbers destroys their meaning.
3. **Version profiles** — voice drifts; keep dated copies. When new samples
   disagree with old `measured` values (z > 2 on stable markers), rebuild
   from recent samples instead of averaging eras.
4. **Calibration expectations** — generations scoring ~1.0 normalized are at
   the author's own self-similarity; realistic prompting-based results land
   well below that. Set the user's expectation to "recognizably in-voice."
5. **Feedback goes to the ban list first.** "I'd never say X" → `never.words`
   immediately; it's the highest-leverage, lowest-risk update.
