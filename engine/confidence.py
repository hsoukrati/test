
from __future__ import annotations

import math
import re
from collections import Counter
from difflib import SequenceMatcher


# =============================================================
# CONFIGURATION
# =============================================================

MIN_WORD_LENGTH = 2

LOW_WORD_CONFIDENCE = 50.0
VERY_LOW_WORD_CONFIDENCE = 30.0

MIN_TEXT_LENGTH = 10
GOOD_TEXT_LENGTH = 50

MIN_WORD_COUNT = 3
GOOD_WORD_COUNT = 10

# Poids des différents critères
WEIGHT_OCR = 0.35
WEIGHT_TEXT = 0.20
WEIGHT_WORDS = 0.15
WEIGHT_LINES = 0.10
WEIGHT_VARIANTS = 0.20


# =============================================================
# OUTILS GENERAUX
# =============================================================

def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    """
    Limite une valeur entre minimum et maximum.
    """

    return max(
        minimum,
        min(
            maximum,
            float(value),
        ),
    )


def safe_float(
    value,
    default: float = 0.0,
) -> float:
    """
    Conversion sécurisée en float.
    """

    try:
        number = float(value)

        if not math.isfinite(number):
            return default

        return number

    except (
        TypeError,
        ValueError,
    ):
        return default


def normalize_text(
    text: str,
) -> str:
    """
    Normalise légèrement un texte pour les comparaisons.

    Cette fonction ne corrige PAS le texte OCR.
    Elle sert uniquement à mesurer sa cohérence.
    """

    text = str(
        text or ""
    ).strip().lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


# =============================================================
# CONFIANCE OCR MOYENNE
# =============================================================

def calculate_ocr_confidence(
    words: list[dict],
    fallback: float = 0.0,
) -> float:
    """
    Calcule la confiance moyenne des mots OCR.

    Tesseract retourne généralement une confiance
    comprise entre 0 et 100.

    Le résultat est normalisé entre 0 et 1.
    """

    confidences = []

    for word in words:

        text = str(
            word.get(
                "text",
                "",
            )
        ).strip()

        if not text:
            continue

        confidence = word.get(
            "confidence",
            word.get(
                "conf",
                None,
            ),
        )

        if confidence is None:
            continue

        confidence = safe_float(
            confidence,
            -1.0,
        )

        if confidence < 0:
            continue

        # Accepte également une confiance déjà
        # normalisée entre 0 et 1.
        if confidence <= 1.0:
            confidence *= 100.0

        confidence = clamp(
            confidence,
            0.0,
            100.0,
        )

        confidences.append(
            confidence
        )

    if not confidences:

        return clamp(
            fallback
        )

    return clamp(
        (
            sum(confidences)
            / len(confidences)
        )
        / 100.0
    )


# =============================================================
# QUALITE DES MOTS
# =============================================================

