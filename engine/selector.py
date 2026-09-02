
from __future__ import annotations

import re
from typing import Any


# =============================================================
# CONFIGURATION
# =============================================================

# Poids utilisés pour calculer le score final.
#
# Le but est de privilégier un texte :
# - lisible
# - suffisamment complet
# - avec une bonne confiance OCR
#
# Aucun champ métier n'est utilisé ici.
# Le sélecteur reste donc totalement générique.

WEIGHT_CONFIDENCE = 0.30
WEIGHT_WORDS = 0.25
WEIGHT_CHARACTERS = 0.20
WEIGHT_LINES = 0.10
WEIGHT_TEXT_QUALITY = 0.15


# =============================================================
# OUTILS
# =============================================================

def clean_text(text: Any) -> str:
    """
    Nettoie légèrement le texte OCR.

    Ne modifie pas agressivement le contenu,
    car le pipeline doit rester générique.
    """

    if text is None:
        return ""

    text = str(text)

    # Espaces multiples
    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    # Lignes vides multiples
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def get_words(
    result: dict,
) -> list[dict]:
    """
    Retourne les mots OCR valides.
    """

    words = result.get(
        "words",
        [],
    )

    if not isinstance(words, list):
        return []

    valid_words = []

    for word in words:

        if not isinstance(word, dict):
            continue

        text = str(
            word.get(
                "text",
                "",
            )
        ).strip()

        if not text:
            continue

        valid_words.append(word)

    return valid_words


def get_text(
    result: dict,
) -> str:
    """
    Retourne le texte OCR nettoyé.
    """

    return clean_text(
        result.get(
            "text",
            "",
        )
    )


# =============================================================
# CONFIANCE OCR
# =============================================================

def normalize_confidence(
    confidence: Any,
) -> float:
    """
    Normalise une confiance OCR vers [0, 1].

    Accepte :

        0.91
        91
        "91"
        "0.91"
    """

    try:

        value = float(
            confidence
        )

    except (
        TypeError,
        ValueError,
    ):

        return 0.0

    # Tesseract retourne souvent une
    # confiance sur 100.
    if value > 1.0:

        value /= 100.0

    return max(
        0.0,
        min(
            1.0,
            value,
        ),
    )


def calculate_word_confidence(
    words: list[dict],
) -> float:
    """
    Calcule la confiance moyenne des mots OCR.

    Cette valeur permet de ne pas dépendre
    uniquement de la confiance globale.
    """

    confidences = []

    for word in words:

        value = word.get(
            "confidence",
            word.get(
                "conf",
                None,
            ),
        )

        if value is None:
            continue

        try:

            value = float(value)

        except (
            TypeError,
            ValueError,
        ):

            continue

        if value < 0:
            continue

        if value > 1:
            value /= 100.0

        confidences.append(
            max(
                0.0,
                min(
                    1.0,
                    value,
                ),
            )
        )

    if not confidences:
        return 0.0

    return sum(confidences) / len(
        confidences
    )


# =============================================================
# QUALITE DU TEXTE
# =============================================================

def calculate_text_quality(
    text: str,
    words: list[dict],
) -> float:
    """
    Calcule une qualité générale du texte OCR.

    Cette fonction ne connaît aucun domaine métier.

    Elle recherche notamment :

    - texte vide
    - texte trop court
    - caractères étranges
    - mots normaux
    - présence de lettres/chiffres
    """

    text = clean_text(
        text
    )

    if not text:
        return 0.0

    if not words:
        return 0.05

    score = 0.0

    # ---------------------------------------------------------
    # 1. Présence de contenu
    # ---------------------------------------------------------

    if len(text) >= 5:
        score += 0.15

    if len(text) >= 10:
        score += 0.10

    if len(text) >= 30:
        score += 0.10

    if len(text) >= 80:
        score += 0.05

    # ---------------------------------------------------------
    # 2. Présence lettres/chiffres
    # ---------------------------------------------------------

    alphanumeric = re.findall(
        r"[A-Za-zÀ-ÿ0-9]",
        text,
    )

    if alphanumeric:
        score += 0.15

    # ---------------------------------------------------------
    # 3. Ratio caractères alphanumériques
    # ---------------------------------------------------------

    useful_chars = sum(
        1
        for char in text
        if char.isalnum()
        or char.isspace()
    )

    if len(text) > 0:

        ratio = (
            useful_chars
            / len(text)
        )

        score += 0.15 * ratio

    # ---------------------------------------------------------
    # 4. Qualité des mots
    # ---------------------------------------------------------

    valid_word_count = 0

    for word in words:

        word_text = str(
            word.get(
                "text",
                "",
            )
        ).strip()

        if not word_text:
            continue

        # Au moins une lettre ou un chiffre
        if re.search(
            r"[A-Za-zÀ-ÿ0-9]",
            word_text,
        ):

            valid_word_count += 1

    if valid_word_count > 0:

        word_ratio = (
            valid_word_count
            / len(words)
        )

        score += 0.20 * word_ratio

    # ---------------------------------------------------------
    # 5. Longueur raisonnable des mots
    # ---------------------------------------------------------

    normal_words = []

    for word in words:

        word_text = str(
            word.get(
                "text",
                "",
            )
        ).strip()

        if not word_text:
            continue

        if 1 <= len(word_text) <= 40:

            normal_words.append(
                word_text
            )

    if normal_words:

        score += 0.10

    return max(
        0.0,
        min(
            1.0,
            score,
        ),
    )


