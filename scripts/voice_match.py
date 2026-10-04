#!/usr/bin/env python3
"""Objective voice-match scoring via authorship/style embeddings, calibrated
per author. Usable as a CLI or imported as a library (see evaluate()).

Raw cosine similarity is meaningless on its own, so every score is reported
relative to two per-author baselines:

  ceiling  mean pairwise cosine among the author's own samples
  floor    mean cosine between the author's samples and the bundled
           floor corpus of other writers

  normalized = (target_cos - floor) / (ceiling - floor)

~1.0 → indistinguishable from the author's own variation; ~0.0 → no closer
than a random other writer. Inference-time methods typically land well below
1.0 (see references/evaluation.md).

Models:
  wegmann  AnnaWegmann/Style-Embedding  (default; content-independent style)
  luar     rrivera1849/LUAR-MUD         (authorship representation, 512-dim)
  any other sentence-transformers HF id is accepted verbatim

Usage:
  voice_match.py --samples S1 S2 S3 [--target GEN.md] [--model wegmann|luar|ID] [--both]

--both runs wegmann AND luar and reports both scores plus their agreement.
Requires the venv created by setup_env.sh; exits 2 with a JSON error if missing.
"""
import argparse
import itertools
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
VENV_PY = os.path.join(SKILL_DIR, ".venv", "bin", "python")
FLOOR_DIR = os.path.join(SKILL_DIR, "assets", "floor_corpus")

MODEL_ALIASES = {
    "wegmann": "AnnaWegmann/Style-Embedding",
    "luar": "rrivera1849/LUAR-MUD",
}
DEFAULT_MODEL = "wegmann"

sys.path.insert(0, HERE)
from stylometry import strip_frontmatter  # noqa: E402


# ── embedding backends ──────────────────────────────────────────────────────

class _StBackend:
    """Any sentence-transformers model (Wegmann default)."""

    def __init__(self, model_id):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_id)

    def encode(self, texts):
        return [list(map(float, v)) for v in self.model.encode(texts)]


class _LuarBackend:
    """LUAR authorship embeddings (episode-shaped transformers API)."""

    def __init__(self, model_id):
        import torch
        from transformers import AutoModel, AutoTokenizer
        self._torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        self.model = AutoModel.from_pretrained(model_id, trust_remote_code=True)
        self.model.eval()

    def encode(self, texts):
        out = []
        for text in texts:
            enc = self.tok(text, max_length=512, truncation=True,
                           padding="max_length", return_tensors="pt")
            # LUAR expects (batch, episode, seq); one doc = episode of 1
            kwargs = {"input_ids": enc["input_ids"].unsqueeze(1),
                      "attention_mask": enc["attention_mask"].unsqueeze(1)}
            with self._torch.no_grad():
                emb = self.model(**kwargs)
            out.append([float(x) for x in emb[0]])
        return out


def load_backend(name):
    model_id = MODEL_ALIASES.get(name, name)
    if "LUAR" in model_id.upper():
        return _LuarBackend(model_id), model_id
    return _StBackend(model_id), model_id


# ── scoring (pure functions; the future web-app API surface) ────────────────

def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def calibrate(sample_embs, floor_embs):
    """Within-author ceiling + cross-author floor from precomputed embeddings."""
    ceiling = _mean([_cos(a, b) for a, b in itertools.combinations(sample_embs, 2)])
    floor = _mean([_cos(s, f) for s in sample_embs for f in floor_embs])
    return {"ceiling_within_author": round(ceiling, 4),
            "floor_cross_author": round(floor, 4),
            "spread": round(ceiling - floor, 4)}


def score_target(target_emb, sample_embs, calibration):
    """Normalized voice-match score for one target against a calibration."""
    target_cos = _mean([_cos(target_emb, s) for s in sample_embs])
    spread = calibration["ceiling_within_author"] - calibration["floor_cross_author"]
    normalized = ((target_cos - calibration["floor_cross_author"]) / spread
                  if abs(spread) > 1e-9 else None)
    return {"cosine_vs_samples": round(target_cos, 4),
            "normalized_score": round(normalized, 3) if normalized is not None else None}


