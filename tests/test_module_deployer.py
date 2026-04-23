"""Tests for ModuleDeployer – the core logic that copies lola-module contents."""

import stat
from pathlib import Path

import pytest

from secdevai_cli import ModuleDeployer

# ---------------------------------------------------------------------------
# detect_platforms
# ---------------------------------------------------------------------------


class TestDetectPlatforms:
    """Tests for ModuleDeployer.detect_platforms."""

    def test_detects_cursor_directory(self, fake_lola_module, target_project):
        (target_project / ".cursor").mkdir()
        deployer = ModuleDeployer(fake_lola_module)
        assert deployer.detect_platforms(target_project) == ["cursor"]

    def test_detects_claude_directory(self, fake_lola_module, target_project):
        (target_project / ".claude").mkdir()
        deployer = ModuleDeployer(fake_lola_module)
        assert deployer.detect_platforms(target_project) == ["claude"]

    def test_detects_gemini_directory(self, fake_lola_module, target_project):
        (target_project / ".gemini").mkdir()
        deployer = ModuleDeployer(fake_lola_module)
        assert deployer.detect_platforms(target_project) == ["gemini"]

    def test_detects_multiple_platforms(self, fake_lola_module, target_project):
        for name in ModuleDeployer.SUPPORTED_PLATFORMS:
            (target_project / f".{name}").mkdir()
        deployer = ModuleDeployer(fake_lola_module)
        platforms = deployer.detect_platforms(target_project)
        assert set(platforms) == ModuleDeployer.SUPPORTED_PLATFORMS

    def test_defaults_to_cursor_and_claude_when_none(self, fake_lola_module, target_project):
        deployer = ModuleDeployer(fake_lola_module)
        platforms = deployer.detect_platforms(target_project)
        assert set(platforms) == set(ModuleDeployer.DEFAULT_PLATFORMS)


# ---------------------------------------------------------------------------
# deploy – file copy completeness
# ---------------------------------------------------------------------------


class TestDeployFilesCopied:
    """Verify that deploy() copies all lola-module files to platform dirs."""

    def _collect_relative_paths(self, root: Path) -> set[str]:
        """Return set of POSIX relative paths for all files under *root*."""
        return {
            str(f.relative_to(root))
            for f in root.rglob("*")
            if f.is_file()
        }

    def test_all_files_deployed_to_cursor(self, fake_lola_module, target_project):
        """Every file in lola-module must appear under .cursor/."""
        (target_project / ".cursor").mkdir()
        deployer = ModuleDeployer(fake_lola_module)
        deployer.deploy(target_project)

        source_files = self._collect_relative_paths(fake_lola_module)
        deployed_files = self._collect_relative_paths(target_project / ".cursor")

        assert source_files == deployed_files

    def test_all_files_deployed_to_claude(self, fake_lola_module, target_project):
        (target_project / ".claude").mkdir()
        deployer = ModuleDeployer(fake_lola_module)
        deployer.deploy(target_project)

        source_files = self._collect_relative_paths(fake_lola_module)
        deployed_files = self._collect_relative_paths(target_project / ".claude")

        assert source_files == deployed_files

    def test_file_contents_match(self, fake_lola_module, target_project):
        """Deployed files must have identical contents to their source."""
        (target_project / ".cursor").mkdir()
        deployer = ModuleDeployer(fake_lola_module)
        deployer.deploy(target_project)

        for src_file in fake_lola_module.rglob("*"):
            if not src_file.is_file():
                continue
            rel = src_file.relative_to(fake_lola_module)
            deployed = target_project / ".cursor" / rel
            assert deployed.exists(), f"Missing: {rel}"
            assert deployed.read_bytes() == src_file.read_bytes(), (
                f"Content mismatch: {rel}"
            )

    def test_deploys_to_all_detected_platforms(self, fake_lola_module, target_project):
        """When multiple platform dirs exist, files go into each one."""
        for name in (".cursor", ".claude"):
            (target_project / name).mkdir()

        deployer = ModuleDeployer(fake_lola_module)
        deployer.deploy(target_project)

        source_files = self._collect_relative_paths(fake_lola_module)

        for platform in ("cursor", "claude"):
            deployed = self._collect_relative_paths(target_project / f".{platform}")
            assert source_files == deployed, f"Mismatch in .{platform}/"

    def test_deploy_with_real_lola_module(self, lola_module_dir, target_project):
        """Integration: deploy the real lola-module tree and verify counts."""
        if not lola_module_dir.exists():
            pytest.skip("lola-module not found (not running from source)")

        (target_project / ".cursor").mkdir()
        deployer = ModuleDeployer(lola_module_dir)
        deployer.deploy(target_project)

        source_count = sum(1 for f in lola_module_dir.rglob("*") if f.is_file())
        deployed_count = sum(
            1 for f in (target_project / ".cursor").rglob("*") if f.is_file()
        )

        assert deployed_count == source_count
        assert source_count > 0, "lola-module should contain at least one file"


# ---------------------------------------------------------------------------
# deploy – shell script permissions
# ---------------------------------------------------------------------------


