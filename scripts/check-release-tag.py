import argparse
import os
import re
import subprocess
import tomllib
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tag", nargs="?")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--check-ref", action="store_true")
    args = parser.parse_args()
    manifest = Path("pyproject.toml")
    source = manifest.read_text()
    actual = tomllib.loads(source)["project"]["version"]
    tag = args.tag
    if tag is None:
        match = re.fullmatch(
            r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
            r"(?:(a|b|rc)([1-9][0-9]*))?",
            actual,
        )
        if not match:
            raise SystemExit(f"Invalid PEP 440 release version: {actual}")
        major, minor, patch, stage, number = match.groups()
        tag = f"v{major}.{minor}.{patch}"
        if stage:
            stages = {"a": "alpha", "b": "beta", "rc": "rc"}
            tag += f"-{stages[stage]}.{number}"
    match = re.fullmatch(
        r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
        r"(?:-(alpha|beta|rc)\.([1-9][0-9]*))?",
        tag,
    )
    if not match:
        raise SystemExit(f"Invalid SemVer release tag: {tag}")
    major, minor, patch, stage, number = match.groups()
    expected = f"{major}.{minor}.{patch}"
    if stage:
        stages = {"alpha": "a", "beta": "b", "rc": "rc"}
        expected += f"{stages[stage]}{number}"
    if args.prepare and actual == tag[1:] and actual != expected:
        source = source.replace(f'version = "{actual}"', f'version = "{expected}"', 1)
        manifest.write_text(source)
        actual = tomllib.loads(source)["project"]["version"]
    if actual != expected:
        raise SystemExit(
            f"pyproject.toml version {actual!r} does not match PEP 440 {expected!r}"
        )
    if args.check_ref:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        target = subprocess.check_output(
            ["git", "rev-parse", f"refs/tags/{tag}^{{commit}}"], text=True
        ).strip()
        if head != target:
            raise SystemExit(f"HEAD {head} does not match tag commit {target}")
    version = tag[1:]
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a") as handle:
            handle.write(
                f"version={version}\nis_prerelease={'true' if stage else 'false'}\n"
            )
    print(version)


if __name__ == "__main__":
    main()
