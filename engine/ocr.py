from __future__ import annotations

import os
from typing import Any

import pytesseract
from PIL import Image


TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def configure_tesseract() -> None:
    """
    Configure Tesseract sous Windows.
    """

    if not os.path.exists(TESSERACT_PATH):
        raise FileNotFoundError(
            f"Tesseract introuvable : {TESSERACT_PATH}"
        )

    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def calculate_confidence(
    data: dict[str, list[Any]],
) -> float:
    """
    Calcule la confiance moyenne Tesseract.
    """

    values = []

    for raw in data.get("conf", []):
        try:
            value = float(raw)

            if value >= 0:
                values.append(value)

        except (TypeError, ValueError):
            continue

    if not values:
        return 0.0

    return round(
        sum(values) / len(values) / 100,
        3,
    )


def ocr_with_coordinates(
    image: Image.Image,
    language: str = "fra",
    psm: int = 11,
) -> dict[str, Any]:
    """
    Effectue OCR avec texte + coordonnées.
    """

    configure_tesseract()

    config = f"--oem 3 --psm {psm}"

    data = pytesseract.image_to_data(
        image,
        lang=language,
        config=config,
        output_type=pytesseract.Output.DICT,
    )

    words = []

    for i, text in enumerate(data["text"]):

        text = text.strip()

        if not text:
            continue

        try:
            confidence = float(
                data["conf"][i]
            )
        except (TypeError, ValueError):
            confidence = -1

        words.append(
            {
                "text": text,
                "x": int(data["left"][i]),
                "y": int(data["top"][i]),
                "width": int(data["width"][i]),
                "height": int(data["height"][i]),
                "confidence": confidence,
                "block": int(data["block_num"][i]),
                "paragraph": int(data["par_num"][i]),
                "line": int(data["line_num"][i]),
            }
        )

    text = pytesseract.image_to_string(
        image,
        lang=language,
        config=config,
    )

    return {
        "text": text.strip(),
        "confidence": calculate_confidence(data),
        "words": words,
    }