
from __future__ import annotations

import re
import unicodedata
from copy import deepcopy


# =============================================================
# CONFIGURATION
# =============================================================

# Caractères OCR souvent confondus.
# IMPORTANT :
# Ces corrections ne sont PAS appliquées aveuglément.
# Elles sont utilisées uniquement dans des contextes numériques
# ou alphanumériques appropriés.

DIGIT_CONTEXT_REPLACEMENTS = {
    "O": "0",
    "o": "0",
    "I": "1",
    "l": "1",
    "S": "5",
    "s": "5",
    "B": "8",
    "G": "6",
}


# Erreurs OCR textuelles très fréquentes.
# Ces corrections sont limitées à des mots connus.
COMMON_WORD_CORRECTIONS = {
    # Français
    "cllent": "client",
    "cllient": "client",
    "ateller": "atelier",
    "atellier": "atelier",

    "deslgnation": "designation",
    "deslgnatlon": "designation",

    "plece": "piece",
    "pleces": "pieces",

    "indlce": "indice",
    "lndice": "indice",

    "quantlte": "quantite",
    "quantlte": "quantite",

    # Quelques erreurs courantes
    "montage": "montage",
    "reglage": "reglage",
}


# Mots qu'on ne doit jamais modifier.
PROTECTED_WORDS = {
    "ocr",
    "pdf",
    "jpg",
    "jpeg",
    "png",
    "tiff",
    "webp",
}


# =============================================================
# NORMALISATION UNICODE
# =============================================================

def normalize_unicode(text: str) -> str:
    """
    Normalise un texte Unicode.

    Exemple :

        caractère accentué
        ↓
        forme Unicode normalisée

    Cette fonction ne supprime PAS les accents.
    """

    return unicodedata.normalize(
        "NFC",
        str(text),
    )


# =============================================================
# NORMALISATION DES ESPACES
# =============================================================

