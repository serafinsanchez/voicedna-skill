---
name: voicedna
description: Use when capturing a person's writing voice from samples, generating content (newsletters, emails, posts) that must sound like a specific person, refining a voice profile from feedback, or judging whether generated text matches a target author's voice.
---

# VoiceDNA

Capture, measure, and replicate individual writing voices. Two principles run
through everything:

1. **Exemplars carry the voice; profiles steer.** Verbatim samples in context
   beat any description of the style. The profile's job is indexing samples,
   holding measured facts, and banning what the author never does.
2. **Numbers come from scripts, judgments come from reading, and the
   generator never grades itself.** Every quantitative claim is computed by
   `scripts/stylometry.py`; voice match is scored by `scripts/voice_match.py`
   on a per-author calibrated scale.

## Workflow

### 1. Analysis (samples → profile)

Follow `references/analysis.md`: store samples as files with register
frontmatter, run `stylometry.py analyze`, calibrate with `voice_match.py`,
read for the qualitative layers. Output per `references/schema.md`.

Minimum input: 3-5 samples, 200+ words each, from the target register.
One profile per register — newsletter voice ≠ email voice.

### 2. Generation (profile → content)

Follow `references/generation.md`: 5 verbatim exemplars first, then the ban
list as hard constraints, then compressed profile, then the task. Refine
against `stylometry.py compare` — maximum 2 passes.

### 3. Evaluation (never self-scored)

Follow `references/evaluation.md`: stylometric compare (always), normalized
embedding score (when the venv exists), blind discrimination by a fresh
subagent (high stakes). Measurements beat impressions.

### 4. Calibration (feedback → profile)

"I'd never say X" → ban list immediately. Repeated corrections the samples
don't support → stale or wrong-register sample pool; ask for fresh samples.

## Scripts

| Command | Purpose | Needs |
|---|---|---|
| `scripts/stylometry.py analyze SAMPLES...` | measured profile block | stdlib only |
| `scripts/stylometry.py compare --author S... --target G` | z-score drift check | stdlib only |
| `scripts/voice_match.py --samples S... [--target G]` | calibrated voice-match score | `scripts/setup_env.sh` once |
| `scripts/export_training_data.py` | LoRA escalation path | see `references/lora.md` |

## Honest Ceiling

Prompting-based generation does not reach indistinguishability — published
evaluations place all inference-time methods below the similarity random
humans share. Promise and deliver "recognizably in-voice," verified by
measurement. When a user has 80k+ words of samples and scores plateau,
`references/lora.md` is the escalation path.

## Quick Reference

| Task | File |
|---|---|
| Extract voice from samples | `references/analysis.md` |
| Profile structure & storage | `references/schema.md` |
| Generate in voice | `references/generation.md` |
| Score / verify a generation | `references/evaluation.md` |
| Fine-tuning escalation | `references/lora.md` |
