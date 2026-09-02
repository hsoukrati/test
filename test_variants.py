from pathlib import Path

from PIL import Image

from engine.preprocessing import generate_variants


image_path = Path("test.png")

if not image_path.exists():
    print("ERREUR : test.png introuvable")
    raise SystemExit(1)


with Image.open(image_path) as image:

    variants = generate_variants(
        image,
        scale=2.0,
    )


print("=" * 70)
print("VARIANTES OCR")
print("=" * 70)

for name, variant in variants.items():

    filename = f"test_{name}.png"

    variant.save(filename)

    print(
        f"{name:15} -> "
        f"{variant.width} x {variant.height} "
        f"-> {filename}"
    )
