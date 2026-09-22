from PIL import Image, ImageOps, ImageFilter
import os


# ---------------------------------------------------------
# CHARACTER SETS
# ---------------------------------------------------------

# Darkest -> brightest
CLEAN_CHARS = " .,:;irsXA253hMHGS#9B&@"

DETAILED_CHARS = (
    " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B$@"
)


# ---------------------------------------------------------
# IMAGE PREPARATION
# ---------------------------------------------------------

def prepare_image(image_path):
    """
    Opens and prepares an image for rendering.
    """

    image_path = os.path.expanduser(image_path)

    image = Image.open(image_path)

    # Correct phone/camera orientation
    image = ImageOps.exif_transpose(image)

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

def image_to_ascii(image_path, width=190, style="clean"):
    """
    Converts an image into clean or detailed ASCII.
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

    pixels = list(image.get_flattened_data())

    ascii_pixels = []

    for pixel in pixels:

        # Leave nearly-black areas blank
        if pixel < 10:
            ascii_pixels.append(" ")
            continue

        index = int(
            pixel / 255 * (len(ascii_chars) - 1)
        )

        ascii_pixels.append(
            ascii_chars[index]
        )

    rows = []

    for i in range(0, len(ascii_pixels), width):

        row = "".join(
            ascii_pixels[i:i + width]
        )

        rows.append(row)

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
    threshold=120
):
    """
    Converts an image into high-detail Unicode Braille art.

    Each Braille character represents a 2x4 grid.
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

            row.append(char)

        rows.append(
            "".join(row)
        )

    return "\n".join(rows)


# ---------------------------------------------------------
# SAVE OUTPUT
# ---------------------------------------------------------

def save_ascii_art(
    art,
    output_path
):
    """
    Saves ASCII or Unicode artwork as a UTF-8 text file.
    """

    if not output_path.lower().endswith(
        ".txt"
    ):
        output_path += ".txt"

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(art)

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
    # 1. CHOOSE STYLE FIRST
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
    # 2. ENTER IMAGE PATH
    # -----------------------------------------------------

    print()

    image_path = input(
        "Enter the path to an image: "
    ).strip()

    # -----------------------------------------------------
    # 3. CHOOSE WIDTH
    # -----------------------------------------------------

    if style == "unicode":

        width_input = input(
            "Unicode width [default: 100]: "
        ).strip()

        default_width = 100

    else:

        width_input = input(
            "ASCII width [default: 190]: "
        ).strip()

        default_width = 190

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
    # 4. UNICODE-SPECIFIC SETTINGS
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
    # 5. GENERATE ART
    # -----------------------------------------------------

    try:

        print()
        print("Generating...")
        print()

        if style == "unicode":

            art = image_to_braille(
                image_path=image_path,
                width=width,
                threshold=threshold
            )

        else:

            art = image_to_ascii(
                image_path=image_path,
                width=width,
                style=style
            )

        # -------------------------------------------------
        # DISPLAY RESULT
        # -------------------------------------------------

        print("=" * 50)

        if style == "clean":
            print("Clean ASCII")

        elif style == "detailed":
            print("Detailed ASCII")

        else:
            print("High Detail Unicode")

        print("=" * 50)
        print()

        print(art)

        # -------------------------------------------------
        # 6. SAVE RESULT
        # -------------------------------------------------

        print()

        save_choice = input(
            "Save artwork to a text file? (y/n): "
        ).strip().lower()

        if save_choice in [
            "y",
            "yes"
        ]:

            output_name = input(
                "File name "
                "[default: ascii_output.txt]: "
            ).strip()

            if output_name == "":
                output_name = (
                    "ascii_output.txt"
                )

            output_name = save_ascii_art(
                art,
                output_name
            )

            print()
            print(
                f"Saved successfully as: "
                f"{output_name}"
            )

    # -----------------------------------------------------
    # ERROR HANDLING
    # -----------------------------------------------------

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