
from __future__ import annotations

"""
DOCUMENT PARSER
=============================================================

Parser générique pour plateforme OCR multi-documents.

OBJECTIFS
---------
- PDF
- PNG
- JPG / JPEG
- TIFF
- BMP
- WEBP si supporté par le loader
- aucun champ métier codé en dur
- OCR avec coordonnées
- regroupement en lignes
- correction OCR
- normalisation
- classification
- détection de structure
- extraction générique des champs
- détection générique des tableaux
- calcul de confiance
- résultat JSON stable

IMPORTANT
---------
Ce module ne connaît PAS :
    Réf. SAP
    Réf. BE
    Client
    Atelier
    N° OP
    etc.

Ces informations doivent être découvertes dynamiquement
par les modules OCR/layout/field_extractor/table_detector.
"""

from pathlib import Path
from typing import Any


# =============================================================
# IMPORTS ENGINE
# =============================================================

from engine.document_loader import load_document
from engine.preprocessing import generate_variants
from engine.ocr import ocr_with_coordinates

from engine.layout import (
    group_words_into_lines,
    lines_to_text,
)

from engine.selector import select_best_variant
from engine.document_classifier import classify_document
from engine.structure_detector import detect_structure
from engine.confidence import evaluate_confidence
from engine.ocr_correction import correct_ocr_result
from engine.text_normalizer import normalize_ocr_result
from engine.table_detector import detect_tables
from engine.field_extractor import extract_fields


# =============================================================
# CONFIGURATION
# =============================================================

DEFAULT_LANGUAGE = "fra"
DEFAULT_PSM = 11
DEFAULT_PDF_DPI = 200
DEFAULT_SCALE = 2.0
DEFAULT_Y_TOLERANCE = 12


# =============================================================
# UTILITAIRES
# =============================================================

def safe_dict(value: Any) -> dict:
    """Retourne un dictionnaire sûr."""

    if isinstance(value, dict):
        return value

    return {}


def safe_list(value: Any) -> list:
    """Retourne une liste sûre."""

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    return []


