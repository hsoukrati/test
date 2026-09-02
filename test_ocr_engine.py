from pathlib import Path

from PIL import Image

from engine.preprocessing import preprocess_image
from engine.ocr_engine import ocr_image


image_path = Path("test.png")

if not image_path.exists():
    print("ERREUR : test.png introuvable")
    raise SystemExit(1)


with Image.open(image_path) as image:

    processed = preprocess_image(
        image,
        scale=2.0,
        autocontrast=True,
        sharpen=True,
    )

    result = ocr_image(
        processed,
        language="fra",
        psm=11,
    )


print("=" * 70)
print("NOUVEAU MOTEUR OCR")
print("=" * 70)

print("Engine     :", result["engine"])
print("Language   :", result["language"])
print("PSM        :", result["psm"])
print("Confidence :", result["confidence"])

print()
print(result["text"])
