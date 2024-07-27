#!/usr/bin/env python3
import array
import fcntl
import sys
import termios
import os
import subprocess
from math import ceil

def get_window_size():
    buf = array.array('H', [0, 0, 0, 0])
    fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ, buf)
    rows, cols, screen_width, screen_height = buf
    return rows, cols, screen_width, screen_height

def calculate_grid_dimensions(num_images, term_cols, term_rows):
    max_cols = min(3, num_images)  # Adjust max columns if needed
    cols = min(num_images, max_cols)
    rows = ceil(num_images / cols)
    return rows, cols

def resize_image(image_path, output_path, width, height):
    command = ['magick', image_path, '-resize', f'{width}x{height}!', output_path]
    subprocess.run(command, check=True)

def render_image(image_path, term_cols, term_rows, x, y):
    command = [
        'kitty',
        '+kitten', 'icat',
        '--place', f'{term_cols}x{term_rows}@{x}x{y}',
        '--transfer-mode', 'stream',
        '--', image_path
    ]
    subprocess.run(command, check=True)


def print_grid_with_images(rows, cols, image_paths, term_cols, term_rows, offset_y):
    num_images = len(image_paths)
    cell_width = term_cols // cols
    cell_height = (term_rows - offset_y) // rows

    print(f"Grid layout: {rows} rows, {cols} columns, cell size: {cell_width}x{cell_height}")

    temp_dir = '/tmp/resized_images'
    os.makedirs(temp_dir, exist_ok=True)

    for row in range(rows):
        for col in range(cols):
            index = row * cols + col
            if index >= num_images:
                break
            image_path = image_paths[index]
            # resized_image_path = os.path.join(temp_dir, f'resized_{index}.png')
            # resize_image(image_path, resized_image_path, cell_width * 10, cell_height * 10)  # Adjusted resize
            render_image(image_path, cell_width, cell_height, col * cell_width, row * cell_height + offset_y)

def main():
    term_rows, term_cols, term_width, term_height = get_window_size()
    print(f"Window size: {term_rows} rows, {term_cols} columns, screen width: {term_width}, screen height: {term_height}")

    image_dir = "."
    image_paths = [os.path.join(image_dir, img) for img in os.listdir(image_dir) if img.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]

    if not image_paths:
        print("No images found in the specified directory.")
        sys.exit(1)

    print(f"Found images: {image_paths}")
    rows, cols = calculate_grid_dimensions(len(image_paths), term_cols, term_rows)
    offset_y = 2  # Start rendering images from the row below the command prompt
    print_grid_with_images(rows, cols, image_paths, term_cols, term_rows, offset_y)

if __name__ == '__main__':
    main()
