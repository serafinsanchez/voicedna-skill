#!/usr/bin/env python3
"""LIWC-adjacent psychological dimension proxies. NOT LIWC.

LIWC-22's summary variables (Analytic/Clout/Authentic/Tone) are proprietary
percentile composites and cannot be reproduced here. This script computes
open, direction-preserving proxies instead:

  analytic_proxy   CDI-style (Pennebaker et al. 2014 formula shape):
                   30 + articles + prepositions - pronouns - auxiliaries
                   - conjunctions - adverbs - negations   (per-100w rates)
  clout_proxy      we + you - i rates (Kacewicz et al. 2014 direction)
  tone_proxy       Empath positive_emotion - negative_emotion (per 100 words)
  plus raw Empath category rates for emotion/social/cognition categories.

Report these as "LIWC-adjacent proxies", never as LIWC scores. They are
comparable between texts measured by this script, not against published
LIWC percentiles.

Usage:
  psycho_profile.py SAMPLE [SAMPLE ...]        # per-file + aggregate JSON

Runs inside the skill venv (needs empath); re-execs automatically.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
VENV_PY = os.path.join(SKILL_DIR, ".venv", "bin", "python")

sys.path.insert(0, HERE)
from stylometry import strip_frontmatter, tokenize, _mean, _sd  # noqa: E402

ARTICLES = {"a", "an", "the"}
PREPOSITIONS = {"in", "on", "at", "by", "to", "of", "from", "with", "into",
                "onto", "upon", "about", "above", "below", "under", "over",
                "between", "among", "through", "during", "against", "toward",
                "towards", "across", "behind", "beyond", "near", "around",
                "along", "past", "per", "via", "without", "within"}
PRONOUNS_I = {"i", "me", "my", "mine", "myself", "i'm", "i've", "i'll", "i'd"}
PRONOUNS_WE = {"we", "us", "our", "ours", "ourselves", "we're", "we've",
               "we'll", "we'd"}
PRONOUNS_YOU = {"you", "your", "yours", "yourself", "yourselves", "you're",
                "you've", "you'll", "you'd"}
PRONOUNS_OTHER = {"he", "him", "his", "she", "her", "hers", "it", "its",
                  "they", "them", "their", "theirs", "this", "that", "these",
                  "those", "it's", "that's"}
AUXILIARIES = {"be", "am", "is", "are", "was", "were", "been", "being",
               "have", "has", "had", "having", "do", "does", "did", "doing",
               "will", "would", "shall", "should", "can", "could", "may",
               "might", "must", "isn't", "aren't", "wasn't", "weren't",
               "don't", "doesn't", "didn't", "won't", "wouldn't", "can't",
               "couldn't", "shouldn't", "hasn't", "haven't", "hadn't"}
CONJUNCTIONS = {"and", "but", "or", "nor", "so", "yet", "because", "although",
                "though", "while", "whereas", "unless", "until", "since",
                "if", "than"}
ADVERBS = {"very", "really", "quite", "rather", "just", "only", "also",
           "too", "even", "still", "again", "then", "there", "here", "now",
           "well", "maybe", "perhaps", "actually", "honestly", "genuinely"}
NEGATIONS = {"no", "not", "never", "none", "nothing", "neither", "nobody",
             "n't", "isn't", "aren't", "wasn't", "weren't", "don't",
             "doesn't", "didn't", "won't", "wouldn't", "can't", "couldn't"}

EMPATH_CATEGORIES = ["positive_emotion", "negative_emotion", "social",
                     "achievement", "work", "leisure", "money", "health",
                     "family", "friends", "anger", "fear", "sadness", "joy",
                     "trust", "anticipation"]

DISCLAIMER = ("LIWC-adjacent proxies computed from open lexicons (Empath + "
              "word-category rates). Direction-preserving only; NOT LIWC "
              "percentiles. Compare between texts measured by this script.")


def _rate(words, vocab):
    n = len(words)
    return sum(1 for w in words if w in vocab) / n * 100 if n else 0.0


def analyze_psycho(text, lexicon=None):
    words = tokenize(text)
    i_rate = _rate(words, PRONOUNS_I)
    we_rate = _rate(words, PRONOUNS_WE)
    you_rate = _rate(words, PRONOUNS_YOU)
    pronouns = i_rate + we_rate + you_rate + _rate(words, PRONOUNS_OTHER)

    analytic = (30 + _rate(words, ARTICLES) + _rate(words, PREPOSITIONS)
                - pronouns - _rate(words, AUXILIARIES)
                - _rate(words, CONJUNCTIONS) - _rate(words, ADVERBS)
                - _rate(words, NEGATIONS))

    out = {
        "analytic_proxy": round(analytic, 2),
        "clout_proxy": round(we_rate + you_rate - i_rate, 2),
        "components": {
            "i": round(i_rate, 2), "we": round(we_rate, 2),
            "you": round(you_rate, 2),
            "articles": round(_rate(words, ARTICLES), 2),
            "prepositions": round(_rate(words, PREPOSITIONS), 2),
            "negations": round(_rate(words, NEGATIONS), 2),
        },
    }

    if lexicon is not None:
        emp = lexicon.analyze(" ".join(words), categories=EMPATH_CATEGORIES,
                              normalize=True) or {}
        empath_rates = {k: round(v * 100, 3) for k, v in emp.items()}
        out["tone_proxy"] = round(empath_rates.get("positive_emotion", 0.0)
                                  - empath_rates.get("negative_emotion", 0.0), 3)
        out["empath_per_100_words"] = empath_rates
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()

    try:
        from empath import Empath
        lexicon = Empath()
    except ImportError:
        lexicon = None  # proxies that need no lexicon still work

    results = []
    for path in args.files:
        with open(path, encoding="utf-8") as f:
            text = strip_frontmatter(f.read())
        results.append({"path": path, "proxies": analyze_psycho(text, lexicon)})

    # aggregate scalar proxies across files
    keys = ["analytic_proxy", "clout_proxy"] + (["tone_proxy"] if lexicon else [])
    aggregate = {}
    for k in keys:
        vals = [r["proxies"][k] for r in results]
        aggregate[k] = {"mean": round(_mean(vals), 2), "sd": round(_sd(vals, ddof=1), 2)}

    print(json.dumps({"disclaimer": DISCLAIMER,
                      "empath_available": lexicon is not None,
                      "files": results, "aggregate": aggregate}, indent=2))


def _reexec_in_venv():
    venv_dir = os.path.dirname(os.path.dirname(VENV_PY))
    if os.path.exists(VENV_PY) and not sys.prefix.startswith(venv_dir):
        os.execv(VENV_PY, [VENV_PY, os.path.abspath(__file__)] + sys.argv[1:])


if __name__ == "__main__":
    _reexec_in_venv()
    main()
