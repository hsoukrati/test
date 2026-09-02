#!/usr/bin/env python3
"""Hybrid PDF/image extraction engine.

The API server sends one JSON document through stdin and receives one JSON
result on stdout. The engine deliberately keeps uncertainty visible instead of
silently "correcting" OCR output.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


def clean_text(value: str) -> str:
    value = value.replace("\x00", "")
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def confidence_from_data(data: dict[str, list[Any]]) -> float:
    values: list[float] = []
    for raw in data.get("conf", []):
        try:
            score = float(raw)
            if score >= 0:
                values.append(score)
        except (TypeError, ValueError):
            continue
    return round(sum(values) / len(values) / 100, 3) if values else 0.0


def ocr_image(image: Any, language: str, enhance: bool, psm: int = 3) -> tuple[str, float]:
    import pytesseract
    from PIL import ImageOps

    # Chemin de Tesseract sous Windows
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    if not os.path.exists(tesseract_path):
        raise FileNotFoundError(
            f"Tesseract introuvable : {tesseract_path}"
        )

    pytesseract.pytesseract.tesseract_cmd = tesseract_path

    if enhance:
        image = image.convert("L")
        image = ImageOps.autocontrast(image)
        image = image.resize(
            (image.width * 2, image.height * 2)
        )

    data = pytesseract.image_to_data(
        image,
        lang=language,
        config=f"--oem 3 --psm {psm}",
        output_type=pytesseract.Output.DICT,
    )

    text = clean_text(
        pytesseract.image_to_string(
            image,
            lang=language,
            config=f"--oem 3 --psm {psm}",
        )
    )

    return text, confidence_from_data(data)

def extract_pdf(path: Path, language: str, enhance: bool, psm: int = 3) -> dict[str, Any]:
    import pymupdf

    document = pymupdf.open(path)
    native_pages: list[str] = []
    for page in document:
        native_pages.append(clean_text(page.get_text("text")))

    native_chars = sum(len(page) for page in native_pages)
    if native_chars >= 30:
        text = clean_text("\n\n".join(native_pages))
        return {
            "documentType": "digital-pdf",
            "pages": len(document),
            "text": text,
            "confidence": 0.995,
            "engine": "PyMuPDF Â· text layer",
            "warnings": [],
        }

    pages: list[str] = []
    confidences: list[float] = []
    for page in document:
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2.5, 2.5), alpha=False)
        from PIL import Image

        image = Image.open(io.BytesIO(pixmap.tobytes("png")))
        page_text, confidence = ocr_image(image, language, enhance, psm)
        pages.append(page_text)
        confidences.append(confidence)

    return {
        "documentType": "scanned-pdf",
        "pages": len(document),
        "text": clean_text("\n\n".join(pages)),
        "confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0.0,
        "engine": "Tesseract OCR Â· 300 DPI render",
        "warnings": ["VÃ©rifiez les passages signalÃ©s si la confiance est infÃ©rieure Ã  85 %."] if confidences and sum(confidences) / len(confidences) < 0.85 else [],
    }


def extract_image(path: Path, language: str, enhance: bool, psm: int = 3) -> dict[str, Any]:
    from PIL import Image

    with Image.open(path) as image:
        text, confidence = ocr_image(image, language, enhance, psm)
    return {
        "documentType": "image",
        "pages": 1,
        "text": text,
        "confidence": confidence,
        "engine": "Tesseract OCR Â· image prÃ©traitÃ©e" if enhance else "Tesseract OCR",
        "warnings": ["VÃ©rifiez les passages signalÃ©s si la confiance est infÃ©rieure Ã  85 %."] if confidence < 0.85 else [],
    }


def main() -> None:
    request = json.loads(sys.stdin.read())
    raw = base64.b64decode(request["contentBase64"])
    suffix = Path(request["fileName"]).suffix.lower() or ".bin"
    language = request.get("language", "fra")
    enhance = bool(request.get("enhanceImage", True))
    psm = int(request.get("psm", 3))

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary:
        temporary.write(raw)
        temp_path = Path(temporary.name)

    try:
        if request["mimeType"] == "application/pdf" or suffix == ".pdf":
            result = extract_pdf(temp_path, language, enhance, psm)
        else:
            result = extract_image(temp_path, language, enhance, psm)
        result["tables"] = []
        result["words"] = len(result["text"].split())
        print(json.dumps(result, ensure_ascii=False))
    except Exception as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        raise
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


if __name__ == "__main__":
    main()

