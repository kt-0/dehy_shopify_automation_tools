"""
image_tools.py — Resize and rename images within a directory tree.
"""

import os
from PIL import Image


def resize_image(image_path: str, output_path: str, width: int):
    with Image.open(image_path) as img:
        ratio = img.height / img.width
        new_height = int(width * ratio)
        img = img.resize((width, new_height), Image.LANCZOS)
        img.save(output_path, quality=90)


def rename_and_resize_images(root_dir: str, width: int = 720):
    for subdir, _, files in os.walk(root_dir):
        immediate_dir = os.path.basename(subdir)
        counter = 1
        for fn in files:
            if fn.lower().endswith(("png", "jpg", "jpeg", "gif", "bmp")):
                src = os.path.join(subdir, fn)
                new_name = f"{immediate_dir}_{counter}.jpg"
                dst = os.path.join(subdir, new_name)
                resize_image(src, dst, width)
                os.remove(src)
                counter += 1
