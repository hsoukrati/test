from pathlib import Path
from PIL import Image

from engine.preprocessing import preprocess_image


image_path = Path("test.png")

if not image_path.exists():
    print("ERREUR : test.png introuvable")
    print("Place une image de test dans V1 et appelle-la test.png")
    raise SystemExit(1)

with Image.open(image_path) as image:
    print("Image originale :", image.size)
    print("Mode original   :", image.mode)

    processed = preprocess_image(image)

    print("Image traitée   :", processed.size)
    print("Mode traité     :", processed.mode)

    processed.save("test_preprocessed.png")

print("OK : test_preprocessed.png créé")
