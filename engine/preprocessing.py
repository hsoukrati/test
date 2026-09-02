
from __future__ import annotations

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


# =============================================================
# CONFIGURATION
# =============================================================

DEFAULT_SCALE = 2.0


# =============================================================
# VERIFICATION IMAGE
# =============================================================

def validate_image(
    image: Image.Image,
) -> Image.Image:
    """
    Vérifie qu'un objet PIL Image est valide.

    Le preprocessing accepte uniquement une image PIL.
    Le chargement PDF/image est géré par document_loader.py.
    """

    if not isinstance(
        image,
        Image.Image,
    ):
        raise TypeError(
            "preprocessing attend une "
            "PIL.Image.Image."
        )

    if image.width <= 0 or image.height <= 0:

        raise ValueError(
            "Les dimensions de l'image "
            "doivent être supérieures à 0."
        )

    return image


# =============================================================
# CONVERSION RGB
# =============================================================

def ensure_rgb(
    image: Image.Image,
) -> Image.Image:
    """
    Convertit l'image en RGB.

    Cela permet d'avoir un format uniforme
    pour toutes les étapes suivantes.
    """

    validate_image(image)

    if image.mode == "RGB":

        return image.copy()

    return image.convert(
        "RGB"
    )


# =============================================================
# REDIMENSIONNEMENT
# =============================================================

def resize_image(
    image: Image.Image,
    scale: float = DEFAULT_SCALE,
) -> Image.Image:
    """
    Agrandit l'image pour améliorer la lecture OCR.

    Exemple :

        1000 x 500
        scale=2

        -> 2000 x 1000
    """

    image = ensure_rgb(
        image
    )

    if scale <= 0:

        raise ValueError(
            "scale doit être supérieur à 0."
        )

    if scale == 1.0:

        return image.copy()

    width = max(
        1,
        int(
            round(
                image.width * scale
            )
        ),
    )

    height = max(
        1,
        int(
            round(
                image.height * scale
            )
        ),
    )

    return image.resize(
        (
            width,
            height,
        ),
        Image.Resampling.LANCZOS,
    )


# =============================================================
# NIVEAUX DE GRIS
# =============================================================

def to_grayscale(
    image: Image.Image,
) -> Image.Image:
    """
    Convertit l'image en niveaux de gris.
    """

    image = ensure_rgb(
        image
    )

    return ImageOps.grayscale(
        image
    )


# =============================================================
# CONTRASTE
# =============================================================

def enhance_contrast(
    image: Image.Image,
    factor: float = 1.5,
) -> Image.Image:
    """
    Améliore le contraste.

    factor=1.0 :
        aucun changement

    factor>1 :
        contraste augmenté
    """

    if factor <= 0:

        raise ValueError(
            "factor doit être supérieur à 0."
        )

    gray = to_grayscale(
        image
    )

    enhanced = ImageEnhance.Contrast(
        gray
    ).enhance(
        factor
    )

    return enhanced


# =============================================================
# NETTETE
# =============================================================

def sharpen_image(
    image: Image.Image,
) -> Image.Image:
    """
    Améliore légèrement la netteté.
    """

    gray = to_grayscale(
        image
    )

    # UnsharpMask est généralement
    # plus contrôlable qu'un sharpen
    # très agressif.

    return gray.filter(
        ImageFilter.UnsharpMask(
            radius=1.2,
            percent=120,
            threshold=3,
        )
    )


# =============================================================
# BINARISATION GLOBALE
# =============================================================

def binary_threshold(
    image: Image.Image,
    threshold: int = 180,
) -> Image.Image:
    """
    Transforme l'image en noir/blanc
    avec un seuil global.

    Cette variante fonctionne bien lorsque
    le fond est relativement uniforme.
    """

    if not 0 <= threshold <= 255:

        raise ValueError(
            "threshold doit être compris "
            "entre 0 et 255."
        )

    gray = to_grayscale(
        image
    )

    return gray.point(
        lambda pixel:
            255
            if pixel >= threshold
            else 0
    )


