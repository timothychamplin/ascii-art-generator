from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageFont
import os
import shutil
import subprocess
import tempfile
import re
import html
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None


# ---------------------------------------------------------
# CHARACTER SETS
# ---------------------------------------------------------

# Darkest -> brightest
CLEAN_CHARS = " .,:;irsXA253hMHGS#9B&@"

DETAILED_CHARS = (
    " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B$@"
)


VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".avi",
    ".mkv",
    ".webm"
}


# ---------------------------------------------------------
# COLOR HELPERS
# ---------------------------------------------------------

def color_text(text, r, g, b):
    """
    Wraps text in a 24-bit ANSI RGB foreground color.
    """
    return f"\033[38;2;{r};{g};{b}m{text}\033[0m"


def strip_ansi(text):
    """
    Removes ANSI color codes before saving to a text file.
    """
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_pattern.sub("", text)


def ansi_to_html(text):
    """
    Converts the ANSI RGB color codes used by this program into HTML spans.
    """
    rgb_pattern = re.compile(
        r"\x1b\[38;2;(\d+);(\d+);(\d+)m(.*?)\x1b\[0m"
    )

    result = []
    last_end = 0

    for match in rgb_pattern.finditer(text):
        # Add any uncolored text before this match.
        result.append(html.escape(text[last_end:match.start()]))

        r, g, b = match.group(1), match.group(2), match.group(3)
        content = html.escape(match.group(4))

        result.append(
            f'<span style="color: rgb({r}, {g}, {b});">{content}</span>'
        )

        last_end = match.end()

    result.append(html.escape(text[last_end:]))

    return "".join(result)


# ---------------------------------------------------------
# IMAGE PREPARATION
# ---------------------------------------------------------

def prepare_source_image(image_path):
    """
    Opens an image, corrects its orientation, and converts it to RGB.
    """

    image_path = os.path.expanduser(image_path)

    image = Image.open(image_path)

    # Correct phone/camera orientation
    image = ImageOps.exif_transpose(image)

    return image.convert("RGB")


def prepare_image(image_path):
    """
    Opens and prepares an image for brightness-based rendering.
    """

    image = prepare_source_image(image_path)

    # Convert to grayscale
    image = image.convert("L")

    # Improve contrast
    image = ImageOps.autocontrast(
        image,
        cutoff=1
    )

    # Sharpen important details
    image = image.filter(
        ImageFilter.UnsharpMask(
            radius=1.5,
            percent=130,
            threshold=4
        )
    )

    return image


# ---------------------------------------------------------
# STANDARD ASCII
# ---------------------------------------------------------

def image_to_ascii(
    image_path,
    width=190,
    style="clean",
    use_color=False
):
    """
    Converts an image into clean or detailed ASCII.

    Character choice is based on grayscale brightness.
    If use_color is True, each character is colored using
    the corresponding RGB pixel from the original image.
    """

    image = prepare_image(image_path)

    if style == "detailed":
        ascii_chars = DETAILED_CHARS
    else:
        ascii_chars = CLEAN_CHARS

    aspect_ratio = image.height / image.width

    # Compensate for terminal character proportions
    character_ratio = 0.45

    height = max(
        1,
        int(width * aspect_ratio * character_ratio)
    )

    image = image.resize(
        (width, height),
        Image.Resampling.LANCZOS
    )

    color_image = None

    if use_color:
        color_image = prepare_source_image(image_path)
        color_image = color_image.resize(
            (width, height),
            Image.Resampling.LANCZOS
        )

    rows = []

    for y in range(height):

        row = []

        for x in range(width):

            pixel = image.getpixel((x, y))

            # Leave nearly-black areas blank
            if pixel < 10:
                row.append(" ")
                continue

            index = int(
                pixel / 255 * (len(ascii_chars) - 1)
            )

            char = ascii_chars[index]

            if use_color:
                r, g, b = color_image.getpixel((x, y))
                char = color_text(char, r, g, b)

            row.append(char)

        rows.append("".join(row))

    return "\n".join(rows)


# ---------------------------------------------------------
# HIGH DETAIL UNICODE / BRAILLE
# ---------------------------------------------------------

