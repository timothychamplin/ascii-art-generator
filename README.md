# ASCII Art Generator

A Python image-to-ASCII art converter that transforms images into text-based artwork directly in the terminal.

## Features

- Clean ASCII rendering
- Detailed ASCII rendering
- High-detail Unicode Braille mode
- Adjustable output width
- Adjustable brightness threshold for Unicode rendering
- Automatic image orientation correction
- Contrast enhancement
- Image sharpening
- Save generated artwork as a `.txt` file
- Supports image paths using `~`, such as `~/Desktop/photo.jpg`

## Rendering Modes

### 1. Clean ASCII

Uses a shorter character set to create a cleaner and more readable result.

Best for:
- portraits
- simple images
- strong silhouettes
- images where readability matters more than maximum texture

### 2. Detailed ASCII

Uses a larger range of characters to represent more brightness levels and texture.

Best for:
- detailed photographs
- landscapes
- textured images
- images with subtle lighting differences

### 3. High Detail Unicode

Uses Unicode Braille characters, where each character can represent a 2×4 grid of dots.

This provides significantly higher effective resolution than standard ASCII and can preserve more fine detail.

## Example Workflow

```text
==================================================
           ASCII ART GENERATOR
==================================================

Rendering Styles:
1. Clean ASCII
2. Detailed ASCII
3. High Detail Unicode

Choose style (1, 2, or 3) [default: 1]: 2

Enter the path to an image: ~/Desktop/photo.jpg

ASCII width [default: 190]: 200

Generating...