class TestDeployExecutablePermissions:
    """Verify .sh files are made executable after deployment."""

    def test_sh_files_are_executable(self, fake_lola_module, target_project):
        (target_project / ".cursor").mkdir()
        deployer = ModuleDeployer(fake_lola_module)
        deployer.deploy(target_project)

        sh_files = list((target_project / ".cursor").rglob("*.sh"))
        assert len(sh_files) > 0, "Expected at least one .sh file in test fixture"

        for sh in sh_files:
            mode = sh.stat().st_mode
            assert mode & stat.S_IEXEC, f"{sh.name} should be owner-executable"
            assert mode & stat.S_IXGRP, f"{sh.name} should be group-executable"
            assert mode & stat.S_IXOTH, f"{sh.name} should be other-executable"

    def test_non_sh_files_not_made_executable(self, fake_lola_module, target_project):
        (target_project / ".cursor").mkdir()
        deployer = ModuleDeployer(fake_lola_module)
        deployer.deploy(target_project)

        md_files = list((target_project / ".cursor").rglob("*.md"))
        assert len(md_files) > 0

        for md in md_files:
            mode = md.stat().st_mode
            # .md files should NOT have the executable bit set (unless OS default)
            # We just verify we didn't explicitly add it
            assert not (mode & stat.S_IEXEC and mode & stat.S_IXGRP and mode & stat.S_IXOTH), (
                f"{md.name} should not be executable"
            )


# ---------------------------------------------------------------------------
# deploy – Gemini TOML conversion
# ---------------------------------------------------------------------------


class TestGeminiTomlConversion:
    """Verify Gemini platform converts commands/*.md to .toml format."""

    def test_md_to_toml_basic_conversion(self, fake_lola_module):
        deployer = ModuleDeployer(fake_lola_module)
        md_content = "# My Command\n\n## Description\nDoes something useful.\n"
        toml = deployer._convert_md_to_toml(md_content)

        assert 'description=' in toml
        assert 'prompt = """' in toml
        assert "# My Command" in toml

    def test_md_to_toml_escapes_quotes(self, fake_lola_module):
        deployer = ModuleDeployer(fake_lola_module)
        md_content = '# Command\n\n## Description\nUses "quoted" text.\n'
        toml = deployer._convert_md_to_toml(md_content)

        # Double quotes in description should be escaped
        assert '\\"' in toml

    def test_gemini_commands_dir_converts(self, tmp_path):
        """commands/*.md should become .toml under .gemini/."""
        module_dir = tmp_path / "lola-module"
        cmd_dir = module_dir / "commands"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "review.md").write_text(
            "# Review\n\n## Description\nRun security review.\n"
        )

        target = tmp_path / "project"
        target.mkdir()
        (target / ".gemini").mkdir()

        deployer = ModuleDeployer(module_dir)
        deployer.deploy(target)

        # .md should NOT exist, .toml SHOULD exist
        assert not (target / ".gemini" / "commands" / "review.md").exists()
        assert (target / ".gemini" / "commands" / "review.toml").exists()

        toml_content = (target / ".gemini" / "commands" / "review.toml").read_text()
        assert 'description=' in toml_content
        assert 'prompt = """' in toml_content

    def test_non_gemini_does_not_convert(self, tmp_path):
        """commands/*.md stays as .md for cursor/claude platforms."""
        module_dir = tmp_path / "lola-module"
        cmd_dir = module_dir / "commands"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "review.md").write_text("# Review\n")

        target = tmp_path / "project"
        target.mkdir()
        (target / ".cursor").mkdir()

        deployer = ModuleDeployer(module_dir)
        deployer.deploy(target)

        assert (target / ".cursor" / "commands" / "review.md").exists()
        assert not (target / ".cursor" / "commands" / "review.toml").exists()

    def test_is_commands_dir_detection(self, fake_lola_module):
        deployer = ModuleDeployer(fake_lola_module)
        assert deployer._is_commands_dir(Path("commands/review.md")) is True
        assert deployer._is_commands_dir(Path("skills/secdevai/SKILL.md")) is False
        assert deployer._is_commands_dir(Path("")) is False


# ---------------------------------------------------------------------------
# deploy – idempotency / overwrite
# ---------------------------------------------------------------------------


class TestDeployIdempotency:
    """Running deploy twice should overwrite without errors."""

    def test_deploy_twice_no_error(self, fake_lola_module, target_project):
        (target_project / ".cursor").mkdir()
        deployer = ModuleDeployer(fake_lola_module)

        deployer.deploy(target_project)
        deployer.deploy(target_project)  # Should not raise

        # Files still present and correct
        for src in fake_lola_module.rglob("*"):
            if src.is_file():
                rel = src.relative_to(fake_lola_module)
                deployed = target_project / ".cursor" / rel
                assert deployed.exists()

    def test_deploy_creates_missing_subdirectories(self, fake_lola_module, target_project):
        """Platform dir exists but nested dirs do not – deploy creates them."""
        (target_project / ".cursor").mkdir()
        deployer = ModuleDeployer(fake_lola_module)
        deployer.deploy(target_project)

        # Spot-check: deeply nested scripts dir should exist
        tool_scripts = target_project / ".cursor" / "skills" / "secdevai-tool" / "scripts"
        assert tool_scripts.is_dir()
