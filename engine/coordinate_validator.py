from __future__ import annotations

from typing import Any


# =============================================================
# OUTILS GEOMETRIQUES
# =============================================================

def _center_y(word: dict[str, Any]) -> float:
    """Retourne le centre vertical."""

    return (
        float(word.get("y", 0))
        + float(word.get("height", 0)) / 2
    )


def _left_x(word: dict[str, Any]) -> float:
    """Retourne la position X gauche."""

    return float(
        word.get("x", 0)
    )


def _right_x(word: dict[str, Any]) -> float:
    """Retourne la position X droite."""

    return (
        float(word.get("x", 0))
        + float(word.get("width", 0))
    )


def _center_x(word: dict[str, Any]) -> float:
    """Retourne le centre X."""

    return (
        float(word.get("x", 0))
        + float(word.get("width", 0)) / 2
    )


# =============================================================
# NORMALISATION
# =============================================================

def _normalize_text(
    text: str,
) -> str:
    """
    Normalise un texte OCR.

    Exemple :

        "Désignation" -> "designation"
        "Pièce:"      -> "piece"
        "BE:"         -> "be"
    """

    value = str(
        text
    ).strip().lower()

    replacements = {
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "à": "a",
        "â": "a",
        "ä": "a",
        "î": "i",
        "ï": "i",
        "ô": "o",
        "ö": "o",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ç": "c",
    }

    for old, new in replacements.items():

        value = value.replace(
            old,
            new,
        )

    for char in [
        ":",
        ".",
        "|",
        "_",
        ";",
    ]:

        value = value.replace(
            char,
            "",
        )

    return value.strip()


# =============================================================
# LIGNE
# =============================================================

def same_line(
    word1: dict[str, Any],
    word2: dict[str, Any],
    tolerance: float = 25.0,
) -> bool:
    """
    Vérifie si deux éléments OCR sont sur
    approximativement la même ligne.
    """

    return abs(
        _center_y(word1)
        - _center_y(word2)
    ) <= tolerance


# =============================================================
# POSITION
# =============================================================

def value_is_right_of(
    label: dict[str, Any],
    value: dict[str, Any],
    max_distance: float = 1200.0,
) -> bool:
    """
    Vérifie que la valeur commence après
    la fin du label.
    """

    label_right = _right_x(
        label
    )

    value_left = _left_x(
        value
    )

    distance = (
        value_left
        - label_right
    )

    return (
        distance >= 0
        and distance <= max_distance
    )


# =============================================================
# SCORE GEOMETRIQUE
# =============================================================

def coordinate_score(
    label: dict[str, Any],
    value: dict[str, Any],
) -> float:
    """
    Score spatial entre 0 et 1.
    """

    if not same_line(
        label,
        value,
    ):
        return 0.0

    distance = (
        _left_x(value)
        - _right_x(label)
    )

    if distance < 0:
        return 0.0

    score = 1.0 / (
        1.0 + distance / 100.0
    )

    return round(
        score,
        3,
    )


# =============================================================
# CONFIANCE OCR
# =============================================================