def calculate_word_quality(
    words: list[dict],
) -> tuple[float, list[dict]]:
    """
    Analyse la qualité des mots OCR.

    Détecte notamment :

    - mots très courts ;
    - confiance faible ;
    - caractères suspects ;
    - chaînes composées presque uniquement
      de symboles.
    """

    valid_words = []

    for word in words:

        text = str(
            word.get(
                "text",
                "",
            )
        ).strip()

        if text:
            valid_words.append(
                word
            )

    if not valid_words:

        return 0.0, []

    scores = []
    suspicious_words = []

    for word in valid_words:

        text = str(
            word.get(
                "text",
                "",
            )
        ).strip()

        score = 1.0
        reasons = []

        # -----------------------------------------------------
        # Confiance OCR
        # -----------------------------------------------------

        confidence = word.get(
            "confidence",
            word.get(
                "conf",
                None,
            ),
        )

        if confidence is not None:

            confidence = safe_float(
                confidence,
                0.0,
            )

            if confidence > 1.0:
                confidence_normalized = (
                    confidence / 100.0
                )
            else:
                confidence_normalized = confidence

            confidence_normalized = clamp(
                confidence_normalized
            )

            score *= (
                0.5
                + 0.5
                * confidence_normalized
            )

            if confidence_normalized < 0.50:

                reasons.append(
                    "confiance OCR faible"
                )

        # -----------------------------------------------------
        # Longueur
        # -----------------------------------------------------

        if len(text) == 1:

            # Un caractère seul peut être parfaitement
            # valide, donc pénalité légère seulement.
            score *= 0.90

            reasons.append(
                "mot très court"
            )

        # -----------------------------------------------------
        # Caractères alphanumériques
        # -----------------------------------------------------

        alphanumeric_count = len(
            re.findall(
                r"[A-Za-zÀ-ÿ0-9]",
                text,
            )
        )

        symbol_count = len(
            re.findall(
                r"[^A-Za-zÀ-ÿ0-9\s]",
                text,
            )
        )

        total_chars = len(
            text.replace(
                " ",
                "",
            )
        )

        if total_chars > 0:

            alpha_ratio = (
                alphanumeric_count
                / total_chars
            )

            symbol_ratio = (
                symbol_count
                / total_chars
            )

            if alpha_ratio < 0.30:

                score *= 0.60

                reasons.append(
                    "beaucoup de symboles"
                )

            elif symbol_ratio > 0.50:

                score *= 0.70

                reasons.append(
                    "forte proportion de symboles"
                )

        # -----------------------------------------------------
        # Répétition excessive
        # -----------------------------------------------------

        if len(text) >= 4:

            unique_chars = len(
                set(
                    text.lower()
                )
            )

            if unique_chars <= 1:

                score *= 0.50

                reasons.append(
                    "caractères répétitifs"
                )

        score = clamp(
            score
        )

        scores.append(
            score
        )

        if reasons:

            suspicious_words.append(
                {
                    "text": text,
                    "score": round(
                        score,
                        3,
                    ),
                    "reasons": reasons,
                }
            )

    quality = (
        sum(scores)
        / len(scores)
    )

    return (
        clamp(
            quality
        ),
        suspicious_words,
    )


# =============================================================
# QUALITE DU TEXTE
# =============================================================

def calculate_text_quality(
    text: str,
) -> float:
    """
    Calcule une estimation générale de la qualité
    du texte OCR.

    Cette fonction reste volontairement générique.
    """

    text = str(
        text or ""
    ).strip()

    if not text:

        return 0.0

    score = 0.0

    # ---------------------------------------------------------
    # Longueur
    # ---------------------------------------------------------

    length = len(text)

    if length < MIN_TEXT_LENGTH:

        length_score = (
            length
            / MIN_TEXT_LENGTH
        )

    elif length >= GOOD_TEXT_LENGTH:

        length_score = 1.0

    else:

        length_score = (
            0.50
            + (
                (
                    length
                    - MIN_TEXT_LENGTH
                )
                / (
                    GOOD_TEXT_LENGTH
                    - MIN_TEXT_LENGTH
                )
            )
            * 0.50
        )

    score += (
        0.35
        * clamp(
            length_score
        )
    )

    # ---------------------------------------------------------
    # Nombre de mots
    # ---------------------------------------------------------

    words = re.findall(
        r"\S+",
        text,
    )

    word_count = len(
        words
    )

    if word_count == 0:

        word_score = 0.0

    elif word_count >= GOOD_WORD_COUNT:

        word_score = 1.0

    else:

        word_score = clamp(
            word_count
            / GOOD_WORD_COUNT
        )

    score += (
        0.30
        * word_score
    )

    # ---------------------------------------------------------
    # Caractères alphanumériques
    # ---------------------------------------------------------

    alphanumeric = len(
        re.findall(
            r"[A-Za-zÀ-ÿ0-9]",
            text,
        )
    )

    non_space = len(
        re.sub(
            r"\s",
            "",
            text,
        )
    )

    if non_space:

        alpha_ratio = (
            alphanumeric
            / non_space
        )

    else:

        alpha_ratio = 0.0

    score += (
        0.20
        * clamp(
            alpha_ratio
        )
    )

    # ---------------------------------------------------------
    # Répétition excessive
    # ---------------------------------------------------------

    if len(text) >= 5:

        unique_ratio = (
            len(
                set(
                    text.lower()
                )
            )
            / len(text)
        )

        repetition_score = clamp(
            unique_ratio
            * 2.0
        )

    else:

        repetition_score = 0.5

    score += (
        0.15
        * repetition_score
    )

    return clamp(
        score
    )