def braille_character(block, threshold):
    """
    Converts a 2x4 pixel block into one Unicode Braille
    character.

    Braille dot layout:

        1 4
        2 5
        3 6
        7 8
    """

    value = 0

    braille_bits = [
        [0, 3],
        [1, 4],
        [2, 5],
        [6, 7]
    ]

    for y in range(4):

        for x in range(2):

            if block[y][x] >= threshold:

                value |= (
                    1 << braille_bits[y][x]
                )

    return chr(
        0x2800 + value
    )


def image_to_braille(
    image_path,
    width=100,
    threshold=120,
    use_color=False
):
    """
    Converts an image into high-detail Unicode Braille art.

    Each Braille character represents a 2x4 grid.
    If use_color is True, each Braille character uses the
    average RGB color of its corresponding 2x4 pixel block.
    """

    image = prepare_image(image_path)

    aspect_ratio = (
        image.height / image.width
    )

    # 2 horizontal pixels per Braille character
    pixel_width = width * 2

    output_height = max(
        1,
        int(
            width
            * aspect_ratio
            * 0.5
        )
    )

    # 4 vertical pixels per Braille character
    pixel_height = output_height * 4

    image = image.resize(
        (pixel_width, pixel_height),
        Image.Resampling.LANCZOS
    )

    color_image = None

    if use_color:
        color_image = prepare_source_image(image_path)
        color_image = color_image.resize(
            (pixel_width, pixel_height),
            Image.Resampling.LANCZOS
        )

    pixels = image.load()

    rows = []

    for y in range(
        0,
        pixel_height,
        4
    ):

        row = []

        for x in range(
            0,
            pixel_width,
            2
        ):

            block = [
                [
                    pixels[x, y],
                    pixels[x + 1, y]
                ],
                [
                    pixels[x, y + 1],
                    pixels[x + 1, y + 1]
                ],
                [
                    pixels[x, y + 2],
                    pixels[x + 1, y + 2]
                ],
                [
                    pixels[x, y + 3],
                    pixels[x + 1, y + 3]
                ]
            ]

            char = braille_character(
                block,
                threshold
            )

            if use_color and char != chr(0x2800):

                rgb_values = []

                for block_y in range(4):
                    for block_x in range(2):
                        rgb_values.append(
                            color_image.getpixel(
                                (x + block_x, y + block_y)
                            )
                        )

                r = sum(rgb[0] for rgb in rgb_values) // len(rgb_values)
                g = sum(rgb[1] for rgb in rgb_values) // len(rgb_values)
                b = sum(rgb[2] for rgb in rgb_values) // len(rgb_values)

                char = color_text(char, r, g, b)

            row.append(char)

        rows.append(
            "".join(row)
        )

    return "\n".join(rows)



# ---------------------------------------------------------
# VIDEO SUPPORT
# ---------------------------------------------------------

def is_video_file(file_path):
    """
    Returns True when the input path has a common video extension.
    """

    extension = os.path.splitext(file_path)[1].lower()
    return extension in VIDEO_EXTENSIONS


