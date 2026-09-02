
from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.document_loader import load_document
from engine.preprocessing import generate_variants
from engine.ocr import ocr_with_coordinates
from engine.layout import (
    group_words_into_lines,
    lines_to_text,
)
from engine.selector import select_best_variant


# =============================================================
# CONFIGURATION
# =============================================================

# Document à tester.
#
# Tu peux mettre :
#     test.png
#     test.jpg
#     test.jpeg
#     test.tif
#     test.tiff
#     test.webp
#     test.pdf
#
DOCUMENT_PATH = Path("test.pdf")

LANGUAGE = "fra"

# PSM 11 :
# OCR adapté aux documents avec une disposition
# relativement libre.
PSM = 11

# Résolution des pages PDF.
PDF_DPI = 200

# Agrandissement utilisé par preprocessing.
PREPROCESSING_SCALE = 2.0


# =============================================================
# EXTENSIONS SUPPORTÉES
# =============================================================

SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".webp",
    ".pdf",
}


# =============================================================
# VERIFICATION DU DOCUMENT
# =============================================================

def verify_document(
    path: Path,
) -> bool:
    """
    Vérifie que le document existe et possède
    une extension supportée.

    Cette fonction ne suppose rien sur le contenu
    du document.
    """

    if not path.exists():

        print(
            f"ERREUR : document introuvable : {path}"
        )

        return False

    if not path.is_file():

        print(
            f"ERREUR : le chemin n'est pas "
            f"un fichier : {path}"
        )

        return False

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:

        print(
            f"ERREUR : format non supporté : "
            f"{extension or '[aucune extension]'}"
        )

        print(
            "Formats acceptés : "
            + ", ".join(
                sorted(SUPPORTED_EXTENSIONS)
            )
        )

        return False

    return True


# =============================================================
# AFFICHAGE INFORMATIONS PAGE
# =============================================================

def print_page_information(
    page_number: int,
    image: Any,
) -> None:
    """
    Affiche les informations d'une page.
    """

    print(
        f"    Page {page_number}: "
        f"{image.width} x {image.height} "
        f"| mode={image.mode}"
    )


# =============================================================
# AFFICHAGE DES MOTS OCR
# =============================================================

