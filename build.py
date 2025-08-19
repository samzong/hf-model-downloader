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
        f"--name={app_name}",
        "--add-data", "README.md:.",
        "--hidden-import", "huggingface_hub",
        "--hidden-import", "tqdm",
        "--hidden-import", "requests",
        "--onedir",  # Create a directory bundle
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
        # Use architecture-specific name for PyInstaller
        win_app_name = f"{app_name}-windows-{arch}"
        cmd[cmd.index(f"--name={app_name}")] = f"--name={win_app_name}"
        cmd.extend([
            "--icon", icon_path,
        ])
        output_name = win_app_name  # Directory name for onedir mode
    
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
            if os.path.isdir(output_path):
                # Calculate directory size for onedir mode
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(output_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        total_size += os.path.getsize(filepath)
                size_mb = total_size / (1024 * 1024)
                print("\nBuild Summary:")
                print(f"- Output: dist/{output_name}/ (directory)")
                print(f"- Total Size: {size_mb:.2f} MB")
            else:
                # Single file mode
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                print("\nBuild Summary:")
                print(f"- Output: dist/{output_name}")
                print(f"- Size: {size_mb:.2f} MB")
            
            print(f"- System: {system}")
            print(f"- Architecture: {arch}")
            print(f"- Python Version: {platform.python_version()}")
            
            if system == "windows":
                exe_name = f"{output_name}.exe" if system == "windows" else f"{app_name}.exe"
                exe_path = os.path.join(output_path, exe_name)
                if os.path.exists(exe_path):
                    print(f"- Executable: {exe_name}")
            
            print("\nTip: To fix icon issues, run `make fix-icons`")
        
        # Create zip package for Windows
        if system == "windows":
            print("\nCreating Windows package...")
            success = create_windows_package(output_name, arch)
            if success:
                # Remove original directory after creating package
                import shutil
                dist_dir = os.path.join("dist", output_name)
                if os.path.exists(dist_dir):
                    shutil.rmtree(dist_dir)
                    print(f"✓ Removed original directory: {dist_dir}")
                    print("✓ Windows package created successfully")
        
    except subprocess.CalledProcessError as e:
        print(f"Error: Build failed: {e}")
        sys.exit(1)

def create_windows_package(app_dir_name, arch):
    """Create Windows zip package"""
    try:
        print(f"Checking for app directory: dist/{app_dir_name}")
        app_dir_path = os.path.join("dist", app_dir_name)
        
        if not os.path.exists(app_dir_path):
            print(f"✗ App directory not found: {app_dir_path}")
            return False
        
        print(f"✓ App directory found: {app_dir_path}")
        print(f"Contents: {os.listdir(app_dir_path)}")
        
        # Create zip package
        import zipfile
        zip_name = f"hf-model-downloader-windows-{arch}.zip"
        
        print(f"Creating zip package: {zip_name}")
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(app_dir_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Create archive path relative to the app directory
                    archive_path = os.path.relpath(file_path, "dist")
                    zipf.write(file_path, archive_path)
        
        if os.path.exists(zip_name):
            zip_size = os.path.getsize(zip_name) / (1024 * 1024)
            print(f"✓ Windows package created: {zip_name} ({zip_size:.2f} MB)")
            return True
        else:
            print(f"✗ Package file not found: {zip_name}")
            return False
        
    except Exception as e:
        print(f"⚠ Failed to create package: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    build_app() 