# =============================================================
# BINARISATION ADAPTATIVE
# =============================================================

def adaptive_threshold(
    image: Image.Image,
    block_size: int = 31,
    offset: int = 10,
) -> Image.Image:
    """
    Binarisation adaptative locale.

    Cette méthode est utile lorsque le document
    contient des zones plus claires ou plus sombres.

    Elle utilise uniquement Pillow.

    block_size :
        taille de la fenêtre locale.

    offset :
        marge soustraite au niveau local.
    """

    if block_size < 3:

        raise ValueError(
            "block_size doit être >= 3."
        )

    # Il est préférable d'avoir
    # une taille impaire.

    if block_size % 2 == 0:

        block_size += 1

    gray = to_grayscale(
        image
    )

    # ---------------------------------------------------------
    # Flou local
    # ---------------------------------------------------------

    local_background = gray.filter(
        ImageFilter.GaussianBlur(
            radius=max(
                1,
                block_size // 6,
            )
        )
    )

    # ---------------------------------------------------------
    # Seuillage local
    # ---------------------------------------------------------

    width = gray.width
    height = gray.height

    result = Image.new(
        "L",
        (
            width,
            height,
            ),
        255,
    )

    source_pixels = gray.load()
    background_pixels = (
        local_background.load()
    )
    result_pixels = result.load()

    for y in range(
        height
    ):

        for x in range(
            width
        ):

            pixel = source_pixels[
                x,
                y,
            ]

            background = background_pixels[
                x,
                y,
            ]

            threshold = (
                background
                - offset
            )

            if pixel < threshold:

                result_pixels[
                    x,
                    y
                ] = 0

            else:

                result_pixels[
                    x,
                    y
                ] = 255

    return result


# =============================================================
# REDUCTION DU BRUIT
# =============================================================

def denoise_image(
    image: Image.Image,
) -> Image.Image:
    """
    Réduction légère du bruit.

    Le filtre reste volontairement modéré
    pour éviter de supprimer les petits caractères.
    """

    gray = to_grayscale(
        image
    )

    return gray.filter(
        ImageFilter.MedianFilter(
            size=3
        )
    )


# =============================================================
# AMELIORATION CONTRASTE + NETTETE
# =============================================================

def enhanced_text(
    image: Image.Image,
) -> Image.Image:
    """
    Variante destinée aux documents
    dont le texte est peu contrasté.

    Étapes :

        niveaux de gris
        contraste
        netteté légère
    """

    gray = to_grayscale(
        image
    )

    contrast = ImageEnhance.Contrast(
        gray
    ).enhance(
        1.6
    )

    sharpened = contrast.filter(
        ImageFilter.UnsharpMask(
            radius=1.0,
            percent=110,
            threshold=3,
        )
    )

    return sharpened


# =============================================================
# GENERATION DES VARIANTES
# =============================================================

def generate_variants(
    image: Image.Image,
    scale: float = DEFAULT_SCALE,
) -> dict[str, Image.Image]:
    """
    Génère plusieurs variantes d'une image
    pour le moteur OCR.

    Important :

    Cette fonction ne connaît aucun champ métier.

    Elle peut donc être utilisée avec :

        facture
        formulaire
        fiche industrielle
        tableau
        contrat
        courrier
        document administratif
        etc.

    Variantes :

        original
        grayscale
        contrast
        sharpened
        binary
        adaptive
        denoised
        enhanced

    """

    image = validate_image(
        image
    )

    # ---------------------------------------------------------
    # Agrandissement commun
    # ---------------------------------------------------------

    scaled = resize_image(
        image,
        scale=scale,
    )

    # ---------------------------------------------------------
    # Génération
    # ---------------------------------------------------------

    variants: dict[
        str,
        Image.Image
    ] = {}

    # 1. Original
    #
    # Important :
    # on conserve toujours une copie
    # aussi proche que possible de l'original.

    variants[
        "original"
    ] = scaled.copy()

    # 2. Grayscale

    variants[
        "grayscale"
    ] = to_grayscale(
        scaled
    )

    # 3. Contraste

    variants[
        "contrast"
    ] = enhance_contrast(
        scaled,
        factor=1.5,
    )

    # 4. Netteté

    variants[
        "sharpened"
    ] = sharpen_image(
        scaled
    )

    # 5. Binarisation globale

    variants[
        "binary"
    ] = binary_threshold(
        scaled,
        threshold=180,
    )

    # 6. Binarisation adaptative

    variants[
        "adaptive"
    ] = adaptive_threshold(
        scaled,
        block_size=31,
        offset=10,
    )

    # 7. Réduction bruit

    variants[
        "denoised"
    ] = denoise_image(
        scaled
    )

    # 8. Variante texte améliorée

    variants[
        "enhanced"
    ] = enhanced_text(
        scaled
    )

    return variants