def get_monospace_font(font_size=14):
    """
    Tries several common monospace fonts and falls back to Pillow's
    built-in font.
    """

    font_paths = [
        "/System/Library/Fonts/Menlo.ttc",
        "/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf"
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            return ImageFont.truetype(
                font_path,
                font_size
            )

    return ImageFont.load_default()


def prepare_video_frame(frame_rgb):
    """
    Applies the same grayscale enhancement used for still images
    to one RGB video frame.
    """

    image = Image.fromarray(frame_rgb).convert("RGB")

    gray = image.convert("L")

    gray = ImageOps.autocontrast(
        gray,
        cutoff=1
    )

    gray = gray.filter(
        ImageFilter.UnsharpMask(
            radius=1.5,
            percent=130,
            threshold=4
        )
    )

    return image, gray


def frame_to_ascii_grid(
    frame_rgb,
    width,
    style,
    use_color
):
    """
    Converts one RGB video frame into a grid of ASCII characters.
    """

    color_image, gray_image = prepare_video_frame(
        frame_rgb
    )

    if style == "detailed":
        ascii_chars = DETAILED_CHARS
    else:
        ascii_chars = CLEAN_CHARS

    aspect_ratio = (
        gray_image.height / gray_image.width
    )

    character_ratio = 0.45

    height = max(
        1,
        int(
            width
            * aspect_ratio
            * character_ratio
        )
    )

    gray_image = gray_image.resize(
        (width, height),
        Image.Resampling.LANCZOS
    )

    if use_color:
        color_image = color_image.resize(
            (width, height),
            Image.Resampling.LANCZOS
        )

    rows = []
    color_rows = []

    for y in range(height):

        row = []
        color_row = []

        for x in range(width):

            brightness = gray_image.getpixel(
                (x, y)
            )

            if brightness < 10:
                char = " "
            else:
                index = int(
                    brightness
                    / 255
                    * (len(ascii_chars) - 1)
                )

                char = ascii_chars[index]

            row.append(char)

            if use_color:
                color_row.append(
                    color_image.getpixel(
                        (x, y)
                    )
                )

        rows.append(row)

        if use_color:
            color_rows.append(color_row)

    return rows, color_rows


def frame_to_braille_grid(
    frame_rgb,
    width,
    threshold,
    use_color
):
    """
    Converts one RGB video frame into a grid of Unicode Braille
    characters.
    """

    color_image, gray_image = prepare_video_frame(
        frame_rgb
    )

    aspect_ratio = (
        gray_image.height / gray_image.width
    )

    pixel_width = width * 2

    output_height = max(
        1,
        int(
            width
            * aspect_ratio
            * 0.5
        )
    )

    pixel_height = output_height * 4

    gray_image = gray_image.resize(
        (pixel_width, pixel_height),
        Image.Resampling.LANCZOS
    )

    if use_color:
        color_image = color_image.resize(
            (pixel_width, pixel_height),
            Image.Resampling.LANCZOS
        )

    pixels = gray_image.load()

    rows = []
    color_rows = []

    for y in range(
        0,
        pixel_height,
        4
    ):

        row = []
        color_row = []

        for x in range(
            0,
            pixel_width,
            2
        ):

            block = [
                [
                    pixels[x, y],
                    pixels[x + 1, y]
                ],
                [
                    pixels[x, y + 1],
                    pixels[x + 1, y + 1]
                ],
                [
                    pixels[x, y + 2],
                    pixels[x + 1, y + 2]
                ],
                [
                    pixels[x, y + 3],
                    pixels[x + 1, y + 3]
                ]
            ]

            char = braille_character(
                block,
                threshold
            )

            row.append(char)

            if use_color:

                rgb_values = []

                for block_y in range(4):

                    for block_x in range(2):

                        rgb_values.append(
                            color_image.getpixel(
                                (
                                    x + block_x,
                                    y + block_y
                                )
                            )
                        )

                r = (
                    sum(
                        rgb[0]
                        for rgb in rgb_values
                    )
                    // len(rgb_values)
                )

                g = (
                    sum(
                        rgb[1]
                        for rgb in rgb_values
                    )
                    // len(rgb_values)
                )

                b = (
                    sum(
                        rgb[2]
                        for rgb in rgb_values
                    )
                    // len(rgb_values)
                )

                color_row.append(
                    (r, g, b)
                )

        rows.append(row)

        if use_color:
            color_rows.append(color_row)

    return rows, color_rows


def render_character_grid(
    rows,
    color_rows,
    use_color,
    font_size=14,
    target_size=None
):
    """
    Renders a character grid to an RGB image with a black background.

    If target_size is provided, the ASCII art is resized to exactly match
    that canvas size so the output fills the full source-video frame.
    """

    font = get_monospace_font(
        font_size
    )

    probe = Image.new(
        "RGB",
        (100, 100),
        "black"
    )

    probe_draw = ImageDraw.Draw(
        probe
    )

    bbox = probe_draw.textbbox(
        (0, 0),
        "M",
        font=font
    )

    cell_width = max(
        1,
        bbox[2] - bbox[0]
    )

    cell_height = max(
        1,
        bbox[3] - bbox[1] + 2
    )

    columns = max(
        len(row)
        for row in rows
    )

    ascii_width = max(
        1,
        columns * cell_width
    )

    ascii_height = max(
        1,
        len(rows) * cell_height
    )

    ascii_canvas = Image.new(
        "RGB",
        (
            ascii_width,
            ascii_height
        ),
        "black"
    )

    draw = ImageDraw.Draw(
        ascii_canvas
    )

    if use_color:

        for y, row in enumerate(rows):

            for x, char in enumerate(row):

                if char == " ":
                    continue

                color = color_rows[y][x]

                draw.text(
                    (
                        x * cell_width,
                        y * cell_height
                    ),
                    char,
                    font=font,
                    fill=color
                )

    else:

        for y, row in enumerate(rows):

            draw.text(
                (
                    0,
                    y * cell_height
                ),
                "".join(row),
                font=font,
                fill="white"
            )

    if target_size is None:
        return ascii_canvas

    target_width, target_height = target_size

    # Resize the rendered ASCII frame to the exact source-video
    # dimensions. This removes the letterboxing caused by fitting
    # the ASCII canvas proportionally inside the source frame.
    final_canvas = ascii_canvas.resize(
        (
            target_width,
            target_height
        ),
        Image.Resampling.LANCZOS
    )

    return final_canvas


def video_to_ascii_video(
    video_path,
    output_path,
    width=120,
    style="clean",
    threshold=120,
    use_color=False,
    font_size=14
):
    """
    Converts a video to ASCII frame by frame and saves it as MP4.

    The original frame rate is preserved. After the ASCII frames are
    rendered, FFmpeg copies the original video's audio into the final
    output when an audio track exists.
    """

    if cv2 is None:
        raise RuntimeError(
            "Video support requires OpenCV. "
            "Install it with: "
            "python -m pip install opencv-python"
        )

    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "Audio preservation requires FFmpeg. "
            "On macOS, install it with: brew install ffmpeg"
        )

    video_path = os.path.expanduser(
        video_path
    )

    if not os.path.exists(video_path):
        raise FileNotFoundError(
            "Video file not found."
        )

    capture = cv2.VideoCapture(
        video_path
    )

    if not capture.isOpened():
        raise FileNotFoundError(
            "Could not open the video file."
        )

    fps = capture.get(
        cv2.CAP_PROP_FPS
    )

    if fps <= 0:
        fps = 30.0

    source_width = int(
        capture.get(
            cv2.CAP_PROP_FRAME_WIDTH
        )
    )

    source_height = int(
        capture.get(
            cv2.CAP_PROP_FRAME_HEIGHT
        )
    )

    if source_width <= 0 or source_height <= 0:
        raise RuntimeError(
            "Could not determine the source video dimensions."
        )

    total_frames = int(
        capture.get(
            cv2.CAP_PROP_FRAME_COUNT
        )
    )

    if not output_path.lower().endswith(
        ".mp4"
    ):
        output_path += ".mp4"

    output_path = os.path.abspath(
        os.path.expanduser(output_path)
    )

    writer = None
    frame_number = 0

    # Render the ASCII frames to a temporary silent MP4 first.
    temp_file = tempfile.NamedTemporaryFile(
        suffix=".mp4",
        delete=False
    )

    silent_video_path = temp_file.name
    temp_file.close()

    try:

        while True:

            success, frame_bgr = capture.read()

            if not success:
                break

            frame_rgb = cv2.cvtColor(
                frame_bgr,
                cv2.COLOR_BGR2RGB
            )

            if style == "unicode":

                rows, color_rows = (
                    frame_to_braille_grid(
                        frame_rgb=frame_rgb,
                        width=width,
                        threshold=threshold,
                        use_color=use_color
                    )
                )

            else:

                rows, color_rows = (
                    frame_to_ascii_grid(
                        frame_rgb=frame_rgb,
                        width=width,
                        style=style,
                        use_color=use_color
                    )
                )

            rendered = render_character_grid(
                rows=rows,
                color_rows=color_rows,
                use_color=use_color,
                font_size=font_size,
                target_size=(
                    source_width,
                    source_height
                )
            )

            rendered_bgr = cv2.cvtColor(
                np.array(rendered),
                cv2.COLOR_RGB2BGR
            )

            if writer is None:

                fourcc = cv2.VideoWriter_fourcc(
                    *"mp4v"
                )

                writer = cv2.VideoWriter(
                    silent_video_path,
                    fourcc,
                    fps,
                    (
                        source_width,
                        source_height
                    )
                )

                if not writer.isOpened():
                    raise RuntimeError(
                        "Could not create the temporary ASCII video."
                    )

            writer.write(
                rendered_bgr
            )

            frame_number += 1

            if (
                frame_number == 1
                or frame_number % 30 == 0
                or frame_number == total_frames
            ):

                if total_frames > 0:

                    percent = (
                        frame_number
                        / total_frames
                        * 100
                    )

                    print(
                        f"Processed "
                        f"{frame_number}/"
                        f"{total_frames} frames "
                        f"({percent:.1f}%)"
                    )

                else:

                    print(
                        f"Processed "
                        f"{frame_number} frames"
                    )

    finally:

        capture.release()

        if writer is not None:
            writer.release()

    if frame_number == 0:

        if os.path.exists(silent_video_path):
            os.remove(silent_video_path)

        raise RuntimeError(
            "No video frames were found."
        )

    print()
    print("Adding original audio...")

    # Use the ASCII video as the video stream and the original file
    # as the audio source. The '?' after a:0 makes audio optional,
    # so videos without audio still work.
    ffmpeg_command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        silent_video_path,
        "-i",
        video_path,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0?",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        output_path
    ]

    try:

        subprocess.run(
            ffmpeg_command,
            check=True
        )

    except subprocess.CalledProcessError as error:

        raise RuntimeError(
            "FFmpeg could not combine the ASCII video "
            "with the original audio."
        ) from error

    finally:

        if os.path.exists(silent_video_path):
            os.remove(silent_video_path)

    return output_path


