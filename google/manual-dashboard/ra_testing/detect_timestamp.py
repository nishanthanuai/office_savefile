"""
Module to detect timestamp from image with fallback techniques and validation.
Author: nishant
"""

import cv2
from django.forms import FilePathField
import numpy as np
import pytesseract
import re

# --- Configuration ---
fallback_configs = [
    "--psm 7 -c tessedit_char_whitelist=0123456789:.- ",
    "--psm 6 -c tessedit_char_whitelist=0123456789:.- ",
    "--psm 11 -c tessedit_char_whitelist=0123456789:.- ",
]


def read_img(img):
    return cv2.imread(str(img))


def crop_img(img):
    return img[0:30, 10:500]


def save_image(path, img):
    cv2.imwrite(str(path), img)


def adapt_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    return gray


# ==========================================
# 2. VALIDATION & CONVERSION
# ==========================================
def convert_to_target_format(raw_text):
    """
    Uses your existing slicing logic to convert MMDDYYYY... to YYYY-MM-DD...
    """
    text = raw_text.strip()

    # Avoid IndexError if OCR returned garbage/short text
    if len(text) >= 14:
        month = text[0:2]
        day = text[2:4]
        year = text[4:8]
        time_part = text[8:].strip()
        return f"{year}-{month}-{day} {time_part}"

    return text


def is_valid_timestamp(text):
    """
    Validates if the text strictly matches 'YYYY-MM-DD HH:MM:SS'
    """
    pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
    return bool(re.match(pattern, text))


def process_image(gray):
    # 🔥 Sharpen instead of blur
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharp = cv2.filter2D(gray, -1, kernel)
    # Invert (white on black works better flipped)
    inv = cv2.bitwise_not(sharp)
    # OTSU threshold (auto thresholding)
    return cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


def prep_technique_2(gray):
    """Alternative 1: Upscale -> No Invert -> Standard OTSU"""
    return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


def prep_technique_3(gray):
    """Alternative 2: Upscale -> Adaptive Thresholding"""
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )


def prep_technique_4(gray):
    """Alternative 3: Just Grayscale + Upscale"""
    # The image passed is already grayscale from [adapt_image](cci:1://file:///home/hanuai/Desktop/Nishant_kagra_code/google/manual-dashboard/ra_testing/detect_timestamp.py:29:0-33:15)
    return cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)


def extract_text(img,config=None):
    if not config:
        config = "--psm 7 -c tessedit_char_whitelist=0123456789:."
    return pytesseract.image_to_string(img, config=config)


def fetch_timestamp(img):
    gray = adapt_image(crop_img(read_img(img)))
    final = process_image(gray)
    raw_text = extract_text(final)
    timestamp = convert_to_target_format(raw_text)
    
    if is_valid_timestamp(timestamp):
        return timestamp
    else:
        # iterate over fallback configs and store methods like prep_technique_2, prep_technique_3, prep_technique_4 in a list and then iterate over the list and apply each method to the image and extract text
        fallback_methods = [prep_technique_2, prep_technique_3, prep_technique_4]
        for method in fallback_methods:
            final = method(gray)
            raw_text = extract_text(final)
            timestamp = convert_to_target_format(raw_text)
            if is_valid_timestamp(timestamp):
                return timestamp
        # return an empty string if timestamp is not found
        return ""
    
    


if __name__ == "__main__":
    from pathlib import Path

    file_path = (
        Path(__file__).resolve().parent.parent
        / "media"
        / "Model_Testing"
        / "ndd.roadathena.com"
        / "furniture"
        / "1"
        / "6"
        / "images"
    )
    frame = 1

    for file in file_path.iterdir():
        img = adapt_image(crop_img(read_img(file)))
        save_image(
            path=f"/home/hanuai/Desktop/Nishant_kagra_code/output/frame_{frame}.jpg",
            img=img,
        )
        timestamp = extract_timestamp(img)
        print(f"File: {file.name} -> Timestamp: {timestamp}")
        frame += 1
