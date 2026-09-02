
from __future__ import annotations

import logging
from pathlib import Path

from flask import Blueprint, jsonify, request

from backend.services.ocr_service import (
    OCRServiceError,
    process_document,
)


# =============================================================
# LOGGING
# =============================================================

logger = logging.getLogger(__name__)


# =============================================================
# BLUEPRINT
# =============================================================

extraction_bp = Blueprint(
    "extraction",
    __name__,
    url_prefix="/api/extraction",
)


# =============================================================
# CONFIGURATION
# =============================================================

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
# UTILITAIRES
# =============================================================

def find_uploaded_file(filename: str) -> Path | None:
    """
    Recherche un fichier dans le dossier uploads.

    Accepte :
        - le nom réel du fichier
        - le nom original si un préfixe UUID existe
    """

    if not filename:
        return None

    filename = Path(filename).name

    # ---------------------------------------------------------
    # Recherche directe
    # ---------------------------------------------------------

    direct_path = UPLOAD_DIR / filename

    if direct_path.exists() and direct_path.is_file():
        return direct_path

    # ---------------------------------------------------------
    # Recherche avec préfixe UUID
    #
    # Exemple :
    #
    # test.pdf
    #
    # devient :
    #
    # a81f92cd_test.pdf
    # ---------------------------------------------------------

    matches = list(
        UPLOAD_DIR.glob(
            f"*_{filename}"
        )
    )

    if matches:
        return matches[0]

    return None


def safe_result_filename(filename: str) -> str:
    """
    Nettoie le nom utilisé pour rechercher le JSON.
    """

    return Path(filename).stem


# =============================================================
# HEALTH CHECK
# =============================================================

@extraction_bp.get("/health")
def extraction_health():
    """
    Vérifie que le service extraction fonctionne.
    """

    return jsonify(
        {
            "success": True,
            "service": "extraction",
            "status": "ok",
            "ai_enabled": False,
            "llm_enabled": False,
        }
    )


# =============================================================
# EXTRACTION D'UN DOCUMENT
# =============================================================

@extraction_bp.post("/")
def extract_document():
    """
    Lance le pipeline OCR sur un document déjà présent
    dans le dossier uploads.

    JSON attendu :

        {
            "filename": "test.pdf"
        }

    ou Form-data :

        filename=test.pdf
    """

    filename = None

    # ---------------------------------------------------------
    # Cas JSON
    # ---------------------------------------------------------

    if request.is_json:

        data = request.get_json(
            silent=True
        )

        if isinstance(data, dict):

            filename = data.get(
                "filename"
            )

    # ---------------------------------------------------------
    # Cas form-data
    # ---------------------------------------------------------

    if not filename:

        filename = request.form.get(
            "filename"
        )

    # ---------------------------------------------------------
    # Vérification
    # ---------------------------------------------------------

    if not filename:

        return jsonify(
            {
                "success": False,
                "error": (
                    "Le nom du fichier est obligatoire."
                ),
                "code": "FILENAME_MISSING",
            }
        ), 400

    # ---------------------------------------------------------
    # Recherche fichier
    # ---------------------------------------------------------

    file_path = find_uploaded_file(
        filename
    )

    if file_path is None:

        return jsonify(
            {
                "success": False,
                "error": (
                    f"Fichier introuvable dans uploads : "
                    f"{filename}"
                ),
                "code": "FILE_NOT_FOUND",
            }
        ), 404

    logger.info(
        "Début extraction OCR : %s",
        file_path.name,
    )

    # ---------------------------------------------------------
    # OCR
    # ---------------------------------------------------------

    try:

        result = process_document(
            file_path,
            save_json=True,
        )

    except OCRServiceError as exc:

        logger.exception(
            "Erreur OCR pendant extraction"
        )

        return jsonify(
            {
                "success": False,
                "error": str(exc),
                "code": "OCR_ERROR",
                "filename": file_path.name,
            }
        ), 500

    except Exception as exc:

        logger.exception(
            "Erreur inattendue extraction"
        )

        return jsonify(
            {
                "success": False,
                "error": (
                    "Erreur inattendue "
                    "pendant l'extraction."
                ),
                "code": "INTERNAL_ERROR",
                "details": str(exc),
            }
        ), 500

    # ---------------------------------------------------------
    # Réponse
    # ---------------------------------------------------------

    return jsonify(
        {
            "success": True,
            "message": (
                "Extraction OCR terminée "
                "avec succès."
            ),
            "filename": file_path.name,
            "result": result,
            "engine": {
                "name": "OCR Engine",
                "ai_enabled": False,
                "llm_enabled": False,
            },
        }
    ), 200


# =============================================================
# EXTRACTION RAPIDE
# =============================================================

@extraction_bp.post("/run")
def run_extraction():
    """
    Alias de /api/extraction/.

    JSON :

        {
            "filename": "test.pdf"
        }
    """

    return extract_document()


# =============================================================
# RÉCUPÉRATION DU RESULTAT JSON
# =============================================================

