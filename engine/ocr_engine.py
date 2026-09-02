from __future__ import annotations

from typing import Any

import pytesseract


# Configuration Windows
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def calculate_confidence(data: dict[str, list[Any]]) -> float:
    values: list[float] = []

    for raw in data.get("conf", []):
        try:
            score = float(raw)

            if score >= 0:
                values.append(score)

        except (TypeError, ValueError):
            continue

    if not values:
        return 0.0

    return round(sum(values) / len(values) / 100, 3)


def ocr_image(
    image,
    language: str = "fra",
    psm: int = 11,
) -> dict[str, Any]:

    config = f"--oem 3 --psm {psm}"

    data = pytesseract.image_to_data(
        image,
        lang=language,
        config=config,
        output_type=pytesseract.Output.DICT,
    )

    text = pytesseract.image_to_string(
        image,
        lang=language,
        config=config,
    )

    confidence = calculate_confidence(data)

    return {
        "text": text.strip(),
        "confidence": confidence,
        "data": data,
        "engine": "Tesseract OCR",
        "language": language,
        "psm": psm,
    }
