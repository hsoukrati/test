from pathlib import Path

from PIL import Image

from engine.preprocessing import generate_variants
from engine.ocr_engine import ocr_image


IMAGE_PATH = Path("test.png")


if not IMAGE_PATH.exists():
    print("ERREUR : test.png introuvable")
    raise SystemExit(1)


with Image.open(IMAGE_PATH) as image:

    variants = generate_variants(
        image,
        scale=2.0,
    )

    # Pour l'instant on utilise la meilleure variante
    # observée dans notre benchmark : original
    selected = variants["original"]

    result = ocr_image(
        selected,
        language="fra",
        psm=11,
    )


data = result["data"]


print("=" * 80)
print("OCR AVEC COORDONNEES")
print("=" * 80)

print()


for i in range(len(data["text"])):

    text = data["text"][i].strip()

    if not text:
        continue

    try:
        confidence = float(data["conf"][i])
    except (TypeError, ValueError):
        confidence = -1

    print(
        f"TEXT={text!r:30} "
        f"x={data['left'][i]:4} "
        f"y={data['top'][i]:4} "
        f"w={data['width'][i]:4} "
        f"h={data['height'][i]:4} "
        f"conf={confidence:6.1f} "
        f"block={data['block_num'][i]:2} "
        f"par={data['par_num'][i]:2} "
        f"line={data['line_num'][i]:2}"
    )