# =============================================================
# SCORE DU NOMBRE DE MOTS
# =============================================================

def calculate_word_score(
    word_count: int,
    all_counts: list[int],
) -> float:
    """
    Calcule un score relatif basé sur le nombre de mots.

    La variante contenant le plus de mots utiles
    obtient un meilleur score.

    Une variante vide est fortement pénalisée.
    """

    if word_count <= 0:
        return 0.0

    positive_counts = [
        count
        for count in all_counts
        if count > 0
    ]

    if not positive_counts:
        return 0.0

    maximum = max(
        positive_counts
    )

    if maximum <= 0:
        return 0.0

    score = (
        word_count
        / maximum
    )

    return max(
        0.0,
        min(
            1.0,
            score,
        ),
    )


# =============================================================
# SCORE DU NOMBRE DE CARACTERES
# =============================================================

def calculate_character_score(
    character_count: int,
    all_counts: list[int],
) -> float:
    """
    Score relatif basé sur le nombre
    de caractères détectés.
    """

    if character_count <= 0:
        return 0.0

    positive_counts = [
        count
        for count in all_counts
        if count > 0
    ]

    if not positive_counts:
        return 0.0

    maximum = max(
        positive_counts
    )

    if maximum <= 0:
        return 0.0

    score = (
        character_count
        / maximum
    )

    return max(
        0.0,
        min(
            1.0,
            score,
        ),
    )


# =============================================================
# SCORE DU NOMBRE DE LIGNES
# =============================================================

def calculate_line_score(
    line_count: int,
    all_counts: list[int],
) -> float:
    """
    Score relatif basé sur le nombre de lignes.
    """

    if line_count <= 0:
        return 0.0

    positive_counts = [
        count
        for count in all_counts
        if count > 0
    ]

    if not positive_counts:
        return 0.0

    maximum = max(
        positive_counts
    )

    if maximum <= 0:
        return 0.0

    score = (
        line_count
        / maximum
    )

    return max(
        0.0,
        min(
            1.0,
            score,
        ),
    )


# =============================================================
# SCORE FINAL
# =============================================================

def calculate_variant_score(
    confidence: float,
    word_score: float,
    character_score: float,
    line_score: float,
    text_quality: float,
) -> float:
    """
    Calcule le score final d'une variante.
    """

    score = (

        WEIGHT_CONFIDENCE
        * confidence

        +

        WEIGHT_WORDS
        * word_score

        +

        WEIGHT_CHARACTERS
        * character_score

        +

        WEIGHT_LINES
        * line_score

        +

        WEIGHT_TEXT_QUALITY
        * text_quality
    )

    return max(
        0.0,
        min(
            1.0,
            score,
        ),
    )


# =============================================================
# SELECTION PRINCIPALE
# =============================================================

