# Fine-Tuning Escalation Path (LoRA)

Prompting has a measured ceiling. Per-author LoRA is the only approach shown
to break it (authorship-classifier accuracy ~88% vs ~69% for 5-shot exemplar
prompting), but it costs training, storage, and a serving path — so it's an
escalation, not a default.

## When to Escalate

Both conditions, not either:

1. **Corpus**: ≥80k tokens of the author's text in the target register(s).
   Check with `export_training_data.py` — it reports the estimate.
2. **Plateau**: normalized `voice_match.py` scores have stopped improving
   across exemplar/ban-list iterations and sit below the user's needs.

Below the threshold, more samples + better retrieval beats fine-tuning:
RAG-style exemplar conditioning wins for cold-start/small-data users, and
combining retrieval with a fine-tune only marginally beats retrieval alone
until data volume is real.

## What This Skill Can and Can't Do

Claude cannot be LoRA-tuned from here. The escalation means drafting on a
tuned **open model**, then optionally editing with Claude — knowing every
LLM editing pass pulls style back toward generic (keep edits mechanical:
facts, typos, never "smoothing").

## Procedure

1. **Export**: `python3 scripts/export_training_data.py voices/<name>/samples/*.md`
   → chat-format JSONL.
2. **Train** (local, Apple Silicon):
   ```bash
   pip install mlx-lm
   mlx_lm.lora --model <open-model-id> --train --data <jsonl-dir> --iters 600
   ```
   Or any hosted fine-tuning service that accepts chat-format JSONL.
3. **Evaluate exactly like prompted output**: `stylometry.py compare` +
   `voice_match.py` against the same calibration. A fine-tune that doesn't
   beat the prompting pipeline's normalized score isn't worth serving.
4. **Keep the profile**: the ban list and measured block still gate outputs;
   a LoRA reduces drift, it doesn't eliminate it.

## Honesty Note

Fine-tuning narrows the gap; published results still show style-classifier
accuracy, not indistinguishability. The deliverable remains "recognizably
in-voice" — now with less per-generation prompting effort and better tail
behavior on long outputs.
