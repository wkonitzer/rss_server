#!/bin/bash
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "Usage: $0 <arch> <python-version> <melange arguments...>"
  echo "Example: $0 x86_64 3.13 melange/apscheduler.yaml ..."
  exit 1
fi

ARCH="$1"
PYTHON_VERSION="$2"
shift 2

BOOTSTRAP_REPO=https://packages.wolfi.dev/bootstrap/stage3
OS_REPO=https://packages.wolfi.dev/os
BOOTSTRAP_KEY=https://packages.wolfi.dev/bootstrap/stage3/wolfi-signing.rsa.pub
OS_KEY=https://packages.wolfi.dev/os/wolfi-signing.rsa.pub

YAML_FILE=""
for arg in "$@"; do
  if [[ "$arg" == *.yaml ]]; then
    YAML_FILE="$arg"
    break
  fi
done

if [ -z "$YAML_FILE" ]; then
  echo "Error: No YAML file provided."
  exit 1
fi

# 🧠 Dynamically extract vars.pypi-package from the YAML
PYPI_PACKAGE=$(grep -A 2 '^vars:' "$YAML_FILE" | grep 'pypi-package' | awk -F ': ' '{print $2}' | tr -d '"' | tr -d "'")

if [ -z "$PYPI_PACKAGE" ]; then
  echo "Error: Could not extract pypi-package from YAML."
  exit 1
fi

echo "Building for Python ${PYTHON_VERSION}, package ${PYPI_PACKAGE}"

melange build "$@" \
  --repository-append "${BOOTSTRAP_REPO}" \
  --repository-append "${OS_REPO}" \
  --keyring-append "${BOOTSTRAP_KEY}" \
  --keyring-append "${OS_KEY}" \
  --runner docker \
  --package-append busybox \
  --package-append python-${PYTHON_VERSION} \
  --only-subpackage py${PYTHON_VERSION//.}-${PYPI_PACKAGE}
