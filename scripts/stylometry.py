#!/usr/bin/env python3
"""Deterministic stylometric analysis for voice profiles. Stdlib only.

Usage:
  stylometry.py analyze SAMPLE [SAMPLE ...]
      Per-file metrics + aggregate means across files, as JSON.

  stylometry.py compare --author SAMPLE [SAMPLE ...] --target GENERATED [--threshold Z]
      Z-scores of the generated text against the author's per-sample
      distribution; markers past the threshold land in "flagged".

All rates are per 100 words so texts of different lengths compare directly.
Length-dependent counts (word_count, sentence_count, paragraph count) are
reported by `analyze` but excluded from `compare`.

Sentence splitting is intentionally simple (runs of .!? end a sentence);
abbreviations like "Dr." split incorrectly. Fine for comparing texts measured
the same way — do not treat absolute sentence stats as exact.
"""
import argparse
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FUNCTION_WORDS_PATH = os.path.join(HERE, "..", "assets", "function_words.txt")

WORD_RE = re.compile(r"[a-zA-Z]+(?:'[a-zA-Z]+)*")
SENTENCE_SPLIT_RE = re.compile(r"[.!?]+(?=\s|$)")
EM_DASH_RE = re.compile(r"—|–|(?<!-)--(?!-)")
ELLIPSIS_RE = re.compile(r"…|\.\.\.")

# compare() only looks at length-normalized metrics
COMPARE_EXCLUDE = {"word_count", "sentence_count", "paragraphs.count",
                   "sentence_length.min", "sentence_length.max"}


def load_function_words(path=FUNCTION_WORDS_PATH):
    words = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip().lower()
            if line and not line.startswith("#"):
                words.add(line)
    return words


def strip_frontmatter(text):
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


def tokenize(text):
    return WORD_RE.findall(text.replace("’", "'").lower())


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _sd(xs, ddof=0):
    if len(xs) <= ddof:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - ddof))


def _mattr(words, window=50):
    """Moving-average type-token ratio; falls back to plain TTR on short texts."""
    if len(words) < window:
        return len(set(words)) / len(words) if words else 0.0
    ratios = [len(set(words[i:i + window])) / window
              for i in range(len(words) - window + 1)]
    return _mean(ratios)


def analyze_text(text, function_words=None):
    if function_words is None:
        function_words = load_function_words()
    words = tokenize(text)
    n = len(words)
    per100 = (lambda c: c / n * 100 if n else 0.0)

    sentences = [tokenize(s) for s in SENTENCE_SPLIT_RE.split(text)]
    sentences = [s for s in sentences if s]
    slens = [len(s) for s in sentences]

    paragraphs = [p for p in re.split(r"\n\s*\n", text) if tokenize(p)]
    para_sentences = [[tokenize(s) for s in SENTENCE_SPLIT_RE.split(p) if tokenize(s)]
                      for p in paragraphs]
    para_sent_counts = [max(1, len(ss)) for ss in para_sentences]
    single = sum(1 for c in para_sent_counts if c == 1)

    # Punch ending: a paragraph whose final sentence is markedly short —
    # ≤ max(6, 0.6 × doc mean sentence length) words. High rates read as
    # engineered punchline cadence, a top blind-judge tell for generated text.
    mean_slen = _mean(slens)
    punch_threshold = max(6.0, 0.6 * mean_slen)
    punches = sum(1 for ss in para_sentences if ss and len(ss[-1]) <= punch_threshold)

    fw_counts = {}
    for w in words:
        if w in function_words:
            fw_counts[w] = fw_counts.get(w, 0) + 1

    contractions = sum(1 for w in words if "'" in w)

    return {
        "word_count": n,
        "sentence_count": len(sentences),
        "sentence_length": {
            "mean": _mean(slens),
            "sd": _sd(slens),
            "min": min(slens) if slens else 0,
            "max": max(slens) if slens else 0,
        },
        "paragraphs": {
            "count": len(paragraphs),
            "mean_sentences": _mean(para_sent_counts),
            "single_sentence_pct": (single / len(paragraphs) * 100) if paragraphs else 0.0,
            "punch_ending_pct": (punches / len(paragraphs) * 100) if paragraphs else 0.0,
        },
        "punctuation": {
            "em_dash": per100(len(EM_DASH_RE.findall(text))),
            "dash_spaced": per100(len(re.findall(r"(?<=\S) - (?=\S)", text))),
            "semicolon": per100(text.count(";")),
            "colon": per100(len(re.findall(r":(?!//)", text))),
            "comma": per100(text.count(",")),
            "exclamation": per100(text.count("!")),
            "question": per100(text.count("?")),
            "ellipsis": per100(len(ELLIPSIS_RE.findall(text))),
            "parenthetical": per100(text.count("(")),
        },
        "function_words": {w: per100(c) for w, c in sorted(fw_counts.items())},
        "function_word_total": per100(sum(fw_counts.values())),
        "contraction_rate": per100(contractions),
        "ttr": len(set(words)) / n if n else 0.0,
        "mattr_50": _mattr(words),
    }