def select_best_variant(
    results: dict[str, dict],
    expected_fields: list[str] | None = None,
) -> dict:
    """
    Sélectionne automatiquement la meilleure variante OCR.

    IMPORTANT :

    expected_fields est conservé pour compatibilité
    avec l'ancien pipeline.

    Mais le sélecteur générique ne dépend PAS
    de champs métier.

    Il fonctionne donc pour :

        facture
        formulaire
        plan
        fiche industrielle
        contrat
        tableau
        courrier
        document administratif
        etc.
    """

    if not results:

        return {
            "selected_variant": "",
            "score": 0.0,
            "confidence": 0.0,
            "fields_found": 0,
            "total_fields": 0,
            "fields": {},
            "all_results": [],
        }

    # ---------------------------------------------------------
    # Collecte des statistiques
    # ---------------------------------------------------------

    statistics = {}

    all_word_counts = []
    all_character_counts = []
    all_line_counts = []

    for variant_name, result in results.items():

        if not isinstance(
            result,
            dict,
        ):
            continue

        words = get_words(
            result
        )

        text = get_text(
            result
        )

        lines = result.get(
            "lines",
            [],
        )

        if not isinstance(
            lines,
            list,
        ):
            lines = []

        word_count = len(
            words
        )

        character_count = len(
            text
        )

        line_count = len(
            [
                line
                for line in lines
                if str(
                    line.get(
                        "text",
                        "",
                    )
                    if isinstance(
                        line,
                        dict,
                    )
                    else line
                ).strip()
            ]
        )

        global_confidence = normalize_confidence(
            result.get(
                "confidence",
                0.0,
            )
        )

        word_confidence = calculate_word_confidence(
            words
        )

        # -----------------------------------------------------
        # Combinaison confiance globale + mots
        # -----------------------------------------------------

        if word_confidence > 0:

            confidence = (
                0.50
                * global_confidence
                +
                0.50
                * word_confidence
            )

        else:

            confidence = (
                global_confidence
            )

        text_quality = calculate_text_quality(
            text,
            words,
        )

        statistics[
            variant_name
        ] = {

            "words":
                words,

            "text":
                text,

            "lines":
                lines,

            "word_count":
                word_count,

            "character_count":
                character_count,

            "line_count":
                line_count,

            "confidence":
                confidence,

            "text_quality":
                text_quality,
        }

        all_word_counts.append(
            word_count
        )

        all_character_counts.append(
            character_count
        )

        all_line_counts.append(
            line_count
        )

    # ---------------------------------------------------------
    # Aucun résultat exploitable
    # ---------------------------------------------------------

    if not statistics:

        return {
            "selected_variant": "",
            "score": 0.0,
            "confidence": 0.0,
            "fields_found": 0,
            "total_fields": len(
                expected_fields or []
            ),
            "fields": {},
            "all_results": [],
        }

    # ---------------------------------------------------------
    # Calcul des scores
    # ---------------------------------------------------------

    scored_results = []

    for variant_name, stats in statistics.items():

        word_score = calculate_word_score(
            stats["word_count"],
            all_word_counts,
        )

        character_score = calculate_character_score(
            stats["character_count"],
            all_character_counts,
        )

        line_score = calculate_line_score(
            stats["line_count"],
            all_line_counts,
        )

        score = calculate_variant_score(
            confidence=stats["confidence"],
            word_score=word_score,
            character_score=character_score,
            line_score=line_score,
            text_quality=stats["text_quality"],
        )

        # -----------------------------------------------------
        # Forte pénalité pour les résultats très pauvres
        # -----------------------------------------------------

        if stats["word_count"] == 0:

            score *= 0.20

        elif stats["word_count"] <= 2:

            score *= 0.70

        scored_results.append(
            {
                "variant":
                    variant_name,

                "confidence":
                    stats["confidence"],

                "fields_found":
                    0,

                "total_fields":
                    len(
                        expected_fields or []
                    ),

                "text_quality":
                    stats["text_quality"],

                "word_count":
                    stats["word_count"],

                "character_count":
                    stats["character_count"],

                "line_count":
                    stats["line_count"],

                "word_score":
                    word_score,

                "character_score":
                    character_score,

                "line_score":
                    line_score,

                "score":
                    score,
            }
        )

    # ---------------------------------------------------------
    # Tri
    # ---------------------------------------------------------

    scored_results.sort(
        key=lambda item: (
            item["score"],
            item["word_count"],
            item["character_count"],
        ),
        reverse=True,
    )

    best = scored_results[0]

    selected_variant = best[
        "variant"
    ]

    selected_result = statistics[
        selected_variant
    ]

    # ---------------------------------------------------------
    # Champs
    #
    # Compatibilité avec les anciennes versions.
    # Le pipeline générique n'en impose aucun.
    # ---------------------------------------------------------

    fields = selected_result.get(
        "fields",
        {}
    )

    if not isinstance(
        fields,
        dict,
    ):
        fields = {}

    fields_found = 0

    if expected_fields:

        fields_found = sum(
            1
            for field in expected_fields
            if fields.get(
                field,
                "",
            )
        )

    # ---------------------------------------------------------
    # Résultat final
    # ---------------------------------------------------------

    return {

        "selected_variant":
            selected_variant,

        "score":
            best["score"],

        "confidence":
            selected_result[
                "confidence"
            ],

        "fields_found":
            fields_found,

        "total_fields":
            len(
                expected_fields or []
            ),

        "fields":
            fields,

        "text":
            selected_result[
                "text"
            ],

        "words":
            selected_result[
                "words"
            ],

        "lines":
            selected_result[
                "lines"
            ],

        "all_results":
            scored_results,
    }


