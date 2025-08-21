#!/usr/bin/env python3
"""
Optimized icon generator
Generates macOS (.icns) and Windows (.ico) icons from original PNG files

Usage:
  python icon_generator.py [options]

Options:
  --source SOURCE     Source image path (default: assets/icon.png)
  --output-dir DIR    Output directory (default: assets)
  --padding PERCENT   Padding percentage (default: 15)
  --radius PERCENT    Corner radius percentage (default: 22)
  --clear-cache       Clear macOS icon cache after generation
  --verbose           Show verbose output
  --help              Show help information
"""

import argparse
import os
import subprocess
import sys

from PIL import Image, ImageDraw


def ensure_directory(directory):
    """Ensure directory exists"""
    if not os.path.exists(directory):
        os.makedirs(directory)


def optimize_source_image(source_path, verbose=True):
    """Optimize source image ensuring it's square with transparent background"""
    try:
        img = Image.open(source_path)

        if img.mode != "RGBA":
            img = img.convert("RGBA")
            if verbose:
                print("Converted image to RGBA mode")

        width, height = img.size
        if width != height:
            size = min(width, height)
            left = (width - size) // 2
            top = (height - size) // 2
            right = left + size
            bottom = top + size
            img = img.crop((left, top, right, bottom))

            optimized_path = source_path.replace(".png", "_optimized.png")
            img.save(optimized_path)
            if verbose:
                print(f"Created optimized source image: {optimized_path}")
            return optimized_path, img

        return source_path, img

    except Exception as e:
        print(f"Error processing source image: {e}")
        sys.exit(1)


def create_square_icon_with_transparency(img, size, padding_percent=15):
    """Create square icon with transparent background and padding

    Args:
        img: Input image
        size: Output image size
        padding_percent: Padding percentage of image width

    Returns:
        Square icon with transparent background and padding
    """
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    content_size = int(size * (1 - padding_percent / 100))

    scaled_img = img.resize((content_size, content_size), Image.Resampling.LANCZOS)

    offset = (size - content_size) // 2

    result.paste(scaled_img, (offset, offset), scaled_img)

    return result


def create_rounded_square_icon(img, size, radius_percent=22, padding_percent=15):
    """Create square icon with rounded corners and transparent background

    Args:
        img: Input image
        size: Output image size
        radius_percent: Corner radius percentage of image width
        padding_percent: Padding percentage of image width

    Returns:
        Square icon with rounded corners and transparent background
    """
    padded_icon = create_square_icon_with_transparency(img, size, padding_percent)

    radius = int(size * radius_percent / 100)

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)

    draw.rounded_rectangle([(0, 0), (size, size)], radius, fill=255)

    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(padded_icon, (0, 0), mask)

    return result


def create_macos_iconset(
    source_img, iconset_path, radius_percent=22, padding_percent=15, verbose=True
):
    """Create macOS icon set with rounded corners and transparent background"""
    sizes = [16, 32, 64, 128, 256, 512, 1024]

    if verbose:
        print("Creating macOS icon set...")

    for size in sizes:
        icon_path = os.path.join(iconset_path, f"icon_{size}x{size}.png")
        rounded_icon = create_rounded_square_icon(
            source_img, size, radius_percent, padding_percent
        )
        rounded_icon.save(icon_path, format="PNG")

        if size <= 512:
            icon_path = os.path.join(iconset_path, f"icon_{size}x{size}@2x.png")
            rounded_icon = create_rounded_square_icon(
                source_img, size * 2, radius_percent, padding_percent
            )
            rounded_icon.save(icon_path, format="PNG")

    if verbose:
        print(f"Created macOS icon set: {iconset_path}")


def create_windows_ico(source_img, output_path, padding_percent=10, verbose=True):
    """Create Windows ICO file"""
    sizes = [16, 24, 32, 48, 64, 128, 256]

    if verbose:
        print("Creating Windows icon...")

    img_list = []
    for size in sizes:
        padded_icon = create_square_icon_with_transparency(
            source_img, size, padding_percent
        )
        img_list.append(padded_icon)

    img_list[0].save(
        output_path,
        format="ICO",
        sizes=[(img.width, img.height) for img in img_list],
        append_images=img_list[1:],
    )

    if verbose:
        print(f"Created Windows icon: {output_path}")