def normalize_spaces(text: str) -> str:
    """
    Nettoie les espaces multiples.

    Exemple :

        "Ref    :    ABC"
        ↓
        "Ref : ABC"
    """

    text = str(text)

    text = text.replace(
        "\u00a0",
        " ",
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    return text.strip()


# =============================================================
# NETTOYAGE DES CARACTERES INVISIBLES
# =============================================================

def remove_invisible_characters(
    text: str,
) -> str:
    """
    Supprime certains caractères de contrôle
    qui peuvent apparaître après OCR.
    """

    result = []

    for char in str(text):

        category = unicodedata.category(
            char
        )

        if category.startswith("C"):

            # On conserve les caractères utiles
            # comme les espaces standards.

            if char in {
                "\n",
                "\t",
            }:
                result.append(
                    char
                )

            continue

        result.append(
            char
        )

    return "".join(
        result
    )


# =============================================================
# PROTECTION DES MOTS
# =============================================================

def is_protected_word(
    text: str,
) -> bool:
    """
    Vérifie si un mot doit être protégé.
    """

    normalized = (
        str(text)
        .strip()
        .lower()
    )

    return normalized in PROTECTED_WORDS


# =============================================================
# DETECTION NUMERIQUE
# =============================================================

def looks_numeric(
    text: str,
) -> bool:
    """
    Détermine si un token ressemble à une valeur numérique.

    Exemples :

        12345       -> True
        12/08/2026  -> True
        123-456     -> True
        ABC123      -> False
        Client      -> False
    """

    text = str(text).strip()

    if not text:
        return False

    # ---------------------------------------------------------
    # Déjà numérique
    # ---------------------------------------------------------

    if re.fullmatch(
        r"[0-9]+",
        text,
    ):
        return True

    # ---------------------------------------------------------
    # Date
    # ---------------------------------------------------------

    if re.fullmatch(
        r"[0-9OolISsB]+[./-]"
        r"[0-9OolISsB]+[./-]"
        r"[0-9OolISsB]+",
        text,
    ):
        return True

    # ---------------------------------------------------------
    # Code numérique avec séparateurs
    # ---------------------------------------------------------

    if re.fullmatch(
        r"[0-9OolISsB][0-9OolISsB._:/-]*",
        text,
    ):
        return True

    return False


# =============================================================
# CORRECTION NUMERIQUE
# =============================================================

def correct_numeric_token(
    text: str,
) -> str:
    """
    Corrige les confusions OCR dans les valeurs
    principalement numériques.

    Exemple :

        O12345  -> 012345
        2O26    -> 2026
        1O/08/2O26 -> 10/08/2026

    Les corrections sont limitées aux caractères
    présentant une confusion classique avec les chiffres.
    """

    text = str(text)

    if not looks_numeric(
        text
    ):
        return text

    corrected = []

    for char in text:

        replacement = (
            DIGIT_CONTEXT_REPLACEMENTS.get(
                char,
                char,
            )
        )

        corrected.append(
            replacement
        )

    return "".join(
        corrected
    )


# =============================================================
# CORRECTION MOT
# =============================================================

def correct_word(
    text: str,
) -> str:
    """
    Corrige un mot OCR.

    Cette fonction est prudente :
    elle n'effectue pas de remplacement
    arbitraire des caractères.
    """

    original = str(
        text
    ).strip()

    if not original:
        return original

    if is_protected_word(
        original
    ):
        return original

    # ---------------------------------------------------------
    # Nettoyage
    # ---------------------------------------------------------

    cleaned = normalize_unicode(
        original
    )

    cleaned = remove_invisible_characters(
        cleaned
    )

    cleaned = normalize_spaces(
        cleaned
    )

    if not cleaned:
        return cleaned

    # ---------------------------------------------------------
    # Correction numérique
    # ---------------------------------------------------------

    numeric_corrected = correct_numeric_token(
        cleaned
    )

    if numeric_corrected != cleaned:

        return numeric_corrected

    # ---------------------------------------------------------
    # Correction de mots connus
    # ---------------------------------------------------------

    lookup = (
        cleaned
        .lower()
        .replace(
            ".",
            "",
        )
        .replace(
            ":",
            "",
        )
    )

    correction = COMMON_WORD_CORRECTIONS.get(
        lookup
    )

    if correction:

        # Conservation approximative de la casse.
        if cleaned.isupper():

            return correction.upper()

        if cleaned.istitle():

            return correction.capitalize()

        return correction

    return cleaned


# =============================================================
# CORRECTION D'UNE LISTE DE MOTS OCR
# =============================================================

def correct_words(
    words: list[dict],
) -> list[dict]:
    """
    Corrige une liste de mots OCR.

    Les informations suivantes sont conservées :

        text
        x
        y
        width
        height
        confidence
        conf
        autres métadonnées

    Une copie des dictionnaires est utilisée
    afin de ne pas modifier directement le résultat OCR original.
    """

    corrected_words = []

    for word in words:

        if not isinstance(
            word,
            dict,
        ):
            continue

        corrected_word = deepcopy(
            word
        )

        original_text = str(
            word.get(
                "text",
                "",
            )
        )

        corrected_text = correct_word(
            original_text
        )

        corrected_word[
            "text_original"
        ] = original_text

        corrected_word[
            "text"
        ] = corrected_text

        # Indique si une correction a été effectuée.
        corrected_word[
            "corrected"
        ] = (
            corrected_text
            != original_text
        )

        corrected_words.append(
            corrected_word
        )

    return corrected_words


# =============================================================
# CORRECTION D'UN TEXTE COMPLET
# =============================================================

def correct_text(
    text: str,
) -> str:
    """
    Corrige un texte OCR complet.

    Le texte est traité ligne par ligne,
    puis mot par mot.
    """

    if not text:
        return ""

    lines = str(
        text
    ).splitlines()

    corrected_lines = []

    for line in lines:

        words = line.split()

        corrected_line = []

        for word in words:

            corrected_line.append(
                correct_word(
                    word
                )
            )

        corrected_lines.append(
            " ".join(
                corrected_line
            )
        )

    return "\n".join(
        corrected_lines
    )


# =============================================================
# STATISTIQUES DE CORRECTION
# =============================================================

def correction_statistics(
    original_words: list[dict],
    corrected_words: list[dict],
) -> dict:
    """
    Calcule les statistiques de correction.
    """

    original_count = len(
        original_words
    )

    corrected_count = 0

    for word in corrected_words:

        if word.get(
            "corrected",
            False,
        ):
            corrected_count += 1

    correction_rate = 0.0

    if original_count > 0:

        correction_rate = (
            corrected_count
            / original_count
        )

    return {
        "original_words": original_count,
        "corrected_words": corrected_count,
        "unchanged_words": (
            original_count
            - corrected_count
        ),
        "correction_rate": correction_rate,
    }


# =============================================================
# CORRECTION D'UN RESULTAT OCR COMPLET
# =============================================================

def correct_ocr_result(
    ocr_result: dict,
) -> dict:
    """
    Corrige directement le résultat retourné
    par le moteur OCR.

    Entrée attendue :

        {
            "words": [...],
            "confidence": ...
        }

    Retourne une copie corrigée.
    """

    if not isinstance(
        ocr_result,
        dict,
    ):
        raise TypeError(
            "ocr_result doit être un dictionnaire."
        )

    result = deepcopy(
        ocr_result
    )

    original_words = result.get(
        "words",
        [],
    )

    if not isinstance(
        original_words,
        list,
    ):
        original_words = []

    corrected_words = correct_words(
        original_words
    )

    result[
        "words_original"
    ] = original_words

    result[
        "words"
    ] = corrected_words

    result[
        "correction"
    ] = correction_statistics(
        original_words,
        corrected_words,
    )

    # ---------------------------------------------------------
    # Reconstruction du texte
    # ---------------------------------------------------------

    if "text" in result:

        result[
            "text_original"
        ] = result.get(
            "text",
            "",
        )

        result[
            "text"
        ] = correct_text(
            result.get(
                "text",
                "",
            )
        )

    return result


# =============================================================
# AFFICHAGE DES CORRECTIONS
# =============================================================

def print_correction_results(
    original_words: list[dict],
    corrected_words: list[dict],
) -> None:
    """
    Affiche uniquement les mots ayant été corrigés.
    """

    print(
        "\nCorrections OCR :"
    )

    corrections_found = False

    for original, corrected in zip(
        original_words,
        corrected_words,
    ):

        original_text = str(
            original.get(
                "text",
                "",
            )
        )

        corrected_text = str(
            corrected.get(
                "text",
                "",
            )
        )

        if (
            original_text
            != corrected_text
        ):

            corrections_found = True

            print(
                f"  {original_text!r}"
                f" -> "
                f"{corrected_text!r}"
            )

    if not corrections_found:

        print(
            "  Aucune correction."
        )


# =============================================================
# TEST DU MODULE
# =============================================================

def main() -> None:

    print(
        "=" * 70
    )

    print(
        "TEST CORRECTION OCR - SANS IA"
    )

    print(
        "=" * 70
    )

    # =========================================================
    # 1. TEST DES MOTS
    # =========================================================

    test_words = [
        "cllent",
        "Ateller",
        "deslgnation",
        "plece",
        "indlce",
        "O12345",
        "2O26",
        "1O/08/2O26",
        "ABC123",
        "Client",
        "Renault",
    ]

    print(
        "\n[1] Test correction des mots"
    )

    for word in test_words:

        corrected = correct_word(
            word
        )

        print(
            f"  {word:<20} "
            f"-> "
            f"{corrected}"
        )

    # =========================================================
    # 2. TEST DES MOTS OCR AVEC COORDONNEES
    # =========================================================

    print(
        "\n[2] Test correction des mots OCR"
    )

    ocr_words = [
        {
            "text": "Ref",
            "x": 100,
            "y": 50,
            "width": 40,
            "height": 20,
            "confidence": 95.0,
        },
        {
            "text": "O12345",
            "x": 150,
            "y": 50,
            "width": 100,
            "height": 20,
            "confidence": 82.0,
        },
        {
            "text": "cllent",
            "x": 300,
            "y": 50,
            "width": 70,
            "height": 20,
            "confidence": 78.0,
        },
        {
            "text": "Ateller",
            "x": 400,
            "y": 50,
            "width": 80,
            "height": 20,
            "confidence": 80.0,
        },
    ]

    corrected_words = correct_words(
        ocr_words
    )

    print_correction_results(
        ocr_words,
        corrected_words,
    )

    # =========================================================
    # 3. STATISTIQUES
    # =========================================================

    statistics = correction_statistics(
        ocr_words,
        corrected_words,
    )

    print(
        "\n[3] Statistiques"
    )

    print(
        f"  Mots originaux    : "
        f"{statistics['original_words']}"
    )

    print(
        f"  Mots corrigés     : "
        f"{statistics['corrected_words']}"
    )

    print(
        f"  Mots inchangés    : "
        f"{statistics['unchanged_words']}"
    )

    print(
        f"  Taux correction   : "
        f"{statistics['correction_rate']:.3f}"
    )

    # =========================================================
    # 4. TEST TEXTE
    # =========================================================

    print(
        "\n[4] Test texte complet"
    )

    test_text = (
        "Ref O12345\n"
        "cllent Renault\n"
        "Ateller Emboutissage\n"
        "Date 1O/08/2O26"
    )

    print(
        "\nTexte original :"
    )

    print(
        test_text
    )

    corrected_text = correct_text(
        test_text
    )

    print(
        "\nTexte corrigé :"
    )

    print(
        corrected_text
    )

    # =========================================================
    # 5. TEST RESULTAT OCR COMPLET
    # =========================================================

    print(
        "\n[5] Test résultat OCR complet"
    )

    ocr_result = {
        "text": test_text,
        "words": ocr_words,
        "confidence": 0.850,
    }

    corrected_result = correct_ocr_result(
        ocr_result
    )

    print(
        "\nRésultat :"
    )

    print(
        f"  Confiance OCR : "
        f"{corrected_result.get('confidence', 0.0):.3f}"
    )

    correction = corrected_result.get(
        "correction",
        {},
    )

    print(
        f"  Corrections   : "
        f"{correction.get('corrected_words', 0)}"
    )

    print(
        f"  Taux          : "
        f"{correction.get('correction_rate', 0.0):.3f}"
    )

    print(
        "\nTexte final :"
    )

    print(
        corrected_result.get(
            "text",
            "",
        )
    )

    # =========================================================
    # FIN
    # =========================================================

    print(
        "\n"
        + "=" * 70
    )

    print(
        "TEST CORRECTION OCR TERMINE"
    )

    print(
        "=" * 70
    )


# =============================================================
# POINT D'ENTREE
# =============================================================

if __name__ == "__main__":

    main()