# =============================================================
# TEST DIRECT
# =============================================================

if __name__ == "__main__":

    print("=" * 70)

    print(
        "TEST SELECTOR OCR"
    )

    print("=" * 70)

    test_results = {

        "original": {
            "confidence": 0.849,
            "text": (
                "Ref SAP M400028D01 "
                "Ref BE ABC123 "
                "Designation piece "
                "LONGERON AR D "
                "Atelier A1"
            ),
            "words": [
                {"text": "Ref", "confidence": 90},
                {"text": "SAP", "confidence": 90},
                {"text": "M400028D01", "confidence": 88},
                {"text": "Ref", "confidence": 90},
                {"text": "BE", "confidence": 90},
                {"text": "ABC123", "confidence": 85},
                {"text": "Designation", "confidence": 88},
                {"text": "piece", "confidence": 90},
                {"text": "LONGERON", "confidence": 80},
                {"text": "AR", "confidence": 90},
                {"text": "D", "confidence": 90},
                {"text": "Atelier", "confidence": 90},
                {"text": "A1", "confidence": 90},
            ],
            "lines": [
                {"text": "Ref SAP M400028D01"},
                {"text": "Ref BE ABC123"},
                {"text": "Designation piece LONGERON AR D"},
                {"text": "Atelier A1"},
            ],
        },

        "binary": {
            "confidence": 0.908,
            "text": "Ref SAP M400028D01",
            "words": [
                {"text": "Ref", "confidence": 91},
                {"text": "SAP", "confidence": 92},
                {"text": "M400028D01", "confidence": 91},
            ],
            "lines": [
                {"text": "Ref SAP M400028D01"},
            ],
        },

        "denoised": {
            "confidence": 0.910,
            "text": "DE COUPE LASER",
            "words": [
                {"text": "DE", "confidence": 91},
                {"text": "COUPE", "confidence": 91},
                {"text": "LASER", "confidence": 91},
            ],
            "lines": [
                {"text": "DE COUPE LASER"},
            ],
        },
    }

    selected = select_best_variant(
        test_results,
        [],
    )

    print(
        "\nRésultats :"
    )

    for result in selected[
        "all_results"
    ]:

        print(
            f"\n"
            f"Variante : "
            f"{result['variant']}"
        )

        print(
            f"  Confiance       : "
            f"{result['confidence']:.3f}"
        )

        print(
            f"  Mots            : "
            f"{result['word_count']}"
        )

        print(
            f"  Caractères      : "
            f"{result['character_count']}"
        )

        print(
            f"  Lignes          : "
            f"{result['line_count']}"
        )

        print(
            f"  Qualité texte   : "
            f"{result['text_quality']:.3f}"
        )

        print(
            f"  Score final     : "
            f"{result['score']:.3f}"
        )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "MEILLEURE VARIANTE"
    )

    print(
        "=" * 70
    )

    print(
        f"Variante : "
        f"{selected['selected_variant']}"
    )

    print(
        f"Score : "
        f"{selected['score']:.3f}"
    )

    print(
        f"Confiance : "
        f"{selected['confidence']:.3f}"
    )

    print(
        "\nTEST TERMINE"
    )

