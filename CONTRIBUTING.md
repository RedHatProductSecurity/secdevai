# Contributing to SecDevAI

Contributions to the project are always welcome. Please feel free to create pull requests, or report issues.

## How to Contribute

The primary way to contribute is by updating or adding more contexts in the **`lola-module/`** directory and by extending or improving existing **skills**.

Note: The `lola-module/` directory can package not only skills, but also commands, subagents, and MCP server components.

### Lola Module (`lola-module/`)

The `lola-module/` directory contains the AI Context Module that packages all SecDevAI skills and contexts. It follows the [Lola](https://github.com/RedHatProductSecurity/lola) pattern for distributing AI skills across multiple assistants (Cursor, Claude Code, Gemini CLI, and more).

You can contribute by:
- Adding new security context files (e.g., language-specific patterns, framework-specific rules)
- Improving existing context files with better detection patterns or examples
- Adding new tool integration scripts

### Skills

Each skill follows the [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) pattern with a `SKILL.md` file that provides instructions for the AI assistant. You can contribute by:
- Improving existing skill instructions for better accuracy and coverage
- Adding new skills for additional security workflows

### Extending Security Contexts

For guidance on adding new security context such as rules, tools, or languages, see the **"Extending SecDevAI"** section in [`docs/USAGE.md`](https://github.com/RedHatProductSecurity/secdevai/blob/main/docs/USAGE.md#extending-secdevai).

We encourage you to contribute your context extensions back to help the community! AI-generated code is absolutely welcome, however, just make sure to test your changes and provide clear descriptions in your PR. Every contribution, big or small, helps make SecDevAI better.

## Local Development

### Running tests

From the `secdevai` repository run:

```sh
uv run pytest
```

### pre-commit hooks

Install pre-commit hooks:

```sh
uv run pre-commit install
```

### Running

From another repository run:

```sh
uvx --no-cache /path/to/secdevai
```
