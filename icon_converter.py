#!/usr/bin/env python3
import os
from PIL import Image
import subprocess

def create_iconset(png_path):
    """Convert PNG to ICNS for macOS"""
    # Create iconset directory if it doesn't exist
    iconset_path = 'assets/icon.iconset'
    if not os.path.exists(iconset_path):
        os.makedirs(iconset_path)

    # Define the sizes needed for ICNS
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    img = Image.open(png_path)

    # Generate different sizes
    for size in sizes:
        # Normal resolution
        icon_path = f"{iconset_path}/icon_{size}x{size}.png"
        img_copy = img.copy()
        img_copy.thumbnail((size, size), Image.Resampling.LANCZOS)
        img_copy.save(icon_path)

        # High resolution (2x) version
        if size <= 512:  # Don't create 2048px version
            icon_path = f"{iconset_path}/icon_{size}x{size}@2x.png"
            img_copy = img.copy()
            img_copy.thumbnail((size * 2, size * 2), Image.Resampling.LANCZOS)
            img_copy.save(icon_path)

    # Convert iconset to icns using macOS iconutil
    subprocess.run(['iconutil', '-c', 'icns', iconset_path])

def create_ico(png_path):
    """Convert PNG to ICO for Windows"""
    img = Image.open(png_path)
    # ICO format typically includes multiple sizes
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_path = 'assets/icon.ico'
    
    # Create a list to store different size versions
    img_list = []
    for size in sizes:
        img_copy = img.copy()
        img_copy.thumbnail(size, Image.Resampling.LANCZOS)
        img_list.append(img_copy)
    
    # Save as ICO with multiple sizes
    img_list[0].save(ico_path, format='ICO', sizes=[(img.width, img.height) for img in img_list], append_images=img_list[1:])

def main():
    png_path = 'assets/icon.png'
    if not os.path.exists(png_path):
        print(f"Error: {png_path} not found!")
        return
    
    print("Converting PNG to ICNS...")
    create_iconset(png_path)
    print("Converting PNG to ICO...")
    create_ico(png_path)
    print("Conversion completed!")

if __name__ == '__main__':
    main() 