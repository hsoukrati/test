
from __future__ import annotations

import re
import unicodedata
from collections import Counter


# =============================================================
# CONFIGURATION
# =============================================================

# Espaces Unicode considérés comme des espaces normaux.
UNICODE_SPACES = {
    "\u00a0",  # espace insécable
    "\u2000",
    "\u2001",
    "\u2002",
    "\u2003",
    "\u2004",
    "\u2005",
    "\u2006",
    "\u2007",
    "\u2008",
    "\u2009",
    "\u200a",
    "\u202f",  # espace fine insécable
    "\u205f",
    "\u3000",
}


# =============================================================
# NORMALISATION UNICODE
# =============================================================

def normalize_unicode(text: str) -> str:
    """
    Normalise les caractères Unicode.

    Cette fonction ne supprime pas les accents.

    Exemple :

        texte OCR avec espaces Unicode
        ->
        texte avec espaces standards
    """

    if not text:
        return ""

    text = str(text)

    # ---------------------------------------------------------
    # Normalisation Unicode
    # ---------------------------------------------------------

    text = unicodedata.normalize(
        "NFC",
        text,
    )

    # ---------------------------------------------------------
    # Conversion des espaces Unicode
    # ---------------------------------------------------------

    for char in UNICODE_SPACES:
        text = text.replace(
            char,
            " ",
        )

    return text


# =============================================================
# NETTOYAGE DES ESPACES
# =============================================================

def normalize_spaces(text: str) -> str:
    """
    Nettoie les espaces inutiles.

    Exemple :

        "Bonjour    monde"
        ->
        "Bonjour monde"

        "  Bonjour monde  "
        ->
        "Bonjour monde"
    """

    if not text:
        return ""

    text = normalize_unicode(
        text
    )

    # Plusieurs espaces -> un seul espace
    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    # Espaces autour des retours à la ligne
    text = re.sub(
        r"[ \t]*\n[ \t]*",
        "\n",
        text,
    )

    return text.strip()


# =============================================================
# NETTOYAGE DES LIGNES
# =============================================================

def normalize_lines(
    text: str,
) -> str:
    """
    Nettoie les lignes du texte OCR.

    Supprime :
        - lignes vides répétées
        - espaces inutiles
        - espaces en début/fin de ligne
    """

    if not text:
        return ""

    text = normalize_unicode(
        text
    )

    raw_lines = text.splitlines()

    cleaned_lines = []

    for line in raw_lines:

        line = normalize_spaces(
            line
        )

        if line:
            cleaned_lines.append(
                line
            )

    return "\n".join(
        cleaned_lines
    )


# =============================================================
# NORMALISATION PONCTUATION
# =============================================================

def normalize_punctuation(
    text: str,
) -> str:
    """
    Nettoie légèrement la ponctuation OCR.

    Important :
    cette fonction ne supprime pas arbitrairement
    la ponctuation car celle-ci peut être importante
    dans les références, dates, numéros, etc.
    """

    if not text:
        return ""

    text = normalize_unicode(
        text
    )

    # ---------------------------------------------------------
    # Deux-points
    # ---------------------------------------------------------

    text = re.sub(
        r"\s*:\s*",
        ": ",
        text,
    )

    # ---------------------------------------------------------
    # Virgule
    # ---------------------------------------------------------

    text = re.sub(
        r"\s*,\s*",
        ", ",
        text,
    )

    # ---------------------------------------------------------
    # Point-virgule
    # ---------------------------------------------------------

    text = re.sub(
        r"\s*;\s*",
        "; ",
        text,
    )

    # ---------------------------------------------------------
    # Parenthèses
    # ---------------------------------------------------------

    text = re.sub(
        r"\(\s+",
        "(",
        text,
    )

    text = re.sub(
        r"\s+\)",
        ")",
        text,
    )

    # ---------------------------------------------------------
    # Tirets
    # ---------------------------------------------------------

    text = re.sub(
        r"\s+-\s+",
        " - ",
        text,
    )

    return text


# =============================================================
# NORMALISATION DES LIGNES OCR
# =============================================================

def normalize_ocr_text(
    text: str,
) -> str:
    """
    Pipeline complet de normalisation du texte OCR.

    Cette fonction ne fait PAS de correction sémantique.

    Elle effectue uniquement :

        Unicode
        espaces
        lignes
        ponctuation
    """

    if not text:
        return ""

    text = normalize_unicode(
        text
    )

    text = normalize_lines(
        text
    )

    text = normalize_punctuation(
        text
    )

    text = normalize_lines(
        text
    )

    return text.strip()


# =============================================================
# NORMALISATION D'UNE LIGNE
# =============================================================

def normalize_single_line(
    line: str,
) -> str:
    """
    Normalise une seule ligne OCR.
    """

    if not line:
        return ""

    line = normalize_unicode(
        line
    )

    line = normalize_spaces(
        line
    )

    line = normalize_punctuation(
        line
    )

    return line.strip()