def print_words(
    words: list[dict],
) -> None:
    """
    Affiche les mots OCR avec leurs coordonnées.
    """

    print("\nMots OCR détectés :")

    if not words:

        print("    Aucun mot détecté.")

        return

    valid_words = 0

    for index, word in enumerate(words):

        text = str(
            word.get(
                "text",
                "",
            )
        ).strip()

        if not text:
            continue

        valid_words += 1

        try:

            x = float(
                word.get(
                    "x",
                    0,
                )
            )

            y = float(
                word.get(
                    "y",
                    0,
                )
            )

            width = float(
                word.get(
                    "width",
                    0,
                )
            )

            height = float(
                word.get(
                    "height",
                    0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            x = 0.0
            y = 0.0
            width = 0.0
            height = 0.0

        confidence = word.get(
            "confidence",
            word.get(
                "conf",
                "",
            ),
        )

        print(
            f"    [{index:04d}] "
            f"{text:<30} "
            f"x={x:7.1f} "
            f"y={y:7.1f} "
            f"w={width:7.1f} "
            f"h={height:7.1f} "
            f"conf={confidence}"
        )

    if valid_words == 0:

        print("    Aucun mot exploitable.")


# =============================================================
# AFFICHAGE DES LIGNES
# =============================================================

def print_lines(
    lines: list,
) -> None:
    """
    Affiche les lignes reconstruites.
    """

    print("\nLignes reconstruites :")

    if not lines:

        print("    Aucune ligne détectée.")

        return

    displayed = 0

    for index, line in enumerate(
        lines,
        start=1,
    ):

        if isinstance(
            line,
            dict,
        ):

            text = str(
                line.get(
                    "text",
                    "",
                )
            ).strip()

        else:

            text = str(
                line
            ).strip()

        if not text:
            continue

        displayed += 1

        print(
            f"    [{index:03d}] {text}"
        )

    if displayed == 0:

        print(
            "    Aucune ligne exploitable."
        )


# =============================================================
# CALCUL QUALITE TEXTE
# =============================================================

def calculate_text_quality(
    text: str,
    words: list[dict],
) -> float:
    """
    Calcule une qualité simple du résultat OCR.

    Cette fonction est volontairement générique.

    Elle ne connaît aucun champ métier.

    Critères :
        - quantité de texte
        - nombre de mots
        - présence de caractères alphanumériques

    Retour :
        score entre 0 et 1
    """

    text = str(
        text or ""
    ).strip()

    if not text:

        return 0.0

    # ---------------------------------------------------------
    # Nombre de mots réellement exploitables
    # ---------------------------------------------------------

    valid_words = 0

    for word in words:

        value = str(
            word.get(
                "text",
                "",
            )
        ).strip()

        if value:

            valid_words += 1

    # ---------------------------------------------------------
    # Score longueur
    # ---------------------------------------------------------

    text_length = len(text)

    length_score = min(
        text_length / 300.0,
        1.0,
    )

    # ---------------------------------------------------------
    # Score mots
    # ---------------------------------------------------------

    word_score = min(
        valid_words / 50.0,
        1.0,
    )

    # ---------------------------------------------------------
    # Caractères alphanumériques
    # ---------------------------------------------------------

    alphanumeric_count = sum(
        1
        for char in text
        if char.isalnum()
    )

    if text_length > 0:

        alphanumeric_ratio = (
            alphanumeric_count
            / text_length
        )

    else:

        alphanumeric_ratio = 0.0

    alphanumeric_score = min(
        alphanumeric_ratio,
        1.0,
    )

    # ---------------------------------------------------------
    # Score final
    # ---------------------------------------------------------

    score = (
        0.35 * length_score
        + 0.35 * word_score
        + 0.30 * alphanumeric_score
    )

    return max(
        0.0,
        min(
            score,
            1.0,
        ),
    )


# =============================================================
# SELECTION GENERIQUE DE VARIANTE
# =============================================================

def select_generic_variant(
    variant_results: dict[str, dict],
) -> dict:
    """
    Sélectionne la meilleure variante OCR.

    IMPORTANT :

    Cette fonction ne dépend d'aucun champ métier.

    Elle utilise uniquement :

        confidence OCR
        qualité du texte
        nombre de mots
    """

    if not variant_results:

        raise ValueError(
            "Aucune variante OCR disponible."
        )

    candidates = []

    for variant_name, result in (
        variant_results.items()
    ):

        confidence = float(
            result.get(
                "confidence",
                0.0,
            )
            or 0.0
        )

        text = str(
            result.get(
                "text",
                "",
            )
            or ""
        )

        words = result.get(
            "words",
            [],
        )

        if not isinstance(
            words,
            list,
        ):

            words = []

        text_quality = calculate_text_quality(
            text,
            words,
        )

        valid_word_count = sum(
            1
            for word in words
            if str(
                word.get(
                    "text",
                    "",
                )
            ).strip()
        )

        # -----------------------------------------------------
        # Normalisation confiance
        # -----------------------------------------------------

        # Certains OCR retournent 0-100.
        # D'autres retournent 0-1.

        if confidence > 1.0:

            confidence_normalized = (
                confidence / 100.0
            )

        else:

            confidence_normalized = confidence

        confidence_normalized = max(
            0.0,
            min(
                confidence_normalized,
                1.0,
            ),
        )

        # -----------------------------------------------------
        # Score nombre de mots
        # -----------------------------------------------------

        word_score = min(
            valid_word_count / 50.0,
            1.0,
        )

        # -----------------------------------------------------
        # Score final
        # -----------------------------------------------------

        score = (
            0.45
            * confidence_normalized
            + 0.35
            * text_quality
            + 0.20
            * word_score
        )

        candidates.append(
            {
                "variant": variant_name,
                "confidence": confidence_normalized,
                "text_quality": text_quality,
                "word_count": valid_word_count,
                "score": score,
            }
        )

    # ---------------------------------------------------------
    # Tri
    # ---------------------------------------------------------

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    best = candidates[0]

    return {
        "selected_variant":
            best["variant"],

        "score":
            best["score"],

        "confidence":
            best["confidence"],

        "all_results":
            candidates,
    }


# =============================================================
# TRAITEMENT D'UNE PAGE
# =============================================================

def process_page(
    image: Any,
    page_number: int,
) -> dict:
    """
    Traite une page avec plusieurs variantes OCR.

    Pipeline :

        Image
          ↓
        Prétraitement
          ↓
        Variantes
          ↓
        OCR
          ↓
        Coordonnées
          ↓
        Lignes
          ↓
        Texte
          ↓
        Sélection meilleure variante

    Aucun champ métier n'est utilisé.
    """

    print("\n")

    print("=" * 70)

    print(
        f"PAGE {page_number}"
    )

    print("=" * 70)

    print(
        f"Dimensions : "
        f"{image.width} x {image.height}"
    )

    # =========================================================
    # 1. GENERATION DES VARIANTES
    # =========================================================

    print(
        "\n[1] Génération des variantes OCR"
    )

    try:

        variants = generate_variants(
            image,
            scale=PREPROCESSING_SCALE,
        )

    except Exception as exc:

        print(
            "ERREUR preprocessing :"
        )

        print(exc)

        return {
            "page_number":
                page_number,

            "selected_variant":
                None,

            "confidence":
                0.0,

            "score":
                0.0,

            "text":
                "",

            "words":
                [],

            "lines":
                [],

            "variants":
                {},
        }

    if not variants:

        print(
            "ERREUR : aucune variante générée."
        )

        return {
            "page_number":
                page_number,

            "selected_variant":
                None,

            "confidence":
                0.0,

            "score":
                0.0,

            "text":
                "",

            "words":
                [],

            "lines":
                [],

            "variants":
                {},
        }

    for name, variant in variants.items():

        print(
            f"    {name:<15} "
            f"-> "
            f"{variant.width} x "
            f"{variant.height}"
        )

    # =========================================================
    # 2. OCR DES VARIANTES
    # =========================================================

    print(
        "\n[2] OCR des variantes"
    )

    variant_results: dict[str, dict] = {}

    for (
        variant_name,
        variant_image,
    ) in variants.items():

        print(
            "\n"
            + "-" * 70
        )

        print(
            f"VARIANTE : {variant_name}"
        )

        print(
            "-" * 70
        )

        # -----------------------------------------------------
        # OCR
        # -----------------------------------------------------

        try:

            ocr_result = ocr_with_coordinates(
                variant_image,
                language=LANGUAGE,
                psm=PSM,
            )

        except Exception as exc:

            print(
                f"ERREUR OCR pour "
                f"{variant_name} :"
            )

            print(exc)

            variant_results[
                variant_name
            ] = {
                "confidence": 0.0,
                "text": "",
                "words": [],
                "lines": [],
            }

            continue

        if not isinstance(
            ocr_result,
            dict,
        ):

            print(
                "ERREUR : le module OCR "
                "n'a pas retourné un dictionnaire."
            )

            variant_results[
                variant_name
            ] = {
                "confidence": 0.0,
                "text": "",
                "words": [],
                "lines": [],
            }

            continue

        words = ocr_result.get(
            "words",
            [],
        )

        if not isinstance(
            words,
            list,
        ):

            words = []

        confidence = ocr_result.get(
            "confidence",
            0.0,
        )

        try:

            confidence = float(
                confidence or 0.0
            )

        except (
            TypeError,
            ValueError,
        ):

            confidence = 0.0

        # -----------------------------------------------------
        # Reconstruction des lignes
        # -----------------------------------------------------

        try:

            lines = group_words_into_lines(
                words,
                y_tolerance=12,
            )

        except Exception as exc:

            print(
                "ERREUR reconstruction lignes :"
            )

            print(exc)

            lines = []

        # -----------------------------------------------------
        # Conversion lignes -> texte
        # -----------------------------------------------------

        try:

            text = lines_to_text(
                lines
            )

        except Exception as exc:

            print(
                "ERREUR conversion texte :"
            )

            print(exc)

            text = ""

        if text is None:

            text = ""

        text = str(text)

        # -----------------------------------------------------
        # Qualité
        # -----------------------------------------------------

        text_quality = calculate_text_quality(
            text,
            words,
        )

        valid_word_count = sum(
            1
            for word in words
            if str(
                word.get(
                    "text",
                    "",
                )
            ).strip()
        )

        # -----------------------------------------------------
        # Sauvegarde
        # -----------------------------------------------------

        variant_results[
            variant_name
        ] = {

            "confidence":
                confidence,

            "text":
                text,

            "words":
                words,

            "lines":
                lines,

            "text_quality":
                text_quality,

            "word_count":
                valid_word_count,
        }

        # -----------------------------------------------------
        # Affichage
        # -----------------------------------------------------

        print(
            f"Confiance OCR : "
            f"{confidence:.3f}"
        )

        print(
            f"Mots détectés : "
            f"{valid_word_count}"
        )

        print(
            f"Lignes détectées : "
            f"{len(lines)}"
        )

        print(
            f"Qualité texte : "
            f"{text_quality:.3f}"
        )

    # =========================================================
    # 3. SELECTION DE LA MEILLEURE VARIANTE
    # =========================================================

    print(
        "\n[3] Sélection de la meilleure variante"
    )

    # ---------------------------------------------------------
    # On essaie d'abord le selector du projet.
    #
    # Comme le projet est maintenant générique,
    # aucun champ métier n'est fourni.
    #
    # Si le selector actuel n'est pas compatible,
    # on utilise automatiquement notre sélection
    # générique locale.
    # ---------------------------------------------------------

    selected = None

    try:

        selected = select_best_variant(
            variant_results,
            [],
        )

        if not isinstance(
            selected,
            dict,
        ):

            selected = None

        elif not selected.get(
            "selected_variant"
        ):

            selected = None

        elif (
            selected["selected_variant"]
            not in variant_results
        ):

            selected = None

    except Exception as exc:

        print(
            "Selector métier non compatible "
            "avec le pipeline générique."
        )

        print(
            f"Fallback générique activé : {exc}"
        )

        selected = None

    # ---------------------------------------------------------
    # Fallback générique
    # ---------------------------------------------------------

    if selected is None:

        selected = select_generic_variant(
            variant_results
        )

    selected_variant = selected[
        "selected_variant"
    ]

    selected_result = variant_results[
        selected_variant
    ]

    # =========================================================
    # 4. RESULTAT FINAL PAGE
    # =========================================================

    print(
        "\n[4] Résultat final de la page"
    )

    print(
        f"Variante sélectionnée : "
        f"{selected_variant}"
    )

    print(
        f"Score : "
        f"{float(selected.get('score', 0.0)):.3f}"
    )

    print(
        f"Confiance : "
        f"{float(selected_result.get('confidence', 0.0)):.3f}"
    )

    print(
        f"Mots : "
        f"{len(selected_result.get('words', []))}"
    )

    print(
        f"Lignes : "
        f"{len(selected_result.get('lines', []))}"
    )

    # =========================================================
    # 5. MOTS OCR
    # =========================================================

    print_words(
        selected_result.get(
            "words",
            [],
        )
    )

    # =========================================================
    # 6. LIGNES
    # =========================================================

    print_lines(
        selected_result.get(
            "lines",
            [],
        )
    )

    # =========================================================
    # 7. TEXTE FINAL
    # =========================================================

    text = str(
        selected_result.get(
            "text",
            "",
        )
        or ""
    )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "TEXTE FINAL DE LA PAGE"
    )

    print(
        "=" * 70
    )

    if text.strip():

        print(text)

    else:

        print(
            "[Aucun texte détecté]"
        )

    # =========================================================
    # RETOUR
    # =========================================================

    return {

        "page_number":
            page_number,

        "selected_variant":
            selected_variant,

        "confidence":
            selected_result.get(
                "confidence",
                0.0,
            ),

        "score":
            selected.get(
                "score",
                0.0,
            ),

        "text":
            text,

        "words":
            selected_result.get(
                "words",
                [],
            ),

        "lines":
            selected_result.get(
                "lines",
                [],
            ),

        "variants":
            variant_results,
    }


# =============================================================
# PIPELINE PRINCIPAL
# =============================================================

def main() -> None:
    """
    Pipeline OCR générique complet.

    Support :

        PNG
        JPG
        JPEG
        TIFF
        WEBP
        PDF
        PDF multipage

    Aucun champ métier n'est imposé.

    Aucune IA n'est utilisée.
    """

    print("=" * 70)

    print(
        "PIPELINE OCR GENERIQUE - SANS IA"
    )

    print("=" * 70)

    # =========================================================
    # 1. VERIFICATION DOCUMENT
    # =========================================================

    print(
        "\n[1] Vérification du document"
    )

    if not verify_document(
        DOCUMENT_PATH
    ):

        return

    print(
        f"Document : "
        f"{DOCUMENT_PATH}"
    )

    print(
        f"Format : "
        f"{DOCUMENT_PATH.suffix.lower()}"
    )

    # =========================================================
    # 2. CHARGEMENT DOCUMENT
    # =========================================================

    print(
        "\n[2] Chargement du document"
    )

    try:

        document = load_document(
            DOCUMENT_PATH,
            pdf_dpi=PDF_DPI,
        )

    except Exception as exc:

        print(
            "\nERREUR CHARGEMENT :"
        )

        print(exc)

        return

    # ---------------------------------------------------------
    # IMPORTANT :
    #
    # document est un objet LoadedDocument.
    #
    # On ne fait PAS :
    #
    # document.get(...)
    #
    # On utilise :
    #
    # document.document_type
    # document.page_count
    # document.pages
    # ---------------------------------------------------------

    print(
        f"Type : "
        f"{document.document_type}"
    )

    print(
        f"Pages : "
        f"{document.page_count}"
    )

    if document.page_count == 0:

        print(
            "ERREUR : le document ne contient "
            "aucune page."
        )

        return

    # =========================================================
    # 3. INFORMATIONS DES PAGES
    # =========================================================

    print(
        "\n[3] Informations des pages"
    )

    for page in document.pages:

        print_page_information(
            page.page_number,
            page.image,
        )

    # =========================================================
    # 4. OCR DE TOUTES LES PAGES
    # =========================================================

    print(
        "\n[4] Traitement OCR"
    )

    page_results = []

    for page in document.pages:

        try:

            result = process_page(
                page.image,
                page.page_number,
            )

            page_results.append(
                result
            )

        except Exception as exc:

            print(
                "\nERREUR PAGE "
                f"{page.page_number} :"
            )

            print(exc)

            # On continue avec les autres pages.
            page_results.append(
                {
                    "page_number":
                        page.page_number,

                    "selected_variant":
                        None,

                    "confidence":
                        0.0,

                    "score":
                        0.0,

                    "text":
                        "",

                    "words":
                        [],

                    "lines":
                        [],

                    "variants":
                        {},
                }
            )

    # =========================================================
    # 5. TEXTE COMPLET DU DOCUMENT
    # =========================================================

    print(
        "\n\n"
        + "=" * 70
    )

    print(
        "TEXTE COMPLET DU DOCUMENT"
    )

    print(
        "=" * 70
    )

    document_text_parts = []

    for result in page_results:

        page_number = result.get(
            "page_number",
            0,
        )

        text = str(
            result.get(
                "text",
                "",
            )
            or ""
        ).strip()

        print(
            f"\n--- PAGE {page_number} ---"
        )

        if text:

            print(text)

            document_text_parts.append(
                text
            )

        else:

            print(
                "[Aucun texte détecté]"
            )

    # =========================================================
    # 6. RESUME
    # =========================================================

    print(
        "\n\n"
        + "=" * 70
    )

    print(
        "RESUME DU TRAITEMENT"
    )

    print(
        "=" * 70
    )

    print(
        f"Document : "
        f"{DOCUMENT_PATH.name}"
    )

    print(
        f"Type : "
        f"{document.document_type}"
    )

    print(
        f"Nombre de pages : "
        f"{document.page_count}"
    )

    # ---------------------------------------------------------
    # Total mots
    # ---------------------------------------------------------

    total_words = sum(
        len(
            result.get(
                "words",
                [],
            )
        )
        for result in page_results
    )

    # ---------------------------------------------------------
    # Total lignes
    # ---------------------------------------------------------

    total_lines = sum(
        len(
            result.get(
                "lines",
                [],
            )
        )
        for result in page_results
    )

    # ---------------------------------------------------------
    # Pages réussies
    # ---------------------------------------------------------

    successful_pages = sum(
        1
        for result in page_results
        if result.get(
            "text",
            "",
        ).strip()
    )

    print(
        f"Pages traitées : "
        f"{len(page_results)}"
    )

    print(
        f"Pages avec texte : "
        f"{successful_pages}"
    )

    print(
        f"Total mots OCR : "
        f"{total_words}"
    )

    print(
        f"Total lignes : "
        f"{total_lines}"
    )

    # ---------------------------------------------------------
    # Texte global disponible
    # ---------------------------------------------------------

    complete_text = "\n\n".join(
        document_text_parts
    )

    print(
        f"Caractères texte : "
        f"{len(complete_text)}"
    )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "PIPELINE OCR TERMINE"
    )

    print(
        "=" * 70
    )


# =============================================================
# POINT D'ENTREE
# =============================================================

if __name__ == "__main__":

    main()