# =============================================================
# QUALITE DES LIGNES
# =============================================================

def calculate_line_quality(
    lines: list,
) -> float:
    """
    Analyse la cohérence des lignes OCR.
    """

    if not lines:

        return 0.0

    valid_lines = []

    for line in lines:

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
                line or ""
            ).strip()

        if text:

            valid_lines.append(
                text
            )

    if not valid_lines:

        return 0.0

    scores = []

    for line in valid_lines:

        score = 1.0

        # Ligne extrêmement courte
        if len(line) == 1:

            score *= 0.80

        # Ligne avec beaucoup de symboles
        alphanumeric = len(
            re.findall(
                r"[A-Za-zÀ-ÿ0-9]",
                line,
            )
        )

        non_space = len(
            re.sub(
                r"\s",
                "",
                line,
            )
        )

        if non_space:

            ratio = (
                alphanumeric
                / non_space
            )

            if ratio < 0.30:

                score *= 0.60

        scores.append(
            score
        )

    return clamp(
        sum(scores)
        / len(scores)
    )


# =============================================================
# ACCORD ENTRE VARIANTES
# =============================================================

def calculate_variant_agreement(
    variant_results: dict[str, dict],
) -> float:
    """
    Mesure l'accord entre les différentes variantes
    de preprocessing.

    Plus les variantes produisent des textes similaires,
    plus le score est élevé.

    Si une seule variante est disponible,
    on retourne 0.5 car il n'existe pas de comparaison.
    """

    texts = []

    for result in variant_results.values():

        if not isinstance(
            result,
            dict,
        ):
            continue

        text = normalize_text(
            result.get(
                "text",
                "",
            )
        )

        if text:

            texts.append(
                text
            )

    if len(texts) <= 1:

        return 0.5

    similarities = []

    for index in range(
        len(texts)
    ):

        for other_index in range(
            index + 1,
            len(texts),
        ):

            similarity = SequenceMatcher(
                None,
                texts[index],
                texts[other_index],
            ).ratio()

            similarities.append(
                similarity
            )

    if not similarities:

        return 0.5

    return clamp(
        sum(similarities)
        / len(similarities)
    )


# =============================================================
# DETECTION DES MOTS FAIBLES
# =============================================================

def find_low_confidence_words(
    words: list[dict],
) -> list[dict]:
    """
    Retourne les mots dont la confiance OCR
    est faible.
    """

    low_confidence = []

    for index, word in enumerate(
        words
    ):

        text = str(
            word.get(
                "text",
                "",
            )
        ).strip()

        if not text:

            continue

        confidence = word.get(
            "confidence",
            word.get(
                "conf",
                None,
            ),
        )

        if confidence is None:

            continue

        confidence = safe_float(
            confidence,
            0.0,
        )

        if confidence <= 1.0:

            confidence *= 100.0

        if confidence < LOW_WORD_CONFIDENCE:

            low_confidence.append(
                {
                    "index": index,
                    "text": text,
                    "confidence": round(
                        confidence,
                        2,
                    ),
                    "very_low": (
                        confidence
                        < VERY_LOW_WORD_CONFIDENCE
                    ),
                }
            )

    return low_confidence


# =============================================================
# SCORE GLOBAL
# =============================================================

def calculate_global_confidence(
    ocr_confidence: float,
    text_quality: float,
    word_quality: float,
    line_quality: float,
    variant_agreement: float,
) -> float:
    """
    Calcule la confiance globale OCR.
    """

    score = (

        WEIGHT_OCR
        * ocr_confidence

        + WEIGHT_TEXT
        * text_quality

        + WEIGHT_WORDS
        * word_quality

        + WEIGHT_LINES
        * line_quality

        + WEIGHT_VARIANTS
        * variant_agreement
    )

    return clamp(
        score
    )


# =============================================================
# NIVEAU DE CONFIANCE
# =============================================================

