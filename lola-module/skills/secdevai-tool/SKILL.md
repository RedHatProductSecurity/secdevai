---
name: secdevai-tool
description: Run external security analysis tools (Bandit, Gosec, Scorecard, Semgrep) inside read-only containers via podman/docker. Use when the user wants to execute specific security tools, combine their output with AI analysis, or run all available tools at once.
---

# SecDevAI Tool Command

## Description
Run external security analysis tools inside isolated, read-only containers. Invoked via `/secdevai tool` or the `/secdevai-tool` alias.

## Usage
```
/secdevai tool bandit          # Python security linter
/secdevai tool gosec           # Go security linter
/secdevai tool scorecard       # Repository security assessment (OSSF)
/secdevai tool semgrep         # Semgrep
/secdevai tool all             # Run all relevant tools for the detected language
/secdevai-tool bandit          # Alias form
```

## Available Tools

| Tool | GitHub | Container Image | Language |
|------|--------|-----------------|----------|
| bandit | https://github.com/PyCQA/bandit | `ghcr.io/pycqa/bandit/bandit` | Python |
| gosec | https://github.com/securego/gosec | `ghcr.io/securego/gosec:latest` | Go |
| scorecard | https://github.com/ossf/scorecard | `gcr.io/openssf/scorecard:stable` | All |
| semgrep | https://github.com/semgrep/semgrep | `local/semgrep` (built locally) | Multi-language |

```yaml
tool_resolution:
  python:
    tools:
      - bandit
      - semgrep
      - scorecard

  go:
    tools:
      - gosec
      - semgrep
      - scorecard

  java:
    tools:
      - semgrep
      - scorecard

  javascript:
    tools:
      - semgrep
      - scorecard

  rust:
    tools:
      - semgrep
      - scorecard
```

## Prerequisites

Tools run exclusively inside containers for isolation and reproducibility. A container runtime is required:

- **Podman** (recommended): `brew install podman` / `dnf install podman` / `apt install podman`
- **Docker**: https://docs.docker.com/get-docker/

The helper script `scripts/container-run.sh` auto-detects `podman` or `docker` at runtime, runs containers with hardened defaults (all capabilities dropped, no-new-privileges, network disabled, resource limits), and prints installation guidance if neither runtime is found.

**Note**: All scripts are under the `${BASE_DIR}` directory (e.g.: `.claude/` or `.cursor/`).

## Expected Response

When this skill is invoked, follow these steps:

### Step 1: Tool Selection

**If no tool specified** (e.g., `/secdevai-tool` with no arguments):
- Prompt the user to select a tool
- Display the Available Tools table above
- Show usage examples
- Do NOT run any tool automatically — wait for user input

```yaml
input_schema:
  tool:
    - bandit
    - gosec
    - scorecard
    - semgrep
    - all
```

### Step 2: Run Tool

Use `${BASE_DIR}/scripts/container-run.sh` to run the container image for the chosen tool. The script auto-detects podman/docker, mounts the current directory read-only at `/src`, and forwards any extra arguments to the container entrypoint.

```sh
# Usage: scripts/container-run.sh [--env K=V]... <image> [args...]
# Network is always disabled (--network=none).
```

#### Tool: Bandit

**Usage:**
```sh
# bandit (Python)
${BASE_DIR}/scripts/container-run.sh ghcr.io/pycqa/bandit/bandit -r . -f json -q
```

#### Tool: GoSec

**Usage:**
```sh
# gosec (Go)
${BASE_DIR}/scripts/container-run.sh ghcr.io/securego/gosec:latest -fmt=sarif ./...
```

#### Tool: Scorecard

**Usage:**
```sh
# scorecard (local-only, filesystem checks only — no GitHub API access)
${BASE_DIR}/scripts/container-run.sh gcr.io/openssf/scorecard:stable --local . --format json
```

**Scorecard**: Runs in `--local` mode only (no network, no GitHub token). Filesystem-based checks work (pinned dependencies, SECURITY.md, dangerous workflows); checks requiring the GitHub API (branch protection, CI/CD status) are skipped.