# ---------------------------------------------------------
# SAVE OUTPUT
# ---------------------------------------------------------

def save_ascii_art(
    art,
    output_path,
    use_color=False
):
    """
    Saves artwork as:
    - .txt when color is off
    - .html when color is on

    HTML is used for colored output so the RGB colors are preserved
    when the file is opened in a web browser.
    """

    if use_color:

        if output_path.lower().endswith(".txt"):
            output_path = output_path[:-4] + ".html"
        elif not output_path.lower().endswith(".html"):
            output_path += ".html"

        html_art = ansi_to_html(art)

        html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ASCII Art</title>
<style>
    body {{
        margin: 0;
        padding: 20px;
        background: black;
        color: white;
        font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
    }}

    pre {{
        margin: 0;
        white-space: pre;
        font-family: "SF Mono", monospace;
        font-size: 11pt;
        line-height: normal;
        letter-spacing: normal;
        font-weight: 400;
    }}
</style>
</head>
<body>
<pre>{html_art}</pre>
</body>
</html>
"""

        with open(
            output_path,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(html_document)

    else:

        if not output_path.lower().endswith(".txt"):
            output_path += ".txt"

        clean_art = strip_ansi(art)

        with open(
            output_path,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(clean_art)

    return output_path


# ---------------------------------------------------------
# MAIN PROGRAM
# ---------------------------------------------------------

def main():

    print()
    print("=" * 50)
    print("           ASCII ART GENERATOR")
    print("=" * 50)

    print()
    print("Rendering Styles:")
    print("1. Clean ASCII")
    print("2. Detailed ASCII")
    print("3. High Detail Unicode")
    print()

    # -----------------------------------------------------
    # 1. CHOOSE STYLE
    # -----------------------------------------------------

    style_input = input(
        "Choose style (1, 2, or 3) [default: 1]: "
    ).strip()

    if style_input == "":
        style_input = "1"

    if style_input == "1":
        style = "clean"

    elif style_input == "2":
        style = "detailed"

    elif style_input == "3":
        style = "unicode"

    else:
        print()
        print(
            "Error: Please choose 1, 2, or 3."
        )
        return

    # -----------------------------------------------------
    # 2. CHOOSE COLOR
    # -----------------------------------------------------

    color_input = input(
        "Use original colors? (y/n) [default: n]: "
    ).strip().lower()

    if color_input in ["", "n", "no"]:
        use_color = False

    elif color_input in ["y", "yes"]:
        use_color = True

    else:
        print()
        print(
            "Error: Please enter y or n."
        )
        return

    # -----------------------------------------------------
    # 3. ENTER IMAGE OR VIDEO PATH
    # -----------------------------------------------------

    print()

    input_path = input(
        "Enter the path to an image or video: "
    ).strip()

    input_path = os.path.expanduser(
        input_path
    )

    video_mode = is_video_file(
        input_path
    )

    # -----------------------------------------------------
    # 4. CHOOSE WIDTH
    # -----------------------------------------------------

    if video_mode:

        if style == "unicode":
            default_width = 80
        else:
            default_width = 120

    else:

        if style == "unicode":
            default_width = 100
        else:
            default_width = 190

    if style == "unicode":

        width_input = input(
            f"Unicode width / detail "
            f"[default: {default_width}]: "
        ).strip()

    else:

        width_input = input(
            f"ASCII width / detail "
            f"[default: {default_width}]: "
        ).strip()

    try:

        if width_input:
            width = int(width_input)

        else:
            width = default_width

        if width < 20:
            print()
            print(
                "Error: Width must be at least 20."
            )
            return

    except ValueError:

        print()
        print(
            "Error: Width must be a number."
        )
        return

    # -----------------------------------------------------
    # 5. UNICODE-SPECIFIC SETTINGS
    # -----------------------------------------------------

    threshold = 120

    if style == "unicode":

        threshold_input = input(
            "Brightness threshold [default: 120]: "
        ).strip()

        try:

            if threshold_input:
                threshold = int(
                    threshold_input
                )

            if threshold < 0 or threshold > 255:

                print()
                print(
                    "Error: Threshold must be "
                    "between 0 and 255."
                )
                return

        except ValueError:

            print()
            print(
                "Error: Threshold must be a number."
            )
            return

    # -----------------------------------------------------
    # 6A. VIDEO MODE
    # -----------------------------------------------------

    if video_mode:

        print()
        print("Video detected.")
        print(
            "The video will be converted "
            "to ASCII frame by frame."
        )
        print(
            "Original audio will be preserved "
            "when the source video has audio."
        )
        print(
            "The final MP4 will keep the source "
            "video's exact pixel dimensions."
        )
        print(
            "ASCII width only changes the detail level."
        )
        print()

        output_name = input(
            "Output video name "
            "[default: ascii_video.mp4]: "
        ).strip()

        if output_name == "":
            output_name = "ascii_video.mp4"

        try:

            print()
            print("Generating ASCII video...")
            print()

            output_name = video_to_ascii_video(
                video_path=input_path,
                output_path=output_name,
                width=width,
                style=style,
                threshold=threshold,
                use_color=use_color
            )

            print()
            print(
                f"Saved successfully as: "
                f"{output_name}"
            )

        except FileNotFoundError:

            print()
            print(
                "Error: Video file not found."
            )

        except PermissionError:

            print()
            print(
                "Error: Permission denied "
                "when accessing the file."
            )

        except Exception as error:

            print()
            print(
                f"Error: {error}"
            )

        return

    # -----------------------------------------------------
    # 6B. IMAGE MODE
    # -----------------------------------------------------

    try:

        print()
        print("Generating...")
        print()

        if style == "unicode":

            art = image_to_braille(
                image_path=input_path,
                width=width,
                threshold=threshold,
                use_color=use_color
            )

        else:

            art = image_to_ascii(
                image_path=input_path,
                width=width,
                style=style,
                use_color=use_color
            )

        print("=" * 50)

        if style == "clean":
            print("Clean ASCII")

        elif style == "detailed":
            print("Detailed ASCII")

        else:
            print("High Detail Unicode")

        if use_color:
            print("Color: ON")
        else:
            print("Color: OFF")

        print("=" * 50)
        print()

        print(art)

        print()

        save_choice = input(
            "Save artwork? (y/n): "
        ).strip().lower()

        if save_choice in [
            "y",
            "yes"
        ]:

            if use_color:
                default_output_name = (
                    "ascii_output.html"
                )
            else:
                default_output_name = (
                    "ascii_output.txt"
                )

            output_name = input(
                f"File name "
                f"[default: "
                f"{default_output_name}]: "
            ).strip()

            if output_name == "":
                output_name = (
                    default_output_name
                )

            output_name = save_ascii_art(
                art,
                output_name,
                use_color=use_color
            )

            print()
            print(
                f"Saved successfully as: "
                f"{output_name}"
            )

    except FileNotFoundError:

        print()
        print(
            "Error: Image file not found."
        )

    except PermissionError:

        print()
        print(
            "Error: Permission denied "
            "when accessing the file."
        )

    except Exception as error:

        print()
        print(
            f"Error: {error}"
        )


# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------

if __name__ == "__main__":
    main()
