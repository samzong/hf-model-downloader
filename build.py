import os
import platform
import subprocess
import sys

# Set UTF-8 encoding for all I/O operations
os.environ["PYTHONUTF8"] = "1"

def get_architecture():
    """Get the current system architecture."""
    machine = platform.machine().lower()
    if machine in ['arm64', 'aarch64']:
        return 'arm64'
    elif machine in ['x86_64', 'amd64']:
        return 'x86_64'
    else:
        return machine

def build_app():
    system = platform.system().lower()
    arch = get_architecture()
    app_name = "hf-model-downloader"
    
    # Ensure assets directory exists
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
    
    # Base PyInstaller command
    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        f"--name={app_name}",  # Remove arch from base name
        "--add-data", "README.md:.",
        "--hidden-import", "huggingface_hub",
        "--hidden-import", "tqdm",
        "--hidden-import", "requests",
        "--onefile",  # Create a single file
        "--windowed",  # No console window
    ]
    
    # Platform specific options
    if system == "darwin":  # macOS
        icon_path = os.path.join(assets_dir, "icon.icns")
        cmd.extend([
            "--icon", icon_path,
            "--osx-bundle-identifier", "com.samzong.hf-model-downloader",
            "--target-arch", arch,  # Specify target architecture for macOS
        ])
        output_name = f"{app_name}-macos-{arch}.app"  # Explicitly include macos in name
        
    elif system == "windows":  # Windows
        icon_path = os.path.join(assets_dir, "icon.ico")
        cmd.extend([
            "--icon", icon_path,
        ])
        output_name = f"{app_name}-windows-{arch}.exe"  # Explicitly include windows in name
    
    # Check if icon exists
    if not os.path.exists(icon_path):
        print(f"Warning: Icon file not found at {icon_path}")
        print(f"Please place the appropriate icon file in the assets directory:")
        print("- macOS: assets/icon.icns")
        print("- Windows: assets/icon.ico")
    
    # Add main script
    cmd.append("main.py")
    
    try:
        print(f"Building {output_name} for {system} ({arch})...")
        print(f"Command: {' '.join(cmd)}")
        
        # Run PyInstaller
        subprocess.run(cmd, check=True)
        
        # Print build information
        output_path = os.path.join("dist", output_name)
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print("\nBuild Summary:")
            print(f"- Output: dist/{output_name}")
            print(f"- Size: {size_mb:.2f} MB")
            print(f"- System: {system}")
            print(f"- Architecture: {arch}")
            print(f"- Python Version: {platform.python_version()}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error: Build failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_app() 