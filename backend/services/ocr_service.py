
from __future__ import annotations

"""
OCR SERVICE
=============================================================

Service backend pour l'analyse OCR.

Responsabilités :

    - validation fichier
    - appel document_parser
    - normalisation résultat
    - conversion des objets Python en JSON
    - sauvegarde JSON
    - structure stable pour API/frontend

Ce service ne connaît aucun champ métier.

IA : désactivée
LLM : désactivé
Base de données : désactivée
"""

import json
import logging

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from engine.document_parser import parse_document


# =============================================================
# LOGGER
# =============================================================

logger = logging.getLogger(__name__)


# =============================================================
# DOSSIERS
# =============================================================

# ocr_service.py :
#
# V1/
# └── backend/
#     └── services/
#         └── ocr_service.py
#
# parents[0] = services
# parents[1] = backend
# parents[2] = V1
#
# On utilise donc parents[2].

BASE_DIR = Path(__file__).resolve().parents[2]

UPLOAD_DIR = BASE_DIR / "uploads"

RESULT_DIR = BASE_DIR / "results"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

RESULT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =============================================================
# EXCEPTION
# =============================================================

class OCRServiceError(Exception):
    """Erreur générale du service OCR."""


# =============================================================
# EXTENSIONS SUPPORTÉES
# =============================================================

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".webp",
}


# =============================================================
# UTILITAIRES DE SÉCURITÉ
# =============================================================

def safe_dict(
    value: Any,
) -> dict:
    """
    Retourne un dictionnaire si value est un dict.
    Sinon retourne {}.
    """

    if isinstance(value, dict):
        return value

    return {}