def _confidence_score(
    word: dict[str, Any],
) -> float:
    """Retourne la confiance OCR normalisée."""

    try:

        confidence = float(
            word.get(
                "confidence",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return 0.0

    confidence = max(
        0.0,
        min(
            100.0,
            confidence,
        ),
    )

    return confidence / 100.0


# =============================================================
# LABELS
# =============================================================

def _build_label_word_set(
    field_labels: dict[str, dict[str, Any]],
) -> set[str]:
    """
    Construit l'ensemble des mots appartenant
    aux labels détectés.
    """

    label_words: set[str] = set()

    for label in field_labels.values():

        words = label.get(
            "label_words"
        )

        if words:

            for text in words:

                normalized = _normalize_text(
                    text
                )

                if normalized:
                    label_words.add(
                        normalized
                    )

        else:

            text = _normalize_text(
                label.get(
                    "text",
                    "",
                )
            )

            for part in text.split():

                normalized = _normalize_text(
                    part
                )

                if normalized:
                    label_words.add(
                        normalized
                    )

    return label_words


# =============================================================
# PROCHAIN LABEL
# =============================================================

def _find_next_label(
    current_label: dict[str, Any],
    field_labels: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Cherche le prochain label situé sur la même ligne.

    Exemple :

        Désignation OP: DECOUPE LASER N° OP: 10
        ^               ^              ^
        label actuel    valeur         prochain label

    Le prochain label est donc N° OP.
    """

    current_right = _right_x(
        current_label
    )

    candidates: list[
        dict[str, Any]
    ] = []

    for label in field_labels.values():

        if label is current_label:
            continue

        if not same_line(
            current_label,
            label,
        ):
            continue

        label_left = _left_x(
            label
        )

        if label_left <= current_right:
            continue

        candidates.append(
            label
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: _left_x(item)
    )

    return candidates[0]


# =============================================================
# ZONE ENTRE DEUX LABELS
# =============================================================

def find_value_region(
    label: dict[str, Any],
    words: list[dict[str, Any]],
    field_labels: dict[str, dict[str, Any]],
    max_distance: float = 1200.0,
) -> dict[str, Any] | None:
    """
    Recherche toute la zone de valeur située
    après un label et avant le prochain label.

    Exemple :

        Désignation pièce: LONGERON ARD Ref. client: 755128396R

        label
        ↓
        Désignation pièce:
                         ↓
                         LONGERON
                         ARD
                         ↓
                         prochain label

        Résultat :

            LONGERON ARD

    La fonction peut donc récupérer plusieurs mots.
    """

    label_right = _right_x(
        label
    )

    # ---------------------------------------------------------
    # Chercher le prochain label
    # ---------------------------------------------------------

    next_label = _find_next_label(
        label,
        field_labels,
    )

    if next_label:

        next_label_left = _left_x(
            next_label
        )

    else:

        next_label_left = float(
            "inf"
        )

    # ---------------------------------------------------------
    # Candidats
    # ---------------------------------------------------------

    candidates: list[
        dict[str, Any]
    ] = []

    label_word_set = _build_label_word_set(
        field_labels
    )

    for word in words:

        text = str(
            word.get(
                "text",
                "",
            )
        ).strip()

        if not text:
            continue

        # -----------------------------------------------------
        # Même ligne
        # -----------------------------------------------------

        if not same_line(
            label,
            word,
        ):
            continue

        # -----------------------------------------------------
        # Position
        # -----------------------------------------------------

        word_left = _left_x(
            word
        )

        word_right = _right_x(
            word
        )

        # Avant la fin du label
        if word_left < label_right:
            continue

        # Trop loin
        if (
            word_left
            - label_right
            > max_distance
        ):
            continue

        # Après le prochain label
        if word_left >= next_label_left:
            continue

        # -----------------------------------------------------
        # Ne pas prendre les mots connus comme labels
        # -----------------------------------------------------

        normalized = _normalize_text(
            text
        )

        if normalized in label_word_set:
            continue

        candidates.append(
            word
        )

    # ---------------------------------------------------------
    # Aucun candidat
    # ---------------------------------------------------------

    if not candidates:
        return None

    # ---------------------------------------------------------
    # Trier horizontalement
    # ---------------------------------------------------------

    candidates.sort(
        key=lambda word: (
            _left_x(word)
        )
    )

    # ---------------------------------------------------------
    # Construire la zone complète
    # ---------------------------------------------------------

    selected: list[
        dict[str, Any]
    ] = []

    previous_word = None

    for word in candidates:

        if previous_word is not None:

            # Distance entre les mots.
            gap = (
                _left_x(word)
                - _right_x(previous_word)
            )

            # Si le trou est énorme, on considère
            # qu'il s'agit probablement d'une autre zone.
            if gap > 300:

                break

        selected.append(
            word
        )

        previous_word = word

    if not selected:
        return None

    # ---------------------------------------------------------
    # Coordonnées globales
    # ---------------------------------------------------------

    min_x = min(
        _left_x(word)
        for word in selected
    )

    min_y = min(
        float(
            word.get(
                "y",
                0,
            )
        )
        for word in selected
    )

    max_x = max(
        _right_x(word)
        for word in selected
    )

    max_y = max(
        float(
            word.get(
                "y",
                0,
            )
        )
        + float(
            word.get(
                "height",
                0,
            )
        )
        for word in selected
    )

    # ---------------------------------------------------------
    # Texte complet
    # ---------------------------------------------------------

    value_text = " ".join(
        str(
            word.get(
                "text",
                "",
            )
        ).strip()
        for word in selected
    ).strip()

    # ---------------------------------------------------------
    # Confiance moyenne
    # ---------------------------------------------------------

    confidences = []

    for word in selected:

        try:

            confidence = float(
                word.get(
                    "confidence",
                    0,
                )
            )

            confidences.append(
                confidence
            )

        except (
            TypeError,
            ValueError,
        ):

            pass

    if confidences:

        average_confidence = (
            sum(confidences)
            / len(confidences)
        )

    else:

        average_confidence = 0.0

    # ---------------------------------------------------------
    # Score géométrique
    # ---------------------------------------------------------

    first_word = selected[0]

    geometry_score = coordinate_score(
        label,
        first_word,
    )

    # ---------------------------------------------------------
    # Score final
    # ---------------------------------------------------------

    confidence_score = (
        average_confidence
        / 100.0
    )

    final_score = (
        geometry_score * 0.70
        + confidence_score * 0.30
    )

    # ---------------------------------------------------------
    # Résultat
    # ---------------------------------------------------------

    return {
        "text": value_text,

        "x": min_x,
        "y": min_y,

        "width": (
            max_x - min_x
        ),

        "height": (
            max_y - min_y
        ),

        "words": selected,

        "word_count": len(
            selected
        ),

        "confidence": round(
            average_confidence,
            2,
        ),

        "coordinate_score": round(
            final_score,
            3,
        ),

        "geometry_score": round(
            geometry_score,
            3,
        ),

        "is_region": True,

        "next_label": (
            next_label.get(
                "text",
                "",
            )
            if next_label
            else None
        ),
    }


# =============================================================
# VALIDATION D'UNE POSITION
# =============================================================

def validate_field_position(
    label: dict[str, Any],
    value: dict[str, Any],
) -> dict[str, Any]:
    """
    Valide la position d'une zone de valeur.
    """

    same = same_line(
        label,
        value,
    )

    right = value_is_right_of(
        label,
        value,
    )

    score = (
        coordinate_score(
            label,
            value,
        )
        if same and right
        else 0.0
    )

    return {
        "valid": score > 0,
        "same_line": same,
        "right_of_label": right,
        "score": score,
    }


# =============================================================
# VALIDATION DE TOUS LES CHAMPS
# =============================================================

def validate_fields_coordinates(
    field_labels: dict[str, dict[str, Any]],
    words: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    Valide les champs en utilisant des zones
    de valeurs complètes.

    Exemple :

        Ref. SAP M400026D01 Ref. BE REN21-507 D

        devient :

        ref_sap -> M400026D01
        ref_be  -> REN21-507 D
    """

    results: dict[
        str,
        dict[str, Any],
    ] = {}

    for field_name, label in field_labels.items():

        value_region = find_value_region(
            label=label,
            words=words,
            field_labels=field_labels,
        )

        # -----------------------------------------------------
        # Valeur non trouvée
        # -----------------------------------------------------

        if value_region is None:

            results[field_name] = {
                "value": None,
                "valid": False,
                "confidence": 0,
                "coordinate_score": 0.0,
            }

            continue

        # -----------------------------------------------------
        # Validation
        # -----------------------------------------------------

        validation = validate_field_position(
            label,
            value_region,
        )

        # -----------------------------------------------------
        # Résultat
        # -----------------------------------------------------

        results[field_name] = {
            "value": value_region.get(
                "text",
                "",
            ),

            "valid": validation.get(
                "valid",
                False,
            ),

            "same_line": validation.get(
                "same_line",
                False,
            ),

            "right_of_label": validation.get(
                "right_of_label",
                False,
            ),

            "confidence": value_region.get(
                "confidence",
                0,
            ),

            "coordinate_score": value_region.get(
                "coordinate_score",
                0.0,
            ),

            "geometry_score": value_region.get(
                "geometry_score",
                0.0,
            ),

            "x": value_region.get(
                "x"
            ),

            "y": value_region.get(
                "y"
            ),

            "width": value_region.get(
                "width"
            ),

            "height": value_region.get(
                "height"
            ),

            "word_count": value_region.get(
                "word_count",
                0,
            ),

            "words": value_region.get(
                "words",
                [],
            ),

            "next_label": value_region.get(
                "next_label"
            ),

            "is_region": True,
        }

    return results