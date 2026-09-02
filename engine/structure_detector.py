from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re


# =============================================================
# CONFIGURATION
# =============================================================

DEFAULT_Y_TOLERANCE = 20.0
DEFAULT_X_GAP_TOLERANCE = 80.0
DEFAULT_COLUMN_TOLERANCE = 35.0
DEFAULT_MIN_WORDS_BLOCK = 1


# =============================================================
# TYPES
# =============================================================

@dataclass
class OCRWord:
    """
    Représente un mot OCR avec ses coordonnées.
    """

    text: str

    x: float
    y: float

    width: float
    height: float

    confidence: float = 0.0

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2.0

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2.0


@dataclass
class OCRLine:
    """
    Ligne OCR reconstruite.
    """

    words: list[OCRWord] = field(
        default_factory=list
    )

    @property
    def text(self) -> str:

        return " ".join(
            word.text
            for word in self.words
            if word.text.strip()
        ).strip()

    @property
    def x(self) -> float:

        if not self.words:
            return 0.0

        return min(
            word.x
            for word in self.words
        )

    @property
    def y(self) -> float:

        if not self.words:
            return 0.0

        return min(
            word.y
            for word in self.words
        )

    @property
    def right(self) -> float:

        if not self.words:
            return 0.0

        return max(
            word.right
            for word in self.words
        )

    @property
    def bottom(self) -> float:

        if not self.words:
            return 0.0

        return max(
            word.bottom
            for word in self.words
        )

    @property
    def width(self) -> float:

        return max(
            0.0,
            self.right - self.x,
        )

    @property
    def height(self) -> float:

        return max(
            0.0,
            self.bottom - self.y,
        )


@dataclass
class OCRBlock:
    """
    Bloc logique de texte.
    """

    lines: list[OCRLine] = field(
        default_factory=list
    )

    @property
    def text(self) -> str:

        return "\n".join(
            line.text
            for line in self.lines
            if line.text
        ).strip()

    @property
    def word_count(self) -> int:

        return sum(
            len(line.words)
            for line in self.lines
        )

    @property
    def line_count(self) -> int:

        return len(self.lines)

    @property
    def x(self) -> float:

        if not self.lines:
            return 0.0

        return min(
            line.x
            for line in self.lines
        )

    @property
    def y(self) -> float:

        if not self.lines:
            return 0.0

        return min(
            line.y
            for line in self.lines
        )

    @property
    def right(self) -> float:

        if not self.lines:
            return 0.0

        return max(
            line.right
            for line in self.lines
        )

    @property
    def bottom(self) -> float:

        if not self.lines:
            return 0.0

        return max(
            line.bottom
            for line in self.lines
        )

    @property
    def width(self) -> float:

        return max(
            0.0,
            self.right - self.x,
        )

    @property
    def height(self) -> float:

        return max(
            0.0,
            self.bottom - self.y,
        )


@dataclass
class StructureResult:
    """
    Résultat complet de l'analyse structurelle.
    """

    words: list[OCRWord]

    lines: list[OCRLine]

    blocks: list[OCRBlock]

    columns: list[list[OCRWord]]

    separators: list[dict[str, Any]]

    statistics: dict[str, Any]


# =============================================================
# CONVERSION DES MOTS OCR
# =============================================================