def safe_float(value: Any, default: float = 0.0) -> float:
    """Conversion robuste vers float."""

    try:
        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Conversion robuste vers int."""

    try:
        if value is None:
            return default

        return int(value)

    except (TypeError, ValueError):
        return default


# =============================================================
# NORMALISATION RESULTAT OCR
# =============================================================

def normalize_ocr_output(
    ocr_result: Any,
) -> dict:
    """
    Normalise la sortie du moteur OCR.

    Accepte plusieurs formats possibles.
    """

    if not isinstance(ocr_result, dict):
        return {
            "words": [],
            "confidence": 0.0,
        }

    words = safe_list(
        ocr_result.get("words", [])
    )

    confidence = safe_float(
        ocr_result.get(
            "confidence",
            ocr_result.get("conf", 0.0),
        )
    )

    return {
        **ocr_result,
        "words": words,
        "confidence": confidence,
    }


# =============================================================
# NORMALISATION DES LIGNES
# =============================================================

def build_lines(
    words: list,
    y_tolerance: int,
) -> list:
    """
    Construit les lignes à partir des mots OCR.
    """

    if not words:
        return []

    try:
        lines = group_words_into_lines(
            words,
            y_tolerance=y_tolerance,
        )

        return safe_list(lines)

    except TypeError:

        try:
            lines = group_words_into_lines(words)

            return safe_list(lines)

        except Exception:
            return []

    except Exception:
        return []


# =============================================================
# CONSTRUCTION TEXTE
# =============================================================

def build_text(
    lines: list,
) -> str:
    """
    Transforme les lignes OCR en texte.
    """

    if not lines:
        return ""

    try:
        text = lines_to_text(lines)

        if text is None:
            return ""

        return str(text).strip()

    except Exception:
        return ""


# =============================================================
# OCR D'UNE VARIANTE
# =============================================================

def process_variant(
    variant_image: Any,
    language: str,
    psm: int,
    y_tolerance: int,
) -> dict:
    """
    Effectue OCR + layout sur une variante.
    """

    try:

        raw_result = ocr_with_coordinates(
            variant_image,
            language=language,
            psm=psm,
        )

    except TypeError:

        try:

            raw_result = ocr_with_coordinates(
                variant_image,
                language,
                psm,
            )

        except Exception as exc:

            return {
                "words": [],
                "lines": [],
                "text": "",
                "confidence": 0.0,
                "error": str(exc),
            }

    except Exception as exc:

        return {
            "words": [],
            "lines": [],
            "text": "",
            "confidence": 0.0,
            "error": str(exc),
        }

    result = normalize_ocr_output(
        raw_result
    )

    words = result["words"]

    lines = build_lines(
        words,
        y_tolerance,
    )

    text = build_text(lines)

    return {
        **result,
        "words": words,
        "lines": lines,
        "text": text,
        "confidence": safe_float(
            result.get("confidence", 0.0)
        ),
    }


# =============================================================
# SELECTION VARIANTE
# =============================================================

def choose_best_variant(
    variant_results: dict,
) -> tuple[str, dict]:
    """
    Sélection robuste de la meilleure variante OCR.
    """

    if not variant_results:
        return "", {}

    try:

        selected = select_best_variant(
            variant_results,
            [],
        )

    except TypeError:

        try:

            selected = select_best_variant(
                variant_results
            )

        except Exception:

            selected = {}

    except Exception:

        selected = {}

    selected = safe_dict(selected)

    selected_name = selected.get(
        "selected_variant"
    )

    if (
        selected_name
        and selected_name in variant_results
    ):

        return (
            selected_name,
            variant_results[selected_name],
        )

    # ---------------------------------------------------------
    # Fallback : meilleure confiance OCR
    # ---------------------------------------------------------

    selected_name = max(
        variant_results,
        key=lambda name: safe_float(
            variant_results[name].get(
                "confidence",
                0.0,
            )
        ),
    )

    return (
        selected_name,
        variant_results[selected_name],
    )


# =============================================================
# CORRECTION OCR
# =============================================================

def apply_ocr_correction(
    result: dict,
) -> dict:
    """
    Applique la correction OCR sans casser le résultat
    en cas d'incompatibilité de signature.
    """

    corrected = dict(result)

    try:

        output = correct_ocr_result(
            corrected
        )

        if isinstance(output, dict):
            return output

    except TypeError:

        pass

    except Exception:

        return corrected

    # ---------------------------------------------------------
    # Compatibilité avec correction(words)
    # ---------------------------------------------------------

    try:

        output = correct_ocr_result(
            corrected.get(
                "words",
                [],
            )
        )

        if isinstance(output, dict):

            corrected.update(output)

        elif isinstance(output, list):

            corrected["words"] = output

    except Exception:

        pass

    return corrected


# =============================================================
# NORMALISATION OCR
# =============================================================

def apply_normalization(
    result: dict,
) -> dict:
    """
    Normalise le résultat OCR.
    """

    normalized = dict(result)

    try:

        output = normalize_ocr_result(
            normalized
        )

        if isinstance(output, dict):
            return output

        if isinstance(output, str):

            normalized["text"] = output

            return normalized

    except TypeError:

        pass

    except Exception:

        return normalized

    # ---------------------------------------------------------
    # Compatibilité avec normalize(text)
    # ---------------------------------------------------------

    try:

        output = normalize_ocr_result(
            normalized.get(
                "text",
                "",
            )
        )

        if isinstance(output, str):

            normalized["text"] = output

    except Exception:

        pass

    return normalized


# =============================================================
# CLASSIFICATION
# =============================================================

def classify_page(
    text: str,
    words: list,
    lines: list,
) -> dict:
    """
    Classification générique.
    """

    try:

        result = classify_document(
            text,
            words,
            lines,
        )

        return safe_dict(result)

    except TypeError:

        try:

            result = classify_document(
                lines
            )

            return safe_dict(result)

        except Exception:

            return {}

    except Exception:

        return {}


# =============================================================
# STRUCTURE
# =============================================================

def detect_page_structure(
    words: list,
    lines: list,
) -> dict:
    """
    Détection générique de structure.
    """

    try:

        result = detect_structure(
            words,
            lines,
        )

        return safe_dict(result)

    except TypeError:

        try:

            result = detect_structure(
                lines
            )

            return safe_dict(result)

        except Exception:

            return {}

    except Exception:

        return {}


# =============================================================
# CHAMPS
# =============================================================

def extract_page_fields(
    words: list,
    lines: list,
) -> dict:
    """
    Extraction générique des champs.
    """

    try:

        result = extract_fields(
            words=words,
            lines=lines,
        )

    except TypeError:

        try:

            result = extract_fields(
                words,
                lines,
            )

        except TypeError:

            try:

                result = extract_fields(
                    lines
                )

            except Exception:

                return {}

        except Exception:

            return {}

    except Exception:

        return {}

    return safe_dict(result)


# =============================================================
# TABLEAUX
# =============================================================

def extract_page_tables(
    words: list,
    lines: list,
) -> list:
    """
    Extraction générique des tableaux.
    """

    try:

        result = detect_tables(
            words,
            lines,
        )

    except TypeError:

        try:

            result = detect_tables(
                words
            )

        except TypeError:

            try:

                result = detect_tables(
                    lines
                )

            except Exception:

                return []

        except Exception:

            return []

    except Exception:

        return []

    if isinstance(result, list):
        return result

    if isinstance(result, dict):

        tables = result.get(
            "tables"
        )

        if isinstance(tables, list):
            return tables

        # Certains détecteurs retournent
        # directement un tableau sous forme dict.

        if result:
            return [result]

    return []


# =============================================================
# CONFIANCE
# =============================================================

def calculate_page_confidence(
    normalized_result: dict,
    variant_results: dict,
    selected_confidence: float,
) -> dict:
    """
    Calcul robuste de confiance.
    """

    try:

        result = evaluate_confidence(
            normalized_result,
            variant_results,
        )

        result = safe_dict(result)

        if result:
            return result

    except TypeError:

        pass

    except Exception:

        pass

    # ---------------------------------------------------------
    # Fallback
    # ---------------------------------------------------------

    return {
        "global_confidence": selected_confidence,
        "ocr_confidence": selected_confidence,
    }


# =============================================================
# PARSING PAGE
# =============================================================

def parse_page(
    image: Any,
    page_number: int,
    language: str = DEFAULT_LANGUAGE,
    psm: int = DEFAULT_PSM,
    scale: float = DEFAULT_SCALE,
    y_tolerance: int = DEFAULT_Y_TOLERANCE,
) -> dict:
    """
    Analyse complète d'une page.
    """

    print()
    print("=" * 70)
    print(f"ANALYSE PAGE {page_number}")
    print("=" * 70)

    # =========================================================
    # 1. PREPROCESSING
    # =========================================================

    print()
    print("[1] Génération des variantes")

    try:

        variants = generate_variants(
            image,
            scale=scale,
        )

    except TypeError:

        variants = generate_variants(
            image
        )

    except Exception as exc:

        print(
            f"Erreur preprocessing : {exc}"
        )

        variants = {
            "original": image
        }

    if not isinstance(variants, dict):
        variants = {
            "original": image
        }

    print(
        f"Variantes générées : {len(variants)}"
    )

    # =========================================================
    # 2. OCR
    # =========================================================

    print()
    print("[2] OCR des variantes")

    variant_results = {}

    for variant_name, variant_image in variants.items():

        print(
            f"  OCR : {variant_name}"
        )

        variant_results[variant_name] = (
            process_variant(
                variant_image,
                language,
                psm,
                y_tolerance,
            )
        )

    # =========================================================
    # 3. SELECTION
    # =========================================================

    print()
    print("[3] Sélection de la meilleure variante")

    selected_variant, selected_result = (
        choose_best_variant(
            variant_results
        )
    )

    selected_result = safe_dict(
        selected_result
    )

    print(
        f"Variante sélectionnée : "
        f"{selected_variant}"
    )

    selected_confidence = safe_float(
        selected_result.get(
            "confidence",
            0.0,
        )
    )

    # =========================================================
    # 4. CORRECTION OCR
    # =========================================================

    print()
    print("[4] Correction OCR")

    corrected_result = apply_ocr_correction(
        selected_result
    )

    # =========================================================
    # 5. NORMALISATION
    # =========================================================

    print()
    print("[5] Normalisation")

    normalized_result = apply_normalization(
        corrected_result
    )

    # =========================================================
    # DONNEES OCR FINALES
    # =========================================================

    final_words = safe_list(
        normalized_result.get(
            "words",
            corrected_result.get(
                "words",
                selected_result.get(
                    "words",
                    [],
                ),
            ),
        )
    )

    final_lines = safe_list(
        normalized_result.get(
            "lines",
            corrected_result.get(
                "lines",
                selected_result.get(
                    "lines",
                    [],
                ),
            ),
        )
    )

    final_text = str(
        normalized_result.get(
            "text",
            corrected_result.get(
                "text",
                selected_result.get(
                    "text",
                    "",
                ),
            ),
        )
        or ""
    ).strip()

    # ---------------------------------------------------------
    # Reconstruction si nécessaire
    # ---------------------------------------------------------

    if not final_lines and final_words:

        final_lines = build_lines(
            final_words,
            y_tolerance,
        )

    if not final_text and final_lines:

        final_text = build_text(
            final_lines
        )

    # =========================================================
    # 6. CLASSIFICATION
    # =========================================================

    print()
    print("[6] Classification")

    classification = classify_page(
        final_text,
        final_words,
        final_lines,
    )

    document_type = classification.get(
        "type",
        classification.get(
            "document_type",
            "unknown",
        ),
    )

    classification_confidence = safe_float(
        classification.get(
            "confidence",
            0.0,
        )
    )

    # =========================================================
    # 7. STRUCTURE
    # =========================================================

    print()
    print("[7] Structure")

    structure = detect_page_structure(
        final_words,
        final_lines,
    )

    # =========================================================
    # 8. CHAMPS
    # =========================================================

    print()
    print("[8] Extraction champs")

    fields_result = extract_page_fields(
        final_words,
        final_lines,
    )

    fields = fields_result.get(
        "fields",
        fields_result,
    )

    if not isinstance(fields, dict):
        fields = {}

    field_list = fields_result.get(
        "field_list",
        [],
    )

    if not isinstance(field_list, list):
        field_list = []

    print(
        f"Champs détectés : {len(fields)}"
    )

    # =========================================================
    # 9. TABLEAUX
    # =========================================================

    print()
    print("[9] Détection tableaux")

    tables = extract_page_tables(
        final_words,
        final_lines,
    )

    print(
        f"Tableaux détectés : {len(tables)}"
    )

    # =========================================================
    # 10. CONFIANCE
    # =========================================================

    print()
    print("[10] Confiance")

    confidence_result = calculate_page_confidence(
        normalized_result,
        variant_results,
        selected_confidence,
    )

    global_confidence = safe_float(
        confidence_result.get(
            "global_confidence",
            confidence_result.get(
                "confidence",
                selected_confidence,
            ),
        )
    )

    # =========================================================
    # RESULTAT PAGE
    # =========================================================

    return {
        "page_number": page_number,

        "image": {
            "width": safe_int(
                getattr(
                    image,
                    "width",
                    0,
                )
            ),

            "height": safe_int(
                getattr(
                    image,
                    "height",
                    0,
                )
            ),

            "mode": str(
                getattr(
                    image,
                    "mode",
                    "",
                )
                or ""
            ),
        },

        "selected_variant": selected_variant,

        "ocr": {
            "text": final_text,
            "words": final_words,
            "lines": final_lines,
            "confidence": selected_confidence,
        },

        "classification": {
            "type": document_type,
            "confidence": classification_confidence,
            "details": classification,
        },

        "structure": structure,

        "fields": fields,

        "field_list": field_list,

        "tables": tables,

        "confidence": {
            **confidence_result,
            "global_confidence": global_confidence,
        },

        "variants": variant_results,
    }


# =============================================================
# PARSING DOCUMENT COMPLET
# =============================================================

def parse_document(
    path: str | Path,
    language: str = DEFAULT_LANGUAGE,
    psm: int = DEFAULT_PSM,
    pdf_dpi: int = DEFAULT_PDF_DPI,
    scale: float = DEFAULT_SCALE,
) -> dict:
    """
    Analyse un document complet.

    Support :
        PDF
        PNG
        JPG
        JPEG
        TIFF
        BMP
        WEBP

    Le parser reste générique.
    """

    document_path = Path(path)

    if not document_path.exists():

        raise FileNotFoundError(
            f"Document introuvable : "
            f"{document_path}"
        )

    print("=" * 70)
    print("DOCUMENT PARSER OCR")
    print("=" * 70)

    print(
        f"Document : {document_path}"
    )

    # =========================================================
    # CHARGEMENT
    # =========================================================

    print()
    print("[1] Chargement document")

    document = load_document(
        document_path,
        pdf_dpi=pdf_dpi,
    )

    document_type = str(
        getattr(
            document,
            "document_type",
            document_path.suffix
            .lower()
            .replace(".", ""),
        )
        or "unknown"
    )

    page_count = safe_int(
        getattr(
            document,
            "page_count",
            0,
        )
    )

    pages = getattr(
        document,
        "pages",
        [],
    )

    pages = safe_list(pages)

    # =========================================================
    # TRAITEMENT PAGES
    # =========================================================

    page_results = []

    for index, page in enumerate(
        pages,
        start=1,
    ):

        page_number = safe_int(
            getattr(
                page,
                "page_number",
                index,
            ),
            index,
        )

        page_image = getattr(
            page,
            "image",
            None,
        )

        if page_image is None:

            print(
                f"Page {page_number} : "
                f"image absente"
            )

            continue

        try:

            result = parse_page(
                page_image,
                page_number,
                language=language,
                psm=psm,
                scale=scale,
            )

            page_results.append(
                result
            )

        except Exception as exc:

            print(
                f"Erreur page "
                f"{page_number} : {exc}"
            )

            # Une page en erreur ne doit pas
            # faire perdre tout le document.

            page_results.append(
                {
                    "page_number": page_number,
                    "image": {},
                    "selected_variant": "",
                    "ocr": {
                        "text": "",
                        "words": [],
                        "lines": [],
                        "confidence": 0.0,
                    },
                    "classification": {
                        "type": "unknown",
                        "confidence": 0.0,
                        "details": {},
                    },
                    "structure": {},
                    "fields": {},
                    "field_list": [],
                    "tables": [],
                    "confidence": {
                        "global_confidence": 0.0,
                    },
                    "variants": {},
                    "error": str(exc),
                }
            )

    # =========================================================
    # TEXTE COMPLET
    # =========================================================

    full_text_parts = []

    for result in page_results:

        ocr = safe_dict(
            result.get("ocr")
        )

        text = str(
            ocr.get(
                "text",
                "",
            )
            or ""
        ).strip()

        if text:
            full_text_parts.append(
                text
            )

    full_text = "\n\n".join(
        full_text_parts
    )

    # =========================================================
    # STATISTIQUES
    # =========================================================

    total_words = 0
    total_lines = 0
    total_fields = 0
    total_tables = 0

    for result in page_results:

        ocr = safe_dict(
            result.get("ocr")
        )

        total_words += len(
            safe_list(
                ocr.get(
                    "words",
                    [],
                )
            )
        )

        total_lines += len(
            safe_list(
                ocr.get(
                    "lines",
                    [],
                )
            )
        )

        fields = result.get(
            "fields",
            {},
        )

        if isinstance(fields, dict):
            total_fields += len(fields)

        total_tables += len(
            safe_list(
                result.get(
                    "tables",
                    [],
                )
            )
        )

    # =========================================================
    # CONFIANCE DOCUMENT
    # =========================================================

    page_confidences = []

    for result in page_results:

        confidence = safe_dict(
            result.get(
                "confidence"
            )
        )

        value = safe_float(
            confidence.get(
                "global_confidence",
                result.get(
                    "ocr",
                    {},
                ).get(
                    "confidence",
                    0.0,
                )
                if isinstance(
                    result.get("ocr"),
                    dict,
                )
                else 0.0,
            )
        )

        page_confidences.append(
            value
        )

    if page_confidences:

        global_confidence = (
            sum(page_confidences)
            / len(page_confidences)
        )

    else:

        global_confidence = 0.0

    # =========================================================
    # RESULTAT FINAL
    # =========================================================

    result = {

        "success": True,

        "document": {

            "path":
                str(document_path),

            "name":
                document_path.name,

            "filename":
                document_path.name,

            "type":
                document_type,

            "page_count":
                page_count,

            # Alias utilisé par certaines API/frontends.
            "pages":
                page_count,
        },

        "text":
            full_text,

        "full_text":
            full_text,

        "pages":
            page_results,

        "fields":
            {},

        "tables":
            [],

        "confidence":
            global_confidence,

        "statistics": {

            "page_count":
                page_count,

            "processed_page_count":
                len(page_results),

            "word_count":
                total_words,

            "line_count":
                total_lines,

            "field_count":
                total_fields,

            "table_count":
                total_tables,

            "character_count":
                len(full_text),

            "confidence":
                global_confidence,
        },
    }

    # =========================================================
    # FUSION CHAMPS DOCUMENT
    # =========================================================

    document_fields = {}

    for page_result in page_results:

        fields = page_result.get(
            "fields",
            {},
        )

        if not isinstance(fields, dict):
            continue

        for label, value in fields.items():

            if label not in document_fields:

                document_fields[label] = value

            else:

                current = document_fields[label]

                if current == value:
                    continue

                if not isinstance(
                    current,
                    list,
                ):

                    current = [
                        current
                    ]

                if value not in current:

                    current.append(
                        value
                    )

                document_fields[label] = (
                    current
                )

    result["fields"] = document_fields

    # =========================================================
    # FUSION TABLEAUX
    # =========================================================

    document_tables = []

    for page_result in page_results:

        document_tables.extend(
            safe_list(
                page_result.get(
                    "tables",
                    [],
                )
            )
        )

    result["tables"] = document_tables

    # =========================================================
    # AFFICHAGE
    # =========================================================

    print()
    print("=" * 70)
    print("RESULTAT FINAL")
    print("=" * 70)

    print(
        f"Document : {document_path.name}"
    )

    print(
        f"Type : {document_type}"
    )

    print(
        f"Pages : {page_count}"
    )

    print(
        f"Mots : {total_words}"
    )

    print(
        f"Lignes : {total_lines}"
    )

    print(
        f"Champs : {total_fields}"
    )

    print(
        f"Tableaux : {total_tables}"
    )

    print(
        f"Confiance : "
        f"{global_confidence:.3f}"
    )

    print()
    print("-" * 70)
    print("TEXTE OCR")
    print("-" * 70)

    print(
        full_text
        if full_text
        else "[Aucun texte détecté]"
    )

    print()
    print("=" * 70)
    print("PARSING TERMINE")
    print("=" * 70)

    return result


# =============================================================
# TEST DIRECT
# =============================================================

if __name__ == "__main__":

    TEST_DOCUMENT = Path(
        "test.pdf"
    )

    if not TEST_DOCUMENT.exists():

        print(
            f"Document introuvable : "
            f"{TEST_DOCUMENT}"
        )

        print(
            "Place un fichier PDF ou image "
            "dans le dossier du projet."
        )

    else:

        parse_document(
            TEST_DOCUMENT
        )

