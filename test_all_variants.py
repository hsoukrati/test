from pathlib import Path
import time

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


results = []


for name, variant in variants.items():

    print()
    print("=" * 70)
    print(f"TEST : {name}")
    print("=" * 70)

    start = time.perf_counter()

    result = ocr_image(
        variant,
        language="fra",
        psm=11,
    )

    duration = time.perf_counter() - start

    text = result["text"]

    words = len(text.split())

    results.append(
        {
            "name": name,
            "confidence": result["confidence"],
            "words": words,
            "duration": duration,
            "text": text,
        }
    )

    print(f"Confidence : {result['confidence']:.3f}")
    print(f"Mots       : {words}")
    print(f"Temps      : {duration:.2f} s")

    print()
    print(text)


print()
print()
print("=" * 70)
print("COMPARAISON DES VARIANTES")
print("=" * 70)

print()

for result in results:

    print(
        f"{result['name']:15} "
        f"| confiance = {result['confidence']:.3f} "
        f"| mots = {result['words']:3} "
        f"| temps = {result['duration']:.2f}s"
    )


best = max(
    results,
    key=lambda item: item["confidence"],
)


print()
print("=" * 70)
print("MEILLEURE VARIANTE")
print("=" * 70)

print(f"Variante   : {best['name']}")
print(f"Confiance  : {best['confidence']:.3f}")
print(f"Mots       : {best['words']}")
print(f"Temps      : {best['duration']:.2f}s")

print()
print("TEXTE RETENU")
print("=" * 70)
print(best["text"])
