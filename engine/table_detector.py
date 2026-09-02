
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Any


# =============================================================
# CONFIGURATION
# =============================================================

DEFAULT_Y_TOLERANCE = 15.0

DEFAULT_COLUMN_TOLERANCE = 45.0

DEFAULT_MIN_ROWS = 2

DEFAULT_MIN_COLUMNS = 2

DEFAULT_MIN_WORDS = 4


# =============================================================
# TYPES
# =============================================================

@dataclass
class OCRWord:
    """
    Représente un mot OCR avec sa géométrie.
    """

    text: str

    x: float
    y: float

    width: float
    height: float

    confidence: float = 0.0

    @property
    def x2(self) -> float:
        return self.x + self.width

    @property
    def y2(self) -> float:
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
    Ligne reconstruite à partir de mots OCR.
    """

    words: list[OCRWord] = field(
        default_factory=list
    )

    @property
    def text(self) -> str:
        return " ".join(
            word.text
            for word in self.words
            if word.text
        )

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
    def x2(self) -> float:
        if not self.words:
            return 0.0

        return max(
            word.x2
            for word in self.words
        )

    @property
    def y2(self) -> float:
        if not self.words:
            return 0.0

        return max(
            word.y2
            for word in self.words
        )

    @property
    def width(self) -> float:
        return self.x2 - self.x

    @property
    def height(self) -> float:
        return self.y2 - self.y


@dataclass
class TableCell:
    """
    Cellule logique d'un tableau.
    """

    row: int

    column: int

    text: str

    words: list[dict]

    x: float

    y: float

    width: float

    height: float

    confidence: float


@dataclass
class TableColumn:
    """
    Colonne détectée.
    """

    index: int

    x_center: float

    word_count: int

    words: list[str]


@dataclass
class TableRow:
    """
    Ligne détectée.
    """

    index: int

    y_center: float

    word_count: int

    words: list[str]


@dataclass
class DetectedTable:
    """
    Tableau détecté dans une page.
    """

    rows: list[TableRow]

    columns: list[TableColumn]

    cells: list[TableCell]

    x: float

    y: float

    width: float

    height: float

    score: float

    confidence: float

    has_header: bool = False

    header_row: int | None = None

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def column_count(self) -> int:
        return len(self.columns)

    @property
    def cell_count(self) -> int:
        return len(self.cells)


# =============================================================
# CONVERSION MOT OCR
# =============================================================

def convert_word(
    word: dict,
) -> OCRWord | None:
    """
    Convertit un dictionnaire OCR en OCRWord.

    Format attendu :

        {
            "text": "...",
            "x": ...,
            "y": ...,
            "width": ...,
            "height": ...,
            "confidence": ...
        }
    """

    if not isinstance(
        word,
        dict,
    ):
        return None

    text = str(
        word.get(
            "text",
            "",
        )
    ).strip()

    if not text:
        return None

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

        confidence = float(
            word.get(
                "confidence",
                word.get(
                    "conf",
                    0,
                ),
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return None

    if width <= 0:
        return None

    if height <= 0:
        return None

    return OCRWord(
        text=text,
        x=x,
        y=y,
        width=width,
        height=height,
        confidence=confidence,
    )


# =============================================================
# CONVERSION LISTE OCR
# =============================================================

def convert_words(
    words: list[dict],
) -> list[OCRWord]:
    """
    Convertit les mots OCR en objets géométriques.
    """

    result = []

    for word in words:

        converted = convert_word(
            word
        )

        if converted is not None:

            result.append(
                converted
            )

    return result


# =============================================================
# RECONSTRUCTION DES LIGNES
# =============================================================

def group_words_into_rows(
    words: list[OCRWord],
    y_tolerance: float = DEFAULT_Y_TOLERANCE,
) -> list[OCRLine]:
    """
    Regroupe les mots ayant une position verticale similaire.
    """

    if not words:
        return []

    sorted_words = sorted(
        words,
        key=lambda word: (
            word.center_y,
            word.x,
        ),
    )

    rows: list[OCRLine] = []

    for word in sorted_words:

        best_row = None

        best_distance = None

        for row in rows:

            distance = abs(
                word.center_y
                - (
                    sum(
                        item.center_y
                        for item in row.words
                    )
                    / len(row.words)
                )
            )

            if distance <= y_tolerance:

                if (
                    best_distance is None
                    or distance < best_distance
                ):

                    best_row = row
                    best_distance = distance

        if best_row is not None:

            best_row.words.append(
                word
            )

            best_row.words.sort(
                key=lambda item: item.x
            )

        else:

            rows.append(
                OCRLine(
                    words=[word]
                )
            )

    rows.sort(
        key=lambda row: row.y
    )

    return rows


# =============================================================
# DISTANCE ENTRE DEUX MOTS
# =============================================================

def horizontal_gap(
    word1: OCRWord,
    word2: OCRWord,
) -> float:
    """
    Distance horizontale entre deux mots.
    """

    if word1.x2 <= word2.x:

        return word2.x - word1.x2

    if word2.x2 <= word1.x:

        return word1.x - word2.x2

    return 0.0


# =============================================================
# DETECTION DES POSITIONS DE COLONNES
# =============================================================

def detect_column_positions(
    rows: list[OCRLine],
    tolerance: float = DEFAULT_COLUMN_TOLERANCE,
) -> list[float]:
    """
    Détecte les positions horizontales récurrentes.

    La position utilisée est le centre X du mot.

    Exemple :

        Produit    Quantité    Prix
        ABC        10          25
        DEF        5           12

    donne approximativement :

        colonne 1 -> x=...
        colonne 2 -> x=...
        colonne 3 -> x=...
    """

    centers = []

    for row in rows:

        for word in row.words:

            centers.append(
                word.center_x
            )

    if not centers:
        return []

    centers.sort()

    clusters: list[list[float]] = []

    for center in centers:

        best_cluster = None

        best_distance = None

        for cluster in clusters:

            cluster_center = (
                sum(cluster)
                / len(cluster)
            )

            distance = abs(
                center
                - cluster_center
            )

            if distance <= tolerance:

                if (
                    best_distance is None
                    or distance < best_distance
                ):

                    best_cluster = cluster
                    best_distance = distance

        if best_cluster is not None:

            best_cluster.append(
                center
            )

        else:

            clusters.append(
                [center]
            )

    # ---------------------------------------------------------
    # Centre de chaque colonne
    # ---------------------------------------------------------

    positions = []

    for cluster in clusters:

        positions.append(
            median(cluster)
        )

    positions.sort()

    return positions


# =============================================================
# REGROUPEMENT DES MOTS PAR COLONNE
# =============================================================

def assign_column(
    word: OCRWord,
    column_positions: list[float],
) -> int:
    """
    Assigne un mot à la colonne la plus proche.
    """

    if not column_positions:
        return -1

    distances = [
        abs(
            word.center_x
            - position
        )
        for position in column_positions
    ]

    return distances.index(
        min(distances)
    )


# =============================================================
# CREATION DES COLONNES
# =============================================================

def build_columns(
    rows: list[OCRLine],
    column_positions: list[float],
) -> list[TableColumn]:
    """
    Construit les objets colonnes.
    """

    columns = []

    for index, position in enumerate(
        column_positions
    ):

        column_words = []

        for row in rows:

            for word in row.words:

                assigned = assign_column(
                    word,
                    column_positions,
                )

                if assigned == index:

                    column_words.append(
                        word.text
                    )

        columns.append(
            TableColumn(
                index=index + 1,
                x_center=position,
                word_count=len(
                    column_words
                ),
                words=column_words,
            )
        )

    return columns


# =============================================================
# CREATION DES LIGNES
# =============================================================

def build_rows(
    rows: list[OCRLine],
) -> list[TableRow]:
    """
    Transforme les lignes OCR en lignes de tableau.
    """

    result = []

    for index, row in enumerate(
        rows,
        start=1,
    ):

        result.append(
            TableRow(
                index=index,
                y_center=(
                    row.y
                    + row.height / 2
                ),
                word_count=len(
                    row.words
                ),
                words=[
                    word.text
                    for word in row.words
                ],
            )
        )

    return result


# =============================================================
# CREATION DES CELLULES
# =============================================================

def build_cells(
    rows: list[OCRLine],
    column_positions: list[float],
) -> list[TableCell]:
    """
    Construit les cellules logiques.

    Plusieurs mots appartenant à la même colonne
    et à la même ligne sont regroupés dans une cellule.
    """

    cells = []

    if not column_positions:
        return cells

    for row_index, row in enumerate(
        rows,
        start=1,
    ):

        grouped: dict[int, list[OCRWord]] = {}

        for word in row.words:

            column_index = assign_column(
                word,
                column_positions,
            )

            grouped.setdefault(
                column_index,
                [],
            ).append(
                word
            )

        for column_index, cell_words in grouped.items():

            if column_index < 0:
                continue

            cell_words.sort(
                key=lambda word: word.x
            )

            min_x = min(
                word.x
                for word in cell_words
            )

            min_y = min(
                word.y
                for word in cell_words
            )

            max_x = max(
                word.x2
                for word in cell_words
            )

            max_y = max(
                word.y2
                for word in cell_words
            )

            confidence_values = [
                word.confidence
                for word in cell_words
                if word.confidence >= 0
            ]

            confidence = (
                sum(
                    confidence_values
                )
                / len(
                    confidence_values
                )
                if confidence_values
                else 0.0
            )

            original_words = [
                {
                    "text": word.text,
                    "x": word.x,
                    "y": word.y,
                    "width": word.width,
                    "height": word.height,
                    "confidence": word.confidence,
                }
                for word in cell_words
            ]

            cells.append(
                TableCell(
                    row=row_index,
                    column=column_index + 1,
                    text=" ".join(
                        word.text
                        for word in cell_words
                    ),
                    words=original_words,
                    x=min_x,
                    y=min_y,
                    width=max_x - min_x,
                    height=max_y - min_y,
                    confidence=confidence,
                )
            )

    return cells


# =============================================================
# DENSITE DU TABLEAU
# =============================================================

def calculate_table_density(
    rows: list[OCRLine],
    column_positions: list[float],
) -> float:
    """
    Calcule la densité du tableau.

    Une structure tabulaire régulière obtient
    généralement une densité élevée.
    """

    if not rows:
        return 0.0

    if not column_positions:
        return 0.0

    expected_cells = (
        len(rows)
        * len(column_positions)
    )

    if expected_cells <= 0:
        return 0.0

    occupied = 0

    for row in rows:

        used_columns = set()

        for word in row.words:

            column = assign_column(
                word,
                column_positions,
            )

            if column >= 0:

                used_columns.add(
                    column
                )

        occupied += len(
            used_columns
        )

    density = (
        occupied
        / expected_cells
    )

    return min(
        1.0,
        max(
            0.0,
            density,
        ),
    )


# =============================================================
# REGULARITE DES COLONNES
# =============================================================

def calculate_column_regularity(
    rows: list[OCRLine],
    column_positions: list[float],
) -> float:
    """
    Mesure la régularité des colonnes.

    Plus les lignes utilisent les mêmes colonnes,
    plus le score est élevé.
    """

    if not rows:
        return 0.0

    if not column_positions:
        return 0.0

    usage = []

    for row in rows:

        used = set()

        for word in row.words:

            column = assign_column(
                word,
                column_positions,
            )

            if column >= 0:

                used.add(
                    column
                )

        usage.append(
            len(used)
        )

    if not usage:
        return 0.0

    maximum = max(
        usage
    )

    if maximum <= 0:
        return 0.0

    average = (
        sum(usage)
        / len(usage)
    )

    return min(
        1.0,
        average
        / maximum,
    )


# =============================================================
# REGULARITE DES LIGNES
# =============================================================

def calculate_row_regularity(
    rows: list[OCRLine],
) -> float:
    """
    Mesure la régularité du nombre de mots
    par ligne.
    """

    if len(rows) < 2:
        return 0.0

    counts = [
        len(row.words)
        for row in rows
    ]

    if not counts:
        return 0.0

    average = (
        sum(counts)
        / len(counts)
    )

    if average <= 0:
        return 0.0

    deviation = sum(
        abs(
            count
            - average
        )
        for count in counts
    ) / len(counts)

    score = 1.0 - (
        deviation
        / average
    )

    return min(
        1.0,
        max(
            0.0,
            score,
        ),
    )


# =============================================================
# SCORE TABLEAU
# =============================================================

def calculate_table_score(
    rows: list[OCRLine],
    columns: list[TableColumn],
    density: float,
    column_regularity: float,
    row_regularity: float,
) -> float:
    """
    Calcule un score global de structure tabulaire.

    Aucun modèle IA.
    """

    row_score = min(
        1.0,
        len(rows) / 5.0,
    )

    column_score = min(
        1.0,
        len(columns) / 4.0,
    )

    score = (
        row_score * 0.20
        + column_score * 0.20
        + density * 0.30
        + column_regularity * 0.20
        + row_regularity * 0.10
    )

    return round(
        min(
            1.0,
            max(
                0.0,
                score,
            ),
        ),
        3,
    )


# =============================================================
# DETECTION ENTETE
# =============================================================

def detect_header(
    rows: list[OCRLine],
) -> tuple[bool, int | None]:
    """
    Essaie de déterminer si la première ligne
    ressemble à un en-tête.

    Cette détection reste heuristique.
    """

    if len(rows) < 2:
        return False, None

    first_row = rows[0]

    second_row = rows[1]

    if not first_row.words:
        return False, None

    if not second_row.words:
        return False, None

    # ---------------------------------------------------------
    # Longueur moyenne des mots
    # ---------------------------------------------------------

    first_average = (
        sum(
            len(word.text)
            for word in first_row.words
        )
        / len(first_row.words)
    )

    second_average = (
        sum(
            len(word.text)
            for word in second_row.words
        )
        / len(second_row.words)
    )

    # ---------------------------------------------------------
    # Première ligne souvent plus courte
    # ---------------------------------------------------------

    if (
        len(first_row.words)
        >= 2
        and first_average <= (
            second_average * 1.5
        )
    ):

        return True, 1

    return False, None


# =============================================================
# DETECTION TABLEAU
# =============================================================

def detect_table(
    words: list[dict],
    y_tolerance: float = DEFAULT_Y_TOLERANCE,
    column_tolerance: float = DEFAULT_COLUMN_TOLERANCE,
    min_rows: int = DEFAULT_MIN_ROWS,
    min_columns: int = DEFAULT_MIN_COLUMNS,
    min_words: int = DEFAULT_MIN_WORDS,
) -> DetectedTable | None:
    """
    Détecte un tableau dans une liste de mots OCR.

    Retourne None si aucune structure tabulaire
    suffisamment forte n'est détectée.
    """

    if not words:
        return None

    converted_words = convert_words(
        words
    )

    if len(converted_words) < min_words:
        return None

    rows = group_words_into_rows(
        converted_words,
        y_tolerance=y_tolerance,
    )

    if len(rows) < min_rows:
        return None

    column_positions = detect_column_positions(
        rows,
        tolerance=column_tolerance,
    )

    if len(column_positions) < min_columns:
        return None

    columns = build_columns(
        rows,
        column_positions,
    )

    table_rows = build_rows(
        rows
    )

    density = calculate_table_density(
        rows,
        column_positions,
    )

    column_regularity = (
        calculate_column_regularity(
            rows,
            column_positions,
        )
    )

    row_regularity = (
        calculate_row_regularity(
            rows
        )
    )

    score = calculate_table_score(
        rows,
        columns,
        density,
        column_regularity,
        row_regularity,
    )

    # ---------------------------------------------------------
    # Rejet des faux tableaux
    # ---------------------------------------------------------

    if density < 0.30:
        return None

    if column_regularity < 0.35:
        return None

    if score < 0.45:
        return None

    cells = build_cells(
        rows,
        column_positions,
    )

    if not cells:
        return None

    min_x = min(
        word.x
        for word in converted_words
    )

    min_y = min(
        word.y
        for word in converted_words
    )

    max_x = max(
        word.x2
        for word in converted_words
    )

    max_y = max(
        word.y2
        for word in converted_words
    )

    average_confidence = (
        sum(
            word.confidence
            for word in converted_words
        )
        / len(converted_words)
    )

    confidence = (
        score
        * 0.60
        + (
            average_confidence
            / 100.0
        )
        * 0.40
    )

    confidence = min(
        1.0,
        max(
            0.0,
            confidence,
        ),
    )

    has_header, header_row = detect_header(
        rows
    )

    return DetectedTable(
        rows=table_rows,
        columns=columns,
        cells=cells,
        x=min_x,
        y=min_y,
        width=max_x - min_x,
        height=max_y - min_y,
        score=score,
        confidence=round(
            confidence,
            3,
        ),
        has_header=has_header,
        header_row=header_row,
    )


# =============================================================
# DETECTION DE PLUSIEURS TABLEAUX
# =============================================================

def detect_tables(
    words: list[dict],
    y_tolerance: float = DEFAULT_Y_TOLERANCE,
    column_tolerance: float = DEFAULT_COLUMN_TOLERANCE,
) -> list[DetectedTable]:
    """
    Détection de tableaux.

    Version volontairement prudente :
    elle cherche d'abord une structure globale.

    Pour les documents complexes contenant plusieurs
    tableaux séparés, une segmentation spatiale pourra
    être ajoutée dans une prochaine étape.
    """

    table = detect_table(
        words,
        y_tolerance=y_tolerance,
        column_tolerance=column_tolerance,
    )

    if table is None:
        return []

    return [table]


# =============================================================
# EXPORT TABLEAU EN DICTIONNAIRE
# =============================================================

def table_to_dict(
    table: DetectedTable,
) -> dict[str, Any]:
    """
    Convertit un tableau en dictionnaire JSON-compatible.
    """

    return {
        "x": table.x,
        "y": table.y,
        "width": table.width,
        "height": table.height,
        "score": table.score,
        "confidence": table.confidence,
        "row_count": table.row_count,
        "column_count": table.column_count,
        "cell_count": table.cell_count,
        "has_header": table.has_header,
        "header_row": table.header_row,

        "rows": [
            {
                "index": row.index,
                "y_center": row.y_center,
                "word_count": row.word_count,
                "words": row.words,
            }
            for row in table.rows
        ],

        "columns": [
            {
                "index": column.index,
                "x_center": column.x_center,
                "word_count": column.word_count,
                "words": column.words,
            }
            for column in table.columns
        ],

        "cells": [
            {
                "row": cell.row,
                "column": cell.column,
                "text": cell.text,
                "x": cell.x,
                "y": cell.y,
                "width": cell.width,
                "height": cell.height,
                "confidence": cell.confidence,
                "words": cell.words,
            }
            for cell in table.cells
        ],
    }


# =============================================================
# AFFICHAGE TABLEAU
# =============================================================

def print_table(
    table: DetectedTable,
) -> None:
    """
    Affiche un tableau détecté.
    """

    print(
        "\n"
        + "=" * 70
    )

    print(
        "TABLEAU DETECTE"
    )

    print(
        "=" * 70
    )

    print(
        f"Position : "
        f"x={table.x:.1f} "
        f"y={table.y:.1f} "
        f"w={table.width:.1f} "
        f"h={table.height:.1f}"
    )

    print(
        f"Lignes : "
        f"{table.row_count}"
    )

    print(
        f"Colonnes : "
        f"{table.column_count}"
    )

    print(
        f"Cellules : "
        f"{table.cell_count}"
    )

    print(
        f"Score : "
        f"{table.score:.3f}"
    )

    print(
        f"Confiance : "
        f"{table.confidence:.3f}"
    )

    print(
        f"En-tête détecté : "
        f"{table.has_header}"
    )

    # =========================================================
    # COLONNES
    # =========================================================

    print(
        "\nColonnes :"
    )

    for column in table.columns:

        print(
            f"  Colonne {column.index}: "
            f"x={column.x_center:.1f} "
            f"mots={column.word_count} "
            f"| "
            f"{' | '.join(column.words)}"
        )

    # =========================================================
    # LIGNES
    # =========================================================

    print(
        "\nLignes :"
    )

    for row in table.rows:

        print(
            f"  Ligne {row.index}: "
            f"y={row.y_center:.1f} "
            f"mots={row.word_count} "
            f"| "
            f"{' | '.join(row.words)}"
        )

    # =========================================================
    # CELLULES
    # =========================================================

    print(
        "\nCellules :"
    )

    for cell in table.cells:

        print(
            f"  [{cell.row},{cell.column}] "
            f"{cell.text:<25} "
            f"x={cell.x:7.1f} "
            f"y={cell.y:7.1f} "
            f"w={cell.width:7.1f} "
            f"h={cell.height:7.1f} "
            f"conf={cell.confidence:.1f}"
        )


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    print("=" * 70)

    print(
        "TEST TABLE DETECTOR OCR - SANS IA"
    )

    print("=" * 70)

    # =========================================================
    # DOCUMENT DE TEST ARTIFICIEL
    # =========================================================

    test_words = [

        # -----------------------------------------------------
        # En-tête
        # -----------------------------------------------------

        {
            "text": "Produit",
            "x": 100,
            "y": 100,
            "width": 80,
            "height": 20,
            "confidence": 95,
        },

        {
            "text": "Quantite",
            "x": 300,
            "y": 100,
            "width": 90,
            "height": 20,
            "confidence": 95,
        },

        {
            "text": "Prix",
            "x": 500,
            "y": 100,
            "width": 50,
            "height": 20,
            "confidence": 96,
        },

        # -----------------------------------------------------
        # Ligne 2
        # -----------------------------------------------------

        {
            "text": "ABC",
            "x": 100,
            "y": 140,
            "width": 50,
            "height": 20,
            "confidence": 94,
        },

        {
            "text": "10",
            "x": 300,
            "y": 140,
            "width": 30,
            "height": 20,
            "confidence": 96,
        },

        {
            "text": "25.50",
            "x": 500,
            "y": 140,
            "width": 60,
            "height": 20,
            "confidence": 95,
        },

        # -----------------------------------------------------
        # Ligne 3
        # -----------------------------------------------------

        {
            "text": "DEF",
            "x": 100,
            "y": 180,
            "width": 50,
            "height": 20,
            "confidence": 94,
        },

        {
            "text": "5",
            "x": 300,
            "y": 180,
            "width": 15,
            "height": 20,
            "confidence": 95,
        },

        {
            "text": "12.00",
            "x": 500,
            "y": 180,
            "width": 60,
            "height": 20,
            "confidence": 95,
        },

        # -----------------------------------------------------
        # Ligne 4
        # -----------------------------------------------------

        {
            "text": "GHI",
            "x": 100,
            "y": 220,
            "width": 50,
            "height": 20,
            "confidence": 93,
        },

        {
            "text": "8",
            "x": 300,
            "y": 220,
            "width": 15,
            "height": 20,
            "confidence": 94,
        },

        {
            "text": "18.75",
            "x": 500,
            "y": 220,
            "width": 60,
            "height": 20,
            "confidence": 94,
        },
    ]

    # =========================================================
    # DETECTION
    # =========================================================

    print(
        "\n[1] Détection du tableau"
    )

    table = detect_table(
        test_words
    )

    if table is None:

        print(
            "\nAucun tableau détecté."
        )

    else:

        print_table(
            table
        )

        # =====================================================
        # EXPORT DICTIONNAIRE
        # =====================================================

        print(
            "\n[2] Résultat dictionnaire"
        )

        result = table_to_dict(
            table
        )

        print(
            f"  row_count      : "
            f"{result['row_count']}"
        )

        print(
            f"  column_count   : "
            f"{result['column_count']}"
        )

        print(
            f"  cell_count     : "
            f"{result['cell_count']}"
        )

        print(
            f"  score          : "
            f"{result['score']}"
        )

        print(
            f"  confidence     : "
            f"{result['confidence']}"
        )

        # =====================================================
        # MATRICE
        # =====================================================

        print(
            "\n[3] Matrice détectée"
        )

        matrix = {}

        for cell in table.cells:

            matrix.setdefault(
                cell.row,
                {}
            )

            matrix[
                cell.row
            ][
                cell.column
            ] = cell.text

        for row_index in sorted(
            matrix
        ):

            values = []

            for column_index in range(
                1,
                table.column_count + 1,
            ):

                values.append(
                    matrix[
                        row_index
                    ].get(
                        column_index,
                        "",
                    )
                )

            print(
                "  "
                + " | ".join(
                    values
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
        "TEST TABLE DETECTOR TERMINE"
    )

    print(
        "=" * 70
    )