# =============================================================
# NETTOYAGE DES MOTS
# =============================================================

def normalize_word(
    word: str,
) -> str:
    """
    Normalise un mot OCR sans modifier son contenu.

    Exemple :

        "  Renault  "
        ->
        "Renault"
    """

    if not word:
        return ""

    word = normalize_unicode(
        word
    )

    word = re.sub(
        r"\s+",
        " ",
        word,
    )

    return word.strip()


# =============================================================
# NORMALISATION DES MOTS OCR
# =============================================================

def normalize_words(
    words: list[dict],
) -> list[dict]:
    """
    Normalise une liste de mots OCR.

    Les coordonnées et les autres informations
    sont conservées.

    Exemple :

        {
            "text": " Renault ",
            "x": 100,
            ...
        }

    devient :

        {
            "text": "Renault",
            "x": 100,
            ...
        }
    """

    normalized_words = []

    for word in words:

        if not isinstance(
            word,
            dict,
        ):
            continue

        new_word = dict(
            word
        )

        original_text = str(
            word.get(
                "text",
                "",
            )
        )

        normalized_text = normalize_word(
            original_text
        )

        new_word["text"] = (
            normalized_text
        )

        if normalized_text:
            normalized_words.append(
                new_word
            )

    return normalized_words


# =============================================================
# SUPPRESSION DES MOTS VIDES
# =============================================================

def remove_empty_words(
    words: list[dict],
) -> list[dict]:
    """
    Supprime les entrées OCR sans texte.
    """

    result = []

    for word in words:

        if not isinstance(
            word,
            dict,
        ):
            continue

        text = str(
            word.get(
                "text",
                "",
            )
        ).strip()

        if text:
            result.append(
                word
            )

    return result


# =============================================================
# TEXTE DEPUIS LES MOTS
# =============================================================

def words_to_text(
    words: list[dict],
) -> str:
    """
    Transforme une liste de mots OCR en texte simple.

    Cette fonction ne reconstruit pas les lignes
    géométriquement.

    Pour la reconstruction spatiale, utiliser
    engine.layout.py.
    """

    if not words:
        return ""

    normalized_words = normalize_words(
        words
    )

    return " ".join(
        word["text"]
        for word in normalized_words
        if word.get("text")
    )


# =============================================================
# STATISTIQUES DU TEXTE
# =============================================================

def text_statistics(
    text: str,
) -> dict:
    """
    Calcule des statistiques générales
    sur le texte OCR.

    Aucun champ métier n'est utilisé.
    """

    text = normalize_ocr_text(
        text
    )

    lines = [
        line
        for line in text.splitlines()
        if line.strip()
    ]

    words = re.findall(
        r"\S+",
        text,
    )

    characters = len(
        text
    )

    letters = sum(
        1
        for char in text
        if char.isalpha()
    )

    digits = sum(
        1
        for char in text
        if char.isdigit()
    )

    spaces = sum(
        1
        for char in text
        if char.isspace()
    )

    punctuation = sum(
        1
        for char in text
        if unicodedata.category(
            char
        ).startswith("P")
    )

    return {
        "character_count": characters,
        "word_count": len(words),
        "line_count": len(lines),
        "letter_count": letters,
        "digit_count": digits,
        "space_count": spaces,
        "punctuation_count": punctuation,
        "average_word_length": (
            round(
                sum(
                    len(word)
                    for word in words
                )
                / len(words),
                3,
            )
            if words
            else 0.0
        ),
        "average_line_length": (
            round(
                sum(
                    len(line)
                    for line in lines
                )
                / len(lines),
                3,
            )
            if lines
            else 0.0
        ),
    }


# =============================================================
# DETECTION DE LIGNES DUPLIQUEES
# =============================================================

def remove_duplicate_lines(
    text: str,
) -> str:
    """
    Supprime uniquement les lignes strictement identiques
    lorsqu'elles apparaissent plusieurs fois consécutivement.

    Exemple :

        Bonjour
        Bonjour
        Client: Renault

    devient :

        Bonjour
        Client: Renault
    """

    if not text:
        return ""

    lines = text.splitlines()

    result = []

    previous = None

    for line in lines:

        normalized = normalize_single_line(
            line
        )

        if not normalized:
            continue

        if normalized == previous:
            continue

        result.append(
            normalized
        )

        previous = normalized

    return "\n".join(
        result
    )


# =============================================================
# NORMALISATION COMPLETE
# =============================================================

