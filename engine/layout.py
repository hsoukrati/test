from __future__ import annotations

from typing import Any


def group_words_into_lines(
    words: list[dict[str, Any]],
    y_tolerance: int = 12,
) -> list[dict[str, Any]]:
    """
    Regroupe les mots OCR selon leur position verticale.

    Chaque mot doit contenir :
        text
        x
        y
        width
        height
        confidence
    """

    if not words:
        return []

    valid_words = []

    for word in words:
        text = str(word.get("text", "")).strip()

        if not text:
            continue

        valid_words.append(word)

    # On commence par trier verticalement.
    valid_words.sort(
        key=lambda item: (
            int(item.get("y", 0)),
            int(item.get("x", 0)),
        )
    )

    lines: list[list[dict[str, Any]]] = []

    for word in valid_words:

        y = int(word.get("y", 0))
        height = int(word.get("height", 0))

        word_center = y + height / 2

        placed = False

        for line in lines:

            line_centers = []

            for existing in line:
                existing_y = int(existing.get("y", 0))
                existing_height = int(
                    existing.get("height", 0)
                )

                center = (
                    existing_y
                    + existing_height / 2
                )

                line_centers.append(center)

            average_center = (
                sum(line_centers)
                / len(line_centers)
            )

            if abs(word_center - average_center) <= y_tolerance:
                line.append(word)
                placed = True
                break

        if not placed:
            lines.append([word])

    result = []

    for line_words in lines:

        # Trier horizontalement.
        line_words.sort(
            key=lambda item: int(
                item.get("x", 0)
            )
        )

        texts = []

        confidences = []

        for word in line_words:

            text = str(
                word.get("text", "")
            ).strip()

            if text:
                texts.append(text)

            try:
                confidence = float(
                    word.get(
                        "confidence",
                        -1,
                    )
                )

                if confidence >= 0:
                    confidences.append(
                        confidence
                    )

            except (TypeError, ValueError):
                pass

        if not texts:
            continue

        x_positions = [
            int(word.get("x", 0))
            for word in line_words
        ]

        y_positions = [
            int(word.get("y", 0))
            for word in line_words
        ]

        line_confidence = (
            sum(confidences)
            / len(confidences)
            if confidences
            else 0.0
        )

        result.append(
            {
                "text": " ".join(texts),
                "x": min(x_positions),
                "y": min(y_positions),
                "confidence": round(
                    line_confidence,
                    1,
                ),
                "words": line_words,
            }
        )

    # Trier les lignes finales de haut en bas.
    result.sort(
        key=lambda item: (
            item["y"],
            item["x"],
        )
    )

    return result


def lines_to_text(
    lines: list[dict[str, Any]],
) -> str:
    """
    Transforme les lignes reconstruites en texte.
    """

    return "\n".join(
        line["text"]
        for line in lines
        if line.get("text")
    )


def average_line_confidence(
    lines: list[dict[str, Any]],
) -> float:
    """
    Calcule la confiance moyenne des lignes.
    """

    values = []

    for line in lines:

        try:
            confidence = float(
                line.get(
                    "confidence",
                    0.0,
                )
            )

            if confidence >= 0:
                values.append(confidence)

        except (TypeError, ValueError):
            continue

    if not values:
        return 0.0

    return round(
        sum(values) / len(values),
        1,
    )