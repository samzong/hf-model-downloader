import os
import platform
import subprocess
import sys
import io

# Set UTF-8 encoding for all I/O operations
os.environ["PYTHONUTF8"] = "1"

# Force stdout to use UTF-8 encoding on Windows
if platform.system().lower() == "windows":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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
    
    # Note: Icon generation is now a separate step in the Makefile
    # Please run `make icons` to generate icons before running this script
    # Or directly use the `make build` command, which will automatically depend on the icons target
    
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
        print(f"Warning: Icon file not found: {icon_path}")
        print(f"Please make sure you've run `make icons` to generate icon files, or place appropriate icon files in the assets directory:")
        print("- macOS: assets/icon.icns")
        print("- Windows: assets/icon.ico")
        print("You can continue building, but the application will not have a custom icon")
    
    # Add main script
    cmd.append("main.py")
    
    try:
        print(f"Building {output_name} for {system} ({arch})...")
        print(f"Command: {' '.join(cmd)}")
        
        # Run PyInstaller
        subprocess.run(cmd, check=True)
        
        # Note: Icon fixing is now a separate step in the Makefile (make fix-icons)
        # We no longer automatically fix icon issues here, but rely on the steps in the Makefile
        
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
            print("\nTip: To fix icon issues, run `make fix-icons`")
        
    except subprocess.CalledProcessError as e:
        print(f"Error: Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_app() 