def create_favicon(source_img, output_path, padding_percent=10, verbose=True):
    """Create website favicon.ico"""
    sizes = [16, 32, 48, 64]

    if verbose:
        print("Creating Favicon...")

    img_list = []
    for size in sizes:
        padded_icon = create_square_icon_with_transparency(
            source_img, size, padding_percent
        )
        img_list.append(padded_icon)

    img_list[0].save(
        output_path,
        format="ICO",
        sizes=[(img.width, img.height) for img in img_list],
        append_images=img_list[1:],
    )

    if verbose:
        print(f"Created Favicon: {output_path}")


def convert_iconset_to_icns(iconset_path, output_path, verbose=True):
    """Convert icon set to ICNS file"""
    try:
        if os.system("which iconutil > /dev/null") != 0:
            print("Warning: iconutil command not available, cannot create .icns file")
            print("This may be because you are not running this script on macOS")
            return False

        subprocess.run(
            ["iconutil", "-c", "icns", iconset_path, "-o", output_path], check=True
        )
        if verbose:
            print(f"Created macOS icon: {output_path}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error converting to ICNS: {e}")
        return False


def clear_icon_cache(verbose=True):
    """Clear macOS icon cache"""
    try:
        if sys.platform == "darwin":
            if verbose:
                print("Clearing macOS icon cache...")
            subprocess.run(
                ["sudo", "rm", "-rfv", "/Library/Caches/com.apple.iconservices.store"],
                check=False,
            )
            subprocess.run(
                [
                    "sudo",
                    "find",
                    "/private/var/folders",
                    "-name",
                    "com.apple.dock.iconcache",
                    "-delete",
                ],
                check=False,
            )
            subprocess.run(
                [
                    "sudo",
                    "find",
                    "/private/var/folders",
                    "-name",
                    "com.apple.iconservices",
                    "-delete",
                ],
                check=False,
            )

            subprocess.run(["killall", "Dock"], check=False)
            subprocess.run(["killall", "Finder"], check=False)

            if verbose:
                print("Icon cache cleared, please restart applications to see changes")
    except Exception as e:
        print(f"Error clearing icon cache: {e}")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Generate macOS (.icns) and Windows (.ico) icons from original PNG files"
    )

    parser.add_argument(
        "--source", default="assets/icon.png", help="Source image path (default: assets/icon.png)"
    )

    parser.add_argument(
        "--output-dir", default="assets", help="Output directory (default: assets)"
    )

    parser.add_argument(
        "--padding", type=float, default=15, help="Padding percentage (default: 15)"
    )

    parser.add_argument(
        "--radius", type=float, default=22, help="Corner radius percentage (default: 22)"
    )

    parser.add_argument(
        "--clear-cache", action="store_true", help="Clear macOS icon cache after generation"
    )

    parser.add_argument("--verbose", action="store_true", help="Show verbose output")

    return parser.parse_args()


def main():
    args = parse_arguments()

    source_path = args.source

    if not os.path.exists(source_path):
        print(f"Error: Source image {source_path} does not exist!")
        sys.exit(1)

    output_dir = args.output_dir
    ensure_directory(output_dir)

    optimized_path, source_img = optimize_source_image(
        source_path, verbose=args.verbose
    )

    iconset_path = os.path.join(output_dir, "icon.iconset")
    ensure_directory(iconset_path)
    create_macos_iconset(
        source_img,
        iconset_path,
        radius_percent=args.radius,
        padding_percent=args.padding,
        verbose=args.verbose,
    )

    icns_path = os.path.join(output_dir, "icon.icns")
    convert_iconset_to_icns(iconset_path, icns_path, verbose=args.verbose)

    ico_path = os.path.join(output_dir, "icon.ico")
    create_windows_ico(
        source_img, ico_path, padding_percent=args.padding, verbose=args.verbose
    )

    favicon_path = os.path.join(output_dir, "favicon.ico")
    create_favicon(
        source_img, favicon_path, padding_percent=args.padding, verbose=args.verbose
    )

    if args.verbose:
        print("\nIcon generation completed!")
        print(f"- macOS icon: {icns_path}")
        print(f"- Windows icon: {ico_path}")
        print(f"- Favicon: {favicon_path}")
        print(f"- Icon set directory: {iconset_path}")

    if args.clear_cache:
        clear_icon_cache(verbose=args.verbose)


if __name__ == "__main__":
    main()
