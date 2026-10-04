#!/bin/bash
# One-time environment setup for voice_match.py (embedding-based voice scoring).
# Creates a dedicated venv and pre-downloads the style-embedding model.
# stylometry.py does NOT need this — it is stdlib-only.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$SKILL_DIR/.venv"

echo "Creating venv at $VENV ..."
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
echo "Installing sentence-transformers (several hundred MB incl. torch) ..."
"$VENV/bin/pip" install --quiet sentence-transformers

echo "Pre-downloading style embedding model ..."
"$VENV/bin/python" - <<'EOF'
from sentence_transformers import SentenceTransformer
SentenceTransformer("AnnaWegmann/Style-Embedding")
print("Model cached OK.")
EOF

echo "Done. voice_match.py is ready."