def convert_words(
    words: list[dict],
) -> list[OCRWord]:
    """
    Convertit les dictionnaires provenant de ocr.py
    vers OCRWord.

    Cette fonction accepte différents noms possibles
    pour la confiance OCR.
    """

    result: list[OCRWord] = []

    for word in words:

        text = str(
            word.get(
                "text",
                "",
            )
        ).strip()

        if not text:
            continue

        try:

            x = float(
                word.get(
                    "x",
                    0,
                )
            )

            y = float(
                word.get(
                    "y",
                    0,
                )
            )

            width = float(
                word.get(
                    "width",
                    0,
                )
            )

            height = float(
                word.get(
                    "height",
                    0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        confidence_value = word.get(
            "confidence",
            word.get(
                "conf",
                0,
            ),
        )

        try:

            confidence = float(
                confidence_value
            )

        except (
            TypeError,
            ValueError,
        ):

            confidence = 0.0

        result.append(
            OCRWord(
                text=text,
                x=x,
                y=y,
                width=width,
                height=height,
                confidence=confidence,
            )
        )

    # ---------------------------------------------------------
    # Tri spatial
    # ---------------------------------------------------------

    result.sort(
        key=lambda item: (
            item.y,
            item.x,
        )
    )

    return result


# =============================================================
# CONSTRUCTION DES LIGNES
# =============================================================

def build_lines(
    words: list[OCRWord],
    y_tolerance: float = DEFAULT_Y_TOLERANCE,
) -> list[OCRLine]:
    """
    Regroupe les mots qui appartiennent à la même ligne.
    """

    if not words:
        return []

    lines: list[OCRLine] = []

    # ---------------------------------------------------------
    # Parcours des mots
    # ---------------------------------------------------------

    for word in words:

        best_line: OCRLine | None = None

        best_distance = float(
            "inf"
        )

        for line in lines:

            if not line.words:
                continue

            center_y = sum(
                item.center_y
                for item in line.words
            ) / len(
                line.words
            )

            distance = abs(
                word.center_y
                - center_y
            )

            if distance <= y_tolerance:

                if distance < best_distance:

                    best_distance = distance

                    best_line = line

        if best_line is None:

            lines.append(
                OCRLine(
                    words=[word]
                )
            )

        else:

            best_line.words.append(
                word
            )

    # ---------------------------------------------------------
    # Tri des mots dans chaque ligne
    # ---------------------------------------------------------

    for line in lines:

        line.words.sort(
            key=lambda item: item.x
        )

    # ---------------------------------------------------------
    # Tri des lignes
    # ---------------------------------------------------------

    lines.sort(
        key=lambda item: item.y
    )

    return lines


# =============================================================
# DETECTION DES BLOCS
# =============================================================

def build_blocks(
    lines: list[OCRLine],
    vertical_gap: float | None = None,
) -> list[OCRBlock]:
    """
    Regroupe les lignes proches verticalement
    dans des blocs.
    """

    if not lines:
        return []

    if vertical_gap is None:

        heights = [
            line.height
            for line in lines
            if line.height > 0
        ]

        if heights:

            average_height = (
                sum(heights)
                / len(heights)
            )

            vertical_gap = max(
                25.0,
                average_height * 1.8,
            )

        else:

            vertical_gap = 30.0

    blocks: list[OCRBlock] = []

    current_block = OCRBlock(
        lines=[lines[0]]
    )

    for line in lines[1:]:

        previous = current_block.lines[
            -1
        ]

        gap = (
            line.y
            - previous.bottom
        )

        # -----------------------------------------------------
        # Même bloc
        # -----------------------------------------------------

        if gap <= vertical_gap:

            current_block.lines.append(
                line
            )

        # -----------------------------------------------------
        # Nouveau bloc
        # -----------------------------------------------------

        else:

            blocks.append(
                current_block
            )

            current_block = OCRBlock(
                lines=[line]
            )

    if current_block.lines:

        blocks.append(
            current_block
        )

    return blocks


# =============================================================
# DETECTION DES COLONNES
# =============================================================

def build_columns(
    words: list[OCRWord],
    tolerance: float = DEFAULT_COLUMN_TOLERANCE,
) -> list[list[OCRWord]]:
    """
    Détecte les groupes de mots ayant des positions X
    similaires.

    Ce n'est pas encore une détection complète de tableau.
    C'est une analyse géométrique générale.
    """

    if not words:
        return []

    columns: list[list[OCRWord]] = []

    for word in sorted(
        words,
        key=lambda item: item.center_x,
    ):

        best_column: list[OCRWord] | None = None

        best_distance = float(
            "inf"
        )

        for column in columns:

            average_x = sum(
                item.center_x
                for item in column
            ) / len(
                column
            )

            distance = abs(
                word.center_x
                - average_x
            )

            if (
                distance <= tolerance
                and distance < best_distance
            ):

                best_distance = distance
                best_column = column

        if best_column is None:

            columns.append(
                [word]
            )

        else:

            best_column.append(
                word
            )

    columns.sort(
        key=lambda column: min(
            word.center_x
            for word in column
        )
    )

    return columns


# =============================================================
# DETECTION DES SEPARATEURS
# =============================================================

def detect_separators(
    words: list[OCRWord],
    lines: list[OCRLine],
) -> list[dict[str, Any]]:
    """
    Détecte les séparateurs textuels.

    Exemples :

        ----------
        ==========
        __________
        | | | |
        +---+---+
    """

    separators: list[dict[str, Any]] = []

    # ---------------------------------------------------------
    # Séparateurs provenant des lignes
    # ---------------------------------------------------------

    for index, line in enumerate(
        lines
    ):

        text = line.text

        if not text:
            continue

        # -----------------------------------------------------
        # Ligne composée principalement de séparateurs
        # -----------------------------------------------------

        compact = re.sub(
            r"\s+",
            "",
            text,
        )

        if len(compact) >= 3:

            separator_characters = sum(
                1
                for char in compact
                if char in "-_=|+"
            )

            ratio = (
                separator_characters
                / len(compact)
            )

            if ratio >= 0.60:

                separators.append(
                    {
                        "type": "horizontal",
                        "line_index": index,
                        "text": text,
                        "x": line.x,
                        "y": line.y,
                        "width": line.width,
                        "height": line.height,
                    }
                )

    # ---------------------------------------------------------
    # Mots contenant des séparateurs
    # ---------------------------------------------------------

    for index, word in enumerate(
        words
    ):

        text = word.text.strip()

        if not text:
            continue

        if re.fullmatch(
            r"[\-_=|+]{2,}",
            text,
        ):

            separators.append(
                {
                    "type": "symbol",
                    "word_index": index,
                    "text": text,
                    "x": word.x,
                    "y": word.y,
                    "width": word.width,
                    "height": word.height,
                }
            )

    return separators


# =============================================================
# DETECTION LABEL : VALEUR
# =============================================================

def detect_label_value_lines(
    lines: list[OCRLine],
) -> list[dict[str, Any]]:
    """
    Détecte les lignes ayant une structure :

        Label : Valeur

    ou :

        Label: Valeur
    """

    result = []

    for index, line in enumerate(
        lines
    ):

        text = line.text.strip()

        if ":" not in text:
            continue

        parts = text.split(
            ":",
            1,
        )

        label = parts[0].strip()
        value = parts[1].strip()

        if not label:
            continue

        result.append(
            {
                "line_index": index,
                "label": label,
                "value": value,
                "text": text,
            }
        )

    return result


# =============================================================
# STATISTIQUES STRUCTURELLES
# =============================================================

def calculate_statistics(
    words: list[OCRWord],
    lines: list[OCRLine],
    blocks: list[OCRBlock],
    columns: list[list[OCRWord]],
    separators: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calcule des statistiques générales.
    """

    word_count = len(
        words
    )

    line_count = len(
        lines
    )

    block_count = len(
        blocks
    )

    column_count = len(
        columns
    )

    separator_count = len(
        separators
    )

    character_count = sum(
        len(word.text)
        for word in words
    )

    line_lengths = [
        len(line.text)
        for line in lines
        if line.text
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
        if 1 <= length <= 20
    )

    colon_lines = sum(
        1
        for line in lines
        if ":" in line.text
    )

    # ---------------------------------------------------------
    # Confiance moyenne
    # ---------------------------------------------------------

    confidences = [
        word.confidence
        for word in words
        if word.confidence > 0
    ]

    average_confidence = (
        sum(confidences)
        / len(confidences)
        if confidences
        else 0.0
    )

    # ---------------------------------------------------------
    # Largeur moyenne des mots
    # ---------------------------------------------------------

    word_widths = [
        word.width
        for word in words
        if word.width > 0
    ]

    average_word_width = (
        sum(word_widths)
        / len(word_widths)
        if word_widths
        else 0.0
    )

    return {
        "word_count":
            word_count,

        "line_count":
            line_count,

        "block_count":
            block_count,

        "column_count":
            column_count,

        "separator_count":
            separator_count,

        "character_count":
            character_count,

        "average_line_length":
            round(
                average_line_length,
                3,
            ),

        "long_lines":
            long_lines,

        "short_lines":
            short_lines,

        "colon_lines":
            colon_lines,

        "average_confidence":
            round(
                average_confidence,
                3,
            ),

        "average_word_width":
            round(
                average_word_width,
                3,
            ),
    }


# =============================================================
# ANALYSE STRUCTURELLE PRINCIPALE
# =============================================================

def analyze_structure(
    words: list[dict],
    lines: list[Any] | None = None,
    *,
    y_tolerance: float = DEFAULT_Y_TOLERANCE,
    column_tolerance: float = DEFAULT_COLUMN_TOLERANCE,
) -> StructureResult:
    """
    Analyse la structure spatiale d'un résultat OCR.

    Fonctionnement :

        mots OCR
            ↓
        lignes
            ↓
        blocs
            ↓
        colonnes
            ↓
        séparateurs
            ↓
        statistiques

    Cette fonction ne connaît aucun champ métier.
    """

    # ---------------------------------------------------------
    # Conversion mots
    # ---------------------------------------------------------

    ocr_words = convert_words(
        words
    )

    # ---------------------------------------------------------
    # Lignes
    # ---------------------------------------------------------

    if lines:

        # Si les lignes viennent déjà de layout.py,
        # nous reconstruisons tout de même les lignes
        # à partir des mots pour conserver une structure
        # homogène.

        ocr_lines = build_lines(
            ocr_words,
            y_tolerance=y_tolerance,
        )

    else:

        ocr_lines = build_lines(
            ocr_words,
            y_tolerance=y_tolerance,
        )

    # ---------------------------------------------------------
    # Blocs
    # ---------------------------------------------------------

    blocks = build_blocks(
        ocr_lines
    )

    # ---------------------------------------------------------
    # Colonnes
    # ---------------------------------------------------------

    columns = build_columns(
        ocr_words,
        tolerance=column_tolerance,
    )

    # ---------------------------------------------------------
    # Séparateurs
    # ---------------------------------------------------------

    separators = detect_separators(
        ocr_words,
        ocr_lines,
    )

    # ---------------------------------------------------------
    # Statistiques
    # ---------------------------------------------------------

    statistics = calculate_statistics(
        ocr_words,
        ocr_lines,
        blocks,
        columns,
        separators,
    )

    return StructureResult(
        words=ocr_words,
        lines=ocr_lines,
        blocks=blocks,
        columns=columns,
        separators=separators,
        statistics=statistics,
    )


# =============================================================
# AFFICHAGE
# =============================================================

def print_structure(
    result: StructureResult,
) -> None:

    print(
        "\n"
        + "=" * 70
    )

    print(
        "ANALYSE STRUCTURELLE OCR"
    )

    print(
        "=" * 70
    )

    # ---------------------------------------------------------
    # Statistiques
    # ---------------------------------------------------------

    print(
        "\nStatistiques :"
    )

    for key, value in result.statistics.items():

        print(
            f"  {key:<25} : "
            f"{value}"
        )

    # ---------------------------------------------------------
    # Lignes
    # ---------------------------------------------------------

    print(
        "\nLignes :"
    )

    if not result.lines:

        print(
            "  Aucune ligne."
        )

    else:

        for index, line in enumerate(
            result.lines,
            start=1,
        ):

            print(
                f"  [{index:03d}] "
                f"x={line.x:7.1f} "
                f"y={line.y:7.1f} "
                f"w={line.width:7.1f} "
                f"h={line.height:7.1f} "
                f"| {line.text}"
            )

    # ---------------------------------------------------------
    # Blocs
    # ---------------------------------------------------------

    print(
        "\nBlocs :"
    )

    if not result.blocks:

        print(
            "  Aucun bloc."
        )

    else:

        for index, block in enumerate(
            result.blocks,
            start=1,
        ):

            print(
                f"  Bloc {index}: "
                f"{block.line_count} lignes, "
                f"{block.word_count} mots, "
                f"x={block.x:.1f}, "
                f"y={block.y:.1f}, "
                f"w={block.width:.1f}, "
                f"h={block.height:.1f}"
            )

            print(
                f"      {block.text.replace(chr(10), ' | ')}"
            )

    # ---------------------------------------------------------
    # Colonnes
    # ---------------------------------------------------------

    print(
        "\nColonnes détectées :"
    )

    if not result.columns:

        print(
            "  Aucune colonne."
        )

    else:

        for index, column in enumerate(
            result.columns,
            start=1,
        ):

            texts = [
                word.text
                for word in column
            ]

            average_x = sum(
                word.center_x
                for word in column
            ) / len(
                column
            )

            print(
                f"  Colonne {index}: "
                f"x_moyen={average_x:.1f} "
                f"mots={len(column)} "
                f"| {' | '.join(texts)}"
            )

    # ---------------------------------------------------------
    # Séparateurs
    # ---------------------------------------------------------

    print(
        "\nSéparateurs :"
    )

    if not result.separators:

        print(
            "  Aucun séparateur."
        )

    else:

        for separator in result.separators:

            print(
                f"  {separator}"
            )

    # ---------------------------------------------------------
    # Labels / valeurs
    # ---------------------------------------------------------

    label_values = detect_label_value_lines(
        result.lines
    )

    print(
        "\nStructures label : valeur :"
    )

    if not label_values:

        print(
            "  Aucune structure label/valeur détectée."
        )

    else:

        for item in label_values:

            print(
                f"  Ligne {item['line_index'] + 1}: "
                f"label='{item['label']}' "
                f"value='{item['value']}'"
            )


# =============================================================
# TEST DIRECT
# =============================================================

if __name__ == "__main__":

    print(
        "=" * 70
    )

    print(
        "TEST STRUCTURE DETECTOR OCR"
    )

    print(
        "=" * 70
    )

    # ---------------------------------------------------------
    # Exemple générique
    # ---------------------------------------------------------

    test_words = [

        {
            "text": "Fiche",
            "x": 100,
            "y": 50,
            "width": 60,
            "height": 20,
            "confidence": 95,
        },

        {
            "text": "technique",
            "x": 170,
            "y": 50,
            "width": 100,
            "height": 20,
            "confidence": 94,
        },

        {
            "text": "Ref:",
            "x": 100,
            "y": 100,
            "width": 40,
            "height": 20,
            "confidence": 92,
        },

        {
            "text": "ABC123",
            "x": 180,
            "y": 100,
            "width": 80,
            "height": 20,
            "confidence": 93,
        },

        {
            "text": "Client:",
            "x": 100,
            "y": 140,
            "width": 55,
            "height": 20,
            "confidence": 90,
        },

        {
            "text": "Renault",
            "x": 180,
            "y": 140,
            "width": 75,
            "height": 20,
            "confidence": 91,
        },

        {
            "text": "Date:",
            "x": 100,
            "y": 180,
            "width": 45,
            "height": 20,
            "confidence": 94,
        },

        {
            "text": "31/08/2026",
            "x": 180,
            "y": 180,
            "width": 100,
            "height": 20,
            "confidence": 94,
        },

        {
            "text": "Produit",
            "x": 100,
            "y": 260,
            "width": 70,
            "height": 20,
            "confidence": 92,
        },

        {
            "text": "Quantite",
            "x": 300,
            "y": 260,
            "width": 80,
            "height": 20,
            "confidence": 91,
        },

        {
            "text": "ABC",
            "x": 100,
            "y": 300,
            "width": 50,
            "height": 20,
            "confidence": 92,
        },

        {
            "text": "10",
            "x": 300,
            "y": 300,
            "width": 25,
            "height": 20,
            "confidence": 93,
        },
    ]

    # ---------------------------------------------------------
    # Analyse
    # ---------------------------------------------------------

    result = analyze_structure(
        test_words
    )

    # ---------------------------------------------------------
    # Affichage
    # ---------------------------------------------------------

    print_structure(
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
def detect_structure(words, lines=None):
    """
    Wrapper public utilisé par document_parser.py.

    Pipeline OCR générique sans IA.
    """
    if lines is None:
        lines = []

    return analyze_structure(
        words=words,
        lines=lines,
    )