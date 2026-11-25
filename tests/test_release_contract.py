import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from semantic_release.commit_parser.angular import (
    AngularCommitParser,
    AngularParserOptions,
)
from semantic_release.enums import LevelBump

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check-release-tag.py"


def run_gate(tmp_path, version, *args):
    (tmp_path / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n')
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_OUTPUT": str(tmp_path / "output")},
        capture_output=True,
        text=True,
    )


def test_release_commit_types():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    options = config["tool"]["semantic_release"]["commit_parser_options"]
    parser = AngularCommitParser(AngularParserOptions(**options))
    for kind in ("docs", "style", "refactor", "test", "chore", "ci", "build"):
        assert (
            parser.parse_message(f"{kind}: update files").bump == LevelBump.NO_RELEASE
        )
        assert parser.parse_message(f"{kind}!: change contract").bump == LevelBump.MAJOR
    assert parser.parse_message("feat: add feature").bump == LevelBump.MINOR
    for kind in ("fix", "perf"):
        assert parser.parse_message(f"{kind}: improve behavior").bump == LevelBump.PATCH
    assert (
        parser.parse_message("fix: change contract\n\nBREAKING CHANGE: new format").bump
        == LevelBump.MAJOR
    )


@pytest.mark.parametrize(
    "suffix,pep", [("", ""), ("-alpha.1", "a1"), ("-beta.2", "b2"), ("-rc.10", "rc10")]
)
def test_release_mapping(tmp_path, suffix, pep):
    result = run_gate(tmp_path, f"1.2.3{pep}", f"v1.2.3{suffix}")
    assert result.returncode == 0, result.stderr
    output = (tmp_path / "output").read_text()
    assert f"version=1.2.3{suffix}\n" in output
    assert f"is_prerelease={'true' if suffix else 'false'}\n" in output
    result = run_gate(tmp_path, f"1.2.3{pep}")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"1.2.3{suffix}"


@pytest.mark.parametrize(
    "tag",
    [
        "v0.1.0-fix.1",
        "v01.2.0",
        "v1.2.3-rc.0",
        "v1.2.3-beta.01",
        "v1.2.3+build.1",
        "v1.2.3-rc1",
    ],
)
def test_invalid_release_tag(tmp_path, tag):
    assert run_gate(tmp_path, "1.2.3", tag).returncode != 0
    assert not (tmp_path / "output").exists()


def test_release_version_mismatch(tmp_path):
    assert run_gate(tmp_path, "1.2.4", "v1.2.3").returncode != 0
    assert run_gate(tmp_path, "1.2.4", "v1.2.3", "--prepare").returncode != 0
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("stage,pep", [("alpha", "a"), ("beta", "b"), ("rc", "rc")])
def test_semantic_release_preparation(tmp_path, stage, pep):
    result = run_gate(tmp_path, f"1.2.3-{stage}.1", f"v1.2.3-{stage}.1", "--prepare")
    assert result.returncode == 0, result.stderr
    assert (
        tomllib.loads((tmp_path / "pyproject.toml").read_text())["project"]["version"]
        == f"1.2.3{pep}1"
    )