@extraction_bp.get("/result/<filename>")
def get_extraction_result(filename: str):
    """
    Retourne le résultat JSON déjà sauvegardé.

    Exemple :

        GET /api/extraction/result/test.pdf
    """

    stem = safe_result_filename(
        filename
    )

    result_path = RESULT_DIR / f"{stem}.json"

    # ---------------------------------------------------------
    # Vérification
    # ---------------------------------------------------------

    if not result_path.exists():

        return jsonify(
            {
                "success": False,
                "error": (
                    f"Résultat introuvable : "
                    f"{result_path.name}"
                ),
                "code": "RESULT_NOT_FOUND",
            }
        ), 404

    # ---------------------------------------------------------
    # Lecture JSON
    # ---------------------------------------------------------

    try:

        import json

        with result_path.open(
            "r",
            encoding="utf-8",
        ) as file:

            result = json.load(file)

    except json.JSONDecodeError as exc:

        logger.exception(
            "JSON résultat invalide"
        )

        return jsonify(
            {
                "success": False,
                "error": (
                    "Le résultat JSON est invalide."
                ),
                "code": "INVALID_JSON",
                "details": str(exc),
            }
        ), 500

    except OSError as exc:

        logger.exception(
            "Erreur lecture résultat"
        )

        return jsonify(
            {
                "success": False,
                "error": (
                    "Impossible de lire le résultat."
                ),
                "code": "READ_ERROR",
                "details": str(exc),
            }
        ), 500

    return jsonify(
        {
            "success": True,
            "filename": filename,
            "result": result,
        }
    ), 200


# =============================================================
# EXTRACTION DES CHAMPS UNIQUEMENT
# =============================================================

@extraction_bp.get("/fields/<filename>")
def get_extracted_fields(filename: str):
    """
    Retourne uniquement les champs extraits.

    Exemple :

        GET /api/extraction/fields/test.pdf
    """

    stem = safe_result_filename(
        filename
    )

    result_path = RESULT_DIR / f"{stem}.json"

    if not result_path.exists():

        return jsonify(
            {
                "success": False,
                "error": "Résultat introuvable.",
                "code": "RESULT_NOT_FOUND",
            }
        ), 404

    try:

        import json

        with result_path.open(
            "r",
            encoding="utf-8",
        ) as file:

            result = json.load(file)

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:

        return jsonify(
            {
                "success": False,
                "error": (
                    "Impossible de lire "
                    "le résultat OCR."
                ),
                "code": "READ_ERROR",
                "details": str(exc),
            }
        ), 500

    fields = result.get(
        "fields",
        {},
    )

    return jsonify(
        {
            "success": True,
            "filename": filename,
            "count": (
                len(fields)
                if isinstance(fields, dict)
                else 0
            ),
            "fields": fields,
        }
    ), 200


# =============================================================
# EXTRACTION DES TABLEAUX UNIQUEMENT
# =============================================================

@extraction_bp.get("/tables/<filename>")
def get_extracted_tables(filename: str):
    """
    Retourne uniquement les tableaux détectés.
    """

    stem = safe_result_filename(
        filename
    )

    result_path = RESULT_DIR / f"{stem}.json"

    if not result_path.exists():

        return jsonify(
            {
                "success": False,
                "error": "Résultat introuvable.",
                "code": "RESULT_NOT_FOUND",
            }
        ), 404

    try:

        import json

        with result_path.open(
            "r",
            encoding="utf-8",
        ) as file:

            result = json.load(file)

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:

        return jsonify(
            {
                "success": False,
                "error": (
                    "Impossible de lire "
                    "le résultat OCR."
                ),
                "code": "READ_ERROR",
                "details": str(exc),
            }
        ), 500

    tables = result.get(
        "tables",
        [],
    )

    if not isinstance(tables, list):
        tables = []

    return jsonify(
        {
            "success": True,
            "filename": filename,
            "count": len(tables),
            "tables": tables,
        }
    ), 200


# =============================================================
# TEST CONFIGURATION
# =============================================================

def test_configuration() -> dict:
    """
    Retourne la configuration du module.
    """

    return {
        "upload_directory": str(
            UPLOAD_DIR
        ),
        "result_directory": str(
            RESULT_DIR
        ),
        "ai_enabled": False,
        "llm_enabled": False,
    }


# =============================================================
# TEST LOCAL
# =============================================================

if __name__ == "__main__":

    print("=" * 70)

    print(
        "TEST EXTRACTION ROUTE OCR - SANS IA"
    )

    print("=" * 70)

    print()

    configuration = test_configuration()

    print(
        "Dossier uploads :"
    )

    print(
        f"  {configuration['upload_directory']}"
    )

    print()

    print(
        "Dossier results :"
    )

    print(
        f"  {configuration['result_directory']}"
    )

    print()

    print(
        "IA activée : NON"
    )

    print(
        "LLM activé : NON"
    )

    print()

    print("=" * 70)

    print(
        "TEST EXTRACTION ROUTE TERMINE"
    )

    print("=" * 70)

