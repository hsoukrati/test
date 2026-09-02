
from __future__ import annotations

"""
FIELD EXTRACTOR OCR
=============================================================

Extracteur générique de champs.

IMPORTANT
---------
Aucun champ métier n'est codé en dur.

Il ne connaît pas :
    Réf. SAP
    Réf. BE
    Client
    Atelier
    N° OP
    etc.

Il cherche uniquement des relations génériques :

    LABEL : VALEUR
    LABEL = VALEUR
    LABEL - VALEUR
    LABEL    VALEUR

et des relations spatiales basées sur les coordonnées OCR.
"""

import re

from dataclasses import dataclass
from typing import Any


# =============================================================
# CONFIGURATION
# =============================================================

DEFAULT_MIN_LABEL_LENGTH = 1
DEFAULT_MAX_LABEL_LENGTH = 100
DEFAULT_MAX_VALUE_LENGTH = 1000

DEFAULT_HORIZONTAL_DISTANCE = 800.0
DEFAULT_VERTICAL_DISTANCE = 150.0

DEFAULT_MIN_WORD_CONFIDENCE = 15.0


# =============================================================
# REGEX
# =============================================================

COLON_PATTERN = re.compile(
    r"^\s*(.+?)\s*:\s*(.+?)\s*$"
)

EQUAL_PATTERN = re.compile(
    r"^\s*(.+?)\s*=\s*(.+?)\s*$"
)

DASH_PATTERN = re.compile(
    r"^\s*(.+?)\s+-\s+(.+?)\s*$"
)


# =============================================================
# TYPES
# =============================================================

@dataclass
class ExtractedField:

    label: str

    value: str

    page_number: int | None = None

    x: float = 0.0

    y: float = 0.0

    width: float = 0.0

    height: float = 0.0

    confidence: float = 0.0

    source: str = "ocr"


# =============================================================
# TEXTE
# =============================================================

