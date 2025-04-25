#!/bin/bash
set -euo pipefail

# Default repos and keyrings
BOOTSTRAP_REPO=https://packages.wolfi.dev/bootstrap/stage3
OS_REPO=https://packages.wolfi.dev/os
BOOTSTRAP_KEY=https://packages.wolfi.dev/bootstrap/stage3/wolfi-signing.rsa.pub
OS_KEY=https://packages.wolfi.dev/os/wolfi-signing.rsa.pub

melange build "$@" \
  --repository-append "${BOOTSTRAP_REPO}" \
  --repository-append "${OS_REPO}" \
  --keyring-append "${BOOTSTRAP_KEY}" \
  --keyring-append "${OS_KEY}"
