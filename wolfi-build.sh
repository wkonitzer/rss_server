#!/bin/bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <arch> <melange arguments...>"
  exit 1
fi

ARCH="$1"
shift

BOOTSTRAP_REPO=https://packages.wolfi.dev/bootstrap/stage3
OS_REPO=https://packages.wolfi.dev/os
BOOTSTRAP_KEY=https://packages.wolfi.dev/bootstrap/stage3/wolfi-signing.rsa.pub
OS_KEY=https://packages.wolfi.dev/os/wolfi-signing.rsa.pub

melange build "$@" \
  --repository-append "${BOOTSTRAP_REPO}" \
  --repository-append "${OS_REPO}" \
  --keyring-append "${BOOTSTRAP_KEY}" \
  --keyring-append "${OS_KEY}" \
  --runner docker \
  --package-append busybox
