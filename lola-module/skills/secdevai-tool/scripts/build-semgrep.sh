#!/bin/bash

set -euo pipefail

detect_runtime() {
    if command -v podman &>/dev/null; then
        echo "podman"
    elif command -v docker &>/dev/null; then
        echo "docker"
    else
        cat >&2 <<'MSG'
Error: No container runtime found.

SecDevAI requires podman or docker to run security tools in isolated,
read-only containers. Please install one of the following:

  Podman (recommended):
    macOS  : brew install podman && podman machine init && podman machine start
    Fedora : sudo dnf install podman
    Ubuntu : sudo apt install podman

  Docker:
    All OS : https://docs.docker.com/get-docker/

After installing, re-run this command.
MSG
        exit 1
    fi
}

runtime="$(detect_runtime)"
echo "Using runtime: ${runtime}" >&2

BASE_DIR="$(dirname "$0")"
IMAGE_TAG="secdevai/semgrep:local"

exec "$runtime" build \
    -t "${IMAGE_TAG}" \
    -f "${BASE_DIR}/Dockerfile.semgrep" \
    ${BASE_DIR}
