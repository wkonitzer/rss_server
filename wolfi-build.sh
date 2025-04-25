#!/bin/bash
set -euo pipefail

# Check for architecture argument
if [ $# -lt 2 ]; then
  echo "Usage: $0 <arch> <melange arguments...>"
  echo "Example: $0 x86_64 melange/package.yaml --out-dir packages"
  exit 1
fi

ARCH="$1"
shift # shift off the first argument so "$@" has just the melange args

# Map ARCH to container image tag
case "${ARCH}" in
  x86_64)
    BASE_IMAGE="wolfi-builder:latest-amd64"
    ;;
  aarch64)
    BASE_IMAGE="wolfi-builder:latest-arm64"
    ;;
  *)
    echo "Unsupported architecture: ${ARCH}"
    exit 1
    ;;
esac

# Default repos and keyrings
BOOTSTRAP_REPO=https://packages.wolfi.dev/bootstrap/stage3
OS_REPO=https://packages.wolfi.dev/os
BOOTSTRAP_KEY=https://packages.wolfi.dev/bootstrap/stage3/wolfi-signing.rsa.pub
OS_KEY=https://packages.wolfi.dev/os/wolfi-signing.rsa.pub

# Run melange build
melange build "$@" \
  --repository-append "${BOOTSTRAP_REPO}" \
  --repository-append "${OS_REPO}" \
  --keyring-append "${BOOTSTRAP_KEY}" \
  --keyring-append "${OS_KEY}" \
  --runner docker \
  --package-append busybox
