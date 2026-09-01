#!/bin/sh
# Installs the repo's hooks. Run once after cloning.
ROOT="$(git rev-parse --show-toplevel)"
cp "$ROOT/hooks/pre-push" "$ROOT/.git/hooks/pre-push"
cp "$ROOT/hooks/pre-commit" "$ROOT/.git/hooks/pre-commit"
chmod +x "$ROOT/.git/hooks/pre-commit"
chmod +x "$ROOT/.git/hooks/pre-push"
echo "pre-push and pre-commit hooks installed."
if [ ! -f "$ROOT/.privacy-patterns" ]; then
  cp "$ROOT/.privacy-patterns.example" "$ROOT/.privacy-patterns"
  echo "created .privacy-patterns from the example - EDIT IT with your real terms."
fi
