#!/usr/bin/env python3
"""
SecDevAI CLI - Setup tool for SecDevAI

Usage:
    uv tool install .
    secdevai [project-path]
"""

import stat
from pathlib import Path

import typer
from rich.console import Console

# Initialize console
console = Console()

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def main():
    """Entry point for CLI."""
    app()


def _find_module_dir() -> Path | None:
    """Locate the lola-module directory via wheel shared-data.

    Hatchling shared-data (pyproject.toml) installs lola-module to
    {data_dir}/share/secdevai/lola-module. sysconfig.get_path("data")
    resolves the correct prefix for any install method (uv run, uv tool
    install, uvx, pip install).
    """
    import sysconfig

    data_dir = sysconfig.get_path("data")
    if data_dir:
        module_dir = Path(data_dir) / "share" / "secdevai" / "lola-module"
        if module_dir.exists():
            return module_dir

    return None


@app.command()
def init(
    project_path: str = typer.Argument(
        ".", help="Path to project directory (defaults to current directory)"
    ),
):
    """Initialize SecDevAI in a project directory."""
    target_dir = Path(project_path).expanduser().resolve()

    if not target_dir.exists():
        console.print(f"[red]Error:[/red] Directory does not exist: {target_dir}")
        raise typer.Exit(1)

    console.print(f"\n[bold blue]Initializing SecDevAI in:[/bold blue] {target_dir}\n")

    module_dir = _find_module_dir()
    if not module_dir:
        console.print("[red]Error:[/red] lola-module directory not found.")
        console.print(
            "[yellow]Hint:[/yellow] Make sure lola-module is included when installing the package."
        )
        raise typer.Exit(1)

    # Deploy lola-module contents
    deployer = ModuleDeployer(module_dir)
    deployer.deploy(target_dir)

    console.print("\n[bold green]✓ SecDevAI initialized successfully![/bold green]\n")
    console.print("You can now use [bold]/secdevai[/bold] in your AI assistant.")


class ModuleDeployer:
    """Service for deploying lola-module contents to project directory.

    Copies the entire lola-module/ tree into each detected platform directory
    (e.g. .cursor/, .claude/, .gemini/), preserving the directory structure.
    For Gemini CLI, .md files inside commands/ are converted to .toml format.
    """

    SUPPORTED_PLATFORMS = {"cursor", "claude", "gemini"}
    DEFAULT_PLATFORMS = ["cursor", "claude"]

    def __init__(self, module_dir: Path):
        """Initialize module deployer."""
        self.module_dir = module_dir

    def detect_platforms(self, target_dir: Path) -> list[str]:
        """Detect which AI assistant platforms are present."""
        platforms = [
            platform
            for platform in ModuleDeployer.SUPPORTED_PLATFORMS
            if (target_dir / f".{platform}").exists()
        ]
        return platforms or ModuleDeployer.DEFAULT_PLATFORMS

    def _convert_md_to_toml(self, md_content: str) -> str:
        """Convert markdown command to Gemini CLI .toml format.

        According to Gemini CLI documentation:
        - https://cloud.google.com/blog/topics/developers-practitioners/gemini-cli-custom-slash-commands
        - Uses .toml format with 'description' and 'prompt' fields
        - Supports {{args}} for arguments and !{...} for shell commands
        """
        import re

        # Extract description from frontmatter or ## Description section
        description_match = re.search(
            r"##\s+Description\s*\n+(.+?)(?=\n##|\n```|$)", md_content, re.DOTALL
        )
        if description_match:
            description = description_match.group(1).strip()
            description = re.sub(r"^\*\*.*?\*\*:\s*", "", description)
            description = re.sub(r"\n.*", "", description)
            description = description.strip()
        else:
            first_line = md_content.split("\n")[0].strip()
            description = (
                first_line.replace("#", "").strip()
                if first_line.startswith("#")
                else "SecDevAI command"
            )

        description = description.replace('"', '\\"')
        prompt_content = md_content.replace('"""', '\\"\\"\\"')

        return f'''description="{description}"
prompt = """
{prompt_content}
"""
'''

    def _is_commands_dir(self, rel_path: Path) -> bool:
        """Check if a file is inside a commands/ directory."""
        return rel_path.parts[0] == "commands" if rel_path.parts else False

    def deploy(self, target_dir: Path):
        """Deploy lola-module contents to each platform directory."""
        platforms = self.detect_platforms(target_dir)
        console.print(f"[dim]Detected platforms: {', '.join(platforms)}[/dim]\n")

        # Collect all files from lola-module/ (preserving relative paths)
        # note: rglob is recursive glob **/*
        source_files = sorted(f for f in self.module_dir.rglob("*") if f.is_file())

        for platform in platforms:
            platform_dir = target_dir / f".{platform}"

            for source_path in source_files:
                rel_path = source_path.relative_to(self.module_dir)

                # For Gemini CLI: convert commands/*.md to .toml
                if (
                    platform == "gemini"
                    and self._is_commands_dir(rel_path)
                    and source_path.suffix == ".md"
                ):
                    toml_content = self._convert_md_to_toml(source_path.read_text(encoding="utf-8"))
                    target_path = platform_dir / rel_path.with_suffix(".toml")
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(toml_content, encoding="utf-8")
                    continue

                target_path = platform_dir / rel_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(source_path.read_bytes())

                # Make shell scripts executable
                if target_path.suffix == ".sh":
                    self._make_executable(target_path)

            console.print(f"[green]✓[/green] Deployed {len(source_files)} files to .{platform}/")

    def _make_executable(self, file_path: Path):
        """Make file executable by adding +x permissions."""
        current_permissions = file_path.stat().st_mode
        file_path.chmod(current_permissions | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


if __name__ == "__main__":
    main()