def analyze_file(path, function_words=None):
    with open(path, encoding="utf-8") as f:
        return analyze_text(strip_frontmatter(f.read()), function_words)


def _flatten(metrics, prefix=""):
    flat = {}
    for k, v in metrics.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            flat.update(_flatten(v, key + "."))
        elif isinstance(v, (int, float)):
            flat[key] = float(v)
    return flat


def is_flaggable(key, author_mean, target):
    """Rare function words (<0.5/100w on both sides) are sampling noise;
    they stay in the metrics dict but never in the flagged list."""
    if key.startswith("function_words."):
        return max(author_mean, target) >= 0.5
    return True


def robust_z(mean, sd, target):
    """Z-score with an sd floor of 10% of the author mean.

    Small sample pools (n=3) produce near-zero sds on consistent markers;
    without a floor, an on-pattern target diluted by a slightly longer text
    explodes into a huge z and gets falsely flagged.
    """
    sd_eff = max(sd, 0.1 * abs(mean))
    return (target - mean) / sd_eff if sd_eff > 1e-9 else None


def compare(author_paths, target_path, threshold=1.5):
    fw = load_function_words()
    author_flat = [_flatten(analyze_file(p, fw)) for p in author_paths]
    target_flat = _flatten(analyze_file(target_path, fw))

    keys = set(target_flat)
    for a in author_flat:
        keys.update(a)
    keys -= COMPARE_EXCLUDE

    metrics, flagged = {}, []
    for key in sorted(keys):
        avals = [a.get(key, 0.0) for a in author_flat]
        mean, sd = _mean(avals), _sd(avals, ddof=1)
        target = target_flat.get(key, 0.0)
        z = robust_z(mean, sd, target)
        entry = {"author_mean": round(mean, 3), "author_sd": round(sd, 3),
                 "target": round(target, 3), "z": round(z, 2) if z is not None else None}
        metrics[key] = entry
        # sd==0 means the author is perfectly consistent on this marker; any
        # meaningful deviation (>0.5 units) is a flag even without a z-score
        deviates = (abs(z) >= threshold) if z is not None else (abs(target - mean) > 0.5)
        if deviates and is_flaggable(key, mean, target):
            flagged.append({"metric": key, **entry,
                            "direction": "over" if target > mean else "under"})

    flagged.sort(key=lambda f: abs(f["z"]) if f["z"] is not None else float("inf"),
                 reverse=True)
    return {"author_files": list(author_paths), "target_file": target_path,
            "threshold": threshold, "metrics": metrics, "flagged": flagged}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_an = sub.add_parser("analyze", help="measure one or more samples")
    ap_an.add_argument("files", nargs="+")

    ap_cmp = sub.add_parser("compare", help="z-score a generated text against author samples")
    ap_cmp.add_argument("--author", nargs="+", required=True)
    ap_cmp.add_argument("--target", required=True)
    ap_cmp.add_argument("--threshold", type=float, default=1.5)

    args = ap.parse_args()
    if args.cmd == "analyze":
        fw = load_function_words()
        results = [{"path": p, "metrics": analyze_file(p, fw)} for p in args.files]
        flats = [_flatten(r["metrics"]) for r in results]
        keys = sorted(set().union(*flats)) if flats else []
        aggregate = {k: {"mean": round(_mean([f.get(k, 0.0) for f in flats]), 3),
                         "sd": round(_sd([f.get(k, 0.0) for f in flats], ddof=1), 3)}
                     for k in keys}
        print(json.dumps({"files": results, "aggregate": aggregate}, indent=2))
    else:
        print(json.dumps(compare(args.author, args.target, args.threshold), indent=2))


if __name__ == "__main__":
    main()
