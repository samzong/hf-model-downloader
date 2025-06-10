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
        cmd.extend([
            "--icon", icon_path,
        ])
        output_name = f"{app_name}-windows-{arch}"  # Directory name for onedir mode
    
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
                exe_path = os.path.join(output_path, f"{app_name}.exe")
                if os.path.exists(exe_path):
                    print(f"- Executable: {app_name}.exe")
            
            print("\nTip: To fix icon issues, run `make fix-icons`")
        
        # Create installer for Windows and clean up
        if system == "windows":
            print("\nCreating Windows installer...")
            success = create_windows_installer(output_name, app_name)
            if success:
                # Remove original directory after creating installer
                import shutil
                dist_dir = os.path.join("dist", output_name)
                if os.path.exists(dist_dir):
                    shutil.rmtree(dist_dir)
                    print(f"✓ Removed original directory: {dist_dir}")
                    print("✓ Only installer package will be distributed")
        
    except subprocess.CalledProcessError as e:
        print(f"Error: Build failed: {e}")
        sys.exit(1)

def create_windows_installer(app_dir_name, app_name):
    """Create Windows installer using NSIS"""
    try:
        # Check if NSIS is available
        subprocess.run(["makensis", "/VERSION"], check=True, capture_output=True)
        
        # Update NSIS script with actual directory name
        nsi_content = None
        with open("installer.nsi", "r", encoding="utf-8") as f:
            nsi_content = f.read()
        
        # Replace the placeholder with actual directory name
        nsi_content = nsi_content.replace(
            'file /r "dist\\${APPNAME}-windows-*\\*"',
            f'file /r "dist\\{app_dir_name}\\*"'
        )
        
        # Write temporary NSI file
        with open("installer_temp.nsi", "w", encoding="utf-8") as f:
            f.write(nsi_content)
        
        # Build installer
        subprocess.run(["makensis", "installer_temp.nsi"], check=True)
        
        # Clean up
        os.remove("installer_temp.nsi")
        
        print("✓ Windows installer created: hf-model-downloader-installer.exe")
        return True
        
    except subprocess.CalledProcessError:
        print("⚠ NSIS not found. Skipping installer creation.")
        print("  To create Windows installer:")
        print("  1. Install NSIS: https://nsis.sourceforge.io/Download")
        print("  2. Add NSIS to PATH")
        print("  3. Run: makensis installer.nsi")
        return False
    except Exception as e:
        print(f"⚠ Failed to create installer: {e}")
        return False

if __name__ == "__main__":
    build_app() 