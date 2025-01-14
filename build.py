import os
import platform
import subprocess

def build_app():
    system = platform.system().lower()
    app_name = "huggingface-model-downloader"
    
    # Ensure assets directory exists
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
    
    # Base PyInstaller command
    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "--name", app_name,
        "--add-data", "README.md:.",
        "--hidden-import", "huggingface_hub",
        "--hidden-import", "tqdm",
        "--hidden-import", "requests",
    ]
    
    # Platform specific options
    if system == "darwin":  # macOS
        icon_path = os.path.join(assets_dir, "icon.icns")
        cmd.extend([
            "--windowed",
            "--icon", icon_path,
            "--osx-bundle-identifier", "com.huggingface.modeldownloader",
        ])
        output_name = f"{app_name}.app"
    elif system == "windows":
        icon_path = os.path.join(assets_dir, "icon.ico")
        cmd.extend([
            "--windowed",
            "--icon", icon_path,
        ])
        output_name = f"{app_name}.exe"
    else:  # Linux
        icon_path = os.path.join(assets_dir, "icon.png")
        cmd.extend([
            "--windowed",
            "--icon", icon_path,
        ])
        output_name = app_name
    
    # Check if icon exists
    if not os.path.exists(icon_path):
        print(f"Warning: Icon file not found at {icon_path}")
        print(f"Please place the appropriate icon file in the assets directory:")
        print("- macOS: assets/icon.icns")
        print("- Windows: assets/icon.ico")
        print("- Linux: assets/icon.png")
    
    # Add main script
    cmd.append("main.py")
    
    print(f"Building {output_name} for {system}...")
    subprocess.run(cmd, check=True)
    print(f"Build completed! Output: dist/{output_name}")

if __name__ == "__main__":
    build_app() 