from pathlib import Path

from PIL import Image

from engine.preprocessing import generate_variants
from engine.ocr_engine import ocr_image
from engine.layout import reconstruct_lines


IMAGE_PATH = Path("test.png")


if not IMAGE_PATH.exists():
    print("ERREUR : test.png introuvable")
    raise SystemExit(1)


with Image.open(IMAGE_PATH) as image:

    variants = generate_variants(
        image,
        scale=2.0,
    )

    # Pour notre document actuel,
    # le benchmark a montré que l'original est meilleur.
    image_ocr = variants["original"]


result = ocr_image(
    image_ocr,
    language="fra",
    psm=11,
)


lines = reconstruct_lines(
    result["data"]
)


print("=" * 80)
print("RECONSTRUCTION DES LIGNES")
print("=" * 80)


for index, line in enumerate(lines, start=1):

    print()
    print(
        f"LIGNE {index:02d} "
        f"| x={line['x']:4} "
        f"| y={line['y']:4} "
        f"| confiance={line['confidence']:5.1f}"
    )

    print(
        f"TEXT : {line['text']}"
    )