#### Tool: semgrep

**Semgrep**: Uses a locally built image (`secdevai/semgrep:local`) that bundles two offline rule sets:
- `/sgrules` — [semgrep/semgrep-rules](https://github.com/semgrep/semgrep-rules) (community rules)
- `/sgrules-trail` — [trailofbits/semgrep-rules](https://github.com/trailofbits/semgrep-rules) (security-focused, AGPL-3.0)

**Build Semgrep container**: (`secdevai/semgrep:local`)
```sh
${BASE_DIR}/scripts/build-semgrep.sh
```

**Semgrep config resolution**
```yaml
semgrep_config_resolution:
  python:
    configs:
      - /sgrules/python

  go:
    configs:
      - /sgrules/go
      - /sgrules-trail/go

  javascript:
    configs:
      - /sgrules/javascript

  typescript:
    configs:
      - /sgrules/typescript

  java:
    configs:
      - /sgrules/java

  ruby:
    configs:
      - /sgrules/ruby
      - /sgrules-trail/ruby

  rust:
    configs:
      - /sgrules/rust
      - /sgrules-trail/rs

  all:
    configs:
      - /sgrules
      - /sgrules-trail
```

**Language detection:**
```yaml
language_detection:
  python:
    files:
      - pyproject.toml
      - requirements.txt
      - setup.py
      - Pipfile
      - poetry.lock
      - "*.py"

  go:
    files:
      - go.mod
      - go.sum
      - "*.go"

  typescript:
    files:
      - tsconfig.json
      - "*.ts"
      - "*.tsx"

  javascript:
    files:
      - package.json
      - "*.js"
      - "*.jsx"

  java:
    files:
      - pom.xml
      - build.gradle
      - build.gradle.kts
      - "*.java"

  ruby:
    files:
      - Gemfile
      - Gemfile.lock
      - "*.rb"

  rust:
    files:
      - Cargo.toml
      - Cargo.lock
      - "*.rs"
```

Select `--config` based on the detected project language.

**Usage:**
```sh
${BASE_DIR}/scripts/container-run.sh \
    --env HOME=/tmp \
    secdevai/semgrep:local \
    scan /src \
    --config /sgrules/<lang> \
    --sarif \
    --metrics off \
    --disable-version-check
```

**Example resolution for Golang:**
```sh
${BASE_DIR}/scripts/container-run.sh \
  --env HOME=/tmp \
  secdevai/semgrep:local \
  scan /src \
  --config /sgrules/go \
  --config /sgrules-trail/go \
  --sarif \
  --metrics off \
  --disable-version-check
```

#### Tool: all

**If `all` is specified**: detect the project language and run each relevant(see Available Tools) tool sequentially, collecting all JSON output. 

If the script exits with an error about missing podman/docker, relay the installation instructions to the user and stop.

### Step 3: Present Findings

- Parse the JSON output from each tool
- Synthesize with AI analysis — add context, explain impact, suggest remediations
- Present findings in a structured format similar to `/secdevai review`
- When `all` is used, clearly indicate which findings came from which tool

### Step 4: Save Results

Collect findings into structured format and export:

```python
import importlib.util
from pathlib import Path

script_path = Path("secdevai-export/scripts/results_exporter.py")
spec = importlib.util.spec_from_file_location("results_exporter", script_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

data = {
    "metadata": {
        "tool": "[tool-name]",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "analyzer": "[tool-name] Security Tool",
    },
    "summary": {
        "total_findings": [count],
        "critical": [count],
        "high": [count],
        "medium": [count],
        "low": [count],
        "info": [count],
    },
    "findings": [list of tool finding objects],
}

markdown_path, sarif_path = mod.export_results(data, command_type="tool")
```

- The exporter prompts the user to confirm the result directory (default: `secdevai-results`)
- Results are saved with timestamp: `secdevai-tool-YYYYMMDD_HHMMSS.md` and `.sarif`