def safe_list(
    value: Any,
) -> list:
    """
    Retourne une liste propre.

    Accepte :
        - list
        - tuple
        - set
    """

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, set):
        return list(value)

    return []


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Conversion sécurisée vers float.
    """

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    """
    Conversion sécurisée vers int.
    """

    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


# =============================================================
# CONVERSION JSON
# =============================================================

def make_json_serializable(
    value: Any,
) -> Any:
    """
    Convertit récursivement les objets Python en types
    compatibles avec JSON.

    Cette fonction est particulièrement importante pour
    les objets retournés par les détecteurs OCR.

    Exemple :

        DetectedTable(...)
        Point(...)
        BoundingBox(...)
        dataclass(...)
    
    deviennent des dictionnaires/listes JSON.

    Types gérés :

        - None
        - str
        - int
        - float
        - bool
        - Path
        - dict
        - list
        - tuple
        - set
        - dataclass
        - objets avec __dict__

    Le dernier recours consiste à convertir l'objet
    en chaîne de caractères.
    """

    # ---------------------------------------------------------
    # Valeurs nulles
    # ---------------------------------------------------------

    if value is None:
        return None

    # ---------------------------------------------------------
    # Types primitifs JSON
    # ---------------------------------------------------------

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    # ---------------------------------------------------------
    # Path
    # ---------------------------------------------------------

    if isinstance(
        value,
        Path,
    ):
        return str(value)

    # ---------------------------------------------------------
    # Dictionnaire
    # ---------------------------------------------------------

    if isinstance(
        value,
        dict,
    ):

        return {
            str(key):
                make_json_serializable(item)

            for key, item in value.items()
        }

    # ---------------------------------------------------------
    # Liste / tuple / set
    # ---------------------------------------------------------

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):

        return [
            make_json_serializable(item)

            for item in value
        ]

    # ---------------------------------------------------------
    # Dataclass
    #
    # Exemple :
    #
    # @dataclass
    # class DetectedTable:
    #     ...
    #
    # ---------------------------------------------------------

    try:

        if is_dataclass(value):

            return make_json_serializable(
                asdict(value)
            )

    except Exception:

        pass

    # ---------------------------------------------------------
    # Objets possédant __dict__
    #
    # Exemple :
    #
    # DetectedTable
    # Objet OCR
    # BoundingBox
    # etc.
    # ---------------------------------------------------------

    if hasattr(
        value,
        "__dict__",
    ):

        try:

            return {
                str(key):
                    make_json_serializable(item)

                for key, item in vars(value).items()
            }

        except Exception:

            pass

    # ---------------------------------------------------------
    # Dernier recours
    # ---------------------------------------------------------

    return str(value)


# =============================================================
# VALIDATION EXTENSION
# =============================================================

def is_supported_file(
    file_path: str | Path,
) -> bool:
    """
    Vérifie si l'extension du fichier est supportée.
    """

    path = Path(
        file_path
    )

    return (
        path.suffix.lower()
        in ALLOWED_EXTENSIONS
    )


# =============================================================
# VALIDATION FICHIER
# =============================================================

def validate_file(
    file_path: str | Path,
) -> Path:
    """
    Vérifie qu'un fichier existe et possède
    une extension supportée.
    """

    path = Path(
        file_path
    )

    # ---------------------------------------------------------
    # Existe ?
    # ---------------------------------------------------------

    if not path.exists():

        raise OCRServiceError(
            f"Fichier introuvable : {path}"
        )

    # ---------------------------------------------------------
    # Est un fichier ?
    # ---------------------------------------------------------

    if not path.is_file():

        raise OCRServiceError(
            f"Le chemin n'est pas un fichier : {path}"
        )

    # ---------------------------------------------------------
    # Extension ?
    # ---------------------------------------------------------

    if not is_supported_file(path):

        raise OCRServiceError(
            f"Format non supporté : {path.suffix}"
        )

    return path


# =============================================================
# ANALYSE DOCUMENT
# =============================================================

def analyze_document(
    file_path: str | Path,
) -> dict[str, Any]:
    """
    Analyse complète d'un document.

    Le moteur OCR est appelé via document_parser.
    """

    path = validate_file(
        file_path
    )

    logger.info(
        "Analyse OCR : %s",
        path.name,
    )

    try:

        result = parse_document(
            str(path)
        )

    except Exception as exc:

        logger.exception(
            "Erreur pendant l'analyse OCR"
        )

        raise OCRServiceError(
            f"Erreur OCR : "
            f"{type(exc).__name__}: "
            f"{exc}"
        ) from exc

    # ---------------------------------------------------------
    # Vérification résultat
    # ---------------------------------------------------------

    if not isinstance(
        result,
        dict,
    ):

        raise OCRServiceError(
            "Le parser OCR n'a pas retourné "
            "un dictionnaire."
        )

    # ---------------------------------------------------------
    # Normalisation
    # ---------------------------------------------------------

    return normalize_parser_result(
        result=result,
        file_path=path,
    )


# =============================================================
# NORMALISATION RÉSULTAT
# =============================================================

def normalize_parser_result(
    result: dict[str, Any],
    file_path: Path,
) -> dict[str, Any]:
    """
    Transforme la sortie interne du parser OCR
    en structure stable pour l'API et le frontend.

    Compatible avec plusieurs versions du parser.
    """

    result = safe_dict(
        result
    )

    # =========================================================
    # DOCUMENT
    # =========================================================

    document = safe_dict(
        result.get(
            "document",
            {},
        )
    )

    # =========================================================
    # STATISTIQUES SOURCE
    # =========================================================

    statistics = safe_dict(
        result.get(
            "statistics",
            {},
        )
    )

    # =========================================================
    # PAGES
    # =========================================================

    page_count = document.get(
        "page_count",
        document.get(
            "pages",
            statistics.get(
                "page_count",
                0,
            ),
        ),
    )

    page_count = safe_int(
        page_count
    )

    # Si le parser contient réellement des pages,
    # on peut utiliser leur nombre comme secours.

    source_pages = safe_list(
        result.get(
            "pages",
            [],
        )
    )

    if page_count == 0 and source_pages:

        page_count = len(
            source_pages
        )

    # =========================================================
    # TYPE DOCUMENT
    # =========================================================

    document_type = document.get(
        "type"
    )

    if not document_type:

        document_type = (
            file_path.suffix
            .lower()
            .replace(
                ".",
                "",
            )
        )

    # =========================================================
    # TEXTE
    # =========================================================

    text = result.get(
        "text",
        result.get(
            "full_text",
            "",
        ),
    )

    if text is None:

        text = ""

    text = str(
        text
    )

    # =========================================================
    # CHAMPS
    # =========================================================

    fields = result.get(
        "fields",
        {},
    )

    if not isinstance(
        fields,
        dict,
    ):

        fields = {}

    # =========================================================
    # TABLEAUX
    # =========================================================

    tables = safe_list(
        result.get(
            "tables",
            [],
        )
    )

    # =========================================================
    # PAGES
    # =========================================================

    pages = source_pages

    # =========================================================
    # CONFIANCE
    # =========================================================

    confidence = result.get(
        "confidence",
        result.get(
            "global_confidence",
            statistics.get(
                "confidence",
                0.0,
            ),
        ),
    )

    confidence = safe_float(
        confidence
    )

    # ---------------------------------------------------------
    # Conversion 0..1 -> pourcentage
    # ---------------------------------------------------------

    if confidence <= 1.0:

        confidence_percent = (
            confidence * 100.0
        )

    else:

        confidence_percent = confidence

    # =========================================================
    # COMPTEURS
    # =========================================================

    field_count = statistics.get(
        "field_count",
        len(fields),
    )

    table_count = statistics.get(
        "table_count",
        len(tables),
    )

    processed_page_count = statistics.get(
        "processed_page_count",
        len(pages),
    )

    # =========================================================
    # STATISTIQUES FINALES
    # =========================================================

    normalized_statistics = {

        # Conserver les statistiques originales
        **statistics,

        "page_count":
            page_count,

        "processed_page_count":
            safe_int(
                processed_page_count,
                len(pages),
            ),

        "word_count":
            safe_int(
                statistics.get(
                    "word_count",
                    0,
                )
            ),

        "line_count":
            safe_int(
                statistics.get(
                    "line_count",
                    0,
                )
            ),

        "field_count":
            safe_int(
                field_count,
                len(fields),
            ),

        "table_count":
            safe_int(
                table_count,
                len(tables),
            ),

        "character_count":
            safe_int(
                statistics.get(
                    "character_count",
                    len(text),
                )
            ),

        "confidence":
            confidence,

        "confidence_percent":
            confidence_percent,
    }

    # =========================================================
    # RÉSULTAT STABLE
    # =========================================================

    normalized = {

        "success":
            True,

        # -----------------------------------------------------
        # DOCUMENT
        # -----------------------------------------------------

        "document": {

            "filename":
                file_path.name,

            "name":
                file_path.name,

            "path":
                str(file_path),

            "type":
                document_type,

            "page_count":
                page_count,

            # Alias frontend
            "pages":
                page_count,
        },

        # -----------------------------------------------------
        # TEXTE
        # -----------------------------------------------------

        "text":
            text,

        "full_text":
            text,

        # -----------------------------------------------------
        # PAGES
        # -----------------------------------------------------

        "pages":
            pages,

        # -----------------------------------------------------
        # CHAMPS
        # -----------------------------------------------------

        "fields":
            fields,

        # -----------------------------------------------------
        # TABLEAUX
        # -----------------------------------------------------

        "tables":
            tables,

        # -----------------------------------------------------
        # STATISTIQUES
        # -----------------------------------------------------

        "statistics":
            normalized_statistics,

        # -----------------------------------------------------
        # CONFIANCE
        # -----------------------------------------------------

        "confidence":
            confidence,

        "confidence_percent":
            confidence_percent,

        # -----------------------------------------------------
        # MOTEUR
        # -----------------------------------------------------

        "engine": {

            "name":
                "OCR Engine",

            "ai_enabled":
                False,

            "llm_enabled":
                False,

            "mode":
                "ocr_only",
        },
    }

    # =========================================================
    # SUMMARY FRONTEND
    # =========================================================

    normalized["summary"] = {

        "pages":
            page_count,

        "fields":
            safe_int(
                field_count,
                len(fields),
            ),

        "tables":
            safe_int(
                table_count,
                len(tables),
            ),

        "confidence":
            confidence_percent,
    }

    # =========================================================
    # CONVERSION JSON
    # =========================================================
    #
    # Important :
    #
    # Le parser peut retourner des objets Python
    # tels que DetectedTable.
    #
    # On les convertit ici AVANT le retour.
    #
    # Cela garantit que l'API reçoit uniquement
    # des données JSON compatibles.
    # =========================================================

    normalized = make_json_serializable(
        normalized
    )

    return normalized


# =============================================================
# SAUVEGARDE JSON
# =============================================================

def save_result(
    result: dict[str, Any],
    file_path: str | Path,
) -> Path:
    """
    Sauvegarde le résultat OCR au format JSON.

    Les objets Python non sérialisables sont convertis
    automatiquement avant json.dump().
    """

    source = Path(
        file_path
    )

    output_path = (
        RESULT_DIR
        / f"{source.stem}.json"
    )

    try:

        # -----------------------------------------------------
        # Conversion complète
        # -----------------------------------------------------

        serializable_result = (
            make_json_serializable(
                result
            )
        )

        # -----------------------------------------------------
        # Écriture JSON
        # -----------------------------------------------------

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                serializable_result,
                file,
                ensure_ascii=False,
                indent=2,
            )

    except OSError as exc:

        raise OCRServiceError(
            f"Impossible de sauvegarder "
            f"le résultat : {exc}"
        ) from exc

    except (
        TypeError,
        ValueError,
    ) as exc:

        logger.exception(
            "Erreur de sérialisation JSON"
        )

        raise OCRServiceError(
            f"Impossible de convertir "
            f"le résultat OCR en JSON : {exc}"
        ) from exc

    logger.info(
        "Résultat OCR sauvegardé : %s",
        output_path,
    )

    return output_path


# =============================================================
# PROCESS DOCUMENT
# =============================================================

def process_document(
    file_path: str | Path,
    save_json: bool = True,
) -> dict[str, Any]:
    """
    Fonction principale utilisée par le backend.

    Exemple :

        result = process_document(
            "uploads/test_2.png"
        )
    """

    path = validate_file(
        file_path
    )

    # ---------------------------------------------------------
    # Analyse OCR
    # ---------------------------------------------------------

    result = analyze_document(
        path
    )

    # ---------------------------------------------------------
    # Sauvegarde JSON
    # ---------------------------------------------------------

    if save_json:

        output_path = save_result(
            result,
            path,
        )

        result["result_file"] = str(
            output_path
        )

    return result


# =============================================================
# TEST SERVICE
# =============================================================

def run_test() -> None:
    """
    Test simple du service.

    Ce test ne lance pas d'OCR.
    Il vérifie uniquement la configuration du service.
    """

    print("=" * 70)

    print(
        "TEST OCR SERVICE"
    )

    print("=" * 70)

    print()

    print(
        f"Base directory : {BASE_DIR}"
    )

    print(
        f"Uploads : {UPLOAD_DIR}"
    )

    print(
        f"Results : {RESULT_DIR}"
    )

    print()

    print(
        "Formats supportés :"
    )

    for extension in sorted(
        ALLOWED_EXTENSIONS
    ):

        print(
            f"  {extension}"
        )

    print()

    print(
        "IA : désactivée"
    )

    print(
        "LLM : désactivé"
    )

    print(
        "Base de données : désactivée"
    )

    print(
        "JSON : activé"
    )

    print()

    print(
        "=" * 70
    )

    print(
        "TEST TERMINE"
    )

    print(
        "=" * 70
    )


# =============================================================
# POINT D'ENTRÉE
# =============================================================

if __name__ == "__main__":

    run_test()

