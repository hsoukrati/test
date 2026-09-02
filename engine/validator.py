from __future__ import annotations

import re
from typing import Any


def validate_ref_sap(value: Any) -> bool:
    """Valide une référence SAP industrielle."""

    if not value:
        return False

    value = str(value).strip().upper()

    # Exemple : M400026D01
    return bool(
        re.fullmatch(
            r"[A-Z0-9][A-Z0-9_-]{5,30}",
            value,
        )
    )


def validate_ref_be(value: Any) -> bool:
    """Valide une référence BE."""

    if not value:
        return False

    value = str(value).strip().upper()

    return bool(
        re.fullmatch(
            r"[A-Z0-9][A-Z0-9 _-]{2,40}",
            value,
        )
    )


def validate_indice_doc(value: Any) -> bool:
    """Valide l'indice du document."""

    if not value:
        return False

    value = str(value).strip()

    return bool(
        re.fullmatch(
            r"[A-Z0-9_-]{1,10}",
            value,
        )
    )


def validate_designation_piece(value: Any) -> bool:
    """Valide la désignation de la pièce."""

    if not value:
        return False

    value = str(value).strip()

    if len(value) < 2:
        return False

    if len(value) > 150:
        return False

    # Doit contenir au moins une lettre.
    return bool(re.search(r"[A-Za-zÀ-ÿ]", value))


def validate_ref_client(value: Any) -> bool:
    """Valide une référence client."""

    if not value:
        return False

    value = str(value).strip().upper()

    return bool(
        re.fullmatch(
            r"[A-Z0-9][A-Z0-9_-]{4,40}",
            value,
        )
    )


def validate_designation_op(value: Any) -> bool:
    """Valide la désignation de l'opération."""

    if not value:
        return False

    value = str(value).strip()

    if len(value) < 2:
        return False

    if len(value) > 150:
        return False

    return bool(re.search(r"[A-Za-zÀ-ÿ]", value))


def validate_numero_op(value: Any) -> bool:
    """Valide le numéro d'opération."""

    if not value:
        return False

    value = str(value).strip()

    return bool(
        re.fullmatch(
            r"\d{1,6}",
            value,
        )
    )


def validate_atelier(value: Any) -> bool:
    """Valide le nom de l'atelier."""

    if not value:
        return False

    value = str(value).strip()

    if len(value) < 2:
        return False

    if len(value) > 100:
        return False

    return bool(re.search(r"[A-Za-zÀ-ÿ]", value))


VALIDATORS = {
    "ref_sap": validate_ref_sap,
    "ref_be": validate_ref_be,
    "indice_doc": validate_indice_doc,
    "designation_piece": validate_designation_piece,
    "ref_client": validate_ref_client,
    "designation_op": validate_designation_op,
    "numero_op": validate_numero_op,
    "atelier": validate_atelier,
}


def validate_fields(
    fields: dict[str, Any],
) -> dict[str, Any]:
    """
    Valide tous les champs extraits.

    Retourne un résultat détaillé pour chaque champ.
    """

    results: dict[str, Any] = {}

    valid_count = 0
    total_count = len(VALIDATORS)

    for field_name, validator in VALIDATORS.items():

        value = fields.get(field_name)

        is_valid = validator(value)

        results[field_name] = {
            "value": value,
            "valid": is_valid,
        }

        if is_valid:
            valid_count += 1

    score = (
        valid_count / total_count
        if total_count > 0
        else 0.0
    )

    return {
        "valid_fields": valid_count,
        "total_fields": total_count,
        "validation_score": round(score, 3),
        "fields": results,
    }


def count_valid_fields(
    fields: dict[str, Any],
) -> int:
    """
    Retourne uniquement le nombre de champs valides.
    """

    result = validate_fields(fields)

    return result["valid_fields"]