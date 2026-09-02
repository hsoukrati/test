from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re


# =============================================================
# TYPES DE DOCUMENTS
# =============================================================

DOCUMENT_TYPES = (
    "empty",
    "text",
    "form",
    "table",
    "mixed",
)


# =============================================================
# RESULTAT CLASSIFICATION
# =============================================================

@dataclass
class DocumentClassification:
    """
    Résultat de la classification structurelle
    d'un document OCR.

    IMPORTANT :
    Cette classification ne fait appel à aucune IA.

    Elle utilise uniquement :
        - mots OCR
        - lignes
        - coordonnées
        - longueur du texte
        - séparateurs
        - alignements
    """

    document_type: str

    confidence: float

    scores: dict[str, float]

    statistics: dict[str, Any]

    reasons: list[str]


# =============================================================
# OUTILS GENERAUX
# =============================================================

def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:
        return float(value)

    except (TypeError, ValueError):

        return default


def clean_text(
    text: Any,
) -> str:

    return str(
        text or ""
    ).strip()


# =============================================================
# EXTRACTION DES MOTS VALIDES
# =============================================================

def get_valid_words(
    words: list[dict],
) -> list[dict]:

    result = []

    for word in words:

        text = clean_text(
            word.get(
                "text",
                "",
            )
        )

        if not text:
            continue

        result.append(word)

    return result


# =============================================================
# EXTRACTION DES LIGNES
# =============================================================

def get_line_texts(
    lines: list[Any],
) -> list[str]:

    result = []

    for line in lines:

        if isinstance(line, dict):

            text = clean_text(
                line.get(
                    "text",
                    "",
                )
            )

        else:

            text = clean_text(
                line
            )

        if text:

            result.append(text)

    return result


# =============================================================
# STATISTIQUES
# =============================================================

def calculate_statistics(
    words: list[dict],
    lines: list[Any],
) -> dict[str, Any]:

    valid_words = get_valid_words(
        words
    )

    line_texts = get_line_texts(
        lines
    )

    word_count = len(
        valid_words
    )

    line_count = len(
        line_texts
    )

    character_count = sum(
        len(
            clean_text(
                word.get(
                    "text",
                    "",
                )
            )
        )
        for word in valid_words
    )

    line_lengths = [
        len(text)
        for text in line_texts
    ]

    average_line_length = (
        sum(line_lengths)
        / len(line_lengths)
        if line_lengths
        else 0.0
    )

    long_lines = sum(
        1
        for length in line_lengths
        if length >= 40
    )

    short_lines = sum(
        1
        for length in line_lengths
        if 1 <= length <= 25
    )

    colon_lines = sum(
        1
        for text in line_texts
        if ":" in text
    )

    separator_lines = sum(
        1
        for text in line_texts
        if re.search(
            r"[-_=]{3,}",
            text,
        )
    )

    return {
        "word_count": word_count,
        "line_count": line_count,
        "character_count": character_count,
        "average_line_length":
            average_line_length,
        "long_lines":
            long_lines,
        "short_lines":
            short_lines,
        "colon_lines":
            colon_lines,
        "separator_lines":
            separator_lines,
    }


# =============================================================
# DETECTION FORMULAIRE
# =============================================================

def calculate_form_score(
    statistics: dict[str, Any],
) -> float:

    line_count = statistics[
        "line_count"
    ]

    if line_count == 0:

        return 0.0

    colon_lines = statistics[
        "colon_lines"
    ]

    short_lines = statistics[
        "short_lines"
    ]

    colon_ratio = (
        colon_lines
        / line_count
    )

    short_ratio = (
        short_lines
        / line_count
    )

    score = (
        colon_ratio * 0.65
        + short_ratio * 0.35
    )

    return min(
        max(score, 0.0),
        1.0,
    )


# =============================================================
# DETECTION TEXTE LIBRE
# =============================================================

