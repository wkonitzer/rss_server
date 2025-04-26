#!/bin/bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <arch> <melange arguments...>"
  echo "Example: $0 x86_64 melange/package.yaml --out-dir packages"
  exit 1
fi

ARCH="$1"
shift

BOOTSTRAP_REPO=https://packages.wolfi.dev/bootstrap/stage3
OS_REPO=https://packages.wolfi.dev/os
BOOTSTRAP_KEY=https://packages.wolfi.dev/bootstrap/stage3/wolfi-signing.rsa.pub
OS_KEY=https://packages.wolfi.dev/os/wolfi-signing.rsa.pub

# Find the YAML file being built
YAML_FILE=""
for arg in "$@"; do
  if [[ "$arg" == *.yaml ]]; then
    YAML_FILE="$arg"
    break
  fi
done

if [ -z "$YAML_FILE" ]; then
  echo "Error: No YAML file provided in arguments."
  exit 1
fi

# Parse Python versions from the YAML (simple grep)
PY_VERSIONS=$(grep -E '^[[:space:]]*3\.(10|11|12|13):' "$YAML_FILE" | sed -E 's/^[[:space:]]*3\.([0-9]+):.*$/3.\1/' | sort -u)

# Default packages to append
EXTRA_PACKAGES=(busybox)

# Add python versions dynamically
for ver in $PY_VERSIONS; do
  EXTRA_PACKAGES+=("python-${ver}")
done

# Now run melange build
melange build "$@" \
  --repository-append "${BOOTSTRAP_REPO}" \
  --repository-append "${OS_REPO}" \
  --keyring-append "${BOOTSTRAP_KEY}" \
  --keyring-append "${OS_KEY}" \
  --runner docker \
  $(printf -- '--package-append %s ' "${EXTRA_PACKAGES[@]}")