def confidence_level(
    score: float,
) -> str:
    """
    Convertit un score numérique en niveau lisible.
    """

    score = clamp(
        score
    )

    if score >= 0.90:

        return "EXCELLENT"

    if score >= 0.75:

        return "BON"

    if score >= 0.55:

        return "MOYEN"

    if score >= 0.35:

        return "FAIBLE"

    return "TRES FAIBLE"


# =============================================================
# GENERATION DES ALERTES
# =============================================================

def generate_confidence_alerts(
    *,
    ocr_confidence: float,
    text_quality: float,
    word_quality: float,
    line_quality: float,
    variant_agreement: float,
    low_confidence_words: list[dict],
    suspicious_words: list[dict],
    global_confidence: float,
) -> list[str]:
    """
    Génère des alertes compréhensibles.
    """

    alerts = []

    # ---------------------------------------------------------
    # OCR
    # ---------------------------------------------------------

    if ocr_confidence < 0.50:

        alerts.append(
            "Confiance Tesseract faible."
        )

    elif ocr_confidence < 0.75:

        alerts.append(
            "Confiance Tesseract moyenne."
        )

    # ---------------------------------------------------------
    # Texte
    # ---------------------------------------------------------

    if text_quality < 0.40:

        alerts.append(
            "Qualité générale du texte faible."
        )

    # ---------------------------------------------------------
    # Mots
    # ---------------------------------------------------------

    if word_quality < 0.50:

        alerts.append(
            "Plusieurs mots OCR semblent suspects."
        )

    # ---------------------------------------------------------
    # Lignes
    # ---------------------------------------------------------

    if line_quality < 0.50:

        alerts.append(
            "La reconstruction des lignes est peu fiable."
        )

    # ---------------------------------------------------------
    # Variantes
    # ---------------------------------------------------------

    if variant_agreement < 0.40:

        alerts.append(
            "Les variantes de preprocessing donnent des résultats très différents."
        )

    elif variant_agreement < 0.65:

        alerts.append(
            "Accord moyen entre les variantes OCR."
        )

    # ---------------------------------------------------------
    # Mots faible confiance
    # ---------------------------------------------------------

    if low_confidence_words:

        alerts.append(
            f"{len(low_confidence_words)} "
            "mot(s) avec une confiance OCR faible."
        )

    # ---------------------------------------------------------
    # Mots suspects
    # ---------------------------------------------------------

    if suspicious_words:

        alerts.append(
            f"{len(suspicious_words)} "
            "mot(s) potentiellement incorrect(s)."
        )

    # ---------------------------------------------------------
    # Global
    # ---------------------------------------------------------

    if global_confidence < 0.35:

        alerts.append(
            "Résultat OCR globalement peu fiable."
        )

    return alerts


# =============================================================
# EVALUATION COMPLETE
# =============================================================