# =============================================================
# TEST DIRECT
# =============================================================

if __name__ == "__main__":

    print("=" * 70)

    print(
        "TEST PREPROCESSING OCR"
    )

    print("=" * 70)

    # ---------------------------------------------------------
    # Recherche d'un document de test
    # ---------------------------------------------------------

    test_candidates = [
        "test.png",
        "test.jpg",
        "test.jpeg",
        "test.tif",
        "test.tiff",
        "test.webp",
    ]

    test_path = None

    for candidate in test_candidates:

        path = __import__(
            "pathlib"
        ).Path(candidate)

        if path.exists():

            test_path = path
            break

    if test_path is None:

        print(
            "\nERREUR : aucune image de test."
        )

        print(
            "Placez par exemple test.png "
            "dans le dossier V1."
        )

        raise SystemExit(1)

    print(
        f"\nImage test : "
        f"{test_path}"
    )

    # ---------------------------------------------------------
    # Chargement
    # ---------------------------------------------------------

    try:

        with Image.open(
            test_path
        ) as image:

            image = image.copy()

    except Exception as exc:

        print(
            f"\nERREUR chargement : "
            f"{exc}"
        )

        raise SystemExit(1)

    print(
        f"Dimensions originales : "
        f"{image.width} x "
        f"{image.height}"
    )

    print(
        f"Mode original : "
        f"{image.mode}"
    )

    # ---------------------------------------------------------
    # Variantes
    # ---------------------------------------------------------

    try:

        variants = generate_variants(
            image,
            scale=2.0,
        )

    except Exception as exc:

        print(
            f"\nERREUR preprocessing : "
            f"{exc}"
        )

        raise SystemExit(1)

    # ---------------------------------------------------------
    # Affichage
    # ---------------------------------------------------------

    print(
        "\nVariantes générées :"
    )

    for name, variant in variants.items():

        print(
            f"  {name:<12} "
            f"-> "
            f"{variant.width} x "
            f"{variant.height} "
            f"| mode={variant.mode}"
        )

    # ---------------------------------------------------------
    # Vérifications
    # ---------------------------------------------------------

    expected_variants = {
        "original",
        "grayscale",
        "contrast",
        "sharpened",
        "binary",
        "adaptive",
        "denoised",
        "enhanced",
    }

    missing = (
        expected_variants
        - set(variants.keys())
    )

    if missing:

        print(
            "\nERREUR : variantes manquantes : "
            + ", ".join(
                sorted(missing)
            )
        )

        raise SystemExit(1)

    # Vérification dimensions

    original_size = (
        variants[
            "original"
        ].size
    )

    for name, variant in variants.items():

        if variant.size != original_size:

            print(
                f"\nERREUR : "
                f"{name} possède une taille "
                f"différente."
            )

            raise SystemExit(1)

    print(
        "\nToutes les variantes possèdent "
        "les mêmes dimensions."
    )

    print(
        "\nTEST PREPROCESSING TERMINE"
    )

    print(
        "=" * 70
    )