def clean_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    text = str(value)

    text = text.replace(
        "\r",
        " ",
    )

    text = text.replace(
        "\n",
        " ",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# =============================================================
# NORMALISATION LABEL
# =============================================================

def normalize_label(
    label: str,
) -> str:

    label = clean_text(
        label
    )

    label = label.rstrip(
        ":=;- "
    )

    return label.strip()


# =============================================================
# NORMALISATION VALEUR
# =============================================================

def normalize_value(
    value: str,
) -> str:

    value = clean_text(
        value
    )

    value = value.strip(
        " \t:;=-"
    )

    return value


# =============================================================
# VALIDATION LABEL
# =============================================================

def is_valid_label(
    label: str,
) -> bool:

    label = normalize_label(
        label
    )

    if not label:
        return False

    if len(label) < DEFAULT_MIN_LABEL_LENGTH:
        return False

    if len(label) > DEFAULT_MAX_LABEL_LENGTH:
        return False

    # ---------------------------------------------------------
    # Uniquement numérique = probablement une valeur
    # ---------------------------------------------------------

    if re.fullmatch(
        r"[\d\s.,:/\\\-]+",
        label,
    ):
        return False

    # ---------------------------------------------------------
    # Le label doit contenir au moins une lettre
    # ---------------------------------------------------------

    if not re.search(
        r"[A-Za-zÀ-ÖØ-öø-ÿ]",
        label,
    ):
        return False

    return True


# =============================================================
# VALIDATION VALEUR
# =============================================================

def is_valid_value(
    value: str,
) -> bool:

    value = normalize_value(
        value
    )

    if not value:
        return False

    if len(value) > DEFAULT_MAX_VALUE_LENGTH:
        return False

    return True


# =============================================================
# VALEUR PROBABLE
# =============================================================

def looks_like_value(
    text: str,
) -> bool:
    """
    Détermine si un mot ressemble à une valeur.

    Exemples :

        ABC123
        M000684G01
        123456
        31/08/2026
        25.50
        REN25-139A-ASJ

    """

    text = clean_text(
        text
    )

    if not text:
        return False

    # ---------------------------------------------------------
    # Date
    # ---------------------------------------------------------

    if re.fullmatch(
        r"\d{1,4}[/-]\d{1,2}[/-]\d{1,4}",
        text,
    ):
        return True

    # ---------------------------------------------------------
    # Nombre
    # ---------------------------------------------------------

    if re.fullmatch(
        r"[\d.,]+",
        text,
    ):
        return True

    # ---------------------------------------------------------
    # Code alphanumérique
    # ---------------------------------------------------------

    if re.fullmatch(
        r"[A-Za-z]+\d+[A-Za-z0-9._/-]*",
        text,
    ):
        return True

    # ---------------------------------------------------------
    # Code commençant par chiffres
    # ---------------------------------------------------------

    if re.fullmatch(
        r"\d+[A-Za-z][A-Za-z0-9._/-]*",
        text,
    ):
        return True

    # ---------------------------------------------------------
    # Code contenant chiffres + tiret
    # ---------------------------------------------------------

    if (
        re.search(r"\d", text)
        and re.search(r"[-_/]", text)
    ):
        return True

    # ---------------------------------------------------------
    # Téléphone
    # ---------------------------------------------------------

    if re.fullmatch(
        r"[+()\d][\d\s()./-]{5,}",
        text,
    ):
        return True

    return False


# =============================================================
# GEOMETRIE
# =============================================================

def word_box(
    word: dict,
) -> tuple[
    float,
    float,
    float,
    float,
]:

    x = float(
        word.get("x", 0.0)
        or 0.0
    )

    y = float(
        word.get("y", 0.0)
        or 0.0
    )

    width = float(
        word.get("width", 0.0)
        or 0.0
    )

    height = float(
        word.get("height", 0.0)
        or 0.0
    )

    return (
        x,
        y,
        width,
        height,
    )


def word_center(
    word: dict,
) -> tuple[float, float]:

    x, y, width, height = word_box(
        word
    )

    return (
        x + width / 2.0,
        y + height / 2.0,
    )


def word_right(
    word: dict,
) -> float:

    x, _, width, _ = word_box(
        word
    )

    return x + width


def word_bottom(
    word: dict,
) -> float:

    _, y, _, height = word_box(
        word
    )

    return y + height


# =============================================================
# CONFIANCE
# =============================================================

def get_word_confidence(
    word: dict,
) -> float:

    value = word.get(
        "confidence",
        word.get(
            "conf",
            0.0,
        ),
    )

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return 0.0


# =============================================================
# EXTRACTION EXPLICITE
# =============================================================

def _extract_pattern_fields(
    lines: list[Any],
    pattern: re.Pattern,
    source: str,
) -> list[ExtractedField]:

    fields = []

    for line in lines:

        if isinstance(
            line,
            dict,
        ):

            text = clean_text(
                line.get(
                    "text",
                    "",
                )
            )

            x = float(
                line.get(
                    "x",
                    0.0,
                )
                or 0.0
            )

            y = float(
                line.get(
                    "y",
                    0.0,
                )
                or 0.0
            )

            width = float(
                line.get(
                    "width",
                    0.0,
                )
                or 0.0
            )

            height = float(
                line.get(
                    "height",
                    0.0,
                )
                or 0.0
            )

            confidence = get_word_confidence(
                line
            )

            page_number = line.get(
                "page_number"
            )

        else:

            text = clean_text(
                line
            )

            x = 0.0
            y = 0.0
            width = 0.0
            height = 0.0
            confidence = 0.0
            page_number = None

        if not text:
            continue

        match = pattern.match(
            text
        )

        if not match:
            continue

        label = normalize_label(
            match.group(1)
        )

        value = normalize_value(
            match.group(2)
        )

        if not is_valid_label(
            label
        ):
            continue

        if not is_valid_value(
            value
        ):
            continue

        fields.append(
            ExtractedField(
                label=label,
                value=value,
                page_number=page_number,
                x=x,
                y=y,
                width=width,
                height=height,
                confidence=confidence,
                source=source,
            )
        )

    return fields


# =============================================================
# COLON
# =============================================================

def extract_colon_fields_from_lines(
    lines: list[Any],
) -> list[ExtractedField]:

    return _extract_pattern_fields(
        lines,
        COLON_PATTERN,
        "label_colon_value",
    )


# =============================================================
# EQUAL
# =============================================================

def extract_equal_fields_from_lines(
    lines: list[Any],
) -> list[ExtractedField]:

    return _extract_pattern_fields(
        lines,
        EQUAL_PATTERN,
        "label_equal_value",
    )


# =============================================================
# DASH
# =============================================================

def extract_dash_fields_from_lines(
    lines: list[Any],
) -> list[ExtractedField]:

    return _extract_pattern_fields(
        lines,
        DASH_PATTERN,
        "label_dash_value",
    )


# =============================================================
# EXTRACTION SPATIALE
# =============================================================

def extract_spatial_fields(
    words: list[dict],
    max_horizontal_distance: float = DEFAULT_HORIZONTAL_DISTANCE,
    max_vertical_distance: float = DEFAULT_VERTICAL_DISTANCE,
) -> list[ExtractedField]:
    """
    Détecte :

        LABEL -> VALEUR

    lorsque le OCR les sépare en mots.

    Exemple :

        Client          Renault

    ou :

        Réf. SAP        M000684G01
    """

    if not words:
        return []

    valid_words = []

    for word in words:

        if not isinstance(
            word,
            dict,
        ):
            continue

        text = clean_text(
            word.get(
                "text",
                "",
            )
        )

        if not text:
            continue

        confidence = get_word_confidence(
            word
        )

        if confidence < DEFAULT_MIN_WORD_CONFIDENCE:
            continue

        valid_words.append(
            word
        )

    if len(valid_words) < 2:
        return []

    candidates = []

    # =========================================================
    # RECHERCHE LABEL -> VALEUR
    # =========================================================

    for label_index, label_word in enumerate(
        valid_words
    ):

        label_text = clean_text(
            label_word.get(
                "text",
                "",
            )
        )

        if not is_valid_label(
            label_text
        ):
            continue

        if looks_like_value(
            label_text
        ):
            continue

        label_x, label_y = word_center(
            label_word
        )

        label_right = word_right(
            label_word
        )

        label_bottom = word_bottom(
            label_word
        )

        best_candidate = None
        best_score = float("inf")

        # =====================================================
        # RECHERCHE VALEUR
        # =====================================================

        for value_index, value_word in enumerate(
            valid_words
        ):

            if value_index == label_index:
                continue

            value_text = clean_text(
                value_word.get(
                    "text",
                    "",
                )
            )

            if not is_valid_value(
                value_text
            ):
                continue

            if (
                value_text.lower()
                == label_text.lower()
            ):
                continue

            value_x, value_y = word_center(
                value_word
            )

            value_left = word_box(
                value_word
            )[0]

            value_top = word_box(
                value_word
            )[1]

            # =================================================
            # CAS A : VALEUR A DROITE
            # =================================================

            horizontal_distance = (
                value_left
                - label_right
            )

            vertical_distance = abs(
                value_y
                - label_y
            )

            if (
                horizontal_distance >= 0
                and horizontal_distance
                <= max_horizontal_distance
                and vertical_distance
                <= max_vertical_distance
            ):

                score = (
                    horizontal_distance
                    + vertical_distance * 2.0
                )

                if score < best_score:

                    best_score = score

                    best_candidate = (
                        value_word,
                        value_index,
                        "right",
                    )

            # =================================================
            # CAS B : VALEUR SOUS LE LABEL
            # =================================================

            vertical_gap = (
                value_top
                - label_bottom
            )

            horizontal_alignment = abs(
                value_x
                - label_x
            )

            if (
                vertical_gap >= 0
                and vertical_gap
                <= max_vertical_distance
                and horizontal_alignment
                <= max_horizontal_distance
            ):

                score = (
                    vertical_gap * 2.0
                    + horizontal_alignment
                )

                if score < best_score:

                    best_score = score

                    best_candidate = (
                        value_word,
                        value_index,
                        "below",
                    )

        if best_candidate is None:
            continue

        (
            value_word,
            value_index,
            relation,
        ) = best_candidate

        value_text = clean_text(
            value_word.get(
                "text",
                "",
            )
        )

        if not value_text:
            continue

        x, y, width, height = word_box(
            label_word
        )

        confidence = (
            get_word_confidence(
                label_word
            )
            +
            get_word_confidence(
                value_word
            )
        ) / 2.0

        candidates.append(
            {
                "label": label_text,
                "value": value_text,
                "score": best_score,
                "confidence": confidence,
                "label_index": label_index,
                "value_index": value_index,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "source": (
                    f"spatial_{relation}"
                ),
            }
        )

    # =========================================================
    # TRI
    # =========================================================

    candidates.sort(
        key=lambda item: (
            item["score"],
            -item["confidence"],
        )
    )

    # =========================================================
    # RESERVATION
    # =========================================================

    used_labels: set[int] = set()
    used_values: set[int] = set()

    fields = []

    for candidate in candidates:

        label_index = candidate[
            "label_index"
        ]

        value_index = candidate[
            "value_index"
        ]

        if label_index in used_values:
            continue

        if value_index in used_values:
            continue

        if label_index in used_labels:
            continue

        used_labels.add(
            label_index
        )

        used_values.add(
            value_index
        )

        fields.append(
            ExtractedField(
                label=candidate["label"],
                value=candidate["value"],
                x=candidate["x"],
                y=candidate["y"],
                width=candidate["width"],
                height=candidate["height"],
                confidence=candidate[
                    "confidence"
                ],
                source=candidate[
                    "source"
                ],
            )
        )

    return fields


# =============================================================
# DEDUPLICATION
# =============================================================

def deduplicate_fields(
    fields: list[ExtractedField],
) -> list[ExtractedField]:

    grouped = {}

    for field in fields:

        label = normalize_label(
            field.label
        )

        value = normalize_value(
            field.value
        )

        if not label or not value:
            continue

        key = (
            label.lower(),
            value.lower(),
        )

        current = grouped.get(
            key
        )

        if current is None:

            grouped[key] = field

        elif (
            field.confidence
            > current.confidence
        ):

            grouped[key] = field

    return list(
        grouped.values()
    )


# =============================================================
# DICTIONNAIRE
# =============================================================

def fields_to_dict(
    fields: list[ExtractedField],
) -> dict[str, Any]:

    result = {}

    for field in fields:

        label = normalize_label(
            field.label
        )

        value = normalize_value(
            field.value
        )

        if not label or not value:
            continue

        if label not in result:

            result[label] = value

            continue

        current = result[label]

        if isinstance(
            current,
            list,
        ):

            if value not in current:

                current.append(
                    value
                )

        else:

            if current != value:

                result[label] = [
                    current,
                    value,
                ]

    return result


# =============================================================
# EXTRACTION PRINCIPALE
# =============================================================

def extract_fields(
    words: list[dict] | None = None,
    lines: list[Any] | None = None,
) -> dict:

    words = words or []
    lines = lines or []

    all_fields = []

    # =========================================================
    # 1. LABEL : VALUE
    # =========================================================

    colon_fields = (
        extract_colon_fields_from_lines(
            lines
        )
    )

    all_fields.extend(
        colon_fields
    )

    # =========================================================
    # 2. LABEL = VALUE
    # =========================================================

    equal_fields = (
        extract_equal_fields_from_lines(
            lines
        )
    )

    all_fields.extend(
        equal_fields
    )

    # =========================================================
    # 3. LABEL - VALUE
    # =========================================================

    dash_fields = (
        extract_dash_fields_from_lines(
            lines
        )
    )

    all_fields.extend(
        dash_fields
    )

    # =========================================================
    # 4. SPATIAL
    # =========================================================

    spatial_fields = (
        extract_spatial_fields(
            words
        )
    )

    # =========================================================
    # RELATIONS EXPLICITES PRIORITAIRES
    # =========================================================

    explicit_pairs = {

        (
            field.label.lower(),
            field.value.lower(),
        )

        for field in (
            colon_fields
            + equal_fields
            + dash_fields
        )
    }

    filtered_spatial = []

    for field in spatial_fields:

        pair = (
            field.label.lower(),
            field.value.lower(),
        )

        if pair in explicit_pairs:
            continue

        filtered_spatial.append(
            field
        )

    all_fields.extend(
        filtered_spatial
    )

    # =========================================================
    # 5. DOUBLONS
    # =========================================================

    unique_fields = deduplicate_fields(
        all_fields
    )

    # =========================================================
    # 6. DICTIONNAIRE
    # =========================================================

    fields_dict = fields_to_dict(
        unique_fields
    )

    # =========================================================
    # 7. LISTE DETAILLEE
    # =========================================================

    field_list = []

    for field in unique_fields:

        field_list.append(
            {
                "label": field.label,
                "value": field.value,
                "page_number":
                    field.page_number,
                "x": field.x,
                "y": field.y,
                "width": field.width,
                "height": field.height,
                "confidence":
                    field.confidence,
                "source": field.source,
            }
        )

    return {

        "fields":
            fields_dict,

        "field_list":
            field_list,

        "count":
            len(unique_fields),

        "methods": {

            "colon":
                len(colon_fields),

            "equal":
                len(equal_fields),

            "dash":
                len(dash_fields),

            "spatial":
                len(filtered_spatial),
        },
    }


# =============================================================
# OCR RESULT
# =============================================================

def extract_from_ocr_result(
    ocr_result: dict,
) -> dict:

    if not isinstance(
        ocr_result,
        dict,
    ):

        raise TypeError(
            "ocr_result doit être "
            "un dictionnaire."
        )

    return extract_fields(
        words=ocr_result.get(
            "words",
            [],
        ),
        lines=ocr_result.get(
            "lines",
            [],
        ),
    )


# =============================================================
# TEST
# =============================================================

def run_test() -> None:

    print("=" * 70)
    print(
        "TEST FIELD EXTRACTOR"
    )
    print("=" * 70)

    lines = [

        {
            "text":
                "Fiche technique",
            "x": 100,
            "y": 50,
            "width": 200,
            "height": 20,
            "confidence": 95,
        },

        {
            "text":
                "Réf. SAP: M000684G01",
            "x": 100,
            "y": 100,
            "width": 250,
            "height": 20,
            "confidence": 95,
        },

        {
            "text":
                "Réf. BE: REN25-139A-ASJ",
            "x": 100,
            "y": 140,
            "width": 300,
            "height": 20,
            "confidence": 94,
        },

        {
            "text":
                "Indice doc: 1",
            "x": 100,
            "y": 180,
            "width": 180,
            "height": 20,
            "confidence": 96,
        },

        {
            "text":
                "Réf. client: 759413876R",
            "x": 100,
            "y": 220,
            "width": 280,
            "height": 20,
            "confidence": 93,
        },

        {
            "text":
                "N° OP: 30",
            "x": 100,
            "y": 260,
            "width": 150,
            "height": 20,
            "confidence": 92,
        },
    ]

    result = extract_fields(
        lines=lines
    )

    print()
    print("Champs :")

    for label, value in result[
        "fields"
    ].items():

        print(
            f"{label} : {value}"
        )

    print()
    print(
        f"Nombre : "
        f"{result['count']}"
    )


if __name__ == "__main__":
    run_test()