def calculate_text_score(
    statistics: dict[str, Any],
) -> float:

    line_count = statistics[
        "line_count"
    ]

    if line_count == 0:

        return 0.0

    long_lines = statistics[
        "long_lines"
    ]

    average_length = statistics[
        "average_line_length"
    ]

    long_ratio = (
        long_lines
        / line_count
    )

    length_score = min(
        average_length / 80.0,
        1.0,
    )

    score = (
        long_ratio * 0.65
        + length_score * 0.35
    )

    return min(
        max(score, 0.0),
        1.0,
    )


# =============================================================
# DETECTION TABLEAU
# =============================================================

def calculate_table_score(
    words: list[dict],
) -> float:

    valid_words = get_valid_words(
        words
    )

    if len(valid_words) < 4:

        return 0.0

    # ---------------------------------------------------------
    # Centres X
    # ---------------------------------------------------------

    x_centers = []

    for word in valid_words:

        x = safe_float(
            word.get(
                "x",
                0,
            )
        )

        width = safe_float(
            word.get(
                "width",
                0,
            )
        )

        x_centers.append(
            x + width / 2
        )

    # ---------------------------------------------------------
    # Recherche d'alignements verticaux
    # ---------------------------------------------------------

    aligned_pairs = 0

    tolerance = 20.0

    for i in range(
        len(x_centers)
    ):

        for j in range(
            i + 1,
            len(x_centers)
        ):

            if abs(
                x_centers[i]
                - x_centers[j]
            ) <= tolerance:

                aligned_pairs += 1

    total_pairs = (
        len(x_centers)
        * (len(x_centers) - 1)
        / 2
    )

    if total_pairs <= 0:

        return 0.0

    alignment_ratio = (
        aligned_pairs
        / total_pairs
    )

    # ---------------------------------------------------------
    # Score limité
    # ---------------------------------------------------------

    return min(
        max(
            alignment_ratio * 2.0,
            0.0,
        ),
        1.0,
    )


# =============================================================
# DETECTION DOCUMENT VIDE
# =============================================================

def calculate_empty_score(
    statistics: dict[str, Any],
) -> float:

    word_count = statistics[
        "word_count"
    ]

    character_count = statistics[
        "character_count"
    ]

    if word_count == 0:

        return 1.0

    if character_count < 5:

        return 0.8

    if word_count < 2:

        return 0.5

    return 0.0


# =============================================================
# DETECTION MIXTE
# =============================================================

def calculate_mixed_score(
    scores: dict[str, float],
) -> float:

    form_score = scores[
        "form"
    ]

    text_score = scores[
        "text"
    ]

    table_score = scores[
        "table"
    ]

    high_scores = sum(
        1
        for score in (
            form_score,
            text_score,
            table_score,
        )
        if score >= 0.35
    )

    if high_scores >= 2:

        return min(
            1.0,
            (
                form_score
                + text_score
                + table_score
            ) / 2.0,
        )

    return 0.0


# =============================================================
# RAISONS
# =============================================================

def build_reasons(
    statistics: dict[str, Any],
    scores: dict[str, float],
    document_type: str,
) -> list[str]:

    reasons = []

    if document_type == "empty":

        reasons.append(
            "Très peu de texte OCR détecté."
        )

    if document_type == "text":

        if statistics["long_lines"] > 0:

            reasons.append(
                "Présence de lignes relativement longues."
            )

        if scores["text"] >= 0.5:

            reasons.append(
                "Structure compatible avec du texte libre."
            )

    if document_type == "form":

        if statistics["colon_lines"] > 0:

            reasons.append(
                "Présence de lignes contenant des labels ':' ."
            )

        if statistics["short_lines"] > 0:

            reasons.append(
                "Présence de nombreuses lignes courtes."
            )

    if document_type == "table":

        reasons.append(
            "Alignements horizontaux/verticaux détectés."
        )

    if document_type == "mixed":

        reasons.append(
            "Plusieurs structures documentaires sont présentes."
        )

    if not reasons:

        reasons.append(
            "Classification basée sur la structure OCR."
        )

    return reasons


