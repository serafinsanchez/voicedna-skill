# VoiceDNA

A Claude Code skill for capturing, measuring, and replicating an individual's
writing voice — built around measurement instead of vibes.

- **Exemplars carry the voice; profiles steer.** Verbatim samples condition
  generation; the profile indexes them, holds measured facts, and bans what
  the author never does.
- **Numbers come from scripts.** `scripts/stylometry.py` (stdlib only)
  computes function-word rates, punctuation, sentence/paragraph shape,
  contractions, and MATTR, and z-scores a draft against the author's samples.
- **The generator never grades itself.** `scripts/voice_match.py` scores
  drafts on a per-author calibrated embedding scale (Wegmann Style-Embedding
  and LUAR), and high-stakes output goes to a blind judge.

See [`SKILL.md`](SKILL.md) for the workflow and `references/` for details.

## Install

```bash
git clone https://github.com/serafinsanchez/voicedna-skill ~/.claude/skills/voicedna
```

Stylometry works out of the box. For embedding-based voice-match scoring,
run once:

```bash
bash ~/.claude/skills/voicedna/scripts/setup_env.sh
```

(`psycho_profile.py` additionally uses `empath` if installed in the venv.)

## Tests

```bash
python3 scripts/test_stylometry.py
```

## Honest ceiling

Prompting-based generation gets to "recognizably in-voice," not
indistinguishable. `references/lora.md` covers the fine-tuning escalation
path for authors with 80k+ tokens of samples.