def evaluate_confidence(
    words: list[dict] | None = None,
    lines: list | None = None,
    text: str = "",
    variant_results: dict[str, dict] | None = None,
) -> dict:
    """
    Effectue une évaluation complète de la confiance OCR.

    Paramètres :

        words :
            mots OCR avec coordonnées et confiance.

        lines :
            lignes reconstruites.

        text :
            texte final.

        variant_results :
            résultats des différentes variantes.

    Retourne un dictionnaire contenant :

        confidence
        level
        components
        low_confidence_words
        suspicious_words
        alerts
    """

    words = (
        words
        if isinstance(
            words,
            list,
        )
        else []
    )

    lines = (
        lines
        if isinstance(
            lines,
            list,
        )
        else []
    )

    variant_results = (
        variant_results
        if isinstance(
            variant_results,
            dict,
        )
        else {}
    )

    # ---------------------------------------------------------
    # Composants
    # ---------------------------------------------------------

    ocr_confidence = calculate_ocr_confidence(
        words
    )

    text_quality = calculate_text_quality(
        text
    )

    word_quality, suspicious_words = (
        calculate_word_quality(
            words
        )
    )

    line_quality = calculate_line_quality(
        lines
    )

    variant_agreement = calculate_variant_agreement(
        variant_results
    )

    # ---------------------------------------------------------
    # Global
    # ---------------------------------------------------------

    global_confidence = (
        calculate_global_confidence(
            ocr_confidence=ocr_confidence,
            text_quality=text_quality,
            word_quality=word_quality,
            line_quality=line_quality,
            variant_agreement=variant_agreement,
        )
    )

    level = confidence_level(
        global_confidence
    )

    # ---------------------------------------------------------
    # Mots faible confiance
    # ---------------------------------------------------------

    low_confidence_words = (
        find_low_confidence_words(
            words
        )
    )

    # ---------------------------------------------------------
    # Alertes
    # ---------------------------------------------------------

    alerts = generate_confidence_alerts(
        ocr_confidence=ocr_confidence,
        text_quality=text_quality,
        word_quality=word_quality,
        line_quality=line_quality,
        variant_agreement=variant_agreement,
        low_confidence_words=low_confidence_words,
        suspicious_words=suspicious_words,
        global_confidence=global_confidence,
    )

    # ---------------------------------------------------------
    # Résultat
    # ---------------------------------------------------------

    return {
        "confidence": round(
            global_confidence,
            3,
        ),

        "level": level,

        "components": {
            "ocr_confidence": round(
                ocr_confidence,
                3,
            ),
            "text_quality": round(
                text_quality,
                3,
            ),
            "word_quality": round(
                word_quality,
                3,
            ),
            "line_quality": round(
                line_quality,
                3,
            ),
            "variant_agreement": round(
                variant_agreement,
                3,
            ),
        },

        "statistics": {
            "word_count": len(
                [
                    word
                    for word in words
                    if str(
                        word.get(
                            "text",
                            "",
                        )
                    ).strip()
                ]
            ),

            "line_count": len(
                [
                    line
                    for line in lines
                    if (
                        str(
                            line.get(
                                "text",
                                "",
                            )
                        ).strip()
                        if isinstance(
                            line,
                            dict,
                        )
                        else str(
                            line or ""
                        ).strip()
                    )
                ]
            ),

            "character_count": len(
                str(
                    text or ""
                )
            ),
        },

        "low_confidence_words":
            low_confidence_words,

        "suspicious_words":
            suspicious_words,

        "alerts":
            alerts,
    }


# =============================================================
# AFFICHAGE RESULTAT
# =============================================================

def print_confidence_report(
    result: dict,
) -> None:
    """
    Affiche le rapport de confiance.
    """

    print(
        "\n"
        + "=" * 70
    )

    print(
        "EVALUATION CONFIANCE OCR"
    )

    print(
        "=" * 70
    )

    confidence = safe_float(
        result.get(
            "confidence",
            0.0,
        )
    )

    level = result.get(
        "level",
        "INCONNU",
    )

    print(
        f"\nConfiance globale : "
        f"{confidence:.3f}"
    )

    print(
        f"Niveau            : "
        f"{level}"
    )

    # ---------------------------------------------------------
    # Composants
    # ---------------------------------------------------------

    components = result.get(
        "components",
        {},
    )

    print(
        "\nComposants :"
    )

    print(
        f"  Confiance OCR       : "
        f"{components.get('ocr_confidence', 0.0):.3f}"
    )

    print(
        f"  Qualité texte       : "
        f"{components.get('text_quality', 0.0):.3f}"
    )

    print(
        f"  Qualité mots        : "
        f"{components.get('word_quality', 0.0):.3f}"
    )

    print(
        f"  Qualité lignes      : "
        f"{components.get('line_quality', 0.0):.3f}"
    )

    print(
        f"  Accord variantes    : "
        f"{components.get('variant_agreement', 0.0):.3f}"
    )

    # ---------------------------------------------------------
    # Statistiques
    # ---------------------------------------------------------

    statistics = result.get(
        "statistics",
        {},
    )

    print(
        "\nStatistiques :"
    )

    print(
        f"  Mots                : "
        f"{statistics.get('word_count', 0)}"
    )

    print(
        f"  Lignes              : "
        f"{statistics.get('line_count', 0)}"
    )

    print(
        f"  Caractères          : "
        f"{statistics.get('character_count', 0)}"
    )

    # ---------------------------------------------------------
    # Mots faibles
    # ---------------------------------------------------------

    low_words = result.get(
        "low_confidence_words",
        [],
    )

    print(
        "\nMots à faible confiance :"
    )

    if not low_words:

        print(
            "  Aucun."
        )

    else:

        for item in low_words:

            print(
                f"  [{item['index']:04d}] "
                f"{item['text']:<25} "
                f"conf={item['confidence']:.1f}"
            )

    # ---------------------------------------------------------
    # Mots suspects
    # ---------------------------------------------------------

    suspicious = result.get(
        "suspicious_words",
        [],
    )

    print(
        "\nMots potentiellement suspects :"
    )

    if not suspicious:

        print(
            "  Aucun."
        )

    else:

        for item in suspicious:

            reasons = ", ".join(
                item.get(
                    "reasons",
                    [],
                )
            )

            print(
                f"  {item.get('text', ''):<25} "
                f"score={item.get('score', 0.0):.3f} "
                f"| {reasons}"
            )

    # ---------------------------------------------------------
    # Alertes
    # ---------------------------------------------------------

    alerts = result.get(
        "alerts",
        [],
    )

    print(
        "\nAlertes :"
    )

    if not alerts:

        print(
            "  Aucune alerte."
        )

    else:

        for alert in alerts:

            print(
                f"  - {alert}"
            )

    print(
        "\n"
        + "=" * 70
    )