def evaluate(sample_texts, floor_texts, target_text=None, model_name=DEFAULT_MODEL):
    """Full pipeline on raw texts. Library entry point for the web app."""
    backend, model_id = load_backend(model_name)
    sample_embs = backend.encode(sample_texts)
    floor_embs = backend.encode(floor_texts)
    out = {"model": model_id, "calibration": calibrate(sample_embs, floor_embs)}
    if out["calibration"]["spread"] < 0.05:
        out["warning"] = ("ceiling and floor are nearly identical — samples may be "
                          "too short, too few, or too heterogeneous for a reliable scale")
    if target_text is not None:
        target_emb = backend.encode([target_text])[0]
        out["target"] = score_target(target_emb, sample_embs, out["calibration"])
        out["target"]["reading"] = ("1.0 ≈ within the author's own variation; "
                                    "0.0 ≈ no closer than a random other writer")
    return out


# ── CLI ──────────────────────────────────────────────────────────────────────

def _reexec_in_venv():
    """If not running inside the skill venv but it exists, re-exec there.

    Compare via sys.prefix, not realpath: on macOS the venv's python is a
    symlink chain to the base interpreter, so realpath() collapses both
    sides to the same file and the check would never fire.
    """
    venv_dir = os.path.dirname(os.path.dirname(VENV_PY))
    if os.path.exists(VENV_PY) and not sys.prefix.startswith(venv_dir):
        os.execv(VENV_PY, [VENV_PY, os.path.abspath(__file__)] + sys.argv[1:])


def _read(path):
    with open(path, encoding="utf-8") as f:
        return strip_frontmatter(f.read())


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--samples", nargs="+", required=True,
                    help="author writing samples (3+ recommended)")
    ap.add_argument("--target", help="generated text to score (omit for calibration only)")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help="wegmann (default), luar, or a sentence-transformers HF id")
    ap.add_argument("--both", action="store_true",
                    help="run wegmann AND luar; report both plus agreement")
    ap.add_argument("--floor-dir", default=FLOOR_DIR,
                    help="directory of other-author texts for the floor baseline")
    args = ap.parse_args()

    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        print(json.dumps({"error": "embedding dependencies not installed",
                          "fix": f"run: bash {os.path.join(HERE, 'setup_env.sh')}",
                          "fallback": "use stylometry.py compare (stdlib-only) meanwhile"}))
        sys.exit(2)

    if len(args.samples) < 2:
        print(json.dumps({"error": "need at least 2 samples to compute a ceiling"}))
        sys.exit(1)

    floor_paths = sorted(
        os.path.join(args.floor_dir, f) for f in os.listdir(args.floor_dir)
        if f.endswith((".md", ".txt")))
    if not floor_paths:
        print(json.dumps({"error": f"no floor corpus texts in {args.floor_dir}"}))
        sys.exit(1)

    sample_texts = [_read(p) for p in args.samples]
    floor_texts = [_read(p) for p in floor_paths]
    target_text = _read(args.target) if args.target else None

    models = ["wegmann", "luar"] if args.both else [args.model]
    results = {m: evaluate(sample_texts, floor_texts, target_text, m) for m in models}

    out = {"samples": args.samples}
    if args.target:
        out["target_file"] = args.target
    if len(models) == 1:
        out.update(results[models[0]])
    else:
        out["models"] = results
        if args.target:
            scores = [results[m]["target"]["normalized_score"] for m in models]
            if None not in scores:
                out["agreement"] = {
                    "normalized_scores": dict(zip(models, scores)),
                    "delta": round(abs(scores[0] - scores[1]), 3),
                    "reading": ("models agree" if abs(scores[0] - scores[1]) < 0.2
                                else "models disagree — trust the lower score and "
                                     "check for topic overlap inflating the higher one"),
                }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    _reexec_in_venv()
    main()
