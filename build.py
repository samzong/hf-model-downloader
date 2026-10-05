import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_architecture():
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    if machine in ("x86_64", "amd64"):
        return "x86_64"
    return machine


def build_app():
    system = platform.system().lower()
    if system not in ("darwin", "windows"):
        raise SystemExit(f"Unsupported build platform: {system}. Use macOS or Windows.")
    arch = get_architecture()
    root = Path(__file__).resolve().parent
    app_name = "hf-model-downloader"
    output_name = (
        f"{app_name}.app" if system == "darwin" else f"{app_name}-windows-{arch}"
    )
    bundle_name = app_name if system == "darwin" else output_name
    icon_path = root / "assets" / ("icon.icns" if system == "darwin" else "icon.ico")
    if not icon_path.is_file():
        raise SystemExit(f"Build icon missing: {icon_path}")
    os.environ["PYINSTALLER_CONFIG_DIR"] = str(root / ".pyinstaller-cache")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        f"--name={bundle_name}",
        "--add-data",
        "README.md:.",
        "--add-data",
        "assets:assets",
        "--collect-all",
        "hf_xet",
        "--hidden-import",
        "modelscope.hub.snapshot_download",
        "--onedir",
        "--windowed",
        "--icon",
        str(icon_path),
    ]
    if system == "darwin":
        cmd.extend(
            [
                "--osx-bundle-identifier",
                "com.samzong.hf-model-downloader",
                "--target-arch",
                arch,
            ]
        )
    cmd.append("main.py")
    for name in ("build", "dist"):
        path = root / name
        if path.exists():
            shutil.rmtree(path)
    for spec in root.glob("*.spec"):
        spec.unlink()
    print(f"Building {output_name} for {system} ({arch})...", flush=True)
    subprocess.run(cmd, check=True, cwd=root)
    output_path = root / "dist" / output_name
    if not output_path.is_dir():
        raise SystemExit(f"Build output missing: {output_path}")
    size_mb = sum(p.stat().st_size for p in output_path.rglob("*") if p.is_file()) / (
        1024 * 1024
    )
    print(f"\nBuild Summary:\n- Output: dist/{output_name}/\n- Size: {size_mb:.2f} MB")
    print(f"- System: {system}\n- Architecture: {arch}")
    if system == "windows":
        zip_path = shutil.make_archive(
            str(root / f"hf-model-downloader-windows-{arch}"),
            "zip",
            root_dir=root / "dist",
            base_dir=output_name,
        )
        print(f"Windows package created: {zip_path}")
        shutil.rmtree(output_path)


if __name__ == "__main__":
    build_app()