def normalize_document_text(
    text: str,
) -> dict:
    """
    Normalise complètement un texte OCR.

    Retourne :

        {
            "original_text": ...,
            "normalized_text": ...,
            "statistics": ...
        }
    """

    original_text = (
        str(text)
        if text is not None
        else ""
    )

    normalized_text = normalize_ocr_text(
        original_text
    )

    normalized_text = (
        remove_duplicate_lines(
            normalized_text
        )
    )

    normalized_text = normalize_lines(
        normalized_text
    )

    return {
        "original_text": original_text,
        "normalized_text": normalized_text,
        "statistics": text_statistics(
            normalized_text
        ),
    }


# =============================================================
# NORMALISATION D'UN RESULTAT OCR COMPLET
# =============================================================

def normalize_ocr_result(
    ocr_result: dict,
) -> dict:
    """
    Normalise un résultat OCR complet.

    Les informations existantes sont conservées.

    Modifie principalement :

        text
        words
    """

    if not isinstance(
        ocr_result,
        dict,
    ):
        raise TypeError(
            "ocr_result doit être un dictionnaire."
        )

    result = dict(
        ocr_result
    )

    # ---------------------------------------------------------
    # Texte
    # ---------------------------------------------------------

    text = str(
        result.get(
            "text",
            "",
        )
    )

    result["text"] = normalize_ocr_text(
        text
    )

    # ---------------------------------------------------------
    # Mots
    # ---------------------------------------------------------

    words = result.get(
        "words",
        [],
    )

    if isinstance(
        words,
        list,
    ):

        words = normalize_words(
            words
        )

        words = remove_empty_words(
            words
        )

        result["words"] = words

    # ---------------------------------------------------------
    # Statistiques
    # ---------------------------------------------------------

    result["text_statistics"] = (
        text_statistics(
            result["text"]
        )
    )

    return result


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    print("=" * 70)

    print(
        "TEST TEXT NORMALIZER OCR - SANS IA"
    )

    print("=" * 70)

    # =========================================================
    # 1. TEST TEXTE
    # =========================================================

    print(
        "\n[1] Test normalisation du texte"
    )

    test_text = (
        "  Fiche   technique  \n"
        "\n"
        "Ref:    ABC123  \n"
        "Client :   Renault\n"
        "Date : 31/08/2026\n"
        "Date : 31/08/2026\n"
    )

    print(
        "\nTexte original :"
    )

    print(
        repr(test_text)
    )

    normalized = normalize_document_text(
        test_text
    )

    print(
        "\nTexte normalisé :"
    )

    print(
        normalized["normalized_text"]
    )

    # =========================================================
    # 2. STATISTIQUES
    # =========================================================

    print(
        "\n[2] Statistiques"
    )

    stats = normalized[
        "statistics"
    ]

    for key, value in stats.items():

        print(
            f"  {key:<25}: {value}"
        )

    # =========================================================
    # 3. TEST MOTS OCR
    # =========================================================

    print(
        "\n[3] Test normalisation des mots OCR"
    )

    test_words = [

        {
            "text": " Ref ",
            "x": 100,
            "y": 50,
            "width": 30,
            "height": 20,
            "confidence": 95,
        },

        {
            "text": " ABC123 ",
            "x": 140,
            "y": 50,
            "width": 70,
            "height": 20,
            "confidence": 96,
        },

        {
            "text": " ",
            "x": 220,
            "y": 50,
            "width": 20,
            "height": 20,
            "confidence": 0,
        },

        {
            "text": "Renault",
            "x": 100,
            "y": 100,
            "width": 80,
            "height": 20,
            "confidence": 94,
        },
    ]

    normalized_words = normalize_words(
        test_words
    )

    for index, word in enumerate(
        normalized_words,
        start=1,
    ):

        print(
            f"  [{index:03d}] "
            f"{word.get('text', ''):<15} "
            f"x={word.get('x', 0):.1f} "
            f"y={word.get('y', 0):.1f} "
            f"conf={word.get('confidence', '')}"
        )

    # =========================================================
    # 4. TEST RESULTAT OCR
    # =========================================================

    print(
        "\n[4] Test résultat OCR complet"
    )

    test_result = {

        "confidence": 0.92,

        "text": (
            " Ref:   ABC123 \n"
            "Client : Renault\n"
            "\n"
            "Date : 31/08/2026"
        ),

        "words": test_words,
    }

    final_result = normalize_ocr_result(
        test_result
    )

    print(
        "\nTexte final :"
    )

    print(
        final_result["text"]
    )

    print(
        "\nNombre de mots : "
        f"{len(final_result['words'])}"
    )

    print(
        "\nStatistiques :"
    )

    for key, value in final_result[
        "text_statistics"
    ].items():

        print(
            f"  {key:<25}: {value}"
        )

    # =========================================================
    # 5. FIN
    # =========================================================

    print(
        "\n"
        + "=" * 70
    )

    print(
        "TEST TEXT NORMALIZER TERMINE"
    )

    print(
        "=" * 70
    )

