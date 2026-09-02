from pathlib import Path

import pytesseract
from PIL import Image

from engine.preprocessing import preprocess_image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


IMAGE_PATH = Path("test.png")


def confidence(data):
    values = []

    for value in data.get("conf", []):
        try:
            value = float(value)
            if value >= 0:
                values.append(value)
        except (TypeError, ValueError):
            pass

    if not values:
        return 0.0

    return sum(values) / len(values) / 100


if not IMAGE_PATH.exists():
    print("ERREUR : test.png introuvable")
    raise SystemExit(1)


with Image.open(IMAGE_PATH) as original:

    # ==============================
    # TEST 1 : IMAGE ORIGINALE
    # ==============================

    data_original = pytesseract.image_to_data(
        original,
        lang="fra",
        config="--oem 3 --psm 11",
        output_type=pytesseract.Output.DICT,
    )

    text_original = pytesseract.image_to_string(
        original,
        lang="fra",
        config="--oem 3 --psm 11",
    )

    conf_original = confidence(data_original)

    # ==============================
    # TEST 2 : IMAGE PRETRAITEE
    # ==============================

    processed = preprocess_image(
        original,
        scale=2.0,
        autocontrast=True,
        sharpen=True,
    )

    data_processed = pytesseract.image_to_data(
        processed,
        lang="fra",
        config="--oem 3 --psm 11",
        output_type=pytesseract.Output.DICT,
    )

    text_processed = pytesseract.image_to_string(
        processed,
        lang="fra",
        config="--oem 3 --psm 11",
    )

    conf_processed = confidence(data_processed)


print()
print("=" * 70)
print("OCR IMAGE ORIGINALE")
print("=" * 70)

print(f"Confiance : {conf_original:.3f}")
print()
print(text_original)


print()
print("=" * 70)
print("OCR IMAGE PRETRAITEE")
print("=" * 70)

print(f"Confiance : {conf_processed:.3f}")
print()
print(text_processed)


print()
print("=" * 70)
print("COMPARAISON")
print("=" * 70)

difference = conf_processed - conf_original

print(f"Original   : {conf_original:.3f}")
print(f"Prétraitée : {conf_processed:.3f}")
print(f"Différence : {difference:+.3f}")

if difference > 0:
    print("RESULTAT : le prétraitement améliore l'OCR.")
elif difference < 0:
    print("RESULTAT : le prétraitement dégrade l'OCR.")
else:
    print("RESULTAT : aucune différence.")

