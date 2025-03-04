#!/usr/bin/env python3
"""
优化的图标生成器
从原始 PNG 文件生成 macOS (.icns) 和 Windows (.ico) 图标

用法:
  python icon_generator.py [选项]

选项:
  --source SOURCE     源图像路径 (默认: assets/icon.png)
  --output-dir DIR    输出目录 (默认: assets)
  --padding PERCENT   内边距百分比 (默认: 15)
  --radius PERCENT    圆角半分比 (默认: 22)
  --clear-cache       生成后清除 macOS 图标缓存
  --verbose           显示详细输出
  --help              显示帮助信息
"""

import os
import sys
import subprocess
import argparse
from PIL import Image, ImageOps, ImageDraw

def ensure_directory(directory):
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def optimize_source_image(source_path, verbose=True):
    """优化源图像，确保它是正方形且有透明背景"""
    try:
        img = Image.open(source_path)
        
        # 确保图像是 RGBA 模式（带透明度）
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
            if verbose:
                print(f"已将图像转换为 RGBA 模式")
        
        # 确保图像是正方形
        width, height = img.size
        if width != height:
            # 裁剪为正方形
            size = min(width, height)
            left = (width - size) // 2
            top = (height - size) // 2
            right = left + size
            bottom = top + size
            img = img.crop((left, top, right, bottom))
            
            # 保存优化后的源图像
            optimized_path = source_path.replace('.png', '_optimized.png')
            img.save(optimized_path)
            if verbose:
                print(f"已创建优化的源图像: {optimized_path}")
            return optimized_path, img
        
        return source_path, img
    
    except Exception as e:
        print(f"处理源图像时出错: {e}")
        sys.exit(1)

def create_square_icon_with_transparency(img, size, padding_percent=15):
    """创建带有透明背景和内边距的正方形图标
    
    Args:
        img: 输入图像
        size: 输出图像的大小
        padding_percent: 内边距占图像宽度的百分比
    
    Returns:
        带有透明背景和内边距的正方形图标
    """
    # 创建一个新的透明图像
    result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    
    # 计算内容大小
    content_size = int(size * (1 - padding_percent / 100))
    
    # 缩放原始图像
    scaled_img = img.resize((content_size, content_size), Image.Resampling.LANCZOS)
    
    # 计算偏移量，使内容居中
    offset = (size - content_size) // 2
    
    # 将缩放后的图像粘贴到中心位置
    result.paste(scaled_img, (offset, offset), scaled_img)
    
    return result

def create_rounded_square_icon(img, size, radius_percent=22, padding_percent=15):
    """创建带有圆角和透明背景的正方形图标
    
    Args:
        img: 输入图像
        size: 输出图像的大小
        radius_percent: 圆角半径占图像宽度的百分比
        padding_percent: 内边距占图像宽度的百分比
    
    Returns:
        带有圆角和透明背景的正方形图标
    """
    # 创建带有内边距的图标
    padded_icon = create_square_icon_with_transparency(img, size, padding_percent)
    
    # 计算圆角半径
    radius = int(size * radius_percent / 100)
    
    # 创建一个带有圆角的蒙版
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    
    # 绘制圆角矩形
    draw.rounded_rectangle([(0, 0), (size, size)], radius, fill=255)
    
    # 应用蒙版
    result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    result.paste(padded_icon, (0, 0), mask)
    
    return result

def create_macos_iconset(source_img, iconset_path, radius_percent=22, padding_percent=15, verbose=True):
    """创建 macOS 图标集，带圆角和透明背景"""
    # macOS 图标尺寸
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    
    if verbose:
        print(f"正在创建 macOS 图标集...")
    
    # 生成不同尺寸的图标
    for size in sizes:
        # 标准分辨率
        icon_path = os.path.join(iconset_path, f"icon_{size}x{size}.png")
        rounded_icon = create_rounded_square_icon(source_img, size, radius_percent, padding_percent)
        rounded_icon.save(icon_path, format='PNG')
        
        # 高分辨率 (2x) 版本
        if size <= 512:  # 不创建 2048px 版本
            icon_path = os.path.join(iconset_path, f"icon_{size}x{size}@2x.png")
            rounded_icon = create_rounded_square_icon(source_img, size * 2, radius_percent, padding_percent)
            rounded_icon.save(icon_path, format='PNG')
    
    if verbose:
        print(f"已创建 macOS 图标集: {iconset_path}")

def create_windows_ico(source_img, output_path, padding_percent=10, verbose=True):
    """创建 Windows ICO 文件"""
    # Windows 图标尺寸
    sizes = [16, 24, 32, 48, 64, 128, 256]
    
    if verbose:
        print(f"正在创建 Windows 图标...")
    
    # 创建不同尺寸的图像列表
    img_list = []
    for size in sizes:
        padded_icon = create_square_icon_with_transparency(source_img, size, padding_percent)
        img_list.append(padded_icon)
    
    # 保存为 ICO 文件
    img_list[0].save(
        output_path, 
        format='ICO', 
        sizes=[(img.width, img.height) for img in img_list],
        append_images=img_list[1:]
    )
    
    if verbose:
        print(f"已创建 Windows 图标: {output_path}")

