from pathlib import Path

from PIL import Image

from engine.preprocessing import generate_variants
from engine.ocr_engine import ocr_image
from engine.layout import reconstruct_lines
from engine.field_extractor import extract_fields


IMAGE_PATH = Path("test.png")


if not IMAGE_PATH.exists():
    print("ERREUR : test.png introuvable")
    raise SystemExit(1)


with Image.open(IMAGE_PATH) as image:

    variants = generate_variants(
        image,
        scale=2.0,
    )

    selected = variants["original"]


result = ocr_image(
    selected,
    language="fra",
    psm=11,
)


lines = reconstruct_lines(
    result["data"]
)


fields = extract_fields(
    lines
)


print("=" * 80)
print("EXTRACTION DES CHAMPS")
print("=" * 80)

print()

for field, value in fields.items():

    print(
        f"{field:25} : {value}"
    )
