
from __future__ import annotations

import re
from typing import Any


EXPECTED_FIELDS = [
    "ref_sap",
    "ref_be",
    "indice_doc",
    "designation_piece",
    "ref_client",
    "designation_op",
    "numero_op",
    "atelier",
]


def normalize_text(text: str) -> str:
    """Nettoyage léger du texte OCR."""

    text = text.replace("\x00", "")
    text = text.replace("|", " ")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_value(value: str) -> str:
    """Nettoie une valeur extraite."""

    value = value.strip()

    value = value.strip(" :|[]{}()")

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def extract_ref_sap(text: str) -> str | None:
    """Extrait la référence SAP."""

    patterns = [
        r"\bRef\.?\s*SAP\s*[:|]?\s*([A-Z0-9][A-Z0-9_-]{5,})",
        r"\bREF\s*SAP\s*[:|]?\s*([A-Z0-9][A-Z0-9_-]{5,})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return clean_value(match.group(1))

    return None


def extract_ref_be(text: str) -> str | None:
    """
    Extrait la référence BE.

    Exemple :
        Ref. BE:|REN21-507 D

    devient :
        REN21-507 D
    """

    normalized = normalize_text(text)

    patterns = [
        r"\bRef\.?\s*B[EÉ]\s*[:|]?\s*"
        r"([A-Z0-9][A-Z0-9_-]*(?:\s+[A-Z0-9_-]+)?)",

        r"\bREF\s*B[EÉ]\s*[:|]?\s*"
        r"([A-Z0-9][A-Z0-9_-]*(?:\s+[A-Z0-9_-]+)?)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE,
        )

        if match:
            value = clean_value(match.group(1))

            # Arrêt avant un autre champ.
            value = re.split(
                r"\b(?:Indice|Désignation|Designation|Ref\.?\s*client|REF\s*CLIENT)\b",
                value,
                flags=re.IGNORECASE,
            )[0]

            value = clean_value(value)

            if value:
                return value

    return None


def extract_indice_doc(text: str) -> str | None:
    """Extrait l'indice du document."""

    normalized = normalize_text(text)

    patterns = [
        r"\bIndice\s*doc\.?\s*[:|]?\s*([A-Z0-9_-]+)",
        r"\bIndice\s*[:|]?\s*([A-Z0-9_-]+)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE,
        )

        if match:
            return clean_value(match.group(1))

    return None


def extract_designation_piece(text: str) -> str | None:
    """Extrait la désignation de la pièce."""

    normalized = normalize_text(text)

    patterns = [
        r"\bDésignation\s*pièce\s*[:|]?\s*(.+?)(?=\s+Ref\.?\s*client|\s+REF\s*CLIENT|\s+Désignation\s*OP|\s+Designation\s*OP|\s+N°?\s*OP|$)",

        r"\bDesignation\s*piece\s*[:|]?\s*(.+?)(?=\s+Ref\.?\s*client|\s+REF\s*CLIENT|\s+Désignation\s*OP|\s+Designation\s*OP|\s+N°?\s*OP|$)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE,
        )

        if match:
            value = clean_value(match.group(1))

            # Supprime les caractères OCR parasites au début.
            value = value.lstrip("[{(")

            if value:
                return value

    return None


def extract_ref_client(text: str) -> str | None:
    """
    Extrait la référence client.

    Exemple :
        Ref. client:|755128396R

    devient :
        755128396R
    """

    normalized = normalize_text(text)

    patterns = [
        r"\bRef\.?\s*client\s*[:|]?\s*"
        r"([A-Z0-9][A-Z0-9_-]{4,})",

        r"\bREF\s*CLIENT\s*[:|]?\s*"
        r"([A-Z0-9][A-Z0-9_-]{4,})",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE,
        )

        if match:
            value = clean_value(match.group(1))

            if value:
                return value

    return None


def extract_designation_op(text: str) -> str | None:
    """Extrait la désignation de l'opération."""

    normalized = normalize_text(text)

    patterns = [
        r"\bDésignation\s*OP\s*[:|]?\s*(.+?)(?=\s+N°?\s*OP|$)",

        r"\bDesignation\s*OP\s*[:|]?\s*(.+?)(?=\s+N°?\s*OP|$)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE,
        )

        if match:
            value = clean_value(match.group(1))

            if value:
                return value

    return None


def extract_numero_op(text: str) -> str | None:
    """Extrait le numéro d'opération."""

    normalized = normalize_text(text)

    patterns = [
        r"\bN°\s*OP\s*[:|]?\s*(\d+)",
        r"\bN\s*OP\s*[:|]?\s*(\d+)",
        r"\bNO\s*OP\s*[:|]?\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

    return None


def extract_atelier(text: str) -> str | None:
    """Extrait l'atelier."""

    normalized = normalize_text(text)

    pattern = r"\bAtelier\s*[:|]?\s*(.+?)(?=\s+Page|\s+Ref\.?\s*SAP|\s+Ref\.?\s*BE|\s+Indice|$)"

    match = re.search(
        pattern,
        normalized,
        re.IGNORECASE,
    )

    if match:
        value = clean_value(match.group(1))

        if value:
            return value

    return None


def extract_fields(text: str) -> dict[str, Any]:
    """
    Extraction complète des champs industriels.

    Méthode :
        - regex
        - règles
        - validation textuelle

    Aucune IA.
    """

    return {
        "ref_sap": extract_ref_sap(text),
        "ref_be": extract_ref_be(text),
        "indice_doc": extract_indice_doc(text),
        "designation_piece": extract_designation_piece(text),
        "ref_client": extract_ref_client(text),
        "designation_op": extract_designation_op(text),
        "numero_op": extract_numero_op(text),
        "atelier": extract_atelier(text),
    }


def count_found_fields(
    fields: dict[str, Any],
) -> int:
    """Compte les champs réellement trouvés."""

    return sum(
        1
        for field in EXPECTED_FIELDS
        if fields.get(field)
    )