def create_favicon(source_img, output_path, padding_percent=10, verbose=True):
    """创建网站 favicon.ico"""
    # Favicon 尺寸
    sizes = [16, 32, 48, 64]
    
    if verbose:
        print(f"正在创建 Favicon...")
    
    # 创建不同尺寸的图像列表
    img_list = []
    for size in sizes:
        padded_icon = create_square_icon_with_transparency(source_img, size, padding_percent)
        img_list.append(padded_icon)
    
    # 保存为 ICO 文件
    img_list[0].save(
        output_path, 
        format='ICO', 
        sizes=[(img.width, img.height) for img in img_list],
        append_images=img_list[1:]
    )
    
    if verbose:
        print(f"已创建 Favicon: {output_path}")

def convert_iconset_to_icns(iconset_path, output_path, verbose=True):
    """将图标集转换为 ICNS 文件"""
    try:
        # 检查 iconutil 命令是否可用（仅在 macOS 上可用）
        if os.system('which iconutil > /dev/null') != 0:
            print("警告: iconutil 命令不可用，无法创建 .icns 文件")
            print("这可能是因为您不在 macOS 系统上运行此脚本")
            return False
        
        # 使用 iconutil 转换
        subprocess.run(['iconutil', '-c', 'icns', iconset_path, '-o', output_path], check=True)
        if verbose:
            print(f"已创建 macOS 图标: {output_path}")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"转换为 ICNS 时出错: {e}")
        return False

def clear_icon_cache(verbose=True):
    """清除 macOS 图标缓存"""
    try:
        if sys.platform == 'darwin':  # 仅在 macOS 上执行
            if verbose:
                print("正在清除 macOS 图标缓存...")
            # 清除图标缓存
            subprocess.run(['sudo', 'rm', '-rfv', '/Library/Caches/com.apple.iconservices.store'], check=False)
            subprocess.run(['sudo', 'find', '/private/var/folders', '-name', 'com.apple.dock.iconcache', '-delete'], check=False)
            subprocess.run(['sudo', 'find', '/private/var/folders', '-name', 'com.apple.iconservices', '-delete'], check=False)
            
            # 重启相关服务
            subprocess.run(['killall', 'Dock'], check=False)
            subprocess.run(['killall', 'Finder'], check=False)
            
            if verbose:
                print("图标缓存已清除，请重新启动应用以查看更改")
    except Exception as e:
        print(f"清除图标缓存时出错: {e}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='从原始 PNG 文件生成 macOS (.icns) 和 Windows (.ico) 图标')
    
    parser.add_argument('--source', default='assets/icon.png',
                        help='源图像路径 (默认: assets/icon.png)')
    
    parser.add_argument('--output-dir', default='assets',
                        help='输出目录 (默认: assets)')
    
    parser.add_argument('--padding', type=float, default=15,
                        help='内边距百分比 (默认: 15)')
    
    parser.add_argument('--radius', type=float, default=22,
                        help='圆角半径百分比 (默认: 22)')
    
    parser.add_argument('--clear-cache', action='store_true',
                        help='生成后清除 macOS 图标缓存')
    
    parser.add_argument('--verbose', action='store_true',
                        help='显示详细输出')
    
    return parser.parse_args()

def main():
    # 解析命令行参数
    args = parse_arguments()
    
    # 源图像路径
    source_path = args.source
    
    # 检查源图像是否存在
    if not os.path.exists(source_path):
        print(f"错误: 源图像 {source_path} 不存在!")
        sys.exit(1)
    
    # 输出目录
    output_dir = args.output_dir
    ensure_directory(output_dir)
    
    # 优化源图像
    optimized_path, source_img = optimize_source_image(source_path, verbose=args.verbose)
    
    # 创建 macOS 图标
    iconset_path = os.path.join(output_dir, 'icon.iconset')
    ensure_directory(iconset_path)
    create_macos_iconset(source_img, iconset_path, 
                         radius_percent=args.radius, 
                         padding_percent=args.padding, 
                         verbose=args.verbose)
    
    # 转换为 ICNS 文件
    icns_path = os.path.join(output_dir, 'icon.icns')
    convert_iconset_to_icns(iconset_path, icns_path, verbose=args.verbose)
    
    # 创建 Windows 图标
    ico_path = os.path.join(output_dir, 'icon.ico')
    create_windows_ico(source_img, ico_path, 
                       padding_percent=args.padding, 
                       verbose=args.verbose)
    
    # 创建 Favicon
    favicon_path = os.path.join(output_dir, 'favicon.ico')
    create_favicon(source_img, favicon_path, 
                   padding_percent=args.padding, 
                   verbose=args.verbose)
    
    if args.verbose:
        print("\n图标生成完成!")
        print(f"- macOS 图标: {icns_path}")
        print(f"- Windows 图标: {ico_path}")
        print(f"- Favicon: {favicon_path}")
        print(f"- 图标集目录: {iconset_path}")
    
    # 清除图标缓存（如果指定）
    if args.clear_cache:
        clear_icon_cache(verbose=args.verbose)

if __name__ == '__main__':
    main() 