# =============================================================
# CLASSIFICATION
# =============================================================

def classify_document(
    words: list[dict],
    lines: list[Any],
) -> DocumentClassification:

    statistics = calculate_statistics(
        words,
        lines,
    )

    # ---------------------------------------------------------
    # Scores
    # ---------------------------------------------------------

    scores = {

        "empty":
            calculate_empty_score(
                statistics
            ),

        "text":
            calculate_text_score(
                statistics
            ),

        "form":
            calculate_form_score(
                statistics
            ),

        "table":
            calculate_table_score(
                words
            ),
    }

    scores["mixed"] = (
        calculate_mixed_score(
            scores
        )
    )

    # ---------------------------------------------------------
    # Cas vide
    # ---------------------------------------------------------

    if scores["empty"] >= 0.8:

        document_type = "empty"

    else:

        # -----------------------------------------------------
        # Recherche meilleur score
        # -----------------------------------------------------

        candidates = {
            key: value
            for key, value
            in scores.items()
            if key != "empty"
        }

        document_type = max(
            candidates,
            key=candidates.get,
        )

    # ---------------------------------------------------------
    # Confiance
    # ---------------------------------------------------------

    confidence = scores[
        document_type
    ]

    confidence = min(
        max(
            float(confidence),
            0.0,
        ),
        1.0,
    )

    # ---------------------------------------------------------
    # Raisons
    # ---------------------------------------------------------

    reasons = build_reasons(
        statistics,
        scores,
        document_type,
    )

    return DocumentClassification(
        document_type=document_type,
        confidence=confidence,
        scores=scores,
        statistics=statistics,
        reasons=reasons,
    )


# =============================================================
# AFFICHAGE
# =============================================================

def print_classification(
    result: DocumentClassification,
) -> None:

    print(
        "\n"
        + "=" * 70
    )

    print(
        "CLASSIFICATION DU DOCUMENT"
    )

    print(
        "=" * 70
    )

    print(
        f"Type : "
        f"{result.document_type}"
    )

    print(
        f"Confiance : "
        f"{result.confidence:.3f}"
    )

    print(
        "\nScores :"
    )

    for name, score in result.scores.items():

        print(
            f"  {name:<10} : "
            f"{score:.3f}"
        )

    print(
        "\nStatistiques :"
    )

    for name, value in result.statistics.items():

        print(
            f"  {name:<25} : "
            f"{value}"
        )

    print(
        "\nRaisons :"
    )

    for reason in result.reasons:

        print(
            f"  - {reason}"
        )


# =============================================================
# TEST DIRECT
# =============================================================

if __name__ == "__main__":

    print(
        "=" * 70
    )

    print(
        "TEST CLASSIFICATION DOCUMENT"
    )

    print(
        "=" * 70
    )

    # ---------------------------------------------------------
    # Exemple 1 : formulaire
    # ---------------------------------------------------------

    example_words = [

        {
            "text": "Ref:",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 20,
        },

        {
            "text": "ABC123",
            "x": 180,
            "y": 100,
            "width": 80,
            "height": 20,
        },

        {
            "text": "Client:",
            "x": 100,
            "y": 140,
            "width": 60,
            "height": 20,
        },

        {
            "text": "Renault",
            "x": 180,
            "y": 140,
            "width": 80,
            "height": 20,
        },

        {
            "text": "Atelier:",
            "x": 100,
            "y": 180,
            "width": 70,
            "height": 20,
        },

        {
            "text": "Découpe",
            "x": 180,
            "y": 180,
            "width": 80,
            "height": 20,
        },
    ]

    example_lines = [

        {
            "text": "Ref: ABC123"
        },

        {
            "text": "Client: Renault"
        },

        {
            "text": "Atelier: Découpe"
        },
    ]

    result = classify_document(
        example_words,
        example_lines,
    )

    print_classification(
        result
    )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "TEST TERMINE"
    )

    print(
        "=" * 70
    )