#!/usr/bin/env python3
"""Export voice samples as fine-tuning data (JSONL). Stdlib only.

Usage:
  export_training_data.py SAMPLE [SAMPLE ...] [--out FILE] [--author NAME]

Emits one chat-format record per sample:
  {"messages": [{"role": "user", "content": "<register/topic writing brief>"},
                {"role": "assistant", "content": "<verbatim sample>"}]}

Also reports estimated token volume against the ~80k-token threshold where
per-author LoRA becomes worthwhile (see references/lora.md).
"""
import argparse
import json
import re
import sys

from stylometry import strip_frontmatter, tokenize  # same dir


def parse_frontmatter(raw):
    meta = {}
    if raw.startswith("---\n"):
        end = raw.find("\n---", 4)
        if end != -1:
            for line in raw[4:end].splitlines():
                m = re.match(r"^(\w[\w-]*):\s*(.+)$", line.strip())
                if m:
                    meta[m.group(1)] = m.group(2).strip()
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("samples", nargs="+")
    ap.add_argument("--out", default="voice_training.jsonl")
    ap.add_argument("--author", default="the author")
    args = ap.parse_args()

    records, word_total = [], 0
    for path in args.samples:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        meta = parse_frontmatter(raw)
        body = strip_frontmatter(raw).strip()
        if not body:
            continue
        register = meta.get("register", "piece")
        topic = meta.get("topic", "a subject of your choosing")
        prompt = f"Write a {register} about {topic}, in your own voice."
        records.append({"messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": body},
        ]})
        word_total += len(tokenize(body))

    with open(args.out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    est_tokens = int(word_total * 1.33)
    print(json.dumps({
        "records": len(records),
        "word_total": word_total,
        "estimated_tokens": est_tokens,
        "lora_threshold_met": est_tokens >= 80_000,
        "out": args.out,
        "note": ("below ~80k tokens, retrieval + exemplar prompting typically "
                 "matches or beats a fine-tune — see references/lora.md"
                 if est_tokens < 80_000 else
                 "enough data for per-author LoRA to give a real fidelity jump"),
    }, indent=2))


if __name__ == "__main__":
    main()
