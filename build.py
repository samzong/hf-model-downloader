import os
import platform
import subprocess
import sys
import shutil

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
    
    # 注意：图标生成现在是 Makefile 中的独立步骤
    # 请先运行 `make icons` 生成图标，然后再运行此脚本
    # 或者直接使用 `make build` 命令，它会自动依赖 icons 目标
    
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
        print(f"警告: 图标文件未找到: {icon_path}")
        print(f"请确保已运行 `make icons` 生成图标文件，或将适当的图标文件放置在 assets 目录中:")
        print("- macOS: assets/icon.icns")
        print("- Windows: assets/icon.ico")
        print("您可以继续构建，但应用将没有自定义图标")
    
    # Add main script
    cmd.append("main.py")
    
    try:
        print(f"构建 {output_name} 用于 {system} ({arch})...")
        print(f"命令: {' '.join(cmd)}")
        
        # Run PyInstaller
        subprocess.run(cmd, check=True)
        
        # 注意：图标修复现在是 Makefile 中的独立步骤 (make fix-icons)
        # 此处不再自动修复图标问题，而是依赖 Makefile 中的步骤
        
        # Print build information
        output_path = os.path.join("dist", output_name)
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print("\n构建摘要:")
            print(f"- 输出: dist/{output_name}")
            print(f"- 大小: {size_mb:.2f} MB")
            print(f"- 系统: {system}")
            print(f"- 架构: {arch}")
            print(f"- Python 版本: {platform.python_version()}")
            print("\n提示: 如需修复图标问题，请运行 `make fix-icons`")
        
    except subprocess.CalledProcessError as e:
        print(f"错误: 构建失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_app() 