# =============================================================
# TEST DIRECT
# =============================================================

def main() -> None:

    print(
        "=" * 70
    )

    print(
        "TEST CONFIDENCE OCR"
    )

    print(
        "=" * 70
    )

    # ---------------------------------------------------------
    # Données OCR de test
    # ---------------------------------------------------------

    words = [
        {
            "text": "Fiche",
            "x": 100,
            "y": 50,
            "width": 80,
            "height": 25,
            "confidence": 95,
        },
        {
            "text": "technique",
            "x": 190,
            "y": 50,
            "width": 120,
            "height": 25,
            "confidence": 94,
        },
        {
            "text": "Ref:",
            "x": 100,
            "y": 100,
            "width": 60,
            "height": 25,
            "confidence": 92,
        },
        {
            "text": "ABC123",
            "x": 170,
            "y": 100,
            "width": 100,
            "height": 25,
            "confidence": 96,
        },
        {
            "text": "Client:",
            "x": 100,
            "y": 140,
            "width": 70,
            "height": 25,
            "confidence": 91,
        },
        {
            "text": "Renault",
            "x": 180,
            "y": 140,
            "width": 100,
            "height": 25,
            "confidence": 95,
        },
        {
            "text": "Date:",
            "x": 100,
            "y": 180,
            "width": 65,
            "height": 25,
            "confidence": 93,
        },
        {
            "text": "31/08/2026",
            "x": 175,
            "y": 180,
            "width": 130,
            "height": 25,
            "confidence": 94,
        },
    ]

    lines = [
        {
            "text": "Fiche technique",
        },
        {
            "text": "Ref: ABC123",
        },
        {
            "text": "Client: Renault",
        },
        {
            "text": "Date: 31/08/2026",
        },
    ]

    text = "\n".join(
        line["text"]
        for line in lines
    )

    # ---------------------------------------------------------
    # Résultats de variantes
    # ---------------------------------------------------------

    variant_results = {

        "original": {
            "text": text,
        },

        "grayscale": {
            "text": text,
        },

        "binary": {
            "text":
                "Fiche technique\n"
                "Ref: ABC123\n"
                "Client: Renault",
        },

        "adaptive": {
            "text":
                text,
        },
    }

    # ---------------------------------------------------------
    # Evaluation
    # ---------------------------------------------------------

    result = evaluate_confidence(
        words=words,
        lines=lines,
        text=text,
        variant_results=variant_results,
    )

    # ---------------------------------------------------------
    # Affichage
    # ---------------------------------------------------------

    print_confidence_report(
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


# =============================================================
# POINT D'ENTREE
# =============================================================

if __name__ == "__main__":

    main()

