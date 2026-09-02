from __future__ import annotations

import re
import unicodedata


# =============================================================
# CORRECTIONS OCR CONNUES
# =============================================================

OCR_LABEL_CORRECTIONS = {
    # ---------------------------------------------------------
    # REF
    # ---------------------------------------------------------
    "ref": "ref",
    "rer": "ref",
    "re": "ref",
    "ret": "ref",
    "r ef": "ref",
    "refe": "ref",

    # ---------------------------------------------------------
    # BE
    # ---------------------------------------------------------
    "be": "be",
    "bé": "be",
    "bè": "be",
    "bê": "be",
    "8e": "be",
    "8é": "be",
    "8e": "be",

    # ---------------------------------------------------------
    # SAP
    # ---------------------------------------------------------
    "sap": "sap",
    "5ap": "sap",
    "sa p": "sap",

    # ---------------------------------------------------------
    # CLIENT
    # ---------------------------------------------------------
    "client": "client",
    "cllent": "client",
    "cllent": "client",
    "clien": "client",
    "client:": "client",

    # ---------------------------------------------------------
    # ATELIER
    # ---------------------------------------------------------
    "atelier": "atelier",
    "ateller": "atelier",
    "atel ier": "atelier",
    "atellier": "atelier",

    # ---------------------------------------------------------
    # INDICE
    # ---------------------------------------------------------
    "indice": "indice",
    "indlce": "indice",
    "indlce": "indice",
    "lndice": "indice",
    "indlce": "indice",

    # ---------------------------------------------------------
    # DOC
    # ---------------------------------------------------------
    "doc": "doc",
    "doe": "doc",
    "d0c": "doc",
    "doc:": "doc",

    # ---------------------------------------------------------
    # DESIGNATION
    # ---------------------------------------------------------
    "designation": "designation",
    "deslgnation": "designation",
    "desiqnation": "designation",
    "desiqn ation": "designation",
    "designatlon": "designation",

    # ---------------------------------------------------------
    # PIECE
    # ---------------------------------------------------------
    "piece": "piece",
    "plece": "piece",
    "pleçe": "piece",
    "p1ece": "piece",
    "piece:": "piece",

    # ---------------------------------------------------------
    # OP
    # ---------------------------------------------------------
    "op": "op",
    "0p": "op",
    "o p": "op",
    "op:": "op",

    # ---------------------------------------------------------
    # N°
    # ---------------------------------------------------------
    "n°": "no",
    "nº": "no",
    "no": "no",
    "n0": "no",
    "n o": "no",
    "n°:": "no",
}


# =============================================================
# NORMALISATION UNICODE
# =============================================================

def remove_accents(text: str) -> str:
    """
    Supprime les accents.

    Exemple :

        Désignation -> Designation
        pièce       -> piece
        BÉ          -> BE
    """

    text = unicodedata.normalize(
        "NFD",
        text,
    )

    return "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"
    )


# =============================================================
# NORMALISATION DE BASE
# =============================================================

def basic_normalize(text: str) -> str:
    """
    Normalisation générale d'un mot OCR.
    """

    value = str(text or "")

    value = value.strip().lower()

    # Accents
    value = remove_accents(value)

    # Quelques confusions OCR générales
    value = value.replace("’", "'")
    value = value.replace("`", "'")

    # Espaces multiples
    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    # Ponctuation de fin
    value = value.rstrip(
        ":.;,|_"
    )

    return value.strip()


# =============================================================
# CORRECTION OCR
# =============================================================

def normalize_label_token(
    text: str,
) -> str:
    """
    Transforme un token OCR en token canonique.

    Exemple :

        Rer.       -> ref
        BÉ         -> be
        Indlce     -> indice
        Deslgnation -> designation
        plece       -> piece
        N0          -> no
    """

    value = basic_normalize(text)

    if not value:
        return ""

    # Première recherche directe
    if value in OCR_LABEL_CORRECTIONS:

        return OCR_LABEL_CORRECTIONS[value]

    # Version sans ponctuation
    compact = re.sub(
        r"[^a-z0-9°º]",
        "",
        value,
    )

    if compact in OCR_LABEL_CORRECTIONS:

        return OCR_LABEL_CORRECTIONS[
            compact
        ]

    # ---------------------------------------------------------
    # Règles spécifiques N°
    # ---------------------------------------------------------

    if compact in {
        "n",
        "no",
        "n0",
        "nº",
        "n°",
    }:

        return "no"

    # ---------------------------------------------------------
    # Règles spécifiques REF
    # ---------------------------------------------------------

    if compact in {
        "ref",
        "rer",
        "re",
        "ret",
        "refe",
    }:

        return "ref"

    # ---------------------------------------------------------
    # Règles spécifiques BE
    # ---------------------------------------------------------

    if compact in {
        "be",
        "8e",
        "8é",
    }:

        return "be"

    # ---------------------------------------------------------
    # Règles spécifiques OP
    # ---------------------------------------------------------

    if compact in {
        "op",
        "0p",
    }:

        return "op"

    # ---------------------------------------------------------
    # Règles spécifiques DOC
    # ---------------------------------------------------------

    if compact in {
        "doc",
        "doe",
        "d0c",
    }:

        return "doc"

    return compact


# =============================================================
# DISTANCE DE LEVENSHTEIN
# =============================================================

def levenshtein_distance(
    a: str,
    b: str,
) -> int:
    """
    Calcule la distance de Levenshtein
    entre deux chaînes.
    """

    if a == b:
        return 0

    if not a:
        return len(b)

    if not b:
        return len(a)

    previous = list(
        range(len(b) + 1)
    )

    for i, char_a in enumerate(
        a,
        start=1,
    ):

        current = [
            i
        ]

        for j, char_b in enumerate(
            b,
            start=1,
        ):

            insert_cost = (
                current[j - 1] + 1
            )

            delete_cost = (
                previous[j] + 1
            )

            replace_cost = (
                previous[j - 1]
                + (
                    0
                    if char_a == char_b
                    else 1
                )
            )

            current.append(
                min(
                    insert_cost,
                    delete_cost,
                    replace_cost,
                )
            )

        previous = current

    return previous[-1]


# =============================================================
# CORRECTION FUZZY
# =============================================================

CANONICAL_LABELS = [
    "ref",
    "sap",
    "be",
    "client",
    "atelier",
    "indice",
    "doc",
    "designation",
    "piece",
    "op",
    "no",
]


def fuzzy_normalize_label(
    text: str,
    max_distance: int = 1,
) -> str:
    """
    Normalisation avec tolérance aux petites erreurs OCR.

    Exemple :

        desiqnation -> designation
        ateller      -> atelier
        cllent       -> client
    """

    normalized = normalize_label_token(
        text
    )

    if not normalized:
        return ""

    # Déjà reconnu
    if normalized in CANONICAL_LABELS:

        return normalized

    best_label = normalized
    best_distance = max_distance + 1

    for label in CANONICAL_LABELS:

        distance = levenshtein_distance(
            normalized,
            label,
        )

        if distance < best_distance:

            best_distance = distance
            best_label = label

    if best_distance <= max_distance:

        return best_label

    return normalized


# =============================================================
# NORMALISATION FORTE
# =============================================================

def normalize_label(
    text: str,
) -> str:
    """
    Fonction principale à utiliser dans le pipeline OCR.

    Elle applique :

        1. normalisation Unicode
        2. corrections OCR connues
        3. correction fuzzy
    """

    value = fuzzy_normalize_label(
        text,
        max_distance=1,
    )

    return value