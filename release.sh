#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:?Usage: ./release.sh <version>  (z.B. 1.2.0)}"
VERSION="${VERSION#v}"

[[ -z "$(git status --porcelain)" ]] || { echo "Working tree nicht sauber."; exit 1; }

git tag "v$VERSION"
git push origin main "v$VERSION"
echo "v$VERSION getaggt – GitHub Action baut ghcr.io Image."
